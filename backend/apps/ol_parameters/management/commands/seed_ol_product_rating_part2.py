from datetime import date
from decimal import Decimal

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.ol_parameters.models import (
    OLBonusRate,
    OLCashSurrenderValue,
    OLInstallmentChargeRate,
    OLMortgageInterestFactor,
    OLParameterTableRegistry,
    OLReinstatementInterestRate,
    OLReserveLoading,
    OLProduct,
)


EFFECTIVE_FROM = date(2026, 1, 1)

REGISTRY_SEEDS = [
    {
        "slug": "reinstatement-interest-rates",
        "label": "OL Reinstatement Interest Rates",
        "description": "Effective-dated interest rates applied to reinstatement financial obligations.",
        "model_label": "ol_parameters.OLReinstatementInterestRate",
        "visible_columns": ["code", "name", "product", "plan", "rate", "calculation_basis", "effective_from", "effective_to", "is_active"],
        "searchable_fields": ["code", "name", "description", "calculation_basis", "product__code", "plan__code"],
        "filter_fields": ["is_active", "product", "plan", "calculation_basis", "effective_from", "effective_to"],
        "default_ordering": ["product", "plan", "calculation_basis", "-effective_from", "code"],
    },
    {
        "slug": "bonus-rates",
        "label": "OL Bonus Rates",
        "description": "Effective-dated bonus declaration assumptions by product or plan scope.",
        "model_label": "ol_parameters.OLBonusRate",
        "visible_columns": ["code", "name", "product", "plan", "bonus_type", "rate", "valuation_year", "declaration_frequency", "effective_from", "effective_to", "is_active"],
        "searchable_fields": ["code", "name", "description", "bonus_type", "declaration_frequency", "product__code", "plan__code"],
        "filter_fields": ["is_active", "product", "plan", "bonus_type", "valuation_year", "declaration_frequency", "effective_from", "effective_to"],
        "default_ordering": ["product", "plan", "bonus_type", "valuation_year", "-effective_from", "code"],
    },
    {
        "slug": "mortgage-interest-factors",
        "label": "OL Mortgage Interest Factors",
        "description": "Policy-loan or mortgage-linked interest factors by product scope.",
        "model_label": "ol_parameters.OLMortgageInterestFactor",
        "visible_columns": ["code", "name", "product", "plan", "factor", "calculation_basis", "effective_from", "effective_to", "is_active"],
        "searchable_fields": ["code", "name", "description", "calculation_basis", "product__code", "plan__code"],
        "filter_fields": ["is_active", "product", "plan", "calculation_basis", "effective_from", "effective_to"],
        "default_ordering": ["product", "plan", "calculation_basis", "-effective_from", "code"],
    },
    {
        "slug": "installment-charge-rates",
        "label": "OL Installment Charge Rates",
        "description": "Frequency- and event-specific installment charge assumptions.",
        "model_label": "ol_parameters.OLInstallmentChargeRate",
        "visible_columns": ["code", "name", "product", "plan", "frequency", "charge_type", "rate_value", "apply_on", "effective_from", "effective_to", "is_active"],
        "searchable_fields": ["code", "name", "description", "frequency", "charge_type", "apply_on", "product__code", "plan__code"],
        "filter_fields": ["is_active", "product", "plan", "frequency", "charge_type", "apply_on", "effective_from", "effective_to"],
        "default_ordering": ["product", "plan", "frequency", "charge_type", "apply_on", "-effective_from", "code"],
    },
    {
        "slug": "cash-surrender-values",
        "label": "OL Cash Surrender Values",
        "description": "Policy-year, age, term, and demographic surrender-value factors or rates.",
        "model_label": "ol_parameters.OLCashSurrenderValue",
        "visible_columns": ["code", "name", "product", "plan", "policy_year_from", "policy_year_to", "age_from", "age_to", "term_from", "term_to", "gender", "smoker_status", "surrender_value_factor", "rate", "effective_from", "effective_to", "is_active"],
        "searchable_fields": ["code", "name", "description", "gender", "smoker_status", "product__code", "plan__code"],
        "filter_fields": ["is_active", "product", "plan", "policy_year_from", "policy_year_to", "age_from", "age_to", "term_from", "term_to", "gender", "smoker_status", "effective_from", "effective_to"],
        "default_ordering": ["product", "plan", "policy_year_from", "age_from", "term_from", "code"],
    },
    {
        "slug": "reserve-loadings",
        "label": "OL Reserve Loadings",
        "description": "Effective-dated reserve expense, risk, contingency, profit, and capital loadings.",
        "model_label": "ol_parameters.OLReserveLoading",
        "visible_columns": ["code", "name", "product", "plan", "loading_type", "loading_basis", "rate_value", "effective_from", "effective_to", "is_active"],
        "searchable_fields": ["code", "name", "description", "loading_type", "loading_basis", "product__code", "plan__code"],
        "filter_fields": ["is_active", "product", "plan", "loading_type", "loading_basis", "effective_from", "effective_to"],
        "default_ordering": ["product", "plan", "loading_type", "loading_basis", "-effective_from", "code"],
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
    help = "Seed idempotent OL Product Rating Part 2 actuarial parameters."

    @transaction.atomic
    def handle(self, *args, **options):
        product = OLProduct.objects.filter(code="STANDARD_ENDOWMENT").first()
        if product is None:
            call_command("seed_ol_product_setup", verbosity=0)
            product = OLProduct.objects.get(code="STANDARD_ENDOWMENT")

        records = {}
        records["reinstatement_interest_rate"], reinstatement_created = upsert(
            OLReinstatementInterestRate,
            {"code": "STANDARD_ENDOWMENT_REINSTATEMENT_INTEREST"},
            {
                "name": "Standard Endowment Reinstatement Interest",
                "description": "Starter reinstatement interest assumption pending actuarial approval.",
                "product": product,
                "plan": None,
                "rate": Decimal("8.00000000"),
                "calculation_basis": "OUTSTANDING_PREMIUM",
                "effective_from": EFFECTIVE_FROM,
                "effective_to": None,
                "is_active": True,
            },
        )
        records["bonus_rate"], bonus_created = upsert(
            OLBonusRate,
            {"code": "STANDARD_ENDOWMENT_REVERSIONARY_BONUS"},
            {
                "name": "Standard Endowment Reversionary Bonus",
                "description": "Starter reversionary bonus assumption pending actuarial approval.",
                "product": product,
                "plan": None,
                "bonus_type": "REVERSIONARY",
                "rate": Decimal("2.00000000"),
                "valuation_year": None,
                "declaration_frequency": "ANNUAL",
                "effective_from": EFFECTIVE_FROM,
                "effective_to": None,
                "is_active": True,
            },
        )
        records["mortgage_interest_factor"], mortgage_created = upsert(
            OLMortgageInterestFactor,
            {"code": "STANDARD_ENDOWMENT_MORTGAGE_INTEREST_FACTOR"},
            {
                "name": "Standard Endowment Mortgage Interest Factor",
                "description": "Starter mortgage or policy-loan interest factor pending actuarial approval.",
                "product": product,
                "plan": None,
                "factor": Decimal("1.08000000"),
                "calculation_basis": "LOAN_BALANCE",
                "effective_from": EFFECTIVE_FROM,
                "effective_to": None,
                "is_active": True,
            },
        )
        records["installment_charge_rate"], installment_created = upsert(
            OLInstallmentChargeRate,
            {"code": "STANDARD_ENDOWMENT_ANNUAL_INSTALLMENT_CHARGE"},
            {
                "name": "Standard Endowment Annual Installment Charge",
                "description": "Starter annual installment charge assumption pending actuarial approval.",
                "product": product,
                "plan": None,
                "frequency": "ANNUAL",
                "charge_type": "PERCENTAGE",
                "rate_value": Decimal("0.00000000"),
                "apply_on": "PREMIUM",
                "effective_from": EFFECTIVE_FROM,
                "effective_to": None,
                "is_active": True,
            },
        )
        records["cash_surrender_value"], surrender_created = upsert(
            OLCashSurrenderValue,
            {"code": "STANDARD_ENDOWMENT_CSV_YEARS_1_30"},
            {
                "name": "Standard Endowment Cash Surrender Value",
                "description": "Starter surrender-value factor row pending actuarial approval.",
                "product": product,
                "plan": None,
                "policy_year_from": 1,
                "policy_year_to": 30,
                "age_from": 18,
                "age_to": 65,
                "term_from": 5,
                "term_to": 30,
                "gender": "",
                "smoker_status": "",
                "surrender_value_factor": Decimal("0.50000000"),
                "rate": None,
                "effective_from": EFFECTIVE_FROM,
                "effective_to": None,
                "is_active": True,
            },
        )
        records["reserve_loading"], reserve_created = upsert(
            OLReserveLoading,
            {"code": "STANDARD_ENDOWMENT_EXPENSE_RESERVE_LOADING"},
            {
                "name": "Standard Endowment Expense Reserve Loading",
                "description": "Starter reserve expense loading pending actuarial approval.",
                "product": product,
                "plan": None,
                "loading_type": "EXPENSE",
                "loading_basis": "RESERVE",
                "rate_value": Decimal("2.00000000"),
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
            upsert(OLParameterTableRegistry, {"slug": metadata["slug"]}, {**metadata, **registry_defaults})

        self.stdout.write(
            self.style.SUCCESS(
                "Seeded OL Product Rating Part 2: "
                f"reinstatement_created={reinstatement_created}, bonus_created={bonus_created}, "
                f"mortgage_created={mortgage_created}, installment_created={installment_created}, "
                f"surrender_created={surrender_created}, reserve_created={reserve_created}, "
                f"registry_contracts={len(REGISTRY_SEEDS)}."
            )
        )
