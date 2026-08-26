from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from rest_framework.test import APITestCase

from apps.common.models import DomainEvent
from apps.ol_commitments.models import CommitmentSourceType, OLCommitment
from apps.ol_parameters.models import OLRiderSetup
from apps.ol_policies.errors import PolicyError
from apps.ol_policies.events import POLICY_ISSUED
from apps.ol_policies.models import Policy, PolicyAuditLog, PolicyBenefit, PolicyMember, PolicyRider
from apps.ol_policies.services.issuance_service import issue_policy_from_proposal
from apps.ol_proposals.models import (
    OLProposal,
    OLProposalBenefit,
    OLProposalMember,
    OLProposalPlanConfig,
    OLProposalRider,
)
from apps.ol_quotations.models import OLQuotation
from apps.partners.models import Partner


class PolicyIssuanceTestCase(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="issuance-admin",
            email="issuance-admin@example.com",
            password="Strong-issuance-password-123!",
        )
        self.partner = Partner.objects.create(
            partner_number="ZIC-ISSUE-P-0001",
            partner_type="CLIENT",
            partner_category="INDIVIDUAL",
            party_type="INDIVIDUAL",
            legal_name="Salma Ali",
            email="salma.issue@example.com",
            mobile_number="+255711100001",
            phone="+255711100001",
        )
        self.agent = Partner.objects.create(
            partner_number="ZIC-ISSUE-A-0001",
            partner_type="AGENT",
            partner_category="INDIVIDUAL",
            party_type="INDIVIDUAL",
            legal_name="Hamisi Agent",
            email="hamisi.issue@example.com",
            mobile_number="+255711100002",
            phone="+255711100002",
        )
        quotation = OLQuotation.objects.create(
            quote_number="QT-ISSUE-0001",
            quote_name="Issuance test quote",
            quote_date=date(2026, 2, 1),
            partner=self.partner,
            currency="TZS",
        )
        self.proposal = OLProposal.objects.create(
            quotation=quotation,
            proposal_number="PROP-ISSUE-0001",
            status="AWAITING_FIRST_PREMIUM",
            partner=self.partner,
            agent_partner=self.agent,
            currency="TZS",
            prospect_snapshot={"name": "Salma Ali", "identity_number": "NIDA-ISSUE-1"},
            financial_summary_snapshot={
                "total_sum_assured": "50000000.00",
                "total_premium": "250000.00",
            },
        )
        self.plan_config = OLProposalPlanConfig.objects.create(
            proposal=self.proposal,
            plan_name_snapshot="ZIC Term Assurance Standard",
            sub_product_code="OL_TERM_STANDARD",
            section_number=1,
            base_sum_assured=Decimal("50000000.00"),
            term_years=10,
            payment_period_years=10,
            premium_frequency="ANNUALLY",
            quote_basis="SUM_ASSURED",
            estimated_maturity_value=Decimal("50000000.00"),
            premium_factor="NONE",
            premium_amount=Decimal("250000.00"),
            is_selected=True,
        )
        OLProposalMember.objects.create(
            proposal=self.proposal,
            member_type="POLICYHOLDER",
            first_name="Salma",
            last_name="Ali",
            date_of_birth=date(1990, 4, 12),
            gender="FEMALE",
            relationship="PRINCIPAL",
            member_sum_assured=Decimal("50000000.00"),
        )
        self.rider = OLRiderSetup.objects.create(
            code="OL_ISSUE_WAIVER",
            name="Premium Waiver",
            rider_category="WAIVER",
            benefit_type="WAIVER_PREMIUM",
            calculation_basis="SUM_ASSURED",
            is_active=True,
        )
        OLProposalRider.objects.create(
            proposal=self.proposal,
            rider=self.rider,
            rider_name_snapshot="Premium Waiver",
            plan_config=self.plan_config,
            rider_sum_assured=Decimal("50000000.00"),
            rider_term_years=10,
            benefit_basis="FIXED",
            benefit_value=Decimal("50000000.00"),
            premium_amount=Decimal("12500.00"),
            is_selected=True,
        )
        OLProposalBenefit.objects.create(
            proposal=self.proposal,
            plan_config=self.plan_config,
            code="DEATH_BENEFIT",
            name="Death Benefit",
            benefit_type="DEATH",
            basis="FIXED",
            value=Decimal("50000000.00"),
            sum_assured=Decimal("50000000.00"),
            premium_amount=Decimal("250000.00"),
            is_selected=True,
        )
        commitment = OLCommitment.objects.create(
            commitment_number="COM-ISSUE-0001",
            source_type=CommitmentSourceType.PROPOSAL,
            source_content_type=ContentType.objects.get_for_model(OLProposal),
            source_object_id=str(self.proposal.pk),
            source_reference=self.proposal.proposal_number,
            partner=self.partner,
            partner_name_snapshot=self.partner.legal_name,
            currency="TZS",
            premium_frequency="ANNUALLY",
            due_date=date(2026, 2, 1),
            premium_amount=Decimal("250000.00"),
            amount_paid=Decimal("250000.00"),
            balance=Decimal("0.00"),
            status="COMPLETED",
        )
        self.proposal.first_premium_commitment = commitment
        self.proposal.save(update_fields=["first_premium_commitment"])
        self.client.force_authenticate(self.user)

    def test_successful_issuance_copies_children_and_updates_proposal(self):
        policy, created = issue_policy_from_proposal(self.proposal.pk, actor=self.user)

        self.assertTrue(created)
        self.assertTrue(policy.policy_number)
        self.assertEqual(policy.proposal_ref_id, self.proposal.pk)
        self.assertEqual(policy.partner_id, self.partner.pk)
        self.assertEqual(policy.agent_id, self.agent.pk)
        self.assertEqual(policy.product_plan_ref, "OL_TERM_STANDARD")
        self.assertEqual(policy.sum_assured, Decimal("50000000.00"))
        self.assertEqual(policy.premium_amount, Decimal("250000.00"))
        self.assertEqual(policy.risk_commencement_date, date(2026, 2, 1))
        self.assertEqual(policy.maturity_date, date(2036, 2, 1))
        self.assertEqual(policy.first_premium_receipt_ref, "")
        self.assertEqual(PolicyMember.objects.filter(policy=policy).count(), 1)
        self.assertEqual(PolicyRider.objects.filter(policy=policy).count(), 1)
        self.assertEqual(PolicyBenefit.objects.filter(policy=policy).count(), 1)

        self.proposal.refresh_from_db()
        self.assertEqual(self.proposal.status, "CONVERTED")
        self.assertEqual(self.proposal.policy_ref, policy.pk)
        self.assertEqual(DomainEvent.objects.filter(event_type=POLICY_ISSUED, aggregate_id=str(policy.pk)).count(), 1)
        self.assertEqual(PolicyAuditLog.objects.filter(policy=policy, event_type=POLICY_ISSUED).count(), 1)

    def test_issuance_is_idempotent_and_does_not_duplicate_event_or_children(self):
        first, first_created = issue_policy_from_proposal(self.proposal.pk, actor=self.user)
        second, second_created = issue_policy_from_proposal(self.proposal.pk, actor=self.user)

        self.assertTrue(first_created)
        self.assertFalse(second_created)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(Policy.objects.filter(proposal_ref=self.proposal).count(), 1)
        self.assertEqual(PolicyMember.objects.filter(policy=first).count(), 1)
        self.assertEqual(PolicyRider.objects.filter(policy=first).count(), 1)
        self.assertEqual(PolicyBenefit.objects.filter(policy=first).count(), 1)
        self.assertEqual(DomainEvent.objects.filter(event_type=POLICY_ISSUED, aggregate_id=str(first.pk)).count(), 1)

    def test_first_premium_guard_blocks_unpaid_commitment(self):
        commitment = self.proposal.first_premium_commitment
        commitment.status = "PENDING"
        commitment.amount_paid = Decimal("0.00")
        commitment.balance = Decimal("250000.00")
        commitment.save(update_fields=["status", "amount_paid", "balance"])

        with self.assertRaises(PolicyError) as raised:
            issue_policy_from_proposal(self.proposal.pk, actor=self.user)
        self.assertEqual(raised.exception.error_code, "POLICY_FIRST_PREMIUM_NOT_POSTED")
        self.assertFalse(Policy.objects.filter(proposal_ref=self.proposal).exists())
        self.proposal.refresh_from_db()
        self.assertEqual(self.proposal.status, "AWAITING_FIRST_PREMIUM")

    def test_ineligible_proposal_status_is_blocked(self):
        self.proposal.status = "DRAFT"
        self.proposal.save(update_fields=["status"])

        with self.assertRaises(PolicyError) as raised:
            issue_policy_from_proposal(self.proposal.pk, actor=self.user)
        self.assertEqual(raised.exception.error_code, "POLICY_ISSUANCE_INVALID")

    def test_issue_endpoint_returns_policy_and_idempotent_retry(self):
        response = self.client.post(
            "/api/v1/ol/policies/issue/",
            {"proposal_id": str(self.proposal.pk)},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data["data"]["created"])
        self.assertEqual(response.data["data"]["policy"]["proposal_ref_display"], self.proposal.proposal_number)
        self.assertNotIn("partner", response.data["data"]["policy"])

        retry = self.client.post(
            "/api/v1/ol/policies/issue/",
            {"proposal_id": str(self.proposal.pk)},
            format="json",
        )
        self.assertEqual(retry.status_code, 200)
        self.assertFalse(retry.data["data"]["created"])
        self.assertTrue(retry.data["data"]["idempotent"])
