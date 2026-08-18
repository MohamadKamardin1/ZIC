from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.ol_parameters.models import (
    OLAnticipatedEndowmentInstallmentRate,
    OLBeneficialType,
    OLGracePeriod,
    OLMemberCoverConfiguration,
    OLParameterTableRegistry,
    OLPolicyRenewalStatus,
    OLPolicyStatus,
)
from apps.ordinary_life.models import OLPlan, OLProduct


EFFECTIVE_FROM = date(2026, 1, 1)

POLICY_STATUS_SEEDS = [
    ("DRAFT", "Draft", False, "NEUTRAL", ["ACTIVE", "CANCELLED"]),
    ("ACTIVE", "Active", False, "POSITIVE", ["LAPSED", "SURRENDERED", "PAID_UP", "MATURED", "CANCELLED", "CLAIMED"]),
    ("LAPSED", "Lapsed", False, "WARNING", ["ACTIVE", "CANCELLED", "SURRENDERED", "CLAIMED"]),
    ("SURRENDERED", "Surrendered", True, "NEUTRAL", []),
    ("PAID_UP", "Paid up", False, "POSITIVE", ["MATURED", "SURRENDERED", "CLAIMED"]),
    ("MATURED", "Matured", True, "POSITIVE", []),
    ("CANCELLED", "Cancelled", True, "NEGATIVE", []),
    ("CLAIMED", "Claimed", True, "POSITIVE", []),
]

RENEWAL_STATUS_SEEDS = [
    ("NOT_DUE", "Not due", "NONE"),
    ("DUE", "Due", "RENEWAL_REQUIRED"),
    ("RENEWED", "Renewed", "RENEWAL_CREATED"),
    ("NOT_RENEWED", "Not renewed", "LAPSE_POLICY"),
]

BENEFICIAL_TYPE_SEEDS = [
    ("SPOUSE", "Spouse", "BENEFICIARY", "PERCENTAGE", Decimal("0"), True),
    ("CHILD", "Child", "BENEFICIARY", "PERCENTAGE", Decimal("0"), True),
    ("PARENT", "Parent", "BENEFICIARY", "PERCENTAGE", Decimal("0"), True),
    ("TRUSTEE", "Trustee", "BENEFICIARY", "PERCENTAGE", Decimal("0"), False),
    ("OTHER", "Other", "BENEFICIARY", "PERCENTAGE", Decimal("0"), True),
    ("DEATH_BENEFIT", "Death benefit", "BENEFIT", "SUM_ASSURED", Decimal("100"), False),
    ("MATURITY_BENEFIT", "Maturity benefit", "BENEFIT", "SUM_ASSURED", Decimal("100"), False),
]

REGISTRY_SEEDS = [
    {
        "slug": "anticipated-endowment-rates",
        "label": "Anticipated Endowment Installment Rates",
        "description": "Effective-dated product, plan, age, term, policy-year, frequency, and currency rate factors.",
        "model_label": "ol_parameters.OLAnticipatedEndowmentInstallmentRate",
        "visible_columns": ["code", "name", "product", "plan", "frequency", "rate_factor", "effective_from", "effective_to", "is_active"],
        "searchable_fields": ["code", "name", "description", "installment_type", "frequency", "currency"],
        "filter_fields": ["is_active", "product", "plan", "installment_type", "frequency", "currency", "effective_from", "effective_to"],
        "default_ordering": ["product", "plan", "frequency", "age_from", "term_from", "code"],
    },
    {
        "slug": "grace-periods",
        "label": "Grace Periods",
        "description": "Premium grace, warning, pre-lapse, and lapse timing by optional product and plan scope.",
        "model_label": "ol_parameters.OLGracePeriod",
        "visible_columns": ["code", "name", "product", "plan", "premium_frequency", "grace_days", "warning_days", "pre_lapse_days", "lapse_days", "is_active"],
        "searchable_fields": ["code", "name", "description", "premium_frequency"],
        "filter_fields": ["is_active", "product", "plan", "premium_frequency", "effective_from", "effective_to"],
        "default_ordering": ["product", "plan", "premium_frequency", "-effective_from", "code"],
    },
    {
        "slug": "policy-statuses",
        "label": "Policy Statuses",
        "description": "Configurable policy lifecycle status catalog with terminal flags and allowed transitions.",
        "model_label": "ol_parameters.OLPolicyStatus",
        "visible_columns": ["display_order", "code", "name", "badge_type", "is_terminal", "allowed_transitions", "is_active"],
        "searchable_fields": ["code", "name", "description", "badge_type"],
        "filter_fields": ["is_active", "is_terminal", "badge_type", "display_order"],
        "default_ordering": ["display_order", "name", "code"],
    },
    {
        "slug": "policy-renewal-statuses",
        "label": "Policy Renewal Statuses",
        "description": "Renewal status catalog and operational renewal action codes.",
        "model_label": "ol_parameters.OLPolicyRenewalStatus",
        "visible_columns": ["display_order", "code", "name", "renewal_action", "is_active"],
        "searchable_fields": ["code", "name", "description", "renewal_action"],
        "filter_fields": ["is_active", "renewal_action", "display_order"],
        "default_ordering": ["display_order", "name", "code"],
    },
    {
        "slug": "beneficial-types",
        "label": "Beneficial Types",
        "description": "Beneficiary, benefit, and coverage type catalog used by policy and claims configuration.",
        "model_label": "ol_parameters.OLBeneficialType",
        "visible_columns": ["category", "code", "name", "calculation_basis", "default_ratio", "allows_multiple", "is_active"],
        "searchable_fields": ["code", "name", "description", "category", "calculation_basis"],
        "filter_fields": ["is_active", "category", "calculation_basis", "allows_multiple"],
        "default_ordering": ["category", "name", "code"],
    },
    {
        "slug": "member-cover-configurations",
        "label": "Member Cover Configurations",
        "description": "Effective-dated member or dependent eligibility and cover limits by optional product and plan scope.",
        "model_label": "ol_parameters.OLMemberCoverConfiguration",
        "visible_columns": ["code", "name", "product", "plan", "cover_type", "member_relation", "min_age", "max_age", "waiting_period_days", "is_active"],
        "searchable_fields": ["code", "name", "description", "cover_type", "member_relation", "premium_basis", "coverage_basis"],
        "filter_fields": ["is_active", "product", "plan", "cover_type", "member_relation", "effective_from", "effective_to"],
        "default_ordering": ["product", "plan", "cover_type", "member_relation", "min_age", "code"],
    },
]


def upsert(model, lookup, defaults):
    record, created = model.objects.get_or_create(**lookup, defaults=defaults)
    for field_name, value in defaults.items():
        setattr(record, field_name, value)
    record.full_clean()
    record.save()
    return record, created


class Command(BaseCommand):
    help = "Seed idempotent OL Policy Setup Part 1 catalogs and safe starter configuration."

    @transaction.atomic
    def handle(self, *args, **options):
        created = 0
        updated = 0
        for index, (code, name, terminal, badge_type, transitions) in enumerate(POLICY_STATUS_SEEDS):
            record, was_created = upsert(
                OLPolicyStatus,
                {"code": code},
                {
                    "name": name,
                    "description": f"Ordinary Life policy lifecycle status: {name}.",
                    "display_order": index + 1,
                    "badge_type": badge_type,
                    "is_terminal": terminal,
                    "allowed_transitions": [],
                    "effective_from": EFFECTIVE_FROM,
                    "is_active": True,
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1

        for index, (code, name, action) in enumerate(RENEWAL_STATUS_SEEDS):
            _, was_created = upsert(
                OLPolicyRenewalStatus,
                {"code": code},
                {
                    "name": name,
                    "description": f"Ordinary Life renewal status: {name}.",
                    "display_order": index + 1,
                    "renewal_action": action,
                    "effective_from": EFFECTIVE_FROM,
                    "is_active": True,
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1

        status_by_code = {record.code: record for record in OLPolicyStatus.objects.filter(code__in=[seed[0] for seed in POLICY_STATUS_SEEDS])}
        for code, _, _, _, transitions in POLICY_STATUS_SEEDS:
            record = status_by_code[code]
            record.allowed_transitions = transitions
            record.full_clean()
            record.save(update_fields=["allowed_transitions", "updated_at"])

        for code, name, category, basis, ratio, allows_multiple in BENEFICIAL_TYPE_SEEDS:
            _, was_created = upsert(
                OLBeneficialType,
                {"code": code},
                {
                    "name": name,
                    "description": f"Ordinary Life {name.lower()} beneficial type.",
                    "category": category,
                    "calculation_basis": basis,
                    "default_ratio": ratio,
                    "allows_multiple": allows_multiple,
                    "effective_from": EFFECTIVE_FROM,
                    "is_active": True,
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1

        _, was_created = upsert(
            OLGracePeriod,
            {"code": "STANDARD_30_DAYS"},
            {
                "name": "Standard 30-Day Grace Period",
                "description": "Standard Ordinary Life premium grace period.",
                "effective_from": EFFECTIVE_FROM,
                "premium_frequency": "",
                "grace_days": 30,
                "warning_days": 15,
                "pre_lapse_days": 7,
                "lapse_days": 30,
                "minimum_due_amount": Decimal("0.00"),
                "is_active": True,
            },
        )
        if was_created:
            created += 1
        else:
            updated += 1

        _, was_created = upsert(
            OLMemberCoverConfiguration,
            {"code": "INDIVIDUAL"},
            {
                "name": "Individual Member Cover",
                "description": "Standard individual member cover configuration.",
                "effective_from": EFFECTIVE_FROM,
                "cover_type": "INDIVIDUAL",
                "member_relation": "MEMBER",
                "min_age": 18,
                "max_age": 65,
                "waiting_period_days": 0,
                "benefit_limit": None,
                "premium_basis": "MEMBER_PREMIUM",
                "coverage_basis": "SUM_ASSURED",
                "is_active": True,
            },
        )
        if was_created:
            created += 1
        else:
            updated += 1

        for registry_seed in REGISTRY_SEEDS:
            defaults = {
                **registry_seed,
                "parameter_group": "Policy Setup",
                "allowed_actions": ["list", "retrieve", "create", "update", "deactivate", "export"],
                "export_support": True,
                "permission_code": "ol_parameters.view",
                "permission_requirements": {
                    "view": "ol_parameters.view",
                    "create": "ol_parameters.create",
                    "update": "ol_parameters.update",
                    "deactivate": "ol_parameters.deactivate",
                    "configure": "ol_parameters.configure",
                },
                "is_active": True,
            }
            _, was_created = upsert(OLParameterTableRegistry, {"slug": registry_seed["slug"]}, defaults)
            if was_created:
                created += 1
            else:
                updated += 1

        product = OLProduct.objects.filter(is_active=True).order_by("code").first()
        if product:
            plan = OLPlan.objects.filter(product_version__product=product, is_active=True).order_by("code").first()
            _, was_created = upsert(
                OLAnticipatedEndowmentInstallmentRate,
                {"code": "BASE_ANTICIPATED_ENDOWMENT"},
                {
                    "name": "Base Anticipated Endowment Rate",
                    "description": "Starter rate factor; replace with approved actuarial rate-table data before production use.",
                    "effective_from": EFFECTIVE_FROM,
                    "product": product,
                    "plan": plan,
                    "installment_type": "ANTICIPATED_ENDOWMENT",
                    "frequency": "ANNUAL",
                    "rate_factor": Decimal("1.00000000"),
                    "currency": "",
                    "is_active": True,
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1
            rate_message = "one product-scoped starter anticipated-endowment rate"
        else:
            rate_message = "no anticipated-endowment rate (active product configuration is required)"

        self.stdout.write(
            self.style.SUCCESS(
                f"OL Policy Setup seeded: {created} created, {updated} updated; {rate_message}."
            )
        )
