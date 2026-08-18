from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework.test import APIClient

from apps.governance.models import AuditLog
from apps.ol_parameters.models import (
    OLComputationApproach,
    OLDefaultSystemParameter,
    OLMaturityClaimSetup,
    OLOverrideCommissionSetup,
)
from apps.users.models import User


class OLDefaultSetupTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="ol-default-setup-admin",
            email="ol-default-setup-admin@example.com",
            password="Strong-pass-123!",
            is_superuser=True,
            is_staff=True,
            is_active=True,
            is_approved=True,
        )
        self.client.force_authenticate(self.user)

    def test_typed_default_system_parameter_is_normalized_and_exposed(self):
        response = self.client.post(
            "/api/v1/ol-parameters/default-system-parameters/",
            {
                "parameter_key": "grace_period_days",
                "name": "Grace Period Days",
                "parameter_category": "lifecycle",
                "description": "Default grace period.",
                "value_type": "INTEGER",
                "typed_value": "30",
                "effective_from": "2026-01-01",
            },
            format="json",
            HTTP_X_REQUEST_ID="ol-default-typed-create",
        )
        self.assertEqual(response.status_code, 201, response.data)
        record = OLDefaultSystemParameter.objects.get(parameter_key="GRACE_PERIOD_DAYS")
        self.assertEqual(record.code, "GRACE_PERIOD_DAYS")
        self.assertEqual(record.integer_value, 30)
        self.assertIsNone(record.string_value)
        self.assertEqual(response.data["value"], 30)
        self.assertTrue(
            AuditLog.objects.filter(
                app_label="ol_parameters",
                model_name="oldefaultsystemparameter",
                object_id=str(record.pk),
                action="CREATE",
                correlation_id="ol-default-typed-create",
            ).exists()
        )

    def test_typed_default_rejects_invalid_value(self):
        response = self.client.post(
            "/api/v1/ol-parameters/default-system-parameters/",
            {
                "code": "INVALID_DAYS",
                "name": "Invalid Days",
                "parameter_category": "lifecycle",
                "value_type": "INTEGER",
                "typed_value": "not-an-integer",
                "effective_from": "2026-01-01",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("typed_value", response.data["error"]["details"])

    def test_typed_default_update_clears_stale_storage_column(self):
        record = OLDefaultSystemParameter.objects.create(
            code="MAX_AGE",
            parameter_key="MAX_AGE",
            name="Maximum Age",
            parameter_category="UNDERWRITING",
            value_type="INTEGER",
            integer_value=65,
            effective_from=date(2026, 1, 1),
        )
        response = self.client.patch(
            f"/api/v1/ol-parameters/default-system-parameters/{record.pk}/",
            {"value_type": "STRING", "typed_value": "sixty-five"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        record.refresh_from_db()
        self.assertEqual(record.string_value, "sixty-five")
        self.assertIsNone(record.integer_value)

    def test_commission_override_rejects_same_scope_and_overlapping_effective_period(self):
        first = OLOverrideCommissionSetup(
            code="COMM_001",
            name="First Year Commission",
            effective_from=date(2026, 1, 1),
            effective_to=date(2026, 12, 31),
            rate_type="PERCENTAGE",
            rate_value=Decimal("10"),
            premium_year_from=1,
            premium_year_to=1,
        )
        first.full_clean()
        first.save()

        second = OLOverrideCommissionSetup(
            code="COMM_002",
            name="Overlapping First Year Commission",
            effective_from=date(2026, 6, 1),
            effective_to=date(2027, 5, 31),
            rate_type="PERCENTAGE",
            rate_value=Decimal("12"),
            premium_year_from=1,
            premium_year_to=1,
        )
        with self.assertRaises(ValidationError):
            second.full_clean()

    def test_commission_override_allows_non_overlapping_period(self):
        first = OLOverrideCommissionSetup(
            code="COMM_003",
            name="2026 Commission",
            effective_from=date(2026, 1, 1),
            effective_to=date(2026, 12, 31),
            rate_type="PERCENTAGE",
            rate_value=Decimal("10"),
        )
        first.full_clean()
        first.save()
        second = OLOverrideCommissionSetup(
            code="COMM_004",
            name="2027 Commission",
            effective_from=date(2027, 1, 1),
            effective_to=None,
            rate_type="PERCENTAGE",
            rate_value=Decimal("11"),
        )
        second.full_clean()
        second.save()
        self.assertEqual(OLOverrideCommissionSetup.objects.count(), 2)

    def test_computation_approach_and_maturity_setup_are_available_as_tables(self):
        approach_response = self.client.post(
            "/api/v1/ol-parameters/computation-approaches/",
            {
                "code": "FIRST_PREMIUM_STANDARD",
                "name": "First Premium Standard",
                "description": "Standard first premium calculation.",
                "effective_from": "2026-01-01",
                "calculation_area": "PREMIUM",
                "calculation_basis": "FIRST_PREMIUM",
                "formula_key": "ol.first_premium.standard",
                "sequence": 1,
                "configuration": {"rounding": "HALF_UP"},
            },
            format="json",
        )
        self.assertEqual(approach_response.status_code, 201, approach_response.data)

        maturity_response = self.client.post(
            "/api/v1/ol-parameters/maturity-claim-setups/",
            {
                "code": "MATURITY_DEFAULT",
                "name": "Maturity Claim Default",
                "description": "Default maturity claim behavior.",
                "effective_from": "2026-01-01",
                "auto_create_maturity_claim": True,
                "days_before_maturity_to_initiate": 30,
                "notification_days": 60,
                "default_payout_method": "bank_transfer",
                "require_documents": True,
                "require_approval": True,
                "maturity_claim_status_to_create": "reported",
            },
            format="json",
        )
        self.assertEqual(maturity_response.status_code, 201, maturity_response.data)
        maturity = OLMaturityClaimSetup.objects.get(code="MATURITY_DEFAULT")
        self.assertEqual(maturity.default_payout_method, "BANK_TRANSFER")
        self.assertEqual(maturity.maturity_claim_status_to_create, "REPORTED")

    def test_default_setup_table_filter_and_csv_export(self):
        OLComputationApproach.objects.create(
            code="PREMIUM_BASIC",
            name="Basic Premium",
            calculation_area="PREMIUM",
            calculation_basis="SUM_ASSURED",
            formula_key="ol.premium.basic",
            effective_from=date(2026, 1, 1),
        )
        OLComputationApproach.objects.create(
            code="CLAIM_BASIC",
            name="Basic Claim",
            calculation_area="CLAIM",
            calculation_basis="SUM_ASSURED",
            formula_key="ol.claim.basic",
            effective_from=date(2026, 1, 1),
        )
        response = self.client.get(
            "/api/v1/ol-parameters/computation-approaches/?calculation_area=PREMIUM&search=Basic"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["data"]), 1)
        self.assertEqual(response.data["data"][0]["code"], "PREMIUM_BASIC")

        export_response = self.client.get("/api/v1/ol-parameters/computation-approaches/export/")
        self.assertEqual(export_response.status_code, 200)
        self.assertIn("text/csv", export_response["Content-Type"])
        self.assertIn("PREMIUM_BASIC", export_response.content.decode())

    def test_deactivation_is_soft_and_audited(self):
        approach = OLComputationApproach.objects.create(
            code="DEACTIVATABLE",
            name="Deactivatable",
            calculation_area="PREMIUM",
            calculation_basis="SUM_ASSURED",
            formula_key="ol.premium.deactivatable",
            effective_from=date(2026, 1, 1),
        )
        response = self.client.post(
            f"/api/v1/ol-parameters/computation-approaches/{approach.pk}/deactivate/",
            {},
            format="json",
            HTTP_X_REQUEST_ID="ol-default-deactivate",
        )
        self.assertEqual(response.status_code, 200)
        approach.refresh_from_db()
        self.assertFalse(approach.is_active)
        self.assertTrue(
            AuditLog.objects.filter(
                app_label="ol_parameters",
                model_name="olcomputationapproach",
                object_id=str(approach.pk),
                action="DEACTIVATE",
                correlation_id="ol-default-deactivate",
            ).exists()
        )
