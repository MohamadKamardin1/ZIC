from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.common.models import DomainEvent
from apps.ol_policies.models import Policy, PolicyNotificationLog, PolicyStatus
from apps.ol_policies.services.integration_service import (
    notify_policy_event,
    policy_dashboard_hooks,
    process_maturing_soon,
)
from apps.ol_proposals.models import OLProposal
from apps.ol_quotations.models import OLQuotation
from apps.partners.models import Partner, UserPartnerLink


class PolicyIntegrationTestCase(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.staff = User.objects.create_superuser(
            username="integration-admin",
            email="integration-admin@example.com",
            password="Strong-integration-password-123!",
        )
        self.portal = User.objects.create_user(
            username="portal-client",
            email="portal-client@example.com",
            password="Strong-portal-password-123!",
            user_type="PORTAL_USER",
        )
        self.other_portal = User.objects.create_user(
            username="portal-other",
            email="portal-other@example.com",
            password="Strong-portal-password-123!",
            user_type="PORTAL_USER",
        )
        self.partner = Partner.objects.create(
            partner_number="ZIC-INT-P-0001",
            partner_type="CLIENT",
            partner_category="INDIVIDUAL",
            party_type="INDIVIDUAL",
            legal_name="Hassan Salim",
            email="hassan.integration@example.com",
            mobile_number="+255711900001",
            phone="+255711900001",
            date_of_birth=date(1985, 1, 5),
            occupation="Teacher",
        )
        self.other_partner = Partner.objects.create(
            partner_number="ZIC-INT-P-0002",
            partner_type="CLIENT",
            partner_category="INDIVIDUAL",
            party_type="INDIVIDUAL",
            legal_name="Other Client",
            email="other.integration@example.com",
            mobile_number="+255711900002",
            phone="+255711900002",
        )
        UserPartnerLink.objects.create(user=self.portal, partner=self.partner, is_primary=True)
        UserPartnerLink.objects.create(user=self.other_portal, partner=self.other_partner, is_primary=True)
        self.policy = self._make_policy("INT-001", self.partner, date.today() + timedelta(days=20))
        self.other_policy = self._make_policy("INT-002", self.other_partner, date.today() + timedelta(days=200))

    def _make_policy(self, suffix, partner, maturity_date):
        quotation = OLQuotation.objects.create(
            quote_number=f"QT-INT-{suffix}",
            quote_name=f"Integration {suffix}",
            quote_date=date.today(),
            partner=partner,
            currency="TZS",
        )
        proposal = OLProposal.objects.create(
            quotation=quotation,
            proposal_number=f"PROP-INT-{suffix}",
            status="CONVERTED",
            partner=partner,
            currency="TZS",
            prospect_snapshot={},
            financial_summary_snapshot={},
        )
        return Policy.objects.create(
            proposal_ref=proposal,
            partner=partner,
            product_plan_ref="OL_INTEGRATION_PLAN",
            currency="TZS",
            sum_assured=Decimal("1000000.00"),
            premium_amount=Decimal("100000.00"),
            premium_frequency="MONTHLY",
            term_years=10,
            risk_commencement_date=date.today(),
            maturity_date=maturity_date,
            status=PolicyStatus.ACTIVE,
            contract_snapshot={"occupation": "Teacher", "plans": [{"product_code": "OL_INTEGRATION_PLAN"}]},
        )

    def test_portal_list_and_detail_are_scoped_and_hide_sensitive_financial_data(self):
        self.client.force_authenticate(self.portal)
        listing = self.client.get("/api/v1/ol/policies/portal/")
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.data["data"]["count"], 1)
        self.assertEqual(listing.data["data"]["results"][0]["policy_number"], self.policy.policy_number)
        self.assertEqual(listing.data["data"]["results"][0]["id"], str(self.policy.pk))
        self.assertNotIn("premium_amount", listing.data["data"]["results"][0])

        detail = self.client.get(f"/api/v1/ol/policies/portal/{self.policy.pk}/")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.data["data"]["id"], str(self.policy.pk))
        self.assertNotIn("sum_assured", detail.data["data"])
        denied = self.client.get(f"/api/v1/ol/policies/portal/{self.other_policy.pk}/")
        self.assertEqual(denied.status_code, 404)

    def test_claim_data_and_reinsurance_risk_data_are_available_to_authorized_policy_users(self):
        self.client.force_authenticate(self.staff)
        claim_data = self.client.get(f"/api/v1/ol/policies/{self.policy.pk}/claim-data/")
        self.assertEqual(claim_data.status_code, 200)
        self.assertTrue(claim_data.data["data"]["coverage_available"])
        self.assertEqual(claim_data.data["data"]["sum_assured"], "1000000.00")
        risk = self.client.get(f"/api/v1/ol/policies/{self.policy.pk}/reinsurance-risk/")
        self.assertEqual(risk.status_code, 200)
        self.assertEqual(risk.data["data"]["occupation"], "Teacher")
        self.assertEqual(risk.data["data"]["age"], 41)

    def test_claim_settlement_exhaustion_closes_policy_and_retry_is_idempotent(self):
        self.client.force_authenticate(self.staff)
        first = self.client.post(
            "/api/v1/ol/policies/integrations/claim-settled/",
            {"policy_id": str(self.policy.pk), "claim_id": "CLM-INT-001", "claim_type": "DEATH", "settlement_amount": "1000000.00"},
            format="json",
        )
        self.assertEqual(first.status_code, 200)
        self.policy.refresh_from_db()
        self.assertEqual(self.policy.status, PolicyStatus.CLAIM_SETTLED)
        second = self.client.post(
            "/api/v1/ol/policies/integrations/claim-settled/",
            {"policy_id": str(self.policy.pk), "claim_id": "CLM-INT-001", "claim_type": "DEATH", "settlement_amount": "1000000.00"},
            format="json",
        )
        self.assertEqual(second.status_code, 200)
        self.assertFalse(second.data["data"]["changed"])
        self.assertEqual(DomainEvent.objects.filter(event_type="PolicyClaimSettledApplied", aggregate_id=str(self.policy.pk)).count(), 1)

    def test_notifications_maturity_reminder_and_dashboard_hooks_are_emitted(self):
        count = notify_policy_event(self.policy, "PolicyIssued", actor=self.staff)
        self.assertGreaterEqual(count, 2)
        self.assertTrue(PolicyNotificationLog.objects.filter(policy=self.policy, event_type="PolicyIssued", channel="EMAIL").exists())
        self.assertTrue(DomainEvent.objects.filter(event_type="PolicyMaturingSoon", aggregate_id=str(self.policy.pk)).exists() is False)
        result = process_maturing_soon(as_of=date.today(), window_days=30, actor=self.staff)
        self.assertEqual(result["processed"], 1)
        self.assertTrue(DomainEvent.objects.filter(event_type="PolicyMaturingSoon", aggregate_id=str(self.policy.pk)).exists())
        self.assertTrue(PolicyNotificationLog.objects.filter(policy=self.policy, event_type="PolicyMaturingSoon").exists())
        hooks = policy_dashboard_hooks()
        self.assertEqual(hooks["active_policy_count"], 2)
        self.assertEqual(hooks["premium_income_annualized"], "2400000.00")
        self.assertEqual(hooks["lapsed_ratio"], 0)
