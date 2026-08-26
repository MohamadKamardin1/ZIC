from datetime import date
from decimal import Decimal

from apps.governance.models import AuditLog
from apps.ol_parameters.models import OLAgentCommissionSetup, OLParameterTableRegistry, OLPlanType, OLProduct
from apps.users.models import User
from django.contrib import admin
from django.core import management
from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework.test import APIClient


class OLAgentManagementTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="ol-agent-management-admin",
            email="ol-agent-management-admin@example.com",
            password="Strong-pass-123!",
            is_superuser=True,
            is_staff=True,
            is_active=True,
            is_approved=True,
        )
        self.client.force_authenticate(self.user)
        self.plan_type = OLPlanType.objects.create(
            code="ENDOWMENT",
            name="Endowment",
            description="Endowment plan type.",
            plan_category="INDIVIDUAL",
            effective_from=date(2026, 1, 1),
        )
        self.product = OLProduct.objects.create(
            code="STANDARD_ENDOWMENT",
            name="Standard Endowment",
            description="Standard endowment product.",
            plan_type=self.plan_type,
            insurance_class="INDIVIDUAL",
            currency="TZS",
            min_entry_age=18,
            max_entry_age=65,
            min_term=5,
            max_term=30,
            min_sum_assured=Decimal("1000000.00"),
            max_sum_assured=Decimal("1000000000.00"),
            premium_frequencies=["MONTHLY", "ANNUAL"],
            allow_riders=True,
            allow_loans=True,
            allow_surrender=True,
            allow_paidup=True,
            allow_bonus=True,
            effective_from=date(2026, 1, 1),
        )

    def payload(self, code="AGENCY_FIRST_PREMIUM_2026", effective_to=None):
        return {
            "code": code,
            "name": "Agency First Premium Commission",
            "description": "Agency first premium commission rule.",
            "partner": None,
            "intermediary_type": "AGENT",
            "distribution_channel": "AGENCY",
            "product": str(self.product.pk),
            "plan": None,
            "rider": None,
            "currency": "TZS",
            "branch": None,
            "commission_type": "FIRST_PREMIUM",
            "premium_year_from": 1,
            "premium_year_to": 1,
            "policy_year_from": 1,
            "policy_year_to": 1,
            "rate_type": "PERCENTAGE",
            "rate_value": "10.00000000",
            "minimum_commission": "0.00000000",
            "maximum_commission": "1000000.00000000",
            "priority": 100,
            "effective_from": "2026-01-01",
            "effective_to": effective_to,
            "is_active": True,
            "reason": "Initial commercial configuration.",
        }

    def test_commission_setup_supports_crud_filters_export_and_deactivation(self):
        response = self.client.post(
            "/api/v1/ol-parameters/agent-commission-setups/",
            self.payload(),
            format="json",
            HTTP_X_REQUEST_ID="agent-commission-create",
        )
        self.assertEqual(response.status_code, 201, response.data)
        record = OLAgentCommissionSetup.objects.get(code="AGENCY_FIRST_PREMIUM_2026")

        patch = self.client.patch(
            f"/api/v1/ol-parameters/agent-commission-setups/{record.pk}/",
            {"rate_value": "12.50000000", "priority": 10},
            format="json",
            HTTP_X_REQUEST_ID="agent-commission-update",
        )
        self.assertEqual(patch.status_code, 200, patch.data)
        record.refresh_from_db()
        self.assertEqual(record.rate_value, Decimal("12.50000000"))
        self.assertEqual(record.priority, 10)

        retrieve = self.client.get(f"/api/v1/ol-parameters/agent-commission-setups/{record.pk}/")
        self.assertEqual(retrieve.status_code, 200, retrieve.data)
        listing = self.client.get(
            "/api/v1/ol-parameters/agent-commission-setups/"
            f"?product={self.product.pk}&commission_type=FIRST_PREMIUM&distribution_channel=AGENCY&rate_type=PERCENTAGE"
        )
        self.assertEqual(listing.status_code, 200, listing.data)
        self.assertEqual(listing.data["pagination"]["total"], 1)
        self.assertEqual(listing.data["data"][0]["code"], "AGENCY_FIRST_PREMIUM_2026")

        export = self.client.get("/api/v1/ol-parameters/agent-commission-setups/export/?product=" + str(self.product.pk))
        self.assertEqual(export.status_code, 200)
        self.assertIn("text/csv", export["Content-Type"])
        self.assertIn("AGENCY_FIRST_PREMIUM_2026", export.content.decode())

        deactivate = self.client.post(
            f"/api/v1/ol-parameters/agent-commission-setups/{record.pk}/deactivate/",
            {},
            format="json",
            HTTP_X_REQUEST_ID="agent-commission-deactivate",
        )
        self.assertEqual(deactivate.status_code, 200, deactivate.data)
        record.refresh_from_db()
        self.assertFalse(record.is_active)

    def test_invalid_rates_ranges_currency_and_dates_are_rejected(self):
        invalid_payloads = [
            {**self.payload("INVALID_PERCENTAGE"), "rate_value": "100.00000001"},
            {**self.payload("INVALID_MIN_MAX"), "minimum_commission": "20", "maximum_commission": "10"},
            {**self.payload("INVALID_PREMIUM_YEARS"), "premium_year_from": 3, "premium_year_to": 2},
            {**self.payload("INVALID_POLICY_YEARS"), "policy_year_from": 3, "policy_year_to": 2},
            {**self.payload("INVALID_CURRENCY"), "currency": "TZ"},
        ]
        for payload in invalid_payloads:
            response = self.client.post(
                "/api/v1/ol-parameters/agent-commission-setups/", payload, format="json"
            )
            self.assertEqual(response.status_code, 400, response.data)

        invalid_dates = self.payload("INVALID_EFFECTIVE_DATES", effective_to="2025-12-31")
        response = self.client.post(
            "/api/v1/ol-parameters/agent-commission-setups/", invalid_dates, format="json"
        )
        self.assertEqual(response.status_code, 400, response.data)

    def test_same_scope_and_overlapping_effective_and_year_ranges_are_rejected(self):
        first = OLAgentCommissionSetup(
            code="AGENCY_OVERLAP_1",
            name="Agency Overlap One",
            intermediary_type="AGENT",
            distribution_channel="AGENCY",
            product=self.product,
            currency="TZS",
            commission_type="FIRST_PREMIUM",
            premium_year_from=1,
            premium_year_to=2,
            policy_year_from=1,
            policy_year_to=2,
            rate_type="PERCENTAGE",
            rate_value=Decimal("10"),
            effective_from=date(2026, 1, 1),
            effective_to=date(2026, 12, 31),
        )
        first.full_clean()
        first.save()

        second = OLAgentCommissionSetup(
            code="AGENCY_OVERLAP_2",
            name="Agency Overlap Two",
            intermediary_type="AGENT",
            distribution_channel="AGENCY",
            product=self.product,
            currency="TZS",
            commission_type="FIRST_PREMIUM",
            premium_year_from=2,
            premium_year_to=3,
            policy_year_from=2,
            policy_year_to=3,
            rate_type="PERCENTAGE",
            rate_value=Decimal("12"),
            effective_from=date(2026, 6, 1),
            effective_to=date(2027, 5, 31),
        )
        with self.assertRaises(ValidationError):
            second.full_clean()

    def test_non_overlapping_effective_or_premium_period_is_allowed(self):
        first = OLAgentCommissionSetup(
            code="AGENCY_NON_OVERLAP_1",
            name="Agency 2026",
            intermediary_type="AGENT",
            distribution_channel="AGENCY",
            product=self.product,
            currency="TZS",
            commission_type="FIRST_PREMIUM",
            premium_year_from=1,
            premium_year_to=1,
            policy_year_from=1,
            policy_year_to=1,
            rate_type="PERCENTAGE",
            rate_value=Decimal("10"),
            effective_from=date(2026, 1, 1),
            effective_to=date(2026, 12, 31),
        )
        first.full_clean()
        first.save()
        second = OLAgentCommissionSetup(
            code="AGENCY_NON_OVERLAP_2",
            name="Agency 2027",
            intermediary_type="AGENT",
            distribution_channel="AGENCY",
            product=self.product,
            currency="TZS",
            commission_type="FIRST_PREMIUM",
            premium_year_from=1,
            premium_year_to=1,
            policy_year_from=1,
            policy_year_to=1,
            rate_type="PERCENTAGE",
            rate_value=Decimal("11"),
            effective_from=date(2027, 1, 1),
            effective_to=None,
        )
        second.full_clean()
        second.save()
        self.assertEqual(OLAgentCommissionSetup.objects.count(), 2)

    def test_permissions_and_audit_logs_are_enforced(self):
        created = self.client.post(
            "/api/v1/ol-parameters/agent-commission-setups/",
            self.payload(),
            format="json",
            HTTP_X_REQUEST_ID="agent-commission-audit-create",
        )
        self.assertEqual(created.status_code, 201, created.data)
        record = OLAgentCommissionSetup.objects.get(code="AGENCY_FIRST_PREMIUM_2026")
        self.assertTrue(
            AuditLog.objects.filter(
                app_label="ol_parameters",
                model_name="olagentcommissionsetup",
                object_id=str(record.pk),
                action="CREATE",
                correlation_id="agent-commission-audit-create",
            ).exists()
        )

        restricted_user = User.objects.create_user(
            username="ol-agent-management-viewer",
            email="ol-agent-management-viewer@example.com",
            password="Strong-pass-123!",
            is_active=True,
            is_approved=True,
        )
        restricted_client = APIClient()
        restricted_client.force_authenticate(restricted_user)
        self.assertEqual(
            restricted_client.get("/api/v1/ol-parameters/agent-commission-setups/").status_code,
            403,
        )

    def test_seed_is_idempotent_and_registers_contract(self):
        management.call_command("seed_ol_agent_management", verbosity=0)
        first_counts = (
            OLAgentCommissionSetup.objects.count(),
            OLParameterTableRegistry.objects.filter(slug="agent-commission-setups").count(),
        )
        management.call_command("seed_ol_agent_management", verbosity=0)
        second_counts = (
            OLAgentCommissionSetup.objects.count(),
            OLParameterTableRegistry.objects.filter(slug="agent-commission-setups").count(),
        )
        self.assertEqual(first_counts, second_counts)
        self.assertEqual(first_counts, (1, 1))

    def test_admin_registration_and_table_columns_exist(self):
        self.assertIn(OLAgentCommissionSetup, admin.site._registry)
        model_admin = admin.site._registry[OLAgentCommissionSetup]
        self.assertTrue(model_admin.list_display)
        self.assertIn("commission_type", model_admin.list_display)
        self.assertIn("rate_value", model_admin.list_display)
