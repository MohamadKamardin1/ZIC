from datetime import date
from decimal import Decimal

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.ol_parameters.models import (
    OLJointLifeSetup,
    OLMortalityRateRow,
    OLMortalityRateTable,
    OLParameterTableRegistry,
    OLPremiumRateRow,
    OLPremiumRateTable,
    OLProduct,
)


EFFECTIVE_FROM = date(2026, 1, 1)

REGISTRY_SEEDS = [
    {
        "slug": "premium-rate-tables",
        "label": "OL Premium Rate Tables",
        "description": "Versioned premium-rate table headers scoped to an OL product and optional plan.",
        "model_label": "ol_parameters.OLPremiumRateTable",
        "visible_columns": ["table_code", "name", "product", "plan", "rating_basis", "currency", "version", "effective_from", "effective_to", "is_active"],
        "searchable_fields": ["table_code", "name", "description", "rating_basis", "currency", "version", "product__code", "plan__code"],
        "filter_fields": ["is_active", "product", "plan", "rating_basis", "currency", "version", "effective_from", "effective_to"],
        "default_ordering": ["table_code", "-effective_from", "version"],
    },
    {
        "slug": "premium-rate-rows",
        "label": "OL Premium Rate Rows",
        "description": "Table-driven premium rate dimensions and decimal rates.",
        "model_label": "ol_parameters.OLPremiumRateRow",
        "visible_columns": ["table", "gender", "smoker_status", "age_from", "age_to", "term_from", "term_to", "frequency", "rate", "rate_unit", "is_active"],
        "searchable_fields": ["code", "name", "description", "table__table_code", "table__version", "gender", "smoker_status", "frequency", "rate_unit"],
        "filter_fields": ["is_active", "table", "gender", "smoker_status", "age_from", "age_to", "term_from", "term_to", "frequency", "rate_unit", "effective_from", "effective_to"],
        "default_ordering": ["table", "gender", "smoker_status", "frequency", "age_from", "term_from", "code"],
    },
    {
        "slug": "mortality-rate-tables",
        "label": "OL Mortality Rate Tables",
        "description": "Versioned mortality basis table headers.",
        "model_label": "ol_parameters.OLMortalityRateTable",
        "visible_columns": ["table_code", "name", "version", "effective_from", "effective_to", "is_active"],
        "searchable_fields": ["table_code", "name", "description", "version"],
        "filter_fields": ["is_active", "version", "effective_from", "effective_to"],
        "default_ordering": ["table_code", "-effective_from", "version"],
    },
    {
        "slug": "mortality-rate-rows",
        "label": "OL Mortality Rate Rows",
        "description": "Age, gender, smoker, policy-year, and decimal mortality-rate rows.",
        "model_label": "ol_parameters.OLMortalityRateRow",
        "visible_columns": ["table", "age", "gender", "smoker_status", "policy_year", "mortality_rate", "is_active"],
        "searchable_fields": ["code", "name", "description", "table__table_code", "table__version", "gender", "smoker_status"],
        "filter_fields": ["is_active", "table", "age", "gender", "smoker_status", "policy_year", "effective_from", "effective_to"],
        "default_ordering": ["table", "age", "gender", "smoker_status", "policy_year", "code"],
    },
    {
        "slug": "joint-life-setups",
        "label": "OL Joint Life Setups",
        "description": "Effective-dated joint-life product or plan configuration rules.",
        "model_label": "ol_parameters.OLJointLifeSetup",
        "visible_columns": ["code", "name", "product", "plan", "joint_life_type", "age_basis", "survivor_benefit_rule", "premium_adjustment_factor", "underwriting_rule", "is_active"],
        "searchable_fields": ["code", "name", "description", "joint_life_type", "age_basis", "survivor_benefit_rule", "underwriting_rule", "product__code", "plan__code"],
        "filter_fields": ["is_active", "product", "plan", "joint_life_type", "age_basis", "effective_from", "effective_to"],
        "default_ordering": ["product", "plan", "joint_life_type", "-effective_from", "code"],
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
    help = "Seed idempotent OL Product Rating Part 1 tables, rows, and registry contracts."

    @transaction.atomic
    def handle(self, *args, **options):
        product = OLProduct.objects.filter(code="STANDARD_ENDOWMENT").first()
        if product is None:
            call_command("seed_ol_product_setup", verbosity=0)
            product = OLProduct.objects.get(code="STANDARD_ENDOWMENT")

        premium_table, premium_table_created = upsert(
            OLPremiumRateTable,
            {"table_code": "STANDARD_ENDOWMENT_PREMIUM", "version": "1.0"},
            {
                "name": "Standard Endowment Premium Rates",
                "description": "Starter annual premium rates pending actuarial approval and production calibration.",
                "product": product,
                "plan": None,
                "rating_basis": "AGE_TERM",
                "currency": "TZS",
                "effective_from": EFFECTIVE_FROM,
                "effective_to": None,
                "is_active": True,
            },
        )
        premium_row, premium_row_created = upsert(
            OLPremiumRateRow,
            {"code": "STANDARD_ENDOWMENT_PREM_M_NS_18_65_5_30_ANNUAL"},
            {
                "name": "Standard Endowment Male Non-Smoker Annual",
                "description": "Starter premium-rate row for development and configuration testing.",
                "table": premium_table,
                "gender": "M",
                "smoker_status": "NS",
                "age_from": 18,
                "age_to": 65,
                "term_from": 5,
                "term_to": 30,
                "frequency": "ANNUAL",
                "sum_assured_band_from": None,
                "sum_assured_band_to": None,
                "rate": Decimal("12.50000000"),
                "rate_unit": "PER_THOUSAND_SUM_ASSURED",
                "effective_from": EFFECTIVE_FROM,
                "effective_to": None,
                "is_active": True,
            },
        )
        mortality_table, mortality_table_created = upsert(
            OLMortalityRateTable,
            {"table_code": "ZIC_STANDARD_MORTALITY", "version": "1.0"},
            {
                "name": "ZIC Standard Mortality Basis",
                "description": "Starter mortality basis for development and configuration testing.",
                "effective_from": EFFECTIVE_FROM,
                "effective_to": None,
                "is_active": True,
            },
        )
        mortality_row, mortality_row_created = upsert(
            OLMortalityRateRow,
            {"code": "ZIC_STANDARD_MORTALITY_AGE_18_M_NS"},
            {
                "name": "Age 18 Male Non-Smoker Mortality",
                "description": "Starter mortality row; replace with approved actuarial basis before production use.",
                "table": mortality_table,
                "age": 18,
                "gender": "M",
                "smoker_status": "NS",
                "policy_year": None,
                "mortality_rate": Decimal("0.001200000000"),
                "effective_from": EFFECTIVE_FROM,
                "effective_to": None,
                "is_active": True,
            },
        )
        joint_life, joint_life_created = upsert(
            OLJointLifeSetup,
            {"code": "STANDARD_ENDOWMENT_JOINT_FIRST_DEATH"},
            {
                "name": "Standard Endowment Joint First Death",
                "description": "Starter joint-life configuration for development and configuration testing.",
                "product": product,
                "plan": None,
                "joint_life_type": "FIRST_DEATH",
                "age_basis": "YOUNGER_LIFE",
                "survivor_benefit_rule": "PAY_ON_FIRST_DEATH",
                "premium_adjustment_factor": Decimal("1.150000"),
                "underwriting_rule": "FULL_UNDERWRITING",
                "effective_from": EFFECTIVE_FROM,
                "effective_to": None,
                "is_active": True,
            },
        )

        registry_defaults = {
            "parameter_group": "PRODUCT_RATING",
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
            defaults = {**metadata, **registry_defaults}
            upsert(OLParameterTableRegistry, {"slug": metadata["slug"]}, defaults)

        self.stdout.write(
            self.style.SUCCESS(
                "Seeded OL Product Rating Part 1: "
                f"premium_table_created={premium_table_created}, premium_row_created={premium_row_created}, "
                f"mortality_table_created={mortality_table_created}, mortality_row_created={mortality_row_created}, "
                f"joint_life_created={joint_life_created}, registry_contracts={len(REGISTRY_SEEDS)}."
            )
        )
