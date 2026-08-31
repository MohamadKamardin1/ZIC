from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.common.models import DomainEvent
from apps.governance.models import AuditLog
from apps.ol_maturity_installments.events import INSTALLMENT_PLAN_CREATED
from apps.ol_maturity_installments.models import (
    InstallmentItemStatus,
    InstallmentPlanStatus,
    OLMaturityInstallmentPlan,
)
from apps.ol_parameters.models import OLAnticipatedEndowmentInstallmentRate
from apps.ol_policies.models import MaturityClaim, Policy
from apps.ol_proposals.models import OLProposal
from apps.ol_quotations.models import OLQuotation
from apps.ordinary_life.models import OLProduct
from apps.partners.models import Partner

CREATE_URL = "/api/v1/ol/maturity-installments/create/"


class InstallmentPlanCreationTestCase(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="installments-creator",
            email="installments-creator@example.com",
            password="Strong-installments-password-123!",
        )
        self.partner = Partner.objects.create(
            partner_number="ZIC-MIP-G-P-0001",
            partner_type="CLIENT",
            partner_category="INDIVIDUAL",
            party_type="INDIVIDUAL",
            legal_name="Rehema Uzalishaji",
            email="rehema.creation@example.com",
            mobile_number="+255711300001",
            phone="+255711300001",
        )
        self.agent = Partner.objects.create(
            partner_number="ZIC-MIP-G-A-0001",
            partner_type="AGENT",
            partner_category="INDIVIDUAL",
            party_type="INDIVIDUAL",
            legal_name="Faraji Creation Agent",
            email="faraji.creation@example.com",
            mobile_number="+255711300002",
            phone="+255711300002",
        )
        self.product = OLProduct.objects.create(
            code="OL_ENDOWMENT_STANDARD",
            name="Endowment Standard",
            business_area="ORDINARY_LIFE",
            is_active=True,
        )
        OLAnticipatedEndowmentInstallmentRate.objects.create(
            code="MIP-CREATE-ANNUAL-10",
            name="Creation annual rate",
            product=self.product,
            plan=None,
            installment_type="ANTICIPATED_ENDOWMENT",
            frequency="ANNUAL",
            term_from=10,
            term_to=10,
            rate_factor=Decimal("10.00000000"),
            currency="",
            is_active=True,
            effective_from=date(2026, 1, 1),
            effective_to=None,
        )
        self.policy = self._policy(
            "POL-MIP-GEN-0001",
            maturity_date=date(2026, 1, 14),
            status="MATURED",
        )
        self.active_policy = self._policy(
            "POL-MIP-GEN-ACTIVE-0001",
            maturity_date=date(2027, 1, 14),
            status="ACTIVE",
        )
        self.other_policy = self._policy(
            "POL-MIP-GEN-OTHER-0001",
            maturity_date=date(2026, 2, 14),
            status="MATURED",
        )
        self.claim = MaturityClaim.objects.create(
            policy=self.policy,
            claim_date=date(2026, 1, 15),
            maturity_value=Decimal("25000000.00"),
            loan_deduction=Decimal("0.00"),
            net_payout=Decimal("25000000.00"),
            payout_method="INSTALLMENTS",
            status="APPROVED",
            created_by=self.user,
        )
        self.pending_claim = MaturityClaim.objects.create(
            policy=self.policy,
            claim_date=date(2026, 1, 16),
            maturity_value=Decimal("25000000.00"),
            loan_deduction=Decimal("0.00"),
            net_payout=Decimal("25000000.00"),
            payout_method="INSTALLMENTS",
            status="PENDING_APPROVAL",
            created_by=self.user,
        )
        self.other_claim = MaturityClaim.objects.create(
            policy=self.other_policy,
            claim_date=date(2026, 2, 16),
            maturity_value=Decimal("20000000.00"),
            loan_deduction=Decimal("0.00"),
            net_payout=Decimal("20000000.00"),
            payout_method="INSTALLMENTS",
            status="APPROVED",
            created_by=self.user,
        )
        self.client.force_authenticate(self.user)

    def _policy(self, policy_number, *, maturity_date, status):
        quotation = OLQuotation.objects.create(
            quote_number=f"QT-{policy_number}",
            quote_name=f"Quote {policy_number}",
            quote_date=date(2026, 1, 1),
            partner=self.partner,
            currency="TZS",
        )
        proposal = OLProposal.objects.create(
            quotation=quotation,
            proposal_number=f"PROP-{policy_number}",
            status="POLICY_ISSUED",
            partner=self.partner,
            agent_partner=self.agent,
            currency="TZS",
        )
        return Policy.objects.create(
            policy_number=policy_number,
            proposal_ref=proposal,
            partner=self.partner,
            agent=self.agent,
            product_plan_ref="OL_ENDOWMENT_STANDARD",
            currency="TZS",
            sum_assured=Decimal("25000000.00"),
            premium_amount=Decimal("125000.00"),
            premium_frequency="ANNUALLY",
            term_years=10,
            risk_commencement_date=date(2016, 1, 15),
            maturity_date=maturity_date,
            status=status,
        )

    def _payload(self, *, policy=None, claim_id=None, frequency="ANNUAL", term_years=10):
        payload = {
            "policy_id": str((policy or self.policy).pk),
            "frequency": frequency,
            "term_years": term_years,
        }
        if claim_id:
            payload["maturity_claim_id"] = str(claim_id)
        return payload

    def _create(self, payload, key="plan-create-001", **headers):
        return self.client.post(
            CREATE_URL,
            payload,
            format="json",
            **{"HTTP_X_IDEMPOTENCY_KEY": key, **headers},
        )

    def test_create_plan_generates_plan_and_items(self):
        response = self._create(self._payload())
        self.assertEqual(response.status_code, 201)
        data = response.data["data"]
        self.assertEqual(data["status"], "CREATED")
        self.assertTrue(data["plan_number"])
        self.assertEqual(data["installment_count"], 10)
        self.assertEqual(data["total_payable_amount"], "25000000.00")
        self.assertEqual(len(data["items"]), 10)
        self.assertTrue(all(item["status"] == "SCHEDULED" for item in data["items"]))
        self.assertEqual(
            sum(Decimal(item["amount"]) for item in data["items"]),
            Decimal("25000000.00"),
        )

        plan = OLMaturityInstallmentPlan.objects.get(pk=data["id"])
        self.assertEqual(plan.status, InstallmentPlanStatus.CREATED)
        self.assertEqual(plan.installment_count, 10)
        self.assertEqual(plan.policy_ref, self.policy)
        self.assertEqual(plan.partner, self.partner)
        self.assertEqual(plan.items.count(), 10)
        self.assertTrue(all(item.status == InstallmentItemStatus.SCHEDULED for item in plan.items.all()))
        self.assertEqual(plan.parameter_snapshot["calculation_basis"], "INSTALLMENT_RATE_TABLE")
        self.assertIsNotNone(plan.config)
        event = DomainEvent.objects.filter(
            event_type=INSTALLMENT_PLAN_CREATED,
            aggregate_id=str(plan.pk),
        ).first()
        self.assertIsNotNone(event)

    def test_create_plan_blocks_non_matured_policy(self):
        response = self._create(self._payload(policy=self.active_policy), key="plan-create-active-001")
        self.assertEqual(response.status_code, 422)
        body = response.data
        self.assertEqual(body["error_code"], "PLAN_POLICY_NOT_MATURED")
        self.assertTrue(body["resolution_steps"])
        self.assertEqual(body["error"]["details"]["policy_number"], self.active_policy.policy_number)

    def test_idempotent_duplicate_returns_same_plan(self):
        first = self._create(self._payload(), key="plan-create-same-001")
        second = self._create(self._payload(), key="plan-create-same-001")
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(
            first.data["data"]["id"],
            second.json()["data"]["id"],
        )
        self.assertEqual(
            OLMaturityInstallmentPlan.objects.filter(idempotency_key="plan-create-same-001").count(),
            1,
        )

    def test_idempotency_conflict_returns_error(self):
        self._create(self._payload(), key="plan-create-conflict-001")
        response = self._create(self._payload(term_years=5), key="plan-create-conflict-001")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["error_code"], "INSTALLMENT_IDEMPOTENCY_CONFLICT")

    def test_create_plan_links_maturity_claim(self):
        response = self._create(self._payload(claim_id=self.claim.pk), key="plan-create-claim-001")
        self.assertEqual(response.status_code, 201)
        data = response.data["data"]
        self.assertEqual(data["maturity_claim_number"], self.claim.claim_number)
        plan = OLMaturityInstallmentPlan.objects.get(pk=data["id"])
        self.assertEqual(plan.maturity_claim_ref, self.claim)
        self.assertEqual(plan.policy_ref, self.policy)
        self.assertEqual(plan.total_maturity_value, Decimal("25000000.00"))

    def test_standalone_plan_links_only_policy(self):
        response = self._create(self._payload(), key="plan-create-standalone-001")
        self.assertEqual(response.status_code, 201)
        plan = OLMaturityInstallmentPlan.objects.get(pk=response.data["data"]["id"])
        self.assertIsNone(plan.maturity_claim_ref)
        self.assertEqual(plan.policy_ref, self.policy)

    def test_claim_not_belonging_to_policy_blocked(self):
        response = self._create(
            self._payload(policy=self.policy, claim_id=self.other_claim.pk),
            key="plan-create-mismatch-001",
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.data["error_code"], "INSTALLMENT_CLAIM_MISMATCH")

    def test_claim_not_settled_blocked(self):
        response = self._create(
            self._payload(policy=self.policy, claim_id=self.pending_claim.pk),
            key="plan-create-pending-001",
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.data["error_code"], "INSTALLMENT_CLAIM_NOT_SETTLED")

    def test_missing_idempotency_key_rejected(self):
        response = self.client.post(CREATE_URL, self._payload(), format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error_code"], "INSTALLMENT_IDEMPOTENCY_REQUIRED")

    def test_audit_row_created(self):
        response = self._create(self._payload(), key="plan-create-audit-001")
        self.assertEqual(response.status_code, 201)
        plan = OLMaturityInstallmentPlan.objects.get(pk=response.data["data"]["id"])
        log = AuditLog.objects.filter(
            app_label="ol_maturity_installments",
            model_name="olmaturityinstallmentplan",
            object_id=str(plan.pk),
        ).latest("created_at")
        self.assertEqual(log.action, "CREATE")
        self.assertEqual(log.user, self.user)
        self.assertEqual(log.after_state["total_payable_amount"], "25000000.00")
