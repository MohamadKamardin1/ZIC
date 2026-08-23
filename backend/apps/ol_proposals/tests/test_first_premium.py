from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APITestCase as DRFTestCase

from apps.governance.models import AuditLog
from apps.ol_commitments.models import OLCommitment, OLCommitmentAllocation
from apps.ol_parameters.models import OLCommitmentStatus
from apps.ol_proposals.errors import ProposalError
from apps.ol_proposals.models import OLProposal
from apps.ol_proposals.services.first_premium_service import (
    ensure_first_premium_posted,
    first_premium_posted,
    first_premium_status,
    link_first_premium_commitment,
)
from apps.ol_quotations.models import OLQuotation, OLQuotationVersion
from apps.partners.models import Partner

User = get_user_model()

REPO_ROOT = Path(__file__).resolve().parents[4]
SEAM_DOC = REPO_ROOT / "docs" / "OL_PROPOSALS_RECEIPTS_SEAM.md"


def seed_commitment_statuses():
    defaults = [
        ("PENDING", "Pending", 10),
        ("PARTIALLY_PAID", "Partially paid", 20),
        ("COMPLETED", "Completed", 30),
    ]
    for code, name, order in defaults:
        OLCommitmentStatus.objects.update_or_create(
            code=code,
            defaults={"name": name, "applies_to": "COMMITMENT", "display_order": order, "is_active": True},
        )


def make_proposal(number="OLP-2026-FP1"):
    partner = Partner.objects.create(
        partner_number=f"PT-FP-{number[-4:]}",
        partner_type="INDIVIDUAL",
        party_type="INDIVIDUAL",
        first_name="Zawadi",
        surname="Kimaro",
        email="zawadi.fp@example.com",
        is_active=True,
        status="ACTIVE",
    )
    quotation = OLQuotation.objects.create(quote_number=f"Q-FP-{number[-4:]}", currency="TZS")
    quotation.partner = partner
    quotation.partner_verified = True
    quotation.current_version_number = 1
    quotation.save()
    version = OLQuotationVersion.objects.create(quotation=quotation, version_number=1, status="FINALIZED")
    proposal = OLProposal(
        quotation=quotation,
        quotation_version=version,
        proposal_number=number,
        status="AWAITING_FIRST_PREMIUM",
        partner=partner,
        partner_name_snapshot=partner.legal_name or str(partner),
        currency="TZS",
        expiry_date=date.today() + timedelta(days=30),
        payment_ready=True,
        financial_summary_snapshot={"total_premium": "50000.00"},
    )
    proposal.save()
    return proposal


def allocate(commitment, amount, receipt_reference, mode="CASH", user=None):
    OLCommitmentAllocation.objects.create(
        commitment=commitment,
        receipt_reference=receipt_reference,
        amount=Decimal(str(amount)),
        payment_mode=mode,
        currency="TZS",
        allocated_by=user,
    )
    commitment.amount_paid = Decimal(str(amount))
    commitment.save()


class FirstPremiumServiceTests(TestCase):
    def setUp(self):
        seed_commitment_statuses()
        self.user = User.objects.create_user(username="fp_ops", password="Password@12345", email="fp_ops@zic.tz")
        self.proposal = make_proposal()
        self.commitment, self.created = link_first_premium_commitment(proposal=self.proposal, actor=self.user, source_channel="API")

    def test_link_creates_proposal_commitment_once_and_reuses(self):
        self.assertTrue(self.created)
        self.assertEqual(OLCommitment.objects.count(), 1)
        self.assertEqual(self.commitment.source_type, "PROPOSAL")
        self.assertEqual(self.commitment.installment_number, 1)
        self.assertEqual(self.commitment.source_reference, self.proposal.proposal_number)
        self.assertEqual(self.proposal.first_premium_commitment, self.commitment)
        self.assertEqual(self.commitment.premium_amount, Decimal("50000.00"))

        again, again_created = link_first_premium_commitment(proposal=self.proposal, actor=self.user, source_channel="API")
        self.assertFalse(again_created)
        self.assertEqual(again.pk, self.commitment.pk)
        self.assertEqual(OLCommitment.objects.count(), 1)
        self.assertTrue(
            AuditLog.objects.filter(action="LINK_FIRST_PREMIUM_COMMITMENT", object_id=str(self.proposal.pk)).exists()
        )

    def test_guard_false_for_partial_payment_and_true_for_full(self):
        self.assertFalse(first_premium_posted(self.proposal))

        allocate(self.commitment, "20000.00", "RCT-FP-0001", user=self.user)
        self.commitment.status = "PARTIALLY_PAID"
        self.commitment.save()
        self.proposal.refresh_from_db()
        self.assertFalse(first_premium_posted(self.proposal))
        with self.assertRaises(ProposalError) as ctx:
            ensure_first_premium_posted(self.proposal)
        self.assertEqual(ctx.exception.error_code, "PROPOSAL_FIRST_PREMIUM_NOT_POSTED")

        allocate(self.commitment, "50000.00", "RCT-FP-0002", user=self.user)
        self.commitment.status = "COMPLETED"
        self.commitment.save()
        self.proposal.refresh_from_db()
        self.assertTrue(first_premium_posted(self.proposal))
        self.assertTrue(ensure_first_premium_posted(self.proposal))

    def test_status_payload_exposes_commitment_and_allocations(self):
        allocate(self.commitment, "20000.00", "RCT-FP-0010", mode="M-PESA", user=self.user)
        self.commitment.status = "PARTIALLY_PAID"
        self.commitment.save()
        payload = first_premium_status(self.proposal)
        self.assertTrue(payload["linked"])
        self.assertFalse(payload["first_premium_posted"])
        self.assertEqual(payload["commitment"]["status"], "PARTIALLY_PAID")
        self.assertEqual(payload["commitment"]["amount_due"], "50000.00")
        self.assertEqual(payload["commitment"]["amount_paid"], "20000.00")
        self.assertEqual(payload["commitment"]["balance"], "30000.00")
        self.assertEqual(payload["commitment"]["payment_mode"], "M-PESA")
        self.assertTrue(payload["commitment"]["last_payment_date"])
        self.assertEqual(len(payload["commitment"]["allocations"]), 1)
        self.assertEqual(payload["commitment"]["allocations"][0]["receipt_reference"], "RCT-FP-0010")
        self.assertIn("Record receipt in Front Office.", payload["next_actions"])


class FirstPremiumEndpointTests(DRFTestCase):
    def setUp(self):
        seed_commitment_statuses()
        self.superuser = User.objects.create_superuser(username="fp_adm", password="Password@12345", email="fp_adm@zic.tz")
        self.proposal = make_proposal("OLP-2026-FP2")
        self.client.force_authenticate(self.superuser)
        self.base = f"/api/v1/ol-proposals/proposals/{self.proposal.pk}"

    def test_first_premium_endpoint_reports_status(self):
        commitment, _ = link_first_premium_commitment(proposal=self.proposal, actor=self.superuser, source_channel="API")
        allocate(commitment, "50000.00", "RCT-FP-EP1", mode="CASH", user=self.superuser)
        commitment.status = "COMPLETED"
        commitment.save()
        response = self.client.get(f"{self.base}/first-premium/")
        self.assertEqual(response.status_code, 200)
        data = response.data["data"]
        self.assertTrue(data["linked"])
        self.assertTrue(data["first_premium_posted"])
        self.assertEqual(data["commitment"]["commitment_number"], commitment.commitment_number)
        self.assertEqual(data["commitment"]["status"], "COMPLETED")
        self.assertEqual(data["commitment"]["balance"], "0.00")
        self.assertIn("Proceed to policy conversion", data["next_actions"][0])

    def test_detail_payload_shows_commitment_status_and_hints(self):
        link_first_premium_commitment(proposal=self.proposal, actor=self.superuser, source_channel="API")
        response = self.client.get(f"{self.base}/")
        self.assertEqual(response.status_code, 200)
        first_premium = response.data["data"]["first_premium"]
        self.assertTrue(first_premium["linked"])
        self.assertIn("commitment_number", first_premium["commitment"])
        self.assertEqual(first_premium["commitment"]["status"], "PENDING")
        self.assertTrue(any("Record receipt in Front Office" in hint for hint in first_premium["next_actions"]))


class ReceiptsSeamDocumentTests(TestCase):
    def test_seam_doc_matches_commitments_allocation_contract(self):
        with open(SEAM_DOC, encoding="utf-8") as handle:
            content = handle.read()
        self.assertIn("OLCommitmentAllocation", content)
        self.assertIn("receipt_reference", content)
        self.assertIn("PremiumReceived", content)
        self.assertIn("allocated_at", content)
        self.assertIn("payment_mode", content)