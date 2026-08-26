from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management import call_command
from rest_framework.test import APITestCase

from apps.common.models import DomainEvent
from apps.front_office.receipts.models import (
    Receipt,
    ReceiptAllocation,
    ReceiptStatus,
    ReceiptStatusHistory,
)
from apps.governance.models import AuditLog
from apps.ol_commitments.models import OLCommitment, OLCommitmentAllocation
from apps.ol_parameters.models import OLCommitmentStatus
from apps.ol_proposals.models import OLProposal
from apps.ol_proposals.services.first_premium_service import (
    first_premium_posted,
    link_first_premium_commitment,
)
from apps.ol_quotations.models import OLQuotation, OLQuotationVersion
from apps.partner_onboarding.models import Branch
from apps.partners.models import Partner

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
            defaults={"name": name, "applies_to": "COMMITMENT", "display_order": order, "is_terminal": terminal, "is_active": True},
        )


def make_partner(seq=1, **overrides):
    defaults = {
        "partner_number": f"ALLOC{seq:04d}",
        "partner_type": "INDIVIDUAL",
        "party_type": "INDIVIDUAL",
        "first_name": "Jane",
        "surname": "Doe",
        "email": f"alloc{seq}@zic.tz",
        "mobile_number": f"2557000000{seq}",
        "is_active": True,
        "status": "ACTIVE",
    }
    defaults.update(overrides)
    return Partner.objects.create(**defaults)


def make_proposal(number="OLP-2026-ALLOC1", partner=None, premium="50000.00"):
    partner = partner or make_partner(seq=99)
    quotation = OLQuotation.objects.create(quote_number=f"Q-ALLOC-{number[-3:]}", currency="TZS")
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
        financial_summary_snapshot={"total_premium": premium},
    )
    proposal.save()
    return proposal


class ReceiptAllocationApiTests(APITestCase):
    def setUp(self):
        call_command("seed_receipt_parameters")
        seed_commitment_statuses()
        self.admin = User.objects.create_superuser(
            username="alloc_admin", password="Password@12345", email="alloc_admin@zic.tz"
        )
        self.plain = User.objects.create_user(
            username="alloc_plain", password="Password@12345", email="alloc_plain@zic.tz"
        )
        self.client.force_authenticate(self.admin)
        self.branch = Branch.objects.create(code="DAR", name="Dar es Salaam")
        self.partner = make_partner()
        self.commitment = OLCommitment.objects.create(
            commitment_number="OLC-ALLOC-0001",
            source_type="MANUAL",
            currency="TZS",
            due_date=date(2026, 9, 1),
            premium_amount="100000.00",
            status="PENDING",
            partner=self.partner,
            partner_name_snapshot=str(self.partner),
            source_channel="API",
        )

    def _create_and_post(self, amount="100000.00", **overrides):
        payload = {
            "payer_name": "Jane Doe",
            "receipt_date": date(2026, 8, 24).isoformat(),
            "receipt_amount": amount,
            "currency": "TZS",
            "branch": str(self.branch.pk),
            "partner": str(self.partner.pk),
        }
        payload.update(overrides)
        created = self.client.post(f"{BASE}/", payload, format="json").data["data"]
        posted = self.client.post(f"{BASE}/{created['id']}/post/", {"reason": "Money confirmed."}, format="json")
        self.assertEqual(posted.status_code, 200, posted.data)
        return posted.data["data"]

    def _allocate(self, receipt_id, target_id, amount, **overrides):
        payload = {
            "target_type": "OL_COMMITMENT",
            "target_id": target_id,
            "amount": str(amount),
        }
        payload.update(overrides)
        return self.client.post(f"{BASE}/{receipt_id}/allocate/", payload, format="json")

    def test_allocate_full_amount_to_one_commitment(self):
        receipt = self._create_and_post()
        response = self._allocate(receipt["id"], self.commitment.commitment_number, "100000.00")
        self.assertEqual(response.status_code, 201, response.data)
        data = response.data["data"]
        self.assertEqual(data["status"], ReceiptStatus.FULLY_ALLOCATED)
        self.assertEqual(data["allocated_amount"], "100000.00")
        self.assertEqual(data["unallocated_amount"], "0.00")

        allocation = ReceiptAllocation.objects.get(receipt_id=receipt["id"])
        self.assertEqual(allocation.commitment, self.commitment)
        self.assertIsNotNone(allocation.ol_commitment_allocation)
        self.assertEqual(allocation.target_id, self.commitment.commitment_number)
        self.assertEqual(allocation.amount, Decimal("100000.00"))

        commitment = OLCommitment.objects.get(pk=self.commitment.pk)
        self.assertEqual(commitment.status, "COMPLETED")
        self.assertEqual(commitment.amount_paid, Decimal("100000.00"))
        self.assertEqual(commitment.balance, Decimal("0.00"))

    def test_partial_allocation_marks_receipt_partially_allocated(self):
        receipt = self._create_and_post()
        response = self._allocate(receipt["id"], self.commitment.commitment_number, "40000.00")
        self.assertEqual(response.status_code, 201, response.data)
        data = response.data["data"]
        self.assertEqual(data["status"], ReceiptStatus.PARTIALLY_ALLOCATED)
        self.assertEqual(data["allocated_amount"], "40000.00")
        self.assertEqual(data["unallocated_amount"], "60000.00")

        commitment = OLCommitment.objects.get(pk=self.commitment.pk)
        self.assertEqual(commitment.status, "PARTIALLY_PAID")
        self.assertEqual(commitment.amount_paid, Decimal("40000.00"))
        self.assertEqual(commitment.balance, Decimal("60000.00"))

    def test_overallocation_blocked_on_receipt_side(self):
        receipt = self._create_and_post(amount="100000.00")
        response = self._allocate(receipt["id"], self.commitment.commitment_number, "150000.00")
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.data["error_code"], "RECEIPT_OVERALLOCATION")
        self.assertIn("amount", response.data["field_errors"])

    def test_overallocation_blocked_on_commitment_side(self):
        small = OLCommitment.objects.create(
            commitment_number="OLC-ALLOC-SMALL",
            source_type="MANUAL",
            currency="TZS",
            due_date=date(2026, 9, 1),
            premium_amount="40000.00",
            status="PENDING",
            partner=self.partner,
            partner_name_snapshot=str(self.partner),
            source_channel="API",
        )
        receipt = self._create_and_post(amount="100000.00")
        response = self._allocate(receipt["id"], small.commitment_number, "100000.00")
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.data["error_code"], "RECEIPT_OVERALLOCATION")

    def test_allocation_updates_commitment_balance_and_writes_ol_allocation(self):
        receipt = self._create_and_post()
        self._allocate(receipt["id"], self.commitment.commitment_number, "60000.00")
        commitment = OLCommitment.objects.get(pk=self.commitment.pk)
        ol_allocation = OLCommitmentAllocation.objects.get(commitment=commitment)
        self.assertEqual(ol_allocation.amount, Decimal("60000.00"))
        self.assertEqual(ol_allocation.receipt_reference, Receipt.objects.get(pk=receipt["id"]).receipt_number)
        self.assertEqual(ol_allocation.currency, "TZS")
        self.assertEqual(ol_allocation.payment_mode, "CASH")
        self.assertEqual(commitment.balance, Decimal("40000.00"))

    def test_allocation_is_idempotent_per_commitment(self):
        receipt = self._create_and_post()
        first = self._allocate(receipt["id"], self.commitment.commitment_number, "100000.00")
        second = self._allocate(receipt["id"], self.commitment.commitment_number, "100000.00")
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.data["data"]["id"], second.data["data"]["id"])
        self.assertEqual(ReceiptAllocation.objects.filter(receipt_id=receipt["id"]).count(), 1)
        self.assertEqual(
            OLCommitment.objects.get(pk=self.commitment.pk).amount_paid,
            Decimal("100000.00"),
        )

    def test_currency_mismatch_blocked(self):
        usd = OLCommitment.objects.create(
            commitment_number="OLC-ALLOC-USD",
            source_type="MANUAL",
            currency="USD",
            due_date=date(2026, 9, 1),
            premium_amount="1000.00",
            status="PENDING",
            partner=self.partner,
            partner_name_snapshot=str(self.partner),
            source_channel="API",
        )
        receipt = self._create_and_post()
        response = self._allocate(receipt["id"], usd.commitment_number, "1000.00")
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.data["error_code"], "RECEIPT_CURRENCY_MISMATCH")

    def test_allocate_draft_receipt_blocked(self):
        created = self.client.post(
            f"{BASE}/",
            {
                "payer_name": "Jane Doe",
                "receipt_date": date(2026, 8, 24).isoformat(),
                "receipt_amount": "100000.00",
                "currency": "TZS",
                "branch": str(self.branch.pk),
                "partner": str(self.partner.pk),
            },
            format="json",
        ).data["data"]
        response = self._allocate(created["id"], self.commitment.commitment_number, "100000.00")
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.data["error_code"], "RECEIPT_INVALID_STATUS")

    def test_allocate_requires_allocate_permission(self):
        receipt = self._create_and_post()
        self.client.force_authenticate(self.plain)
        response = self._allocate(receipt["id"], self.commitment.commitment_number, "100000.00")
        self.assertEqual(response.status_code, 403)

    def test_allocation_options_lists_open_commitments_only(self):
        settled = OLCommitment.objects.create(
            commitment_number="OLC-ALLOC-DONE",
            source_type="MANUAL",
            currency="TZS",
            due_date=date(2026, 9, 1),
            premium_amount="100000.00",
            amount_paid="100000.00",
            status="COMPLETED",
            partner=self.partner,
            partner_name_snapshot=str(self.partner),
            source_channel="API",
        )
        settled.recompute_balance()
        settled.save()
        receipt = self._create_and_post()
        response = self.client.get(f"{BASE}/{receipt['id']}/allocation-options/")
        self.assertEqual(response.status_code, 200)
        commitments = response.data["data"]["commitments"]
        numbers = {item["commitment_number"] for item in commitments}
        self.assertIn(self.commitment.commitment_number, numbers)
        self.assertNotIn("OLC-ALLOC-DONE", numbers)

        option = next(item for item in commitments if item["commitment_number"] == self.commitment.commitment_number)
        self.assertEqual(option["source_type"], "MANUAL")
        self.assertEqual(option["balance"], "100000.00")
        self.assertEqual(option["amount_due"], "100000.00")
        self.assertEqual(option["amount_paid"], "0.00")
        self.assertEqual(option["currency"], "TZS")
        self.assertEqual(option["status"], "PENDING")
        self.assertEqual(option["due_date"], "2026-09-01")
        self.assertTrue(option["id"])

    def test_auto_allocate_oldest_first_same_currency(self):
        # A dedicated partner keeps setUp's self.commitment out of the open set.
        auto_partner = make_partner(seq=2)
        older = OLCommitment.objects.create(
            commitment_number="OLC-ALLOC-OLDER",
            source_type="MANUAL",
            currency="TZS",
            due_date=date(2026, 7, 15),
            premium_amount="60000.00",
            status="PENDING",
            partner=auto_partner,
            partner_name_snapshot=str(auto_partner),
            source_channel="API",
        )
        newer = OLCommitment.objects.create(
            commitment_number="OLC-ALLOC-NEWER",
            source_type="MANUAL",
            currency="TZS",
            due_date=date(2026, 10, 1),
            premium_amount="40000.00",
            status="PENDING",
            partner=auto_partner,
            partner_name_snapshot=str(auto_partner),
            source_channel="API",
        )
        receipt = self._create_and_post(amount="80000.00", partner=str(auto_partner.pk))
        response = self.client.post(f"{BASE}/{receipt['id']}/auto-allocate/", {}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        data = response.data["data"]
        self.assertEqual(data["receipt_status"], ReceiptStatus.FULLY_ALLOCATED)
        self.assertEqual(data["total_allocated"], "80000.00")
        self.assertEqual(data["remaining_unallocated"], "0.00")
        self.assertEqual(data["commitments_count"], 2)
        self.assertTrue(data["exhausted"])

        order = [item["commitment_number"] for item in data["allocations"]]
        self.assertEqual(order, [older.commitment_number, newer.commitment_number])
        self.assertEqual(data["allocations"][0]["amount"], "60000.00")
        self.assertEqual(data["allocations"][0]["balance_before"], "60000.00")
        self.assertEqual(data["allocations"][0]["balance_after"], "0.00")
        self.assertEqual(data["allocations"][0]["status"], "COMPLETED")
        self.assertEqual(data["allocations"][1]["amount"], "20000.00")
        self.assertEqual(data["allocations"][1]["balance_after"], "20000.00")

        older.refresh_from_db()
        newer.refresh_from_db()
        self.assertEqual(older.status, "COMPLETED")
        self.assertEqual(older.balance, Decimal("0.00"))
        self.assertEqual(newer.status, "PARTIALLY_PAID")
        self.assertEqual(newer.balance, Decimal("20000.00"))

    def test_first_premium_completion_unlocks_proposal_guard(self):
        proposal = make_proposal()
        commitment, _created = link_first_premium_commitment(proposal=proposal, actor=self.admin, source_channel="API")
        self.assertEqual(commitment.installment_number, 1)
        self.assertEqual(commitment.source_type, "PROPOSAL")
        self.assertFalse(first_premium_posted(proposal))

        receipt = self._create_and_post(amount="50000.00", partner=str(proposal.partner_id))
        response = self._allocate(receipt["id"], commitment.commitment_number, "50000.00")
        self.assertEqual(response.status_code, 201, response.data)

        commitment.refresh_from_db()
        self.assertEqual(commitment.status, "COMPLETED")
        self.assertEqual(commitment.balance, Decimal("0.00"))
        self.assertTrue(first_premium_posted(proposal))

        premium_event = DomainEvent.objects.get(
            event_type="PremiumReceived", aggregate_id=str(commitment.pk)
        )
        self.assertEqual(premium_event.payload["commitment_number"], commitment.commitment_number)
        self.assertEqual(premium_event.payload["proposal_number"], proposal.proposal_number)
        self.assertEqual(premium_event.payload["amount"], "50000.00")
        self.assertEqual(premium_event.payload["to_status"], "COMPLETED")

        first_event = DomainEvent.objects.get(
            event_type="FirstPremiumReceived", aggregate_id=str(receipt["id"])
        )
        self.assertEqual(first_event.payload["commitment_number"], commitment.commitment_number)
        self.assertEqual(first_event.payload["proposal_number"], proposal.proposal_number)
        self.assertEqual(first_event.payload["receipt_reference"], Receipt.objects.get(pk=receipt["id"]).receipt_number)
        self.assertEqual(first_event.payload["amount"], "50000.00")

    def test_allocation_emits_receipt_events_and_audits_both_sides(self):
        receipt = self._create_and_post()
        self._allocate(receipt["id"], self.commitment.commitment_number, "50000.00")

        receipt_id = receipt["id"]
        self.assertTrue(
            DomainEvent.objects.filter(event_type="ReceiptAllocated", aggregate_id=receipt_id).exists()
        )
        self.assertTrue(
            DomainEvent.objects.filter(event_type="PremiumReceived", aggregate_id=str(self.commitment.pk)).exists()
        )
        self.assertTrue(
            DomainEvent.objects.filter(
                event_type="CommitmentPaymentAllocated", aggregate_id=str(self.commitment.pk)
            ).exists()
        )

        receipt_audit = AuditLog.objects.filter(
            entity_type="receipt", entity_id=receipt_id, action_type="UPDATE"
        ).first()
        self.assertIsNotNone(receipt_audit, "allocation must write a receipt UPDATE audit row")
        self.assertIn("allocated_amount", receipt_audit.changed_fields)
        self.assertIn("status", receipt_audit.changed_fields)

        commitment_audit = AuditLog.objects.filter(
            app_label="ol_commitments", object_id=str(self.commitment.pk), action="UPDATE"
        ).first()
        self.assertIsNotNone(commitment_audit, "allocation must write a commitment UPDATE audit row")
        self.assertIn("amount_paid", commitment_audit.changed_fields)

        allocation_audit = AuditLog.objects.filter(
            entity_type="receiptallocation", entity_id=ReceiptAllocation.objects.get(receipt_id=receipt_id).pk
        ).first()
        self.assertIsNotNone(allocation_audit, "ReceiptAllocation must be audited")

        self.assertTrue(
            ReceiptStatusHistory.objects.filter(receipt_id=receipt_id, to_status=ReceiptStatus.PARTIALLY_ALLOCATED).exists()
        )
