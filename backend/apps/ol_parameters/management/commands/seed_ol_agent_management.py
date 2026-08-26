from datetime import date
from decimal import Decimal

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.ol_parameters.models import OLAgentCommissionSetup, OLParameterTableRegistry, OLProduct, OLRiderSetup

EFFECTIVE_FROM = date(2026, 1, 1)

REGISTRY_SEEDS = [
    {
        "slug": "agent-commission-setups",
        "label": "OL Agent Commission Setups",
        "description": "Effective-dated intermediary commission rules by product, channel, and commission type.",
        "model_label": "ol_parameters.OLAgentCommissionSetup",
        "visible_columns": [
            "code", "name", "partner", "intermediary_type", "distribution_channel", "product", "plan", "rider",
            "commission_type", "rate_type", "rate_value", "priority", "effective_from", "effective_to", "is_active",
        ],
        "searchable_fields": [
            "code", "name", "description", "reason", "intermediary_type", "distribution_channel", "currency",
            "partner__code", "product__code", "plan__code", "rider__code",
        ],
        "filter_fields": [
            "is_active", "partner", "product", "plan", "rider", "branch", "intermediary_type", "distribution_channel",
            "currency", "commission_type", "rate_type", "priority", "premium_year_from", "premium_year_to",
            "policy_year_from", "policy_year_to", "effective_from", "effective_to",
        ],
        "default_ordering": ["priority", "commission_type", "-effective_from", "code"],
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
    help = "Seed idempotent OL Agent Management commission parameters."

    @transaction.atomic
    def handle(self, *args, **options):
        product = OLProduct.objects.filter(code="STANDARD_ENDOWMENT").first()
        if product is None:
            call_command("seed_ol_product_setup", verbosity=0)
            product = OLProduct.objects.get(code="STANDARD_ENDOWMENT")

        rider = OLRiderSetup.objects.filter(code="STANDARD_ENDOWMENT_ACCIDENTAL_DEATH").first()
        if rider is None:
            call_command("seed_ol_rider_setup", verbosity=0)
            rider = OLRiderSetup.objects.get(code="STANDARD_ENDOWMENT_ACCIDENTAL_DEATH")

        commission, commission_created = upsert(
            OLAgentCommissionSetup,
            {"code": "STANDARD_ENDOWMENT_AGENCY_FIRST_PREMIUM"},
            {
                "name": "Standard Endowment Agency First Premium Commission",
                "description": "Starter agency commission rule pending commercial and actuarial approval.",
                "partner": None,
                "intermediary_type": "AGENT",
                "distribution_channel": "AGENCY",
                "product": product,
                "plan": None,
                "rider": rider,
                "currency": "TZS",
                "branch": None,
                "commission_type": "FIRST_PREMIUM",
                "premium_year_from": 1,
                "premium_year_to": 1,
                "policy_year_from": 1,
                "policy_year_to": 1,
                "rate_type": "PERCENTAGE",
                "rate_value": Decimal("10.00000000"),
                "minimum_commission": Decimal("0.00000000"),
                "maximum_commission": None,
                "priority": 100,
                "effective_from": EFFECTIVE_FROM,
                "effective_to": None,
                "is_active": True,
                "reason": "Development starter configuration; requires approval before production use.",
            },
        )

        registry_defaults = {
            "parameter_group": "AGENT_MANAGEMENT",
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
        for metadata in REGISTRY_SEEDS:
            upsert(OLParameterTableRegistry, {"slug": metadata["slug"]}, {**metadata, **registry_defaults})

        self.stdout.write(
            self.style.SUCCESS(
                "Seeded OL Agent Management: "
                f"commission_created={commission_created}, registry_contracts={len(REGISTRY_SEEDS)}."
            )
        )
