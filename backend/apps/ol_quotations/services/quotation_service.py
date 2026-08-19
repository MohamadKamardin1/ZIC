from datetime import date
from decimal import Decimal

from django.db import models, transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.common.models import DomainEvent
from apps.governance.services.audit_service import AuditService
from apps.system_parameters.services.config_service import ConfigurationService
from apps.system_parameters.services.numbering_service import NumberingEngine

from apps.ol_parameters.models import (
    OLBonusRate,
    OLAnticipatedEndowmentInstallmentRate,
    OLPaidUpRate,
    OLMemberCoverConfiguration,
    OLJointLifeSetup,
    OLMortgageInterestFactor,
    OLInvestmentFund,
    OLRiderSetup,
    OLProduct as ParameterProduct,
)
from apps.ordinary_life.models import OLPlan, OLProductVersion
from apps.ol_quotations.models import (
    OLQuotation,
    OLQuotationEvent,
    OLQuotationFinancialSummary,
    OLQuotationInstallmentConfiguration,
    OLQuotationInstallmentRateRow,
    OLQuotationMember,
    OLQuotationFundAllocation,
    OLQuotationPlanConfiguration,
    OLQuotationVersion,
    QuotationStatus,
)


class QuotationServiceError(ValidationError):
    """A domain validation or lifecycle error for quotation workflows."""


class QuotationService:
    MODULE = "ol_quotations"

    @staticmethod
    def actor(user):
        return user if user and not getattr(user, "is_anonymous", False) else None

    @staticmethod
    def default_currency():
        value = ConfigurationService.get_str_parameter("DEFAULT_CURRENCY", "TZS")
        value = (value or "TZS").strip().upper()
        return value if len(value) == 3 and value.isalpha() else "TZS"

    @staticmethod
    def generate_quote_number():
        return NumberingEngine.generate_number(
            numbering_code="OL_QUOTATION",
            model_class=OLQuotation,
            field_name="quote_number",
        )

    @staticmethod
    def snapshot(quotation):
        return {
            "id": str(quotation.pk),
            "quote_number": quotation.quote_number,
            "quote_name": quotation.quote_name,
            "quote_date": quotation.quote_date.isoformat() if quotation.quote_date else None,
            "status": quotation.status,
            "partner_id": str(quotation.partner_id) if quotation.partner_id else None,
            "linked_partner_id": str(quotation.linked_partner_id) if quotation.linked_partner_id else None,
            "product_id": str(quotation.product_id) if quotation.product_id else None,
            "product_version_id": str(quotation.product_version_id) if quotation.product_version_id else None,
            "product_selection_ids": [str(pk) for pk in quotation.products.filter(is_selected=True).values_list("pk", flat=True)],
            "currency": quotation.currency,
            "current_version_number": quotation.current_version_number,
            "wizard_step_completion": quotation.wizard_step_completion or {},
            "identity_type": quotation.identity_type,
            "identity_number": quotation.identity_number,
            "date_of_birth": quotation.date_of_birth.isoformat() if quotation.date_of_birth else None,
            "age_at_quote": quotation.age_at_quote,
            "gender": quotation.gender,
            "smoker_status": quotation.smoker_status,
            "location": quotation.location,
            "location_master_id": str(quotation.location_master_id) if quotation.location_master_id else None,
            "agent_id": str(quotation.agent_id) if quotation.agent_id else None,
            "agent_partner_id": str(quotation.agent_partner_id) if quotation.agent_partner_id else None,
            "address": quotation.address,
            "partner_verified": quotation.partner_verified,
            "approval_required": quotation.approval_required,
            "expiry_date": quotation.expiry_date.isoformat() if quotation.expiry_date else None,
            "total_sum_assured": str(quotation.total_sum_assured) if quotation.total_sum_assured is not None else None,
            "total_premium": str(quotation.total_premium) if quotation.total_premium is not None else None,
            "calculation_snapshot": quotation.calculation_snapshot or {},
        }

    @staticmethod
    def _plan_requires_investment_funds(plan_config, quotation=None):
        rules = dict(plan_config.coverage_rules or {})
        for key in ("investment_linked", "investment_linked_plan", "requires_investment_funds"):
            if key in rules:
                return bool(rules[key])
        product_rules = dict(getattr(plan_config.product_version, "servicing_rules", {}) or {})
        for key in ("investment_linked", "investment_linked_plan", "requires_investment_funds"):
            if key in product_rules:
                return bool(product_rules[key])
        if quotation is not None:
            if getattr(getattr(quotation, "product", None), "investment_linked", False):
                return True
            return quotation.products.filter(
                is_selected=True,
                product__investment_linked=True,
            ).exists()
        return False

    @staticmethod
    def wizard_completion(quotation):
        selected_plan = (
            quotation.plan_configurations.filter(is_selected=True).exists()
            or quotation.products.filter(is_selected=True).exists()
        )
        members = quotation.members.exists()
        selected_installments = quotation.installment_configurations.filter(is_selected=True).exists()
        applicable_plan_configs = [
            config
            for config in quotation.plan_configurations.filter(is_selected=True).select_related("product_version__product")
            if QuotationService._plan_requires_investment_funds(config, quotation)
        ]
        funds = quotation.fund_allocations.filter(is_selected=True)
        fund_complete = True
        if applicable_plan_configs:
            fund_complete = all(
                funds.filter(plan_configuration=config).aggregate(total=models.Sum("allocation_percentage"))["total"] == Decimal("100")
                for config in applicable_plan_configs
            )
        riders_or_benefits = not quotation.rider_selections.filter(is_selected=True).exists() and not quotation.benefits.filter(is_selected=True).exists()
        if quotation.rider_selections.filter(is_selected=True).exists() or quotation.benefits.filter(is_selected=True).exists():
            riders_or_benefits = True
        payment = hasattr(quotation, "payment_detail")
        underwriting = hasattr(quotation, "underwriting_detail")
        personal_details = bool(
            quotation.quote_name
            or quotation.identity_type
            or quotation.identity_number
            or quotation.date_of_birth
            or quotation.partner_id
            or quotation.linked_partner_id
            or quotation.agent_id
            or quotation.agent_partner_id
            or quotation.address
            or quotation.location
        )
        return {
            "1_personal_details": personal_details,
            "2_plan_and_sub_products": selected_plan,
            "3_member_coverage": members,
            "4_installments": selected_installments,
            "5_investment_funds": fund_complete,
            "6_riders_and_benefits": riders_or_benefits,
            "7_financial_details": payment and underwriting,
        }

    @staticmethod
    def _record_version(quotation, actor=None, reason=""):
        snapshot = QuotationService.snapshot(quotation)
        return OLQuotationVersion.objects.create(
            quotation=quotation,
            version_number=quotation.current_version_number,
            status=quotation.status,
            snapshot=snapshot,
            change_reason=reason or "Quotation version captured.",
            created_by=QuotationService.actor(actor),
            updated_by=QuotationService.actor(actor),
        )

    @staticmethod
    def _record_event(
        quotation,
        event_type,
        actor=None,
        from_status="",
        to_status="",
        notes="",
        metadata=None,
        before_state=None,
        after_state=None,
        request=None,
    ):
        event = OLQuotationEvent.objects.create(
            quotation=quotation,
            event_type=event_type,
            from_status=from_status or "",
            to_status=to_status or "",
            actor=QuotationService.actor(actor),
            notes=notes or "",
            metadata=metadata or {},
        )
        AuditService.log_action(
            action=event_type,
            instance=quotation,
            actor=actor,
            request=request,
            before_state=before_state,
            after_state=after_state,
            changed_fields=AuditService.changed_fields(before_state or {}, after_state or {}),
            reason=notes or event_type.replace("_", " ").title(),
        )
        DomainEvent.objects.create(
            event_type=f"Quotation{event_type.title().replace('_', '')}",
            aggregate_type="OLQuotation",
            aggregate_id=str(quotation.pk),
            payload={
                "quote_number": quotation.quote_number,
                "quotation_id": str(quotation.pk),
                "actor_id": str(actor.pk) if actor and getattr(actor, "pk", None) else None,
                "from_status": from_status or "",
                "to_status": to_status or "",
                "metadata": metadata or {},
            },
        )
        return event

    @staticmethod
    def validate_wizard(quotation):
        errors = {}
        if not (
            quotation.plan_configurations.filter(is_selected=True).exists()
            or quotation.products.filter(is_selected=True).exists()
        ):
            errors["plan_configuration"] = "At least one selected product or plan configuration is required."
        if not quotation.members.exists():
            errors["members"] = "At least one quotation member is required."
        elif not quotation.members.filter(member_type="LIFE_ASSURED").exists():
            errors["life_assured"] = "At least one life assured member is required."
        if not quotation.installment_configurations.filter(is_selected=True).exists():
            errors["installments"] = "At least one selected installment configuration is required."
        if quotation.fund_allocations.filter(is_selected=True).exists():
            total_allocated = quotation.fund_allocations.filter(is_selected=True).aggregate(
                total=models.Sum("allocation_percentage")
            )["total"] or Decimal("0")
            if total_allocated != Decimal("100"):
                errors["fund_allocations"] = "Selected fund allocation percentages must total exactly 100."
        if quotation.beneficiaries.exists():
            beneficiary_total = quotation.beneficiaries.aggregate(
                total=models.Sum("percentage")
            )["total"] or Decimal("0")
            if beneficiary_total != Decimal("100"):
                errors["beneficiaries"] = "Beneficiary percentages must total exactly 100."
        underwriting = getattr(quotation, "underwriting_detail", None)
        if underwriting is None:
            errors["underwriting"] = "Underwriting answers must be captured before finalization."
        payment = getattr(quotation, "payment_detail", None)
        if payment is None:
            errors["payment_detail"] = "Payment details must be captured before finalization."
        if errors:
            raise QuotationServiceError({"detail": "Quotation wizard is incomplete.", "errors": errors})
        return True

    @staticmethod
    def calculate_totals(quotation):
        sum_assured = sum(
            (item.base_sum_assured for item in quotation.plan_configurations.filter(is_selected=True)),
            Decimal("0"),
        )
        premium = sum(
            (item.premium_amount or Decimal("0") for item in quotation.plan_configurations.filter(is_selected=True)),
            Decimal("0"),
        )
        premium += sum(
            (item.premium_amount or Decimal("0") for item in quotation.rider_selections.filter(is_selected=True)),
            Decimal("0"),
        )
        premium += sum(
            (item.premium_amount or Decimal("0") for item in quotation.benefits.filter(is_selected=True)),
            Decimal("0"),
        )
        return sum_assured, premium

    @staticmethod
    @transaction.atomic
    def create_draft(*, actor, validated_data, request=None):
        payload = dict(validated_data)
        payload.pop("quote_number", None)
        payload["status"] = QuotationStatus.DRAFT
        payload["currency"] = (payload.get("currency") or QuotationService.default_currency()).upper()
        if payload.get("linked_partner") and not payload.get("partner"):
            payload["partner"] = payload["linked_partner"]
        payload["created_by"] = QuotationService.actor(actor)
        payload["updated_by"] = QuotationService.actor(actor)
        payload["quote_number"] = QuotationService.generate_quote_number()
        quotation = OLQuotation.objects.create(**payload)
        quotation.wizard_step_completion = QuotationService.wizard_completion(quotation)
        quotation.save(update_fields=["wizard_step_completion", "updated_at"])
        after = QuotationService.snapshot(quotation)
        QuotationService._record_version(quotation, actor=actor, reason="Initial quotation draft version.")
        QuotationService._record_event(
            quotation,
            "CREATED",
            actor=actor,
            to_status=QuotationStatus.DRAFT,
            notes="Ordinary Life quotation draft created.",
            after_state=after,
            request=request,
        )
        return quotation

    @staticmethod
    @transaction.atomic
    def update_personal_details(*, quotation, actor, validated_data, request=None):
        locked = OLQuotation.objects.select_for_update().get(pk=quotation.pk)
        if locked.status != QuotationStatus.DRAFT:
            raise QuotationServiceError("Only draft quotations can be updated.")

        payload = dict(validated_data)
        duplicate_warning = bool(payload.pop("_duplicate_active_quotation_warning", False))
        partner_exists = bool(payload.pop("_partner_exists", False))
        partner_id = payload.pop("_partner_id", None)
        partner_compliant = bool(payload.pop("_partner_compliant", False))

        if partner_compliant and partner_id:
            payload["linked_partner_id"] = partner_id
            payload["partner_verified"] = True

        allowed_fields = {
            "quote_name",
            "quote_date",
            "identity_type",
            "identity_number",
            "date_of_birth",
            "age_at_quote",
            "gender",
            "smoker_status",
            "location",
            "location_master",
            "agent_partner",
            "address",
            "linked_partner_id",
            "partner_verified",
        }
        payload = {field: value for field, value in payload.items() if field in allowed_fields}
        before = QuotationService.snapshot(locked)
        for field, value in payload.items():
            setattr(locked, field, value)
        locked.updated_by = QuotationService.actor(actor)
        locked.full_clean(exclude=["quote_number"])
        locked.wizard_step_completion = QuotationService.wizard_completion(locked)
        locked.current_version_number += 1
        locked.save(update_fields=[
            *payload.keys(),
            "updated_by",
            "wizard_step_completion",
            "current_version_number",
            "updated_at",
        ])
        QuotationService._sync_principal_member(quotation=locked, actor=actor, request=request)
        after = QuotationService.snapshot(locked)
        QuotationService._record_version(locked, actor=actor, reason="Personal Details wizard step updated.")
        QuotationService._record_event(
            locked,
            "PERSONAL_DETAILS_UPDATED",
            actor=actor,
            from_status=locked.status,
            to_status=locked.status,
            notes="Ordinary Life quotation Personal Details updated.",
            metadata={
                "duplicate_active_quotation_warning": duplicate_warning,
                "partner_exists": partner_exists,
                "partner_id": str(partner_id) if partner_id else None,
                "compliant": partner_compliant,
            },
            before_state=before,
            after_state=after,
            request=request,
        )
        return locked

    @staticmethod
    def _effective_queryset(queryset, as_of):
        return queryset.filter(is_active=True).filter(
            Q(effective_from__isnull=True) | Q(effective_from__lte=as_of)
        ).filter(
            Q(effective_to__isnull=True) | Q(effective_to__gte=as_of)
        )

    @staticmethod
    def _parameter_product_for_legacy_product(legacy_product):
        if not legacy_product:
            return None
        return ParameterProduct.objects.filter(
            code__iexact=legacy_product.code,
            is_active=True,
        ).first()

    @staticmethod
    def _plan_scope(legacy_product, plan, as_of):
        parameter_product = QuotationService._parameter_product_for_legacy_product(legacy_product)
        return parameter_product, as_of

    @staticmethod
    def _plan_feature_availability(*, legacy_product, plan, age=None, term=None, as_of=None):
        as_of = as_of or timezone.localdate()
        parameter_product = QuotationService._parameter_product_for_legacy_product(legacy_product)
        product_filter = Q(product=parameter_product) if parameter_product else Q(product__isnull=True)
        scoped_product_filter = product_filter | Q(product__isnull=True)

        joint_life_qs = QuotationService._effective_queryset(
            OLJointLifeSetup.objects.filter(
                Q(plan=plan) | (Q(plan__isnull=True) & scoped_product_filter)
            ),
            as_of,
        )
        mortgage_qs = QuotationService._effective_queryset(
            OLMortgageInterestFactor.objects.filter(
                Q(plan=plan) | (Q(plan__isnull=True) & scoped_product_filter)
            ),
            as_of,
        )
        rider_qs = QuotationService._effective_queryset(
            OLRiderSetup.objects.filter(
                Q(plan=plan) | (Q(plan__isnull=True) & scoped_product_filter)
            ),
            as_of,
        )
        if age is not None:
            rider_qs = rider_qs.filter(min_age__lte=age, max_age__gte=age)
        if term is not None:
            rider_qs = rider_qs.filter(min_term__lte=term, max_term__gte=term)

        return {
            "with_profit": bool(
                getattr(legacy_product, "allow_bonus", False)
                or QuotationService._effective_queryset(
                    OLBonusRate.objects.filter(
                        Q(plan=plan) | (Q(plan__isnull=True) & scoped_product_filter)
                    ),
                    as_of,
                ).exists()
            ),
            "joint_life": joint_life_qs.exists(),
            "mortgage": bool(getattr(legacy_product, "allow_loans", False) or mortgage_qs.exists()),
            "personal_accident": rider_qs.filter(
                Q(rider_category="ACCIDENT") | Q(benefit_type="ACCIDENTAL_DEATH")
            ).exists(),
            "premium_waiver": rider_qs.filter(
                Q(rider_category="WAIVER") | Q(benefit_type="WAIVER_PREMIUM")
            ).exists(),
        }

    @staticmethod
    def _bonus_default(*, legacy_product, plan, as_of):
        parameter_product = QuotationService._parameter_product_for_legacy_product(legacy_product)
        scope = Q(plan=plan)
        if parameter_product:
            scope |= Q(plan__isnull=True, product=parameter_product)
        rows = QuotationService._effective_queryset(OLBonusRate.objects.filter(scope), as_of)
        row = rows.order_by("-plan_id", "-effective_from", "code").first()
        return row.rate if row else Decimal("0")

    @staticmethod
    def _default_maturity_value(*, legacy_product, plan, parameter_product=None):
        if plan and plan.minimum_sum_assured:
            return plan.minimum_sum_assured
        if parameter_product and parameter_product.min_sum_assured:
            return parameter_product.min_sum_assured
        return None

    @staticmethod
    def _plan_card(*, product_version, plan, quotation=None, as_of=None):
        as_of = as_of or (quotation.quote_date if quotation else timezone.localdate())
        legacy_product = product_version.product
        parameter_product = (
            quotation.product if quotation and quotation.product_id
            else QuotationService._parameter_product_for_legacy_product(legacy_product)
        )
        flags = QuotationService._plan_feature_availability(
            legacy_product=legacy_product,
            plan=plan,
            age=quotation.age_at_quote if quotation else None,
            term=None,
            as_of=as_of,
        )
        badges = []
        if flags["with_profit"]:
            badges.append("WITH_PROFIT")
        if flags["joint_life"]:
            badges.append("JOINT_LIFE")
        return {
            "id": str(plan.pk),
            "plan_id": str(plan.pk),
            "product_version_id": str(product_version.pk),
            "product_code": legacy_product.code,
            "product_name": legacy_product.name,
            "product_version": product_version.version_number,
            "code": plan.code,
            "name": plan.name,
            "description": plan.description,
            "badges": badges,
            "plan_type_badges": badges,
            "with_profit": flags["with_profit"],
            "joint_life": flags["joint_life"],
            "mortgage": flags["mortgage"],
            "personal_accident": flags["personal_accident"],
            "premium_waiver": flags["premium_waiver"],
            "minimum_sum_assured": str(plan.minimum_sum_assured) if plan.minimum_sum_assured is not None else None,
            "maximum_sum_assured": str(plan.maximum_sum_assured) if plan.maximum_sum_assured is not None else None,
            "currency": product_version.currency,
            "payment_frequencies": list(product_version.payment_frequencies or []),
            "min_entry_age": product_version.min_entry_age,
            "max_entry_age": product_version.max_entry_age,
            "min_term_years": product_version.min_term_years,
            "max_term_years": product_version.max_term_years,
            "allow_bonus": bool(getattr(parameter_product, "allow_bonus", False) or flags["with_profit"]),
        }

    @staticmethod
    def search_plans(*, search="", product_version_id=None, product_code=None, quotation=None, limit=50):
        queryset = OLProductVersion.objects.select_related("product").prefetch_related("plans")
        queryset = queryset.filter(is_active=True, product__is_active=True)
        as_of = quotation.quote_date if quotation else timezone.localdate()
        queryset = queryset.filter(effective_from__lte=as_of).filter(
            Q(effective_to__isnull=True) | Q(effective_to__gte=as_of)
        )
        if product_version_id:
            queryset = queryset.filter(pk=product_version_id)
        if product_code:
            queryset = queryset.filter(product__code__iexact=product_code)
        if search:
            search_filter = (
                Q(product__code__icontains=search)
                | Q(product__name__icontains=search)
                | Q(product__description__icontains=search)
                | Q(plans__code__icontains=search)
                | Q(plans__name__icontains=search)
                | Q(plans__description__icontains=search)
            )
            queryset = queryset.filter(search_filter)
        cards = []
        for version in queryset.order_by("product__name", "-version_number").distinct():
            for plan in version.plans.filter(is_active=True).order_by("name", "code"):
                if search and not any(
                    search.lower() in str(value or "").lower()
                    for value in (version.product.code, version.product.name, plan.code, plan.name, plan.description)
                ):
                    continue
                cards.append(QuotationService._plan_card(
                    product_version=version,
                    plan=plan,
                    quotation=quotation,
                    as_of=as_of,
                ))
                if len(cards) >= limit:
                    return cards
        return cards

    @staticmethod
    def plan_options(*, quotation, plan_id=None):
        as_of = quotation.quote_date or timezone.localdate()
        product_version = quotation.product_version
        selected_plan = None
        if product_version and plan_id:
            selected_plan = product_version.plans.filter(pk=plan_id, is_active=True).first()
            if selected_plan is None:
                raise QuotationServiceError({"plan_id": "The selected plan does not belong to this quotation product version."})
        frequencies = list(product_version.payment_frequencies or []) if product_version else []
        if not frequencies and quotation.product_id:
            frequencies = list(getattr(quotation.product, "premium_frequencies", []) or [])
        legacy_product = product_version.product if product_version else None
        features = QuotationService._plan_feature_availability(
            legacy_product=legacy_product,
            plan=selected_plan,
            age=quotation.age_at_quote,
            term=None,
            as_of=as_of,
        ) if legacy_product else {
            "joint_life": False,
            "mortgage": False,
            "personal_accident": False,
            "premium_waiver": False,
        }
        quote_bases = ConfigurationService.get_choice_list("OL_QUOTE_BASIS_CHOICES")
        premium_factors = ConfigurationService.get_choice_list("OL_PREMIUM_FACTOR_CHOICES")
        return {
            "payment_frequencies": [{"value": value, "label": value.replace("_", " ").title()} for value in frequencies],
            "quote_bases": quote_bases,
            "premium_factors": premium_factors,
            "plan_features": features,
            "selected_plan_id": str(selected_plan.pk) if selected_plan else None,
            "as_of": as_of.isoformat(),
        }

    @staticmethod
    def _choice_values(code):
        return {str(item.get("value", "")).strip().upper() for item in ConfigurationService.get_choice_list(code)}

    @staticmethod
    def _validate_plan_selection(*, quotation, product_version, plan, payload, existing=None):
        as_of = quotation.quote_date or timezone.localdate()
        if not product_version.is_active or not product_version.product.is_active:
            raise QuotationServiceError({"product_version": "The selected product version is not active."})
        if product_version.effective_from > as_of or (
            product_version.effective_to and product_version.effective_to < as_of
        ):
            raise QuotationServiceError({"product_version": "The selected product version is not effective on the quote date."})
        if plan is not None and (not plan.is_active or plan.product_version_id != product_version.pk):
            raise QuotationServiceError({"plan": "The selected plan is not active or does not belong to the product version."})

        age = quotation.age_at_quote
        min_age = product_version.min_entry_age
        max_age = product_version.max_entry_age
        if quotation.product_id:
            min_age = max(min_age, quotation.product.min_entry_age)
            max_age = min(max_age, quotation.product.max_entry_age)
        if age is not None and not (min_age <= age <= max_age):
            raise QuotationServiceError({"age_at_quote": f"Age must be between {min_age} and {max_age} for the selected product."})

        term = payload.get("term_years")
        if term is None:
            term = product_version.min_term_years
            if quotation.product_id:
                term = max(term, quotation.product.min_term)
        term = int(term)
        min_term = product_version.min_term_years
        max_term = product_version.max_term_years
        if quotation.product_id:
            min_term = max(min_term, quotation.product.min_term)
            max_term = min(max_term, quotation.product.max_term)
        if not min_term <= term <= max_term:
            raise QuotationServiceError({"term_years": f"Policy term must be between {min_term} and {max_term} years."})

        payment_period = payload.get("payment_period_years")
        if payment_period is None:
            payment_period = term
        payment_period = int(payment_period)
        if payment_period <= 0 or payment_period > term:
            raise QuotationServiceError({"payment_period_years": "Payment period must be positive and cannot exceed policy term."})

        frequency = str(payload.get("premium_frequency") or "").strip().upper()
        allowed_frequencies = {str(item).strip().upper() for item in (product_version.payment_frequencies or [])}
        if not allowed_frequencies and quotation.product_id:
            allowed_frequencies = {str(item).strip().upper() for item in (quotation.product.premium_frequencies or [])}
        if not frequency and allowed_frequencies:
            frequency = sorted(allowed_frequencies)[0]
        if frequency not in allowed_frequencies:
            raise QuotationServiceError({"premium_frequency": "The selected payment frequency is not allowed for this product version."})

        quote_basis_values = QuotationService._choice_values("OL_QUOTE_BASIS_CHOICES")
        premium_factor_values = QuotationService._choice_values("OL_PREMIUM_FACTOR_CHOICES")
        quote_basis = str(payload.get("quote_basis") or (sorted(quote_basis_values)[0] if quote_basis_values else "")).strip().upper()
        premium_factor = str(payload.get("premium_factor") or (sorted(premium_factor_values)[0] if premium_factor_values else "")).strip().upper()
        if quote_basis not in quote_basis_values:
            raise QuotationServiceError({"quote_basis": "The selected quote basis is not configured."})
        if premium_factor not in premium_factor_values:
            raise QuotationServiceError({"premium_factor": "The selected premium factor is not configured."})

        parameter_product = quotation.product or QuotationService._parameter_product_for_legacy_product(product_version.product)
        features = QuotationService._plan_feature_availability(
            legacy_product=product_version.product,
            plan=plan,
            age=age,
            term=term,
            as_of=as_of,
        )
        for field in ("joint_life", "mortgage", "personal_accident", "premium_waiver"):
            if payload.get(field) and not features[field]:
                raise QuotationServiceError({field: f"{field.replace('_', ' ').title()} is not available for the selected plan."})

        estimated_maturity_value = payload.get("estimated_maturity_value")
        if estimated_maturity_value is None:
            estimated_maturity_value = QuotationService._default_maturity_value(
                legacy_product=product_version.product,
                plan=plan,
                parameter_product=parameter_product,
            )
        if estimated_maturity_value is None or Decimal(str(estimated_maturity_value)) <= 0:
            raise QuotationServiceError({"estimated_maturity_value": "Estimated maturity value must be greater than zero."})
        base_sum_assured = payload.get("base_sum_assured") or estimated_maturity_value
        if Decimal(str(base_sum_assured)) <= 0:
            raise QuotationServiceError({"base_sum_assured": "Base sum assured must be greater than zero."})
        if plan and plan.minimum_sum_assured and Decimal(str(base_sum_assured)) < plan.minimum_sum_assured:
            raise QuotationServiceError({"base_sum_assured": "Base sum assured is below the selected plan minimum."})
        if plan and plan.maximum_sum_assured and Decimal(str(base_sum_assured)) > plan.maximum_sum_assured:
            raise QuotationServiceError({"base_sum_assured": "Base sum assured exceeds the selected plan maximum."})

        bonus = payload.get("estimated_bonus_rate")
        if bonus is None:
            bonus = QuotationService._bonus_default(
                legacy_product=product_version.product,
                plan=plan,
                as_of=as_of,
            )
        if Decimal(str(bonus)) < 0:
            raise QuotationServiceError({"estimated_bonus_rate": "Estimated bonus rate cannot be negative."})

        return {
            "product_version": product_version,
            "plan": plan,
            "term_years": term,
            "payment_period_years": payment_period,
            "premium_frequency": frequency,
            "quote_basis": quote_basis,
            "estimated_maturity_value": Decimal(str(estimated_maturity_value)),
            "premium_factor": premium_factor,
            "joint_life": bool(payload.get("joint_life", False)),
            "mortgage": bool(payload.get("mortgage", False)),
            "personal_accident": bool(payload.get("personal_accident", False)),
            "premium_waiver": bool(payload.get("premium_waiver", False)),
            "estimated_bonus_rate": Decimal(str(bonus)),
            "base_sum_assured": Decimal(str(base_sum_assured)),
            "sub_product_code": str(payload.get("sub_product_code") or "").strip(),
            "is_selected": bool(payload.get("is_selected", True)),
            "coverage_rules": dict(payload.get("coverage_rules") or {}),
        }

    @staticmethod
    def _installment_payment_modes(*, quotation, plan_config=None):
        product_version = plan_config.product_version if plan_config else quotation.product_version
        modes = list(getattr(product_version, "payment_frequencies", []) or []) if product_version else []
        if not modes and quotation.product_id:
            modes = list(getattr(quotation.product, "premium_frequencies", []) or [])
        if not modes:
            modes = [item.get("value") for item in ConfigurationService.get_choice_list("OL_PAYMENT_MODE_CHOICES")]
        return list(dict.fromkeys(str(value).strip().upper() for value in modes if str(value or "").strip()))

    @staticmethod
    def _effective_parameter_rows(queryset, as_of):
        return queryset.filter(is_active=True, effective_from__lte=as_of).filter(
            Q(effective_to__isnull=True) | Q(effective_to__gte=as_of)
        )

    @staticmethod
    def _installment_plan_context(*, quotation, plan_config_id, lock=False):
        queryset = quotation.plan_configurations.select_related("product_version__product", "plan")
        if lock:
            queryset = queryset.select_for_update()
        try:
            return queryset.get(pk=plan_config_id, is_selected=True)
        except OLQuotationPlanConfiguration.DoesNotExist:
            raise QuotationServiceError({"plan_configuration_id": "Selected plan configuration was not found."})

    @staticmethod
    def _installment_scope_rows(*, model, product, plan, as_of, term, age=None, frequency=None, policy_year=None):
        queryset = QuotationService._effective_parameter_rows(model.objects, as_of).filter(product=product)
        if plan is not None:
            queryset = queryset.filter(Q(plan=plan) | Q(plan__isnull=True))
        else:
            queryset = queryset.filter(plan__isnull=True)
        if term is not None:
            queryset = queryset.filter(
                Q(term_from__isnull=True) | Q(term_from__lte=term),
                Q(term_to__isnull=True) | Q(term_to__gte=term),
            )
        if age is not None and hasattr(model, "age_from"):
            queryset = queryset.filter(
                Q(age_from__isnull=True) | Q(age_from__lte=age),
                Q(age_to__isnull=True) | Q(age_to__gte=age),
            )
        if frequency is not None and hasattr(model, "frequency"):
            queryset = queryset.filter(frequency=str(frequency).strip().upper())
        if policy_year is not None and hasattr(model, "policy_year_from"):
            queryset = queryset.filter(
                Q(policy_year_from__isnull=True) | Q(policy_year_from__lte=policy_year),
                Q(policy_year_to__isnull=True) | Q(policy_year_to__gte=policy_year),
            )
        if plan is not None:
            plan_priority = models.Case(
                models.When(plan=plan, then=models.Value(0)),
                models.When(plan__isnull=True, then=models.Value(1)),
                default=models.Value(2),
                output_field=models.IntegerField(),
            )
        else:
            plan_priority = models.Case(
                models.When(plan__isnull=True, then=models.Value(0)),
                default=models.Value(1),
                output_field=models.IntegerField(),
            )
        ordering = [plan_priority]
        if hasattr(model, "policy_year_from"):
            ordering.append("policy_year_from")
        if hasattr(model, "row_order"):
            ordering.append("row_order")
        ordering.append("code")
        return queryset.order_by(*ordering)

    @staticmethod
    def _paid_up_rate_default(*, product, plan, as_of, term, age, policy_year):
        rows = QuotationService._installment_scope_rows(
            model=OLPaidUpRate,
            product=product,
            plan=plan,
            as_of=as_of,
            term=term,
            age=age,
            policy_year=policy_year,
        )
        exact = rows.filter(plan=plan).first() if plan is not None else None
        fallback = rows.filter(plan__isnull=True).first()
        row = exact or fallback
        return row.rate_factor if row else None

    @staticmethod
    def _investment_fund_effective_queryset(as_of):
        return OLInvestmentFund.objects.select_related("fund_type").filter(
            is_active=True,
            fund_type__is_active=True,
            effective_from__lte=as_of,
        ).filter(
            Q(effective_to__isnull=True) | Q(effective_to__gte=as_of)
        )

    @staticmethod
    def _fund_currency_compatible(*, fund, quotation_currency):
        quotation_currency = str(quotation_currency or "").strip().upper()
        fund_currency = str(fund.currency or "").strip().upper()
        if fund_currency == quotation_currency:
            return True, False
        rules = dict(fund.allocation_rules or {})
        allowed = rules.get("allowed_quotation_currencies") or rules.get("supported_quotation_currencies") or []
        allowed = {str(value).strip().upper() for value in allowed if value}
        conversion_allowed = bool(rules.get("allow_currency_conversion"))
        return quotation_currency in allowed or conversion_allowed, conversion_allowed

    @staticmethod
    def _investment_fund_snapshot(allocation):
        fund = allocation.fund
        return {
            "id": str(allocation.pk),
            "plan_configuration_id": str(allocation.plan_configuration_id) if allocation.plan_configuration_id else None,
            "fund_id": str(fund.pk),
            "fund_code": fund.code,
            "fund_name": fund.name,
            "fund_type_id": str(fund.fund_type_id),
            "fund_type_code": fund.fund_type.code,
            "fund_type_name": fund.fund_type.name,
            "risk_profile": fund.fund_type.risk_profile,
            "currency": fund.currency,
            "valuation_frequency": fund.valuation_frequency,
            "allocation_percent": str(allocation.allocation_percentage),
            "allocated_amount": str(allocation.allocation_amount) if allocation.allocation_amount is not None else None,
            "is_selected": allocation.is_selected,
        }

    @staticmethod
    def investment_fund_options(*, quotation, plan_config_id=None):
        as_of = quotation.quote_date or timezone.localdate()
        if plan_config_id:
            try:
                plan_config = quotation.plan_configurations.select_related("product_version__product", "plan").get(
                    pk=plan_config_id,
                    is_selected=True,
                )
            except OLQuotationPlanConfiguration.DoesNotExist:
                raise QuotationServiceError({"plan_configuration_id": "Selected plan configuration was not found."})
            if not QuotationService._plan_requires_investment_funds(plan_config, quotation):
                return {
                    "plan_configuration_id": str(plan_config.pk),
                    "not_applicable": True,
                    "quotation_currency": quotation.currency,
                    "funds": [],
                }
        funds = QuotationService._investment_fund_effective_queryset(as_of).order_by("name", "code")
        result = []
        for fund in funds:
            compatible, conversion_allowed = QuotationService._fund_currency_compatible(
                fund=fund,
                quotation_currency=quotation.currency,
            )
            result.append({
                "id": str(fund.pk),
                "code": fund.code,
                "name": fund.name,
                "description": fund.description,
                "fund_type_id": str(fund.fund_type_id),
                "fund_type_code": fund.fund_type.code,
                "fund_type_name": fund.fund_type.name,
                "risk_profile": fund.fund_type.risk_profile,
                "currency": fund.currency,
                "valuation_frequency": fund.valuation_frequency,
                "unit_price": fund.unit_price,
                "currency_compatible": compatible,
                "currency_conversion_allowed": conversion_allowed,
                "selectable": compatible,
            })
        return {
            "plan_configuration_id": str(plan_config_id) if plan_config_id else None,
            "not_applicable": False,
            "quotation_currency": quotation.currency,
            "funds": result,
        }

    @staticmethod
    def investment_fund_state(*, quotation):
        selected = quotation.plan_configurations.filter(is_selected=True).select_related(
            "product_version__product", "plan"
        ).prefetch_related("fund_allocations__fund__fund_type").order_by("section_number", "created_at")
        plan_rows = []
        applicable_rows = []
        for plan_config in selected:
            applicable = QuotationService._plan_requires_investment_funds(plan_config, quotation)
            allocations = list(plan_config.fund_allocations.filter(is_selected=True).order_by("fund__code"))
            total = sum((allocation.allocation_percentage for allocation in allocations), Decimal("0"))
            status = "NOT_APPLICABLE" if not applicable else ("CONFIGURED" if total == Decimal("100") and allocations else "READY_TO_CONFIGURE")
            row = {
                "plan_configuration_id": str(plan_config.pk),
                "plan_code": plan_config.plan.code if plan_config.plan else plan_config.sub_product_code or "",
                "plan_name": plan_config.plan.name if plan_config.plan else plan_config.sub_product_code or "",
                "investment_linked": applicable,
                "status": status,
                "allocation_total": str(total),
                "allocations": [QuotationService._investment_fund_snapshot(allocation) for allocation in allocations],
                "can_configure": applicable,
            }
            plan_rows.append(row)
            if applicable:
                applicable_rows.append(row)
        return {
            "plan_rows": plan_rows,
            "requires_allocation": any(row["status"] == "READY_TO_CONFIGURE" for row in applicable_rows),
            "not_applicable": not applicable_rows,
            "wizard_complete": bool((quotation.wizard_step_completion or {}).get("5_investment_funds")) if applicable_rows else True,
        }

    @staticmethod
    @transaction.atomic
    def configure_investment_funds(*, quotation, actor, validated_data, request=None):
        locked = OLQuotation.objects.select_for_update().get(pk=quotation.pk)
        if locked.status != QuotationStatus.DRAFT:
            raise QuotationServiceError({"status": "Only draft quotations can configure investment funds."})
        selected = list(locked.plan_configurations.filter(is_selected=True).select_related("product_version__product", "plan").select_for_update())
        applicable = [config for config in selected if QuotationService._plan_requires_investment_funds(config, locked)]
        before_state = [
            QuotationService._investment_fund_snapshot(allocation)
            for allocation in locked.fund_allocations.filter(is_selected=True).select_related("fund__fund_type")
        ]
        if not applicable:
            locked.wizard_step_completion = QuotationService.wizard_completion(locked)
            locked.save(update_fields=["wizard_step_completion", "updated_at"])
            return {"not_applicable": True, "state": QuotationService.investment_fund_state(quotation=locked)}

        rows = validated_data["allocations"]
        config_by_id = {str(config.pk): config for config in applicable}
        grouped = {}
        seen = set()
        for row in rows:
            config_id = str(row["plan_config_id"])
            if config_id not in config_by_id:
                raise QuotationServiceError({"allocations": "Every allocation must reference an applicable selected plan configuration."})
            fund_id = str(row["fund_id"])
            key = (config_id, fund_id)
            if key in seen:
                raise QuotationServiceError({"allocations": "A fund may only appear once per plan configuration."})
            seen.add(key)
            percentage = row["allocation_percent"]
            if percentage < Decimal("0") or percentage > Decimal("100"):
                raise QuotationServiceError({"allocation_percent": "Allocation percentage must be between 0 and 100."})
            grouped.setdefault(config_id, []).append(row)
        missing = [str(config.pk) for config in applicable if str(config.pk) not in grouped]
        if missing:
            raise QuotationServiceError({"allocations": "Every investment-linked selected plan must have fund allocations."})
        for config_id, config_rows in grouped.items():
            total = sum((row["allocation_percent"] for row in config_rows), Decimal("0"))
            if total != Decimal("100"):
                raise QuotationServiceError({"allocations": f"Allocations for plan configuration {config_id} must sum exactly to 100."})

        effective_funds = QuotationService._investment_fund_effective_queryset(locked.quote_date or timezone.localdate())
        created = []
        for row in rows:
            try:
                fund = effective_funds.get(pk=row["fund_id"])
            except OLInvestmentFund.DoesNotExist:
                raise QuotationServiceError({"fund_id": "The selected investment fund is inactive, expired, not yet effective, or has an inactive fund type."})
            compatible, _ = QuotationService._fund_currency_compatible(fund=fund, quotation_currency=locked.currency)
            if not compatible:
                raise QuotationServiceError({"fund_id": f"Fund {fund.code} is not compatible with quotation currency {locked.currency}."})
            created.append((config_by_id[str(row["plan_config_id"])], fund, row))

        locked.fund_allocations.all().delete()
        for config, fund, row in created:
            OLQuotationFundAllocation.objects.create(
                quotation=locked,
                plan_configuration=config,
                fund=fund,
                allocation_percentage=row["allocation_percent"],
                allocation_amount=row.get("allocated_amount"),
                is_selected=True,
                created_by=QuotationService.actor(actor),
                updated_by=QuotationService.actor(actor),
            )
        locked.wizard_step_completion = QuotationService.wizard_completion(locked)
        locked.current_version_number = int(locked.current_version_number or 1) + 1
        locked.save(update_fields=["wizard_step_completion", "current_version_number", "updated_at"])
        locked.refresh_from_db()
        after_state = [
            QuotationService._investment_fund_snapshot(allocation)
            for allocation in locked.fund_allocations.filter(is_selected=True).select_related("fund__fund_type")
        ]
        QuotationService._record_event(
            locked,
            "INVESTMENT_FUND_ALLOCATIONS_UPDATED",
            actor=actor,
            notes="Investment fund allocations saved.",
            metadata={"allocation_count": len(after_state)},
            before_state={"allocations": before_state},
            after_state={"allocations": after_state},
            request=request,
        )
        return {"not_applicable": False, "state": QuotationService.investment_fund_state(quotation=locked)}

    @staticmethod
    def installment_state(*, quotation):
        rows = []
        selected = quotation.plan_configurations.filter(is_selected=True).select_related("product_version__product", "plan").order_by("section_number", "created_at")
        for plan_config in selected:
            configuration = quotation.installment_configurations.filter(plan_configuration=plan_config, is_selected=True).prefetch_related("rate_rows").first()
            policy_term = plan_config.term_years
            plan = plan_config.plan
            rows.append({
                "plan_configuration_id": str(plan_config.pk),
                "plan_code": plan.code if plan else plan_config.sub_product_code or "",
                "plan_name": plan.name if plan else plan_config.sub_product_code or "",
                "policy_term_years": policy_term,
                "payment_mode": configuration.frequency if configuration else plan_config.premium_frequency,
                "total_number_of_installments": configuration.number_of_installments if configuration else 0,
                "status": "CONFIGURED" if configuration and configuration.rate_rows.exists() else "READY_TO_CONFIGURE",
                "can_configure": True,
            })
        return {
            "rows": rows,
            "requires_configuration": any(row["status"] == "READY_TO_CONFIGURE" for row in rows),
            "wizard_complete": bool(quotation.wizard_step_completion.get("4_installments")),
        }

    @staticmethod
    def installment_template(*, quotation, plan_config_id):
        plan_config = QuotationService._installment_plan_context(quotation=quotation, plan_config_id=plan_config_id)
        as_of = quotation.quote_date or timezone.localdate()
        product = plan_config.product_version.product
        plan = plan_config.plan
        modes = QuotationService._installment_payment_modes(quotation=quotation, plan_config=plan_config)
        payment_mode = plan_config.premium_frequency if plan_config.premium_frequency in modes else (modes[0] if modes else "")
        rows = QuotationService._installment_scope_rows(
            model=OLAnticipatedEndowmentInstallmentRate,
            product=product,
            plan=plan,
            as_of=as_of,
            term=plan_config.term_years,
            age=quotation.age_at_quote,
            frequency=payment_mode,
        )
        exact_rows = rows.filter(plan=plan) if plan is not None else rows.none()
        template_rows = list(exact_rows) or list(rows.filter(plan__isnull=True))
        result_rows = []
        for index, source in enumerate(template_rows, start=1):
            sequence = int(getattr(source, "policy_year", None) or getattr(source, "policy_year_from", None) or index)
            paid_up = QuotationService._paid_up_rate_default(
                product=product,
                plan=plan,
                as_of=as_of,
                term=plan_config.term_years,
                age=quotation.age_at_quote,
                policy_year=sequence,
            )
            result_rows.append({
                "sequence": sequence,
                "description": f"Installment {sequence}",
                "rate_percent": source.rate_factor,
                "paid_up_rate": paid_up,
            })
        return {
            "plan_configuration_id": str(plan_config.pk),
            "has_template": bool(result_rows),
            "banner": "" if result_rows else "No templates available. You can still configure installments manually...",
            "policy_term_years": plan_config.term_years,
            "payment_mode": payment_mode,
            "available_payment_modes": modes,
            "rate_rows": result_rows,
        }

    @staticmethod
    def _installment_snapshot(configuration):
        if not configuration:
            return None
        return {
            "id": str(configuration.pk),
            "plan_configuration_id": str(configuration.plan_configuration_id) if configuration.plan_configuration_id else None,
            "frequency": configuration.frequency,
            "annuity_period_years": configuration.annuity_period_years,
            "number_of_installments": configuration.number_of_installments,
            "after_maturity_benefits": configuration.after_maturity_benefits,
            "before_maturity_benefits": configuration.before_maturity_benefits,
            "rate_rows": [
                {
                    "sequence": row.sequence,
                    "description": row.description,
                    "rate_percent": str(row.rate_percent),
                    "paid_up_rate": str(row.paid_up_rate) if row.paid_up_rate is not None else None,
                }
                for row in configuration.rate_rows.all().order_by("sequence")
            ],
        }

    @staticmethod
    @transaction.atomic
    def configure_installments(*, quotation, plan_config_id, actor, validated_data, request=None):
        locked = OLQuotation.objects.select_for_update().get(pk=quotation.pk)
        if locked.status != QuotationStatus.DRAFT:
            raise QuotationServiceError({"status": "Only draft quotations can configure installments."})
        plan_config = QuotationService._installment_plan_context(
            quotation=locked,
            plan_config_id=plan_config_id,
            lock=True,
        )
        term = plan_config.term_years
        annuity_period = int(validated_data["annuity_period_years"])
        if annuity_period > term:
            raise QuotationServiceError({"annuity_period_years": "Annuity period cannot exceed the inherited policy term."})
        payment_mode = str(validated_data["payment_mode"]).strip().upper()
        if payment_mode not in QuotationService._installment_payment_modes(quotation=locked, plan_config=plan_config):
            raise QuotationServiceError({"payment_mode": "The selected payment mode is not configured for this product."})
        rate_rows = validated_data["rate_rows"]
        total_rate = sum((row["rate_percent"] for row in rate_rows), Decimal("0"))
        if total_rate != Decimal("100"):
            raise QuotationServiceError({"rate_rows": "Installment rates must sum exactly to 100."})
        rules = dict(plan_config.coverage_rules or {})
        product_rules = dict(getattr(plan_config.product_version, "servicing_rules", {}) or {})
        requires_benefit_toggle = bool(
            rules.get("requires_installment_benefits")
            or rules.get("installment_benefits_required")
            or product_rules.get("requires_installment_benefits")
            or product_rules.get("installment_benefits_required")
        )
        if requires_benefit_toggle and not (validated_data.get("after_maturity_benefits") or validated_data.get("before_maturity_benefits")):
            raise QuotationServiceError({"benefits": "At least one installment benefit toggle must be selected for this plan."})
        existing = locked.installment_configurations.filter(plan_configuration=plan_config, is_selected=True).prefetch_related("rate_rows").first()
        before_state = QuotationService._installment_snapshot(existing)
        amount = existing.installment_amount if existing else plan_config.estimated_maturity_value
        if amount is None or Decimal(str(amount)) <= 0:
            raise QuotationServiceError({"installment_amount": "The selected plan must have a positive estimated maturity value before installments can be configured."})
        configuration = existing or OLQuotationInstallmentConfiguration(
            quotation=locked,
            plan_configuration=plan_config,
            installment_amount=Decimal(str(amount)),
            currency=locked.currency or QuotationService.default_currency(),
            is_selected=True,
        )
        configuration.frequency = payment_mode
        configuration.annuity_period_years = annuity_period
        configuration.number_of_installments = len(rate_rows)
        configuration.after_maturity_benefits = bool(validated_data.get("after_maturity_benefits", False))
        configuration.before_maturity_benefits = bool(validated_data.get("before_maturity_benefits", False))
        configuration.is_selected = True
        configuration.save()
        OLQuotationInstallmentRateRow.objects.filter(installment_configuration=configuration).delete()
        for row in rate_rows:
            paid_up = row.get("paid_up_rate")
            if paid_up is None:
                paid_up = QuotationService._paid_up_rate_default(
                    product=plan_config.product_version.product,
                    plan=plan_config.plan,
                    as_of=locked.quote_date or timezone.localdate(),
                    term=term,
                    age=locked.age_at_quote,
                    policy_year=row["sequence"],
                )
            description = str(row["description"]).strip()
            OLQuotationInstallmentRateRow.objects.create(
                installment_configuration=configuration,
                sequence=row["sequence"],
                description=description,
                rate_percent=row["rate_percent"],
                paid_up_rate=paid_up,
                period_from=row["sequence"],
                period_to=row["sequence"],
                rate=row["rate_percent"],
                charge=Decimal("0"),
                notes=description,
                created_by=QuotationService.actor(actor),
                updated_by=QuotationService.actor(actor),
            )
        locked.wizard_step_completion = QuotationService.wizard_completion(locked)
        locked.current_version_number = int(locked.current_version_number or 1) + 1
        locked.save(update_fields=["wizard_step_completion", "current_version_number", "updated_at"])
        configuration.refresh_from_db()
        after_state = QuotationService._installment_snapshot(configuration)
        QuotationService._record_event(
            locked,
            "INSTALLMENT_CONFIGURATION_UPDATED",
            actor=actor,
            notes="Installment configuration saved.",
            metadata={
                "plan_configuration_id": str(plan_config.pk),
                "total_number_of_installments": configuration.number_of_installments,
                "annuity_period_years": configuration.annuity_period_years,
            },
            before_state=before_state,
            after_state=after_state,
            request=request,
        )
        return configuration

    @staticmethod
    def _plan_config_snapshot(quotation):
        return [
            {
                "id": str(row.pk),
                "section_number": row.section_number,
                "product_version_id": str(row.product_version_id),
                "plan_id": str(row.plan_id) if row.plan_id else None,
                "sub_product_code": row.sub_product_code,
                "is_selected": row.is_selected,
                "base_sum_assured": str(row.base_sum_assured),
                "term_years": row.term_years,
                "payment_period_years": row.payment_period_years,
                "premium_frequency": row.premium_frequency,
                "quote_basis": row.quote_basis,
                "estimated_maturity_value": str(row.estimated_maturity_value) if row.estimated_maturity_value is not None else None,
                "premium_factor": row.premium_factor,
                "joint_life": row.joint_life,
                "mortgage": row.mortgage,
                "personal_accident": row.personal_accident,
                "premium_waiver": row.premium_waiver,
                "estimated_bonus_rate": str(row.estimated_bonus_rate),
            }
            for row in quotation.plan_configurations.order_by("section_number", "created_at")
        ]

    @staticmethod
    @transaction.atomic
    def select_plans(*, quotation, actor, selections, request=None):
        locked = OLQuotation.objects.select_for_update().get(pk=quotation.pk)
        if locked.status != QuotationStatus.DRAFT:
            raise QuotationServiceError("Only draft quotations can be updated.")
        if not selections:
            raise QuotationServiceError({"plans": "At least one plan must be selected."})

        normalized = []
        seen = set()
        for item in selections:
            item = dict(item or {})
            product_version_id = item.get("product_version_id") or locked.product_version_id
            plan_id = item.get("plan_id")
            key = (str(product_version_id), str(plan_id or ""), str(item.get("sub_product_code") or "").strip().upper())
            if key in seen:
                raise QuotationServiceError({"plans": "The same plan cannot be selected more than once."})
            seen.add(key)
            try:
                product_version = OLProductVersion.objects.select_related("product").get(pk=product_version_id)
            except (OLProductVersion.DoesNotExist, ValueError, TypeError):
                raise QuotationServiceError({"product_version_id": "Selected product version does not exist."})
            plan = None
            if plan_id:
                try:
                    plan = OLPlan.objects.get(pk=plan_id)
                except (OLPlan.DoesNotExist, ValueError, TypeError):
                    raise QuotationServiceError({"plan_id": "Selected plan does not exist."})
            validated = QuotationService._validate_plan_selection(
                quotation=locked,
                product_version=product_version,
                plan=plan,
                payload=item,
            )
            normalized.append(validated)

        before = QuotationService.snapshot(locked)
        before_configs = QuotationService._plan_config_snapshot(locked)
        incoming_keys = {
            (str(row["product_version"].pk), str(row["plan"].pk) if row["plan"] else "", row["sub_product_code"].upper())
            for row in normalized
        }
        existing_rows = list(locked.plan_configurations.select_for_update().all())
        for row in existing_rows:
            row.is_selected = False
            row.section_number = None
            row.updated_by = QuotationService.actor(actor)
            row.save(update_fields=["is_selected", "section_number", "updated_by", "updated_at"])

        configurations = []
        for section_number, row in enumerate(normalized, start=1):
            key = (str(row["product_version"].pk), str(row["plan"].pk) if row["plan"] else "", row["sub_product_code"].upper())
            existing = next(
                (
                    candidate for candidate in existing_rows
                    if (
                        str(candidate.product_version_id),
                        str(candidate.plan_id) if candidate.plan_id else "",
                        (candidate.sub_product_code or "").upper(),
                    ) == key
                ),
                None,
            )
            values = {key: value for key, value in row.items() if key not in {"product_version", "plan"}}
            values.update({"product_version": row["product_version"], "plan": row["plan"], "section_number": section_number, "is_selected": True})
            if existing:
                for field, value in values.items():
                    setattr(existing, field, value)
                existing.updated_by = QuotationService.actor(actor)
                existing.full_clean()
                existing.save()
                config = existing
            else:
                config = OLQuotationPlanConfiguration.objects.create(
                    quotation=locked,
                    created_by=QuotationService.actor(actor),
                    updated_by=QuotationService.actor(actor),
                    **values,
                )
            configurations.append(config)

        update_fields = ["wizard_step_completion", "current_version_number", "updated_by", "updated_at"]
        if not locked.product_version_id:
            locked.product_version = normalized[0]["product_version"]
            update_fields.append("product_version")
        locked.updated_by = QuotationService.actor(actor)
        locked.wizard_step_completion = QuotationService.wizard_completion(locked)
        locked.current_version_number += 1
        locked.save(update_fields=update_fields)
        after = QuotationService.snapshot(locked)
        after_configs = QuotationService._plan_config_snapshot(locked)
        QuotationService._record_version(locked, actor=actor, reason="Plan Selection wizard step updated.")
        QuotationService._record_event(
            locked,
            "PLAN_SELECTION_UPDATED",
            actor=actor,
            from_status=locked.status,
            to_status=locked.status,
            notes="Ordinary Life quotation plan selection updated.",
            metadata={"before_plan_configurations": before_configs, "after_plan_configurations": after_configs},
            before_state=before,
            after_state=after,
            request=request,
        )
        return locked, configurations

    @staticmethod
    @transaction.atomic
    def update_plan_configuration(*, quotation, configuration_id, actor, payload, request=None):
        locked = OLQuotation.objects.select_for_update().get(pk=quotation.pk)
        if locked.status != QuotationStatus.DRAFT:
            raise QuotationServiceError("Only draft quotations can be updated.")
        try:
            configuration = locked.plan_configurations.select_for_update().select_related("product_version__product", "plan").get(pk=configuration_id)
        except (OLQuotationPlanConfiguration.DoesNotExist, ValueError, TypeError):
            raise QuotationServiceError({"configuration_id": "Plan configuration does not exist for this quotation."})
        values = {
            "term_years": configuration.term_years,
            "payment_period_years": configuration.payment_period_years,
            "premium_frequency": configuration.premium_frequency,
            "quote_basis": configuration.quote_basis,
            "estimated_maturity_value": configuration.estimated_maturity_value,
            "premium_factor": configuration.premium_factor,
            "joint_life": configuration.joint_life,
            "mortgage": configuration.mortgage,
            "personal_accident": configuration.personal_accident,
            "premium_waiver": configuration.premium_waiver,
            "estimated_bonus_rate": configuration.estimated_bonus_rate,
            "base_sum_assured": configuration.base_sum_assured,
            "sub_product_code": configuration.sub_product_code,
            "is_selected": configuration.is_selected,
            "coverage_rules": configuration.coverage_rules,
        }
        values.update({key: value for key, value in payload.items() if key in values})
        validated = QuotationService._validate_plan_selection(
            quotation=locked,
            product_version=configuration.product_version,
            plan=configuration.plan,
            payload=values,
            existing=configuration,
        )
        before = QuotationService.snapshot(locked)
        before_configs = QuotationService._plan_config_snapshot(locked)
        for field, value in validated.items():
            if field in {"product_version", "plan"}:
                continue
            setattr(configuration, field, value)
        configuration.updated_by = QuotationService.actor(actor)
        configuration.full_clean()
        configuration.save()
        locked.updated_by = QuotationService.actor(actor)
        locked.wizard_step_completion = QuotationService.wizard_completion(locked)
        locked.current_version_number += 1
        locked.save(update_fields=["wizard_step_completion", "current_version_number", "updated_by", "updated_at"])
        after = QuotationService.snapshot(locked)
        after_configs = QuotationService._plan_config_snapshot(locked)
        QuotationService._record_version(locked, actor=actor, reason="Plan configuration wizard section updated.")
        QuotationService._record_event(
            locked,
            "PLAN_CONFIGURATION_UPDATED",
            actor=actor,
            from_status=locked.status,
            to_status=locked.status,
            notes="Ordinary Life quotation plan configuration updated.",
            metadata={"configuration_id": str(configuration.pk), "before_plan_configurations": before_configs, "after_plan_configurations": after_configs},
            before_state=before,
            after_state=after,
            request=request,
        )
        return locked, configuration

    @staticmethod
    def _split_member_name(full_name):
        parts = [part for part in str(full_name or "").strip().split() if part]
        if not parts:
            raise QuotationServiceError({"full_name": "Full name is required."})
        if len(parts) == 1:
            return parts[0], ""
        return parts[0], " ".join(parts[1:])

    @staticmethod
    def _member_cover_rows(*, quotation):
        """Return the highest-priority effective cover row for each configured relation."""
        as_of = quotation.quote_date or timezone.localdate()
        selected = list(
            quotation.plan_configurations.filter(is_selected=True)
            .select_related("product_version__product", "plan")
            .order_by("section_number", "created_at")
        )
        rows_by_relation = {}
        for selected_config in selected:
            product = selected_config.product_version.product
            plan = selected_config.plan
            scope = Q(product=product, plan=plan)
            scope |= Q(product=product, plan__isnull=True)
            scope |= Q(product__isnull=True, plan__isnull=True)
            rows = QuotationService._effective_queryset(
                OLMemberCoverConfiguration.objects.filter(scope),
                as_of,
            ).order_by(
                models.Case(
                    models.When(plan=plan, then=0),
                    models.When(product=product, plan__isnull=True, then=1),
                    default=2,
                    output_field=models.IntegerField(),
                ),
                "member_relation",
                "min_age",
                "code",
            )
            for row in rows:
                relation = (row.member_relation or "").strip().upper()
                if relation and relation not in rows_by_relation:
                    rows_by_relation[relation] = row
        return rows_by_relation

    @staticmethod
    def _member_requirements(*, quotation):
        rows_by_relation = QuotationService._member_cover_rows(quotation=quotation)
        principal_relations = {"POLICYHOLDER", "PRINCIPAL", "LIFE_ASSURED", "SELF"}
        additional = {
            relation: row
            for relation, row in rows_by_relation.items()
            if relation not in principal_relations
        }
        return {
            "rows_by_relation": rows_by_relation,
            "additional_by_relation": additional,
            "requires_additional_coverage": bool(additional),
        }

    @staticmethod
    def _member_state(member, *, is_principal=False, configuration=None):
        return {
            "id": str(member.pk) if member and member.pk else None,
            "member_type": member.member_type if member else "LIFE_ASSURED",
            "full_name": (
                " ".join(part for part in [member.first_name, member.last_name] if part).strip()
                if member else ""
            ),
            "first_name": member.first_name if member else "",
            "last_name": member.last_name if member else "",
            "relation": member.relationship if member else "POLICYHOLDER",
            "date_of_birth": member.date_of_birth.isoformat() if member and member.date_of_birth else None,
            "age_at_quote": member.age_at_quote if member else None,
            "gender": member.gender if member else "",
            "sum_assured": str(member.member_sum_assured) if member and member.member_sum_assured is not None else None,
            "coverage_basis": (
                member.coverage_basis
                if member and member.coverage_basis
                else (configuration.coverage_basis if configuration else "")
            ),
            "waiting_period_days": (
                member.waiting_period_days
                if member
                else (configuration.waiting_period_days if configuration else 0)
            ),
            "is_principal": bool(is_principal),
        }

    @staticmethod
    def _sync_principal_member(*, quotation, actor=None, request=None):
        if not quotation.quote_name or not quotation.date_of_birth:
            return None
        first_name, last_name = QuotationService._split_member_name(quotation.quote_name)
        principal = quotation.members.filter(
            metadata__is_principal=True,
        ).order_by("created_at").first()
        if principal is None:
            principal = quotation.members.filter(
                member_type="LIFE_ASSURED",
                relationship__in=["POLICYHOLDER", "PRINCIPAL", "SELF"],
            ).order_by("created_at").first()
        values = {
            "member_type": "LIFE_ASSURED",
            "first_name": first_name,
            "last_name": last_name,
            "identity_number": quotation.identity_number or "",
            "date_of_birth": quotation.date_of_birth,
            "age_at_quote": quotation.age_at_quote,
            "gender": (quotation.gender or "").strip().upper(),
            "smoker_status": (quotation.smoker_status or "").strip().upper(),
            "relationship": "POLICYHOLDER",
            "partner": quotation.linked_partner or quotation.partner,
            "coverage_basis": "PRINCIPAL",
            "waiting_period_days": 0,
            "metadata": {"is_principal": True, "source": "personal_details"},
        }
        if principal is None:
            principal = OLQuotationMember(
                quotation=quotation,
                created_by=QuotationService.actor(actor),
                updated_by=QuotationService.actor(actor),
                **values,
            )
            principal.full_clean()
            principal.save()
            AuditService.log_create(
                principal,
                actor=actor,
                request=request,
                reason="Principal quotation member automatically configured from Personal Details.",
            )
            return principal

        before = AuditService.snapshot(principal)
        changed = False
        for field, value in values.items():
            if getattr(principal, field) != value:
                setattr(principal, field, value)
                changed = True
        if changed:
            principal.updated_by = QuotationService.actor(actor)
            principal.full_clean()
            principal.save()
            AuditService.log_update(
                principal,
                before_state=before,
                actor=actor,
                request=request,
                reason="Principal quotation member synchronized from Personal Details.",
            )
        return principal

    @staticmethod
    def _validate_additional_member(*, quotation, payload, existing=None):
        requirements = QuotationService._member_requirements(quotation=quotation)
        if not requirements["requires_additional_coverage"]:
            raise QuotationServiceError({
                "members": "Selected plans do not require additional member coverage configuration."
            })
        relation = str(payload.get("relation") or (existing.relationship if existing else "")).strip().upper()
        if relation not in requirements["additional_by_relation"]:
            allowed = sorted(requirements["additional_by_relation"])
            raise QuotationServiceError({"relation": f"Relation is not allowed by the selected plans. Allowed relations: {', '.join(allowed)}."})
        configuration = requirements["additional_by_relation"][relation]
        date_of_birth = payload.get("date_of_birth") or (existing.date_of_birth if existing else None)
        if not date_of_birth:
            raise QuotationServiceError({"date_of_birth": "Date of birth is required."})
        quote_date = quotation.quote_date or timezone.localdate()
        if date_of_birth > quote_date:
            raise QuotationServiceError({"date_of_birth": "Date of birth cannot be after the quote date."})
        age = quote_date.year - date_of_birth.year - ((quote_date.month, quote_date.day) < (date_of_birth.month, date_of_birth.day))
        if configuration.min_age is not None and age < configuration.min_age:
            raise QuotationServiceError({"date_of_birth": f"Member age must be at least {configuration.min_age} years."})
        if configuration.max_age is not None and age > configuration.max_age:
            raise QuotationServiceError({"date_of_birth": f"Member age cannot exceed {configuration.max_age} years."})

        full_name = str(payload.get("full_name") or "").strip()
        if not full_name and existing:
            full_name = " ".join(part for part in [existing.first_name, existing.last_name] if part).strip()
        first_name, last_name = QuotationService._split_member_name(full_name)
        gender = str(payload.get("gender") or (existing.gender if existing else "")).strip().upper()
        if not gender:
            raise QuotationServiceError({"gender": "Gender is required."})
        sum_assured = payload.get("sum_assured", existing.member_sum_assured if existing else None)
        if sum_assured is not None:
            sum_assured = Decimal(str(sum_assured))
        configured_basis = (configuration.coverage_basis or "").strip().upper()
        if configured_basis in {"SUM_ASSURED", "SUM_ASSURED_BAND"} and sum_assured is None:
            raise QuotationServiceError({"sum_assured": "Sum assured is required for this coverage basis."})
        if configuration.benefit_limit is not None and sum_assured is not None and sum_assured > configuration.benefit_limit:
            raise QuotationServiceError({"sum_assured": f"Sum assured cannot exceed the configured benefit limit of {configuration.benefit_limit}."})

        duplicate_query = quotation.members.filter(
            member_type="DEPENDENT",
            first_name__iexact=first_name,
            last_name__iexact=last_name,
            relationship=relation,
            date_of_birth=date_of_birth,
        )
        if existing:
            duplicate_query = duplicate_query.exclude(pk=existing.pk)
        if duplicate_query.exists():
            raise QuotationServiceError({"member": "An additional member with the same name, relation, and date of birth already exists."})
        return {
            "first_name": first_name,
            "last_name": last_name,
            "date_of_birth": date_of_birth,
            "age_at_quote": age,
            "gender": gender,
            "relationship": relation,
            "member_sum_assured": sum_assured,
            "coverage_basis": configured_basis,
            "waiting_period_days": configuration.waiting_period_days,
            "configuration": configuration,
        }

    @staticmethod
    @transaction.atomic
    def member_coverage_state(*, quotation, actor=None, request=None):
        locked = OLQuotation.objects.select_for_update().get(pk=quotation.pk)
        principal = QuotationService._sync_principal_member(quotation=locked, actor=actor, request=request)
        completion = QuotationService.wizard_completion(locked)
        if locked.wizard_step_completion != completion:
            locked.wizard_step_completion = completion
            locked.save(update_fields=["wizard_step_completion", "updated_at"])
        requirements = QuotationService._member_requirements(quotation=locked)
        additional = locked.members.exclude(pk=principal.pk if principal else None).order_by("created_at")
        return locked, principal, list(additional), requirements

    @staticmethod
    @transaction.atomic
    def add_member(*, quotation, actor, payload, request=None):
        locked = OLQuotation.objects.select_for_update().get(pk=quotation.pk)
        if locked.status != QuotationStatus.DRAFT:
            raise QuotationServiceError("Only draft quotations can be updated.")
        principal = QuotationService._sync_principal_member(quotation=locked, actor=actor, request=request)
        validated = QuotationService._validate_additional_member(quotation=locked, payload=payload)
        member = OLQuotationMember(
            quotation=locked,
            member_type="DEPENDENT",
            created_by=QuotationService.actor(actor),
            updated_by=QuotationService.actor(actor),
            first_name=validated["first_name"],
            last_name=validated["last_name"],
            date_of_birth=validated["date_of_birth"],
            age_at_quote=validated["age_at_quote"],
            gender=validated["gender"],
            relationship=validated["relationship"],
            member_sum_assured=validated["member_sum_assured"],
            coverage_basis=validated["coverage_basis"],
            waiting_period_days=validated["waiting_period_days"],
            metadata={"cover_configuration_id": str(validated["configuration"].pk), "cover_type": validated["configuration"].cover_type},
        )
        member.full_clean()
        member.save()
        AuditService.log_create(member, actor=actor, request=request, reason="Additional quotation member added.")
        locked.updated_by = QuotationService.actor(actor)
        locked.wizard_step_completion = QuotationService.wizard_completion(locked)
        locked.current_version_number += 1
        locked.save(update_fields=["wizard_step_completion", "current_version_number", "updated_by", "updated_at"])
        after_members = [QuotationService._member_state(row, is_principal=row.pk == getattr(principal, "pk", None)) for row in locked.members.order_by("created_at")]
        QuotationService._record_version(locked, actor=actor, reason="Member Coverage wizard step updated.")
        QuotationService._record_event(
            locked,
            "MEMBER_COVERAGE_UPDATED",
            actor=actor,
            from_status=locked.status,
            to_status=locked.status,
            notes="Additional quotation member added.",
            metadata={"operation": "ADD", "member_id": str(member.pk), "members": after_members},
            request=request,
        )
        return locked, member, QuotationService._member_requirements(quotation=locked)

    @staticmethod
    @transaction.atomic
    def update_member(*, quotation, member_id, actor, payload, request=None):
        locked = OLQuotation.objects.select_for_update().get(pk=quotation.pk)
        if locked.status != QuotationStatus.DRAFT:
            raise QuotationServiceError("Only draft quotations can be updated.")
        try:
            member = locked.members.select_for_update().get(pk=member_id)
        except (OLQuotationMember.DoesNotExist, ValueError, TypeError):
            raise QuotationServiceError({"member_id": "Member does not exist for this quotation."})
        if member.metadata.get("is_principal") or member.relationship in {"POLICYHOLDER", "PRINCIPAL", "LIFE_ASSURED", "SELF"}:
            raise QuotationServiceError({"member": "The principal member is immutable here; update Personal Details instead."})
        values = {
            "full_name": payload.get("full_name", " ".join(part for part in [member.first_name, member.last_name] if part).strip()),
            "relation": payload.get("relation", member.relationship),
            "date_of_birth": payload.get("date_of_birth", member.date_of_birth),
            "gender": payload.get("gender", member.gender),
            "sum_assured": payload.get("sum_assured", member.member_sum_assured),
        }
        validated = QuotationService._validate_additional_member(quotation=locked, payload=values, existing=member)
        before = AuditService.snapshot(member)
        for field, value in {
            "first_name": validated["first_name"],
            "last_name": validated["last_name"],
            "date_of_birth": validated["date_of_birth"],
            "age_at_quote": validated["age_at_quote"],
            "gender": validated["gender"],
            "relationship": validated["relationship"],
            "member_sum_assured": validated["member_sum_assured"],
            "coverage_basis": validated["coverage_basis"],
            "waiting_period_days": validated["waiting_period_days"],
        }.items():
            setattr(member, field, value)
        member.updated_by = QuotationService.actor(actor)
        member.full_clean()
        member.save()
        AuditService.log_update(member, before_state=before, actor=actor, request=request, reason="Additional quotation member updated.")
        locked.updated_by = QuotationService.actor(actor)
        locked.wizard_step_completion = QuotationService.wizard_completion(locked)
        locked.current_version_number += 1
        locked.save(update_fields=["wizard_step_completion", "current_version_number", "updated_by", "updated_at"])
        QuotationService._record_version(locked, actor=actor, reason="Member Coverage wizard step updated.")
        QuotationService._record_event(
            locked,
            "MEMBER_COVERAGE_UPDATED",
            actor=actor,
            from_status=locked.status,
            to_status=locked.status,
            notes="Additional quotation member updated.",
            metadata={"operation": "UPDATE", "member_id": str(member.pk), "member": QuotationService._member_state(member)},
            request=request,
        )
        return locked, member, QuotationService._member_requirements(quotation=locked)

    @staticmethod
    @transaction.atomic
    def remove_member(*, quotation, member_id, actor, request=None):
        locked = OLQuotation.objects.select_for_update().get(pk=quotation.pk)
        if locked.status != QuotationStatus.DRAFT:
            raise QuotationServiceError("Only draft quotations can be updated.")
        try:
            member = locked.members.select_for_update().get(pk=member_id)
        except (OLQuotationMember.DoesNotExist, ValueError, TypeError):
            raise QuotationServiceError({"member_id": "Member does not exist for this quotation."})
        if member.metadata.get("is_principal") or member.relationship in {"POLICYHOLDER", "PRINCIPAL", "LIFE_ASSURED", "SELF"}:
            raise QuotationServiceError({"member": "The principal member cannot be removed; update Personal Details instead."})
        member_state = QuotationService._member_state(member)
        AuditService.log_delete(member, actor=actor, request=request, reason="Additional quotation member removed.")
        member.delete()
        locked.updated_by = QuotationService.actor(actor)
        locked.wizard_step_completion = QuotationService.wizard_completion(locked)
        locked.current_version_number += 1
        locked.save(update_fields=["wizard_step_completion", "current_version_number", "updated_by", "updated_at"])
        QuotationService._record_version(locked, actor=actor, reason="Member Coverage wizard step updated.")
        QuotationService._record_event(
            locked,
            "MEMBER_COVERAGE_UPDATED",
            actor=actor,
            from_status=locked.status,
            to_status=locked.status,
            notes="Additional quotation member removed.",
            metadata={"operation": "REMOVE", "member": member_state},
            request=request,
        )
        return locked, QuotationService._member_requirements(quotation=locked)

    @staticmethod
    @transaction.atomic
    def update_draft(*, quotation, actor, validated_data, request=None):
        locked = OLQuotation.objects.select_for_update().get(pk=quotation.pk)
        if locked.status != QuotationStatus.DRAFT:
            raise QuotationServiceError("Only draft quotations can be updated.")
        before = QuotationService.snapshot(locked)
        for field, value in validated_data.items():
            setattr(locked, field, value)
        locked.updated_by = QuotationService.actor(actor)
        locked.full_clean(exclude=["quote_number"])
        locked.wizard_step_completion = QuotationService.wizard_completion(locked)
        locked.save()
        after = QuotationService.snapshot(locked)
        if before != after:
            locked.current_version_number += 1
            locked.save(update_fields=["current_version_number", "wizard_step_completion", "updated_at"])
            after = QuotationService.snapshot(locked)
            QuotationService._record_version(locked, actor=actor, reason="Quotation draft updated.")
            QuotationService._record_event(
                locked,
                "UPDATED",
                actor=actor,
                from_status=locked.status,
                to_status=locked.status,
                notes="Ordinary Life quotation draft updated.",
                before_state=before,
                after_state=after,
                request=request,
            )
        return locked

    @staticmethod
    @transaction.atomic
    def transition(*, quotation, target_status, actor, notes="", request=None):
        allowed = {
            QuotationStatus.DRAFT: {QuotationStatus.FINALIZED, QuotationStatus.EXPIRED},
            QuotationStatus.FINALIZED: {QuotationStatus.CONVERTED, QuotationStatus.EXPIRED},
            QuotationStatus.CONVERTED: set(),
            QuotationStatus.EXPIRED: set(),
        }
        locked = OLQuotation.objects.select_for_update().get(pk=quotation.pk)
        if target_status not in allowed.get(locked.status, set()):
            raise QuotationServiceError(
                {
                    "detail": "Quotation status transition is not allowed.",
                    "current_status": locked.status,
                    "requested_status": target_status,
                    "allowed_statuses": sorted(allowed.get(locked.status, set())),
                }
            )
        if target_status == QuotationStatus.FINALIZED:
            QuotationService.validate_wizard(locked)
            total_sum_assured, total_premium = QuotationService.calculate_totals(locked)
            locked.total_sum_assured = total_sum_assured
            locked.total_premium = total_premium
            locked.calculation_snapshot = {
                "calculated_at": timezone.now().isoformat(),
                "currency": locked.currency,
                "total_sum_assured": str(total_sum_assured),
                "total_premium": str(total_premium),
                "plan_configuration_ids": [str(pk) for pk in locked.plan_configurations.filter(is_selected=True).values_list("pk", flat=True)],
                "rider_selection_ids": [str(pk) for pk in locked.rider_selections.filter(is_selected=True).values_list("pk", flat=True)],
                "benefit_ids": [str(pk) for pk in locked.benefits.filter(is_selected=True).values_list("pk", flat=True)],
                "version_number": locked.current_version_number,
            }
        if target_status == QuotationStatus.CONVERTED and not locked.partner_verified:
            raise QuotationServiceError("Partner verification is required before conversion.")
        if target_status == QuotationStatus.EXPIRED and locked.expiry_date and locked.expiry_date > date.today():
            raise QuotationServiceError("A quotation cannot be expired before its configured expiry date.")
        before = QuotationService.snapshot(locked)
        locked.status = target_status
        locked.wizard_step_completion = QuotationService.wizard_completion(locked)
        locked.current_version_number += 1
        locked.updated_by = QuotationService.actor(actor)
        locked.save(update_fields=["status", "total_sum_assured", "total_premium", "calculation_snapshot", "wizard_step_completion", "current_version_number", "updated_by", "updated_at"])
        after = QuotationService.snapshot(locked)
        QuotationService._record_version(locked, actor=actor, reason=f"Quotation transitioned to {target_status}.")
        if target_status == QuotationStatus.FINALIZED:
            OLQuotationFinancialSummary.objects.update_or_create(
                quotation=locked,
                defaults={
                    "total_sum_assured": locked.total_sum_assured or Decimal("0"),
                    "total_premium": locked.total_premium or Decimal("0"),
                    "total_rider_premium": sum((item.premium_amount or Decimal("0") for item in locked.rider_selections.filter(is_selected=True)), Decimal("0")),
                    "total_benefit_premium": sum((item.premium_amount or Decimal("0") for item in locked.benefits.filter(is_selected=True)), Decimal("0")),
                    "currency": locked.currency,
                    "calculation_snapshot": locked.calculation_snapshot or {},
                    "created_by": QuotationService.actor(actor),
                    "updated_by": QuotationService.actor(actor),
                },
            )
        QuotationService._record_event(
            locked,
            target_status,
            actor=actor,
            from_status=before["status"],
            to_status=target_status,
            notes=notes or f"Quotation transitioned to {target_status}.",
            before_state=before,
            after_state=after,
            request=request,
        )
        return locked

    @staticmethod
    @transaction.atomic
    def revise(*, quotation, actor, request=None):
        locked = OLQuotation.objects.select_for_update().get(pk=quotation.pk)
        if locked.status != QuotationStatus.FINALIZED:
            raise QuotationServiceError("Only finalized quotations can be revised.")
        before = QuotationService.snapshot(locked)
        locked.status = QuotationStatus.DRAFT
        locked.total_sum_assured = None
        locked.total_premium = None
        locked.calculation_snapshot = {}
        locked.current_version_number += 1
        locked.wizard_step_completion = QuotationService.wizard_completion(locked)
        locked.updated_by = QuotationService.actor(actor)
        locked.save(update_fields=[
            "status",
            "total_sum_assured",
            "total_premium",
            "calculation_snapshot",
            "current_version_number",
            "wizard_step_completion",
            "updated_by",
            "updated_at",
        ])
        OLQuotationFinancialSummary.objects.filter(quotation=locked).delete()
        after = QuotationService.snapshot(locked)
        QuotationService._record_version(locked, actor=actor, reason="Quotation returned to draft for revision.")
        QuotationService._record_event(
            locked,
            "REVISED",
            actor=actor,
            from_status=QuotationStatus.FINALIZED,
            to_status=QuotationStatus.DRAFT,
            notes="Quotation returned to draft for revision.",
            before_state=before,
            after_state=after,
            request=request,
        )
        return locked

    @staticmethod
    def record_print(*, quotation, actor, request=None):
        snapshot = QuotationService.snapshot(quotation)
        return AuditService.log_action(
            action="PRINT",
            instance=quotation,
            actor=actor,
            request=request,
            before_state=snapshot,
            after_state=snapshot,
            reason="Quotation print metadata requested.",
            changed_fields=[],
        )

    @staticmethod
    @transaction.atomic
    def delete_draft(*, quotation, actor, request=None):
        locked = OLQuotation.objects.select_for_update().get(pk=quotation.pk)
        if locked.status != QuotationStatus.DRAFT:
            raise QuotationServiceError("Only draft quotations can be deleted.")
        before = QuotationService.snapshot(locked)
        AuditService.log_delete(
            instance=locked,
            actor=actor,
            request=request,
            reason="Quotation draft deleted.",
        )
        DomainEvent.objects.create(
            event_type="QuotationDeleted",
            aggregate_type="OLQuotation",
            aggregate_id=str(locked.pk),
            payload={
                "quote_number": locked.quote_number,
                "quotation_id": str(locked.pk),
                "actor_id": str(actor.pk) if actor and getattr(actor, "pk", None) else None,
                "before_state": before,
            },
        )
        locked.delete()
        return locked

    @staticmethod
    def ensure_expired(quotation):
        return bool(
            quotation.status in {QuotationStatus.DRAFT, QuotationStatus.FINALIZED}
            and quotation.expiry_date
            and quotation.expiry_date < date.today()
        )
