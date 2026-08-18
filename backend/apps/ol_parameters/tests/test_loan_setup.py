from datetime import date
from decimal import Decimal

from django.contrib import admin
from django.core import management
from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework.test import APIClient

from apps.governance.models import AuditLog
from apps.ol_parameters.models import (
    OLLoanInterestControl,
    OLLoanSystemSetup,
    OLParameterTableRegistry,
    OLPlanType,
    OLProduct,
)
from apps.users.models import User


class OLLoanSetupTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="ol-loan-setup-admin",
            email="ol-loan-setup-admin@example.com",
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

    def system_payload(self, code="POLICY_LOAN_2026", effective_to=None):
        return {
            "code": code,
            "name": "Policy Loan Configuration",
            "description": "Loan configuration for standard endowment.",
            "product": str(self.product.pk),
            "plan": None,
            "allow_policy_loans": True,
            "loan_basis": "CASH_VALUE",
            "max_loan_percentage_of_cash_value": "80.00000000",
            "min_loan_amount": "100000.00",
            "max_loan_amount": "10000000.00",
            "loan_currency": "TZS",
            "repayment_options": [
                {"code": "LUMP_SUM", "enabled": True},
                {"code": "PAYMENT_SCHEDULE", "enabled": True},
            ],
            "auto_deduct_from_benefits": True,
            "effect_on_claim": "DEDUCT_BALANCE",
            "effect_on_surrender": "DEDUCT_BALANCE",
            "effect_on_maturity": "DEDUCT_BALANCE",
            "require_approval": False,
            "effective_from": "2026-01-01",
            "effective_to": effective_to,
            "is_active": True,
        }

    def interest_payload(self, code="POLICY_LOAN_INTEREST_2026", effective_to=None):
        return {
            "code": code,
            "name": "Policy Loan Interest Control",
            "description": "Interest configuration for standard endowment loans.",
            "product": str(self.product.pk),
            "plan": None,
            "interest_rate": "8.00000000",
            "compounding_frequency": "ANNUAL",
            "interest_calculation_basis": "COMPOUND",
            "grace_period_days": 30,
            "penalty_interest_rate": "2.00000000",
            "interest_suspension_rule": "SUSPEND_DURING_APPROVED_CLAIM_REVIEW",
            "capitalize_interest": True,
            "effective_from": "2026-01-01",
            "effective_to": effective_to,
            "is_active": True,
        }

    def test_loan_system_setup_supports_crud_filters_export_and_deactivation(self):
        response = self.client.post(
            "/api/v1/ol-parameters/loan-system-setups/",
            self.system_payload(),
            format="json",
            HTTP_X_REQUEST_ID="loan-system-create",
        )
        self.assertEqual(response.status_code, 201, response.data)
        record = OLLoanSystemSetup.objects.get(code="POLICY_LOAN_2026")

        patch = self.client.patch(
            f"/api/v1/ol-parameters/loan-system-setups/{record.pk}/",
            {"max_loan_percentage_of_cash_value": "75.00000000", "require_approval": True},
            format="json",
            HTTP_X_REQUEST_ID="loan-system-update",
        )
        self.assertEqual(patch.status_code, 200, patch.data)
        record.refresh_from_db()
        self.assertEqual(record.max_loan_percentage_of_cash_value, Decimal("75.00000000"))
        self.assertTrue(record.require_approval)

        retrieve = self.client.get(f"/api/v1/ol-parameters/loan-system-setups/{record.pk}/")
        self.assertEqual(retrieve.status_code, 200, retrieve.data)
        listing = self.client.get(
            "/api/v1/ol-parameters/loan-system-setups/"
            f"?product={self.product.pk}&loan_basis=CASH_VALUE&loan_currency=TZS"
        )
        self.assertEqual(listing.status_code, 200, listing.data)
        self.assertEqual(listing.data["pagination"]["total"], 1)
        self.assertEqual(listing.data["data"][0]["code"], "POLICY_LOAN_2026")

        export = self.client.get(
            "/api/v1/ol-parameters/loan-system-setups/export/?product=" + str(self.product.pk)
        )
        self.assertEqual(export.status_code, 200)
        self.assertIn("text/csv", export["Content-Type"])
        self.assertIn("POLICY_LOAN_2026", export.content.decode())

        deactivate = self.client.post(
            f"/api/v1/ol-parameters/loan-system-setups/{record.pk}/deactivate/",
            {},
            format="json",
            HTTP_X_REQUEST_ID="loan-system-deactivate",
        )
        self.assertEqual(deactivate.status_code, 200, deactivate.data)
        record.refresh_from_db()
        self.assertFalse(record.is_active)

    def test_loan_interest_control_supports_crud_filters_and_export(self):
        response = self.client.post(
            "/api/v1/ol-parameters/loan-interest-controls/",
            self.interest_payload(),
            format="json",
            HTTP_X_REQUEST_ID="loan-interest-create",
        )
        self.assertEqual(response.status_code, 201, response.data)
        record = OLLoanInterestControl.objects.get(code="POLICY_LOAN_INTEREST_2026")

        patch = self.client.patch(
            f"/api/v1/ol-parameters/loan-interest-controls/{record.pk}/",
            {"interest_rate": "9.00000000", "capitalize_interest": False},
            format="json",
            HTTP_X_REQUEST_ID="loan-interest-update",
        )
        self.assertEqual(patch.status_code, 200, patch.data)
        record.refresh_from_db()
        self.assertEqual(record.interest_rate, Decimal("9.00000000"))
        self.assertFalse(record.capitalize_interest)

        listing = self.client.get(
            "/api/v1/ol-parameters/loan-interest-controls/"
            f"?product={self.product.pk}&compounding_frequency=ANNUAL&interest_calculation_basis=COMPOUND"
        )
        self.assertEqual(listing.status_code, 200, listing.data)
        self.assertEqual(listing.data["pagination"]["total"], 1)
        self.assertEqual(listing.data["data"][0]["code"], "POLICY_LOAN_INTEREST_2026")

        export = self.client.get(
            "/api/v1/ol-parameters/loan-interest-controls/export/?product=" + str(self.product.pk)
        )
        self.assertEqual(export.status_code, 200)
        self.assertIn("text/csv", export["Content-Type"])
        self.assertIn("POLICY_LOAN_INTEREST_2026", export.content.decode())

    def test_invalid_percentages_amounts_choices_and_dates_are_rejected(self):
        invalid_system_payloads = [
            {**self.system_payload("INVALID_LOAN_PERCENTAGE"), "max_loan_percentage_of_cash_value": "100.00000001"},
            {**self.system_payload("INVALID_MIN_AMOUNT"), "min_loan_amount": "0"},
            {**self.system_payload("INVALID_MAX_AMOUNT"), "min_loan_amount": "1000", "max_loan_amount": "999"},
            {**self.system_payload("INVALID_CURRENCY"), "loan_currency": "TZ"},
            {**self.system_payload("INVALID_EFFECT"), "effect_on_claim": "UNSUPPORTED"},
        ]
        for payload in invalid_system_payloads:
            response = self.client.post(
                "/api/v1/ol-parameters/loan-system-setups/", payload, format="json"
            )
            self.assertEqual(response.status_code, 400, response.data)

        invalid_interest_payloads = [
            {**self.interest_payload("INVALID_INTEREST_RATE"), "interest_rate": "100.00000001"},
            {**self.interest_payload("INVALID_PENALTY_RATE"), "penalty_interest_rate": "-0.1"},
            {**self.interest_payload("INVALID_FREQUENCY"), "compounding_frequency": "WEEKLY"},
        ]
        for payload in invalid_interest_payloads:
            response = self.client.post(
                "/api/v1/ol-parameters/loan-interest-controls/", payload, format="json"
            )
            self.assertEqual(response.status_code, 400, response.data)

        invalid_dates = self.system_payload("INVALID_EFFECTIVE_DATES", effective_to="2025-12-31")
        response = self.client.post(
            "/api/v1/ol-parameters/loan-system-setups/", invalid_dates, format="json"
        )
        self.assertEqual(response.status_code, 400, response.data)

    def test_same_product_plan_scope_and_overlapping_effective_period_is_rejected(self):
        first = OLLoanSystemSetup(
            code="LOAN_OVERLAP_1",
            name="Loan Overlap One",
            product=self.product,
            loan_basis="CASH_VALUE",
            max_loan_percentage_of_cash_value=Decimal("80"),
            min_loan_amount=Decimal("1000"),
            effective_from=date(2026, 1, 1),
            effective_to=date(2026, 12, 31),
        )
        first.full_clean()
        first.save()

        second = OLLoanSystemSetup(
            code="LOAN_OVERLAP_2",
            name="Loan Overlap Two",
            product=self.product,
            loan_basis="CASH_VALUE",
            max_loan_percentage_of_cash_value=Decimal("75"),
            min_loan_amount=Decimal("1000"),
            effective_from=date(2026, 6, 1),
            effective_to=date(2027, 5, 31),
        )
        with self.assertRaises(ValidationError):
            second.full_clean()

        interest_first = OLLoanInterestControl(
            code="INTEREST_OVERLAP_1",
            name="Interest Overlap One",
            product=self.product,
            interest_rate=Decimal("8"),
            compounding_frequency="ANNUAL",
            interest_calculation_basis="COMPOUND",
            effective_from=date(2026, 1, 1),
            effective_to=date(2026, 12, 31),
        )
        interest_first.full_clean()
        interest_first.save()
        interest_second = OLLoanInterestControl(
            code="INTEREST_OVERLAP_2",
            name="Interest Overlap Two",
            product=self.product,
            interest_rate=Decimal("9"),
            compounding_frequency="ANNUAL",
            interest_calculation_basis="COMPOUND",
            effective_from=date(2026, 6, 1),
            effective_to=None,
        )
        with self.assertRaises(ValidationError):
            interest_second.full_clean()

    def test_permissions_and_audit_logs_are_enforced(self):
        created = self.client.post(
            "/api/v1/ol-parameters/loan-system-setups/",
            self.system_payload(),
            format="json",
            HTTP_X_REQUEST_ID="loan-audit-create",
        )
        self.assertEqual(created.status_code, 201, created.data)
        record = OLLoanSystemSetup.objects.get(code="POLICY_LOAN_2026")
        self.assertTrue(
            AuditLog.objects.filter(
                app_label="ol_parameters",
                model_name="olloansystemsetup",
                object_id=str(record.pk),
                action="CREATE",
                correlation_id="loan-audit-create",
            ).exists()
        )

        updated = self.client.patch(
            f"/api/v1/ol-parameters/loan-system-setups/{record.pk}/",
            {"max_loan_percentage_of_cash_value": "70.00000000"},
            format="json",
            HTTP_X_REQUEST_ID="loan-audit-update",
        )
        self.assertEqual(updated.status_code, 200, updated.data)
        self.assertTrue(
            AuditLog.objects.filter(
                app_label="ol_parameters",
                model_name="olloansystemsetup",
                object_id=str(record.pk),
                action="UPDATE",
                correlation_id="loan-audit-update",
            ).exists()
        )

        restricted_user = User.objects.create_user(
            username="ol-loan-setup-viewer",
            email="ol-loan-setup-viewer@example.com",
            password="Strong-pass-123!",
            is_active=True,
            is_approved=True,
        )
        restricted_client = APIClient()
        restricted_client.force_authenticate(restricted_user)
        self.assertEqual(
            restricted_client.get("/api/v1/ol-parameters/loan-system-setups/").status_code,
            403,
        )
        self.assertEqual(
            restricted_client.get("/api/v1/ol-parameters/loan-interest-controls/").status_code,
            403,
        )

    def test_seed_is_idempotent_and_registers_both_contracts(self):
        management.call_command("seed_ol_loan_setup", verbosity=0)
        first_counts = (
            OLLoanSystemSetup.objects.count(),
            OLLoanInterestControl.objects.count(),
            OLParameterTableRegistry.objects.filter(parameter_group="LOAN_SETUP").count(),
        )
        management.call_command("seed_ol_loan_setup", verbosity=0)
        second_counts = (
            OLLoanSystemSetup.objects.count(),
            OLLoanInterestControl.objects.count(),
            OLParameterTableRegistry.objects.filter(parameter_group="LOAN_SETUP").count(),
        )
        self.assertEqual(first_counts, second_counts)
        self.assertEqual(first_counts, (1, 1, 2))

    def test_admin_registration_and_table_columns_exist(self):
        self.assertIn(OLLoanSystemSetup, admin.site._registry)
        self.assertIn(OLLoanInterestControl, admin.site._registry)
        system_admin = admin.site._registry[OLLoanSystemSetup]
        interest_admin = admin.site._registry[OLLoanInterestControl]
        self.assertIn("loan_basis", system_admin.list_display)
        self.assertIn("max_loan_percentage_of_cash_value", system_admin.list_display)
        self.assertIn("interest_rate", interest_admin.list_display)
        self.assertIn("compounding_frequency", interest_admin.list_display)
