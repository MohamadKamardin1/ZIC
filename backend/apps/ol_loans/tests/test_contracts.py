from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.common.models import DomainEvent
from apps.ol_loans.errors import LoanError, LOAN_ERROR_CODES, parameter_missing
from apps.ol_loans.events import EVENT_TYPES, LOAN_REQUESTED, emit_loan_requested
from apps.ol_loans.models import LoanStatus, OLLoan
from apps.ol_policies.models import Policy
from apps.ol_proposals.models import OLProposal
from apps.ol_quotations.models import OLQuotation
from apps.partners.models import Partner


class OLLoanContractTestCase(TestCase):
    def test_error_registry_and_error_coach_shape_are_stable(self):
        self.assertEqual(len(LOAN_ERROR_CODES), 8)
        error = parameter_missing("maximum loan percentage")
        self.assertEqual(error.error_code, "LOAN_PARAMETER_MISSING")
        self.assertTrue(error.resolution_steps)
        self.assertEqual(error.doc_ref, "docs/OL_LOANS_DESIGN.md")
        self.assertIn("navigation_path", error.details)
        self.assertIsInstance(LoanError("message").field_errors, dict)

    def test_domain_event_registry_and_loan_event_payload(self):
        User = get_user_model()
        actor = User.objects.create_superuser(
            username="loan-event-admin",
            email="loan-event-admin@example.com",
            password="Strong-loan-event-password-123!",
        )
        partner = Partner.objects.create(
            partner_number="ZIC-LOAN-EVENT-P-0001",
            partner_type="CLIENT",
            partner_category="INDIVIDUAL",
            party_type="INDIVIDUAL",
            legal_name="Event Applicant",
        )
        quotation = OLQuotation.objects.create(
            quote_number="QT-LOAN-EVENT-001",
            quote_name="Event test",
            quote_date=date.today(),
            partner=partner,
            currency="TZS",
        )
        proposal = OLProposal.objects.create(
            quotation=quotation,
            proposal_number="PROP-LOAN-EVENT-001",
            status="CONVERTED",
            partner=partner,
            currency="TZS",
            prospect_snapshot={},
            financial_summary_snapshot={},
        )
        policy = Policy.objects.create(
            proposal_ref=proposal,
            partner=partner,
            product_plan_ref="OL_EVENT_PLAN",
            currency="TZS",
            sum_assured=Decimal("10000000.00"),
            premium_amount=Decimal("100000.00"),
            premium_frequency="MONTHLY",
            term_years=10,
            risk_commencement_date=date.today(),
            maturity_date=date(date.today().year + 10, date.today().month, date.today().day),
            status="ACTIVE",
        )
        loan = OLLoan.objects.create(
            loan_number="LOAN-EVENT-001",
            policy_ref=policy,
            partner=partner,
            principal_amount=Decimal("1000000.00"),
            interest_rate=Decimal("0.12"),
            compounding_frequency="MONTHLY",
            term_months=12,
            status=LoanStatus.REQUESTED,
        )

        event = emit_loan_requested(loan, actor=actor, reason="Customer request", source_channel="API")
        self.assertEqual(event.event_type, LOAN_REQUESTED)
        self.assertEqual(event.aggregate_type, "OLLoan")
        self.assertEqual(event.payload["loan_number"], loan.loan_number)
        self.assertEqual(event.payload["actor_id"], str(actor.pk))
        self.assertEqual(event.payload["source_channel"], "API")
        self.assertEqual(set(EVENT_TYPES), {
            "LoanRequested",
            "LoanApproved",
            "LoanDisbursed",
            "LoanInterestAccrued",
            "LoanRepaid",
            "LoanDefaulted",
            "LoanOffset",
            "LoanSettled",
        })
        self.assertTrue(DomainEvent.objects.filter(pk=event.pk).exists())
