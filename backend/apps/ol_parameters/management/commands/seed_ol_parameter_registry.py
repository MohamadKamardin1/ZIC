from django.core.management.base import BaseCommand
from django.db import transaction

from apps.ol_parameters.models import OLParameterTableRegistry


PERMISSION_REQUIREMENTS = {
    "view": "ol_parameters.view",
    "create": "ol_parameters.create",
    "update": "ol_parameters.update",
    "deactivate": "ol_parameters.deactivate",
    "configure": "ol_parameters.configure",
}


REGISTRY_SEEDS = [
    {
        "slug": "ol-default-setup",
        "label": "OL Default Setup",
        "parameter_group": "OL_DEFAULT_SETUP",
        "model_label": "ol_parameters.OLDefaultSystemParameter",
        "description": "Typed, effective-dated Ordinary Life defaults and operating parameters.",
        "visible_columns": [
            "code", "name", "parameter_key", "parameter_category", "value_type",
            "is_active", "effective_from", "effective_to",
        ],
        "searchable_fields": ["code", "name", "parameter_key", "parameter_category", "value_type"],
        "filter_fields": ["is_active", "parameter_category", "value_type", "effective_from", "effective_to"],
        "default_ordering": ["parameter_category", "name", "parameter_key"],
    },
    {
        "slug": "ol-policy-setup",
        "label": "OL Policy Setup",
        "parameter_group": "OL_POLICY_SETUP",
        "model_label": "ol_parameters.OLPolicyStatus",
        "description": "Policy lifecycle status and transition configuration; related policy tables are exposed by their own API routes.",
        "visible_columns": ["code", "name", "display_order", "badge_type", "is_terminal", "is_active"],
        "searchable_fields": ["code", "name", "description", "badge_type"],
        "filter_fields": ["is_active", "is_terminal", "badge_type", "display_order"],
        "default_ordering": ["display_order", "name", "code"],
    },
    {
        "slug": "ol-product-setup",
        "label": "OL Product Setup",
        "parameter_group": "OL_PRODUCT_SETUP",
        "model_label": "ol_parameters.OLProduct",
        "description": "Ordinary Life product definitions and product-level eligibility controls.",
        "visible_columns": [
            "code", "name", "plan_type", "insurance_class", "currency", "min_entry_age",
            "max_entry_age", "min_term", "max_term", "is_active", "effective_from", "effective_to",
        ],
        "searchable_fields": ["code", "name", "description", "insurance_class", "currency", "plan_type__code"],
        "filter_fields": ["is_active", "plan_type", "insurance_class", "currency", "effective_from", "effective_to"],
        "default_ordering": ["name", "code"],
    },
    {
        "slug": "ol-product-rating",
        "label": "OL Product Rating",
        "parameter_group": "OL_PRODUCT_RATING",
        "model_label": "ol_parameters.OLPremiumRateTable",
        "description": "Premium-rate table versions and the related mortality, joint-life, loading, and charge tables.",
        "visible_columns": [
            "table_code", "name", "product", "plan", "rating_basis", "currency", "version",
            "effective_from", "effective_to", "is_active",
        ],
        "searchable_fields": [
            "table_code", "name", "description", "rating_basis", "currency", "version",
            "product__code", "plan__code",
        ],
        "filter_fields": [
            "is_active", "product", "plan", "rating_basis", "currency", "version",
            "effective_from", "effective_to",
        ],
        "default_ordering": ["table_code", "-effective_from", "version"],
    },
    {
        "slug": "ol-rider-setup",
        "label": "OL Rider Setup",
        "parameter_group": "OL_RIDER_SETUP",
        "model_label": "ol_parameters.OLRiderSetup",
        "description": "Rider definitions, applicability, underwriting requirements, and rider rate tables.",
        "visible_columns": [
            "code", "name", "rider_category", "benefit_type", "calculation_basis", "product", "plan",
            "min_age", "max_age", "is_active", "effective_from", "effective_to",
        ],
        "searchable_fields": [
            "code", "name", "description", "rider_category", "benefit_type", "calculation_basis",
            "product__code", "plan__code",
        ],
        "filter_fields": [
            "is_active", "rider_category", "benefit_type", "calculation_basis", "product", "plan",
            "allows_standalone", "requires_underwriting", "effective_from", "effective_to",
        ],
        "default_ordering": ["rider_category", "name", "code"],
    },
    {
        "slug": "ol-agent-management",
        "label": "OL Agent Management",
        "parameter_group": "OL_AGENT_MANAGEMENT",
        "model_label": "ol_parameters.OLAgentCommissionSetup",
        "description": "Effective-dated intermediary commission rules by product, channel, and commission type.",
        "visible_columns": [
            "code", "name", "partner", "intermediary_type", "distribution_channel", "product", "plan",
            "rider", "commission_type", "rate_type", "rate_value", "priority", "effective_from",
            "effective_to", "is_active",
        ],
        "searchable_fields": [
            "code", "name", "description", "reason", "intermediary_type", "distribution_channel", "currency",
            "partner__partner_number", "product__code", "plan__code", "rider__code",
        ],
        "filter_fields": [
            "is_active", "partner", "product", "plan", "rider", "branch", "intermediary_type",
            "distribution_channel", "currency", "commission_type", "rate_type", "priority",
            "premium_year_from", "premium_year_to", "policy_year_from", "policy_year_to",
            "effective_from", "effective_to",
        ],
        "default_ordering": ["priority", "commission_type", "-effective_from", "code"],
    },
    {
        "slug": "ol-loan-setup",
        "label": "OL Loan Setup",
        "parameter_group": "OL_LOAN_SETUP",
        "model_label": "ol_parameters.OLLoanSystemSetup",
        "description": "Policy-loan eligibility, limits, benefit effects, approval rules, and related interest controls.",
        "visible_columns": [
            "code", "name", "product", "plan", "allow_policy_loans", "loan_basis", "loan_currency",
            "max_loan_percentage_of_cash_value", "min_loan_amount", "max_loan_amount", "require_approval",
            "is_active", "effective_from", "effective_to",
        ],
        "searchable_fields": ["code", "name", "description", "loan_basis", "loan_currency", "effect_on_claim", "effect_on_surrender", "effect_on_maturity"],
        "filter_fields": ["is_active", "product", "plan", "allow_policy_loans", "loan_basis", "loan_currency", "require_approval", "effective_from", "effective_to"],
        "default_ordering": ["product", "plan", "-effective_from", "code"],
    },
    {
        "slug": "ol-medical-underwriting",
        "label": "OL Medical / Underwriting",
        "parameter_group": "OL_MEDICAL_UW",
        "model_label": "ol_parameters.OLMedicalCode",
        "description": "Medical evidence and underwriting catalogs, risk limits, facility references, and practitioner references.",
        "visible_columns": ["code", "name", "medical_category", "description", "is_active", "effective_from", "effective_to"],
        "searchable_fields": ["code", "name", "description", "medical_category"],
        "filter_fields": ["is_active", "medical_category", "effective_from", "effective_to"],
        "default_ordering": ["medical_category", "name", "code"],
    },
    {
        "slug": "ol-claim-setup",
        "label": "OL Claim Setup",
        "parameter_group": "OL_CLAIM_SETUP",
        "model_label": "ol_parameters.OLClaimType",
        "description": "Claim types, reasons, statuses, discharge templates, and correspondence catalogs.",
        "visible_columns": [
            "code", "name", "claim_category", "calculation_basis", "duplicate_check_rule", "waiting_period_days",
            "allow_waiver_of_premium", "require_approval", "is_active",
        ],
        "searchable_fields": ["code", "name", "description", "claim_category", "calculation_basis", "duplicate_check_rule"],
        "filter_fields": ["is_active", "claim_category", "calculation_basis", "duplicate_check_rule", "allow_waiver_of_premium", "require_approval"],
        "default_ordering": ["claim_category", "name", "code"],
    },
]


class Command(BaseCommand):
    help = "Seed the table metadata registry for the nine Ordinary Life parameter groups."

    @transaction.atomic
    def handle(self, *args, **options):
        created = 0
        updated = 0
        for seed in REGISTRY_SEEDS:
            defaults = {
                **seed,
                "allowed_actions": ["view", "create", "update", "deactivate", "configure"],
                "export_support": True,
                "permission_code": "ol_parameters.view",
                "permission_requirements": PERMISSION_REQUIREMENTS,
                "is_active": True,
            }
            _, was_created = OLParameterTableRegistry.objects.update_or_create(
                slug=seed["slug"], defaults=defaults
            )
            if was_created:
                created += 1
            else:
                updated += 1
        self.stdout.write(
            self.style.SUCCESS(
                f"OL parameter registry seeded: {created} created, {updated} updated."
            )
        )
