from datetime import date
from decimal import Decimal

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.ol_parameters.models import (
    OLInvestmentFund,
    OLInvestmentFundRiskProfile,
    OLInvestmentFundType,
    OLProduct as ParameterProduct,
    OLPlanType,
    OLRiderSetup,
)
from apps.ordinary_life.models import (
    OLComputationApproach,
    OLPlan,
    OLProduct,
    OLProductVersion,
    OLRateBand,
)


SEED_COMMANDS = (
    "seed_ol_parameters_release",
    "seed_ordinary_life_reference_data",
)
EFFECTIVE_FROM = date(2026, 1, 1)


class Command(BaseCommand):
    help = (
        "Seed a complete, idempotent Zanzibar Insurance Ordinary Life demo dataset "
        "for parameter dropdowns and quotation-wizard testing without flushing data."
    )

    @transaction.atomic
    def handle(self, *args, **options):
        for command_name in SEED_COMMANDS:
            self.stdout.write(f"Running {command_name}...")
            call_command(command_name, verbosity=0)

        computation, _ = OLComputationApproach.objects.update_or_create(
            code="LEVEL_PREMIUM",
            defaults={
                "name": "Level premium",
                "description": "Level premium calculation for the Zanzibar demo products.",
                "is_active": True,
            },
        )

        term_type, _ = OLPlanType.objects.update_or_create(
            code="TERM_LIFE",
            defaults={"name": "Term Life", "plan_category": "INDIVIDUAL", "is_active": True},
        )
        savings_type, _ = OLPlanType.objects.update_or_create(
            code="EDUCATION_SAVINGS",
            defaults={"name": "Education Savings", "plan_category": "INDIVIDUAL", "is_active": True},
        )
        linked_type, _ = OLPlanType.objects.update_or_create(
            code="INVESTMENT_LINKED",
            defaults={"name": "Investment Linked", "plan_category": "INDIVIDUAL", "is_active": True},
        )

        parameter_products = {}
        for code, name, plan_type, investment_linked, allow_bonus in [
            ("OL_TERM_LIFE", "ZIC Ordinary Life Term Assurance", term_type, False, False),
            ("OL_EDUCATION_SAVINGS", "ZIC Elimu Bora Education Plan", savings_type, False, True),
            ("OL_INVESTMENT_LINKED", "ZIC Jenga Kesho Investment Plan", linked_type, True, True),
        ]:
            parameter_products[code], _ = ParameterProduct.objects.update_or_create(
                code=code,
                defaults={
                    "name": name,
                    "description": f"Zanzibar Insurance Company {name} demo product.",
                    "plan_type": plan_type,
                    "insurance_class": "INDIVIDUAL",
                    "currency": "TZS",
                    "min_entry_age": 18,
                    "max_entry_age": 65,
                    "min_term": 5,
                    "max_term": 30,
                    "min_sum_assured": Decimal("1000000.00"),
                    "max_sum_assured": Decimal("500000000.00"),
                    "premium_frequencies": ["MONTHLY", "QUARTERLY", "SEMI_ANNUAL", "ANNUAL"],
                    "allow_riders": True,
                    "allow_loans": True,
                    "allow_withdrawals": investment_linked,
                    "allow_surrender": True,
                    "allow_paidup": True,
                    "allow_bonus": allow_bonus,
                    "investment_linked": investment_linked,
                    "effective_from": EFFECTIVE_FROM,
                    "effective_to": None,
                    "is_active": True,
                },
            )

        operational_products = {}
        for code, name, description, product_type, currency in [
            (
                "OL_TERM_LIFE",
                "ZIC Ordinary Life Term Assurance",
                "Affordable level-premium protection for families, professionals, and small businesses.",
                "TERM_LIFE",
                "TZS",
            ),
            (
                "OL_EDUCATION_SAVINGS",
                "ZIC Elimu Bora Education Plan",
                "Protection and savings support for school and university milestones.",
                "ENDOWMENT",
                "TZS",
            ),
            (
                "OL_INVESTMENT_LINKED",
                "ZIC Jenga Kesho Investment Plan",
                "Flexible investment-linked protection with selectable managed funds.",
                "INVESTMENT_LINKED",
                "TZS",
            ),
        ]:
            product, _ = OLProduct.objects.update_or_create(
                code=code,
                defaults={
                    "name": name,
                    "description": description,
                    "business_area": "ORDINARY_LIFE",
                    "min_age": 18,
                    "max_age": 65,
                    "term_length_years": 20,
                    "is_active": True,
                },
            )
            operational_products[code] = product

            version, _ = OLProductVersion.objects.update_or_create(
                product=product,
                version_number=1,
                defaults={
                    "effective_from": EFFECTIVE_FROM,
                    "effective_to": None,
                    "currency": currency,
                    "min_entry_age": 18,
                    "max_entry_age": 65,
                    "min_term_years": 5,
                    "max_term_years": 30,
                    "payment_frequencies": ["MONTHLY", "QUARTERLY", "SEMI_ANNUAL", "ANNUAL"],
                    "calculation_approach": computation,
                    "underwriting_rules": {
                        "medical_threshold_tzs": 100000000,
                        "automatic_acceptance": False,
                        "resident_country": "TANZANIA",
                    },
                    "servicing_rules": {"grace_period_days": 30, "reinstatement_window_months": 12},
                    "snapshot": {"seed_key": f"ZIC_{code}_V1", "currency": currency},
                    "is_active": True,
                },
            )

            plan_rows = {
                "OL_TERM_LIFE": [
                    ("OL_TERM_STANDARD", "ZIC Term Assurance Standard", "Core death protection for individual lives.", "1000000.00", "500000000.00"),
                    ("OL_TERM_FAMILY", "ZIC Term Assurance Family", "Family-focused protection with flexible payment options.", "500000.00", "250000000.00"),
                ],
                "OL_EDUCATION_SAVINGS": [
                    ("OL_EDU_GROWTH", "Elimu Bora Growth Plan", "Education savings with protection and maturity benefit.", "5000000.00", "300000000.00"),
                    ("OL_EDU_PREMIER", "Elimu Bora Premier Plan", "Higher-benefit education and family protection plan.", "10000000.00", "500000000.00"),
                ],
                "OL_INVESTMENT_LINKED": [
                    ("OL_JENGA_BALANCED", "Jenga Kesho Balanced", "Investment-linked plan using balanced managed funds.", "1000000.00", "500000000.00"),
                    ("OL_JENGA_FLEX", "Jenga Kesho Flexible", "Investment-linked plan with flexible fund allocation.", "500000.00", "250000000.00"),
                ],
            }
            for plan_code, plan_name, plan_description, minimum, maximum in plan_rows[code]:
                plan, _ = OLPlan.objects.update_or_create(
                    product_version=version,
                    code=plan_code,
                    defaults={
                        "name": plan_name,
                        "description": plan_description,
                        "minimum_sum_assured": Decimal(minimum),
                        "maximum_sum_assured": Decimal(maximum),
                        "is_active": True,
                    },
                )
                for min_age, max_age, min_term, max_term, rate in [
                    (18, 35, 5, 30, Decimal("0.00120000")),
                    (36, 50, 5, 25, Decimal("0.00210000")),
                    (51, 65, 5, 15, Decimal("0.00450000")),
                ]:
                    OLRateBand.objects.update_or_create(
                        product_version=version,
                        plan=plan,
                        min_age=min_age,
                        max_age=max_age,
                        min_term_years=min_term,
                        max_term_years=max_term,
                        defaults={
                            "rate": rate,
                            "assumptions": {"basis": "ZIC_DEMO_ACTUARIAL_STARTER_RATE", "currency": "TZS"},
                            "is_active": True,
                        },
                    )

        # Product-scoped rider records make PA and premium-waiver selections visible.
        rider_rows = [
            (
                "ZIC_ACCIDENTAL_DEATH_RIDER",
                "ZIC Accidental Death Rider",
                "ACCIDENT",
                "ACCIDENTAL_DEATH",
                "SUM_ASSURED",
                18,
                60,
                5,
                30,
                False,
                True,
            ),
            (
                "ZIC_PREMIUM_WAIVER_RIDER",
                "ZIC Premium Waiver Rider",
                "WAIVER",
                "WAIVER_PREMIUM",
                "PREMIUM",
                18,
                55,
                5,
                30,
                False,
                True,
            ),
        ]
        for code, name, category, benefit_type, basis, min_age, max_age, min_term, max_term, standalone, underwriting in rider_rows:
            for product_code in operational_products:
                OLRiderSetup.objects.update_or_create(
                    code=f"{code}_{product_code}",
                    defaults={
                        "name": name,
                        "description": f"{name} available under {operational_products[product_code].name}.",
                        "rider_category": category,
                        "benefit_type": benefit_type,
                        "calculation_basis": basis,
                        "min_age": min_age,
                        "max_age": max_age,
                        "min_term": min_term,
                        "max_term": max_term,
                        "min_sum_assured": Decimal("1000000.00"),
                        "max_sum_assured": Decimal("500000000.00"),
                        "waiting_period_days": 30 if category == "ACCIDENT" else 0,
                        "allows_standalone": standalone,
                        "requires_underwriting": underwriting,
                        "exclusion_rules": {"country": "TANZANIA", "currency": "TZS"},
                        "product": parameter_products[product_code],
                        "plan": None,
                        "effective_from": EFFECTIVE_FROM,
                        "effective_to": None,
                        "is_active": True,
                    },
                )

        fund_types = {}
        for code, name, risk in [
            ("ZIC_FUND_MONEY_MARKET", "ZIC Money Market Fund", OLInvestmentFundRiskProfile.CONSERVATIVE),
            ("ZIC_FUND_BALANCED", "ZIC Balanced Fund", OLInvestmentFundRiskProfile.BALANCED),
            ("ZIC_FUND_EQUITY", "ZIC Equity Growth Fund", OLInvestmentFundRiskProfile.AGGRESSIVE),
        ]:
            fund_types[code], _ = OLInvestmentFundType.objects.update_or_create(
                code=code,
                defaults={"name": name, "description": f"ZIC managed fund: {name}.", "risk_profile": risk, "is_active": True},
            )

        for code, name, fund_type_code, price, frequency in [
            ("ZIC_MM_TZS", "ZIC Money Market Fund - TZS", "ZIC_FUND_MONEY_MARKET", "1.000000", "DAILY"),
            ("ZIC_BAL_TZS", "ZIC Balanced Fund - TZS", "ZIC_FUND_BALANCED", "1.250000", "DAILY"),
            ("ZIC_EQ_TZS", "ZIC Equity Growth Fund - TZS", "ZIC_FUND_EQUITY", "1.750000", "DAILY"),
        ]:
            OLInvestmentFund.objects.update_or_create(
                code=code,
                defaults={
                    "name": name,
                    "description": f"Zanzibar Insurance Company investment fund priced in Tanzanian Shillings.",
                    "fund_type": fund_types[fund_type_code],
                    "currency": "TZS",
                    "valuation_frequency": frequency,
                    "unit_price": Decimal(price),
                    "allocation_rules": {
                        "minimum_allocation_percent": 5,
                        "maximum_allocation_percent": 100,
                        "currency_conversion_allowed": False,
                        "eligible_products": ["OL_INVESTMENT_LINKED"],
                    },
                    "effective_from": EFFECTIVE_FROM,
                    "effective_to": None,
                    "is_active": True,
                },
            )

        self.stdout.write(self.style.SUCCESS("Zanzibar Insurance OL demo seed completed successfully."))
        self.stdout.write("Seeded all OL parameter groups, 3 operational products, 6 plans, rating bands, riders, and 3 investment funds.")
        self.stdout.write("Existing records were updated in place; no database flush or destructive reset was performed.")
