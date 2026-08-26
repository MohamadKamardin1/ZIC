from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.ol_loans.models import (
    LoanOffsetSourceType,
    LoanStatus,
    OLLoan,
    OLLoanInterestAccrual,
    OLLoanOffset,
    OLLoanRepayment,
    OLLoanSchedule,
)
from apps.ol_policies.models import Policy
from apps.ol_proposals.models import OLProposal
from apps.ol_quotations.models import OLQuotation
from apps.partners.models import Partner


class OLLoanModelTestCase(TestCase):
    def setUp(self):
        User = get_user_model()
        self.actor = User.objects.create_superuser(
            username="loan-model-admin",
            email="loan-model-admin@example.com",
            password="Strong-loan-model-password-123!",
        )
        self.partner = Partner.objects.create(
            partner_number="ZIC-LOAN-P-0001",
            partner_type="CLIENT",
            partner_category="INDIVIDUAL",
            party_type="INDIVIDUAL",
            legal_name="Asha Salim",
        )
        quotation = OLQuotation.objects.create(
            quote_number="QT-LOAN-MODEL-001",
            quote_name="Loan model test",
            quote_date=date.today(),
            partner=self.partner,
            currency="TZS",
        )
        proposal = OLProposal.objects.create(
            quotation=quotation,
            proposal_number="PROP-LOAN-MODEL-001",
            status="CONVERTED",
            partner=self.partner,
            currency="TZS",
            prospect_snapshot={},
            financial_summary_snapshot={},
        )
        self.policy = Policy.objects.create(
            proposal_ref=proposal,
            partner=self.partner,
            product_plan_ref="OL_TEST_PLAN",
            currency="TZS",
            sum_assured=Decimal("10000000.00"),
            premium_amount=Decimal("100000.00"),
            premium_frequency="MONTHLY",
            term_years=10,
            risk_commencement_date=date.today(),
            maturity_date=date.today().replace(year=date.today().year + 10),
            status="ACTIVE",
        )

    def make_loan(self, **overrides):
        values = {
            "loan_number": "LOAN-MODEL-001",
            "policy_ref": self.policy,
            "partner": self.partner,
            "currency": "tzs",
            "principal_amount": Decimal("1000000.00"),
            "disbursed_amount": Decimal("0.00"),
            "interest_rate": Decimal("0.12000000"),
            "compounding_frequency": "MONTHLY",
            "term_months": 12,
            "status": LoanStatus.REQUESTED,
            "outstanding_balance": Decimal("0.00"),
            "created_by": self.actor,
            "updated_by": self.actor,
            "source_channel": "API",
        }
        values.update(overrides)
        return OLLoan.objects.create(**values)

    def test_loan_and_child_financial_records_preserve_relationships(self):
        loan = self.make_loan()
        schedule = OLLoanSchedule.objects.create(
            loan=loan,
            installment_number=1,
            due_date=date.today(),
            principal_due=Decimal("80000.00"),
            interest_due=Decimal("10000.00"),
            balance=Decimal("90000.00"),
            created_by=self.actor,
            source_channel="API",
        )
        repayment = OLLoanRepayment.objects.create(
            loan=loan,
            receipt_ref="RCT-LOAN-001",
            amount=Decimal("50000.00"),
            currency="TZS",
            exchange_rate=Decimal("1.00000000"),
            allocation_breakdown={"penalty": "0.00", "interest": "10000.00", "principal": "40000.00"},
            created_by=self.actor,
            source_channel="API",
        )
        accrual = OLLoanInterestAccrual.objects.create(
            loan=loan,
            period_start=date.today(),
            period_end=date.today(),
            principal_base=Decimal("1000000.00"),
            interest_amount=Decimal("10000.00"),
            cumulative_interest=Decimal("10000.00"),
            created_by=self.actor,
            source_channel="SYSTEM",
        )
        offset = OLLoanOffset.objects.create(
            loan=loan,
            source_type=LoanOffsetSourceType.SURRENDER,
            source_id="SUR-LOAN-001",
            offset_amount=Decimal("100000.00"),
            remaining_payout=Decimal("900000.00"),
            created_by=self.actor,
            source_channel="API",
        )

        self.assertEqual(loan.policy_ref, self.policy)
        self.assertEqual(loan.partner, self.partner)
        self.assertEqual(loan.schedules.get(), schedule)
        self.assertEqual(loan.repayments.get(), repayment)
        self.assertEqual(loan.interest_accruals.get(), accrual)
        self.assertEqual(loan.offsets.get(), offset)
        self.assertEqual(str(loan), "LOAN-MODEL-001")
        self.assertEqual(loan.currency, "TZS")

    def test_status_enum_and_money_validation_are_enforced(self):
        loan = self.make_loan(status="NOT_A_LOAN_STATUS")
        with self.assertRaises(ValidationError):
            loan.full_clean()

        invalid = OLLoan(
            loan_number="LOAN-MODEL-002",
            policy_ref=self.policy,
            partner=self.partner,
            currency="TZS",
            principal_amount=Decimal("0.00"),
            interest_rate=Decimal("0.12"),
            compounding_frequency="MONTHLY",
            term_months=12,
        )
        with self.assertRaises(ValidationError):
            invalid.full_clean()

    def test_period_and_source_constraints_prevent_duplicate_financial_rows(self):
        loan = self.make_loan()
        OLLoanInterestAccrual.objects.create(
            loan=loan,
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
            principal_base=Decimal("1000000.00"),
        )
        with self.assertRaises(Exception):
            OLLoanInterestAccrual.objects.create(
                loan=loan,
                period_start=date(2026, 1, 1),
                period_end=date(2026, 1, 31),
                principal_base=Decimal("1000000.00"),
            )
