from datetime import date
from decimal import Decimal

from django.core.management import call_command
from django.test import TestCase

from apps.common.models import DomainEvent
from apps.governance.models import AuditLog
from apps.ol_loans.errors import LoanError
from apps.ol_loans.models import LoanOffsetSourceType, LoanScheduleStatus, LoanStatus, OLLoan, OLLoanOffset, OLLoanSchedule
from apps.ol_loans.services.default_service import detect_loan_defaults, process_loan_offset, system_actor
from apps.ol_parameters.models import OLLoanInterestControl, OLLoanSystemSetup, OLPlanType, OLProduct
from apps.ol_policies.models import Policy
from apps.ol_proposals.models import OLProposal
from apps.ol_quotations.models import OLQuotation
from apps.partners.models import Partner
from apps.users.models import User


class OLLoanDefaultOffsetTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            username="ol-loan-default-admin",
            email="ol-loan-default-admin@example.com",
            password="Strong-loan-default-password-123!",
        )
        self.partner = Partner.objects.create(
            partner_number="ZIC-LOAN-DEFAULT-P-0001",
            partner_type="CLIENT",
            partner_category="INDIVIDUAL",
            party_type="INDIVIDUAL",
            legal_name="Default Applicant",
        )
        self.plan_type = OLPlanType.objects.create(
            code="LOAN_DEFAULT_PLAN_TYPE",
            name="Loan default plan type",
            plan_category="INDIVIDUAL",
            effective_from=date(2026, 1, 1),
        )
        self.product = OLProduct.objects.create(
            code="LOAN_DEFAULT_PRODUCT",
            name="Loan default product",
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
            quote_number="QT-LOAN-DEFAULT-001",
            quote_name="Loan default quote",
            quote_date=date(2026, 1, 1),
            partner=self.partner,
            currency="TZS",
        )
        proposal = OLProposal.objects.create(
            quotation=quotation,
            proposal_number="PROP-LOAN-DEFAULT-001",
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
            contract_snapshot={"cash_value": "5000000.00", "product_id": str(self.product.pk)},
        )
        OLLoanSystemSetup.objects.create(
            code="LOAN_DEFAULT_SYSTEM_2026",
            name="Loan default system setup",
            product=self.product,
            allow_policy_loans=True,
            loan_basis="CASH_VALUE",
            max_loan_percentage_of_cash_value=Decimal("80.00000000"),
            min_loan_amount=Decimal("100.00"),
            max_loan_amount=Decimal("4000000.00"),
            loan_currency="TZS",
            repayment_options=[{"code": "EQUAL_INSTALLMENT", "term_months": [1], "enabled": True}],
            effect_on_claim="DEDUCT_BALANCE",
            effect_on_surrender="DEDUCT_BALANCE",
            effect_on_maturity="DEDUCT_BALANCE",
            require_approval=False,
            effective_from=date(2026, 1, 1),
        )
        OLLoanInterestControl.objects.create(
            code="LOAN_DEFAULT_INTEREST_2026",
            name="Loan default interest control",
            product=self.product,
            interest_rate=Decimal("12.00000000"),
            compounding_frequency="ANNUAL",
            interest_calculation_basis="SIMPLE",
            grace_period_days=30,
            penalty_period_days=15,
            penalty_interest_rate=Decimal("2.00000000"),
            capitalize_interest=True,
            effective_from=date(2026, 1, 1),
        )

    def make_loan(self, number, *, status=LoanStatus.ACTIVE, outstanding=Decimal("1120.00")):
        loan = OLLoan.objects.create(
            loan_number=number,
            policy_ref=self.policy,
            partner=self.partner,
            currency="TZS",
            principal_amount=Decimal("1000.00"),
            cash_value_snapshot=Decimal("5000000.00"),
            disbursed_amount=Decimal("1000.00"),
            interest_rate=Decimal("12.00000000"),
            compounding_frequency="ANNUAL",
            term_months=1,
            disbursement_date=date(2026, 1, 1),
            maturity_date=date(2026, 2, 1),
            repayment_mode="EQUAL_INSTALLMENT",
            status=status,
            total_repaid=Decimal("0.00"),
            outstanding_balance=outstanding,
            reason="Default lifecycle test loan",
            created_by=self.user,
            updated_by=self.user,
        )
        OLLoanSchedule.objects.create(
            loan=loan,
            installment_number=1,
            due_date=date(2026, 1, 1),
            principal_due=Decimal("1000.00"),
            interest_due=Decimal("100.00"),
            penalty_due=Decimal("20.00"),
            balance=outstanding,
            status=LoanScheduleStatus.PENDING,
            created_by=self.user,
            updated_by=self.user,
        )
        return loan

    def test_default_threshold_is_strictly_grace_plus_penalty_period(self):
        loan = self.make_loan("LOAN-DEFAULT-THRESHOLD-001")
        at_threshold = detect_loan_defaults(
            as_of=date(2026, 2, 15),
            actor=self.user,
            source_channel="BATCH",
            correlation_id="OL-DEFAULT-THRESHOLD-001",
        )
        loan.refresh_from_db()
        self.assertEqual(at_threshold.defaulted, 0)
        self.assertEqual(loan.status, LoanStatus.ACTIVE)

        beyond_threshold = detect_loan_defaults(
            as_of=date(2026, 2, 16),
            actor=self.user,
            source_channel="BATCH",
            correlation_id="OL-DEFAULT-THRESHOLD-002",
        )
        loan.refresh_from_db()
        self.assertEqual(beyond_threshold.defaulted, 1)
        self.assertEqual(loan.status, LoanStatus.DEFAULTED)
        self.assertTrue(DomainEvent.objects.filter(event_type="LoanDefaulted", aggregate_id=str(loan.pk)).exists())
        audit = AuditLog.objects.get(action="LOAN_DEFAULTED", object_id=str(loan.pk))
        self.assertEqual(audit.source_channel, "BATCH")
        self.assertEqual(audit.after_state["threshold_days"], 45)

    def test_default_detection_is_idempotent_on_rerun(self):
        loan = self.make_loan("LOAN-DEFAULT-IDEMPOTENT-001")
        first = detect_loan_defaults(
            as_of=date(2026, 2, 20),
            actor=self.user,
            source_channel="BATCH",
            correlation_id="OL-DEFAULT-IDEMPOTENT-001",
        )
        second = detect_loan_defaults(
            as_of=date(2026, 2, 20),
            actor=self.user,
            source_channel="BATCH",
            correlation_id="OL-DEFAULT-IDEMPOTENT-002",
        )
        loan.refresh_from_db()
        self.assertEqual(first.defaulted, 1)
        self.assertEqual(second.defaulted, 0)
        self.assertEqual(DomainEvent.objects.filter(event_type="LoanDefaulted", aggregate_id=str(loan.pk)).count(), 1)
        self.assertEqual(AuditLog.objects.filter(action="LOAN_DEFAULTED", object_id=str(loan.pk)).count(), 1)

    def test_management_command_uses_system_actor_and_logs_batch(self):
        loan = self.make_loan("LOAN-DEFAULT-COMMAND-001")
        call_command(
            "detect_loan_defaults",
            as_of="2026-02-20",
            loan_id=str(loan.pk),
            correlation_id="OL-DEFAULT-COMMAND-001",
            stdout=None,
        )
        loan.refresh_from_db()
        self.assertEqual(loan.status, LoanStatus.DEFAULTED)
        audit = AuditLog.objects.get(action="LOAN_DEFAULT_DETECTION_BATCH", request_id="OL-DEFAULT-COMMAND-001")
        self.assertEqual(audit.user.username, "system")
        self.assertEqual(audit.after_state["defaulted"], 1)

    def test_offset_deducts_minimum_updates_status_and_is_idempotent(self):
        loan = self.make_loan("LOAN-OFFSET-SURRENDER-001", status=LoanStatus.DEFAULTED)
        first = process_loan_offset(
            loan,
            LoanOffsetSourceType.SURRENDER,
            "SUR-0001",
            Decimal("800.00"),
            actor=self.user,
            source_channel="API",
            reason="Surrender proceeds offset.",
        )
        loan.refresh_from_db()
        self.assertTrue(first.created)
        self.assertEqual(first.offset.offset_amount, Decimal("800.00"))
        self.assertEqual(first.offset.remaining_payout, Decimal("0.00"))
        self.assertEqual(loan.outstanding_balance, Decimal("320.00"))
        self.assertEqual(loan.status, LoanStatus.OFFSET_ON_SURRENDER)

        replay = process_loan_offset(
            loan,
            LoanOffsetSourceType.SURRENDER,
            "SUR-0001",
            Decimal("800.00"),
            actor=self.user,
            source_channel="API",
        )
        self.assertFalse(replay.created)
        self.assertEqual(OLLoanOffset.objects.filter(loan=loan).count(), 1)

        audit = AuditLog.objects.get(action="LOAN_OFFSET", object_id=str(loan.pk))
        self.assertEqual(audit.source_channel, "API")
        self.assertEqual(audit.after_state["source_id"], "SUR-0001")
        event = DomainEvent.objects.get(event_type="LoanOffset", aggregate_id=str(loan.pk))
        self.assertEqual(event.payload["offset_amount"], "800.00")

    def test_full_offset_closes_loan_and_returns_remaining_payout(self):
        loan = self.make_loan("LOAN-OFFSET-MATURITY-001", status=LoanStatus.ACTIVE)
        result = process_loan_offset(
            loan,
            LoanOffsetSourceType.MATURITY,
            "MAT-0001",
            Decimal("1500.00"),
            actor=self.user,
            source_channel="API",
        )
        loan.refresh_from_db()
        self.assertEqual(result.offset.offset_amount, Decimal("1120.00"))
        self.assertEqual(result.offset.remaining_payout, Decimal("380.00"))
        self.assertEqual(loan.outstanding_balance, Decimal("0.00"))
        self.assertEqual(loan.status, LoanStatus.CLOSED)

    def test_settled_or_closed_loan_and_nonpositive_payout_are_blocked(self):
        settled = self.make_loan("LOAN-OFFSET-SETTLED-001", status=LoanStatus.SETTLED, outstanding=Decimal("0.00"))
        with self.assertRaises(LoanError) as settled_error:
            process_loan_offset(settled, LoanOffsetSourceType.CLAIM, "CLM-0001", Decimal("100.00"), actor=self.user)
        self.assertEqual(settled_error.exception.error_code, "LOAN_OFFSET_INVALID")

        active = self.make_loan("LOAN-OFFSET-ZERO-001")
        with self.assertRaises(LoanError) as payout_error:
            process_loan_offset(active, LoanOffsetSourceType.CLAIM, "CLM-0002", Decimal("0.00"), actor=self.user)
        self.assertEqual(payout_error.exception.error_code, "LOAN_OFFSET_INVALID")
        self.assertEqual(OLLoanOffset.objects.filter(loan=active).count(), 0)
