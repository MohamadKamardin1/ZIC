from datetime import date
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from apps.common.models import DomainEvent
from apps.front_office.receipts.models import Receipt, ReceiptAllocation, ReceiptAllocationStatus, ReceiptSourceModule, ReceiptStatus
from apps.governance.models import AuditLog
from apps.ol_loans.errors import LoanError
from apps.ol_loans.models import LoanScheduleStatus, LoanStatus, OLLoan, OLLoanRepayment, OLLoanSchedule
from apps.ol_loans.services.repayment_service import repay_loan
from apps.ol_parameters.models import OLLoanInterestControl, OLLoanSystemSetup, OLPlanType, OLProduct
from apps.ol_policies.models import Policy
from apps.ol_proposals.models import OLProposal
from apps.ol_quotations.models import OLQuotation
from apps.partners.models import Partner
from apps.users.models import User


class OLLoanRepaymentTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_superuser(
            username="ol-loan-repayment-admin",
            email="ol-loan-repayment-admin@example.com",
            password="Strong-loan-repayment-password-123!",
        )
        self.client.force_authenticate(self.user)
        self.partner = Partner.objects.create(
            partner_number="ZIC-LOAN-REPAY-P-0001",
            partner_type="CLIENT",
            partner_category="INDIVIDUAL",
            party_type="INDIVIDUAL",
            legal_name="Repayment Applicant",
        )
        self.plan_type = OLPlanType.objects.create(
            code="LOAN_REPAY_PLAN_TYPE",
            name="Loan repayment plan type",
            plan_category="INDIVIDUAL",
            effective_from=date(2026, 1, 1),
        )
        self.product = OLProduct.objects.create(
            code="LOAN_REPAY_PRODUCT",
            name="Loan repayment product",
            plan_type=self.plan_type,
            insurance_class="INDIVIDUAL",
            currency="TZS",
            min_entry_age=18,
            max_entry_age=65,
            min_term=1,
            max_term=30,
            min_sum_assured=Decimal("1000000.00"),
            max_sum_assured=Decimal("1000000000.00"),
            premium_frequencies=["MONTHLY"],
            allow_loans=True,
            effective_from=date(2026, 1, 1),
        )
        quotation = OLQuotation.objects.create(
            quote_number="QT-LOAN-REPAY-001",
            quote_name="Loan repayment quote",
            quote_date=date(2026, 1, 1),
            partner=self.partner,
            currency="TZS",
        )
        proposal = OLProposal.objects.create(
            quotation=quotation,
            proposal_number="PROP-LOAN-REPAY-001",
            status="CONVERTED",
            partner=self.partner,
            currency="TZS",
            prospect_snapshot={},
            financial_summary_snapshot={},
        )
        self.policy = Policy.objects.create(
            proposal_ref=proposal,
            partner=self.partner,
            product_plan_ref=self.product.code,
            currency="TZS",
            sum_assured=Decimal("10000000.00"),
            premium_amount=Decimal("100000.00"),
            premium_frequency="MONTHLY",
            term_years=10,
            risk_commencement_date=date(2026, 1, 1),
            maturity_date=date(2036, 1, 1),
            status="ACTIVE",
            contract_snapshot={
                "cash_value": "5000000.00",
                "plans": [{"product_id": str(self.product.pk), "product_code": self.product.code}],
            },
        )
        OLLoanSystemSetup.objects.create(
            code="LOAN_REPAY_SYSTEM_2026",
            name="Loan repayment system setup",
            product=self.product,
            allow_policy_loans=True,
            loan_basis="CASH_VALUE",
            max_loan_percentage_of_cash_value=Decimal("80.00000000"),
            min_loan_amount=Decimal("100.00"),
            max_loan_amount=Decimal("4000000.00"),
            loan_currency="TZS",
            repayment_options=[{"code": "EQUAL_INSTALLMENT", "term_months": [1, 12], "enabled": True}],
            effect_on_claim="DEDUCT_BALANCE",
            effect_on_surrender="DEDUCT_BALANCE",
            effect_on_maturity="DEDUCT_BALANCE",
            require_approval=False,
            effective_from=date(2026, 1, 1),
        )
        OLLoanInterestControl.objects.create(
            code="LOAN_REPAY_INTEREST_2026",
            name="Loan repayment interest control",
            product=self.product,
            interest_rate=Decimal("12.00000000"),
            compounding_frequency="ANNUAL",
            interest_calculation_basis="SIMPLE",
            grace_period_days=30,
            penalty_interest_rate=Decimal("2.00000000"),
            capitalize_interest=True,
            effective_from=date(2026, 1, 1),
        )

    def make_loan(self, number, *, principal=Decimal("1000.00"), interest=Decimal("100.00"), penalty=Decimal("20.00")):
        total = principal + interest + penalty
        loan = OLLoan.objects.create(
            loan_number=number,
            policy_ref=self.policy,
            partner=self.partner,
            currency="TZS",
            principal_amount=principal,
            cash_value_snapshot=Decimal("5000000.00"),
            disbursed_amount=principal,
            interest_rate=Decimal("12.00000000"),
            compounding_frequency="ANNUAL",
            term_months=1,
            disbursement_date=date(2026, 1, 1),
            maturity_date=date(2026, 2, 1),
            repayment_mode="EQUAL_INSTALLMENT",
            status=LoanStatus.ACTIVE,
            outstanding_balance=total,
            reason="Repayment test loan",
            created_by=self.user,
            updated_by=self.user,
        )
        OLLoanSchedule.objects.create(
            loan=loan,
            installment_number=1,
            due_date=date(2026, 1, 1),
            principal_due=principal,
            interest_due=interest,
            penalty_due=penalty,
            balance=total,
            status=LoanScheduleStatus.PENDING,
            created_by=self.user,
            updated_by=self.user,
        )
        return loan

    def repay(self, loan, amount, **overrides):
        payload = {
            "amount": amount,
            "currency": "TZS",
            "payment_date": date(2026, 2, 15),
            "reason": "Repayment received",
            "idempotency_key": f"repayment-{loan.loan_number}-{amount}",
            "actor": self.user,
            "source_channel": "API",
        }
        payload.update(overrides)
        return repay_loan(loan.pk, **payload)

    def test_allocation_order_is_penalty_then_interest_then_principal(self):
        loan = self.make_loan("LOAN-REPAY-ORDER-001", penalty=Decimal("50.00"))
        result = self.repay(loan, Decimal("250.00"))
        breakdown = result.repayment.allocation_breakdown
        self.assertEqual(breakdown["penalty"], "50.00")
        self.assertEqual(breakdown["interest"], "100.00")
        self.assertEqual(breakdown["principal"], "100.00")
        self.assertEqual(breakdown["allocation_order"], ["penalty", "interest", "principal"])
        schedule = loan.schedules.get()
        self.assertEqual(schedule.penalty_paid, Decimal("50.00"))
        self.assertEqual(schedule.interest_paid, Decimal("100.00"))
        self.assertEqual(schedule.principal_paid, Decimal("100.00"))
        self.assertEqual(schedule.amount_paid, Decimal("250.00"))

    def test_partial_repayment_updates_components_balance_and_status(self):
        loan = self.make_loan("LOAN-REPAY-PARTIAL-001")
        result = self.repay(loan, Decimal("500.00"))
        loan.refresh_from_db()
        schedule = loan.schedules.get()
        self.assertTrue(result.created)
        self.assertEqual(loan.status, LoanStatus.PARTIALLY_REPAID)
        self.assertEqual(loan.total_repaid, Decimal("500.00"))
        self.assertEqual(loan.outstanding_balance, Decimal("620.00"))
        self.assertEqual(schedule.penalty_paid, Decimal("20.00"))
        self.assertEqual(schedule.interest_paid, Decimal("100.00"))
        self.assertEqual(schedule.principal_paid, Decimal("380.00"))
        self.assertEqual(schedule.balance, Decimal("620.00"))
        self.assertEqual(schedule.status, LoanScheduleStatus.OVERDUE)

    def test_full_repayment_sets_settled_and_emits_repaid_and_settled_events(self):
        loan = self.make_loan("LOAN-REPAY-FULL-001")
        result = self.repay(loan, Decimal("1120.00"))
        loan.refresh_from_db()
        schedule = loan.schedules.get()
        self.assertTrue(result.created)
        self.assertEqual(loan.status, LoanStatus.SETTLED)
        self.assertEqual(loan.outstanding_balance, Decimal("0.00"))
        self.assertEqual(schedule.status, LoanScheduleStatus.PAID)
        self.assertEqual(schedule.balance, Decimal("0.00"))
        self.assertTrue(DomainEvent.objects.filter(event_type="LoanRepaid", aggregate_id=str(loan.pk)).exists())
        self.assertTrue(DomainEvent.objects.filter(event_type="LoanSettled", aggregate_id=str(loan.pk)).exists())

    def test_overpayment_returns_teachable_error_without_writing_repayment(self):
        loan = self.make_loan("LOAN-REPAY-OVERPAY-001")
        with self.assertRaises(LoanError) as context:
            self.repay(loan, Decimal("1120.01"))
        self.assertEqual(context.exception.error_code, "LOAN_REPAYMENT_OVERPAYMENT")
        self.assertTrue(context.exception.resolution_steps)
        self.assertIn("amount", context.exception.field_errors)
        self.assertEqual(OLLoanRepayment.objects.filter(loan=loan).count(), 0)

    def test_receipt_reference_links_active_front_office_allocation(self):
        loan = self.make_loan("LOAN-REPAY-RECEIPT-001")
        receipt = Receipt.objects.create(
            receipt_number="RCT-LOAN-REPAY-001",
            receipt_date=date(2026, 2, 15),
            payer_name=str(self.partner),
            partner=self.partner,
            source_module=ReceiptSourceModule.MANUAL,
            currency="TZS",
            receipt_amount=Decimal("1120.00"),
            allocated_amount=Decimal("0.00"),
            unallocated_amount=Decimal("1120.00"),
            status=ReceiptStatus.POSTED,
        )
        allocation = ReceiptAllocation.objects.create(
            receipt=receipt,
            target_type="MANUAL",
            target_id=loan.loan_number,
            target_display=loan.loan_number,
            amount=Decimal("1120.00"),
            currency="TZS",
            converted_amount=Decimal("1120.00"),
            allocation_status=ReceiptAllocationStatus.ACTIVE,
            allocated_by=self.user,
        )
        result = self.repay(
            loan,
            Decimal("1120.00"),
            receipt_ref=receipt.receipt_number,
            idempotency_key="repayment-receipt-001",
        )
        repayment = result.repayment
        self.assertEqual(repayment.receipt_allocation_id, allocation.pk)
        self.assertEqual(repayment.receipt_ref, receipt.receipt_number)
        self.assertEqual(repayment.allocation_breakdown["receipt_ref"], receipt.receipt_number)

    def test_repayment_endpoint_is_permission_gated_and_idempotent(self):
        loan = self.make_loan("LOAN-REPAY-API-001")
        viewer = User.objects.create_user(
            username="ol-loan-repayment-viewer",
            email="ol-loan-repayment-viewer@example.com",
            password="Strong-loan-repayment-viewer-password-123!",
        )
        self.client.force_authenticate(viewer)
        denied = self.client.post(
            f"/api/v1/ol/loans/{loan.pk}/repay/",
            {"amount": "100.00", "currency": "TZS"},
            format="json",
        )
        self.assertEqual(denied.status_code, 403, denied.data)

        self.client.force_authenticate(self.user)
        payload = {"amount": "500.00", "currency": "TZS", "payment_date": "2026-02-15", "reason": "API partial"}
        response = self.client.post(
            f"/api/v1/ol/loans/{loan.pk}/repay/",
            payload,
            format="json",
            HTTP_X_IDEMPOTENCY_KEY="repayment-api-001",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["meta"]["allocation_breakdown"]["penalty"], "20.00")
        replay = self.client.post(
            f"/api/v1/ol/loans/{loan.pk}/repay/",
            payload,
            format="json",
            HTTP_X_IDEMPOTENCY_KEY="repayment-api-001",
        )
        self.assertEqual(replay.status_code, 200, replay.data)
        self.assertTrue(replay.data["meta"]["idempotent_replay"])

        audit = AuditLog.objects.filter(object_id=str(loan.pk), action="LOAN_REPAID").latest("created_at")
        self.assertEqual(audit.user, self.user)
        self.assertEqual(audit.source_channel, "API")
        self.assertIn("allocation_breakdown", audit.after_state)
