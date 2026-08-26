from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from django.test import TestCase
from rest_framework.test import APIClient

from apps.governance.models import AuditLog
from apps.ol_loans.errors import LoanError
from apps.ol_loans.services.parameter_resolver import get_loan_config
from apps.ol_parameters.models import OLLoanInterestControl, OLLoanSystemSetup, OLPlanType, OLProduct
from apps.users.models import User


class OLLoanParameterEngineTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_superuser(
            username="ol-loan-parameter-admin",
            email="ol-loan-parameter-admin@example.com",
            password="Strong-loan-parameter-password-123!",
        )
        self.client.force_authenticate(self.user)
        self.plan_type = OLPlanType.objects.create(
            code="LOAN_PLAN_TYPE",
            name="Loan plan type",
            plan_category="INDIVIDUAL",
            effective_from=date(2026, 1, 1),
        )
        self.product = OLProduct.objects.create(
            code="LOAN_PARAMETER_PRODUCT",
            name="Loan parameter product",
            plan_type=self.plan_type,
            insurance_class="INDIVIDUAL",
            currency="TZS",
            min_entry_age=18,
            max_entry_age=65,
            min_term=5,
            max_term=30,
            min_sum_assured=Decimal("1000000.00"),
            max_sum_assured=Decimal("1000000000.00"),
            premium_frequencies=["MONTHLY"],
            allow_loans=True,
            effective_from=date(2026, 1, 1),
        )
        self.policy = SimpleNamespace(
            pk=uuid4(),
            policy_number="POL-LOAN-PARAM-001",
            contract_snapshot={"product_id": str(self.product.pk)},
            product_plan_ref=self.product.code,
        )

    def make_system(self, **overrides):
        values = {
            "code": "LOAN_SYSTEM_PARAMETER_2026",
            "name": "Loan system parameter",
            "product": self.product,
            "allow_policy_loans": True,
            "loan_basis": "CASH_VALUE",
            "max_loan_percentage_of_cash_value": Decimal("80.00000000"),
            "min_loan_amount": Decimal("100000.00"),
            "max_loan_amount": Decimal("10000000.00"),
            "loan_currency": "TZS",
            "repayment_options": [
                {"code": "LUMP_SUM", "label": "Lump sum", "enabled": True},
                {"code": "PAYMENT_SCHEDULE", "label": "Payment schedule", "enabled": True},
            ],
            "auto_deduct_from_benefits": True,
            "effect_on_claim": "DEDUCT_BALANCE",
            "effect_on_surrender": "DEDUCT_BALANCE",
            "effect_on_maturity": "NET_BENEFIT",
            "require_approval": False,
            "effective_from": date(2026, 1, 1),
            "is_active": True,
        }
        values.update(overrides)
        return OLLoanSystemSetup.objects.create(**values)

    def make_interest(self, **overrides):
        values = {
            "code": "LOAN_INTEREST_PARAMETER_2026",
            "name": "Loan interest parameter",
            "product": self.product,
            "interest_rate": Decimal("8.00000000"),
            "compounding_frequency": "ANNUAL",
            "interest_calculation_basis": "COMPOUND",
            "grace_period_days": 30,
            "penalty_interest_rate": Decimal("2.00000000"),
            "capitalize_interest": True,
            "effective_from": date(2026, 1, 1),
            "is_active": True,
        }
        values.update(overrides)
        return OLLoanInterestControl.objects.create(**values)

    def test_resolver_returns_specific_config_and_audits_parameter_read(self):
        system = self.make_system()
        interest = self.make_interest()
        config = get_loan_config(self.policy, as_of=date(2026, 6, 1), actor=self.user, source_channel="API")

        self.assertIsNotNone(config)
        self.assertEqual(config.system_setup_id, str(system.pk))
        self.assertEqual(config.interest_control_id, str(interest.pk))
        self.assertEqual(config.max_loan_percentage, Decimal("80.00000000"))
        self.assertEqual(config.grace_days, 30)
        self.assertEqual(config.repayment_options[0]["code"], "LUMP_SUM")
        self.assertTrue(
            AuditLog.objects.filter(
                entity_type="ol_loans.loan_configuration",
                action="READ_CONFIGURATION",
                object_id=str(self.policy.pk),
                source_channel="API",
            ).exists()
        )

    def test_missing_setup_or_interest_returns_teachable_error(self):
        self.make_system()
        with self.assertRaises(LoanError) as context:
            get_loan_config(self.policy, as_of=date(2026, 6, 1), actor=self.user)
        self.assertEqual(context.exception.error_code, "LOAN_PARAMETER_MISSING")
        self.assertIn("Ordinary Life Parameters", context.exception.resolution_steps[1])
        self.assertEqual(context.exception.deep_link, "/ol-parameters/loan-system-setups/")

        self.make_interest()
        self.assertIsNotNone(get_loan_config(self.policy, as_of=date(2026, 6, 1), actor=self.user))

    def test_parameter_update_invalidates_cached_configuration(self):
        self.make_system()
        interest = self.make_interest()
        first = get_loan_config(self.policy, as_of=date(2026, 6, 1), actor=self.user)
        interest.interest_rate = Decimal("9.00000000")
        interest.save()
        second = get_loan_config(self.policy, as_of=date(2026, 6, 1), actor=self.user)

        self.assertEqual(first.interest_rate, Decimal("8.00000000"))
        self.assertEqual(second.interest_rate, Decimal("9.00000000"))

    def test_repayment_options_filter_inactive_and_future_rows_and_support_search_pagination(self):
        self.make_system(effective_to=date(2026, 12, 31))
        self.make_system(
            code="LOAN_SYSTEM_INACTIVE",
            name="Inactive loan system",
            product=None,
            is_active=False,
            effective_from=date(2026, 1, 1),
            repayment_options=[{"code": "INACTIVE", "label": "Inactive", "enabled": True}],
        )
        self.make_system(
            code="LOAN_SYSTEM_FUTURE",
            name="Future loan system",
            effective_from=date(2027, 1, 1),
            repayment_options=[{"code": "FUTURE", "label": "Future", "enabled": True}],
        )
        response = self.client.get("/api/v1/ol/loans/options/repayment-terms/?q=lump&page=1&page_size=1&as_of=2026-06-01")
        self.assertEqual(response.status_code, 200, response.data)
        payload = response.data["data"]
        self.assertEqual(payload["count"], 1)
        self.assertEqual(payload["results"][0]["value"], "LUMP_SUM")
        self.assertEqual(payload["results"][0]["label"], "Lump sum")
        self.assertIn("as_of", payload["results"][0]["meta"])
        all_options = self.client.get("/api/v1/ol/loans/options/repayment-terms/?as_of=2026-06-01")
        self.assertEqual(all_options.status_code, 200, all_options.data)
        all_values = {item["value"] for item in all_options.data["data"]["results"]}
        self.assertNotIn("INACTIVE", all_values)
        self.assertNotIn("FUTURE", all_values)
        self.assertTrue(
            AuditLog.objects.filter(
                entity_type="ol_loans.loan_option",
                action="READ_OPTIONS",
                object_repr="repayment-terms",
            ).exists()
        )

    def test_compounding_and_offset_options_are_standardized(self):
        self.make_system()
        self.make_interest()
        frequencies = self.client.get("/api/v1/ol/loans/options/compounding-frequencies/?as_of=2026-06-01")
        self.assertEqual(frequencies.status_code, 200, frequencies.data)
        frequency = frequencies.data["data"]["results"][0]
        self.assertEqual(set(frequency), {"value", "label", "meta"})
        self.assertEqual(frequency["value"], "ANNUAL")

        offsets = self.client.get("/api/v1/ol/loans/options/offset-rules/?as_of=2026-06-01")
        self.assertEqual(offsets.status_code, 200, offsets.data)
        values = {item["value"]: item for item in offsets.data["data"]["results"]}
        self.assertIn("DEDUCT_BALANCE", values)
        self.assertIn("NET_BENEFIT", values)
        self.assertIn("CLAIM", values["DEDUCT_BALANCE"]["meta"]["sources"])
