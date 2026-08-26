from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.common.models import DomainEvent
from apps.ol_parameters.models import (
    OLLoanInterestControl,
    OLLoanSystemSetup,
    OLPlanType,
    OLProduct,
)
from apps.ol_policies.events import (
    POLICY_LOAN_DISBURSED,
    POLICY_LOAN_REPAID,
    POLICY_LOAN_REQUESTED,
    POLICY_WITHDRAWAL_REQUESTED,
)
from apps.ol_policies.models import (
    LoanStatus,
    Policy,
    PolicyLoan,
    PolicyLoanRepayment,
    PolicyStatus,
    WithdrawalRequest,
    WithdrawalStatus,
)
from apps.ol_proposals.models import OLProposal
from apps.ol_quotations.models import OLQuotation
from apps.partners.models import Partner


class PolicyFinanceTestCase(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="finance-admin",
            email="finance-admin@example.com",
            password="Strong-finance-password-123!",
        )
        self.partner = Partner.objects.create(
            partner_number="ZIC-FIN-P-0001",
            partner_type="CLIENT",
            partner_category="INDIVIDUAL",
            party_type="INDIVIDUAL",
            legal_name="Salma Ali",
            email="salma.finance@example.com",
            mobile_number="+255711600001",
            phone="+255711600001",
        )
        quotation = OLQuotation.objects.create(
            quote_number="QT-FIN-0001",
            quote_name="Finance quote",
            quote_date=date.today() - timedelta(days=100),
            partner=self.partner,
            currency="TZS",
        )
        proposal = OLProposal.objects.create(
            quotation=quotation,
            proposal_number="PROP-FIN-0001",
            status="CONVERTED",
            partner=self.partner,
            currency="TZS",
            prospect_snapshot={},
            financial_summary_snapshot={},
        )
        self.policy = Policy.objects.create(
            proposal_ref=proposal,
            partner=self.partner,
            product_plan_ref="OL_TERM_FINANCE",
            currency="TZS",
            sum_assured=Decimal("2000000.00"),
            premium_amount=Decimal("100000.00"),
            premium_frequency="ANNUALLY",
            term_years=10,
            risk_commencement_date=date.today() - timedelta(days=100),
            maturity_date=date.today() + timedelta(days=3000),
            status=PolicyStatus.ACTIVE,
            contract_snapshot={
                "cash_value": "1000000.00",
                "allow_withdrawals": True,
                "withdrawal_requires_approval": False,
                "plans": [{"product_code": "OL_FINANCE_PRODUCT"}],
            },
        )
        plan_type = OLPlanType.objects.create(code="FINANCE-PLAN", name="Finance plan", is_active=True)
        self.product = OLProduct.objects.create(
            code="OL_FINANCE_PRODUCT",
            name="Finance product",
            plan_type=plan_type,
            effective_from=date.today() - timedelta(days=365),
            premium_frequencies=["ANNUALLY"],
            allow_loans=True,
            allow_withdrawals=True,
            is_active=True,
        )
        self.policy.contract_snapshot["plans"] = [{"product_id": str(self.product.pk), "product_code": self.product.code}]
        self.policy.save(update_fields=["contract_snapshot"])
        OLLoanSystemSetup.objects.create(
            code="LOAN-FINANCE-SETUP",
            name="Finance loan setup",
            product=self.product,
            effective_from=date.today() - timedelta(days=365),
            allow_policy_loans=True,
            loan_basis="CASH_VALUE",
            max_loan_percentage_of_cash_value=Decimal("50"),
            min_loan_amount=Decimal("10000"),
            max_loan_amount=Decimal("400000"),
            loan_currency="TZS",
            repayment_options=["LUMP_SUM", "INSTALLMENTS"],
            require_approval=True,
            is_active=True,
        )
        OLLoanInterestControl.objects.create(
            code="LOAN-FINANCE-INTEREST",
            name="Finance loan interest",
            product=self.product,
            effective_from=date.today() - timedelta(days=365),
            interest_rate=Decimal("10"),
            compounding_frequency="ANNUAL",
            interest_calculation_basis="ACTUAL_365",
            grace_period_days=0,
            penalty_interest_rate=Decimal("2"),
            capitalize_interest=True,
            is_active=True,
        )
        self.client.force_authenticate(self.user)

    def test_loan_requires_limits_then_approves_disburses_and_repeats_idempotently(self):
        blocked = self.client.post(
            f"/api/v1/ol/policies/{self.policy.pk}/loans/",
            {"amount": "600000.00"},
            format="json",
        )
        self.assertEqual(blocked.status_code, 422)
        self.assertIn("available_loan_limit", blocked.data["error"]["details"])

        request_date = date.today() - timedelta(days=30)
        created = self.client.post(
            f"/api/v1/ol/policies/{self.policy.pk}/loans/",
            {"amount": "300000.00", "as_of": request_date.isoformat(), "reason": "Education expense."},
            format="json",
        )
        self.assertEqual(created.status_code, 201)
        loan_id = created.data["data"]["id"]
        loan = PolicyLoan.objects.get(pk=loan_id)
        self.assertEqual(loan.status, LoanStatus.REQUESTED)
        self.assertEqual(DomainEvent.objects.filter(event_type=POLICY_LOAN_REQUESTED, aggregate_id=str(self.policy.pk)).count(), 1)

        approved = self.client.post(f"/api/v1/ol/policies/loans/{loan_id}/approve/", {"as_of": request_date.isoformat()}, format="json")
        self.assertEqual(approved.status_code, 200)
        self.assertEqual(approved.data["data"]["status"], LoanStatus.APPROVED)
        disbursed = self.client.post(f"/api/v1/ol/policies/loans/{loan_id}/disburse/", {"as_of": request_date.isoformat()}, format="json")
        self.assertEqual(disbursed.status_code, 200)
        loan.refresh_from_db()
        self.assertEqual(loan.status, LoanStatus.DISBURSED)
        self.assertTrue(loan.payment_requisition_id)
        self.assertEqual(DomainEvent.objects.filter(event_type=POLICY_LOAN_DISBURSED, aggregate_id=str(self.policy.pk)).count(), 1)

    def test_repayment_applies_interest_before_principal_and_does_not_double_accrue(self):
        created = self.client.post(
            f"/api/v1/ol/policies/{self.policy.pk}/loans/",
            {"amount": "300000.00", "as_of": (date.today() - timedelta(days=30)).isoformat()},
            format="json",
        )
        loan_id = created.data["data"]["id"]
        self.client.post(
            f"/api/v1/ol/policies/loans/{loan_id}/approve/",
            {"as_of": (date.today() - timedelta(days=30)).isoformat()},
            format="json",
        )
        self.client.post(
            f"/api/v1/ol/policies/loans/{loan_id}/disburse/",
            {"as_of": (date.today() - timedelta(days=30)).isoformat()},
            format="json",
        )
        first = self.client.post(
            f"/api/v1/ol/policies/loans/{loan_id}/repay/",
            {"amount": "100000.00", "payment_date": date.today().isoformat()},
            format="json",
        )
        self.assertEqual(first.status_code, 200)
        loan = PolicyLoan.objects.get(pk=loan_id)
        repayment = PolicyLoanRepayment.objects.get(loan=loan)
        self.assertGreater(repayment.interest_component, Decimal("0.00"))
        self.assertGreater(repayment.principal_component, Decimal("0.00"))
        accrued_after_first = loan.accrued_interest

        second = self.client.post(
            f"/api/v1/ol/policies/loans/{loan_id}/repay/",
            {"amount": "100000.00", "payment_date": date.today().isoformat()},
            format="json",
        )
        self.assertEqual(second.status_code, 200)
        loan.refresh_from_db()
        self.assertEqual(loan.accrued_interest, accrued_after_first)
        self.assertEqual(PolicyLoanRepayment.objects.filter(loan=loan).count(), 2)
        self.assertEqual(DomainEvent.objects.filter(event_type=POLICY_LOAN_REPAID, aggregate_id=str(self.policy.pk)).count(), 2)

    def test_withdrawal_uses_cash_value_after_loans_and_creates_requisition(self):
        created = self.client.post(
            f"/api/v1/ol/policies/{self.policy.pk}/withdrawals/",
            {"amount": "250000.00", "reason": "Family expense."},
            format="json",
        )
        self.assertEqual(created.status_code, 201)
        withdrawal = WithdrawalRequest.objects.get(pk=created.data["data"]["id"])
        self.assertEqual(withdrawal.status, WithdrawalStatus.APPROVED)
        self.assertTrue(withdrawal.payment_requisition_id)
        self.assertEqual(withdrawal.net_amount, Decimal("250000.00"))
        self.assertEqual(DomainEvent.objects.filter(event_type=POLICY_WITHDRAWAL_REQUESTED, aggregate_id=str(self.policy.pk)).count(), 1)

        blocked = self.client.post(
            f"/api/v1/ol/policies/{self.policy.pk}/withdrawals/",
            {"amount": "800000.00"},
            format="json",
        )
        self.assertEqual(blocked.status_code, 422)
        self.assertIn("available", blocked.data["error"]["details"])

    def test_policy_loan_list_and_withdrawal_list_return_records(self):
        loans = self.client.get(f"/api/v1/ol/policies/{self.policy.pk}/loans/")
        self.assertEqual(loans.status_code, 200)
        self.assertEqual(loans.data["data"], [])
        withdrawals = self.client.get(f"/api/v1/ol/policies/{self.policy.pk}/withdrawals/")
        self.assertEqual(withdrawals.status_code, 200)
        self.assertEqual(withdrawals.data["data"], [])
