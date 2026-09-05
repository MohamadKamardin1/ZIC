"""Prompt 5 — full GC Parameters seed runs, is idempotent, and feeds the APIs."""

from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient

from apps.group_credit.models import (
    GCClaimReason,
    GCClaimStatus,
    GCClaimType,
    GCCorrespondentType,
    GCDischargeType,
    GCMedicalCode,
    GCMedicalFacility,
    GCMedicalHistory,
    GCMedicalLimit,
    GCMedicalPractitioner,
    GCProduct,
    GCRider,
    GCRiderRate,
    GCSchemePremiumRate,
    GCSchemeType,
    GCSubProduct,
    GCUnderwritingDecision,
)
from apps.partners.models import Partner
from apps.users.models import User

BASE_UNIT_RATE_COUNT = 4


class GCSeedReleaseTests(TestCase):
    """Prompt 5 — seed runs without errors and leaves data for every category."""

    @classmethod
    def setUpTestData(cls):
        call_command("seed_gc_parameters_full", verbosity=0)

    def test_seed_creates_scheme_types_and_statuses(self):
        self.assertEqual(GCSchemeType.objects.count(), 4)
        for code in ("MORTGAGE_PROTECTION", "BANK_LOAN", "CORPORATE_SALARY", "HIRE_PURCHASE"):
            self.assertTrue(GCSchemeType.objects.filter(code=code).exists())

    def test_seed_creates_products_with_loan_term_limits(self):
        self.assertEqual(GCProduct.objects.count(), 2)
        plan_a = GCProduct.objects.get(code="CREDIT_LIFE_A")
        self.assertEqual(plan_a.name, "Credit Life Plan A")
        self.assertEqual(plan_a.scheme_type_ref.code, "BANK_LOAN")
        self.assertEqual(plan_a.max_loan_term, 240)
        plan_b = GCProduct.objects.get(code="CREDIT_LIFE_B")
        self.assertEqual(plan_b.name, "Credit Life Plan B")
        self.assertEqual(plan_b.scheme_type_ref.code, "CORPORATE_SALARY")
        self.assertEqual(plan_b.max_loan_term, 360)
        self.assertEqual(GCSubProduct.objects.get(code="GROUP_CREDIT_LIFE").name, "Group Credit Life")

    def test_seed_creates_product_scoped_unit_rates(self):
        self.assertTrue(
            GCSchemePremiumRate.objects.filter(
                name="Credit Life Plan A - Standard Unit Rate",
                product_ref__code="CREDIT_LIFE_A",
                rate_type="UNIT",
            ).exists()
        )
        # The base command's four scheme-scoped unit rates are preserved.
        self.assertEqual(
            GCSchemePremiumRate.objects.filter(rate_type="UNIT", product_ref__isnull=True).count(),
            BASE_UNIT_RATE_COUNT,
        )

    def test_seed_creates_riders_and_rates(self):
        adb = GCRider.objects.get(code="ACCIDENTAL_DEATH_BENEFIT")
        self.assertEqual(adb.name, "Accidental Death Benefit")
        self.assertEqual(adb.rider_category, "ACCIDENTAL_DEATH")
        ptd = GCRider.objects.get(code="PERMANENT_DISABILITY")
        self.assertEqual(ptd.rider_category, "DISABILITY")
        self.assertTrue(ptd.requires_underwriting)
        # One rate per rider per flagship product.
        self.assertEqual(GCRiderRate.objects.count(), 4)
        self.assertEqual(
            GCRiderRate.objects.filter(product_ref__code="CREDIT_LIFE_B").count(), 2
        )

    def test_seed_creates_medical_catalog(self):
        self.assertTrue(
            GCMedicalHistory.objects.filter(code="HYPERTENSION").exists()
        )
        self.assertTrue(
            GCMedicalHistory.objects.filter(code="DIABETES").exists()
        )
        for icd_code in ("I10", "E11", "I21", "C50"):
            self.assertTrue(GCMedicalCode.objects.filter(code=icd_code).exists())
        self.assertEqual(GCMedicalLimit.objects.filter(scheme_type_ref__code="BANK_LOAN").count(), 2)
        self.assertEqual(set(GCUnderwritingDecision.objects.values_list("code", flat=True)), {"STANDARD", "LOADING", "DECLINE"})
        self.assertEqual(GCMedicalFacility.objects.count(), 2)
        self.assertEqual(
            GCMedicalFacility.objects.get(code="DSM-GENERAL-HOSP").name,
            "Dar es Salaam General Hospital",
        )
        practitioner = GCMedicalPractitioner.objects.get(code="DR-J-MWANZA")
        self.assertEqual(practitioner.specialization, "CARDIOLOGY")
        self.assertEqual(practitioner.facility.code, "DSM-GENERAL-HOSP")
        # Facilities are backed by real Partner rows.
        self.assertEqual(
            Partner.objects.filter(
                partner_number__in=("PTN-DSM-GENERAL-HOSP", "PTN-UHURU-CLINIC")
            ).count(),
            2,
        )

    def test_seed_creates_claim_catalog(self):
        death = GCClaimType.objects.get(code="DEATH")
        ptd = GCClaimType.objects.get(code="PTD")
        self.assertEqual(death.category, "DEATH")
        self.assertEqual(ptd.name, "Permanent Total Disability")
        self.assertEqual(ptd.category, "PERMANENT_DISABILITY")
        self.assertEqual(GCClaimReason.objects.count(), 4)
        self.assertTrue(
            GCClaimReason.objects.filter(
                claim_type=death, category="ACCIDENT", name="Accident"
            ).exists()
        )
        self.assertTrue(
            GCClaimReason.objects.filter(
                claim_type=death, category="ILLNESS", name="Natural Causes"
            ).exists()
        )
        self.assertEqual(GCClaimStatus.objects.count(), 5)
        self.assertTrue(
            GCClaimStatus.objects.filter(code="PAID", is_terminal=True).exists()
        )
        self.assertTrue(GCDischargeType.objects.filter(code="SETTLEMENT").exists())
        self.assertTrue(
            GCCorrespondentType.objects.filter(code="MEMBER_EMAIL").exists()
        )

    def test_seed_is_idempotent(self):
        before = {
            "products": GCProduct.objects.count(),
            "riders": GCRider.objects.count(),
            "rider_rates": GCRiderRate.objects.count(),
            "medical_codes": GCMedicalCode.objects.count(),
            "facilities": GCMedicalFacility.objects.count(),
            "practitioners": GCMedicalPractitioner.objects.count(),
            "claim_types": GCClaimType.objects.count(),
            "claim_reasons": GCClaimReason.objects.count(),
            "claim_statuses": GCClaimStatus.objects.count(),
            "partners": Partner.objects.filter(
                partner_number__in=("PTN-DSM-GENERAL-HOSP", "PTN-UHURU-CLINIC")
            ).count(),
        }
        call_command("seed_gc_parameters_full", verbosity=0)
        after = {
            "products": GCProduct.objects.count(),
            "riders": GCRider.objects.count(),
            "rider_rates": GCRiderRate.objects.count(),
            "medical_codes": GCMedicalCode.objects.count(),
            "facilities": GCMedicalFacility.objects.count(),
            "practitioners": GCMedicalPractitioner.objects.count(),
            "claim_types": GCClaimType.objects.count(),
            "claim_reasons": GCClaimReason.objects.count(),
            "claim_statuses": GCClaimStatus.objects.count(),
            "partners": Partner.objects.filter(
                partner_number__in=("PTN-DSM-GENERAL-HOSP", "PTN-UHURU-CLINIC")
            ).count(),
        }
        self.assertEqual(after, before)


class GCSeededAPITests(TestCase):
    """Prompt 5 — the APIs return the seeded data."""

    @classmethod
    def setUpTestData(cls):
        call_command("seed_gc_parameters_full", verbosity=0)
        cls.user = User.objects.create_user(
            username="gc-seed-checker",
            email="gc-seed-checker@example.com",
            password="Strong-pass-123!",
            is_superuser=True,
            is_staff=True,
            is_active=True,
            is_approved=True,
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_products_list_returns_seeded_rows(self):
        response = self.client.get("/api/v1/gc/parameters/products/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["pagination"]["total"], 2)
        codes = {row["code"] for row in response.data["data"]}
        self.assertEqual(codes, {"CREDIT_LIFE_A", "CREDIT_LIFE_B"})
        by_code = {row["code"]: row for row in response.data["data"]}
        self.assertEqual(by_code["CREDIT_LIFE_A"]["display_name"], "CREDIT_LIFE_A — Credit Life Plan A")
        self.assertEqual(by_code["CREDIT_LIFE_B"]["scheme_type_ref_display"], "CORPORATE_SALARY — Corporate Salary")

    def test_products_options_filter_by_scheme_type(self):
        response = self.client.get(
            "/api/v1/gc/options/products/?scheme_type=BANK_LOAN"
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(len(response.data), 1)
        item = response.data[0]
        self.assertEqual(item["label"], "CREDIT_LIFE_A — Credit Life Plan A")
        self.assertEqual(item["meta"]["scheme_type_code"], "BANK_LOAN")

    def test_claim_types_options_return_seeded_types(self):
        response = self.client.get("/api/v1/gc/options/claim-types/")
        self.assertEqual(response.status_code, 200, response.data)
        by_label = {item["label"]: item for item in response.data}
        self.assertIn("DEATH — Death", by_label)
        self.assertIn("PTD — Permanent Total Disability", by_label)
        self.assertEqual(
            by_label["PTD — Permanent Total Disability"]["meta"]["category"],
            "PERMANENT_DISABILITY",
        )

    def test_medical_facilities_list_returns_seeded_rows(self):
        response = self.client.get("/api/v1/gc/parameters/medical/facilities/")
        self.assertEqual(response.status_code, 200, response.data)
        names = {row["name"] for row in response.data["data"]}
        self.assertIn("Dar es Salaam General Hospital", names)
