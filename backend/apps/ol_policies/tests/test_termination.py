from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.common.models import DomainEvent
from apps.front_office.models import FORequisition
from apps.ol_commitments.models import OLCommitment
from apps.ol_parameters.models import OLPaidUpRate, OLPaidUpSetup, OLSurrenderSetup
from apps.ol_policies.events import POLICY_CANCELLED, POLICY_PAID_UP, POLICY_SURRENDER_REQUESTED
from apps.ol_policies.models import Policy, PolicyStatus, SurrenderRequest, SurrenderStatus
from apps.ol_proposals.models import OLProposal
from apps.ol_quotations.models import OLQuotation
from apps.ordinary_life.models import OLProduct as LegacyProduct
from apps.partners.models import Partner


class PolicyTerminationTestCase(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="termination-admin",
            email="termination-admin@example.com",
            password="Strong-termination-password-123!",
        )
        self.partner = Partner.objects.create(
            partner_number="ZIC-TERM-P-0001",
            partner_type="CLIENT",
            partner_category="INDIVIDUAL",
            party_type="INDIVIDUAL",
            legal_name="Mwana Amani",
            email="mwana.term@example.com",
            mobile_number="+255711500001",
            phone="+255711500001",
        )
        quotation = OLQuotation.objects.create(
            quote_number="QT-TERM-0001",
            quote_name="Termination quote",
            quote_date=date.today() - timedelta(days=400),
            partner=self.partner,
            currency="TZS",
        )
        proposal = OLProposal.objects.create(
            quotation=quotation,
            proposal_number="PROP-TERM-0001",
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
            sum_assured=Decimal("1000000.00"),
            premium_amount=Decimal("100000.00"),
            premium_frequency="ANNUALLY",
            term_years=10,
            risk_commencement_date=date.today() - timedelta(days=400),
            maturity_date=date.today() + timedelta(days=3000),
            status=PolicyStatus.ACTIVE,
            contract_snapshot={
                "plans": [{"product_code": "OL_TERM_STANDARD"}],
                "surrender_value_rate": "0.80",
                "free_look_days": 5000,
            },
        )
        self.commitment = OLCommitment.objects.create(
            commitment_number="COM-TERM-0001",
            source_type="POLICY",
            source_reference=self.policy.policy_number,
            partner=self.partner,
            currency="TZS",
            premium_frequency="ANNUALLY",
            due_date=date.today() - timedelta(days=20),
            premium_amount=Decimal("100000.00"),
            amount_paid=Decimal("100000.00"),
            balance=Decimal("0.00"),
            status="COMPLETED",
        )
        self.client.force_authenticate(self.user)

    def test_surrender_calculates_value_charge_and_creates_requisition(self):
        OLSurrenderSetup.objects.create(
            code="SURRENDER-TERM-1",
            name="Standard surrender",
            effective_from=date.today() - timedelta(days=1),
            minimum_premiums_paid=1,
            minimum_policy_months=1,
            minimum_premium_paid_ratio=Decimal("100"),
            surrender_charge_type="PERCENTAGE",
            surrender_charge_value=Decimal("10"),
            partial_surrender_allowed=False,
            require_approval=False,
            is_active=True,
        )
        response = self.client.post(
            f"/api/v1/ol/policies/{self.policy.pk}/surrender/",
            {"as_of": date.today().isoformat()},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.policy.refresh_from_db()
        self.assertEqual(self.policy.status, PolicyStatus.SURRENDER_PENDING)
        surrender = SurrenderRequest.objects.get(policy=self.policy)
        self.assertEqual(surrender.surrender_value, Decimal("800000.00"))
        self.assertEqual(surrender.charges, Decimal("80000.00"))
        self.assertEqual(surrender.net_surrender_value, Decimal("720000.00"))
        self.assertEqual(surrender.status, SurrenderStatus.PENDING_PAYMENT)
        self.assertTrue(surrender.payment_requisition_id)
        self.assertEqual(FORequisition.objects.get(pk=surrender.payment_requisition_id).amount, Decimal("720000.00"))
        self.assertEqual(DomainEvent.objects.filter(event_type=POLICY_SURRENDER_REQUESTED, aggregate_id=str(self.policy.pk)).count(), 1)

        retry = self.client.post(f"/api/v1/ol/policies/{self.policy.pk}/surrender/", {}, format="json")
        self.assertEqual(retry.status_code, 200)
        self.assertEqual(SurrenderRequest.objects.filter(policy=self.policy).count(), 1)

    def test_surrender_blocked_when_active_loan_balance_exists(self):
        OLSurrenderSetup.objects.create(
            code="SURRENDER-TERM-LOAN",
            name="Loan surrender",
            effective_from=date.today() - timedelta(days=1),
            minimum_premiums_paid=1,
            minimum_policy_months=1,
            minimum_premium_paid_ratio=Decimal("0"),
            is_active=True,
        )
        snapshot = dict(self.policy.contract_snapshot)
        snapshot["active_loan_balance"] = "10000.00"
        self.policy.contract_snapshot = snapshot
        self.policy.save(update_fields=["contract_snapshot"])
        response = self.client.post(f"/api/v1/ol/policies/{self.policy.pk}/surrender/", {}, format="json")
        self.assertEqual(response.status_code, 422)
        self.assertIn("active policy loan", response.data["message"])
        self.assertFalse(SurrenderRequest.objects.filter(policy=self.policy).exists())

    def test_paid_up_conversion_reduces_sum_assured_and_stops_future_commitments(self):
        product = LegacyProduct.objects.create(code="OL_TERM_STANDARD_PAIDUP", name="Standard paid-up product", is_active=True)
        OLPaidUpSetup.objects.create(
            code="PAIDUP-TERM-1",
            name="Standard paid-up",
            effective_from=date.today() - timedelta(days=1),
            minimum_premiums_paid=1,
            minimum_policy_months=1,
            allow_paidup=True,
            is_active=True,
        )
        self.policy.contract_snapshot = {"plans": [{"product_code": product.code}]}
        self.policy.save(update_fields=["contract_snapshot"])
        OLPaidUpRate.objects.create(
            code="PAIDUP-RATE-TERM-1",
            name="Paid-up factor year one",
            effective_from=date.today() - timedelta(days=1),
            product=product,
            table_code="PAIDUP-TERM",
            policy_year_from=1,
            policy_year_to=20,
            rate_factor=Decimal("0.60"),
            is_active=True,
        )
        future = OLCommitment.objects.create(
            commitment_number="COM-TERM-FUTURE",
            source_type="POLICY",
            source_reference=self.policy.policy_number,
            partner=self.partner,
            currency="TZS",
            premium_frequency="ANNUALLY",
            due_date=date.today() + timedelta(days=30),
            premium_amount=Decimal("100000.00"),
            balance=Decimal("100000.00"),
            status="PENDING",
        )
        self.policy.status = PolicyStatus.LAPSED
        self.policy.lapsed_at = date.today() - timedelta(days=10)
        self.policy.save(update_fields=["status", "lapsed_at"])

        response = self.client.post(f"/api/v1/ol/policies/{self.policy.pk}/paid-up/", {}, format="json")
        self.assertEqual(response.status_code, 200)
        self.policy.refresh_from_db()
        future.refresh_from_db()
        self.assertEqual(self.policy.status, PolicyStatus.PAID_UP)
        self.assertEqual(self.policy.sum_assured, Decimal("600000.00"))
        self.assertEqual(future.status, "CANCELLED")
        self.assertEqual(future.balance, Decimal("0.00"))
        self.assertEqual(DomainEvent.objects.filter(event_type=POLICY_PAID_UP, aggregate_id=str(self.policy.pk)).count(), 1)

    def test_free_look_cancellation_refunds_paid_premiums_and_creates_requisition(self):
        response = self.client.post(
            f"/api/v1/ol/policies/{self.policy.pk}/cancel/",
            {"reason": "Customer exercised the free-look right."},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.policy.refresh_from_db()
        self.assertEqual(self.policy.status, PolicyStatus.CANCELLED)
        cancellation = self.policy.contract_snapshot["cancellation"]
        self.assertEqual(cancellation["refund_amount"], "100000.00")
        self.assertTrue(cancellation["within_free_look"])
        self.assertTrue(cancellation["requisition_number"])
        self.assertEqual(DomainEvent.objects.filter(event_type=POLICY_CANCELLED, aggregate_id=str(self.policy.pk)).count(), 1)

    def test_cancellation_requires_reason_and_does_not_repeat_terminal_action(self):
        missing = self.client.post(f"/api/v1/ol/policies/{self.policy.pk}/cancel/", {}, format="json")
        self.assertEqual(missing.status_code, 422)
        self.assertIn("reason", missing.data["field_errors"])
        self.policy.status = PolicyStatus.CANCELLED
        self.policy.save(update_fields=["status"])
        repeat = self.client.post(
            f"/api/v1/ol/policies/{self.policy.pk}/cancel/",
            {"reason": "Repeat"},
            format="json",
        )
        self.assertEqual(repeat.status_code, 422)
