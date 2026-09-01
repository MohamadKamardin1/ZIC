from datetime import date

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.governance.models import AuditLog
from apps.group_credit.errors import (
    GC_PARAMETERS_ERROR_REGISTRY,
    GCParameterError,
    scheme_not_found,
)
from apps.group_credit.models import (
    GCProduct,
    GCRider,
    GCRiderRate,
    GCSchemeType,
    GCSubProduct,
)


class GCProductSetupTests(TestCase):
    """Prompt 2 — product creation links to Scheme Type and validates relationships."""

    def setUp(self):
        self.scheme_type = GCSchemeType.objects.create(
            code="BANK_LOAN", name="Bank Loan", partner_type_restriction="BANK"
        )
        self.sub_product = GCSubProduct.objects.create(code="CL", name="Credit Life")

    def test_product_creation_links_to_scheme_type(self):
        product = GCProduct.objects.create(
            code="CL_A",
            name="Credit Life Plan A",
            scheme_type_ref=self.scheme_type,
            sub_product=self.sub_product,
            insurance_class="CREDIT_LIFE",
            premium_basis="SINGLE",
            requires_medical=True,
            min_loan_term=12,
            max_loan_term=240,
        )
        self.assertEqual(product.scheme_type_ref, self.scheme_type)
        self.assertEqual(self.scheme_type.products.count(), 1)
        self.assertEqual(product.premium_basis, "SINGLE")
        self.assertTrue(product.requires_medical)
        self.assertEqual(product.min_loan_term, 12)
        self.assertEqual(product.max_loan_term, 240)

    def test_product_rejects_missing_scheme_type(self):
        product = GCProduct(
            code="CL_B", name="Credit Life Plan B", sub_product=self.sub_product
        )
        with self.assertRaises(ValidationError) as ctx:
            product.full_clean()
        self.assertIn("PRODUCT_INVALID_SCHEME", str(ctx.exception))

    def test_product_rejects_inactive_scheme_type(self):
        self.scheme_type.is_active = False
        self.scheme_type.save()
        product = GCProduct(
            code="CL_C",
            name="Credit Life Plan C",
            scheme_type_ref=self.scheme_type,
            sub_product=self.sub_product,
        )
        with self.assertRaises(ValidationError) as ctx:
            product.full_clean()
        self.assertIn("PRODUCT_INVALID_SCHEME", str(ctx.exception))

    def test_product_validates_age_band(self):
        product = GCProduct(
            code="CL_D",
            name="Credit Life Plan D",
            scheme_type_ref=self.scheme_type,
            sub_product=self.sub_product,
            min_entry_age=65,
            max_entry_age=40,
        )
        with self.assertRaises(ValidationError):
            product.full_clean()

    def test_product_validates_loan_term(self):
        product = GCProduct(
            code="CL_E",
            name="Credit Life Plan E",
            scheme_type_ref=self.scheme_type,
            sub_product=self.sub_product,
            min_loan_term=300,
            max_loan_term=120,
        )
        with self.assertRaises(ValidationError):
            product.full_clean()


class GCRiderSetupTests(TestCase):
    """Prompt 2 — rider creation links to product and rates validate consistently."""

    def setUp(self):
        scheme_type = GCSchemeType.objects.create(
            code="CORPORATE_SALARY", name="Corporate Salary", partner_type_restriction="CORPORATE"
        )
        sub_product = GCSubProduct.objects.create(code="CL", name="Credit Life")
        self.product = GCProduct.objects.create(
            code="CL_A",
            name="Credit Life Plan A",
            scheme_type_ref=scheme_type,
            sub_product=sub_product,
        )
        self.rider = GCRider.objects.create(
            code="ADB",
            name="Accidental Death Benefit",
            rider_category="ACCIDENTAL_DEATH",
            benefit_type="PERCENTAGE",
            requires_underwriting=True,
        )

    def test_rider_creation_links_to_product(self):
        rate = GCRiderRate.objects.create(
            rider=self.rider,
            product_ref=self.product,
            rate_type="PERCENTAGE",
            rate_value="25.000000",
            currency="TZS",
            age_band_start=18,
            age_band_end=65,
            effective_date=date(2026, 1, 1),
            effective_from=date(2026, 1, 1),
            effective_to=None,
        )
        self.assertEqual(rate.product_ref, self.product)
        self.assertEqual(rate.rider, self.rider)
        self.assertEqual(self.product.rider_rates.count(), 1)
        self.assertEqual(self.rider.rider_category, "ACCIDENTAL_DEATH")
        self.assertEqual(self.rider.benefit_type, "PERCENTAGE")
        self.assertTrue(self.rider.requires_underwriting)

    def test_rider_rate_rejects_negative_value(self):
        rate = GCRiderRate(
            rider=self.rider,
            product_ref=self.product,
            rate_type="FIXED",
            rate_value="-100.000000",
            age_band_start=18,
            age_band_end=65,
            effective_date=date(2026, 1, 1),
        )
        with self.assertRaises(ValidationError) as ctx:
            rate.full_clean()
        self.assertIn("RATE_MISMATCH", str(ctx.exception))

    def test_rider_rate_rejects_percentage_outside_bounds(self):
        rate = GCRiderRate(
            rider=self.rider,
            product_ref=self.product,
            rate_type="PERCENTAGE",
            rate_value="150.000000",
            age_band_start=18,
            age_band_end=65,
            effective_date=date(2026, 1, 1),
        )
        with self.assertRaises(ValidationError) as ctx:
            rate.full_clean()
        self.assertIn("RATE_MISMATCH", str(ctx.exception))

    def test_rider_rate_rejects_invalid_effective_window(self):
        rate = GCRiderRate(
            rider=self.rider,
            product_ref=self.product,
            rate_type="FIXED",
            rate_value="1000.000000",
            age_band_start=18,
            age_band_end=65,
            effective_date=date(2026, 1, 1),
            effective_from=date(2026, 12, 31),
            effective_to=date(2026, 1, 1),
        )
        with self.assertRaises(ValidationError) as ctx:
            rate.full_clean()
        self.assertIn("RATE_MISMATCH", str(ctx.exception))


class GCProductRiderAuditTests(TestCase):
    """Prompt 2 — audit rows created for product and rider changes."""

    def setUp(self):
        self.scheme_type = GCSchemeType.objects.create(code="BANK_LOAN", name="Bank Loan")
        self.sub_product = GCSubProduct.objects.create(code="CL", name="Credit Life")

    def test_product_and_rider_changes_are_audited(self):
        product = GCProduct.objects.create(
            code="CL_A",
            name="Credit Life Plan A",
            scheme_type_ref=self.scheme_type,
            sub_product=self.sub_product,
        )
        self.assertTrue(
            AuditLog.objects.filter(action="CREATE", entity_id=product.pk).exists()
        )

        product.name = "Credit Life Plan A (Revised)"
        product.save()
        self.assertTrue(
            AuditLog.objects.filter(action="UPDATE", entity_id=product.pk).exists()
        )
        update_log = (
            AuditLog.objects.filter(action="UPDATE", entity_id=product.pk)
            .order_by("-timestamp")
            .first()
        )
        self.assertIn("name", update_log.changed_fields)
        self.assertEqual(update_log.before_state.get("name"), "Credit Life Plan A")
        self.assertEqual(update_log.after_state.get("name"), "Credit Life Plan A (Revised)")

        rider = GCRider.objects.create(code="ADB", name="Accidental Death Benefit")
        self.assertTrue(
            AuditLog.objects.filter(action="CREATE", entity_id=rider.pk).exists()
        )


class GCParameterErrorRegistryTests(TestCase):
    """Prompt 2 — structured error registry exposes the required codes."""

    def test_registry_contains_required_codes(self):
        for code in ("SCHEME_NOT_FOUND", "PRODUCT_INVALID_SCHEME", "RATE_MISMATCH"):
            self.assertIn(code, GC_PARAMETERS_ERROR_REGISTRY)
            self.assertIn("message", GC_PARAMETERS_ERROR_REGISTRY[code])
            self.assertIn("status_code", GC_PARAMETERS_ERROR_REGISTRY[code])

    def test_registry_error_raises_structured_exception(self):
        error = scheme_not_found()
        self.assertIsInstance(error, GCParameterError)
        self.assertEqual(error.code, "SCHEME_NOT_FOUND")
        self.assertEqual(error.error_code, "SCHEME_NOT_FOUND")
        self.assertEqual(error.status_code, 404)
