from datetime import date
from decimal import Decimal

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.ol_parameters.models import (
    OLCommissionRateType,
    OLComputationApproach as ParameterComputationApproach,
    OLInvestmentFund,
    OLInvestmentFundRiskProfile,
    OLInvestmentFundType,
    OLMaturityClaimSetup,
    OLOverrideCommissionSetup,
    OLPremiumRateRow,
    OLPremiumRateTable,
    OLRiderRateRow,
    OLRiderRateTable,
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
from apps.partner_onboarding.models import Branch, Location
from apps.partners.models import Partner, PartnerType, PartnerTypeAssignment


SEED_COMMANDS = (
    "seed_ol_parameters_release",
    "seed_ordinary_life_reference_data",
    "seed_ol_quotations",
)
EFFECTIVE_FROM = date(2026, 1, 1)


class Command(BaseCommand):
    help = (
        "Seed a complete, idempotent Zanzibar Insurance Ordinary Life demo dataset "
        "for parameter dropdowns and quotation-wizard testing without flushing data."
    )

    def _seed_demo_locations(self):
        """Create the canonical Zanzibar location master data used by quotations.

        Location is shared onboarding master data, not an OL-specific lookup. The
        records are deliberately maintained here as part of the official demo seed
        so a fresh environment and an existing environment converge idempotently.
        """
        branches = {
            "ZIC-ZNZ": ("ZIC Zanzibar Main Branch", [
                ("ZIC-MALINDI", "Malindi"),
                ("ZIC-STONE-TOWN", "Stone Town"),
                ("ZIC-MWANAKWEREKWE", "Mwanakwerekwe"),
                ("ZIC-MAGOMENI", "Magomeni"),
                ("ZIC-MICHENZANI", "Michenzani"),
            ]),
            "ZIC-UNGUJA-NORTH": ("ZIC Unguja North Branch", [
                ("ZIC-KIWENGWA", "Kiwengwa"),
                ("ZIC-MKOKOTONI", "Mkokotoni"),
                ("ZIC-NUNGWI", "Nungwi"),
                ("ZIC-MATEMWE", "Matemwe"),
            ]),
            "ZIC-UNGUJA-SOUTH": ("ZIC Unguja South Branch", [
                ("ZIC-KIZIMKAZI", "Kizimkazi"),
                ("ZIC-JAMBIANI", "Jambiani"),
                ("ZIC-MAKUNDUCHI", "Makunduchi"),
                ("ZIC-FUONI", "Fuoni"),
            ]),
            "ZIC-PEMBA": ("ZIC Pemba Branch", [
                ("ZIC-CHAKE-CHAKE", "Chake Chake"),
                ("ZIC-MKOANI", "Mkoani"),
                ("ZIC-WETE", "Wete"),
                ("ZIC-MICHEWENI", "Micheweni"),
            ]),
        }
        seeded_locations = 0
        for branch_code, (branch_name, locations) in branches.items():
            branch, _ = Branch.objects.update_or_create(
                code=branch_code,
                defaults={"name": branch_name, "is_active": True},
            )
            for location_code, location_name in locations:
                Location.objects.update_or_create(
                    branch=branch,
                    code=location_code.upper(),
                    defaults={"name": location_name, "is_active": True},
                )
                seeded_locations += 1
        return seeded_locations

    def _seed_demo_agent(self):
        agent_type, _ = PartnerType.objects.update_or_create(
            code="AGENT",
            defaults={
                "name": "Insurance Agent",
                "description": "Active agent type used by Zanzibar Insurance OL quotation demos.",
                "is_active": True,
            },
        )
        agent, _ = Partner.objects.update_or_create(
            partner_number="ZIC-AGENT-0001",
            defaults={
                "partner_type": "AGENT",
                "partner_category": "INDIVIDUAL",
                "party_type": "INDIVIDUAL",
                "legal_name": "Asha Salim Insurance Agency",
                "status": "ACTIVE",
                "is_active": True,
                "identification_type": "NATIONAL_ID",
                "identification_number": "19900101-00001-00001-01",
                "national_id": "19900101-00001-00001-01",
                "title": "MS",
                "first_name": "Asha",
                "surname": "Salim",
                "gender": "FEMALE",
                "date_of_birth": date(1990, 1, 1),
                "nationality": "Tanzanian",
                "email": "asha.salim.agent@zic.co.tz",
                "phone": "+255242000001",
                "telephone_number": "+255242000001",
                "mobile_number": "+255712000001",
                "physical_address": "Malindi, Zanzibar, Tanzania",
                "postal_address": "P.O. Box 1234, Zanzibar, Tanzania",
                "political_risk": "LOW",
                "aml_risk": "LOW",
                "activated_at": timezone.now(),
            },
        )
        PartnerTypeAssignment.objects.update_or_create(
            partner=agent,
            partner_type=agent_type,
            defaults={
                "status": "ACTIVE",
                "effective_date": EFFECTIVE_FROM,
                "share_data_externally": False,
            },
        )
        return agent

    @transaction.atomic
    def handle(self, *args, **options):
        for command_name in SEED_COMMANDS:
            self.stdout.write(f"Running {command_name}...")
            call_command(command_name, verbosity=0)

        seeded_locations = self._seed_demo_locations()
        self.stdout.write(f"Seeded {seeded_locations} canonical Zanzibar locations.")
        agent = self._seed_demo_agent()

        for code, name, area, basis, formula, sequence, configuration in [
            (
                "ZIC_PREMIUM_CALCULATION",
                "ZIC Premium Calculation",
                "PREMIUM",
                "RATE_PER_SUM_ASSURED",
                "OL_BASE_PREMIUM_V1",
                1,
                {"rounding": "HALF_UP", "decimal_places": 2, "currency": "TZS"},
            ),
            (
                "ZIC_RIDER_CALCULATION",
                "ZIC Rider Calculation",
                "RIDER",
                "RATE_PER_SUM_ASSURED",
                "OL_RIDER_PREMIUM_V1",
                2,
                {"rounding": "HALF_UP", "decimal_places": 2, "currency": "TZS"},
            ),
            (
                "ZIC_TAX_CALCULATION",
                "ZIC Tax Calculation",
                "TAX",
                "SEQUENTIAL",
                "OL_PLAN_TAX_V1",
                3,
                {"sequence": "configured", "rounding": "HALF_UP", "decimal_places": 2},
            ),
            (
                "ZIC_PROJECTION_CALCULATION",
                "ZIC Projection Calculation",
                "PROJECTION",
                "POLICY_YEAR",
                "OL_VALUE_PROJECTION_V1",
                4,
                {"bonus_basis": "PER_MILLE", "currency": "TZS"},
            ),
        ]:
            ParameterComputationApproach.objects.update_or_create(
                code=code,
                defaults={
                    "name": name,
                    "description": f"Zanzibar Insurance {name.lower()} configuration.",
                    "calculation_area": area,
                    "calculation_basis": basis,
                    "formula_key": formula,
                    "sequence": sequence,
                    "configuration": configuration,
                    "effective_from": EFFECTIVE_FROM,
                    "effective_to": None,
                    "is_active": True,
                },
            )

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
                    "premium_frequencies": ["MONTHLY", "QUARTERLY", "SEMI_ANNUALLY", "ANNUALLY"],
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
                    "payment_frequencies": ["MONTHLY", "QUARTERLY", "SEMI_ANNUALLY", "ANNUALLY"],
                    "calculation_approach": computation,
                    "underwriting_rules": {
                        "medical_threshold_tzs": 100000000,
                        "automatic_acceptance": False,
                        "resident_country": "TANZANIA",
                    },
                    "servicing_rules": {
                        "grace_period_days": 30,
                        "reinstatement_window_months": 12,
                        "investment_linked": investment_linked,
                        "requires_investment_funds": investment_linked,
                        "allow_riders": True,
                        "allow_loans": True,
                        "allow_withdrawals": True,
                        "allow_surrender": True,
                        "allow_paidup": True,
                        "allow_bonus": allow_bonus,
                        "personal_accident": True,
                        "premium_waiver": True,
                    },
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

                premium_table, _ = OLPremiumRateTable.objects.update_or_create(
                    table_code=f"ZIC_{plan_code}_PREMIUM",
                    version="1.0",
                    defaults={
                        "name": f"{plan_name} Premium Rates",
                        "description": f"Zanzibar Insurance starter premium rates for {plan_name}.",
                        "product": parameter_products[code],
                        "plan": plan,
                        "rating_basis": "AGE_TERM",
                        "currency": "TZS",
                        "effective_from": EFFECTIVE_FROM,
                        "effective_to": None,
                        "is_active": True,
                    },
                )
                for gender in ("MALE", "FEMALE", "OTHER"):
                    for smoker_status in ("NON_SMOKER", "SMOKER"):
                        for frequency in ("MONTHLY", "QUARTERLY", "SEMI_ANNUALLY", "ANNUALLY"):
                            for min_age, max_age, min_term, max_term, rate in [
                                (18, 35, 5, 30, Decimal("1.20000000")),
                                (36, 50, 5, 25, Decimal("2.10000000")),
                                (51, 65, 5, 15, Decimal("4.50000000")),
                            ]:
                                OLPremiumRateRow.objects.update_or_create(
                                    code=(
                                        f"ZIC_{plan_code}_{gender}_{smoker_status}_{frequency}_"
                                        f"{min_age}_{max_age}_{min_term}_{max_term}"
                                    ),
                                    defaults={
                                        "table": premium_table,
                                        "name": f"{plan_name} {gender} {smoker_status} {frequency} {min_age}-{max_age}",
                                        "gender": gender,
                                        "smoker_status": smoker_status,
                                        "age_from": min_age,
                                        "age_to": max_age,
                                        "term_from": min_term,
                                        "term_to": max_term,
                                        "frequency": frequency,
                                        "sum_assured_band_from": None,
                                        "sum_assured_band_to": None,
                                        "rate": rate,
                                        "rate_unit": "PER_THOUSAND_SUM_ASSURED",
                                        "effective_from": EFFECTIVE_FROM,
                                        "effective_to": None,
                                        "is_active": True,
                                    },
                                )

        term_product = operational_products["OL_TERM_LIFE"]
        term_plan = OLPlan.objects.get(product_version__product=term_product, code="OL_TERM_STANDARD")
        linked_product = operational_products["OL_INVESTMENT_LINKED"]
        linked_plan = OLPlan.objects.get(product_version__product=linked_product, code="OL_JENGA_BALANCED")

        OLMaturityClaimSetup.objects.update_or_create(
            code="ZIC_TERM_MATURITY_CLAIM",
            defaults={
                "name": "ZIC Term Maturity Claim Setup",
                "description": "Automatic maturity workflow for eligible Zanzibar Insurance plans.",
                "product": term_product,
                "plan": term_plan,
                "auto_create_maturity_claim": True,
                "days_before_maturity_to_initiate": 30,
                "notification_days": 14,
                "default_payout_method": "BANK_TRANSFER",
                "require_documents": True,
                "require_approval": True,
                "maturity_claim_status_to_create": "REPORTED",
                "effective_from": EFFECTIVE_FROM,
                "effective_to": None,
                "is_active": True,
            },
        )
        OLMaturityClaimSetup.objects.update_or_create(
            code="ZIC_LINKED_MATURITY_CLAIM",
            defaults={
                "name": "ZIC Investment Maturity Claim Setup",
                "description": "Maturity workflow for investment-linked Zanzibar Insurance plans.",
                "product": linked_product,
                "plan": linked_plan,
                "auto_create_maturity_claim": True,
                "days_before_maturity_to_initiate": 45,
                "notification_days": 21,
                "default_payout_method": "BANK_TRANSFER",
                "require_documents": True,
                "require_approval": False,
                "maturity_claim_status_to_create": "REPORTED",
                "effective_from": EFFECTIVE_FROM,
                "effective_to": None,
                "is_active": True,
            },
        )
        OLOverrideCommissionSetup.objects.update_or_create(
            code="ZIC_AGENT_TERM_OVERRIDE",
            defaults={
                "name": "ZIC Agent Term Override",
                "description": "Demo agent commission override for term assurance.",
                "partner": agent,
                "intermediary_type": "AGENT",
                "product": term_product,
                "plan": term_plan,
                "channel": "AGENCY",
                "currency": "TZS",
                "rate_type": OLCommissionRateType.PERCENTAGE,
                "rate_value": Decimal("2.50000000"),
                "priority": 10,
                "reason": "Zanzibar Insurance OL demo distribution setup.",
                "effective_from": EFFECTIVE_FROM,
                "effective_to": None,
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

        rider_rate_specs = {
            "ZIC_ACCIDENTAL_DEATH_RIDER": Decimal("0.50000000"),
            "ZIC_PREMIUM_WAIVER_RIDER": Decimal("0.30000000"),
        }
        for rider_code, rider_rate in rider_rate_specs.items():
            for product_code, parameter_product in parameter_products.items():
                rider = OLRiderSetup.objects.get(code=f"{rider_code}_{product_code}")
                rider_table, _ = OLRiderRateTable.objects.update_or_create(
                    table_code=f"ZIC_{rider_code}_{product_code}_RATES",
                    version="1.0",
                    defaults={
                        "name": f"{rider.name} Rates - {product_code}",
                        "description": f"Zanzibar Insurance starter rates for {rider.name}.",
                        "rider": rider,
                        "product": parameter_product,
                        "plan": None,
                        "rating_basis": "AGE_TERM",
                        "effective_from": EFFECTIVE_FROM,
                        "effective_to": None,
                        "is_active": True,
                    },
                )
                for gender in ("MALE", "FEMALE", "OTHER"):
                    for smoker_status in ("NON_SMOKER", "SMOKER"):
                        for frequency in ("MONTHLY", "QUARTERLY", "SEMI_ANNUALLY", "ANNUALLY"):
                            for min_age, max_age, min_term, max_term in [
                                (18, 35, 5, 30),
                                (36, 50, 5, 25),
                                (51, 65, 5, 15),
                            ]:
                                OLRiderRateRow.objects.update_or_create(
                                    code=(
                                        f"ZIC_{rider_code}_{product_code}_{gender}_{smoker_status}_"
                                        f"{frequency}_{min_age}_{max_age}_{min_term}_{max_term}"
                                    ),
                                    defaults={
                                        "table": rider_table,
                                        "name": f"{rider.name} {gender} {smoker_status} {frequency} {min_age}-{max_age}",
                                        "gender": gender,
                                        "smoker_status": smoker_status,
                                        "age_from": min_age,
                                        "age_to": max_age,
                                        "term_from": min_term,
                                        "term_to": max_term,
                                        "frequency": frequency,
                                        "sum_assured_band_from": None,
                                        "sum_assured_band_to": None,
                                        "rate": rider_rate,
                                        "rate_unit": "PER_THOUSAND_SUM_ASSURED",
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
        self.stdout.write("Seeded all OL parameter groups, four calculation approaches, maturity and commission setups, 3 operational products, 6 plans, rating bands, riders, and 3 investment funds.")
        self.stdout.write("Existing records were updated in place; no database flush or destructive reset was performed.")
