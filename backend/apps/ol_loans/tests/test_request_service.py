from datetime import date
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from apps.common.models import DomainEvent
from apps.governance.models import ApprovalRequest, AuditLog
from apps.ol_loans.models import LoanStatus, OLLoan
from apps.ol_parameters.models import OLLoanInterestControl, OLLoanSystemSetup, OLPlanType, OLProduct
from apps.ol_policies.models import Policy
from apps.ol_proposals.models import OLProposal
from apps.ol_quotations.models import OLQuotation
from apps.partners.models import Partner
from apps.users.models import User


class PolicyLoanRequestTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_superuser(
            username="ol-loan-request-admin",
            email="ol-loan-request-admin@example.com",
            password="Strong-loan-request-password-123!",
        )
        self.client.force_authenticate(self.user)
        self.partner = Partner.objects.create(
            partner_number="ZIC-LOAN-REQUEST-P-0001",
            partner_type="CLIENT",
            partner_category="INDIVIDUAL",
            party_type="INDIVIDUAL",
            legal_name="Request Applicant",
        )
        self.plan_type = OLPlanType.objects.create(
            code="LOAN_REQUEST_PLAN_TYPE",
            name="Loan request plan type",
            plan_category="INDIVIDUAL",
            effective_from=date(2026, 1, 1),
        )
        self.product = OLProduct.objects.create(
            code="LOAN_REQUEST_PRODUCT",
            name="Loan request product",
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
        self.policy = self._make_policy()
        self.system = OLLoanSystemSetup.objects.create(
            code="LOAN_REQUEST_SYSTEM_2026",
            name="Loan request system setup",
            product=self.product,
            allow_policy_loans=True,
            loan_basis="CASH_VALUE",
            max_loan_percentage_of_cash_value=Decimal("80.00000000"),
            min_loan_amount=Decimal("100000.00"),
            max_loan_amount=Decimal("4000000.00"),
            loan_currency="TZS",
            repayment_options=[{"code": "PAYMENT_SCHEDULE", "label": "Payment schedule", "term_months": [6, 12], "enabled": True}],
            effect_on_claim="DEDUCT_BALANCE",
            effect_on_surrender="DEDUCT_BALANCE",
            effect_on_maturity="DEDUCT_BALANCE",
            require_approval=False,
            auto_approve_limit=Decimal("500000.00"),
            effective_from=date(2026, 1, 1),
        )
        self.interest = OLLoanInterestControl.objects.create(
            code="LOAN_REQUEST_INTEREST_2026",
            name="Loan request interest control",
            product=self.product,
            interest_rate=Decimal("8.00000000"),
            compounding_frequency="ANNUAL",
            interest_calculation_basis="COMPOUND",
            grace_period_days=30,
            penalty_interest_rate=Decimal("2.00000000"),
            capitalize_interest=True,
            effective_from=date(2026, 1, 1),
        )

    def _make_policy(self):
        quotation = OLQuotation.objects.create(
            quote_number="QT-LOAN-REQUEST-001",
            quote_name="Loan request quote",
            quote_date=date.today(),
            partner=self.partner,
            currency="TZS",
        )
        proposal = OLProposal.objects.create(
            quotation=quotation,
            proposal_number="PROP-LOAN-REQUEST-001",
            status="CONVERTED",
            partner=self.partner,
            currency="TZS",
            prospect_snapshot={},
            financial_summary_snapshot={},
        )
        return Policy.objects.create(
            proposal_ref=proposal,
            partner=self.partner,
            product_plan_ref=self.product.code,
            currency="TZS",
            sum_assured=Decimal("10000000.00"),
            premium_amount=Decimal("100000.00"),
            premium_frequency="MONTHLY",
            term_years=10,
            risk_commencement_date=date.today(),
            maturity_date=date(date.today().year + 10, date.today().month, date.today().day),
            status="ACTIVE",
            contract_snapshot={
                "cash_value": "5000000.00",
                "plans": [{"product_id": str(self.product.pk), "product_code": self.product.code}],
            },
        )

    def request_payload(self, **overrides):
        payload = {
            "requested_amount": "1000000.00",
            "term_months": 12,
            "repayment_mode": "PAYMENT_SCHEDULE",
            "reason": "Education expenses",
            "as_of": "2026-06-01",
        }
        payload.update(overrides)
        return payload

    def post_request(self, key="loan-request-key-001", payload=None):
        return self.client.post(
            f"/api/v1/ol/policies/{self.policy.pk}/loans/request/",
            payload or self.request_payload(),
            format="json",
            HTTP_X_IDEMPOTENCY_KEY=key,
            HTTP_X_REQUEST_ID="loan-request-test",
        )

    def test_success_creates_requested_loan_with_snapshot_event_and_audit(self):
        response = self.post_request()
        self.assertEqual(response.status_code, 201, response.data)
        loan = OLLoan.objects.get()
        self.assertEqual(loan.status, LoanStatus.REQUESTED)
        self.assertEqual(loan.principal_amount, Decimal("1000000.00"))
        self.assertEqual(loan.cash_value_snapshot, Decimal("5000000.00"))
        self.assertEqual(loan.repayment_mode, "PAYMENT_SCHEDULE")
        self.assertEqual(loan.interest_rate, self.interest.interest_rate)
        self.assertEqual(loan.currency, "TZS")
        self.assertTrue(loan.approval_required)
        self.assertTrue(ApprovalRequest.objects.filter(entity_id=loan.pk, status="PENDING").exists())
        self.assertTrue(DomainEvent.objects.filter(event_type="LoanRequested", aggregate_id=str(loan.pk)).exists())
        self.assertTrue(
            AuditLog.objects.filter(
                object_id=str(loan.pk),
                action="LOAN_REQUESTED",
                reason="Education expenses",
                source_channel="API",
            ).exists()
        )

    def test_same_idempotency_key_returns_the_original_loan(self):
        first = self.post_request(key="same-request-key")
        second = self.post_request(key="same-request-key", payload=self.request_payload(requested_amount="2000000.00"))
        self.assertEqual(first.status_code, 201, first.data)
        self.assertEqual(second.status_code, 200, second.data)
        self.assertTrue(second.data["meta"]["idempotent_replay"])
        self.assertEqual(first.data["data"]["id"], second.data["data"]["id"])
        self.assertEqual(OLLoan.objects.count(), 1)

    def test_lapsed_policy_is_blocked_with_teachable_error(self):
        self.policy.status = "LAPSED"
        self.policy.save(update_fields=["status", "updated_at"])
        response = self.post_request()
        self.assertEqual(response.status_code, 422, response.data)
        self.assertEqual(response.data["error_code"], "LOAN_INELIGIBLE")
        self.assertTrue(response.data["resolution_steps"])
        self.assertIn("Active or Paid-up", response.data["field_errors"]["policy"][0])

    def test_amount_above_cash_value_or_configured_limit_is_blocked(self):
        response = self.post_request(payload=self.request_payload(requested_amount="4500000.00"))
        self.assertEqual(response.status_code, 422, response.data)
        self.assertEqual(response.data["error_code"], "LOAN_EXCEEDS_LIMIT")
        self.assertIn("available_loan_limit", response.data["error"]["details"])
        self.assertTrue(response.data["resolution_steps"])

    def test_active_loan_and_unconfigured_term_are_blocked(self):
        OLLoan.objects.create(
            policy_ref=self.policy,
            partner=self.partner,
            currency="TZS",
            principal_amount=Decimal("500000.00"),
            cash_value_snapshot=Decimal("5000000.00"),
            interest_rate=Decimal("8.00000000"),
            compounding_frequency="ANNUAL",
            term_months=6,
            status=LoanStatus.ACTIVE,
        )
        response = self.post_request(key="blocked-active-loan")
        self.assertEqual(response.status_code, 409, response.data)
        self.assertEqual(response.data["error_code"], "LOAN_ACTIVE_EXISTS")

        self.policy.contract_snapshot = {
            "cash_value": "5000000.00",
            "plans": [{"product_id": str(self.product.pk), "product_code": self.product.code}],
        }
        self.policy.save(update_fields=["contract_snapshot", "updated_at"])
        OLLoan.objects.all().delete()
        response = self.post_request(key="blocked-term", payload=self.request_payload(term_months=24))
        self.assertEqual(response.status_code, 422, response.data)
        self.assertEqual(response.data["error_code"], "LOAN_INELIGIBLE")
        self.assertIn("term_months", response.data["field_errors"])

    def test_missing_idempotency_key_is_rejected_before_creating_a_loan(self):
        response = self.post_request(key="", payload=self.request_payload())
        self.assertEqual(response.status_code, 422, response.data)
        self.assertEqual(response.data["error_code"], "LOAN_INELIGIBLE")
        self.assertIn("idempotency_key", response.data["field_errors"])
        self.assertEqual(OLLoan.objects.count(), 0)
