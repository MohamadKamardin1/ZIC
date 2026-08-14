from io import StringIO

from django.core import management
from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.governance.models import AuditLog
from apps.ordinary_life.models import OLProduct, OLProductVersion, OLRateBand
from apps.ordinary_life.validation import validate_reference_data


class OrdinaryLifePhase4ConfigurationTests(TestCase):
    def test_reference_seed_is_idempotent(self):
        first_output = StringIO()
        management.call_command("seed_ordinary_life_reference_data", stdout=first_output)
        first_counts = {
            "products": OLProduct.objects.count(),
            "versions": OLProductVersion.objects.count(),
            "rate_bands": OLRateBand.objects.count(),
        }
        second_output = StringIO()
        management.call_command("seed_ordinary_life_reference_data", stdout=second_output)
        self.assertEqual(first_counts["products"], OLProduct.objects.count())
        self.assertEqual(first_counts["versions"], OLProductVersion.objects.count())
        self.assertEqual(first_counts["rate_bands"], OLRateBand.objects.count())
        self.assertIn("created", second_output.getvalue())

    def test_seeded_reference_data_passes_validator(self):
        management.call_command("seed_ordinary_life_reference_data", stdout=StringIO())
        self.assertTrue(validate_reference_data())

    def test_validator_rejects_active_version_without_rate_band(self):
        product = OLProduct.objects.create(code="PH4-NO-RATE", name="No Rate Product", business_area="ORDINARY_LIFE")
        OLProductVersion.objects.create(
            product=product,
            version_number=1,
            effective_from="2026-01-01",
            min_entry_age=18,
            max_entry_age=65,
            min_term_years=5,
            max_term_years=30,
            is_active=True,
        )
        with self.assertRaises(ValidationError):
            validate_reference_data()

    def test_material_product_creation_is_audited(self):
        product = OLProduct.objects.create(code="PH4-AUDIT", name="Audited Product", business_area="ORDINARY_LIFE")
        self.assertTrue(
            AuditLog.objects.filter(
                app_label="ordinary_life",
                model_name="olproduct",
                object_id=str(product.pk),
                action="CREATE",
            ).exists()
        )

    def test_material_product_update_records_changed_fields(self):
        product = OLProduct.objects.create(code="PH4-UPDATE", name="Before", business_area="ORDINARY_LIFE")
        product.name = "After"
        product.save()
        audit = AuditLog.objects.filter(
            app_label="ordinary_life",
            model_name="olproduct",
            object_id=str(product.pk),
            action="UPDATE",
        ).latest("created_at")
        self.assertIn("name", audit.changed_fields)
        self.assertEqual(audit.before_state["name"], "Before")
        self.assertEqual(audit.after_state["name"], "After")
