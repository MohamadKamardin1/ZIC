from django.core.management.base import BaseCommand
from django.db import transaction

from apps.ol_parameters.models import OLParameterTableRegistry


REGISTRY_SEEDS = [
    {
        "slug": "ol-default-setup",
        "label": "OL Default Setup",
        "parameter_group": "OL_DEFAULT_SETUP",
        "model_label": "ol_parameters.OLDefaultSetup",
        "description": "Global Ordinary Life defaults, lookup values, and operating rules.",
    },
    {
        "slug": "ol-policy-setup",
        "label": "OL Policy Setup",
        "parameter_group": "OL_POLICY_SETUP",
        "model_label": "ol_parameters.OLPolicySetup",
        "description": "Policy lifecycle, payment, grace, lapse, renewal, surrender, and reinstatement configuration.",
    },
    {
        "slug": "ol-product-setup",
        "label": "OL Product Setup",
        "parameter_group": "OL_PRODUCT_SETUP",
        "model_label": "ol_parameters.OLProductSetup",
        "description": "Product, plan, benefit, eligibility, and coverage configuration.",
    },
    {
        "slug": "ol-product-rating",
        "label": "OL Product Rating",
        "parameter_group": "OL_PRODUCT_RATING",
        "model_label": "ol_parameters.OLProductRating",
        "description": "Rate table headers, versions, rate dimensions, loadings, discounts, and rating rules.",
    },
    {
        "slug": "ol-rider-setup",
        "label": "OL Rider Setup",
        "parameter_group": "OL_RIDER_SETUP",
        "model_label": "ol_parameters.OLRiderSetup",
        "description": "Rider eligibility, benefits, limits, and pricing configuration.",
    },
    {
        "slug": "ol-agent-management",
        "label": "OL Agent Management",
        "parameter_group": "OL_AGENT_MANAGEMENT",
        "model_label": "ol_parameters.OLAgentManagement",
        "description": "Intermediary, agency, commission, hierarchy, and distribution configuration.",
    },
    {
        "slug": "ol-loan-setup",
        "label": "OL Loan Setup",
        "parameter_group": "OL_LOAN_SETUP",
        "model_label": "ol_parameters.OLLoanSetup",
        "description": "Ordinary Life loan eligibility, limits, terms, interest, and repayment configuration.",
    },
    {
        "slug": "ol-medical-underwriting",
        "label": "OL Medical / Underwriting",
        "parameter_group": "OL_MEDICAL_UW",
        "model_label": "ol_parameters.OLMedicalUnderwriting",
        "description": "Health questions, medical thresholds, underwriting requirements, and escalation rules.",
    },
    {
        "slug": "ol-claim-setup",
        "label": "OL Claim Setup",
        "parameter_group": "OL_CLAIM_SETUP",
        "model_label": "ol_parameters.OLClaimSetup",
        "description": "Claim types, waiting periods, documents, benefit calculations, and settlement rules.",
    },
]

DEFAULT_COLUMNS = [
    "code",
    "name",
    "description",
    "is_active",
    "effective_from",
    "effective_to",
    "created_at",
    "updated_at",
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
                "visible_columns": DEFAULT_COLUMNS,
                "searchable_fields": ["code", "name", "description"],
                "filter_fields": ["is_active", "effective_from", "effective_to"],
                "default_ordering": ["name", "code"],
                "allowed_actions": ["view", "create", "update", "deactivate", "configure"],
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
