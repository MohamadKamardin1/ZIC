"""Prompt 9 integration tests: policy guard, claim linkage, portal scope, notifications."""

from datetime import date
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from apps.common.models import DomainEvent
from apps.dashboard.models import DashboardNotification
from apps.governance.models import AuditLog
from apps.ol_maturity_installments.events import (
    INSTALLMENT_PAYMENT_DUE,
    INSTALLMENT_PAYMENT_MISSED,
    INSTALLMENT_PLAN_COMPLETED,
)
from apps.ol_maturity_installments.models import (
    InstallmentPlanStatus,
    OLInstallmentItem,
    OLMaturityInstallmentPlan,
)
from apps.ol_maturity_installments.services.lifecycle import detect_missed_installments
from apps.ol_maturity_installments.services.payment import confirm_item_payment, process_item_payment
from apps.ol_policies.errors import PolicyError
from apps.ol_policies.models import MaturityClaim, Policy, PolicyNotificationLog
from apps.ol_policies.serializers import PolicyDetailSerializer
from apps.ol_policies.services.termination_service import cancel_policy, request_policy_surrender
from apps.ol_proposals.models import OLProposal
from apps.ol_quotations.models import OLQuotation
from apps.partners.models import Partner, PartnerBankAccount, UserPartnerLink
from apps.system_parameters.models import ParameterGroup, SystemParameter
from apps.system_parameters.services.config_service import ConfigurationService
from apps.users.models import User

PORTAL_LIST_URL = "/api/v1/ol/maturity-installments/portal/"
PORTAL_DETAIL_URL = "/api/v1/ol/maturity-installments/portal/{plan_id}/"
ALLOW_PARAMETER = "INSTALLMENT_ALLOW_POLICY_ACTION_WITH_ACTIVE_PLAN"


class OLInstallmentIntegrationsTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="installment-integration",
            email="installment.integration@example.com",
            password="Strong-integration-password-123!",
        )
        cls.portal_user = User.objects.create_user(
            username="installment-portal",
            email="installment.portal@example.com",
            password="Strong-portal-password-123!",
        )
        cls.other_portal_user = User.objects.create_user(
            username="other-installment-portal",
            email="other.installment.portal@example.com",
            password="Strong-other-portal-password-123!",
        )
        cls.partner = Partner.objects.create(
            partner_number="ZIC-MIP-INT-P-0001",
            partner_type="CLIENT",
            partner_category="INDIVIDUAL",
            party_type="INDIVIDUAL",
            legal_name="Integration Policyholder",
            email="integration.policyholder@example.com",
            mobile_number="+255711900001",
            phone="+255711900001",
        )
        cls.other_partner = Partner.objects.create(
            partner_number="ZIC-MIP-INT-P-0002",
            partner_type="CLIENT",
            partner_category="INDIVIDUAL",
            party_type="INDIVIDUAL",
            legal_name="Other Policyholder",
            email="other.policyholder@example.com",
            mobile_number="+255711900002",
            phone="+255711900002",
        )
        cls.agent = Partner.objects.create(
            partner_number="ZIC-MIP-INT-A-0001",
            partner_type="AGENT",
            partner_category="INDIVIDUAL",
            party_type="INDIVIDUAL",
            legal_name="Integration Agent",
            email="integration.agent@example.com",
        )
        UserPartnerLink.objects.create(
            user=cls.portal_user, partner=cls.partner, is_primary=True, created_by=cls.portal_user
        )
        UserPartnerLink.objects.create(
            user=cls.other_portal_user, partner=cls.other_partner, is_primary=True, created_by=cls.other_portal_user
        )

    # ------------------------------------------------------------------
    # Fixtures
    # ------------------------------------------------------------------

    def _policy(self, partner, *, number, status="ACTIVE", maturity_date=None):
        quotation = OLQuotation.objects.create(
            quote_number=f"QT-{number}",
            quote_name=f"Quote {number}",
            quote_date=date.today(),
            partner=partner,
            currency="TZS",
        )
        proposal = OLProposal.objects.create(
            quotation=quotation,
            proposal_number=f"PROP-{number}",
            status="CONVERTED",
            partner=partner,
            currency="TZS",
            prospect_snapshot={},
            financial_summary_snapshot={},
        )
        return Policy.objects.create(
            policy_number=f"POL-{number}",
            proposal_ref=proposal,
            partner=partner,
            agent=self.agent,
            product_plan_ref="OL_ENDOWMENT_STANDARD",
            currency="TZS",
            sum_assured=Decimal("25000000.00"),
            premium_amount=Decimal("125000.00"),
            premium_frequency="ANNUALLY",
            term_years=10,
            risk_commencement_date=date(2016, 1, 15),
            maturity_date=maturity_date or date(2026, 1, 14),
            status=status,
        )

    def _plan(self, policy, *, status="CREATED", claim=None):
        return OLMaturityInstallmentPlan.objects.create(
            policy_ref=policy,
            maturity_claim_ref=claim,
            partner=policy.partner,
            currency="TZS",
            total_maturity_value=Decimal("25000000.00"),
            total_payable_amount=Decimal("25000000.00"),
            installment_count=2,
            frequency="ANNUAL",
            start_date=date(2025, 1, 14),
            end_date=date(2026, 1, 14),
            status=status,
            created_by=self.user,
        )

    def _item(self, plan, number, *, status="SCHEDULED", paid_date=None, payment_reference=""):
        return OLInstallmentItem.objects.create(
            plan_ref=plan,
            installment_number=number,
            due_date=date(2025, 1, 14) if number == 1 else date(2026, 1, 14),
            amount=Decimal("12500000.00"),
            status=status,
            paid_date=paid_date,
            payment_reference=payment_reference,
            created_by=self.user,
        )

    def _bank(self, partner):
        return PartnerBankAccount.objects.create(
            partner=partner,
            bank_name="NBC Bank",
            branch_name="Dar es Salaam",
            account_name="Integration Policyholder",
            account_number="0123456789",
            swift_code="NLCBTZTX",
            iban="TZ0010123456789",
            currency="TZS",
            is_primary=True,
            is_verified=True,
        )

    def _payment_channels(self, policy):
        recipients = {("EMAIL", policy.partner.email), ("SMS", policy.partner.mobile_number)}
        if self.portal_user.email and self.portal_user.active_partner_links().filter(partner=policy.partner).exists():
            recipients.add(("EMAIL", self.portal_user.email))
        return len(recipients)

    # ------------------------------------------------------------------
    # Claims integration
    # ------------------------------------------------------------------

    def test_claim_linked_and_marked_paid_via_installments_on_plan_start(self):
        policy = self._policy(self.partner, number="INT-CLAIM-001", status="MATURED")
        claim = MaturityClaim.objects.create(
            policy=policy,
            maturity_value=Decimal("25000000.00"),
            net_payout=Decimal("25000000.00"),
            status="APPROVED",
        )
        plan = self._plan(policy, claim=claim)
        self._item(plan, 1)
        self._item(plan, 2)
        self._bank(self.partner)

        item = plan.items.get(installment_number=1)
        _item, _requisition, created = process_item_payment(item_id=item.pk, actor=self.user)
        self.assertTrue(created)
        _item, plan_completed, confirmed = confirm_item_payment(item_id=item.pk, actor=self.user)
        self.assertTrue(confirmed)
        self.assertFalse(plan_completed)

        plan.refresh_from_db()
        self.assertEqual(plan.status, InstallmentPlanStatus.ACTIVE)
        self.assertIsNotNone(plan.activated_at)
        self.assertEqual(plan.activated_by, self.user)
        claim.refresh_from_db()
        self.assertEqual(claim.status, "PAID_VIA_INSTALLMENTS")
        self.assertTrue(
            AuditLog.objects.filter(action="INSTALLMENT_PLAN_ACTIVATED", object_id=str(plan.pk)).exists()
        )
        self.assertTrue(
            AuditLog.objects.filter(
                action="MATURITY_CLAIM_PAID_VIA_INSTALLMENTS", object_id=str(claim.pk)
            ).exists()
        )

    def test_policy_detail_exposes_maturity_installment_plan_summary(self):
        policy = self._policy(self.partner, number="INT-SUMMARY-001", status="MATURED")
        plan = self._plan(policy, status="ACTIVE")
        self._item(plan, 1, status="PAID", paid_date=date(2025, 1, 14), payment_reference="REF-INT-0001")
        self._item(plan, 2)

        payload = PolicyDetailSerializer(policy).data["maturity_installment_plan_summary"]
        self.assertEqual(payload["count"], 1)
        self.assertEqual(payload["active_count"], 1)
        self.assertEqual(payload["completed_count"], 0)
        row = payload["plans"][0]
        self.assertEqual(row["plan_number"], plan.plan_number)
        self.assertEqual(row["policy_number"], "POL-INT-SUMMARY-001")
        self.assertEqual(row["status"], InstallmentPlanStatus.ACTIVE)
        self.assertEqual(row["total_amount"], "25000000.00")
        self.assertEqual(row["paid_amount"], "12500000.00")
        self.assertEqual(row["balance"], "12500000.00")
        self.assertEqual(row["next_due_date"], "2026-01-14")

    # ------------------------------------------------------------------
    # Policy integration guard
    # ------------------------------------------------------------------

    def test_surrender_blocked_by_active_maturity_plan(self):
        policy = self._policy(self.partner, number="INT-SURR-001", status="ACTIVE")
        plan = self._plan(policy, status="CREATED")
        with self.assertRaises(PolicyError) as raised:
            request_policy_surrender(policy.pk)
        self.assertEqual(raised.exception.code, "POLICY_SURRENDER_BLOCKED")
        self.assertEqual(raised.exception.details["blocking_plans"][0]["plan_number"], plan.plan_number)
        self.assertFalse(raised.exception.details["parameter_allows"])
        policy.refresh_from_db()
        self.assertEqual(policy.status, "ACTIVE")

    def test_cancel_blocked_by_active_maturity_plan(self):
        policy = self._policy(self.partner, number="INT-CANC-001", status="ACTIVE")
        plan = self._plan(policy, status="ACTIVE")
        with self.assertRaises(PolicyError) as raised:
            cancel_policy(policy.pk, reason="Blocked cancellation test.")
        self.assertEqual(raised.exception.code, "POLICY_CANCELLATION_BLOCKED")
        self.assertEqual(raised.exception.details["blocking_plans"][0]["plan_number"], plan.plan_number)
        policy.refresh_from_db()
        self.assertEqual(policy.status, "ACTIVE")

    def test_parameter_allows_policy_action_with_active_plan(self):
        policy = self._policy(self.partner, number="INT-PARAM-001", status="ACTIVE")
        self._plan(policy, status="ACTIVE")
        group, _created = ParameterGroup.objects.get_or_create(
            code="OL_MATURITY_INSTALLMENTS", defaults={"name": "OL Maturity Installments"}
        )
        SystemParameter.objects.create(
            group=group,
            code=ALLOW_PARAMETER,
            name="Allow policy action with active plan",
            value_type="BOOLEAN",
            boolean_value=True,
            is_active=True,
        )
        ConfigurationService.invalidate_parameter(ALLOW_PARAMETER)
        policy, _requisition = cancel_policy(policy.pk, reason="Parameter permits cancellation.")
        policy.refresh_from_db()
        self.assertEqual(policy.status, "CANCELLED")
        # The DB row rolls back with the test but the LocMemCache entry does not.
        ConfigurationService.invalidate_parameter(ALLOW_PARAMETER)

    # ------------------------------------------------------------------
    # Partner portal
    # ------------------------------------------------------------------

    def test_portal_is_partner_scoped_read_only_and_sanitizes_cross_partner_detail(self):
        own_policy = self._policy(self.partner, number="INT-PORT-001", status="MATURED")
        own_plan = self._plan(own_policy, status="ACTIVE")
        self._item(own_plan, 1, status="PAID", paid_date=date(2025, 1, 14), payment_reference="REF-PORT-0001")
        self._item(own_plan, 2)
        other_policy = self._policy(self.other_partner, number="INT-PORT-002", status="MATURED")
        other_plan = self._plan(other_policy, status="ACTIVE")
        self._item(other_plan, 1)

        client = APIClient()
        client.force_authenticate(self.portal_user)

        listing = client.get(PORTAL_LIST_URL)
        self.assertEqual(listing.status_code, 200)
        results = listing.data["data"]["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["plan_number"], own_plan.plan_number)
        self.assertNotIn(str(other_plan.pk), str(listing.data))

        hidden = client.get(PORTAL_DETAIL_URL.format(plan_id=other_plan.pk))
        self.assertEqual(hidden.status_code, 404)
        self.assertEqual(hidden.data["error_code"], "PORTAL_RESOURCE_NOT_FOUND")

        by_number = client.get(PORTAL_DETAIL_URL.format(plan_id=own_plan.plan_number))
        self.assertEqual(by_number.status_code, 200)
        self.assertEqual(by_number.data["data"]["plan_number"], own_plan.plan_number)
        self.assertEqual(by_number.data["data"]["total_installments"], 2)
        self.assertEqual(len(by_number.data["data"]["schedule"]), 2)
        self.assertEqual(by_number.data["data"]["paid_installments"], 1)
        self.assertEqual(by_number.data["data"]["paid_amount"], "12,500,000.00")

        read_only = client.post(PORTAL_LIST_URL, {}, format="json")
        self.assertEqual(read_only.status_code, 405)

    # ------------------------------------------------------------------
    # Notifications (domain-event outbox -> notification center)
    # ------------------------------------------------------------------

    def test_installment_payment_due_notification_emitted_once(self):
        policy = self._policy(self.partner, number="INT-NOTIF-DUE-001", status="MATURED")
        plan = self._plan(policy)
        self._item(plan, 1)
        self._item(plan, 2)
        self._bank(self.partner)
        expected = self._payment_channels(policy)

        item = plan.items.get(installment_number=1)
        _item, _requisition, created = process_item_payment(item_id=item.pk, actor=self.user)
        self.assertTrue(created)
        self.assertEqual(
            PolicyNotificationLog.objects.filter(policy=policy, event_type=INSTALLMENT_PAYMENT_DUE).count(),
            expected,
        )
        self.assertTrue(
            DashboardNotification.objects.filter(
                owner=self.portal_user,
                external_key=f"installment:{plan.pk}:{INSTALLMENT_PAYMENT_DUE}",
            ).exists()
        )

        # Replaying the idempotent process must not emit a second event or copy.
        event_count = DomainEvent.objects.filter(
            event_type=INSTALLMENT_PAYMENT_DUE, aggregate_id=str(plan.pk)
        ).count()
        _item, _requisition, replayed = process_item_payment(item_id=item.pk, actor=self.user)
        self.assertFalse(replayed)
        self.assertEqual(
            DomainEvent.objects.filter(event_type=INSTALLMENT_PAYMENT_DUE, aggregate_id=str(plan.pk)).count(),
            event_count,
        )
        self.assertEqual(
            PolicyNotificationLog.objects.filter(policy=policy, event_type=INSTALLMENT_PAYMENT_DUE).count(),
            expected,
        )

    def test_installment_payment_missed_notification_emitted_once(self):
        policy = self._policy(self.partner, number="INT-NOTIF-MISS-001", status="MATURED")
        plan = self._plan(policy)
        self._item(plan, 1)
        expected = self._payment_channels(policy)

        result = detect_missed_installments(as_of=date(2026, 2, 1), plan_id=plan.pk)
        self.assertGreaterEqual(result.missed, 1)
        self.assertEqual(
            PolicyNotificationLog.objects.filter(policy=policy, event_type=INSTALLMENT_PAYMENT_MISSED).count(),
            expected,
        )

        # Re-running the idempotent batch must not emit again.
        result_again = detect_missed_installments(as_of=date(2026, 2, 1), plan_id=plan.pk)
        self.assertEqual(result_again.missed, 0)
        self.assertEqual(
            PolicyNotificationLog.objects.filter(policy=policy, event_type=INSTALLMENT_PAYMENT_MISSED).count(),
            expected,
        )

    def test_installment_plan_completed_notification_emitted_once(self):
        policy = self._policy(self.partner, number="INT-NOTIF-DONE-001", status="MATURED")
        plan = self._plan(policy)
        self._item(plan, 1)
        self._item(plan, 2)
        self._bank(self.partner)
        expected = self._payment_channels(policy)

        for number in (1, 2):
            item = plan.items.get(installment_number=number)
            process_item_payment(item_id=item.pk, actor=self.user)
            confirm_item_payment(item_id=item.pk, actor=self.user)
        plan.refresh_from_db()
        self.assertEqual(plan.status, InstallmentPlanStatus.COMPLETED)
        self.assertEqual(
            PolicyNotificationLog.objects.filter(policy=policy, event_type=INSTALLMENT_PLAN_COMPLETED).count(),
            expected,
        )

        # Reconfirming a paid item must not duplicate the completion event.
        event_count = DomainEvent.objects.filter(
            event_type=INSTALLMENT_PLAN_COMPLETED, aggregate_id=str(plan.pk)
        ).count()
        paid_item = plan.items.get(installment_number=1)
        confirm_item_payment(item_id=paid_item.pk, actor=self.user)
        self.assertEqual(
            DomainEvent.objects.filter(event_type=INSTALLMENT_PLAN_COMPLETED, aggregate_id=str(plan.pk)).count(),
            event_count,
        )
        self.assertEqual(
            PolicyNotificationLog.objects.filter(policy=policy, event_type=INSTALLMENT_PLAN_COMPLETED).count(),
            expected,
        )
