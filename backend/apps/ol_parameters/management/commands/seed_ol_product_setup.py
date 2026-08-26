from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.ol_parameters.models import (
    OLInvestmentFund,
    OLInvestmentFundType,
    OLParameterTableRegistry,
    OLPlanOccupationRiskLimit,
    OLPlanRiskCategory,
    OLPlanTargetMarket,
    OLPlanTaxConfiguration,
    OLPlanType,
    OLProduct,
)


EFFECTIVE_FROM = date(2026, 1, 1)


REGISTRY_SEEDS = [
    {
        "slug": "plan-types",
        "label": "OL Plan Types",
        "description": "Plan-category catalog used to classify Ordinary Life products.",
        "model_label": "ol_parameters.OLPlanType",
        "visible_columns": ["code", "name", "plan_category", "is_active"],
        "searchable_fields": ["code", "name", "description", "plan_category"],
        "filter_fields": ["is_active", "plan_category"],
        "default_ordering": ["name", "code"],
    },
    {
        "slug": "products",
        "label": "OL Products",
        "description": "Table-driven Ordinary Life product contracts for quotation, proposal, and policy workflows.",
        "model_label": "ol_parameters.OLProduct",
        "visible_columns": ["code", "name", "plan_type", "insurance_class", "currency", "min_entry_age", "max_entry_age", "is_active"],
        "searchable_fields": ["code", "name", "description", "currency", "insurance_class"],
        "filter_fields": ["is_active", "plan_type", "insurance_class", "currency", "investment_linked", "effective_from", "effective_to"],
        "default_ordering": ["name", "code"],
    },
    {
        "slug": "plan-tax-configurations",
        "label": "Plan Tax Configurations",
        "description": "Ordered, effective-dated tax components scoped to a product or operational plan.",
        "model_label": "ol_parameters.OLPlanTaxConfiguration",
        "visible_columns": ["code", "name", "product", "plan", "tax_type", "tax_basis", "rate_type", "rate_value", "apply_on", "sequence", "is_active"],
        "searchable_fields": ["code", "name", "description", "tax_type", "tax_basis", "apply_on", "country_or_branch"],
        "filter_fields": ["is_active", "product", "plan", "tax_type", "tax_basis", "rate_type", "sequence", "country_or_branch", "effective_from", "effective_to"],
        "default_ordering": ["product", "plan", "sequence", "code"],
    },
    {
        "slug": "plan-target-markets",
        "label": "Plan Target Markets",
        "description": "Target-market eligibility rows scoped to a product or operational plan.",
        "model_label": "ol_parameters.OLPlanTargetMarket",
        "visible_columns": ["code", "name", "product", "plan", "target_market_type", "min_age", "max_age", "residency_requirement", "is_active"],
        "searchable_fields": ["code", "name", "description", "target_market_type", "residency_requirement"],
        "filter_fields": ["is_active", "product", "plan", "target_market_type", "residency_requirement", "effective_from", "effective_to"],
        "default_ordering": ["product", "plan", "target_market_type", "code"],
    },
    {
        "slug": "plan-risk-categories",
        "label": "Plan Risk Categories",
        "description": "Underwriting class and loading-basis configuration by product, plan, or global scope.",
        "model_label": "ol_parameters.OLPlanRiskCategory",
        "visible_columns": ["code", "name", "product", "plan", "underwriting_class", "loading_basis", "is_active"],
        "searchable_fields": ["code", "name", "description", "underwriting_class", "loading_basis"],
        "filter_fields": ["is_active", "product", "plan", "underwriting_class", "loading_basis", "effective_from", "effective_to"],
        "default_ordering": ["product", "plan", "underwriting_class", "code"],
    },
    {
        "slug": "plan-occupation-risk-limits",
        "label": "Plan Occupation Risk Limits",
        "description": "Occupation risk category limits, loadings, exclusions, and effective dates.",
        "model_label": "ol_parameters.OLPlanOccupationRiskLimit",
        "visible_columns": ["code", "name", "product", "plan", "occupation_risk_category", "max_sum_assured", "loading_rate", "exclusion_flag", "is_active"],
        "searchable_fields": ["code", "name", "description", "occupation_risk_category"],
        "filter_fields": ["is_active", "product", "plan", "occupation_risk_category", "exclusion_flag", "effective_from", "effective_to"],
        "default_ordering": ["product", "plan", "occupation_risk_category", "code"],
    },
    {
        "slug": "investment-fund-types",
        "label": "Investment Fund Types",
        "description": "Investment fund risk-profile catalog for investment-linked Ordinary Life products.",
        "model_label": "ol_parameters.OLInvestmentFundType",
        "visible_columns": ["code", "name", "risk_profile", "is_active"],
        "searchable_fields": ["code", "name", "description", "risk_profile"],
        "filter_fields": ["is_active", "risk_profile"],
        "default_ordering": ["name", "code"],
    },
    {
        "slug": "investment-funds",
        "label": "Investment Funds",
        "description": "Effective-dated investment fund catalog with valuation and allocation metadata.",
        "model_label": "ol_parameters.OLInvestmentFund",
        "visible_columns": ["code", "name", "fund_type", "currency", "valuation_frequency", "unit_price", "is_active"],
        "searchable_fields": ["code", "name", "description", "currency", "valuation_frequency"],
        "filter_fields": ["is_active", "fund_type", "currency", "valuation_frequency", "effective_from", "effective_to"],
        "default_ordering": ["name", "code"],
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
    help = "Seed idempotent OL Product Setup catalogs, configuration, and table registry contracts."

    @transaction.atomic
    def handle(self, *args, **options):
        created = 0
        updated = 0

        for code, name, description, category in (
            ("ENDOWMENT", "Endowment", "Savings-oriented Ordinary Life plan with maturity benefit.", "INDIVIDUAL"),
            ("WHOLE_LIFE", "Whole Life", "Whole-life protection plan category.", "INDIVIDUAL"),
            ("TERM_LIFE", "Term Life", "Term protection plan category.", "INDIVIDUAL"),
            ("EDUCATION", "Education", "Education-focused savings and protection plan category.", "INDIVIDUAL"),
            ("PENSION_LINKED", "Pension-linked", "Pension-linked Ordinary Life plan category.", "INDIVIDUAL"),
            ("CREDIT_LINKED", "Credit-linked", "Credit-linked protection plan category.", "CREDIT"),
        ):
            _, was_created = upsert(
                OLPlanType,
                {"code": code},
                {
                    "name": name,
                    "description": description,
                    "plan_category": category,
                    "effective_from": EFFECTIVE_FROM,
                    "is_active": True,
                },
            )
            created += int(was_created)
            updated += int(not was_created)

        plan_type = OLPlanType.objects.get(code="ENDOWMENT")
        product, was_created = upsert(
            OLProduct,
            {"code": "STANDARD_ENDOWMENT"},
            {
                "name": "Standard Endowment",
                "description": "Starter Ordinary Life endowment product contract for development and configuration testing.",
                "plan_type": plan_type,
                "insurance_class": "INDIVIDUAL",
                "currency": "TZS",
                "min_entry_age": 18,
                "max_entry_age": 65,
                "min_term": 5,
                "max_term": 30,
                "min_sum_assured": Decimal("1000000.00"),
                "max_sum_assured": Decimal("1000000000.00"),
                "premium_frequencies": ["MONTHLY", "QUARTERLY", "SEMI_ANNUALLY", "ANNUALLY"],
                "allow_riders": True,
                "allow_loans": True,
                "allow_withdrawals": False,
                "allow_surrender": True,
                "allow_paidup": True,
                "allow_bonus": True,
                "investment_linked": False,
                "effective_from": EFFECTIVE_FROM,
                "is_active": True,
            },
        )
        created += int(was_created)
        updated += int(not was_created)

        starter_rows = [
            (
                OLPlanTaxConfiguration,
                {"code": "STANDARD_ENDOWMENT_STAMP_DUTY"},
                {
                    "name": "Standard Endowment Stamp Duty",
                    "description": "Starter stamp duty tax component for the standard endowment product.",
                    "product": product,
                    "plan": None,
                    "tax_type": "STAMP_DUTY",
                    "tax_basis": "PREMIUM",
                    "rate_type": "PERCENTAGE",
                    "rate_value": Decimal("0.000000"),
                    "apply_on": "PREMIUM_RECEIPT",
                    "sequence": 1,
                    "country_or_branch": "TZ",
                    "effective_from": EFFECTIVE_FROM,
                    "is_active": True,
                },
            ),
            (
                OLPlanTargetMarket,
                {"code": "STANDARD_ENDOWMENT_TZ_RESIDENTS"},
                {
                    "name": "Tanzania Resident Endowment Market",
                    "description": "Starter target-market rule for residents within the standard age range.",
                    "product": product,
                    "plan": None,
                    "target_market_type": "INDIVIDUAL_RESIDENT",
                    "min_age": 18,
                    "max_age": 65,
                    "occupation_categories": [],
                    "residency_requirement": "TZ_RESIDENT",
                    "effective_from": EFFECTIVE_FROM,
                    "is_active": True,
                },
            ),
            (
                OLPlanRiskCategory,
                {"code": "STANDARD_ENDOWMENT_STANDARD_RISK"},
                {
                    "name": "Standard Endowment Standard Risk",
                    "description": "Starter standard underwriting risk class for the standard endowment product.",
                    "product": product,
                    "plan": None,
                    "underwriting_class": "STANDARD",
                    "loading_basis": "NO_LOADING",
                    "effective_from": EFFECTIVE_FROM,
                    "is_active": True,
                },
            ),
            (
                OLPlanOccupationRiskLimit,
                {"code": "STANDARD_ENDOWMENT_MANUAL_RISK"},
                {
                    "name": "Standard Endowment Manual Risk Limit",
                    "description": "Starter occupation risk limit; replace with approved underwriting parameters before production use.",
                    "product": product,
                    "plan": None,
                    "occupation_risk_category": "MANUAL_RISK",
                    "max_sum_assured": Decimal("500000000.00"),
                    "loading_rate": Decimal("0.000000"),
                    "exclusion_flag": False,
                    "effective_from": EFFECTIVE_FROM,
                    "is_active": True,
                },
            ),
        ]
        for model, lookup, defaults in starter_rows:
            _, was_created = upsert(model, lookup, defaults)
            created += int(was_created)
            updated += int(not was_created)

        for code, name, risk_profile, description in (
            ("CONSERVATIVE", "Conservative Fund", "CONSERVATIVE", "Capital-preservation investment fund profile."),
            ("MODERATE", "Moderate Fund", "MODERATE", "Balanced investment fund profile."),
            ("AGGRESSIVE", "Aggressive Fund", "AGGRESSIVE", "Growth-oriented investment fund profile."),
        ):
            _, was_created = upsert(
                OLInvestmentFundType,
                {"code": code},
                {
                    "name": name,
                    "description": description,
                    "risk_profile": risk_profile,
                    "effective_from": EFFECTIVE_FROM,
                    "is_active": True,
                },
            )
            created += int(was_created)
            updated += int(not was_created)

        fund_type = OLInvestmentFundType.objects.get(code="MODERATE")
        _, was_created = upsert(
            OLInvestmentFund,
            {"code": "STANDARD_BALANCED_FUND"},
            {
                "name": "Standard Balanced Fund",
                "description": "Starter balanced investment fund catalog row for investment-linked product configuration.",
                "fund_type": fund_type,
                "currency": "TZS",
                "valuation_frequency": "DAILY",
                "unit_price": Decimal("100.000000"),
                "allocation_rules": {"default_allocation_percent": 100, "minimum_allocation_percent": 0, "maximum_allocation_percent": 100},
                "effective_from": EFFECTIVE_FROM,
                "is_active": True,
            },
        )
        created += int(was_created)
        updated += int(not was_created)

        for registry_seed in REGISTRY_SEEDS:
            defaults = {
                **registry_seed,
                "parameter_group": "Product Setup",
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
            created += int(was_created)
            updated += int(not was_created)

        self.stdout.write(
            self.style.SUCCESS(
                f"OL Product Setup seed complete: {created} created, {updated} updated, {len(REGISTRY_SEEDS)} registry tables maintained."
            )
        )
