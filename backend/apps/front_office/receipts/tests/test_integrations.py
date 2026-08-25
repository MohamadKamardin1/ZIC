"""Prompt 10 — integration tests across proposals, commitments, dashboard,
reporting, portal, notifications, and the ERP/GL outbox seam."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.common.models import DomainEvent
from apps.front_office.receipts.models import ReceiptNotificationLog
from apps.ol_commitments.models import OLCommitment, OLCommitmentAllocation
from apps.ol_parameters.models import OLCommitmentStatus, OLParameterTableRegistry
from apps.ol_proposals.models import OLProposal
from apps.ol_proposals.services.first_premium_service import (
    first_premium_posted,
    first_premium_status,
    link_first_premium_commitment,
)
from apps.ol_quotations.models import OLQuotation, OLQuotationVersion
from apps.partner_onboarding.models import Branch
from apps.partners.models import Partner, UserPartnerLink
from apps.users.models import ReportCategory

User = get_user_model()

BASE = "/api/v1/front-office/receipts"


def seed_commitment_statuses():
    for code, name, order, terminal in (
        ("PENDING", "Pending", 10, False),
        ("PARTIALLY_PAID", "Partially paid", 20, False),
        ("COMPLETED", "Completed", 30, True),
    ):
        OLCommitmentStatus.objects.update_or_create(
            code=code,
            defaults={
                "name": name,
                "applies_to": "COMMITMENT",
                "display_order": order,
                "is_terminal": terminal,
                "is_active": True,
            },
        )


def make_partner(seq=1, **overrides):
    defaults = {
        "partner_number": f"INT{seq:04d}",
        "partner_type": "INDIVIDUAL",
        "party_type": "INDIVIDUAL",
        "first_name": "Jane",
        "surname": "Doe",
        "email": f"int{seq}@zic.tz",
        "mobile_number": f"2557000000{seq}",
        "is_active": True,
        "status": "ACTIVE",
    }
    defaults.update(overrides)
    return Partner.objects.create(**defaults)


def make_proposal(number="OLP-2026-INT1", partner=None, premium="50000.00"):
    partner = partner or make_partner(seq=99)
    quotation = OLQuotation.objects.create(quote_number=f"Q-INT-{number[-3:]}", currency="TZS")
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
        expiry_date=timezone.localdate() + timedelta(days=30),
        payment_ready=True,
        financial_summary_snapshot={"total_premium": premium},
    )
    proposal.save()
    return proposal


class ReceiptIntegrationTests(APITestCase):
    def setUp(self):
        call_command("seed_receipt_parameters")
        seed_commitment_statuses()
        self.admin = User.objects.create_superuser(
            username="int_admin", password="Password@12345", email="int_admin@zic.tz"
        )
        self.client.force_authenticate(self.admin)
        self.branch = Branch.objects.create(code="DAR", name="Dar es Salaam")
        self.partner = make_partner()

    def _create_and_post(self, amount="50000.00", receipt_date=None, partner=None, **overrides):
        payload = {
            "payer_name": "Jane Doe",
            "receipt_date": (receipt_date or timezone.localdate()).isoformat(),
            "receipt_amount": amount,
            "currency": "TZS",
            "branch": str(self.branch.pk),
            "partner": str((partner or self.partner).pk),
        }
        payload.update(overrides)
        created = self.client.post(f"{BASE}/", payload, format="json")
        self.assertEqual(created.status_code, 201, created.data)
        posted = self.client.post(f"{BASE}/{created.data['data']['id']}/post/", {"reason": "Money confirmed."}, format="json")
        self.assertEqual(posted.status_code, 200, posted.data)
        return posted.data["data"]

    def _allocate(self, receipt_id, target_id, amount):
        response = self.client.post(
            f"{BASE}/{receipt_id}/allocate/",
            {"target_type": "OL_COMMITMENT", "target_id": target_id, "amount": str(amount)},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        return response

    def _link_and_allocate(self, proposal, receipt):
        commitment, created = link_first_premium_commitment(proposal=proposal, actor=self.admin, source_channel="API")
        self.assertTrue(created)
        self._allocate(receipt["id"], commitment.commitment_number, receipt["receipt_amount"])
        return commitment

    # Scope 1 — OL Proposals: first premium status reflects receipt allocations.
    def test_proposal_first_premium_status_reflects_receipt(self):
        proposal = make_proposal(number="OLP-2026-INT1", partner=self.partner, premium="50000.00")
        receipt = self._create_and_post(
            amount="50000.00",
            source_module="OL_PROPOSAL",
            source_reference_type="PROPOSAL",
            source_reference_id=proposal.proposal_number,
        )
        commitment = self._link_and_allocate(proposal, receipt)
        proposal.refresh_from_db()

        self.assertTrue(first_premium_posted(proposal))
        status_payload = first_premium_status(proposal)
        self.assertTrue(status_payload["first_premium_posted"])
        self.assertEqual(status_payload["commitment"]["status"], "COMPLETED")
        self.assertEqual(status_payload["commitment"]["balance"], "0.00")
        self.assertEqual(
            status_payload["commitment"]["commitment_number"], commitment.commitment_number
        )
        self.assertTrue(
            any(
                allocation["receipt_reference"] == receipt["receipt_number"]
                for allocation in status_payload["commitment"]["allocations"]
            )
        )

        endpoint = self.client.get(f"/api/v1/ol-proposals/proposals/{proposal.pk}/first-premium/")
        self.assertEqual(endpoint.status_code, 200)
        data = endpoint.data["data"]
        self.assertTrue(data["first_premium_posted"])
        self.assertEqual(data["commitment"]["status"], "COMPLETED")
        self.assertEqual(data["commitment"]["balance"], "0.00")

        detail = self.client.get(f"/api/v1/ol-proposals/proposals/{proposal.pk}/")
        self.assertEqual(detail.status_code, 200)
        receipts = detail.data["data"]["receipts"]
        self.assertEqual(len(receipts), 1)
        self.assertEqual(receipts[0]["receipt_number"], receipt["receipt_number"])
        self.assertEqual(receipts[0]["amount"], "50000.00")
        self.assertEqual(receipts[0]["status"], "FULLY_ALLOCATED")

    # Scope 2 — OL Commitments: detail shows the linked receipt allocation.
    def test_commitment_detail_includes_receipt_references(self):
        proposal = make_proposal(number="OLP-2026-INT2", partner=self.partner, premium="50000.00")
        receipt = self._create_and_post(amount="50000.00")
        commitment = self._link_and_allocate(proposal, receipt)

        ol_allocation = OLCommitmentAllocation.objects.filter(commitment=commitment).first()
        self.assertIsNotNone(ol_allocation)
        self.assertEqual(ol_allocation.receipt_reference, receipt["receipt_number"])

        detail = self.client.get(f"/api/v1/ol-commitments/commitments/{commitment.pk}/")
        self.assertEqual(detail.status_code, 200, detail.data)
        allocations = detail.data["data"]["allocations"]
        self.assertTrue(
            any(
                allocation["receipt_reference"] == receipt["receipt_number"]
                for allocation in allocations
            )
        )

        event = DomainEvent.objects.filter(
            event_type="CommitmentPaymentAllocated",
            aggregate_id=str(commitment.pk),
        ).order_by("-occurred_at").first()
        self.assertIsNotNone(event)
        self.assertEqual(event.payload.get("receipt_reference"), receipt["receipt_number"])

    # Scope 5 — Portal: partner-scoped read-only receipts, no cross-partner leak.
    def test_portal_scoping_denies_other_partners(self):
        partner_b = make_partner(seq=2, email="int_b@zic.tz")
        receipt_a = self._create_and_post(amount="100000.00", partner=self.partner)
        receipt_b = self._create_and_post(amount="20000.00", partner=partner_b)

        portal_user = User.objects.create_user(
            username="portal_user", password="Password@12345", email="portal_user@zic.tz"
        )
        UserPartnerLink.objects.create(
            user=portal_user, partner=self.partner, link_status="ACTIVE", is_primary=True
        )
        self.client.force_authenticate(portal_user)

        listing = self.client.get(f"{BASE}/portal/")
        self.assertEqual(listing.status_code, 200)
        results = listing.data["data"]["results"]
        self.assertEqual(listing.data["data"]["count"], 1)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["receipt_number"], receipt_a["receipt_number"])
        for forbidden in ("allowed_actions", "audit_timeline", "created_by_display"):
            self.assertNotIn(forbidden, results[0])

        own = self.client.get(f"{BASE}/portal/{receipt_a['id']}/")
        self.assertEqual(own.status_code, 200)
        self.assertEqual(own.data["data"]["receipt_number"], receipt_a["receipt_number"])
        self.assertNotIn("allowed_actions", own.data["data"])
        self.assertNotIn("audit_timeline", own.data["data"])

        foreign = self.client.get(f"{BASE}/portal/{receipt_b['id']}/")
        self.assertEqual(foreign.status_code, 404)
        self.assertEqual(foreign.data["error_code"], "RECEIPT_NOT_FOUND")

    # Scope 3 — Dashboard: front-office KPI hook math.
    def test_dashboard_kpi_math(self):
        today = timezone.localdate()
        commitment = OLCommitment.objects.create(
            commitment_number="OLC-INT-KPI-0001",
            source_type="MANUAL",
            currency="TZS",
            due_date=today + timedelta(days=10),
            premium_amount="50000.00",
            status="PENDING",
            partner=self.partner,
            partner_name_snapshot=str(self.partner),
            source_channel="API",
        )
        # A: today, posted, unallocated.
        _receipt_a = self._create_and_post(amount="100000.00", receipt_date=today)
        # B: today, posted, fully allocated.
        receipt_b = self._create_and_post(amount="50000.00", receipt_date=today)
        self._allocate(receipt_b["id"], commitment.commitment_number, "50000.00")
        # C: yesterday, posted, then reversed.
        receipt_c = self._create_and_post(amount="20000.00", receipt_date=today - timedelta(days=1))
        reversed_response = self.client.post(
            f"{BASE}/{receipt_c['id']}/reverse/", {"reason": "Duplicate payment."}, format="json"
        )
        self.assertEqual(reversed_response.status_code, 200, reversed_response.data)

        response = self.client.get(f"{BASE}/kpis/")
        self.assertEqual(response.status_code, 200)
        kpis = response.data["data"]
        self.assertEqual(kpis["receipts_today"], 2)
        self.assertEqual(kpis["amount_received_today"], "150000.00")
        self.assertEqual(kpis["unallocated_receipts"], 1)
        self.assertEqual(kpis["reversed_receipts"], 1)
        self.assertEqual(kpis["total_received_period"], "170000.00")
        self.assertEqual(kpis["total_unallocated"], "100000.00")
        self.assertEqual(kpis["reversed_amount"], "20000.00")
        self.assertEqual(kpis["receipt_count"], 3)

    # Scope 4 — Reporting: category + dataset registry registered, field contract.
    def test_report_dataset_registered(self):
        response = self.client.get(f"{BASE}/reporting/dataset/")
        self.assertEqual(response.status_code, 200)
        contract = response.data["data"]
        self.assertEqual(contract["category"]["code"], "FRONT_OFFICE_RECEIPTS")
        self.assertEqual(contract["category"]["name"], "Front Office Receipts")
        field_names = [field["field"] for field in contract["fields"]]
        self.assertEqual(
            field_names,
            [
                "receipt_number",
                "date",
                "branch",
                "payer",
                "payment_mode",
                "currency",
                "amount",
                "allocated",
                "unallocated",
                "status",
                "cashier",
                "source_module",
            ],
        )

        self.assertTrue(
            ReportCategory.objects.filter(code="FRONT_OFFICE_RECEIPTS", is_active=True).exists()
        )
        registry = OLParameterTableRegistry.objects.filter(slug="front-office-receipts-report").first()
        self.assertIsNotNone(registry)
        self.assertEqual(registry.parameter_group, "REPORT")
        self.assertEqual(registry.permission_code, "front_office.receipts.view")

    # Scope 7 — ERP/GL seam: outbox payloads on posting and reversal.
    def test_gl_outbox_events_emitted_on_post_and_reverse(self):
        receipt = self._create_and_post(amount="30000.00")
        posting = DomainEvent.objects.filter(
            event_type="GLReceiptPosting",
            aggregate_type="Receipt",
            aggregate_id=receipt["id"],
        ).first()
        self.assertIsNotNone(posting)
        self.assertEqual(posting.payload["receipt_number"], receipt["receipt_number"])
        self.assertEqual(posting.payload["amount"], "30000.00")
        self.assertEqual(posting.payload["status"], "POSTED")
        self.assertEqual(posting.payload["mapping"]["dr"], "BANK_OR_CASH")
        self.assertEqual(posting.payload["mapping"]["cr"], "PREMIUM_SUSPENSE")

        reversed_response = self.client.post(
            f"{BASE}/{receipt['id']}/reverse/", {"reason": "Wrong account."}, format="json"
        )
        self.assertEqual(reversed_response.status_code, 200, reversed_response.data)
        reversal = DomainEvent.objects.filter(
            event_type="GLReceiptReversal",
            aggregate_type="Receipt",
            aggregate_id=receipt["id"],
        ).order_by("-occurred_at").first()
        self.assertIsNotNone(reversal)
        self.assertEqual(reversal.payload["status"], "REVERSED")
        self.assertEqual(reversal.payload["mapping"]["dr"], "PREMIUM_SUSPENSE")
        self.assertEqual(reversal.payload["mapping"]["cr"], "BANK_OR_CASH")
        self.assertTrue(reversal.payload["reversed_at"])

    # Scope 6 — Notifications: ReceiptPosted, FirstPremiumReceived, ReceiptReversed.
    def test_receipt_notifications_logged(self):
        proposal = make_proposal(number="OLP-2026-INT3", partner=self.partner, premium="50000.00")
        receipt = self._create_and_post(amount="50000.00")
        self.assertTrue(
            ReceiptNotificationLog.objects.filter(
                receipt_id=receipt["id"], event_type="ReceiptPosted"
            ).exists()
        )

        commitment = self._link_and_allocate(proposal, receipt)
        self.assertTrue(
            ReceiptNotificationLog.objects.filter(
                receipt_id=receipt["id"], event_type="FirstPremiumReceived"
            ).exists()
        )

        reversed_response = self.client.post(
            f"{BASE}/{receipt['id']}/reverse/", {"reason": "Client double paid."}, format="json"
        )
        self.assertEqual(reversed_response.status_code, 200, reversed_response.data)
        self.assertTrue(
            ReceiptNotificationLog.objects.filter(
                receipt_id=receipt["id"], event_type="ReceiptReversed"
            ).exists()
        )

        first_premium_log = ReceiptNotificationLog.objects.filter(
            receipt_id=receipt["id"], event_type="FirstPremiumReceived"
        ).first()
        self.assertEqual(
            first_premium_log.payload.get("proposal_number"), proposal.proposal_number
        )
        self.assertEqual(
            first_premium_log.payload.get("commitment_number"), commitment.commitment_number
        )
