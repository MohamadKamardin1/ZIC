from datetime import date
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from apps.common.models import DomainEvent
from apps.dashboard.models import DashboardNotification
from apps.governance.models import AuditLog
from apps.ol_loans.models import LoanStatus, OLLoan, OLLoanOffset
from apps.ol_loans.services.integration_service import loan_dashboard_hooks, policy_loan_summary
from apps.ol_policies.models import Policy
from apps.ol_policies.serializers import PolicyDetailSerializer
from apps.ol_policies.services.lifecycle_service import reinstate_policy
from apps.ol_proposals.models import OLProposal
from apps.ol_quotations.models import OLQuotation
from apps.partners.models import Partner, UserPartnerLink
from apps.users.models import User


class OLLoanIntegrationsTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.partner = Partner.objects.create(
            partner_number="ZIC-INTEGRATION-P-0001",
            partner_type="CLIENT",
            partner_category="INDIVIDUAL",
            party_type="INDIVIDUAL",
            legal_name="Integration Policyholder",
            email="integration.policyholder@example.com",
        )
        cls.other_partner = Partner.objects.create(
            partner_number="ZIC-INTEGRATION-P-0002",
            partner_type="CLIENT",
            partner_category="INDIVIDUAL",
            party_type="INDIVIDUAL",
            legal_name="Other Policyholder",
            email="other.policyholder@example.com",
        )
        cls.agent = Partner.objects.create(
            partner_number="ZIC-INTEGRATION-A-0001",
            partner_type="AGENT",
            partner_category="INTERMEDIARY",
            party_type="ORGANIZATION",
            legal_name="Integration Agency",
            email="integration.agency@example.com",
        )
        quotation = OLQuotation.objects.create(
            quote_number="QT-INTEGRATION-001",
            quote_name="Integration quote",
            quote_date=date.today(),
            partner=cls.partner,
            currency="TZS",
        )
        other_quotation = OLQuotation.objects.create(
            quote_number="QT-INTEGRATION-002",
            quote_name="Other integration quote",
            quote_date=date.today(),
            partner=cls.other_partner,
            currency="TZS",
        )
        proposal = OLProposal.objects.create(
            quotation=quotation,
            proposal_number="PROP-INTEGRATION-001",
            status="CONVERTED",
            partner=cls.partner,
            currency="TZS",
            prospect_snapshot={},
            financial_summary_snapshot={},
        )
        other_proposal = OLProposal.objects.create(
            quotation=other_quotation,
            proposal_number="PROP-INTEGRATION-002",
            status="CONVERTED",
            partner=cls.other_partner,
            currency="TZS",
            prospect_snapshot={},
            financial_summary_snapshot={},
        )
        cls.policy = Policy.objects.create(
            proposal_ref=proposal,
            partner=cls.partner,
            agent=cls.agent,
            product_plan_ref="OL_INTEGRATION_PLAN",
            currency="TZS",
            sum_assured=Decimal("5000000.00"),
            premium_amount=Decimal("50000.00"),
            premium_frequency="MONTHLY",
            term_years=10,
            risk_commencement_date=date.today(),
            maturity_date=date(2036, 1, 1),
            status="ACTIVE",
            contract_snapshot={"branch_name": "ZIC Main Branch", "product_name": "Integration Protection Plan"},
        )
        cls.other_policy = Policy.objects.create(
            proposal_ref=other_proposal,
            partner=cls.other_partner,
            agent=cls.agent,
            product_plan_ref="OL_OTHER_PLAN",
            currency="TZS",
            sum_assured=Decimal("3000000.00"),
            premium_amount=Decimal("30000.00"),
            premium_frequency="MONTHLY",
            term_years=10,
            risk_commencement_date=date.today(),
            maturity_date=date(2036, 1, 1),
            status="ACTIVE",
            contract_snapshot={"branch_name": "ZIC North Branch", "product_name": "Other Protection Plan"},
        )
        cls.loan = OLLoan.objects.create(
            loan_number="LOAN-INTEGRATION-001",
            policy_ref=cls.policy,
            partner=cls.partner,
            currency="TZS",
            principal_amount=Decimal("1000.00"),
            cash_value_snapshot=Decimal("2500.00"),
            disbursed_amount=Decimal("1000.00"),
            repayment_mode="EQUAL_INSTALLMENT",
            interest_rate=Decimal("0.12000000"),
            compounding_frequency="MONTHLY",
            term_months=12,
            disbursement_date=date.today(),
            maturity_date=date(2027, 1, 1),
            status=LoanStatus.ACTIVE,
            outstanding_balance=Decimal("600.00"),
        )
        cls.other_loan = OLLoan.objects.create(
            loan_number="LOAN-INTEGRATION-002",
            policy_ref=cls.other_policy,
            partner=cls.other_partner,
            currency="TZS",
            principal_amount=Decimal("2000.00"),
            cash_value_snapshot=Decimal("3000.00"),
            disbursed_amount=Decimal("2000.00"),
            repayment_mode="EQUAL_INSTALLMENT",
            interest_rate=Decimal("0.10000000"),
            compounding_frequency="MONTHLY",
            term_months=12,
            disbursement_date=date.today(),
            maturity_date=date(2027, 1, 1),
            status=LoanStatus.ACTIVE,
            outstanding_balance=Decimal("1000.00"),
        )
        cls.dashboard_user = User.objects.create_superuser(
            username="integration-dashboard-admin",
            email="integration-dashboard-admin@example.com",
            password="Strong-integration-dashboard-password-123!",
        )
        cls.portal_user = User.objects.create_user(
            username="integration-portal-user",
            email="integration-portal-user@example.com",
            password="Strong-integration-password-123!",
        )
        UserPartnerLink.objects.create(user=cls.portal_user, partner=cls.partner, is_primary=True, created_by=cls.portal_user)
        cls.other_portal_user = User.objects.create_user(
            username="other-portal-user",
            email="other-portal-user@example.com",
            password="Strong-other-portal-password-123!",
        )
        UserPartnerLink.objects.create(user=cls.other_portal_user, partner=cls.other_partner, is_primary=True, created_by=cls.other_portal_user)

    def test_policy_detail_exposes_ol_loan_summary_without_loan_uuid(self):
        payload = PolicyDetailSerializer(self.policy).data
        summary = payload["ol_loan_summary"]
        self.assertEqual(summary["count"], 1)
        self.assertEqual(summary["outstanding_balance"], "600.00")
        self.assertEqual(summary["loans"][0]["loan_number"], "LOAN-INTEGRATION-001")
        self.assertNotIn(str(self.loan.pk), str(summary))

    def test_reinstatement_is_blocked_until_defaulted_loan_is_cleared_or_offset(self):
        self.policy.status = "LAPSED"
        self.policy.save(update_fields=["status", "updated_at"])
        self.loan.status = LoanStatus.DEFAULTED
        self.loan.outstanding_balance = Decimal("600.00")
        self.loan.save(update_fields=["status", "outstanding_balance", "updated_at"])
        with self.assertRaises(Exception) as raised:
            reinstate_policy(self.policy.pk, as_of=date.today())
        self.assertIn("loan default", str(raised.exception).lower())
        self.loan.status = LoanStatus.CLOSED
        self.loan.outstanding_balance = Decimal("0.00")
        self.loan.save(update_fields=["status", "outstanding_balance", "updated_at"])
        # The loan guard no longer blocks the policy; the next configured-window
        # validation is intentionally outside this integration assertion.
        with self.assertRaises(Exception) as after_clear:
            reinstate_policy(self.policy.pk, as_of=date.today())
        self.assertNotIn("loan default remains uncleared", str(after_clear.exception).lower())

    def test_policy_claim_settlement_event_triggers_idempotent_offset_and_net_payout(self):
        event = DomainEvent.objects.create(
            event_type="PolicyClaimSettledApplied",
            aggregate_type="OLPolicy",
            aggregate_id=str(self.policy.pk),
            payload={
                "policy_id": str(self.policy.pk),
                "claim_id": "CLM-INTEGRATION-001",
                "claim_type": "DEATH",
                "settlement_amount": "1000.00",
            },
        )
        self.loan.refresh_from_db()
        self.assertEqual(self.loan.status, LoanStatus.CLOSED)
        self.assertEqual(self.loan.outstanding_balance, Decimal("0.00"))
        self.assertEqual(OLLoanOffset.objects.filter(loan=self.loan, source_id="CLM-INTEGRATION-001").count(), 1)
        self.assertTrue(AuditLog.objects.filter(action="POLICY_LOAN_NET_PAYOUT", object_id=str(self.policy.pk)).exists())
        # Replaying the same settlement event must not create another offset.
        from apps.ol_loans.services.integration_service import apply_settlement_event

        result = apply_settlement_event(event)
        self.assertEqual(result["offset_amount"], "0.00")
        self.assertEqual(OLLoanOffset.objects.filter(loan=self.loan, source_id="CLM-INTEGRATION-001").count(), 1)

    def test_portal_is_partner_scoped_read_only_and_sanitizes_cross_partner_detail(self):
        client = APIClient()
        client.force_authenticate(self.portal_user)
        listing = client.get("/api/v1/ol/loans/portal/")
        self.assertEqual(listing.status_code, 200, listing.data)
        self.assertEqual(listing.data["data"]["count"], 1)
        self.assertEqual(listing.data["data"]["results"][0]["loan_number"], "LOAN-INTEGRATION-001")
        self.assertNotIn(str(self.loan.pk), str(listing.data))
        hidden = client.get(f"/api/v1/ol/loans/portal/{self.other_loan.pk}/")
        self.assertEqual(hidden.status_code, 404)
        self.assertNotIn(str(self.other_loan.pk), str(hidden.data))
        self.assertNotIn("approve", str(hidden.data).lower())
        by_number = client.get("/api/v1/ol/loans/portal/LOAN-INTEGRATION-001/")
        self.assertEqual(by_number.status_code, 200, by_number.data)
        self.assertEqual(by_number.data["data"]["loan_number"], "LOAN-INTEGRATION-001")
        self.assertNotIn(str(self.loan.pk), str(by_number.data))

    def test_dashboard_hooks_endpoint_returns_aggregates(self):
        client = APIClient()
        client.force_authenticate(self.dashboard_user)
        response = client.get("/api/v1/ol/loans/dashboard/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["data"]["loan_count"], 2)
        self.assertEqual(response.data["data"]["default_rate"], 0)
        self.assertEqual({row["name"] for row in response.data["data"]["by_product"]}, {"Integration Protection Plan", "Other Protection Plan"})

    def test_loan_notifications_are_emitted_once_and_dashboard_hooks_aggregate(self):
        event_payload = {
            "loan_id": str(self.loan.pk),
            "policy_id": str(self.policy.pk),
            "loan_number": self.loan.loan_number,
            "source_channel": "API",
        }
        DomainEvent.objects.create(event_type="LoanDisbursed", aggregate_type="OLLoan", aggregate_id=str(self.loan.pk), payload=event_payload)
        DomainEvent.objects.create(event_type="LoanDisbursed", aggregate_type="OLLoan", aggregate_id=str(self.loan.pk), payload=event_payload)
        self.assertEqual(DashboardNotification.objects.filter(external_key=f"loan:{self.loan.pk}:LoanDisbursed").count(), 1)
        # Calling the delivery seam repeatedly remains idempotent.
        from apps.ol_loans.services.integration_service import notify_loan_event

        notify_loan_event(self.loan, "LoanDisbursed", source_channel="EVENT")
        notify_loan_event(self.loan, "LoanDisbursed", source_channel="EVENT")
        self.assertEqual(DashboardNotification.objects.filter(external_key=f"loan:{self.loan.pk}:LoanDisbursed").count(), 1)
        hooks = loan_dashboard_hooks()
        self.assertEqual(hooks["loan_count"], 2)
        self.assertEqual(hooks["defaulted_count"], 0)
        self.assertEqual(hooks["default_rate"], 0)
        self.assertEqual({row["name"] for row in hooks["by_branch"]}, {"ZIC Main Branch", "ZIC North Branch"})
        self.assertEqual(sum(Decimal(row["outstanding_balance"]) for row in hooks["by_product"]), Decimal("1600.00"))
