from datetime import date
from decimal import Decimal

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q

from apps.ol_parameters.models import (
    OLAgentCommissionSetup,
    OLAnticipatedEndowmentInstallmentRate,
    OLBeneficialType,
    OLBonusRate,
    OLCashSurrenderValue,
    OLClaimReason,
    OLClaimStatus,
    OLClaimType,
    OLCommitmentStatus,
    OLComputationApproach,
    OLCorrespondentType,
    OLDefaultSystemParameter,
    OLDischargeType,
    OLGracePeriod,
    OLGracePeriodNotificationSchedule,
    OLHealthQuestion,
    OLHealthQuestionnaire,
    OLHealthQuestionnaireItem,
    OLInstallmentChargeRate,
    OLInvestmentFund,
    OLInvestmentFundRiskProfile,
    OLInvestmentFundType,
    OLJointLifeSetup,
    OLLoanInterestControl,
    OLLoanSystemSetup,
    OLMaturityClaimSetup,
    OLMedicalCode,
    OLMedicalFacility,
    OLMedicalHistory,
    OLMedicalLimit,
    OLMedicalPractitioner,
    OLMemberCoverConfiguration,
    OLMortalityRateRow,
    OLMortalityRateTable,
    OLMortgageInterestFactor,
    OLOverrideCommissionSetup,
    OLPaidUpRate,
    OLPaidUpSetup,
    OLPlanOccupationRiskLimit,
    OLPlanRiskCategory,
    OLPlanTargetMarket,
    OLPlanTaxConfiguration,
    OLPlanType,
    OLPolicyRenewalStatus,
    OLPolicyStatus,
    OLPremiumRateRow,
    OLPremiumRateTable,
    OLProduct,
    OLReinstatementInterestRate,
    OLReinstatementWindow,
    OLReserveLoading,
    OLRiderRateRow,
    OLRiderRateTable,
    OLRiderSetup,
    OLSurrenderSetup,
    OLSurrenderValueRate,
)
from apps.ordinary_life.models import OLPlan
from apps.ordinary_life.models import OLProduct as OperationalProduct
from apps.partner_onboarding.models import Branch
from apps.partners.models import Partner

EFFECTIVE_FROM = date(2026, 1, 1)


class Command(BaseCommand):
    help = (
        "Seed the complete, production-shaped Zanzibar Insurance Company Ordinary Life "
        "master-data graph without flushing existing data."
    )

    REQUIRED_MODELS = (
        OLDefaultSystemParameter,
        OLOverrideCommissionSetup,
        OLAgentCommissionSetup,
        OLComputationApproach,
        OLMaturityClaimSetup,
        OLAnticipatedEndowmentInstallmentRate,
        OLGracePeriod,
        OLPolicyStatus,
        OLPolicyRenewalStatus,
        OLBeneficialType,
        OLMemberCoverConfiguration,
        OLSurrenderSetup,
        OLPaidUpSetup,
        OLSurrenderValueRate,
        OLPaidUpRate,
        OLCommitmentStatus,
        OLHealthQuestion,
        OLHealthQuestionnaire,
        OLHealthQuestionnaireItem,
        OLGracePeriodNotificationSchedule,
        OLPlanType,
        OLProduct,
        OLPlanTaxConfiguration,
        OLPlanTargetMarket,
        OLPlanRiskCategory,
        OLPlanOccupationRiskLimit,
        OLInvestmentFundType,
        OLInvestmentFund,
        OLPremiumRateTable,
        OLPremiumRateRow,
        OLMortalityRateTable,
        OLMortalityRateRow,
        OLJointLifeSetup,
        OLReinstatementInterestRate,
        OLBonusRate,
        OLMortgageInterestFactor,
        OLInstallmentChargeRate,
        OLCashSurrenderValue,
        OLReserveLoading,
        OLRiderSetup,
        OLRiderRateTable,
        OLRiderRateRow,
        OLLoanSystemSetup,
        OLLoanInterestControl,
        OLMedicalCode,
        OLMedicalLimit,
        OLMedicalHistory,
        OLMedicalFacility,
        OLMedicalPractitioner,
        OLClaimType,
        OLClaimReason,
        OLClaimStatus,
        OLDischargeType,
        OLCorrespondentType,
        OLReinstatementWindow,
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--verify-only",
            action="store_true",
            help="Do not mutate data; verify that the complete active OL graph exists.",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.created = 0
        self.updated = 0
        self.touched = {}

    def _upsert(self, model, lookup, defaults):
        obj, created = model.objects.update_or_create(defaults=defaults, **lookup)
        label = model._meta.label
        self.touched[label] = self.touched.get(label, 0) + 1
        if created:
            self.created += 1
        else:
            self.updated += 1
        return obj

    @staticmethod
    def _common(name, description):
        return {
            "name": name,
            "description": description,
            "effective_from": EFFECTIVE_FROM,
            "effective_to": None,
            "is_active": True,
        }

    def _seed_defaults_and_system(self):
        typed_defaults = [
            (
                "ZIC_DEFAULT_CURRENCY",
                "Default currency",
                "STRING",
                {"string_value": "TZS", "parameter_category": "QUOTATION"},
            ),
            (
                "ZIC_DEFAULT_GRACE_DAYS",
                "Default grace period",
                "INTEGER",
                {"integer_value": 30, "parameter_category": "POLICY"},
            ),
            (
                "ZIC_DEFAULT_MINIMUM_PREMIUM",
                "Minimum monthly premium",
                "DECIMAL",
                {"decimal_value": Decimal("25000.00"), "parameter_category": "PRICING"},
            ),
            (
                "ZIC_DEFAULT_AUTO_DEBIT",
                "Automatic premium debit default",
                "BOOLEAN",
                {"boolean_value": True, "parameter_category": "COLLECTION"},
            ),
            (
                "ZIC_DEFAULT_EFFECTIVE_DATE",
                "Current parameter effective date",
                "DATE",
                {"date_value": EFFECTIVE_FROM, "parameter_category": "SYSTEM"},
            ),
            (
                "ZIC_DEFAULT_ROUNDING_RULE",
                "Quotation rounding configuration",
                "JSON",
                {
                    "json_value": {"mode": "HALF_UP", "decimal_places": 2, "currency": "TZS"},
                    "parameter_category": "CALCULATION",
                },
            ),
        ]
        for code, name, value_type, extra in typed_defaults:
            defaults = self._common(name, f"Zanzibar Insurance Company OL {name.lower()}.")
            defaults.update({
                "parameter_key": code,
                "parameter_category": extra.pop("parameter_category"),
                "value_type": value_type,
                "string_value": None,
                "integer_value": None,
                "decimal_value": None,
                "boolean_value": None,
                "date_value": None,
                "json_value": None,
            })
            defaults.update(extra)
            self._upsert(OLDefaultSystemParameter, {"code": code}, defaults)

        for code, name, area, basis, formula, sequence, config in [
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
            (
                "ZIC_UW_CALCULATION",
                "ZIC Underwriting Calculation",
                "UNDERWRITING",
                "MEDICAL_AND_FINANCIAL_LIMITS",
                "OL_UW_RULES_V1",
                5,
                {"resident_country": "TANZANIA", "currency": "TZS"},
            ),
        ]:
            self._upsert(
                OLComputationApproach,
                {"code": code},
                {
                    **self._common(name, f"Zanzibar Insurance Company {name.lower()} configuration."),
                    "calculation_area": area,
                    "calculation_basis": basis,
                    "formula_key": formula,
                    "sequence": sequence,
                    "configuration": config,
                },
            )

        # Quotation numbering is owned by seed_ol_quotations, invoked by the
        # baseline Zanzibar seed above, so this command does not duplicate it.

    def _load_graph(self):
        products = {
            code: OLProduct.objects.get(code=code)
            for code in ("OL_TERM_LIFE", "OL_EDUCATION_SAVINGS", "OL_INVESTMENT_LINKED")
        }
        operational_products = {
            code: OperationalProduct.objects.get(code=code)
            for code in products
        }
        plans = {
            plan.code: plan
            for plan in OLPlan.objects.filter(product_version__product__code__in=products).select_related(
                "product_version__product"
            )
        }
        if len(plans) < 6:
            raise CommandError("The baseline OL seed did not create all six quotation-ready plans.")
        branches = {branch.code: branch for branch in Branch.objects.filter(is_active=True)}
        branch = branches.get("ZIC-ZNZ") or next(iter(branches.values()), None)
        if branch is None:
            raise CommandError("No active Zanzibar branch is available for OL master data.")
        agent = Partner.objects.filter(partner_number="ZIC-AGENT-0001", is_active=True).first()
        if agent is None:
            raise CommandError("The baseline OL seed did not create the demo agent partner.")
        return products, operational_products, plans, branch, agent

    def _seed_policy_setup(self, products, operational_products, plans):
        policy_statuses = [
            ("ZIC_POLICY_QUOTE", "Quotation", 10, False, "INFO", ["ZIC_POLICY_PROPOSAL"]),
            ("ZIC_POLICY_PROPOSAL", "Proposal", 20, False, "PRIMARY", ["ZIC_POLICY_ACTIVE"]),
            ("ZIC_POLICY_ACTIVE", "Active", 30, False, "SUCCESS", ["ZIC_POLICY_LAPSED", "ZIC_POLICY_SURRENDERED"]),
            ("ZIC_POLICY_LAPSED", "Lapsed", 40, False, "WARNING", ["ZIC_POLICY_REINSTATED", "ZIC_POLICY_SURRENDERED"]),
            ("ZIC_POLICY_REINSTATED", "Reinstated", 50, False, "SUCCESS", ["ZIC_POLICY_ACTIVE"]),
            ("ZIC_POLICY_SURRENDERED", "Surrendered", 60, True, "NEUTRAL", []),
        ]
        # OLPolicyStatus validates transition targets against active catalog rows;
        # establish the nodes first, then add the edges in a second pass.
        for code, name, order, terminal, badge, _transitions in policy_statuses:
            self._upsert(
                OLPolicyStatus,
                {"code": code},
                {
                    **self._common(name, f"ZIC OL policy lifecycle status: {name}."),
                    "display_order": order,
                    "badge_type": badge,
                    "is_terminal": terminal,
                    "allowed_transitions": [],
                },
            )
        for code, _name, _order, _terminal, _badge, transitions in policy_statuses:
            self._upsert(OLPolicyStatus, {"code": code}, {"allowed_transitions": transitions})

        for code, name, order, action in [
            ("ZIC_RENEWAL_DUE", "Renewal due", 10, "GENERATE_RENEWAL_NOTICE"),
            ("ZIC_RENEWAL_OFFERED", "Renewal offered", 20, "AWAIT_PAYMENT"),
            ("ZIC_RENEWAL_ACCEPTED", "Renewal accepted", 30, "CREATE_RENEWAL"),
            ("ZIC_RENEWAL_DECLINED", "Renewal declined", 40, "CLOSE_RENEWAL"),
            ("ZIC_RENEWAL_EXPIRED", "Renewal expired", 50, "CLOSE_RENEWAL"),
        ]:
            self._upsert(
                OLPolicyRenewalStatus,
                {"code": code},
                {
                    **self._common(name, f"ZIC OL renewal status: {name}."),
                    "display_order": order,
                    "renewal_action": action,
                },
            )

        for code, name, category, basis, ratio, multiple in [
            ("ZIC_BENEFICIARY_PRIMARY", "Primary beneficiary", "BENEFICIARY", "PERCENTAGE", Decimal("100.0000"), False),
            ("ZIC_BENEFICIARY_CONTINGENT", "Contingent beneficiary", "BENEFICIARY", "PERCENTAGE", Decimal("0.0000"), True),
            ("ZIC_BENEFIT_MATURITY", "Maturity benefit", "BENEFIT", "FIXED", Decimal("100.0000"), False),
            ("ZIC_BENEFIT_DEATH", "Death benefit", "BENEFIT", "SUM_ASSURED", Decimal("100.0000"), False),
        ]:
            self._upsert(
                OLBeneficialType,
                {"code": code},
                {
                    **self._common(name, f"ZIC OL beneficiary/benefit type: {name}."),
                    "category": category,
                    "calculation_basis": basis,
                    "default_ratio": ratio,
                    "allows_multiple": multiple,
                },
            )

        for index, (code, name, _action, terminal) in enumerate([
            ("ZIC_COMMITMENT_PENDING", "Commitment pending", "AWAIT_PAYMENT", False),
            ("ZIC_COMMITMENT_PARTIAL", "Commitment partially paid", "AWAIT_BALANCE", False),
            ("ZIC_COMMITMENT_COMPLETE", "Commitment complete", "ISSUE_POLICY", True),
            ("ZIC_COMMITMENT_CANCELLED", "Commitment cancelled", "CLOSE_COMMITMENT", True),
        ], start=1):
            self._upsert(
                OLCommitmentStatus,
                {"code": code},
                {
                    **self._common(name, f"ZIC OL commitment status: {name}."),
                    "display_order": index * 10,
                    "applies_to": "COMMITMENT",
                    "is_terminal": terminal,
                },
            )

        for product_code, product in operational_products.items():
            products[product_code]
            product_plans = [plan for plan in plans.values() if plan.product_version.product_id == product.id]
            for plan in product_plans:
                for frequency, grace, warning, pre_lapse, lapse in [
                    ("MONTHLY", 30, 14, 7, 45),
                    ("QUARTERLY", 30, 14, 7, 45),
                    ("ANNUAL", 45, 21, 7, 60),
                ]:
                    self._upsert(
                        OLGracePeriod,
                        {"code": f"ZIC_{plan.code}_{frequency}_GRACE"},
                        {
                            **self._common(f"{plan.name} {frequency} grace period", "ZIC OL premium-due lifecycle grace configuration."),
                            "product": product,
                            "plan": plan,
                            "premium_frequency": frequency,
                            "grace_days": grace,
                            "warning_days": warning,
                            "pre_lapse_days": pre_lapse,
                            "lapse_days": lapse,
                            "minimum_due_amount": Decimal("25000.00"),
                        },
                    )
                self._upsert(
                    OLAnticipatedEndowmentInstallmentRate,
                    {"code": f"ZIC_{plan.code}_ANTICIPATED_01"},
                    {
                        **self._common(f"{plan.name} anticipated installment", "ZIC OL anticipated endowment benefit installment."),
                        "product": product,
                        "plan": plan,
                        "installment_type": "ANTICIPATED_ENDOWMENT",
                        "frequency": "ANNUAL",
                        "age_from": 18,
                        "age_to": 65,
                        "term_from": 5,
                        "term_to": 30,
                        "policy_year_from": 1,
                        "policy_year_to": 1,
                        "rate_factor": Decimal("0.10000000"),
                        "currency": "TZS",
                    },
                )
                self._upsert(
                    OLMemberCoverConfiguration,
                    {"code": f"ZIC_{plan.code}_PRINCIPAL_COVER"},
                    {
                        **self._common(f"{plan.name} principal member cover", "Principal member cover is automatically configured for every OL quote."),
                        "product": product,
                        "plan": plan,
                        "cover_type": "PRINCIPAL",
                        "member_relation": "SELF",
                        "min_age": 18,
                        "max_age": 65,
                        "waiting_period_days": 0,
                        "benefit_limit": Decimal("500000000.00"),
                        "premium_basis": "SUM_ASSURED",
                        "coverage_basis": "FULL",
                    },
                )
                self._upsert(
                    OLSurrenderSetup,
                    {"code": f"ZIC_{plan.code}_SURRENDER_SETUP"},
                    {
                        **self._common(f"{plan.name} surrender setup", "ZIC OL surrender eligibility and charge configuration."),
                        "product": product,
                        "plan": plan,
                        "minimum_premiums_paid": 24,
                        "minimum_policy_months": 24,
                        "minimum_premium_paid_ratio": Decimal("0.5000"),
                        "surrender_charge_type": "PERCENTAGE",
                        "surrender_charge_value": Decimal("0.05000000"),
                        "partial_surrender_allowed": product_code == "OL_INVESTMENT_LINKED",
                        "surrender_payout_days": 10,
                        "require_approval": True,
                    },
                )
                self._upsert(
                    OLPaidUpSetup,
                    {"code": f"ZIC_{plan.code}_PAIDUP_SETUP"},
                    {
                        **self._common(f"{plan.name} paid-up setup", "ZIC OL paid-up conversion eligibility and effective rule."),
                        "product": product,
                        "plan": plan,
                        "minimum_premiums_paid": 24,
                        "minimum_policy_months": 24,
                        "paidup_conversion_basis": "PROPORTIONAL",
                        "allow_paidup": True,
                        "paidup_effective_rule": "NEXT_ANNIVERSARY",
                    },
                )
                for rate_model, prefix, value in [
                    (OLSurrenderValueRate, "SURRENDER_VALUE", Decimal("0.35000000")),
                    (OLPaidUpRate, "PAIDUP_VALUE", Decimal("0.45000000")),
                ]:
                    self._upsert(
                        rate_model,
                        {"code": f"ZIC_{plan.code}_{prefix}_Y01"},
                        {
                            **self._common(f"{plan.name} {prefix.lower()} year 1", "ZIC OL policy-value factor row."),
                            "table_code": f"ZIC_{prefix}_2026",
                            "rate_table_version": "1.0",
                            "product": product,
                            "plan": plan,
                            "gender": "MALE",
                            "smoker_status": "NON_SMOKER",
                            "age_from": 18,
                            "age_to": 65,
                            "term_from": 5,
                            "term_to": 30,
                            "policy_year_from": 1,
                            "policy_year_to": 1,
                            "rate_factor": value,
                            "row_order": 1,
                        },
                    )
                    self._upsert(
                        rate_model,
                        {"code": f"ZIC_{plan.code}_{prefix}_Y02"},
                        {
                            **self._common(f"{plan.name} {prefix.lower()} year 2", "ZIC OL policy-value factor row."),
                            "table_code": f"ZIC_{prefix}_2026",
                            "rate_table_version": "1.0",
                            "product": product,
                            "plan": plan,
                            "gender": "MALE",
                            "smoker_status": "NON_SMOKER",
                            "age_from": 18,
                            "age_to": 65,
                            "term_from": 5,
                            "term_to": 30,
                            "policy_year_from": 2,
                            "policy_year_to": 2,
                            "rate_factor": value + Decimal("0.10000000"),
                            "row_order": 2,
                        },
                    )
                self._upsert(
                    OLReinstatementWindow,
                    {"code": f"ZIC_{plan.code}_REINSTATEMENT_WINDOW"},
                    {
                        **self._common(f"{plan.name} reinstatement window", "ZIC OL reinstatement eligibility after lapse."),
                        "product": product,
                        "plan": plan,
                        "days_after_lapse": 365,
                        "maximum_reinstatements": 2,
                        "require_medical_underwriting": True,
                        "require_outstanding_premium_payment": True,
                        "interest_rate": Decimal("0.1200"),
                        "penalty_rate": Decimal("0.0200"),
                    },
                )

    def _seed_product_setup(self, products, operational_products, plans):
        for code, name, category in [
            ("TERM_LIFE", "Term Life", "INDIVIDUAL"),
            ("EDUCATION_SAVINGS", "Education Savings", "INDIVIDUAL"),
            ("INVESTMENT_LINKED", "Investment Linked", "INDIVIDUAL"),
            ("GROUP_LIFE", "Group Life", "GROUP"),
        ]:
            self._upsert(
                OLPlanType,
                {"code": code},
                {
                    **self._common(name, f"ZIC OL plan type: {name}."),
                    "plan_category": category,
                },
            )

        for product_code, product in products.items():
            self._upsert(
                OLProduct,
                {"code": product_code},
                {
                    **self._common(product.name, product.description),
                    "plan_type": product.plan_type,
                    "insurance_class": product.insurance_class,
                    "currency": "TZS",
                    "min_entry_age": 18,
                    "max_entry_age": 65,
                    "min_term": 5,
                    "max_term": 30,
                    "min_sum_assured": Decimal("500000.00"),
                    "max_sum_assured": Decimal("500000000.00"),
                    "premium_frequencies": ["MONTHLY", "QUARTERLY", "SEMI_ANNUALLY", "ANNUALLY"],
                    "allow_riders": True,
                    "allow_loans": True,
                    "allow_withdrawals": product_code == "OL_INVESTMENT_LINKED",
                    "allow_surrender": True,
                    "allow_paidup": True,
                    "allow_bonus": product_code != "OL_TERM_LIFE",
                    "investment_linked": product_code == "OL_INVESTMENT_LINKED",
                },
            )

        for plan_code, plan in plans.items():
            product = products[plan.product_version.product.code]
            self._upsert(
                OLPlanTaxConfiguration,
                {"code": f"ZIC_{plan_code}_TAX"},
                {
                    **self._common(f"{plan.name} tax configuration", "ZIC OL Tanzania insurance tax configuration."),
                    "product": None,
                    "plan": plan,
                    "tax_type": "INSURANCE_LEVY",
                    "tax_basis": "PREMIUM",
                    "rate_type": "PERCENTAGE",
                    "rate_value": Decimal("0.000000"),
                    "apply_on": "BASE_AND_RIDER_PREMIUM",
                    "sequence": 1,
                    "country_or_branch": "TANZANIA-ZANZIBAR",
                },
            )
            self._upsert(
                OLPlanTargetMarket,
                {"code": f"ZIC_{plan_code}_TARGET_MARKET"},
                {
                    **self._common(f"{plan.name} target market", "ZIC OL target-market definition for Zanzibar residents."),
                    "product": None,
                    "plan": plan,
                    "target_market_type": "RETAIL_INDIVIDUAL",
                    "min_age": 18,
                    "max_age": 65,
                    "occupation_categories": ["FORMAL_EMPLOYEE", "SELF_EMPLOYED", "FARMER", "PROFESSIONAL"],
                    "residency_requirement": "TANZANIA_RESIDENT",
                },
            )
            self._upsert(
                OLPlanRiskCategory,
                {"code": f"ZIC_{plan_code}_RISK"},
                {
                    **self._common(f"{plan.name} underwriting risk category", "ZIC OL underwriting risk classification."),
                    "product": None,
                    "plan": plan,
                    "underwriting_class": "STANDARD",
                    "loading_basis": "MEDICAL_AND_OCCUPATION",
                },
            )
            self._upsert(
                OLPlanOccupationRiskLimit,
                {"code": f"ZIC_{plan_code}_OCCUPATION_LIMIT"},
                {
                    **self._common(f"{plan.name} occupation risk limit", "ZIC OL occupation-based sum assured control."),
                    "product": None,
                    "plan": plan,
                    "occupation_risk_category": "STANDARD",
                    "max_sum_assured": Decimal("250000000.00"),
                    "loading_rate": Decimal("0.000000"),
                    "exclusion_flag": False,
                },
            )

    def _seed_rating(self, products, plans):
        mortality_table = self._upsert(
            OLMortalityRateTable,
            {"table_code": "ZIC_TANZANIA_MORTALITY_2026", "version": "1.0"},
            {
                **self._common("ZIC Tanzania Mortality 2026", "ZIC OL mortality assumptions for Zanzibar individual life business."),
            },
        )
        for gender in ("MALE", "FEMALE", "OTHER"):
            for smoker_status, multiplier in (("NON_SMOKER", Decimal("1.00")), ("SMOKER", Decimal("1.80"))):
                for age, base_rate in ((18, Decimal("0.000600000000")), (35, Decimal("0.001100000000")), (50, Decimal("0.003500000000")), (65, Decimal("0.012000000000"))):
                    self._upsert(
                        OLMortalityRateRow,
                        {"code": f"ZIC_MORT_{gender}_{smoker_status}_{age}"},
                        {
                            **self._common(f"Mortality age {age} {gender} {smoker_status}", "ZIC OL mortality-rate assumption row."),
                            "table": mortality_table,
                            "age": age,
                            "gender": gender,
                            "smoker_status": smoker_status,
                            "policy_year": None,
                            "mortality_rate": (base_rate * multiplier).quantize(Decimal("0.000000000001")),
                        },
                    )

        for plan_code, plan in plans.items():
            product = products[plan.product_version.product.code]
            for frequency in ("MONTHLY", "QUARTERLY", "HALF_YEARLY", "ANNUAL"):
                self._upsert(
                    OLInstallmentChargeRate,
                    {"code": f"ZIC_{plan_code}_{frequency}_CHARGE"},
                    {
                        **self._common(f"{plan.name} {frequency} installment charge", "ZIC OL installment administration charge."),
                        "product": None,
                        "plan": plan,
                        "frequency": frequency,
                        "charge_type": "PERCENTAGE",
                        "rate_value": Decimal("0.000000"),
                        "apply_on": "INSTALLMENT",
                    },
                )
            self._upsert(
                OLReinstatementInterestRate,
                {"code": f"ZIC_{plan_code}_REINSTATEMENT_INTEREST"},
                {
                    **self._common(f"{plan.name} reinstatement interest", "ZIC OL interest applied to outstanding reinstatement premiums."),
                    "product": None,
                    "plan": plan,
                    "rate": Decimal("0.1200"),
                    "calculation_basis": "OUTSTANDING_PREMIUM",
                },
            )
            self._upsert(
                OLBonusRate,
                {"code": f"ZIC_{plan_code}_BONUS"},
                {
                    **self._common(f"{plan.name} reversionary bonus", "ZIC OL annual reversionary bonus assumption."),
                    "product": None,
                    "plan": plan,
                    "bonus_type": "REVERSIONARY",
                    "rate": Decimal("0.02500000"),
                    "valuation_year": 1,
                    "declaration_frequency": "ANNUAL",
                },
            )
            self._upsert(
                OLMortgageInterestFactor,
                {"code": f"ZIC_{product.code}_MORTGAGE_FACTOR"},
                {
                    **self._common(f"{product.name} mortgage interest factor", "ZIC OL mortgage-linked interest factor."),
                    "product": product,
                    "plan": None,
                    "factor": Decimal("1.00000000"),
                    "calculation_basis": "LOAN_BALANCE",
                },
            )
            for loading_type, rate in (("EXPENSE", Decimal("0.01500000")), ("RISK", Decimal("0.01000000"))):
                self._upsert(
                    OLReserveLoading,
                    {"code": f"ZIC_{plan_code}_{loading_type}_RESERVE_LOADING"},
                    {
                        **self._common(f"{plan.name} {loading_type.lower()} reserve loading", "ZIC OL reserve loading assumption."),
                        "product": None,
                        "plan": plan,
                        "loading_type": loading_type,
                        "loading_basis": "PREMIUM",
                        "rate_value": rate,
                    },
                )

        # A joint-life setup is attached to the family plan and is consumed by
        # the joint-life quotation branch.
        family_plan = plans["OL_TERM_FAMILY"]
        products[family_plan.product_version.product.code]
        self._upsert(
            OLJointLifeSetup,
            {"code": "ZIC_OL_TERM_FAMILY_JOINT_LIFE"},
            {
                **self._common("ZIC Term Family joint life", "First-death joint-life configuration for family protection."),
                "product": None,
                "plan": family_plan,
                "joint_life_type": "FIRST_DEATH",
                "age_basis": "YOUNGER_LIFE",
                "survivor_benefit_rule": "FULL_SUM_ASSURED_ON_FIRST_DEATH",
                "premium_adjustment_factor": Decimal("1.050000"),
                "underwriting_rule": "UNDERWRITE_EACH_LIFE",
            },
        )

        # Ensure every current premium table has at least one current row even
        # when the baseline release command was run against a partially seeded DB.
        for table in OLPremiumRateTable.objects.filter(is_active=True, plan__is_active=True):
            if not OLPremiumRateRow.objects.filter(table=table, is_active=True).exists():
                self._upsert(
                    OLPremiumRateRow,
                    {"code": f"{table.table_code}_FALLBACK_MALE_NS"},
                    {
                        **self._common(f"{table.name} fallback rate", "ZIC OL fallback premium-rate row."),
                        "table": table,
                        "gender": "MALE",
                        "smoker_status": "NON_SMOKER",
                        "age_from": 18,
                        "age_to": 65,
                        "term_from": 5,
                        "term_to": 30,
                        "frequency": "ANNUAL",
                        "sum_assured_band_from": None,
                        "sum_assured_band_to": None,
                        "rate": Decimal("2.50000000"),
                        "rate_unit": "PER_THOUSAND_SUM_ASSURED",
                    },
                )

    def _seed_riders_and_funds(self, products, plans):
        linked_product = products["OL_INVESTMENT_LINKED"]
        linked_plan = plans["OL_JENGA_BALANCED"]
        rider = self._upsert(
            OLRiderSetup,
            {"code": "ZIC_HOSPITAL_CASH_RIDER_OL_INVESTMENT_LINKED"},
            {
                **self._common("ZIC Hospital Cash Rider", "Daily hospital cash support for eligible Zanzibar OL policyholders."),
                "rider_category": "HEALTH",
                "benefit_type": "HOSPITAL_CASH",
                "calculation_basis": "FLAT",
                "min_age": 18,
                "max_age": 65,
                "min_term": 5,
                "max_term": 30,
                "min_sum_assured": Decimal("500000.00"),
                "max_sum_assured": Decimal("10000000.00"),
                "waiting_period_days": 30,
                "allows_standalone": False,
                "requires_underwriting": True,
                "exclusion_rules": {"pre_existing_conditions": True, "maximum_days_per_year": 30},
                "product": None,
                "plan": linked_plan,
            },
        )
        rider_table = self._upsert(
            OLRiderRateTable,
            {"table_code": "ZIC_HOSPITAL_CASH_RIDER_RATES", "version": "1.0"},
            {
                **self._common("ZIC Hospital Cash Rider rates", "ZIC OL hospital cash rider rate table."),
                "rider": rider,
                "product": None,
                "plan": linked_plan,
                "rating_basis": "FLAT",
            },
        )
        self._upsert(
            OLRiderRateRow,
            {"code": "ZIC_HOSPITAL_CASH_RIDER_RATE_MALE_NS"},
            {
                **self._common("Hospital cash rider standard rate", "ZIC OL hospital cash rider rate row."),
                "table": rider_table,
                "gender": "MALE",
                "smoker_status": "NON_SMOKER",
                "age_from": 18,
                "age_to": 65,
                "term_from": 5,
                "term_to": 30,
                "frequency": "MONTHLY",
                "sum_assured_band_from": None,
                "sum_assured_band_to": None,
                "rate": Decimal("0.75000000"),
                "rate_unit": "PERCENTAGE",
            },
        )

        funds = {}
        for code, name, risk in [
            ("ZIC_FUND_MONEY_MARKET", "ZIC Money Market Fund", OLInvestmentFundRiskProfile.CONSERVATIVE),
            ("ZIC_FUND_BALANCED", "ZIC Balanced Fund", OLInvestmentFundRiskProfile.BALANCED),
            ("ZIC_FUND_EQUITY", "ZIC Equity Growth Fund", OLInvestmentFundRiskProfile.AGGRESSIVE),
            ("ZIC_FUND_GOVERNMENT_BOND", "ZIC Government Bond Fund", OLInvestmentFundRiskProfile.MODERATE),
        ]:
            funds[code] = self._upsert(
                OLInvestmentFundType,
                {"code": code},
                {
                    **self._common(name, f"Zanzibar Insurance Company managed fund type: {name}."),
                    "risk_profile": risk,
                },
            )
        for code, name, type_code, price, frequency in [
            ("ZIC_MM_TZS", "ZIC Money Market Fund - TZS", "ZIC_FUND_MONEY_MARKET", "1.000000", "DAILY"),
            ("ZIC_BAL_TZS", "ZIC Balanced Fund - TZS", "ZIC_FUND_BALANCED", "1.250000", "DAILY"),
            ("ZIC_EQ_TZS", "ZIC Equity Growth Fund - TZS", "ZIC_FUND_EQUITY", "1.750000", "DAILY"),
            ("ZIC_GOVT_BOND_TZS", "ZIC Government Bond Fund - TZS", "ZIC_FUND_GOVERNMENT_BOND", "1.100000", "WEEKLY"),
        ]:
            self._upsert(
                OLInvestmentFund,
                {"code": code},
                {
                    **self._common(name, "Zanzibar Insurance Company investment fund priced in Tanzanian Shillings."),
                    "fund_type": funds[type_code],
                    "currency": "TZS",
                    "valuation_frequency": frequency,
                    "unit_price": Decimal(price),
                    "allocation_rules": {
                        "minimum_allocation_percent": 5,
                        "maximum_allocation_percent": 100,
                        "currency_conversion_allowed": False,
                        "eligible_products": [linked_product.code],
                    },
                },
            )

    def _seed_commission_loans_maturity(self, products, operational_products, plans, branch, agent):
        term_plan = plans["OL_TERM_STANDARD"]
        term_product = operational_products["OL_TERM_LIFE"]
        self._upsert(
            OLOverrideCommissionSetup,
            {"code": "ZIC_AGENT_TERM_OVERRIDE_COMPLETE"},
            {
                **self._common("ZIC Agent term override", "ZIC OL distribution override for the Zanzibar agency channel."),
                "partner": agent,
                "intermediary_type": "AGENT",
                "product": term_product,
                "plan": term_plan,
                "rider": None,
                "channel": "AGENCY",
                "branch": branch,
                "currency": "TZS",
                "rate_type": "PERCENTAGE",
                "rate_value": Decimal("2.50000000"),
                "premium_year_from": 1,
                "premium_year_to": 1,
                "policy_year_from": None,
                "policy_year_to": None,
                "priority": 10,
                "reason": "Zanzibar Insurance OL agency distribution setup.",
            },
        )
        self._upsert(
            OLAgentCommissionSetup,
            {"code": "ZIC_AGENT_EDUCATION_COMMISSION_COMPLETE"},
            {
                **self._common("ZIC Education agent commission", "ZIC OL agent commission for education savings plans."),
                "partner": agent,
                "intermediary_type": "AGENT",
                "distribution_channel": "AGENCY",
                "product": products["OL_EDUCATION_SAVINGS"],
                "plan": None,
                "rider": None,
                "currency": "TZS",
                "branch": branch,
                "commission_type": "FIRST_PREMIUM",
                "premium_year_from": 1,
                "premium_year_to": 1,
                "policy_year_from": None,
                "policy_year_to": None,
                "rate_type": "PERCENTAGE",
                "rate_value": Decimal("3.00000000"),
                "minimum_commission": Decimal("0.00"),
                "maximum_commission": Decimal("5000000.00"),
                "priority": 20,
                "reason": "Zanzibar Insurance OL education distribution setup.",
            },
        )
        for plan_code, plan in plans.items():
            operational_product = operational_products[plan.product_version.product.code]
            self._upsert(
                OLMaturityClaimSetup,
                {"code": f"ZIC_{plan_code}_MATURITY_CLAIM_COMPLETE"},
                {
                    **self._common(f"{plan.name} maturity claim setup", "ZIC OL maturity claim and payout workflow."),
                    "product": operational_product,
                    "plan": plan,
                    "auto_create_maturity_claim": True,
                    "days_before_maturity_to_initiate": 45,
                    "notification_days": 21,
                    "default_payout_method": "BANK_TRANSFER",
                    "require_documents": True,
                    "require_approval": operational_product.code != "OL_INVESTMENT_LINKED",
                    "maturity_claim_status_to_create": "REPORTED",
                },
            )

        for product_code, parameter_product in products.items():
            self._upsert(
                OLLoanSystemSetup,
                {"code": f"ZIC_{product_code}_LOAN_SYSTEM"},
                {
                    **self._common(f"{parameter_product.name} loan system setup", "ZIC OL policy loan controls."),
                    "product": parameter_product,
                    "plan": None,
                    "allow_policy_loans": True,
                    "loan_basis": "CASH_VALUE",
                    "max_loan_percentage_of_cash_value": Decimal("0.80000000"),
                    "min_loan_amount": Decimal("500000.00"),
                    "max_loan_amount": Decimal("100000000.00"),
                    "loan_currency": "TZS",
                    "repayment_options": ["REGULAR_PAYMENT", "DEDUCT_FROM_BENEFITS", "CAPITALIZE_INTEREST"],
                    "auto_deduct_from_benefits": True,
                    "effect_on_claim": "DEDUCT_BALANCE",
                    "effect_on_surrender": "DEDUCT_BALANCE",
                    "effect_on_maturity": "DEDUCT_BALANCE",
                    "require_approval": True,
                },
            )
            self._upsert(
                OLLoanInterestControl,
                {"code": f"ZIC_{product_code}_LOAN_INTEREST"},
                {
                    **self._common(f"{parameter_product.name} loan interest control", "ZIC OL policy-loan interest calculation."),
                    "product": parameter_product,
                    "plan": None,
                    "interest_rate": Decimal("0.1200"),
                    "compounding_frequency": "ANNUAL",
                    "interest_calculation_basis": "COMPOUND",
                    "grace_period_days": 30,
                    "penalty_interest_rate": Decimal("0.0200"),
                    "interest_suspension_rule": "SUSPEND_DURING_CLAIM_REVIEW",
                    "capitalize_interest": True,
                },
            )

    def _seed_medical_and_claims(self, agent):
        medical_code = self._upsert(
            OLMedicalCode,
            {"code": "ZIC_MEDICAL_EXAM_STANDARD"},
            {
                **self._common("Standard medical examination", "Medical examination required for higher-sum-assured OL proposals."),
                "medical_category": "MEDICAL_EXAMINATION",
            },
        )
        self._upsert(
            OLMedicalLimit,
            {"code": "ZIC_MEDICAL_LIMIT_STANDARD"},
            {
                **self._common("Standard medical limit", "ZIC OL automatic underwriting threshold."),
                "medical_code": medical_code,
                "product": None,
                "plan": None,
                "age_from": 18,
                "age_to": 65,
                "sum_assured_from": Decimal("100000000.00"),
                "sum_assured_to": Decimal("500000000.00"),
                "limit_type": "MEDICAL",
                "limit_amount": Decimal("2500000.00"),
                "required_frequency": "ONE_OFF",
                "mandatory_flag": True,
            },
        )
        for code, name, habit, impact, evidence in [
            ("ZIC_HABIT_SMOKING", "Smoking declaration", "SMOKING", "HIGH", True),
            ("ZIC_HABIT_ALCOHOL", "Alcohol consumption declaration", "ALCOHOL", "MEDIUM", False),
            ("ZIC_HABIT_HAZARDOUS_WORK", "Hazardous occupation declaration", "OCCUPATION_HAZARD", "HIGH", True),
        ]:
            self._upsert(
                # The model is imported lazily to keep this module’s import list
                # readable while retaining an explicit deterministic dataset.
                self._medical_habit_model(),
                {"code": code},
                {
                    **self._common(name, f"ZIC OL personal habit catalog: {name}."),
                    "habit_category": habit,
                    "question_text": f"Does the proposer have {name.lower()}?",
                    "underwriting_impact": impact,
                    "requires_evidence": evidence,
                },
            )
        for code, name, category, severity, waiting, exclusion, loading in [
            ("ZIC_HISTORY_DIABETES", "Diabetes history", "METABOLIC", "MEDIUM", 365, False, True),
            ("ZIC_HISTORY_HEART_DISEASE", "Heart disease history", "CARDIOVASCULAR", "HIGH", 730, True, True),
            ("ZIC_HISTORY_ASTHMA", "Asthma history", "RESPIRATORY", "LOW", 180, False, True),
        ]:
            self._upsert(
                OLMedicalHistory,
                {"code": code},
                {
                    **self._common(name, f"ZIC OL medical history catalog: {name}."),
                    "condition_category": category,
                    "severity": severity,
                    "waiting_period_days": waiting,
                    "exclusion_flag": exclusion,
                    "loading_flag": loading,
                    "underwriting_note": "Refer to medical underwriting guidelines and supporting evidence.",
                },
            )
        facility = self._upsert(
            OLMedicalFacility,
            {"code": "ZIC_MADINA_MEDICAL_FACILITY"},
            {
                **self._common("Madina Medical Centre", "Approved Zanzibar medical facility for OL underwriting."),
                "partner": None,
                "facility_code": "ZIC-MMC-001",
                "facility_type": "CLINIC",
                "registration_number": "ZMC-2026-0001",
                "address": "Mkunazini Road, Stone Town",
                "city": "Zanzibar City",
                "country": "Tanzania",
                "contact_email": "underwriting@madinamedical.co.tz",
                "contact_phone": "+255242000101",
                "approval_status": "APPROVED",
            },
        )
        self._upsert(
            OLMedicalPractitioner,
            {"code": "ZIC_DR_SALMA_HASSAN"},
            {
                **self._common("Dr. Salma Hassan", "Approved medical practitioner for ZIC OL underwriting referrals."),
                "partner": None,
                "practitioner_code": "ZIC-DOC-0001",
                "first_name": "Salma",
                "last_name": "Hassan",
                "specialty": "General Medicine",
                "license_number": "MCT-2026-0001",
                "medical_facility": facility,
                "email": "salma.hassan@madinamedical.co.tz",
                "phone": "+255712000101",
                "approval_status": "APPROVED",
            },
        )

        claim_type = self._upsert(
            OLClaimType,
            {"code": "ZIC_CLAIM_DEATH"},
            {
                **self._common("Death claim", "ZIC OL death claim processing configuration."),
                "claim_category": "DEATH",
                "calculation_basis": "SUM_ASSURED",
                "duplicate_check_rule": "POLICY_AND_EVENT_DATE",
                "waiting_period_days": 0,
                "payable_to_rules": {"beneficiary": True, "policyholder": False},
                "allow_waiver_of_premium": True,
                    "require_documents": ["CLAIM_FORM", "DEATH_CERTIFICATE", "IDENTITY_DOCUMENT"],
                    "require_approval": True,
            },
        )
        for code, name, category in [
            ("ZIC_REASON_NATURAL_DEATH", "Natural death", "EVENT"),
            ("ZIC_REASON_ACCIDENTAL_DEATH", "Accidental death", "EVENT"),
            ("ZIC_REASON_UNVERIFIED_DOCUMENTS", "Unverified claim documents", "DOCUMENTARY"),
        ]:
            self._upsert(
                OLClaimReason,
                {"code": code},
                {
                    **self._common(name, f"ZIC OL claim reason: {name}."),
                    "claim_type": claim_type,
                    "reason_category": category,
                },
            )
        claim_statuses = [
            ("ZIC_CLAIM_REPORTED", "Reported", 10, "INFO", False, False, ["ZIC_CLAIM_ASSESSING"]),
            ("ZIC_CLAIM_ASSESSING", "Assessing", 20, "PRIMARY", False, False, ["ZIC_CLAIM_APPROVED", "ZIC_CLAIM_REJECTED"]),
            ("ZIC_CLAIM_APPROVED", "Approved", 30, "SUCCESS", False, True, ["ZIC_CLAIM_PAID"]),
            ("ZIC_CLAIM_REJECTED", "Rejected", 40, "DANGER", True, False, []),
            ("ZIC_CLAIM_PAID", "Paid", 50, "SUCCESS", True, True, []),
        ]
        for code, name, order, badge, terminal, payable, _transitions in claim_statuses:
            self._upsert(
                OLClaimStatus,
                {"code": code},
                {
                    **self._common(name, f"ZIC OL claim status: {name}."),
                    "display_order": order,
                    "badge_type": badge,
                    "is_terminal": terminal,
                    "is_payable": payable,
                    "allowed_transitions": [],
                },
            )
        for code, _name, _order, _badge, _terminal, _payable, transitions in claim_statuses:
            self._upsert(OLClaimStatus, {"code": code}, {"allowed_transitions": transitions})
        for code, name, category, template, variables in [
            ("ZIC_DISCHARGE_FULL_FINAL", "Full and final discharge", "FULL_AND_FINAL", "ZIC-DISCHARGE-FULL", {"claim_number": "string", "payee_name": "string", "amount": "decimal"}),
            ("ZIC_DISCHARGE_PARTIAL", "Partial discharge", "PARTIAL", "ZIC-DISCHARGE-PARTIAL", {"claim_number": "string", "amount": "decimal"}),
            ("ZIC_DISCHARGE_ASSIGNMENT", "Assignment discharge", "ASSIGNMENT", "ZIC-DISCHARGE-ASSIGN", {"claim_number": "string", "assignee_name": "string"}),
        ]:
            self._upsert(
                OLDischargeType,
                {"code": code},
                {
                    **self._common(name, f"ZIC OL discharge document type: {name}."),
                    "discharge_category": category,
                    "template_code": template,
                    "variables": variables,
                },
            )
        for code, name, category, channel, purpose in [
            ("ZIC_CORRESPONDENT_CLAIMS_EMAIL", "Claims email correspondent", "CLAIM_ACKNOWLEDGEMENT", "EMAIL", "Claim acknowledgement and correspondence."),
            ("ZIC_CORRESPONDENT_CLAIMS_SMS", "Claims SMS correspondent", "DOCUMENT_REQUEST", "SMS", "Urgent claim document reminders."),
            ("ZIC_CORRESPONDENT_AGENT_PORTAL", "Agent portal correspondent", "DECISION", "PORTAL", "Agent claim decision notification."),
            ("ZIC_CORRESPONDENT_PAYMENT_LETTER", "Payment letter correspondent", "PAYMENT", "LETTER", "Payment advice and discharge workflow."),
        ]:
            self._upsert(
                OLCorrespondentType,
                {"code": code},
                {
                    **self._common(name, f"ZIC OL correspondent type: {name}."),
                    "correspondence_category": category,
                    "communication_channel": channel,
                    "purpose": purpose,
                },
            )

    def _medical_habit_model(self):
        from apps.ol_parameters.models import OLPersonalHabit

        return OLPersonalHabit

    def _seed_health_and_notifications(self, products, plans):
        questions = []
        for code, name, text, category, answer_type, impact, followup in [
            ("ZIC_HEALTH_Q01", "General health", "Are you currently in good health?", "GENERAL", "BOOLEAN", "MEDIUM", False),
            ("ZIC_HEALTH_Q02", "Medical treatment", "Have you received medical treatment in the last five years?", "MEDICAL_HISTORY", "BOOLEAN", "MEDIUM", True),
            ("ZIC_HEALTH_Q03", "Chronic condition", "Have you ever been diagnosed with a chronic condition?", "MEDICAL_HISTORY", "BOOLEAN", "HIGH", True),
            ("ZIC_HEALTH_Q04", "Hospitalisation", "Have you been hospitalised during the last three years?", "MEDICAL_HISTORY", "BOOLEAN", "HIGH", True),
            ("ZIC_HEALTH_Q05", "Occupation", "Does your occupation involve hazardous duties?", "OCCUPATION", "BOOLEAN", "HIGH", True),
            ("ZIC_HEALTH_Q06", "Lifestyle", "Do you smoke or use tobacco products?", "LIFESTYLE", "BOOLEAN", "HIGH", False),
        ]:
            questions.append(
                self._upsert(
                    OLHealthQuestion,
                    {"code": code},
                    {
                        **self._common(name, f"ZIC OL health question: {name}."),
                        "question_text": text,
                        "category": category,
                        "answer_type": answer_type,
                        "underwriting_impact": impact,
                        "requires_medical_followup": followup,
                    },
                )
            )
        questionnaire = self._upsert(
            OLHealthQuestionnaire,
            {"code": "ZIC_OL_GLOBAL_UW_QUESTIONNAIRE_2026"},
            {
                **self._common("ZIC OL global underwriting questionnaire", "Effective health declaration questionnaire for Zanzibar OL quotations."),
                "applies_to_scope": "GLOBAL",
                "product": None,
                "plan": None,
                "scheme_code": "",
                "sum_assured_threshold": Decimal("100000000.00"),
                "age_threshold": 45,
                "version": "1.0",
            },
        )
        for sequence, question in enumerate(questions, start=1):
            self._upsert(
                OLHealthQuestionnaireItem,
                {"code": f"ZIC_OL_GLOBAL_UW_Q{sequence:02d}"},
                {
                    **self._common(f"Question {sequence}: {question.name}", "ZIC OL questionnaire item."),
                    "questionnaire": questionnaire,
                    "health_question": question,
                    "sequence": sequence,
                    "mandatory": True,
                    "trigger_medical_requirement": question.requires_medical_followup,
                    "score": sequence,
                },
            )
        for code, name, event, offset, channel, recipient, template in [
            ("ZIC_NOTIFY_PREMIUM_DUE", "Premium due notice", "PREMIUM_DUE", 0, "SMS", "POLICYHOLDER", "ZIC-OL-PREMIUM-DUE"),
            ("ZIC_NOTIFY_GRACE_START", "Grace period started", "GRACE_START", 1, "SMS", "POLICYHOLDER", "ZIC-OL-GRACE-START"),
            ("ZIC_NOTIFY_PRE_LAPSE", "Pre-lapse warning", "PRE_LAPSE", -7, "EMAIL", "AGENT", "ZIC-OL-PRE-LAPSE"),
            ("ZIC_NOTIFY_LAPSE", "Policy lapsed", "LAPSE", 0, "PORTAL", "AGENT", "ZIC-OL-LAPSE"),
        ]:
            self._upsert(
                OLGracePeriodNotificationSchedule,
                {"code": code},
                {
                    **self._common(name, f"ZIC OL grace-period notification: {name}."),
                    "event_type": event,
                    "days_offset": offset,
                    "notification_channel": channel,
                    "recipient_type": recipient,
                    "template_code": template,
                },
            )

    def _verify(self):
        today = date.today()
        missing = []
        for model in self.REQUIRED_MODELS:
            queryset = model.objects.filter(is_active=True)
            if any(field.name == "effective_from" for field in model._meta.fields):
                queryset = queryset.filter(
                    Q(effective_from__isnull=True) | Q(effective_from__lte=today),
                    Q(effective_to__isnull=True) | Q(effective_to__gte=today),
                )
            if not queryset.exists():
                missing.append(model._meta.label)
                continue
            relation_fields = [
                field for field in model._meta.fields
                if getattr(field, "many_to_one", False) and getattr(field, "concrete", False) and not field.null
            ]
            if relation_fields:
                rows = queryset.select_related(*(field.name for field in relation_fields))
                for row in rows:
                    for field in relation_fields:
                        related = getattr(row, field.name, None)
                        if related is None:
                            missing.append(f"{model._meta.label}.{field.name}")
                            continue
                        related_fields = {related_field.name for related_field in related._meta.fields}
                        if "is_active" in related_fields and not related.is_active:
                            missing.append(f"{model._meta.label}.{field.name}.inactive")
                        if "effective_from" in related_fields:
                            if related.effective_from and related.effective_from > today:
                                missing.append(f"{model._meta.label}.{field.name}.future")
                            if related.effective_to and related.effective_to < today:
                                missing.append(f"{model._meta.label}.{field.name}.expired")
        if not OLPremiumRateTable.objects.filter(is_active=True, plan__is_active=True, rows__is_active=True).exists():
            missing.append("ol_parameters.OLPremiumRateTable.rows")
        if not OLRiderRateTable.objects.filter(is_active=True, rider__is_active=True, rows__is_active=True).exists():
            missing.append("ol_parameters.OLRiderRateTable.rows")
        if not OLMortalityRateTable.objects.filter(is_active=True, rows__is_active=True).exists():
            missing.append("ol_parameters.OLMortalityRateTable.rows")
        if not OLInvestmentFund.objects.filter(is_active=True, fund_type__is_active=True).exists():
            missing.append("ol_parameters.OLInvestmentFund.fund_type")
        if not missing:
            return True
        raise CommandError("Complete OL seed verification failed; missing active data: " + ", ".join(missing))

    @transaction.atomic
    def handle(self, *args, **options):
        if not options["verify_only"]:
            # Existing seeders own canonical ChoiceLists, RBAC, quotation numbering,
            # operational product versions, plans, rate bands, locations, and demo
            # partner data. This command then completes the parameter graph.
            call_command("seed_zanzibar_ol_demo", verbosity=0)
            # The demo command intentionally seeds the release before operational
            # products exist. Re-run it after the product graph is present so
            # product-dependent baseline rows are created on the first complete
            # run as well as subsequent runs, preserving repeatability.
            call_command("seed_ol_parameters_release", verbosity=0)
            self._seed_defaults_and_system()
            products, operational_products, plans, branch, agent = self._load_graph()
            self._seed_product_setup(products, operational_products, plans)
            self._seed_policy_setup(products, operational_products, plans)
            self._seed_rating(products, plans)
            self._seed_riders_and_funds(products, plans)
            self._seed_commission_loans_maturity(products, operational_products, plans, branch, agent)
            self._seed_medical_and_claims(agent)
            self._seed_health_and_notifications(products, plans)
        self._verify()

        if options["verify_only"]:
            self.stdout.write(self.style.SUCCESS("Zanzibar OL complete seed verification passed."))
            return
        self.stdout.write(
            self.style.SUCCESS(
                f"Zanzibar OL complete seed finished: {self.created} created, {self.updated} updated; "
                f"{len(self.touched)} model families touched."
            )
        )
        self.stdout.write("No tables were flushed or deleted; all records use deterministic natural keys and active 2026 effective dates.")
