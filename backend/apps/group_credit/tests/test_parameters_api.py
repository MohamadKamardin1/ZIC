"""Prompt 4 — GC Parameters APIs, Options endpoints, Validation Services and CSV export."""

from datetime import date

from django.test import TestCase
from rest_framework.test import APIClient

from apps.group_credit.errors import GCParameterError
from apps.group_credit.models import (
    GCClaimType,
    GCHealthQuestion,
    GCHealthQuestionnaire,
    GCMedicalCode,
    GCMedicalLimit,
    GCProduct,
    GCSchemePremiumRate,
    GCSchemeType,
    GCSubProduct,
)
from apps.group_credit.services import (
    ClaimTypeValidator,
    ProductValidator,
    SchemeRateValidator,
)
from apps.users.models import User

API_ROOT = "/api/v1/gc"


class GCParameterAPIListingTests(TestCase):
    """Prompt 4 — List/Detail APIs return paginated, display-name data."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="gc-param-admin",
            email="gc-param-admin@example.com",
            password="Strong-pass-123!",
            is_superuser=True,
            is_staff=True,
            is_active=True,
            is_approved=True,
        )
        self.client.force_authenticate(self.user)

        self.scheme_type = GCSchemeType.objects.create(
            code="BANK_LOAN", name="Bank Loan", partner_type_restriction="BANK"
        )
        self.other_scheme = GCSchemeType.objects.create(
            code="CORPORATE", name="Corporate Salary"
        )
        self.sub_product = GCSubProduct.objects.create(
            code="LOAN_PROT", name="Loan Protection"
        )
        self.product = GCProduct.objects.create(
            code="LP_STANDARD",
            name="Loan Protection Standard",
            sub_product=self.sub_product,
            scheme_type_ref=self.scheme_type,
            max_loan_amount="10000000.00",
            free_cover_limit="2000000.00",
        )
        self.code = GCMedicalCode.objects.create(
            code="CVD001", name="Cardiovascular condition", category="ICD_10"
        )
        self.limit = GCMedicalLimit.objects.create(
            scheme_type_ref=self.scheme_type,
            medical_code_ref=self.code,
            limit_amount="5000000.00",
            age_min=18,
            age_max=65,
        )
        self.claim_type = GCClaimType.objects.create(
            code="DEATH", name="Death", category="DEATH"
        )

    def test_scheme_types_list_returns_paginated_envelope(self):
        response = self.client.get(f"{API_ROOT}/parameters/scheme-types/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["status_code"], 200)
        self.assertEqual(response.data["pagination"]["total"], 2)
        rows = response.data["data"]
        self.assertEqual(len(rows), 2)
        returned = {row["code"] for row in rows}
        self.assertEqual(returned, {"BANK_LOAN", "CORPORATE"})

    def test_scheme_type_detail_returns_display_name(self):
        response = self.client.get(
            f"{API_ROOT}/parameters/scheme-types/{self.scheme_type.pk}/"
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["code"], "BANK_LOAN")
        self.assertEqual(response.data["display_name"], "BANK_LOAN — Bank Loan")
        self.assertEqual(response.data["is_active"], True)

    def test_products_list_includes_display_names(self):
        response = self.client.get(f"{API_ROOT}/parameters/products/")
        self.assertEqual(response.status_code, 200, response.data)
        row = response.data["data"][0]
        self.assertEqual(row["code"], "LP_STANDARD")
        self.assertEqual(row["display_name"], "LP_STANDARD — Loan Protection Standard")
        self.assertEqual(row["scheme_type_ref_display"], "BANK_LOAN — Bank Loan")
        self.assertEqual(row["sub_product_display"], "LOAN_PROT — Loan Protection")

    def test_medical_codes_list_supports_filtering(self):
        GCMedicalCode.objects.create(code="HTN", name="Hypertension", category="INTERNAL")
        response = self.client.get(f"{API_ROOT}/parameters/medical/codes/?category=ICD_10")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["pagination"]["total"], 1)
        self.assertEqual(response.data["data"][0]["code"], "CVD001")

    def test_medical_limits_list_includes_relation_displays(self):
        response = self.client.get(f"{API_ROOT}/parameters/medical/limits/")
        self.assertEqual(response.status_code, 200, response.data)
        row = response.data["data"][0]
        self.assertEqual(row["display_name"], "Limits for BANK_LOAN - Bank Loan (Age 18-65)")
        self.assertEqual(row["scheme_type_ref_display"], "BANK_LOAN — Bank Loan")
        self.assertEqual(row["medical_code_ref_display"], "CVD001 — Cardiovascular condition")

    def test_claims_types_list_returns_display_name(self):
        response = self.client.get(f"{API_ROOT}/parameters/claims/types/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["pagination"]["total"], 1)
        self.assertEqual(response.data["data"][0]["display_name"], "DEATH — Death")

    def test_scheme_types_supports_search(self):
        response = self.client.get(f"{API_ROOT}/parameters/scheme-types/?search=corporate")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["pagination"]["total"], 1)
        self.assertEqual(response.data["data"][0]["code"], "CORPORATE")

    def test_list_respects_per_page_pagination(self):
        response = self.client.get(f"{API_ROOT}/parameters/scheme-types/?per_page=1")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["pagination"]["per_page"], 1)
        self.assertEqual(len(response.data["data"]), 1)


class GCOptionEndpointTests(TestCase):
    """Prompt 4 — SmartSelects options return {value, label, meta}."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="gc-option-user",
            email="gc-option-user@example.com",
            password="Strong-pass-123!",
            is_active=True,
            is_approved=True,
        )
        self.client.force_authenticate(self.user)

        self.scheme_type = GCSchemeType.objects.create(
            code="BANK_LOAN", name="Bank Loan", partner_type_restriction="BANK"
        )
        self.other_scheme = GCSchemeType.objects.create(
            code="CORPORATE", name="Corporate Salary"
        )
        self.sub_product = GCSubProduct.objects.create(
            code="LOAN_PROT", name="Loan Protection"
        )
        self.product = GCProduct.objects.create(
            code="LP_STANDARD",
            name="Loan Protection Standard",
            sub_product=self.sub_product,
            scheme_type_ref=self.scheme_type,
        )
        self.product_other = GCProduct.objects.create(
            code="CS_PLUS",
            name="Corporate Salary Plus",
            sub_product=self.sub_product,
            scheme_type_ref=self.other_scheme,
        )
        self.question = GCHealthQuestion.objects.create(
            code="SMOKING", question_text="Do you smoke?"
        )
        self.questionnaire = GCHealthQuestionnaire.objects.create(
            code="GC_HQ_V1",
            name="GC Health Questionnaire",
            version="1.0",
            scheme_type_ref=self.scheme_type,
            effective_date=date(2026, 1, 1),
        )
        self.claim_type = GCClaimType.objects.create(
            code="CI", name="Critical Illness", category="CRITICAL_ILLNESS"
        )

    def test_scheme_types_options_payload_shape(self):
        response = self.client.get(f"{API_ROOT}/options/scheme-types/")
        self.assertEqual(response.status_code, 200, response.data)
        by_value = {item["value"]: item for item in response.data}
        bank = by_value[str(self.scheme_type.pk)]
        self.assertEqual(bank["label"], "BANK_LOAN — Bank Loan")
        self.assertEqual(bank["meta"]["code"], "BANK_LOAN")
        self.assertEqual(bank["meta"]["partner_type_restriction"], "BANK")
        self.assertEqual(bank["meta"]["is_active"], True)
        self.assertEqual(len(response.data), 2)

    def test_products_options_filter_by_scheme_type_uuid(self):
        response = self.client.get(
            f"{API_ROOT}/options/products/?scheme_type={self.scheme_type.pk}"
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(len(response.data), 1)
        item = response.data[0]
        self.assertEqual(item["label"], "LP_STANDARD — Loan Protection Standard")
        self.assertEqual(item["meta"]["scheme_type_code"], "BANK_LOAN")
        self.assertEqual(item["meta"]["currency"], "TZS")

    def test_products_options_filter_by_scheme_type_code(self):
        response = self.client.get(
            f"{API_ROOT}/options/products/?scheme_type=CORPORATE"
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["value"], str(self.product_other.pk))

    def test_products_options_without_filter_returns_all(self):
        response = self.client.get(f"{API_ROOT}/options/products/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(len(response.data), 2)

    def test_questionnaires_options_include_version(self):
        response = self.client.get(f"{API_ROOT}/options/questionnaires/")
        self.assertEqual(response.status_code, 200, response.data)
        item = response.data[0]
        self.assertEqual(item["label"], "GC_HQ_V1 — GC Health Questionnaire")
        self.assertEqual(item["meta"]["version"], "1.0")

    def test_claim_types_options_include_category(self):
        response = self.client.get(f"{API_ROOT}/options/claim-types/")
        self.assertEqual(response.status_code, 200, response.data)
        item = response.data[0]
        self.assertEqual(item["label"], "CI — Critical Illness")
        self.assertEqual(item["meta"]["category"], "CRITICAL_ILLNESS")

    def test_options_support_search_and_exclude_inactive(self):
        self.other_scheme.is_active = False
        self.other_scheme.save()
        response = self.client.get(f"{API_ROOT}/options/scheme-types/?search=BANK")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["value"], str(self.scheme_type.pk))


class GCValidationServiceTests(TestCase):
    """Prompt 4 — validation services catch constraint violations."""

    def setUp(self):
        self.scheme_type = GCSchemeType.objects.create(
            code="VALIDATE", name="Validation"
        )

    def test_scheme_rate_validator_rejects_overlapping_window(self):
        GCSchemePremiumRate.objects.create(
            name="Open-ended rate",
            scheme_type=self.scheme_type,
            rate_type="UNIT",
            rate_value="3.000000",
            age_band_start=18,
            age_band_end=65,
            effective_date=date(2026, 1, 1),
            effective_from=date(2026, 1, 1),
            effective_to=None,
        )
        with self.assertRaises(GCParameterError) as ctx:
            SchemeRateValidator.validate(
                scheme_type_id=self.scheme_type.pk,
                effective_from=date(2026, 6, 1),
            )
        self.assertEqual(ctx.exception.code, "SCHEME_RATE_OVERLAP")
        self.assertEqual(ctx.exception.details["scheme_type_id"], str(self.scheme_type.pk))

    def test_scheme_rate_validator_accepts_non_overlapping_window(self):
        GCSchemePremiumRate.objects.create(
            name="Closed rate",
            scheme_type=self.scheme_type,
            rate_type="FLAT",
            rate_value="100000.000000",
            age_band_start=18,
            age_band_end=65,
            effective_date=date(2026, 1, 1),
            effective_from=date(2026, 1, 1),
            effective_to=date(2026, 3, 31),
        )
        self.assertTrue(
            SchemeRateValidator.validate(
                scheme_type_id=self.scheme_type.pk,
                effective_from=date(2026, 6, 1),
            )
        )

    def test_scheme_rate_validator_excludes_own_window(self):
        rate = GCSchemePremiumRate.objects.create(
            name="Self rate",
            scheme_type=self.scheme_type,
            rate_type="UNIT",
            rate_value="3.000000",
            age_band_start=18,
            age_band_end=65,
            effective_date=date(2026, 1, 1),
            effective_from=date(2026, 1, 1),
            effective_to=None,
        )
        self.assertTrue(
            SchemeRateValidator.validate(
                scheme_type_id=self.scheme_type.pk,
                effective_from=date(2026, 1, 1),
                exclude_id=rate.pk,
            )
        )

    def test_product_validator_rejects_inverted_age_band(self):
        with self.assertRaises(GCParameterError) as ctx:
            ProductValidator.validate(min_entry_age=65, max_entry_age=18)
        self.assertEqual(ctx.exception.code, "PRODUCT_INVALID_LIMITS")
        self.assertIn("min_entry_age", ctx.exception.details["problems"][0])

    def test_product_validator_rejects_free_cover_above_max_loan(self):
        with self.assertRaises(GCParameterError) as ctx:
            ProductValidator.validate(
                free_cover_limit="5000000.00", max_loan_amount="1000000.00"
            )
        self.assertEqual(ctx.exception.code, "PRODUCT_INVALID_LIMITS")

    def test_product_validator_rejects_negative_free_cover(self):
        with self.assertRaises(GCParameterError):
            ProductValidator.validate(free_cover_limit="-1.00")

    def test_product_validator_accepts_valid_limits(self):
        self.assertTrue(
            ProductValidator.validate(
                min_entry_age=18,
                max_entry_age=65,
                free_cover_limit="2000000.00",
                max_loan_amount="10000000.00",
            )
        )

    def test_claim_type_validator_rejects_duplicate_active_name(self):
        GCClaimType.objects.create(
            code="CI", name="Critical Illness", category="CRITICAL_ILLNESS"
        )
        with self.assertRaises(GCParameterError) as ctx:
            ClaimTypeValidator.validate(name="critical illness", category="CRITICAL_ILLNESS")
        self.assertEqual(ctx.exception.code, "CLAIM_TYPE_DUPLICATE")
        self.assertEqual(ctx.exception.details["name"], "Critical Illness")

    def test_claim_type_validator_allows_distinct_name_or_category(self):
        GCClaimType.objects.create(
            code="CI", name="Critical Illness", category="CRITICAL_ILLNESS"
        )
        self.assertTrue(ClaimTypeValidator.validate(name="Death", category="DEATH"))
        self.assertTrue(
            ClaimTypeValidator.validate(name="Critical Illness", category="DEATH")
        )

    def test_claim_type_validator_exclude_id(self):
        existing = GCClaimType.objects.create(
            code="CI", name="Critical Illness", category="CRITICAL_ILLNESS"
        )
        self.assertTrue(
            ClaimTypeValidator.validate(
                name="Critical Illness",
                category="CRITICAL_ILLNESS",
                exclude_id=existing.pk,
            )
        )


class GCParameterCSVExportTests(TestCase):
    """Prompt 4 — CSV export action on list endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="gc-export-user",
            email="gc-export-user@example.com",
            password="Strong-pass-123!",
            is_superuser=True,
            is_staff=True,
            is_active=True,
            is_approved=True,
        )
        self.client.force_authenticate(self.user)
        self.scheme_type = GCSchemeType.objects.create(
            code="EXPORT", name="Exportable"
        )

    def test_export_returns_csv_with_header_and_rows(self):
        response = self.client.get(f"{API_ROOT}/parameters/scheme-types/export/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response["Content-Type"])
        self.assertIn(
            'attachment; filename="gcschemetype.csv"',
            response["Content-Disposition"],
        )
        content = response.content.decode("utf-8")
        lines = content.strip().splitlines()
        self.assertEqual(lines[0].split(",")[0], "id")
        self.assertIn("display_name", lines[0])
        self.assertTrue(any("EXPORT" in line for line in lines))

    def test_export_respects_filters_and_search(self):
        response = self.client.get(
            f"{API_ROOT}/parameters/scheme-types/export/?search=nonexistent"
        )
        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")
        self.assertNotIn("EXPORT", content)
