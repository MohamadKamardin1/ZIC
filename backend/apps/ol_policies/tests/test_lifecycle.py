from datetime import date, timedelta
from decimal import Decimal
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from rest_framework.test import APITestCase

from apps.common.models import DomainEvent
from apps.ol_commitments.models import OLCommitment
from apps.ol_parameters.models import OLGracePeriod, OLReinstatementWindow
from apps.ol_policies.events import POLICY_EXPIRED, POLICY_LAPSED, POLICY_REINSTATED
from apps.ol_policies.models import Policy, PolicyStatus
from apps.ol_proposals.models import OLProposal
from apps.ol_quotations.models import OLQuotation
from apps.partners.models import Partner


class PolicyLifecycleTestCase(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="lifecycle-admin",
            email="lifecycle-admin@example.com",
            password="Strong-lifecycle-password-123!",
        )
        self.partner = Partner.objects.create(
            partner_number="ZIC-LIFE-P-0001",
            partner_type="CLIENT",
            partner_category="INDIVIDUAL",
            party_type="INDIVIDUAL",
            legal_name="Hawa Suleiman",
            email="hawa.life@example.com",
            mobile_number="+255711400001",
            phone="+255711400001",
        )
        quotation = OLQuotation.objects.create(
            quote_number="QT-LIFE-0001",
            quote_name="Lifecycle quote",
            quote_date=date(2026, 1, 1),
            partner=self.partner,
            currency="TZS",
        )
        proposal = OLProposal.objects.create(
            quotation=quotation,
            proposal_number="PROP-LIFE-0001",
            status="CONVERTED",
            partner=self.partner,
            currency="TZS",
            prospect_snapshot={},
            financial_summary_snapshot={},
        )
        self.policy = Policy.objects.create(
            proposal_ref=proposal,
            partner=self.partner,
            product_plan_ref="OL_TERM_STANDARD",
            currency="TZS",
            sum_assured=Decimal("30000000.00"),
            premium_amount=Decimal("100000.00"),
            premium_frequency="ANNUALLY",
            term_years=10,
            risk_commencement_date=date(2026, 1, 1),
            maturity_date=date(2036, 1, 1),
            status=PolicyStatus.ACTIVE,
            contract_snapshot={"plans": [{"product_code": "OL_TERM_STANDARD"}]},
        )
        self.commitment = OLCommitment.objects.create(
            commitment_number="COM-LIFE-0001",
            source_type="POLICY",
            source_reference=self.policy.policy_number,
            partner=self.partner,
            currency="TZS",
            premium_frequency="ANNUALLY",
            due_date=date.today() - timedelta(days=30),
            premium_amount=Decimal("100000.00"),
            balance=Decimal("100000.00"),
            status="PENDING",
        )
        OLGracePeriod.objects.create(
            code="GRACE-LIFE-ANNUAL",
            name="Annual policy grace",
            effective_from=date.today() - timedelta(days=1),
            premium_frequency="ANNUALLY",
            grace_days=5,
            warning_days=7,
            pre_lapse_days=8,
            lapse_days=10,
            is_active=True,
        )
        self.client.force_authenticate(self.user)

    def test_lapse_processing_uses_grace_parameters_and_is_idempotent(self):
        output = StringIO()
        call_command("process_policy_lapses", "--as-of", date.today().isoformat(), stdout=output)
        self.assertIn("changed=1", output.getvalue())
        self.policy.refresh_from_db()
        self.assertEqual(self.policy.status, PolicyStatus.LAPSED)
        self.assertEqual(self.policy.lapsed_at, date.today())
        self.assertEqual(DomainEvent.objects.filter(event_type=POLICY_LAPSED, aggregate_id=str(self.policy.pk)).count(), 1)

        output = StringIO()
        call_command("process_policy_lapses", "--as-of", date.today().isoformat(), stdout=output)
        self.assertIn("changed=0", output.getvalue())
        self.assertEqual(DomainEvent.objects.filter(event_type=POLICY_LAPSED, aggregate_id=str(self.policy.pk)).count(), 1)

    def test_reinstatement_requires_payment_and_succeeds_inside_window(self):
        self.policy.status = PolicyStatus.LAPSED
        self.policy.lapsed_at = date.today() - timedelta(days=5)
        self.policy.save(update_fields=["status", "lapsed_at"])
        OLReinstatementWindow.objects.create(
            code="REINSTATE-LIFE-30",
            name="Thirty day reinstatement",
            effective_from=date.today() - timedelta(days=1),
            days_after_lapse=30,
            require_medical_underwriting=False,
            require_outstanding_premium_payment=True,
            interest_rate=Decimal("10.0000"),
            penalty_rate=Decimal("5.0000"),
            is_active=True,
        )

        blocked = self.client.post(
            f"/api/v1/ol/policies/{self.policy.pk}/reinstate/",
            {"payment_amount": "100000.00"},
            format="json",
        )
        self.assertEqual(blocked.status_code, 422)
        self.assertIn("required_amount", blocked.data["error"]["details"])

        success = self.client.post(
            f"/api/v1/ol/policies/{self.policy.pk}/reinstate/",
            {"payment_amount": "115000.00", "as_of": date.today().isoformat()},
            format="json",
        )
        self.assertEqual(success.status_code, 200)
        self.policy.refresh_from_db()
        self.commitment.refresh_from_db()
        self.assertEqual(self.policy.status, PolicyStatus.ACTIVE)
        self.assertEqual(self.policy.reinstated_at, date.today())
        self.assertEqual(self.commitment.status, "COMPLETED")
        self.assertEqual(self.commitment.balance, Decimal("0.00"))
        self.assertEqual(DomainEvent.objects.filter(event_type=POLICY_REINSTATED, aggregate_id=str(self.policy.pk)).count(), 1)

    def test_reinstatement_is_blocked_outside_window_and_for_required_medical_clearance(self):
        self.policy.status = PolicyStatus.LAPSED
        self.policy.lapsed_at = date.today() - timedelta(days=40)
        self.policy.save(update_fields=["status", "lapsed_at"])
        OLReinstatementWindow.objects.create(
            code="REINSTATE-LIFE-MED",
            name="Medical reinstatement",
            effective_from=date.today() - timedelta(days=1),
            days_after_lapse=30,
            require_medical_underwriting=True,
            require_outstanding_premium_payment=False,
            is_active=True,
        )
        outside = self.client.post(
            f"/api/v1/ol/policies/{self.policy.pk}/reinstate/",
            {"payment_amount": "0"},
            format="json",
        )
        self.assertEqual(outside.status_code, 422)
        self.assertIn("outside", outside.data["message"])

        self.policy.lapsed_at = date.today() - timedelta(days=3)
        self.policy.save(update_fields=["lapsed_at"])
        missing_medical = self.client.post(
            f"/api/v1/ol/policies/{self.policy.pk}/reinstate/",
            {"payment_amount": "0"},
            format="json",
        )
        self.assertEqual(missing_medical.status_code, 422)
        self.assertIn("medical_clearance", missing_medical.data["field_errors"])

    def test_expiry_processing_moves_matured_active_policy_and_is_idempotent(self):
        self.commitment.delete()
        self.policy.maturity_date = date.today() - timedelta(days=1)
        self.policy.save(update_fields=["maturity_date"])
        output = StringIO()
        call_command("process_policy_expiry", "--as-of", date.today().isoformat(), stdout=output)
        self.assertIn("changed=1", output.getvalue())
        self.policy.refresh_from_db()
        self.assertEqual(self.policy.status, PolicyStatus.EXPIRED)
        self.assertEqual(self.policy.expired_at, date.today())
        self.assertEqual(DomainEvent.objects.filter(event_type=POLICY_EXPIRED, aggregate_id=str(self.policy.pk)).count(), 1)

        output = StringIO()
        call_command("process_policy_expiry", "--as-of", date.today().isoformat(), stdout=output)
        self.assertIn("changed=0", output.getvalue())
        self.assertEqual(DomainEvent.objects.filter(event_type=POLICY_EXPIRED, aggregate_id=str(self.policy.pk)).count(), 1)
