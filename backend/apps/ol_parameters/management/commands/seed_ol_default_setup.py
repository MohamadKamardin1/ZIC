from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.ol_parameters.models import OLDefaultSystemParameter

DEFAULT_SETUP_SEEDS = [
    {
        "parameter_key": "DEFAULT_CURRENCY",
        "name": "Default Currency",
        "parameter_category": "GENERAL",
        "value_type": "STRING",
        "typed_value": "TZS",
        "description": "Currency used when an OL product or transaction does not override the currency.",
    },
    {
        "parameter_key": "PREMIUM_CALCULATION_MODE",
        "name": "Premium Calculation Mode",
        "parameter_category": "RATING",
        "value_type": "STRING",
        "typed_value": "ANNUALIZED",
        "description": "Default premium calculation mode for Ordinary Life quotations and policies.",
    },
    {
        "parameter_key": "QUOTATION_EXPIRY_DAYS",
        "name": "Quotation Expiry Days",
        "parameter_category": "LIFECYCLE",
        "value_type": "INTEGER",
        "typed_value": 30,
        "description": "Number of days before an unconverted quotation expires.",
    },
    {
        "parameter_key": "PROPOSAL_VALIDITY_DAYS",
        "name": "Proposal Validity Days",
        "parameter_category": "LIFECYCLE",
        "value_type": "INTEGER",
        "typed_value": 30,
        "description": "Number of days a submitted proposal remains valid before review escalation.",
    },
    {
        "parameter_key": "FIRST_PREMIUM_REQUIRED",
        "name": "First Premium Required",
        "parameter_category": "LIFECYCLE",
        "value_type": "BOOLEAN",
        "typed_value": True,
        "description": "Whether first premium receipt is required before proposal-to-policy conversion.",
    },
    {
        "parameter_key": "DUPLICATE_CLAIM_BEHAVIOR",
        "name": "Duplicate Claim Behavior",
        "parameter_category": "CLAIMS",
        "value_type": "STRING",
        "typed_value": "REJECT",
        "description": "Default action when a claim appears to duplicate an existing claim event.",
    },
    {
        "parameter_key": "GRACE_PERIOD_DAYS",
        "name": "Grace Period Days",
        "parameter_category": "LIFECYCLE",
        "value_type": "INTEGER",
        "typed_value": 30,
        "description": "Default policy grace period after a missed premium due date.",
    },
    {
        "parameter_key": "WARNING_PERIOD_DAYS",
        "name": "Warning Period Days",
        "parameter_category": "LIFECYCLE",
        "value_type": "INTEGER",
        "typed_value": 15,
        "description": "Default warning period before lapse processing.",
    },
    {
        "parameter_key": "MATURITY_AUTO_CREATE_CLAIM",
        "name": "Automatically Create Maturity Claim",
        "parameter_category": "MATURITY",
        "value_type": "BOOLEAN",
        "typed_value": True,
        "description": "Whether maturity processing creates a claim automatically when no product override applies.",
    },
    {
        "parameter_key": "COMMISSION_BASIS",
        "name": "Commission Basis",
        "parameter_category": "COMMISSION",
        "value_type": "STRING",
        "typed_value": "FIRST_YEAR_PREMIUM",
        "description": "Default basis used when selecting a commission override.",
    },
    {
        "parameter_key": "POLICY_NUMBER_FORMAT",
        "name": "Policy Number Format",
        "parameter_category": "IDENTIFICATION",
        "value_type": "STRING",
        "typed_value": "OL-{YYYY}-{SEQ}",
        "description": "Default policy number template for Ordinary Life policy issuance.",
    },
]


def typed_storage(value_type, typed_value):
    fields = {
        "string_value": None,
        "integer_value": None,
        "decimal_value": None,
        "boolean_value": None,
        "date_value": None,
        "json_value": None,
    }
    field_for_type = {
        "STRING": "string_value",
        "TEXT": "string_value",
        "INTEGER": "integer_value",
        "DECIMAL": "decimal_value",
        "BOOLEAN": "boolean_value",
        "DATE": "date_value",
        "JSON": "json_value",
    }[value_type]
    fields[field_for_type] = typed_value
    return fields


class Command(BaseCommand):
    help = "Seed idempotent typed defaults for the Ordinary Life Default Setup group."

    @transaction.atomic
    def handle(self, *args, **options):
        created = 0
        updated = 0
        for seed in DEFAULT_SETUP_SEEDS:
            parameter_key = seed["parameter_key"]
            record, was_created = OLDefaultSystemParameter.objects.get_or_create(
                parameter_key=parameter_key,
                defaults={
                    "code": parameter_key,
                    "name": seed["name"],
                    "parameter_category": seed["parameter_category"],
                    "value_type": seed["value_type"],
                    "effective_from": date(2026, 1, 1),
                    "description": seed["description"],
                    "is_active": True,
                    **typed_storage(seed["value_type"], seed["typed_value"]),
                },
            )
            record.code = parameter_key
            record.name = seed["name"]
            record.parameter_category = seed["parameter_category"]
            record.description = seed["description"]
            record.value_type = seed["value_type"]
            record.effective_from = date(2026, 1, 1)
            record.is_active = True
            record.value = seed["typed_value"]
            record.full_clean()
            record.save()
            if was_created:
                created += 1
            else:
                updated += 1
        self.stdout.write(self.style.SUCCESS(f"OL Default Setup seeded: {created} created, {updated} updated."))
