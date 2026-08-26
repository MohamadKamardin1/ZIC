from datetime import date
from decimal import Decimal

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.ol_parameters.models import (
    OLParameterTableRegistry,
    OLProduct,
    OLRiderRateRow,
    OLRiderRateTable,
    OLRiderSetup,
)

EFFECTIVE_FROM = date(2026, 1, 1)

REGISTRY_SEEDS = [
    {
        "slug": "rider-setups",
        "label": "OL Rider Setups",
        "description": "Parameterized Ordinary Life rider catalog and applicability rules.",
        "model_label": "ol_parameters.OLRiderSetup",
        "visible_columns": [
            "code",
            "name",
            "rider_category",
            "benefit_type",
            "calculation_basis",
            "product",
            "plan",
            "min_age",
            "max_age",
            "min_term",
            "max_term",
            "allows_standalone",
            "requires_underwriting",
            "effective_from",
            "effective_to",
            "is_active",
        ],
        "searchable_fields": [
            "code",
            "name",
            "description",
            "rider_category",
            "benefit_type",
            "product__code",
            "plan__code",
        ],
        "filter_fields": [
            "is_active",
            "rider_category",
            "benefit_type",
            "calculation_basis",
            "product",
            "plan",
            "allows_standalone",
            "requires_underwriting",
            "effective_from",
            "effective_to",
        ],
        "default_ordering": ["rider_category", "benefit_type", "name", "code"],
    },
    {
        "slug": "rider-rate-tables",
        "label": "OL Rider Rate Tables",
        "description": "Versioned rider rate table headers scoped to riders and product applicability.",
        "model_label": "ol_parameters.OLRiderRateTable",
        "visible_columns": [
            "table_code",
            "name",
            "rider",
            "product",
            "plan",
            "rating_basis",
            "version",
            "effective_from",
            "effective_to",
            "is_active",
        ],
        "searchable_fields": [
            "table_code",
            "name",
            "description",
            "rider__code",
            "product__code",
            "plan__code",
            "rating_basis",
            "version",
        ],
        "filter_fields": [
            "is_active",
            "rider",
            "product",
            "plan",
            "rating_basis",
            "version",
            "effective_from",
            "effective_to",
        ],
        "default_ordering": ["table_code", "rider", "-effective_from", "version"],
    },
    {
        "slug": "rider-rate-rows",
        "label": "OL Rider Rate Rows",
        "description": "Multi-dimensional rider premium rate rows by demographic, age, term, and sum-assured bands.",
        "model_label": "ol_parameters.OLRiderRateRow",
        "visible_columns": [
            "code",
            "table",
            "gender",
            "smoker_status",
            "age_from",
            "age_to",
            "term_from",
            "term_to",
            "frequency",
            "sum_assured_band_from",
            "sum_assured_band_to",
            "rate",
            "rate_unit",
            "effective_from",
            "effective_to",
            "is_active",
        ],
        "searchable_fields": [
            "code",
            "name",
            "description",
            "gender",
            "smoker_status",
            "frequency",
            "table__table_code",
        ],
        "filter_fields": [
            "is_active",
            "table",
            "gender",
            "smoker_status",
            "frequency",
            "rate_unit",
            "age_from",
            "age_to",
            "term_from",
            "term_to",
            "effective_from",
            "effective_to",
        ],
        "default_ordering": [
            "table",
            "gender",
            "smoker_status",
            "frequency",
            "age_from",
            "term_from",
            "code",
        ],
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
    help = "Seed idempotent OL Rider Setup parameters."

    @transaction.atomic
    def handle(self, *args, **options):
        product = OLProduct.objects.filter(code="STANDARD_ENDOWMENT").first()
        if product is None:
            call_command("seed_ol_product_setup", verbosity=0)
            product = OLProduct.objects.get(code="STANDARD_ENDOWMENT")

        rider, rider_created = upsert(
            OLRiderSetup,
            {"code": "STANDARD_ENDOWMENT_ACCIDENTAL_DEATH"},
            {
                "name": "Standard Endowment Accidental Death Rider",
                "description": "Starter accidental-death rider applicability pending actuarial approval.",
                "rider_category": "ACCIDENT",
                "benefit_type": "ACCIDENTAL_DEATH",
                "calculation_basis": "SUM_ASSURED",
                "min_age": 18,
                "max_age": 65,
                "min_term": 5,
                "max_term": 30,
                "min_sum_assured": Decimal("1000000.00"),
                "max_sum_assured": Decimal("1000000000.00"),
                "waiting_period_days": 30,
                "allows_standalone": False,
                "requires_underwriting": True,
                "exclusion_rules": {"codes": ["SELF_INFLICTED_INJURY", "WAR"], "review_required": True},
                "product": product,
                "plan": None,
                "effective_from": EFFECTIVE_FROM,
                "effective_to": None,
                "is_active": True,
            },
        )

        rate_table, rate_table_created = upsert(
            OLRiderRateTable,
            {"table_code": "STANDARD_ENDOWMENT_ACCIDENTAL_DEATH_RATE", "version": "1.0"},
            {
                "name": "Standard Endowment Accidental Death Rider Rate",
                "description": "Starter accidental-death rider rate table pending actuarial approval.",
                "rider": rider,
                "product": product,
                "plan": None,
                "rating_basis": "AGE_TERM",
                "version": "1.0",
                "effective_from": EFFECTIVE_FROM,
                "effective_to": None,
                "is_active": True,
            },
        )

        row, row_created = upsert(
            OLRiderRateRow,
            {"code": "STANDARD_ENDOWMENT_ACCIDENTAL_DEATH_RATE_M_NS"},
            {
                "name": "Standard Endowment Accidental Death Male Non-Smoker Rate",
                "description": "Starter rider rate row pending actuarial approval.",
                "table": rate_table,
                "gender": "M",
                "smoker_status": "NS",
                "age_from": 18,
                "age_to": 65,
                "term_from": 5,
                "term_to": 30,
                "frequency": "ANNUAL",
                "sum_assured_band_from": Decimal("1000000.00"),
                "sum_assured_band_to": Decimal("1000000000.00"),
                "rate": Decimal("1.25000000"),
                "rate_unit": "PER_THOUSAND_SUM_ASSURED",
                "effective_from": EFFECTIVE_FROM,
                "effective_to": None,
                "is_active": True,
            },
        )

        registry_defaults = {
            "parameter_group": "RIDER_SETUP",
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
                "Seeded OL Rider Setup: "
                f"rider_created={rider_created}, rate_table_created={rate_table_created}, "
                f"rate_row_created={row_created}, registry_contracts={len(REGISTRY_SEEDS)}."
            )
        )
