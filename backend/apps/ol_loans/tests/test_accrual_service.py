from datetime import date
from decimal import Decimal

from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient

from apps.common.models import DomainEvent
from apps.governance.models import AuditLog
from apps.ol_loans.errors import LoanError
from apps.ol_loans.models import LoanStatus, OLLoan, OLLoanInterestAccrual, OLLoanSchedule
from apps.ol_loans.services.accrual_service import accrue_loan_interest, balance_for_loan, calculate_interest
from apps.ol_parameters.models import OLLoanInterestControl, OLLoanSystemSetup, OLPlanType, OLProduct
from apps.ol_policies.models import Policy
from apps.ol_proposals.models import OLProposal
from apps.ol_quotations.models import OLQuotation
from apps.partners.models import Partner
from apps.users.models import User


class OLLoanAccrualTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_superuser(
            username="ol-loan-accrual-admin",
            email="ol-loan-accrual-admin@example.com",
            password="Strong-loan-accrual-password-123!",
        )
        self.client.force_authenticate(self.user)
        self.partner = Partner.objects.create(
            partner_number="ZIC-LOAN-ACCRUAL-P-0001",
            partner_type="CLIENT",
            partner_category="INDIVIDUAL",
            party_type="INDIVIDUAL",
            legal_name="Accrual Applicant",
        )
        self.plan_type = OLPlanType.objects.create(
            code="LOAN_ACCRUAL_PLAN_TYPE",
            name="Loan accrual plan type",
            plan_category="INDIVIDUAL",
            effective_from=date(2026, 1, 1),
        )
        self.product = OLProduct.objects.create(
            code="LOAN_ACCRUAL_PRODUCT",
            name="Loan accrual product",
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
        quotation = OLQuotation.objects.create(
            quote_number="QT-LOAN-ACCRUAL-001",
            quote_name="Loan accrual quote",
            quote_date=date(2026, 1, 1),
            partner=self.partner,
            currency="TZS",
        )
        proposal = OLProposal.objects.create(
            quotation=quotation,
            proposal_number="PROP-LOAN-ACCRUAL-001",
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
        self.system = OLLoanSystemSetup.objects.create(
            code="LOAN_ACCRUAL_SYSTEM_2026",
            name="Loan accrual system setup",
            product=self.product,
            allow_policy_loans=True,
            loan_basis="CASH_VALUE",
            max_loan_percentage_of_cash_value=Decimal("80.00000000"),
            min_loan_amount=Decimal("100000.00"),
            max_loan_amount=Decimal("4000000.00"),
            loan_currency="TZS",
            repayment_options=[{"code": "EQUAL_INSTALLMENT", "term_months": [12], "enabled": True}],
            effect_on_claim="DEDUCT_BALANCE",
            effect_on_surrender="DEDUCT_BALANCE",
            effect_on_maturity="DEDUCT_BALANCE",
            require_approval=False,
            effective_from=date(2026, 1, 1),
        )
        self.interest = OLLoanInterestControl.objects.create(
            code="LOAN_ACCRUAL_INTEREST_2026",
            name="Loan accrual interest control",
            product=self.product,
            interest_rate=Decimal("12.00000000"),
            compounding_frequency="ANNUAL",
            interest_calculation_basis="COMPOUND",
            grace_period_days=30,
            penalty_interest_rate=Decimal("2.00000000"),
            capitalize_interest=True,
            effective_from=date(2026, 1, 1),
        )

    def make_loan(self, number="LOAN-ACCRUAL-001", *, status=LoanStatus.ACTIVE):
        return OLLoan.objects.create(
            loan_number=number,
            policy_ref=self.policy,
            partner=self.partner,
            currency="TZS",
            principal_amount=Decimal("1200000.00"),
            cash_value_snapshot=Decimal("5000000.00"),
            disbursed_amount=Decimal("1200000.00"),
            interest_rate=self.interest.interest_rate,
            compounding_frequency=self.interest.compounding_frequency,
            term_months=12,
            disbursement_date=date(2026, 1, 1),
            maturity_date=date(2027, 1, 1),
            repayment_mode="EQUAL_INSTALLMENT",
            status=status,
            outstanding_balance=Decimal("1200000.00"),
            reason="Accrual test loan",
            created_by=self.user,
            updated_by=self.user,
        )

    def test_simple_and_compound_math_are_exact_for_one_year(self):
        simple_config = type("Config", (), {
            "interest_calculation_basis": "SIMPLE",
            "compounding_frequency": "ANNUAL",
        })()
        compound_config = type("Config", (), {
            "interest_calculation_basis": "COMPOUND",
            "compounding_frequency": "ANNUAL",
        })()
        simple = calculate_interest(Decimal("1000.00"), Decimal("12.00"), 365, simple_config)
        compound = calculate_interest(Decimal("1000.00"), Decimal("12.00"), 365, compound_config)
        self.assertEqual(simple, Decimal("120.00"))
        self.assertEqual(compound, Decimal("120.00"))

    def test_accrual_creates_interest_record_and_updates_balance(self):
        loan = self.make_loan()
        result = accrue_loan_interest(
            loan.pk,
            period_start=date(2026, 1, 1),
            period_end=date(2027, 1, 1),
            actor=self.user,
            source_channel="BATCH",
            correlation_id="OL-ACCRUAL-TEST-001",
        )
        loan.refresh_from_db()
        self.assertTrue(result.created)
        self.assertEqual(result.accrual.interest_amount, Decimal("144000.00"))
        self.assertEqual(result.accrual.penalty_amount, Decimal("0.00"))
        self.assertEqual(result.accrual.principal_base, Decimal("1200000.00"))
        self.assertEqual(result.accrual.cumulative_interest, Decimal("144000.00"))
        self.assertEqual(loan.outstanding_balance, Decimal("1344000.00"))
        audit = AuditLog.objects.filter(object_id=str(loan.pk), action="LOAN_INTEREST_ACCRUED").latest("created_at")
        self.assertEqual(audit.source_channel, "BATCH")
        self.assertEqual(audit.request_id, "OL-ACCRUAL-TEST-001")
        event = DomainEvent.objects.get(event_type="LoanInterestAccrued", aggregate_id=str(loan.pk))
        self.assertEqual(event.payload["interest_amount"], "144000.00")

    def test_penalty_starts_after_configured_grace_period_for_overdue_schedule(self):
        loan = self.make_loan("LOAN-ACCRUAL-PENALTY-001")
        OLLoanSchedule.objects.create(
            loan=loan,
            installment_number=1,
            due_date=date(2026, 1, 1),
            principal_due=Decimal("1000.00"),
            interest_due=Decimal("100.00"),
            balance=Decimal("1100.00"),
            status="PENDING",
        )
        result = accrue_loan_interest(
            loan.pk,
            period_start=date(2026, 2, 1),
            period_end=date(2026, 2, 10),
            actor=self.user,
            source_channel="BATCH",
            correlation_id="OL-ACCRUAL-PENALTY-001",
        )
        self.assertEqual(result.accrual.penalty_amount, Decimal("0.54"))
        self.assertGreater(result.accrual.penalty_amount, Decimal("0.00"))

    def test_same_period_is_idempotent_and_does_not_double_balance(self):
        loan = self.make_loan("LOAN-ACCRUAL-IDEMPOTENT-001")
        kwargs = {
            "period_start": date(2026, 1, 1),
            "period_end": date(2026, 2, 1),
            "actor": self.user,
            "source_channel": "BATCH",
            "correlation_id": "OL-ACCRUAL-IDEMPOTENT-001",
        }
        first = accrue_loan_interest(loan.pk, **kwargs)
        loan.refresh_from_db()
        balance_after_first = loan.outstanding_balance
        second = accrue_loan_interest(loan.pk, **kwargs)
        loan.refresh_from_db()
        self.assertTrue(first.created)
        self.assertFalse(second.created)
        self.assertEqual(first.accrual.pk, second.accrual.pk)
        self.assertEqual(OLLoanInterestAccrual.objects.filter(loan=loan).count(), 1)
        self.assertEqual(loan.outstanding_balance, balance_after_first)

    def test_balance_endpoint_matches_accrual_records(self):
        loan = self.make_loan("LOAN-ACCRUAL-BALANCE-001")
        accrue_loan_interest(
            loan.pk,
            period_start=date(2026, 1, 1),
            period_end=date(2026, 2, 1),
            actor=self.user,
            source_channel="BATCH",
            correlation_id="OL-ACCRUAL-BALANCE-001",
        )
        response = self.client.get(f"/api/v1/ol/loans/{loan.pk}/balance/")
        self.assertEqual(response.status_code, 200, response.data)
        data = response.data["data"]
        self.assertEqual(data["principal"], "1200000.00")
        self.assertEqual(data["accrued_interest"], "11605.98")
        self.assertEqual(data["penalty"], "0.00")
        self.assertEqual(data["total_outstanding"], "1211605.98")

    def test_settled_and_closed_loans_cannot_accrue(self):
        for status in (LoanStatus.SETTLED, LoanStatus.CLOSED):
            loan = self.make_loan(f"LOAN-ACCRUAL-{status}-001", status=status)
            with self.assertRaises(LoanError) as context:
                accrue_loan_interest(
                    loan.pk,
                    period_start=date(2026, 1, 1),
                    period_end=date(2026, 2, 1),
                    actor=self.user,
                )
            self.assertEqual(context.exception.error_code, "LOAN_INVALID_STATUS")
            self.assertEqual(OLLoanInterestAccrual.objects.filter(loan=loan).count(), 0)

    def test_management_command_uses_system_actor_and_writes_batch_audit(self):
        loan = self.make_loan("LOAN-ACCRUAL-COMMAND-001")
        call_command(
            "accrue_loan_interest",
            period_start="2026-01-01",
            period_end="2026-02-01",
            loan_id=str(loan.pk),
            correlation_id="OL-ACCRUAL-COMMAND-001",
            stdout=None,
        )
        batch_audit = AuditLog.objects.get(
            action="LOAN_INTEREST_ACCRUAL_BATCH",
            request_id="OL-ACCRUAL-COMMAND-001",
        )
        self.assertEqual(batch_audit.source_channel, "BATCH")
        self.assertEqual(batch_audit.user.username, "system")
        self.assertEqual(batch_audit.after_state["created"], 1)
