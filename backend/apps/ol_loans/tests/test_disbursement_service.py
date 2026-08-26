from datetime import date
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from apps.common.models import DomainEvent
from apps.front_office.models import FORequisition
from apps.front_office.receipts.config_models import CompanyBankAccount, ReceiptPaymentModeRule
from apps.governance.models import AuditLog
from apps.ol_loans.errors import LoanError
from apps.ol_loans.models import LoanStatus, OLLoan, OLLoanDisbursement, OLLoanSchedule
from apps.ol_loans.services.disbursement_service import disburse_loan
from apps.ol_parameters.models import OLLoanInterestControl, OLLoanSystemSetup, OLPlanType, OLProduct
from apps.ol_policies.models import Policy
from apps.ol_proposals.models import OLProposal
from apps.ol_quotations.models import OLQuotation
from apps.partners.models import Partner
from apps.users.models import User


class OLLoanDisbursementTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_superuser(
            username="ol-loan-disbursement-admin",
            email="ol-loan-disbursement-admin@example.com",
            password="Strong-loan-disbursement-password-123!",
        )
        self.client.force_authenticate(self.user)
        self.partner = Partner.objects.create(
            partner_number="ZIC-LOAN-DISBURSE-P-0001",
            partner_type="CLIENT",
            partner_category="INDIVIDUAL",
            party_type="INDIVIDUAL",
            legal_name="Disbursement Applicant",
        )
        self.plan_type = OLPlanType.objects.create(
            code="LOAN_DISBURSE_PLAN_TYPE",
            name="Loan disbursement plan type",
            plan_category="INDIVIDUAL",
            effective_from=date(2026, 1, 1),
        )
        self.product = OLProduct.objects.create(
            code="LOAN_DISBURSE_PRODUCT",
            name="Loan disbursement product",
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
            quote_number="QT-LOAN-DISBURSE-001",
            quote_name="Loan disbursement quote",
            quote_date=date(2026, 1, 1),
            partner=self.partner,
            currency="TZS",
        )
        proposal = OLProposal.objects.create(
            quotation=quotation,
            proposal_number="PROP-LOAN-DISBURSE-001",
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
            code="LOAN_DISBURSE_SYSTEM_2026",
            name="Loan disbursement system setup",
            product=self.product,
            allow_policy_loans=True,
            loan_basis="CASH_VALUE",
            max_loan_percentage_of_cash_value=Decimal("80.00000000"),
            min_loan_amount=Decimal("100000.00"),
            max_loan_amount=Decimal("4000000.00"),
            loan_currency="TZS",
            repayment_options=[
                {
                    "code": "EQUAL_INSTALLMENT",
                    "label": "Equal installment",
                    "term_months": [6, 12],
                    "enabled": True,
                }
            ],
            effect_on_claim="DEDUCT_BALANCE",
            effect_on_surrender="DEDUCT_BALANCE",
            effect_on_maturity="DEDUCT_BALANCE",
            require_approval=False,
            effective_from=date(2026, 1, 1),
        )
        self.interest = OLLoanInterestControl.objects.create(
            code="LOAN_DISBURSE_INTEREST_2026",
            name="Loan disbursement interest control",
            product=self.product,
            interest_rate=Decimal("12.00000000"),
            compounding_frequency="MONTHLY",
            interest_calculation_basis="COMPOUND",
            grace_period_days=30,
            penalty_interest_rate=Decimal("2.00000000"),
            capitalize_interest=True,
            effective_from=date(2026, 1, 1),
        )
        self.payment_rule = ReceiptPaymentModeRule.objects.create(
            payment_mode="BANK_TRANSFER",
            requires_reference=False,
            requires_bank_account=True,
            allows_bank_transfer=True,
        )
        self.bank_account = CompanyBankAccount.objects.create(
            code="ZIC-LOAN-TZS",
            bank_name="Zanzibar Commercial Bank",
            account_name="ZIC Loan Disbursements",
            account_number="0123456789",
            currency="TZS",
            is_default=True,
            is_active=True,
        )

    def make_loan(self, number="LOAN-DISBURSE-001", *, mode="EQUAL_INSTALLMENT", term=12):
        return OLLoan.objects.create(
            loan_number=number,
            policy_ref=self.policy,
            partner=self.partner,
            currency="TZS",
            principal_amount=Decimal("1200000.00"),
            cash_value_snapshot=Decimal("5000000.00"),
            interest_rate=self.interest.interest_rate,
            compounding_frequency=self.interest.compounding_frequency,
            term_months=term,
            repayment_mode=mode,
            status=LoanStatus.APPROVED,
            approval_required=False,
            reason="Approved education loan",
            created_by=self.user,
            updated_by=self.user,
        )

    def test_disbursement_creates_schedule_financial_seam_and_audit(self):
        loan = self.make_loan()
        result = disburse_loan(
            loan.pk,
            payment_mode="BANK_TRANSFER",
            bank_account_code=self.bank_account.code,
            as_of=date(2026, 6, 1),
            reason="Release approved education loan",
            idempotency_key="loan-disbursement-test-001",
            actor=self.user,
            source_channel="API",
        )
        loan.refresh_from_db()
        self.assertTrue(result.changed)
        self.assertEqual(loan.status, LoanStatus.ACTIVE)
        self.assertEqual(loan.disbursed_amount, Decimal("1200000.00"))
        self.assertEqual(loan.outstanding_balance, Decimal("1200000.00"))
        self.assertEqual(loan.disbursement_date, date(2026, 6, 1))
        self.assertEqual(loan.maturity_date, date(2027, 6, 1))
        self.assertEqual(OLLoanSchedule.objects.filter(loan=loan).count(), 12)
        first = OLLoanSchedule.objects.get(loan=loan, installment_number=1)
        last = OLLoanSchedule.objects.get(loan=loan, installment_number=12)
        self.assertEqual(first.due_date, date(2026, 7, 1))
        self.assertGreater(first.interest_due, Decimal("0.00"))
        self.assertEqual(last.balance, Decimal("0.00"))
        self.assertEqual(sum(row.principal_due for row in OLLoanSchedule.objects.filter(loan=loan)), Decimal("1200000.00"))

        disbursement = OLLoanDisbursement.objects.get(loan=loan)
        self.assertTrue(disbursement.requisition.requisition_number.startswith("LOAN-"))
        self.assertEqual(disbursement.requisition.department, "OL_LOAN_FINANCE")
        self.assertEqual(FORequisition.objects.filter(pk=disbursement.requisition_id).count(), 1)
        audit = AuditLog.objects.filter(object_id=str(loan.pk), action="LOAN_DISBURSED").latest("created_at")
        self.assertEqual(audit.user, self.user)
        self.assertEqual(audit.source_channel, "API")
        self.assertIn("schedule_count", audit.after_state)
        event = DomainEvent.objects.get(event_type="LoanDisbursed", aggregate_id=str(loan.pk))
        self.assertEqual(event.payload["requisition_number"], disbursement.requisition.requisition_number)
        self.assertEqual(event.payload["schedule_count"], 12)

    def test_equal_principal_schedule_reconciles_principal(self):
        self.system.repayment_options = [{"code": "EQUAL_PRINCIPAL", "term_months": [6], "enabled": True}]
        self.system.save(update_fields=["repayment_options", "updated_at"])
        loan = self.make_loan("LOAN-DISBURSE-PRINCIPAL-001", mode="EQUAL_PRINCIPAL", term=6)
        result = disburse_loan(
            loan.pk,
            payment_mode="BANK_TRANSFER",
            bank_account_code=self.bank_account.code,
            as_of=date(2026, 6, 1),
            idempotency_key="loan-disbursement-test-principal",
            actor=self.user,
        )
        self.assertEqual(len(result.schedules), 6)
        self.assertEqual(result.schedules[0].principal_due, Decimal("200000.00"))
        self.assertEqual(result.schedules[-1].balance, Decimal("0.00"))

    def test_repeated_disbursement_returns_existing_record_without_duplicates(self):
        loan = self.make_loan()
        kwargs = {
            "payment_mode": "BANK_TRANSFER",
            "bank_account_code": self.bank_account.code,
            "as_of": date(2026, 6, 1),
            "idempotency_key": "loan-disbursement-repeat",
            "actor": self.user,
        }
        first = disburse_loan(loan.pk, **kwargs)
        second = disburse_loan(loan.pk, **kwargs)
        self.assertTrue(first.changed)
        self.assertFalse(second.changed)
        self.assertEqual(first.disbursement.pk, second.disbursement.pk)
        self.assertEqual(OLLoanDisbursement.objects.filter(loan=loan).count(), 1)
        self.assertEqual(OLLoanSchedule.objects.filter(loan=loan).count(), 12)

    def test_missing_payment_configuration_is_teachable(self):
        self.payment_rule.is_active = False
        self.payment_rule.save(update_fields=["is_active", "updated_at"])
        loan = self.make_loan()
        with self.assertRaises(LoanError) as context:
            disburse_loan(
                loan.pk,
                payment_mode="BANK_TRANSFER",
                bank_account_code=self.bank_account.code,
                as_of=date(2026, 6, 1),
                idempotency_key="loan-disbursement-missing-mode",
                actor=self.user,
            )
        self.assertEqual(context.exception.error_code, "LOAN_DISBURSEMENT_FAILED")
        self.assertIn("payment_mode", context.exception.field_errors)
        self.assertEqual(OLLoanDisbursement.objects.count(), 0)
        self.assertEqual(OLLoanSchedule.objects.count(), 0)

    def test_disbursement_endpoint_is_permission_gated_and_returns_idempotency_meta(self):
        loan = self.make_loan()
        viewer = User.objects.create_user(
            username="ol-loan-disbursement-viewer",
            email="ol-loan-disbursement-viewer@example.com",
            password="Strong-loan-viewer-password-123!",
        )
        self.client.force_authenticate(viewer)
        denied = self.client.post(
            f"/api/v1/ol/loans/{loan.pk}/disburse/",
            {"payment_mode": "BANK_TRANSFER", "bank_account_code": self.bank_account.code},
            format="json",
        )
        self.assertEqual(denied.status_code, 403, denied.data)

        self.client.force_authenticate(self.user)
        response = self.client.post(
            f"/api/v1/ol/loans/{loan.pk}/disburse/",
            {"payment_mode": "BANK_TRANSFER", "bank_account_code": self.bank_account.code, "as_of": "2026-06-01"},
            format="json",
            HTTP_X_IDEMPOTENCY_KEY="loan-disbursement-api-001",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["meta"]["schedule_count"], 12)
        self.assertEqual(response.data["data"]["disbursement"]["requisition_number"], OLLoanDisbursement.objects.get(loan=loan).requisition.requisition_number)

        replay = self.client.post(
            f"/api/v1/ol/loans/{loan.pk}/disburse/",
            {"payment_mode": "BANK_TRANSFER", "bank_account_code": self.bank_account.code},
            format="json",
            HTTP_X_IDEMPOTENCY_KEY="loan-disbursement-api-001",
        )
        self.assertEqual(replay.status_code, 200, replay.data)
        self.assertTrue(replay.data["meta"]["idempotent_replay"])
