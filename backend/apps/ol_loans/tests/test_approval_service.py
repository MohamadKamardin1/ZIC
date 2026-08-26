from datetime import date
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from apps.common.models import DomainEvent
from apps.governance.models import ApprovalRequest, AuditLog
from apps.ol_loans.errors import LoanError
from apps.ol_loans.models import LoanStatus, OLLoan
from apps.ol_loans.services.approval_service import approve_loan, bulk_approve, bulk_reject, reject_loan
from apps.ol_policies.models import Policy
from apps.ol_proposals.models import OLProposal
from apps.ol_quotations.models import OLQuotation
from apps.partners.models import Partner
from apps.users.models import User


class OLLoanApprovalServiceTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            username="ol-loan-approval-admin",
            email="ol-loan-approval-admin@example.com",
            password="Strong-loan-approval-password-123!",
        )
        self.partner = Partner.objects.create(
            partner_number="ZIC-LOAN-APPROVAL-P-0001",
            partner_type="CLIENT",
            partner_category="INDIVIDUAL",
            party_type="INDIVIDUAL",
            legal_name="Approval Applicant",
        )
        quotation = OLQuotation.objects.create(
            quote_number="QT-LOAN-APPROVAL-001",
            quote_name="Approval quote",
            quote_date=date.today(),
            partner=self.partner,
            currency="TZS",
        )
        proposal = OLProposal.objects.create(
            quotation=quotation,
            proposal_number="PROP-LOAN-APPROVAL-001",
            status="CONVERTED",
            partner=self.partner,
            currency="TZS",
            prospect_snapshot={},
            financial_summary_snapshot={},
        )
        self.policy = Policy.objects.create(
            proposal_ref=proposal,
            partner=self.partner,
            product_plan_ref="LOAN_APPROVAL_PRODUCT",
            currency="TZS",
            sum_assured=Decimal("10000000.00"),
            premium_amount=Decimal("100000.00"),
            premium_frequency="MONTHLY",
            term_years=10,
            risk_commencement_date=date.today(),
            maturity_date=date(date.today().year + 10, date.today().month, date.today().day),
            status="ACTIVE",
        )

    def make_loan(self, number, *, approval_required=True):
        loan = OLLoan.objects.create(
            loan_number=number,
            policy_ref=self.policy,
            partner=self.partner,
            currency="TZS",
            principal_amount=Decimal("1000000.00"),
            cash_value_snapshot=Decimal("5000000.00"),
            interest_rate=Decimal("8.00000000"),
            compounding_frequency="ANNUAL",
            term_months=12,
            status=LoanStatus.REQUESTED,
            approval_required=approval_required,
            reason="Approval test",
            created_by=self.user,
            updated_by=self.user,
        )
        approval = ApprovalRequest.objects.create(
            module="OL_LOANS",
            entity_type="OLLoan",
            entity_id=loan.pk,
            entity_repr=loan.loan_number,
            action="DISBURSE",
            requested_data={"requested_amount": str(loan.principal_amount)},
            current_data={"status": loan.status},
            submitted_by=self.user,
        )
        loan.approval_request = approval
        loan.save(update_fields=["approval_request", "updated_at"])
        return loan, approval

    def test_approve_transitions_status_and_updates_governance_audit_and_event(self):
        loan, approval = self.make_loan("LOAN-APPROVE-001")
        result = approve_loan(loan.pk, actor=self.user, reason="Reviewed and approved", source_channel="API")
        loan.refresh_from_db()
        approval.refresh_from_db()

        self.assertTrue(result.changed)
        self.assertEqual(loan.status, LoanStatus.APPROVED)
        self.assertEqual(loan.approved_by, self.user)
        self.assertIsNotNone(loan.approved_at)
        self.assertEqual(approval.status, "APPROVED")
        self.assertEqual(approval.reviewed_by, self.user)
        self.assertEqual(approval.comments, "Reviewed and approved")
        self.assertTrue(
            AuditLog.objects.filter(object_id=str(loan.pk), action="LOAN_APPROVED", source_channel="API").exists()
        )
        self.assertTrue(
            DomainEvent.objects.filter(event_type="LoanApproved", aggregate_id=str(loan.pk)).exists()
        )

    def test_reject_requires_reason_and_records_rejection(self):
        loan, approval = self.make_loan("LOAN-REJECT-001")
        with self.assertRaises(LoanError) as context:
            reject_loan(loan.pk, reason="", actor=self.user)
        self.assertEqual(context.exception.error_code, "LOAN_INVALID_STATUS")
        self.assertIn("reason", context.exception.field_errors)

        result = reject_loan(loan.pk, reason="Missing required underwriting evidence", actor=self.user)
        loan.refresh_from_db()
        approval.refresh_from_db()
        self.assertTrue(result.changed)
        self.assertEqual(loan.status, LoanStatus.REJECTED)
        self.assertEqual(loan.rejected_by, self.user)
        self.assertEqual(loan.rejection_reason, "Missing required underwriting evidence")
        self.assertEqual(approval.status, "REJECTED")
        self.assertEqual(approval.comments, "Missing required underwriting evidence")
        self.assertTrue(AuditLog.objects.filter(object_id=str(loan.pk), action="LOAN_REJECTED").exists())

    def test_invalid_status_and_non_manual_approval_are_blocked(self):
        loan, _ = self.make_loan("LOAN-INVALID-001")
        loan.status = LoanStatus.APPROVED
        loan.save(update_fields=["status", "updated_at"])
        with self.assertRaises(LoanError) as context:
            approve_loan(loan.pk, actor=self.user)
        self.assertEqual(context.exception.error_code, "LOAN_INVALID_STATUS")

        no_approval, _ = self.make_loan("LOAN-NO-APPROVAL-001", approval_required=False)
        with self.assertRaises(LoanError) as context:
            approve_loan(no_approval.pk, actor=self.user)
        self.assertIn("manual approval", str(context.exception))

    def test_bulk_approve_and_reject_return_per_record_results(self):
        first, _ = self.make_loan("LOAN-BULK-APPROVE-001")
        second, _ = self.make_loan("LOAN-BULK-APPROVE-002")
        results, errors = bulk_approve([first.pk, second.pk], actor=self.user)
        self.assertEqual(len(results), 2)
        self.assertEqual(errors, [])
        self.assertEqual(set(OLLoan.objects.filter(pk__in=[first.pk, second.pk]).values_list("status", flat=True)), {LoanStatus.APPROVED})

        third, _ = self.make_loan("LOAN-BULK-REJECT-001")
        results, errors = bulk_reject([third.pk], reason="Duplicate request", actor=self.user)
        self.assertEqual(len(results), 1)
        self.assertEqual(errors, [])
        third.refresh_from_db()
        self.assertEqual(third.status, LoanStatus.REJECTED)

    def test_approval_endpoint_and_bulk_endpoint_are_permission_gated(self):
        client = APIClient()
        unauthorized = User.objects.create_user(
            username="ol-loan-approval-viewer",
            email="ol-loan-approval-viewer@example.com",
            password="Strong-loan-viewer-password-123!",
        )
        client.force_authenticate(unauthorized)
        denied_loan, _ = self.make_loan("LOAN-API-DENIED-001")
        denied = client.post(f"/api/v1/ol/loans/{denied_loan.pk}/approve/", {"reason": "No"}, format="json")
        self.assertEqual(denied.status_code, 403, denied.data)
        denied_bulk = client.post("/api/v1/ol/loans/bulk-approve/", {"loan_ids": [str(denied_loan.pk)]}, format="json")
        self.assertEqual(denied_bulk.status_code, 403, denied_bulk.data)

        client.force_authenticate(self.user)
        loan, _ = self.make_loan("LOAN-API-APPROVE-001")
        response = client.post(f"/api/v1/ol/loans/{loan.pk}/approve/", {"reason": "Approved"}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["data"]["status"], LoanStatus.APPROVED)

        rejected, _ = self.make_loan("LOAN-API-REJECT-001")
        response = client.post(f"/api/v1/ol/loans/{rejected.pk}/reject/", {}, format="json")
        self.assertEqual(response.status_code, 422, response.data)
        self.assertEqual(response.data["error_code"], "LOAN_INVALID_STATUS")

        bulk, _ = self.make_loan("LOAN-API-BULK-001")
        response = client.post("/api/v1/ol/loans/bulk-approve/", {"loan_ids": [str(bulk.pk)]}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["data"]["count"], 1)
