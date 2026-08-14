from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.ordinary_life.models import (
    OLBeneficiaryType,
    OLBenefit,
    OLCommitmentStatus,
    OLComputationApproach,
    OLGracePeriod,
    OLGracePeriodNotificationSchedule,
    OLHealthQuestion,
    OLHealthQuestionnaire,
    OLMemberCoverConfiguration,
    OLPaidUpRate,
    OLPaidUpSetup,
    OLPlan,
    OLPolicyRenewalStatus,
    OLPolicyStatus,
    OLProduct,
    OLProductBenefit,
    OLProductRider,
    OLProductVersion,
    OLRateBand,
    OLReinstatementWindow,
    OLRider,
    OLSurrenderSetup,
    OLSurrenderValueRate,
)


class Command(BaseCommand):
    help = "Seed idempotent Ordinary Life reference data and baseline product configuration."

    @transaction.atomic
    def handle(self, *args, **options):
        today = date(2026, 1, 1)
        counts = {}

        def upsert(model, lookup, defaults):
            record, created = model.objects.update_or_create(defaults=defaults, **lookup)
            counts[model.__name__] = counts.get(model.__name__, 0) + int(created)
            return record

        computation = upsert(
            OLComputationApproach,
            {"code": "LEVEL_PREMIUM"},
            {"name": "Level premium", "description": "Level premium calculation over the selected term.", "is_active": True},
        )

        product = upsert(
            OLProduct,
            {"code": "OL_TERM_LIFE"},
            {
                "name": "Ordinary Life Term Protection",
                "description": "Individual life protection with level premium and optional riders.",
                "business_area": "ORDINARY_LIFE",
                "min_age": 18,
                "max_age": 65,
                "term_length_years": 10,
                "is_active": True,
            },
        )
        version = upsert(
            OLProductVersion,
            {"product": product, "version_number": 1},
            {
                "effective_from": today,
                "effective_to": None,
                "currency": "TZS",
                "min_entry_age": 18,
                "max_entry_age": 65,
                "min_term_years": 5,
                "max_term_years": 30,
                "payment_frequencies": ["MONTHLY", "QUARTERLY", "SEMI_ANNUAL", "ANNUAL"],
                "calculation_approach": computation,
                "underwriting_rules": {"medical_threshold_tzs": 100000000, "automatic_acceptance": False},
                "servicing_rules": {"grace_period_days": 30, "reinstatement_window_months": 12},
                "snapshot": {"seed_key": "OL_TERM_LIFE_V1", "currency": "TZS"},
                "is_active": True,
            },
        )

        plans = [
            ("OL_TERM_STANDARD", "Standard term protection", Decimal("1000000.00"), Decimal("500000000.00")),
            ("OL_TERM_FAMILY", "Family term protection", Decimal("500000.00"), Decimal("100000000.00")),
        ]
        plan_records = {}
        for code, name, minimum, maximum in plans:
            plan_records[code] = upsert(
                OLPlan,
                {"product_version": version, "code": code},
                {
                    "name": name,
                    "description": f"{name} under Ordinary Life Term Protection.",
                    "minimum_sum_assured": minimum,
                    "maximum_sum_assured": maximum,
                    "is_active": True,
                },
            )

        benefits = {}
        for code, name, benefit_type, description in [
            ("DEATH", "Death benefit", "CORE", "Payable on death of the life assured during the policy term."),
            ("ACCIDENTAL_DEATH", "Accidental death benefit", "RIDER", "Additional benefit for qualifying accidental death."),
            ("PREMIUM_WAIVER", "Premium waiver", "RIDER", "Waives qualifying future premiums after an insured event."),
        ]:
            benefits[code] = upsert(
                OLBenefit,
                {"code": code},
                {"name": name, "benefit_type": benefit_type, "description": description, "is_active": True},
            )

        for benefit_code, mandatory, minimum, maximum in [
            ("DEATH", True, Decimal("1000000.00"), Decimal("500000000.00")),
            ("ACCIDENTAL_DEATH", False, None, Decimal("500000000.00")),
            ("PREMIUM_WAIVER", False, None, None),
        ]:
            upsert(
                OLProductBenefit,
                {"product_version": version, "benefit": benefits[benefit_code]},
                {"is_mandatory": mandatory, "minimum_amount": minimum, "maximum_amount": maximum, "rules": {}, "is_active": True},
            )

        rider = upsert(
            OLRider,
            {"code": "RIDER_ACCIDENTAL_DEATH"},
            {"name": "Accidental death rider", "description": "Optional accidental death cover.", "eligibility_rules": {"max_entry_age": 60}, "is_active": True},
        )
        upsert(
            OLProductRider,
            {"product_version": version, "rider": rider},
            {"is_mandatory": False, "premium_rate": Decimal("0.000250"), "rules": {}, "is_active": True},
        )

        for plan_code, min_age, max_age, min_term, max_term, rate in [
            ("OL_TERM_STANDARD", 18, 35, 5, 30, Decimal("0.00120000")),
            ("OL_TERM_STANDARD", 36, 50, 5, 25, Decimal("0.00210000")),
            ("OL_TERM_STANDARD", 51, 65, 5, 15, Decimal("0.00450000")),
            ("OL_TERM_FAMILY", 18, 45, 5, 25, Decimal("0.00150000")),
            ("OL_TERM_FAMILY", 46, 65, 5, 15, Decimal("0.00350000")),
        ]:
            upsert(
                OLRateBand,
                {"product_version": version, "plan": plan_records[plan_code], "min_age": min_age, "max_age": max_age, "min_term_years": min_term, "max_term_years": max_term},
                {"rate": rate, "assumptions": {"basis": "BASELINE_REFERENCE_DATA"}, "is_active": True},
            )

        for code, name, terminal in [
            ("DRAFT", "Draft", False),
            ("ACTIVE", "Active", False),
            ("LAPSED", "Lapsed", False),
            ("SURRENDERED", "Surrendered", True),
            ("PAID_UP", "Paid up", False),
            ("MATURED", "Matured", True),
            ("CANCELLED", "Cancelled", True),
            ("CLAIMED", "Claimed", True),
        ]:
            upsert(OLPolicyStatus, {"code": code}, {"name": name, "is_terminal": terminal, "is_active": True})

        for code, name in [
            ("NOT_DUE", "Not due"),
            ("DUE", "Due"),
            ("RENEWED", "Renewed"),
            ("NOT_RENEWED", "Not renewed"),
        ]:
            upsert(OLPolicyRenewalStatus, {"code": code}, {"name": name, "is_active": True})

        for code, name in [
            ("SPOUSE", "Spouse"),
            ("CHILD", "Child"),
            ("PARENT", "Parent"),
            ("TRUSTEE", "Trustee"),
            ("OTHER", "Other"),
        ]:
            upsert(OLBeneficiaryType, {"code": code}, {"name": name, "is_active": True})

        for code, name in [
            ("PENDING", "Pending"),
            ("PARTIALLY_PAID", "Partially paid"),
            ("PAID", "Paid"),
            ("CANCELLED", "Cancelled"),
            ("REFUNDED", "Refunded"),
        ]:
            upsert(OLCommitmentStatus, {"code": code}, {"name": name, "is_active": True})

        upsert(OLGracePeriod, {"code": "STANDARD_30_DAYS"}, {"days": 30, "description": "Standard Ordinary Life premium grace period.", "is_active": True})
        for days, notification_type in [(1, "SMS"), (15, "EMAIL"), (30, "SMS")]:
            upsert(
                OLGracePeriodNotificationSchedule,
                {"days_past_due": days, "notification_type": notification_type},
                {"is_active": True},
            )
        upsert(OLReinstatementWindow, {"max_months": 12}, {"requires_medical": True, "is_active": True})
        upsert(OLMemberCoverConfiguration, {"code": "INDIVIDUAL"}, {"name": "Individual cover", "max_dependents": 0, "is_active": True})
        upsert(OLSurrenderSetup, {"code": "STANDARD"}, {"min_years_in_force": 3, "penalty_percentage": Decimal("10.00"), "is_active": True})
        upsert(OLPaidUpSetup, {"code": "STANDARD"}, {"min_years_in_force": 3, "is_active": True})
        for policy_year, surrender_factor, paid_up_factor in [(3, Decimal("0.25000"), Decimal("0.30000")), (5, Decimal("0.50000"), Decimal("0.60000")), (10, Decimal("0.75000"), Decimal("0.85000"))]:
            upsert(OLSurrenderValueRate, {"policy_year": policy_year}, {"rate_factor": surrender_factor, "is_active": True})
            upsert(OLPaidUpRate, {"policy_year": policy_year}, {"rate_factor": paid_up_factor, "is_active": True})

        questionnaire = upsert(
            OLHealthQuestionnaire,
            {"code": "OL_STANDARD_HEALTH_V1"},
            {"name": "Ordinary Life standard health questionnaire", "version": "1.0", "effective_date": today, "is_active": True},
        )
        del questionnaire
        for code, question_text, category in [
            ("HEALTH_01", "Have you consulted a doctor or been hospitalized in the last five years?", "MEDICAL_HISTORY"),
            ("HEALTH_02", "Do you currently take prescribed medication?", "MEDICATION"),
            ("HEALTH_03", "Have you ever been diagnosed with a chronic condition?", "CHRONIC_CONDITION"),
            ("HEALTH_04", "Do you smoke or use tobacco products?", "LIFESTYLE"),
        ]:
            upsert(OLHealthQuestion, {"code": code}, {"question_text": question_text, "category": category, "is_active": True})

        self.stdout.write(self.style.SUCCESS("Ordinary Life reference data seeded successfully."))
        for model_name, created in sorted(counts.items()):
            self.stdout.write(f"{model_name}: {created} created")
