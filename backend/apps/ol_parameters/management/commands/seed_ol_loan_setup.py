from datetime import date
from decimal import Decimal

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.ol_parameters.models import (
    OLLoanInterestControl,
    OLLoanSystemSetup,
    OLParameterTableRegistry,
    OLProduct,
)


EFFECTIVE_FROM = date(2026, 1, 1)

REGISTRY_SEEDS = [
    {
        "slug": "loan-system-setups",
        "label": "OL Loan System Setups",
        "description": "Effective-dated policy loan eligibility, limits, repayment, and benefit-effect configuration.",
        "model_label": "ol_parameters.OLLoanSystemSetup",
        "visible_columns": [
            "code", "name", "product", "plan", "allow_policy_loans", "loan_basis",
            "max_loan_percentage_of_cash_value", "min_loan_amount", "max_loan_amount",
            "loan_currency", "auto_deduct_from_benefits", "require_approval", "effective_from", "effective_to", "is_active",
        ],
        "searchable_fields": [
            "code", "name", "description", "loan_basis", "loan_currency",
            "effect_on_claim", "effect_on_surrender", "effect_on_maturity", "product__code", "plan__code",
        ],
        "filter_fields": [
            "is_active", "product", "plan", "allow_policy_loans", "loan_basis", "loan_currency",
            "auto_deduct_from_benefits", "require_approval", "effect_on_claim", "effect_on_surrender",
            "effect_on_maturity", "effective_from", "effective_to",
        ],
        "default_ordering": ["product", "plan", "-effective_from", "code"],
    },
    {
        "slug": "loan-interest-controls",
        "label": "OL Loan Interest Controls",
        "description": "Effective-dated loan interest, grace, penalty, suspension, and capitalization configuration.",
        "model_label": "ol_parameters.OLLoanInterestControl",
        "visible_columns": [
            "code", "name", "product", "plan", "interest_rate", "compounding_frequency",
            "interest_calculation_basis", "grace_period_days", "penalty_interest_rate",
            "capitalize_interest", "effective_from", "effective_to", "is_active",
        ],
        "searchable_fields": [
            "code", "name", "description", "compounding_frequency", "interest_calculation_basis",
            "interest_suspension_rule", "product__code", "plan__code",
        ],
        "filter_fields": [
            "is_active", "product", "plan", "compounding_frequency", "interest_calculation_basis",
            "capitalize_interest", "effective_from", "effective_to",
        ],
        "default_ordering": ["product", "plan", "-effective_from", "code"],
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
    help = "Seed idempotent OL Loan Setup parameters."

    @transaction.atomic
    def handle(self, *args, **options):
        product = OLProduct.objects.filter(code="STANDARD_ENDOWMENT").first()
        if product is None:
            call_command("seed_ol_product_setup", verbosity=0)
            product = OLProduct.objects.get(code="STANDARD_ENDOWMENT")

        loan_system, loan_system_created = upsert(
            OLLoanSystemSetup,
            {"code": "STANDARD_ENDOWMENT_POLICY_LOAN"},
            {
                "name": "Standard Endowment Policy Loan",
                "description": "Starter policy-loan configuration pending product, actuarial, and governance approval.",
                "product": product,
                "plan": None,
                "allow_policy_loans": True,
                "loan_basis": "CASH_VALUE",
                "max_loan_percentage_of_cash_value": Decimal("80.00000000"),
                "min_loan_amount": Decimal("100000.00"),
                "max_loan_amount": None,
                "loan_currency": "TZS",
                "repayment_options": [
                    {"code": "LUMP_SUM", "label": "Lump-sum repayment", "enabled": True},
                    {"code": "PAYMENT_SCHEDULE", "label": "Payment schedule", "enabled": True},
                    {"code": "DEDUCT_FROM_BENEFIT", "label": "Deduct from benefit", "enabled": True},
                ],
                "auto_deduct_from_benefits": True,
                "effect_on_claim": "DEDUCT_BALANCE",
                "effect_on_surrender": "DEDUCT_BALANCE",
                "effect_on_maturity": "DEDUCT_BALANCE",
                "require_approval": False,
                "effective_from": EFFECTIVE_FROM,
                "effective_to": None,
                "is_active": True,
            },
        )

        interest_control, interest_control_created = upsert(
            OLLoanInterestControl,
            {"code": "STANDARD_ENDOWMENT_POLICY_LOAN_INTEREST"},
            {
                "name": "Standard Endowment Policy Loan Interest",
                "description": "Starter policy-loan interest configuration pending actuarial and governance approval.",
                "product": product,
                "plan": None,
                "interest_rate": Decimal("8.00000000"),
                "compounding_frequency": "ANNUAL",
                "interest_calculation_basis": "COMPOUND",
                "grace_period_days": 30,
                "penalty_interest_rate": Decimal("2.00000000"),
                "interest_suspension_rule": "SUSPEND_DURING_APPROVED_CLAIM_REVIEW",
                "capitalize_interest": True,
                "effective_from": EFFECTIVE_FROM,
                "effective_to": None,
                "is_active": True,
            },
        )

        registry_defaults = {
            "parameter_group": "LOAN_SETUP",
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
                "Seeded OL Loan Setup: "
                f"loan_system_created={loan_system_created}, "
                f"interest_control_created={interest_control_created}, "
                f"registry_contracts={len(REGISTRY_SEEDS)}."
            )
        )
