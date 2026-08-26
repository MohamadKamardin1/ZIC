from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Callable

from django.db.models import Prefetch, Q, QuerySet
from django.utils import timezone

from apps.ol_parameters.models import (
    OLBeneficialType,
    OLInvestmentFund,
    OLInvestmentFundType,
    OLPlanType,
    OLProduct,
    OLRiderSetup,
)
from apps.partner_onboarding.models import Location
from apps.partners.models import Partner, PartnerTypeAssignment
from apps.system_parameters.services.config_service import ConfigurationService


@dataclass(frozen=True)
class OptionPage:
    """A stable option response independent of the source model."""

    items: list[dict[str, Any]]
    count: int
    page: int
    page_size: int


@dataclass(frozen=True)
class ProviderSpec:
    provider: Callable[[str, int, int], OptionPage]
    searchable: bool = False


DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200


def _choice_options(*codes: str) -> list[dict[str, Any]]:
    """Resolve the first configured choice list, preserving active-only behavior."""

    for code in codes:
        try:
            values = ConfigurationService.get_choice_list(code, active_only=True)
        except Exception:
            continue
        if values:
            return [
                {
                    "value": str(item.get("value", "")),
                    "label": str(item.get("label", item.get("value", ""))),
                    "meta": {"source": code},
                }
                for item in values
                if item.get("value") not in (None, "")
            ]
    return []


def _paginate(items: list[dict[str, Any]], page: int, page_size: int) -> OptionPage:
    page = max(page, 1)
    page_size = min(max(page_size, 1), MAX_PAGE_SIZE)
    start = (page - 1) * page_size
    return OptionPage(items=items[start : start + page_size], count=len(items), page=page, page_size=page_size)


def _active_effective(queryset: QuerySet, today: date | None = None) -> QuerySet:
    """Apply the common lifecycle contract to catalog models where fields exist."""

    today = today or timezone.localdate()
    fields = {field.name for field in queryset.model._meta.get_fields()}
    if "is_active" in fields:
        queryset = queryset.filter(is_active=True)
    if "effective_from" in fields:
        queryset = queryset.filter(Q(effective_from__isnull=True) | Q(effective_from__lte=today))
    if "effective_to" in fields:
        queryset = queryset.filter(Q(effective_to__isnull=True) | Q(effective_to__gte=today))
    return queryset


def _text_match(item: dict[str, Any], query: str) -> bool:
    query = query.strip().casefold()
    if not query:
        return True
    haystack = " ".join(
        str(value)
        for value in [item.get("value"), item.get("label"), item.get("meta", {})]
    ).casefold()
    return query in haystack


def _model_page(
    queryset: QuerySet,
    *,
    label_builder: Callable[[Any], str],
    meta_builder: Callable[[Any], dict[str, Any]] | None = None,
    q: str = "",
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> OptionPage:
    queryset = _active_effective(queryset)
    rows = [
        {
            "value": str(obj.pk),
            "label": label_builder(obj),
            "meta": (meta_builder(obj) if meta_builder else {}),
        }
        for obj in queryset
    ]
    if q:
        rows = [row for row in rows if _text_match(row, q)]
    return _paginate(rows, page, page_size)


def _choice_page(codes: tuple[str, ...], q: str, page: int, page_size: int) -> OptionPage:
    rows = _choice_options(*codes)
    if q:
        rows = [row for row in rows if _text_match(row, q)]
    return _paginate(rows, page, page_size)


def _model_label(obj: Any) -> str:
    code = getattr(obj, "code", "")
    name = getattr(obj, "name", "")
    if code and name:
        return f"{code} — {name}"
    return str(name or code or obj)


def _location_page(q: str, page: int, page_size: int) -> OptionPage:
    queryset = _active_effective(Location.objects.select_related("branch")).order_by("name", "code")
    if q:
        queryset = queryset.filter(
            Q(code__icontains=q) | Q(name__icontains=q) | Q(branch__code__icontains=q) | Q(branch__name__icontains=q)
        )
    return _model_page(
        queryset,
        label_builder=lambda obj: f"{obj.code} — {obj.name}",
        meta_builder=lambda obj: {
            "code": obj.code,
            "branch_id": str(obj.branch_id),
            "branch_display": f"{obj.branch.code} — {obj.branch.name}" if obj.branch_id else None,
        },
        page=page,
        page_size=page_size,
    )


def _partner_location_display(obj: Partner) -> str | None:
    assignments = getattr(obj, "_active_option_assignments", None)
    assignment = assignments[0] if assignments else obj.type_assignments.filter(status="ACTIVE").select_related("location").order_by("-created_at").first()
    location = getattr(assignment, "location", None)
    if not location:
        return None
    code = getattr(location, "code", "")
    name = getattr(location, "name", "")
    return f"{code} — {name}" if code and name else name or code or None


def _partner_display(obj: Partner) -> str:
    name = getattr(obj, "legal_name", "") or getattr(obj, "company_name", "") or getattr(obj, "display_name", "")
    if not name:
        name = " ".join(part for part in [getattr(obj, "first_name", ""), getattr(obj, "other_name", ""), getattr(obj, "surname", "")] if part).strip()
    return f"{obj.partner_number} — {name}" if obj.partner_number and name else str(obj.partner_number or name or obj.pk)


def _partner_option_page(partner_types: tuple[str, ...], q: str, page: int, page_size: int) -> OptionPage:
    queryset = Partner.objects.filter(
        partner_type__in=partner_types,
        is_active=True,
        status="ACTIVE",
    ).prefetch_related(
        Prefetch(
            "type_assignments",
            queryset=PartnerTypeAssignment.objects.filter(status="ACTIVE").select_related("location").order_by("-created_at"),
            to_attr="_active_option_assignments",
        )
    ).order_by("partner_number", "legal_name", "company_name")
    if q:
        queryset = queryset.filter(
            Q(legal_name__icontains=q)
            | Q(partner_number__icontains=q)
            | Q(registration_number__icontains=q)
        )
    return _model_page(
        queryset,
        label_builder=_partner_display,
        meta_builder=lambda obj: {
            "partner_type": obj.partner_type,
            "location": _partner_location_display(obj),
            "active_status": obj.status,
        },
        page=page,
        page_size=page_size,
    )


def _bank_page(q: str, page: int, page_size: int) -> OptionPage:
    return _partner_option_page(("BANK",), q, page, page_size)


def _intermediary_page(q: str, page: int, page_size: int) -> OptionPage:
    return _partner_option_page(("INTERMEDIARY", "AGENT"), q, page, page_size)


def _employer_page(q: str, page: int, page_size: int) -> OptionPage:
    return _partner_option_page(("EMPLOYER", "CORPORATE"), q, page, page_size)


def _agent_display(obj: Partner) -> str:
    name = " ".join(
        part for part in [getattr(obj, "title", ""), getattr(obj, "first_name", ""), getattr(obj, "surname", "")]
        if part
    ).strip() or getattr(obj, "legal_name", "") or getattr(obj, "partner_number", "")
    return f"{obj.partner_number} — {name}" if obj.partner_number else name


def _agent_page(q: str, page: int, page_size: int) -> OptionPage:
    agent_type = ConfigurationService.get_str_parameter("OL_AGENT_PARTNER_TYPE_CODE", "AGENT")
    queryset = Partner.objects.filter(
        is_active=True,
        status="ACTIVE",
        type_assignments__status="ACTIVE",
        type_assignments__partner_type__is_active=True,
        type_assignments__partner_type__code__iexact=agent_type,
    ).distinct().order_by("partner_number", "legal_name", "surname", "first_name")
    if q:
        queryset = queryset.filter(
            Q(partner_number__icontains=q)
            | Q(legal_name__icontains=q)
            | Q(first_name__icontains=q)
            | Q(surname__icontains=q)
        )
    return _model_page(
        queryset,
        label_builder=_agent_display,
        meta_builder=lambda obj: {
            "partner_number": obj.partner_number,
            "partner_type": agent_type,
            "status": obj.status,
        },
        page=page,
        page_size=page_size,
    )


def _product_page(q: str, page: int, page_size: int) -> OptionPage:
    queryset = _active_effective(OLProduct.objects.select_related("plan_type")).order_by("code", "name")
    if q:
        queryset = queryset.filter(
            Q(code__icontains=q) | Q(name__icontains=q) | Q(plan_type__code__icontains=q) | Q(plan_type__name__icontains=q)
        )
    return _model_page(
        queryset,
        label_builder=_model_label,
        meta_builder=lambda obj: {
            "code": obj.code,
            "plan_type_id": str(obj.plan_type_id),
            "plan_type_display": _model_label(obj.plan_type),
            "currency": obj.currency,
            "investment_linked": obj.investment_linked,
            "premium_frequencies": obj.premium_frequencies,
        },
        page=page,
        page_size=page_size,
    )


def _plan_type_page(q: str, page: int, page_size: int) -> OptionPage:
    queryset = _active_effective(OLPlanType.objects.all()).order_by("code", "name")
    if q:
        queryset = queryset.filter(Q(code__icontains=q) | Q(name__icontains=q) | Q(plan_category__icontains=q))
    return _model_page(
        queryset,
        label_builder=_model_label,
        meta_builder=lambda obj: {"code": obj.code, "plan_category": obj.plan_category},
        page=page,
        page_size=page_size,
    )


def _fund_type_page(q: str, page: int, page_size: int) -> OptionPage:
    queryset = _active_effective(OLInvestmentFundType.objects.all()).order_by("code", "name")
    if q:
        queryset = queryset.filter(Q(code__icontains=q) | Q(name__icontains=q) | Q(risk_profile__icontains=q))
    return _model_page(
        queryset,
        label_builder=_model_label,
        meta_builder=lambda obj: {"code": obj.code, "risk_profile": obj.risk_profile},
        page=page,
        page_size=page_size,
    )


def _fund_page(q: str, page: int, page_size: int) -> OptionPage:
    queryset = _active_effective(OLInvestmentFund.objects.select_related("fund_type")).order_by("code", "name")
    if q:
        queryset = queryset.filter(
            Q(code__icontains=q)
            | Q(name__icontains=q)
            | Q(currency__icontains=q)
            | Q(fund_type__code__icontains=q)
            | Q(fund_type__name__icontains=q)
        )
    return _model_page(
        queryset,
        label_builder=lambda obj: f"{obj.code} — {obj.name}",
        meta_builder=lambda obj: {
            "code": obj.code,
            "fund_type_id": str(obj.fund_type_id),
            "fund_type_display": _model_label(obj.fund_type),
            "risk_profile": obj.fund_type.risk_profile,
            "currency": obj.currency,
            "valuation_frequency": obj.valuation_frequency,
        },
        page=page,
        page_size=page_size,
    )


def _rider_page(q: str, page: int, page_size: int) -> OptionPage:
    queryset = _active_effective(OLRiderSetup.objects.select_related("product", "plan")).order_by("code", "name")
    if q:
        queryset = queryset.filter(Q(code__icontains=q) | Q(name__icontains=q) | Q(description__icontains=q))
    return _model_page(
        queryset,
        label_builder=_model_label,
        meta_builder=lambda obj: {
            "code": obj.code,
            "rider_category": obj.rider_category,
            "benefit_type": obj.benefit_type,
            "calculation_basis": obj.calculation_basis,
            "product_id": str(obj.product_id) if obj.product_id else None,
            "product_display": _model_label(obj.product) if obj.product_id else None,
            "plan_id": str(obj.plan_id) if obj.plan_id else None,
            "plan_display": _model_label(obj.plan) if obj.plan_id else None,
        },
        page=page,
        page_size=page_size,
    )


def _benefit_type_page(q: str, page: int, page_size: int) -> OptionPage:
    queryset = _active_effective(OLBeneficialType.objects.all()).order_by("code", "name")
    if q:
        queryset = queryset.filter(Q(code__icontains=q) | Q(name__icontains=q) | Q(category__icontains=q))
    return _model_page(
        queryset,
        label_builder=_model_label,
        meta_builder=lambda obj: {"code": obj.code, "category": obj.category, "calculation_basis": obj.calculation_basis},
        page=page,
        page_size=page_size,
    )


CHOICE_PROVIDERS: dict[str, tuple[str, ...]] = {
    "identity-types": ("IDENTIFICATION_TYPE_CHOICES", "DOCUMENT_TYPE_CHOICES"),
    "payment-frequencies": ("OL_PREMIUM_FREQUENCY_CHOICES", "PREMIUM_FREQUENCY_CHOICES"),
    "quote-bases": ("OL_QUOTE_BASIS_CHOICES",),
    "premium-factors": ("OL_PREMIUM_FACTOR_CHOICES",),
    "member-relations": ("OL_MEMBER_RELATION_CHOICES",),
    "cover-types": ("OL_COVER_TYPE_CHOICES",),
    "payment-modes": ("OL_PAYMENT_MODE_CHOICES",),
    "benefit-type-codes": ("OL_BENEFIT_TYPE_CHOICES",),
    "currencies": ("CURRENCY_CHOICES",),
}

MODEL_PROVIDERS: dict[str, Callable[[str, int, int], OptionPage]] = {
    "locations": _location_page,
    "agents": _agent_page,
    "banks": _bank_page,
    "intermediaries": _intermediary_page,
    "employers": _employer_page,
    "products": _product_page,
    "plan-types": _plan_type_page,
    "investment-funds": _fund_page,
    "investment-fund-types": _fund_type_page,
    "riders": _rider_page,
    # `benefit-types` is the public FK option entity used by quotation
    # benefits and therefore must return OLBeneficialType UUID values.
    "benefit-types": _benefit_type_page,
    "benefit-types-catalog": _benefit_type_page,
}


ENTITY_ALIASES = {
    "identity-type": "identity-types",
    "identity_type": "identity-types",
    "identity_types": "identity-types",
    "payment-frequency": "payment-frequencies",
    "payment_frequency": "payment-frequencies",
    "payment_frequencies": "payment-frequencies",
    "quote-base": "quote-bases",
    "quote_basis": "quote-bases",
    "quote_bases": "quote-bases",
    "premium-factor": "premium-factors",
    "premium_factor": "premium-factors",
    "premium_factors": "premium-factors",
    "member-relation": "member-relations",
    "member_relation": "member-relations",
    "member_relations": "member-relations",
    "cover-type": "cover-types",
    "cover_type": "cover-types",
    "cover_types": "cover-types",
    "payment-mode": "payment-modes",
    "payment_mode": "payment-modes",
    "payment_modes": "payment-modes",
    "investment-fund": "investment-funds",
    "investment_fund": "investment-funds",
    "investment_funds": "investment-funds",
    "investment-fund-type": "investment-fund-types",
    "investment_fund_type": "investment-fund-types",
    "investment_fund_types": "investment-fund-types",
    "benefit-type": "benefit-types",
    "benefit_type": "benefit-types",
    "benefit_types": "benefit-types",
    "benefit-code": "benefit-type-codes",
    "benefit_type_code": "benefit-type-codes",
    "benefit_type_codes": "benefit-type-codes",
    "bank": "banks",
    "intermediary": "intermediaries",
    "employer": "employers",
}


def canonical_entity(entity: str) -> str:
    normalized = (entity or "").strip().lower().replace("_", "-")
    return ENTITY_ALIASES.get(normalized, normalized)


def list_entities() -> list[str]:
    return sorted(set(CHOICE_PROVIDERS) | set(MODEL_PROVIDERS))


def get_options(entity: str, *, q: str = "", page: int = 1, page_size: int = DEFAULT_PAGE_SIZE) -> tuple[str, OptionPage]:
    canonical = canonical_entity(entity)
    if canonical in CHOICE_PROVIDERS:
        return canonical, _choice_page(CHOICE_PROVIDERS[canonical], q, page, page_size)
    provider = MODEL_PROVIDERS.get(canonical)
    if provider is None:
        raise KeyError(canonical)
    return canonical, provider(q, page, page_size)
