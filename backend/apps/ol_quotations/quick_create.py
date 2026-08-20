from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q

from apps.governance.models import AuditLog
from apps.governance.services.audit_service import AuditService
from apps.ol_parameters.models import (
    OLBeneficialType,
    OLBeneficialTypeCategory,
    OLInsuranceClass,
    OLInvestmentFund,
    OLInvestmentFundRiskProfile,
    OLInvestmentFundType,
    OLPlanType,
    OLProduct,
    OLRiderBenefitType,
    OLRiderCalculationBasis,
    OLRiderCategory,
    OLRiderSetup,
    OLValuationFrequency,
)
from apps.ol_parameters.services.default_setup_service import OLDefaultSetupService
from apps.partner_onboarding.models import Branch, Location
from apps.partners.models import Partner, PartnerType
from apps.partners.services.partner_type_service import PartnerTypeAssignmentService
from apps.system_parameters.models import ChoiceList, ChoiceOption
from apps.system_parameters.services.config_service import ConfigurationService
from apps.system_parameters.services.numbering_service import NumberingEngine

from .option_registry import canonical_entity, get_options


QUICK_CREATE_REASON = "Created from OL quotation wizard"
QUICK_CREATE_CHANNEL = AuditLog.SourceChannel.QUICK_CREATE


@dataclass(frozen=True)
class FieldSpec:
    name: str
    type: str = "string"
    required: bool = True
    choices: tuple[tuple[str, str], ...] = ()
    default: Any = None
    nested_entity: str | None = None

    def as_dict(self) -> dict[str, Any]:
        payload = {
            "name": self.name,
            "type": self.type,
            "required": self.required,
            "choices": [{"value": value, "label": label} for value, label in self.choices],
            "default": self.default,
        }
        if self.nested_entity:
            payload["nested_entity"] = self.nested_entity
        return payload


@dataclass(frozen=True)
class QuickCreateSpec:
    entity: str
    permission: str
    fields: tuple[FieldSpec, ...]
    creator: Callable[[dict[str, Any], Any, Any], Any]

    def schema(self) -> dict[str, Any]:
        fields = [field.as_dict() for field in self.fields]
        return {
            "entity": self.entity,
            "permission": self.permission,
            "fields": fields,
            "defaults": {field.name: field.default for field in self.fields if field.default is not None},
        }


def _enum_choices(enum_class) -> tuple[tuple[str, str], ...]:
    return tuple((value, label) for value, label in enum_class.choices)


def _dynamic_choices(entity: str) -> tuple[tuple[str, str], ...]:
    try:
        _canonical, page = get_options(entity, page=1, page_size=200)
    except (KeyError, Exception):
        return ()
    return tuple((str(item["value"]), str(item["label"])) for item in page.items)


def _choice_list_for(entity: str) -> ChoiceList:
    from .option_registry import CHOICE_PROVIDERS

    codes = CHOICE_PROVIDERS.get(entity, ())
    choice_list = ChoiceList.objects.filter(code__in=codes, is_active=True).order_by("code").first()
    if choice_list is None:
        raise ValidationError({"entity": f"No active choice list is configured for '{entity}'."})
    return choice_list


def _clean_text(data: dict[str, Any], field: str, *, required: bool = True) -> str:
    value = data.get(field)
    if value is None:
        value = ""
    value = str(value).strip()
    if required and not value:
        raise ValidationError({field: "This field is required."})
    return value


def _duplicate_error(model, code: str, name: str, *, exclude=None) -> None:
    queryset = model.objects.filter(Q(code__iexact=code) | Q(name__iexact=name))
    if exclude is not None:
        queryset = queryset.exclude(pk=exclude.pk)
    match = queryset.first()
    if match is not None:
        duplicate_field = "code" if str(match.code).casefold() == code.casefold() else "name"
        raise ValidationError({duplicate_field: f"An active or existing {model._meta.verbose_name} with this {duplicate_field} already exists."})


def _create_ol_model(model, data: dict[str, Any], actor, request):
    code = _clean_text(data, "code")
    name = _clean_text(data, "name")
    _duplicate_error(model, code, name)
    payload = {key: value for key, value in data.items() if key not in {"code", "name"} and value is not None}
    payload.update(code=code, name=name, is_active=True)
    try:
        return OLDefaultSetupService.create(
            model=model,
            actor=actor,
            data=payload,
            request=request,
            audit_reason=QUICK_CREATE_REASON,
            source_channel=QUICK_CREATE_CHANNEL,
        )
    except IntegrityError as exc:
        raise ValidationError({"code": "An option with this code already exists."}) from exc


def _resolve_model_ref(model, value: Any, field: str):
    if value in (None, ""):
        raise ValidationError({field: "This field is required."})
    queryset = model.objects.filter(is_active=True)
    try:
        instance = queryset.filter(pk=value).first()
    except (ValueError, TypeError):
        instance = None
    if instance is None:
        instance = queryset.filter(code__iexact=str(value).strip()).first()
    if instance is None:
        raise ValidationError({field: "Select a valid active option."})
    return instance


def _create_choice(entity: str, data: dict[str, Any], actor, request):
    code = _clean_text(data, "code")
    name = _clean_text(data, "name")
    choice_list = _choice_list_for(entity)
    existing = choice_list.options.filter(Q(code__iexact=code) | Q(label__iexact=name)).first()
    if existing is not None:
        duplicate_field = "code" if existing.code.casefold() == code.casefold() else "name"
        raise ValidationError({duplicate_field: f"An option with this {duplicate_field} already exists."})
    next_sort = (choice_list.options.order_by("-sort_order").values_list("sort_order", flat=True).first() or 0) + 1
    try:
        option = ChoiceOption.objects.create(
            choice_list=choice_list,
            code=code,
            label=name,
            is_active=True,
            sort_order=next_sort,
            metadata={"source_channel": QUICK_CREATE_CHANNEL, "reason": QUICK_CREATE_REASON},
        )
    except IntegrityError as exc:
        raise ValidationError({"code": "An option with this code already exists."}) from exc
    ConfigurationService.invalidate_cache()
    AuditService.log_create(
        option,
        actor=actor,
        request=request,
        reason=QUICK_CREATE_REASON,
        source_channel=QUICK_CREATE_CHANNEL,
    )
    return option


def _create_location(data: dict[str, Any], actor, request):
    code = _clean_text(data, "code")
    name = _clean_text(data, "name")
    branch = _resolve_model_ref(Branch, data.get("branch"), "branch")
    if Location.objects.filter(branch=branch, code__iexact=code).exists():
        raise ValidationError({"code": "A location with this code already exists in the selected branch."})
    if Location.objects.filter(branch=branch, name__iexact=name).exists():
        raise ValidationError({"name": "A location with this name already exists in the selected branch."})
    try:
        location = Location.objects.create(branch=branch, code=code, name=name, is_active=True)
    except IntegrityError as exc:
        raise ValidationError({"code": "A location with this code already exists in the selected branch."}) from exc
    AuditService.log_create(location, actor=actor, request=request, reason=QUICK_CREATE_REASON, source_channel=QUICK_CREATE_CHANNEL)
    return location


def _create_agent(data: dict[str, Any], actor, request):
    partner_type = _clean_text(data, "partner_type").upper()
    if partner_type not in {"AGENT", "INTERMEDIARY"}:
        raise ValidationError({"partner_type": "Partner type must be AGENT or INTERMEDIARY."})
    legal_name = _clean_text(data, "legal_name")
    email = _clean_text(data, "email").lower()
    phone = _clean_text(data, "phone")
    national_id = _clean_text(data, "national_id", required=False)
    duplicate = Partner.objects.filter(Q(email__iexact=email) | Q(mobile_number=phone))
    if national_id:
        duplicate = duplicate | Partner.objects.filter(Q(national_id__iexact=national_id) | Q(identification_number__iexact=national_id))
    if duplicate.exists():
        raise ValidationError({"email": "A partner with this email, phone, or national ID already exists."})

    partner = Partner(
        partner_number=NumberingEngine.generate_partner_number(),
        partner_type=partner_type,
        partner_category="CORPORATE",
        party_type="CORPORATE",
        legal_name=legal_name,
        company_name=legal_name,
        email=email,
        phone=phone,
        mobile_number=phone,
        national_id=national_id,
        identification_number=national_id,
        identification_type="NIN" if national_id else "",
        status="ACTIVE",
        is_active=True,
        created_by=actor,
        updated_by=actor,
    )
    partner.full_clean()
    partner.save()

    partner_type_record = PartnerType.objects.filter(code__iexact=partner_type, is_active=True).first()
    if partner_type_record is None:
        partner_type_record = PartnerType.objects.create(code=partner_type, name=partner_type.title(), is_active=True)
        AuditService.log_create(partner_type_record, actor=actor, request=request, reason=QUICK_CREATE_REASON, source_channel=QUICK_CREATE_CHANNEL)
    PartnerTypeAssignmentService.assign(partner, partner_type_record)
    AuditService.log_create(partner, actor=actor, request=request, reason=QUICK_CREATE_REASON, source_channel=QUICK_CREATE_CHANNEL)
    return partner


def _create_plan_type(data: dict[str, Any], actor, request):
    payload = {"plan_category": str(data.get("plan_category") or "INDIVIDUAL").strip().upper()}
    return _create_ol_model(OLPlanType, {**data, **payload}, actor, request)


def _create_fund_type(data: dict[str, Any], actor, request):
    risk_profile = str(data.get("risk_profile") or OLInvestmentFundRiskProfile.MODERATE).strip().upper()
    return _create_ol_model(OLInvestmentFundType, {**data, "risk_profile": risk_profile}, actor, request)


def _create_fund(data: dict[str, Any], actor, request):
    fund_type = _resolve_model_ref(OLInvestmentFundType, data.get("fund_type"), "fund_type")
    payload = {
        **data,
        "fund_type": fund_type,
        "currency": str(data.get("currency") or "TZS").strip().upper(),
        "valuation_frequency": str(data.get("valuation_frequency") or OLValuationFrequency.DAILY).strip().upper(),
    }
    return _create_ol_model(OLInvestmentFund, payload, actor, request)


def _create_product(data: dict[str, Any], actor, request):
    plan_type = _resolve_model_ref(OLPlanType, data.get("plan_type"), "plan_type")
    payload = {
        **data,
        "plan_type": plan_type,
        "insurance_class": str(data.get("insurance_class") or OLInsuranceClass.INDIVIDUAL).strip().upper(),
        "currency": str(data.get("currency") or "TZS").strip().upper(),
        "premium_frequencies": data.get("premium_frequencies") or [],
        "allow_surrender": bool(data.get("allow_surrender", True)),
    }
    for field in ("allow_riders", "allow_loans", "allow_withdrawals", "allow_paidup", "allow_bonus", "investment_linked"):
        payload[field] = bool(data.get(field, False))
    return _create_ol_model(OLProduct, payload, actor, request)


def _create_rider(data: dict[str, Any], actor, request):
    payload = {
        **data,
        "rider_category": str(data.get("rider_category") or "OTHER").strip().upper(),
        "benefit_type": str(data.get("benefit_type") or "OTHER").strip().upper(),
        "calculation_basis": str(data.get("calculation_basis") or OLRiderCalculationBasis.SUM_ASSURED).strip().upper(),
    }
    return _create_ol_model(OLRiderSetup, payload, actor, request)


def _create_benefit_catalog(data: dict[str, Any], actor, request):
    payload = {
        **data,
        "category": str(data.get("category") or OLBeneficialTypeCategory.BENEFIT).strip().upper(),
        "calculation_basis": str(data.get("calculation_basis") or "PERCENTAGE").strip().upper(),
        "default_ratio": data.get("default_ratio", 0),
    }
    return _create_ol_model(OLBeneficialType, payload, actor, request)


def _model_fields(model: Any) -> tuple[FieldSpec, ...]:
    return (
        FieldSpec("code"),
        FieldSpec("name"),
    )


def _branch_choices() -> tuple[tuple[str, str], ...]:
    return tuple((str(item.pk), f"{item.code} — {item.name}") for item in Branch.objects.filter(is_active=True).order_by("name"))


def _specs() -> dict[str, QuickCreateSpec]:
    choice_specs = {
        entity: QuickCreateSpec(entity, "system_parameters.manage", (FieldSpec("code"), FieldSpec("name")), lambda data, actor, request, entity=entity: _create_choice(entity, data, actor, request))
        for entity in (
            "identity-types", "payment-frequencies", "quote-bases", "premium-factors", "member-relations",
            "cover-types", "payment-modes", "benefit-types", "currencies",
        )
    }
    return {
        **choice_specs,
        "locations": QuickCreateSpec(
            "locations", "ol_parameters.create",
            (FieldSpec("code"), FieldSpec("name"), FieldSpec("branch", "select", True, _branch_choices())),
            _create_location,
        ),
        "agents": QuickCreateSpec(
            "agents", "partners.create",
            (
                FieldSpec("partner_type", "select", True, (("AGENT", "Agent"), ("INTERMEDIARY", "Intermediary")), "AGENT"),
                FieldSpec("legal_name"), FieldSpec("national_id", required=False), FieldSpec("phone"), FieldSpec("email", "email"),
            ), _create_agent,
        ),
        "plan-types": QuickCreateSpec("plan-types", "ol_parameters.create", (*_model_fields(OLPlanType), FieldSpec("plan_category", "select", False, (("INDIVIDUAL", "Individual"), ("GROUP", "Group"), ("CREDIT", "Credit")), "INDIVIDUAL")), _create_plan_type),
        "investment-fund-types": QuickCreateSpec("investment-fund-types", "ol_parameters.create", (*_model_fields(OLInvestmentFundType), FieldSpec("risk_profile", "select", False, _enum_choices(OLInvestmentFundRiskProfile), OLInvestmentFundRiskProfile.MODERATE)), _create_fund_type),
        "investment-funds": QuickCreateSpec("investment-funds", "ol_parameters.create", (*_model_fields(OLInvestmentFund), FieldSpec("fund_type", "select", True, (), None, "investment-fund-types"), FieldSpec("currency", "select", False, _dynamic_choices("currencies"), "TZS"), FieldSpec("valuation_frequency", "select", False, _enum_choices(OLValuationFrequency), OLValuationFrequency.DAILY)), _create_fund),
        "products": QuickCreateSpec("products", "ol_parameters.create", (*_model_fields(OLProduct), FieldSpec("plan_type", "select", True, (), None, "plan-types"), FieldSpec("insurance_class", "select", False, _enum_choices(OLInsuranceClass), OLInsuranceClass.INDIVIDUAL), FieldSpec("allow_riders", "boolean", False, (), False), FieldSpec("allow_loans", "boolean", False, (), False), FieldSpec("allow_withdrawals", "boolean", False, (), False), FieldSpec("allow_surrender", "boolean", False, (), True), FieldSpec("allow_paidup", "boolean", False, (), False), FieldSpec("allow_bonus", "boolean", False, (), False), FieldSpec("investment_linked", "boolean", False, (), False)), _create_product),
        "riders": QuickCreateSpec("riders", "ol_parameters.create", (*_model_fields(OLRiderSetup), FieldSpec("rider_category", "select", True, _enum_choices(OLRiderCategory)), FieldSpec("benefit_type", "select", True, _enum_choices(OLRiderBenefitType)), FieldSpec("calculation_basis", "select", False, _enum_choices(OLRiderCalculationBasis), OLRiderCalculationBasis.SUM_ASSURED)), _create_rider),
        "benefit-types-catalog": QuickCreateSpec("benefit-types-catalog", "ol_parameters.create", (*_model_fields(OLBeneficialType), FieldSpec("category", "select", False, _enum_choices(OLBeneficialTypeCategory), OLBeneficialTypeCategory.BENEFIT), FieldSpec("calculation_basis", required=False, default="PERCENTAGE"), FieldSpec("default_ratio", "decimal", False, (), 0)), _create_benefit_catalog),
    }


def get_quick_create_spec(entity: str) -> QuickCreateSpec:
    canonical = canonical_entity(entity)
    spec = _specs().get(canonical)
    if spec is None:
        raise KeyError(canonical)
    return spec


def list_quick_create_entities() -> list[str]:
    return sorted(_specs())


def get_quick_create_schema(entity: str) -> dict[str, Any]:
    spec = get_quick_create_spec(entity)
    schema = spec.schema()
    dynamic_choices = {
        "branch": _branch_choices(),
        "plan_type": tuple(
            (str(item.pk), f"{item.code} — {item.name}")
            for item in OLPlanType.objects.filter(is_active=True).order_by("name", "code")
        ),
        "fund_type": tuple(
            (str(item.pk), f"{item.code} — {item.name}")
            for item in OLInvestmentFundType.objects.filter(is_active=True).order_by("name", "code")
        ),
        "currency": _dynamic_choices("currencies"),
    }
    for field in schema["fields"]:
        if field["name"] in dynamic_choices:
            field["choices"] = [
                {"value": value, "label": label}
                for value, label in dynamic_choices[field["name"]]
            ]
    return schema


def check_quick_create_permission(user, spec: QuickCreateSpec) -> None:
    if getattr(user, "is_superuser", False):
        return
    module, action = spec.permission.split(".", 1)
    if not user.has_module_permission(module, action.upper()):
        from rest_framework.exceptions import PermissionDenied
        raise PermissionDenied(f"Missing permission: {spec.permission}")


def _created_payload(entity: str, instance: Any) -> dict[str, Any]:
    if isinstance(instance, ChoiceOption):
        return {"id": str(instance.pk), "code": instance.code, "name": instance.label, "value": instance.code, "label": instance.label, "meta": {"choice_list": instance.choice_list.code}}
    if isinstance(instance, Location):
        label = f"{instance.code} — {instance.name}"
        return {"id": str(instance.pk), "code": instance.code, "name": instance.name, "value": str(instance.pk), "label": label, "meta": {"branch_id": str(instance.branch_id), "branch_display": f"{instance.branch.code} — {instance.branch.name}"}}
    if isinstance(instance, Partner):
        name = instance.display_name or instance.legal_name or instance.partner_number
        label = f"{instance.partner_number} — {name}"
        return {"id": str(instance.pk), "code": instance.partner_number, "name": name, "value": str(instance.pk), "label": label, "meta": {"partner_number": instance.partner_number, "partner_type": instance.partner_type, "completion_required": not bool(instance.national_id)}}
    code = getattr(instance, "code", str(instance.pk))
    name = getattr(instance, "name", str(instance))
    meta = {"code": code, "name": name}
    for field in ("plan_type_id", "fund_type_id", "currency", "rider_category", "benefit_type", "investment_linked"):
        if hasattr(instance, field):
            value = getattr(instance, field)
            meta[field] = str(value) if value is not None else None
    return {"id": str(instance.pk), "code": code, "name": name, "value": str(instance.pk), "label": f"{code} — {name}", "meta": meta}


@transaction.atomic
def create_quick_option(entity: str, data: dict[str, Any], actor, request) -> dict[str, Any]:
    spec = get_quick_create_spec(entity)
    check_quick_create_permission(actor, spec)
    instance = spec.creator(data, actor, request)
    return _created_payload(spec.entity, instance)
