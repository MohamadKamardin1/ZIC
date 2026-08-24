from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from rest_framework.test import APITestCase

from apps.common.models import DomainEvent
from apps.front_office.receipts.models import (
    Receipt,
    ReceiptAllocation,
    ReceiptReversal,
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
from apps.system_parameters.models import ParameterGroup, SystemParameter

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
        "partner_number": f"REV{seq:04d}",
        "partner_type": "INDIVIDUAL",
        "party_type": "INDIVIDUAL",
        "first_name": "Jane",
        "surname": "Doe",
        "email": f"rev{seq}@zic.tz",
        "mobile_number": f"2557000000{seq}",
        "is_active": True,
        "status": "ACTIVE",
    }
    defaults.update(overrides)
    return Partner.objects.create(**defaults)


def make_proposal(number="OLP-2026-REV1", partner=None, premium="50000.00"):
    partner = partner or make_partner(seq=99)
    quotation = OLQuotation.objects.create(quote_number=f"Q-REV-{number[-3:]}", currency="TZS")
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


class ReceiptReversalApiTests(APITestCase):
    def setUp(self):
        call_command("seed_receipt_parameters")
        seed_commitment_statuses()
        self.admin = User.objects.create_superuser(
            username="rev_admin", password="Password@12345", email="rev_admin@zic.tz"
        )
        self.plain = User.objects.create_user(
            username="rev_plain", password="Password@12345", email="rev_plain@zic.tz"
        )
        self.client.force_authenticate(self.admin)
        self.branch = Branch.objects.create(code="DAR", name="Dar es Salaam")
        self.partner = make_partner()
        self.commitment = OLCommitment.objects.create(
            commitment_number="OLC-REV-0001",
            source_type="MANUAL",
            currency="TZS",
            due_date=date(2026, 9, 1),
            premium_amount="100000.00",
            status="PENDING",
            partner=self.partner,
            partner_name_snapshot=str(self.partner),
            source_channel="API",
        )

    def _create_and_post(self, amount="100000.00", receipt_date=date(2026, 8, 25), **overrides):
        payload = {
            "payer_name": "Jane Doe",
            "receipt_date": receipt_date.isoformat(),
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

    def _reverse(self, receipt_id, reason="Collected in error."):
        return self.client.post(f"{BASE}/{receipt_id}/reverse/", {"reason": reason}, format="json")

    def _reverse_allocation(self, receipt_id, allocation_id, reason="Wrong allocation."):
        return self.client.post(
            f"{BASE}/{receipt_id}/allocations/{allocation_id}/reverse/",
            {"reason": reason},
            format="json",
        )

    def _cancel(self, receipt_id, reason="Draft no longer required."):
        return self.client.post(f"{BASE}/{receipt_id}/cancel/", {"reason": reason}, format="json")

    # --- draft cancellation -------------------------------------------------

    def test_cancel_draft(self):
        created = self.client.post(
            f"{BASE}/",
            {
                "payer_name": "Jane Doe",
                "receipt_date": date(2026, 8, 25).isoformat(),
                "receipt_amount": "100000.00",
                "currency": "TZS",
                "branch": str(self.branch.pk),
                "partner": str(self.partner.pk),
            },
            format="json",
        ).data["data"]
        self.assertEqual(created["status"], ReceiptStatus.DRAFT)
        self.assertIsNone(created["receipt_number"])

        response = self._cancel(created["id"])
        self.assertEqual(response.status_code, 200, response.data)
        data = response.data["data"]
        self.assertEqual(data["status"], ReceiptStatus.CANCELLED)
        self.assertEqual(data["cancellation_reason"], "Draft no longer required.")

        receipt = Receipt.objects.get(pk=created["id"])
        self.assertEqual(receipt.status, ReceiptStatus.CANCELLED)
        # The draft row is retained — never hard-deleted.
        self.assertIsNone(receipt.receipt_number)
        self.assertTrue(
            DomainEvent.objects.filter(
                event_type="ReceiptCancelled", aggregate_id=created["id"]
            ).exists()
        )
        self.assertTrue(
            ReceiptStatusHistory.objects.filter(
                receipt_id=created["id"], from_status="DRAFT", to_status="CANCELLED"
            ).exists()
        )
        audit = AuditLog.objects.filter(
            entity_type="receipt", entity_id=created["id"], action_type="UPDATE"
        ).first()
        self.assertIsNotNone(audit)
        self.assertIn("cancellation_reason", audit.changed_fields)

    def test_cancel_draft_requires_reason(self):
        created = self.client.post(
            f"{BASE}/",
            {
                "payer_name": "Jane Doe",
                "receipt_date": date(2026, 8, 25).isoformat(),
                "receipt_amount": "100000.00",
                "currency": "TZS",
                "branch": str(self.branch.pk),
                "partner": str(self.partner.pk),
            },
            format="json",
        ).data["data"]
        response = self.client.post(f"{BASE}/{created['id']}/cancel/", {}, format="json")
        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("reason", response.data["field_errors"])

    def test_cancel_posted_receipt_blocked(self):
        receipt = self._create_and_post()
        response = self._cancel(receipt["id"])
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.data["error_code"], "RECEIPT_INVALID_STATUS")

    # --- full receipt reversal ----------------------------------------------

    def test_reverse_fully_allocated_receipt(self):
        receipt = self._create_and_post()
        response = self._allocate(receipt["id"], self.commitment.commitment_number, "100000.00")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["data"]["status"], ReceiptStatus.FULLY_ALLOCATED)

        original = ReceiptAllocation.objects.get(receipt_id=receipt["id"], reversal_of__isnull=True)
        self.commitment.refresh_from_db()
        self.assertEqual(self.commitment.status, "COMPLETED")
        self.assertEqual(self.commitment.amount_paid, Decimal("100000.00"))
        self.assertEqual(self.commitment.balance, Decimal("0.00"))

        reversed_response = self._reverse(receipt["id"])
        self.assertEqual(reversed_response.status_code, 200, reversed_response.data)
        data = reversed_response.data["data"]
        self.assertEqual(data["status"], ReceiptStatus.REVERSED)
        self.assertIsNotNone(data["reversed_at"])
        self.assertEqual(data["reversed_by"], self.admin.pk)

        receipt_obj = Receipt.objects.get(pk=receipt["id"])
        self.assertEqual(receipt_obj.allocated_amount, Decimal("0.00"))
        self.assertEqual(receipt_obj.unallocated_amount, Decimal("100000.00"))

        original.refresh_from_db()
        self.assertEqual(original.allocation_status, "REVERSED")
        reversal_row = ReceiptAllocation.objects.get(
            receipt_id=receipt["id"], reversal_of_id=original.pk
        )
        self.assertEqual(reversal_row.allocation_status, "REVERSED")
        self.assertEqual(reversal_row.amount, Decimal("100000.00"))

        reversal_record = ReceiptReversal.objects.get(receipt_id=receipt["id"])
        self.assertTrue(reversal_record.reversal_number.startswith("RVR-"))
        self.assertEqual(reversal_record.reason, "Collected in error.")
        self.assertEqual(reversal_record.reversed_by, self.admin)
        snapshot = reversal_record.reversed_allocations[0]
        self.assertEqual(snapshot["allocation_id"], str(original.pk))
        self.assertEqual(snapshot["reversal_allocation_id"], str(reversal_row.pk))
        self.assertIsNotNone(snapshot["ol_reversal_allocation_id"])

        self.commitment.refresh_from_db()
        self.assertEqual(self.commitment.amount_paid, Decimal("0.00"))
        self.assertEqual(self.commitment.balance, Decimal("100000.00"))
        self.assertEqual(self.commitment.status, "PENDING")

        ol_reversal = OLCommitmentAllocation.objects.get(
            commitment=self.commitment, reversal_of__isnull=False
        )
        self.assertEqual(ol_reversal.converted_amount, Decimal("100000.00"))
        self.assertTrue(
            DomainEvent.objects.filter(
                event_type="ReceiptReversed", aggregate_id=receipt["id"]
            ).exists()
        )
        self.assertTrue(
            DomainEvent.objects.filter(
                event_type="CommitmentPaymentReversed", aggregate_id=str(self.commitment.pk)
            ).exists()
        )

    def test_reverse_posted_receipt_without_allocations(self):
        receipt = self._create_and_post()
        self.assertEqual(receipt["status"], ReceiptStatus.POSTED)
        response = self._reverse(receipt["id"])
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["data"]["status"], ReceiptStatus.REVERSED)
        reversal_record = ReceiptReversal.objects.get(receipt_id=receipt["id"])
        self.assertEqual(reversal_record.reversed_allocations, [])

    def test_reverse_requires_reason(self):
        receipt = self._create_and_post()
        response = self.client.post(f"{BASE}/{receipt['id']}/reverse/", {}, format="json")
        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("reason", response.data["field_errors"])

    def test_reverse_draft_blocked(self):
        created = self.client.post(
            f"{BASE}/",
            {
                "payer_name": "Jane Doe",
                "receipt_date": date(2026, 8, 25).isoformat(),
                "receipt_amount": "100000.00",
                "currency": "TZS",
                "branch": str(self.branch.pk),
                "partner": str(self.partner.pk),
            },
            format="json",
        ).data["data"]
        response = self._reverse(created["id"])
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.data["error_code"], "RECEIPT_INVALID_STATUS")

    def test_reverse_requires_reverse_permission(self):
        receipt = self._create_and_post()
        self.client.force_authenticate(self.plain)
        response = self._reverse(receipt["id"])
        self.assertEqual(response.status_code, 403)

    # --- single allocation reversal -----------------------------------------

    def test_reverse_one_allocation_recalculates_receipt(self):
        other = OLCommitment.objects.create(
            commitment_number="OLC-REV-0002",
            source_type="MANUAL",
            currency="TZS",
            due_date=date(2026, 9, 1),
            premium_amount="60000.00",
            status="PENDING",
            partner=self.partner,
            partner_name_snapshot=str(self.partner),
            source_channel="API",
        )
        receipt = self._create_and_post()
        self.assertEqual(self._allocate(receipt["id"], self.commitment.commitment_number, "60000.00").status_code, 201)
        full = self._allocate(receipt["id"], other.commitment_number, "40000.00")
        self.assertEqual(full.status_code, 201, full.data)
        self.assertEqual(full.data["data"]["status"], ReceiptStatus.FULLY_ALLOCATED)

        target = ReceiptAllocation.objects.get(receipt_id=receipt["id"], commitment=other)
        response = self._reverse_allocation(receipt["id"], target.pk)
        self.assertEqual(response.status_code, 200, response.data)
        data = response.data["data"]
        self.assertEqual(data["status"], ReceiptStatus.PARTIALLY_ALLOCATED)
        self.assertEqual(data["allocated_amount"], "60000.00")
        self.assertEqual(data["unallocated_amount"], "40000.00")

        target.refresh_from_db()
        self.assertEqual(target.allocation_status, "REVERSED")
        reversal_row = ReceiptAllocation.objects.get(receipt_id=receipt["id"], reversal_of_id=target.pk)
        self.assertEqual(reversal_row.allocation_status, "REVERSED")
        self.assertEqual(reversal_row.amount, Decimal("40000.00"))

        other.refresh_from_db()
        self.assertEqual(other.amount_paid, Decimal("0.00"))
        self.assertEqual(other.balance, Decimal("60000.00"))
        self.assertEqual(other.status, "PENDING")

        # The commitment-side reversal row is linked to the original.
        ol_original = OLCommitmentAllocation.objects.get(commitment=other, reversal_of__isnull=True)
        self.assertEqual(ol_original.converted_amount, Decimal("40000.00"))
        ol_reversal = OLCommitmentAllocation.objects.get(commitment=other, reversal_of=ol_original)
        self.assertEqual(ol_reversal.converted_amount, Decimal("40000.00"))
        self.assertTrue(
            DomainEvent.objects.filter(
                event_type="CommitmentPaymentReversed", aggregate_id=str(other.pk)
            ).exists()
        )
        self.assertTrue(
            ReceiptStatusHistory.objects.filter(
                receipt_id=receipt["id"], from_status="FULLY_ALLOCATED", to_status="PARTIALLY_ALLOCATED"
            ).exists()
        )

    def test_reverse_one_allocation_requires_reason(self):
        receipt = self._create_and_post()
        self._allocate(receipt["id"], self.commitment.commitment_number, "100000.00")
        target = ReceiptAllocation.objects.get(receipt_id=receipt["id"], reversal_of__isnull=True)
        response = self.client.post(
            f"{BASE}/{receipt['id']}/allocations/{target.pk}/reverse/", {}, format="json"
        )
        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("reason", response.data["field_errors"])

    def test_reverse_allocation_not_found(self):
        receipt = self._create_and_post()
        import uuid

        response = self.client.post(
            f"{BASE}/{receipt['id']}/allocations/{uuid.uuid4()}/reverse/",
            {"reason": "Wrong target."},
            format="json",
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.data["error_code"], "RECEIPT_ALLOCATION_INVALID")

    # --- first premium guard -------------------------------------------------

    def test_proposal_guard_false_after_first_premium_reversal(self):
        proposal = make_proposal()
        commitment, _created = link_first_premium_commitment(proposal=proposal, actor=self.admin, source_channel="API")
        self.assertFalse(first_premium_posted(proposal))

        receipt = self._create_and_post(amount="50000.00", partner=str(proposal.partner_id))
        self._allocate(receipt["id"], commitment.commitment_number, "50000.00")

        proposal.refresh_from_db()
        self.assertTrue(first_premium_posted(proposal))

        self._reverse(receipt["id"])
        proposal = OLProposal.objects.get(pk=proposal.pk)
        commitment = OLCommitment.objects.get(pk=commitment.pk)
        self.assertEqual(commitment.amount_paid, Decimal("0.00"))
        self.assertEqual(commitment.status, "PENDING")
        self.assertFalse(first_premium_posted(proposal))

    # --- constraints ---------------------------------------------------------

    def test_already_reversed_blocked(self):
        receipt = self._create_and_post()
        self._allocate(receipt["id"], self.commitment.commitment_number, "100000.00")
        self.assertEqual(self._reverse(receipt["id"]).status_code, 200)
        second = self._reverse(receipt["id"])
        self.assertEqual(second.status_code, 409)
        self.assertEqual(second.data["error_code"], "RECEIPT_ALREADY_REVERSED")
        self.assertEqual(ReceiptReversal.objects.filter(receipt_id=receipt["id"]).count(), 1)

    def test_already_reversed_allocation_blocked(self):
        receipt = self._create_and_post()
        self._allocate(receipt["id"], self.commitment.commitment_number, "100000.00")
        target = ReceiptAllocation.objects.get(receipt_id=receipt["id"], reversal_of__isnull=True)
        self.assertEqual(self._reverse_allocation(receipt["id"], target.pk).status_code, 200)
        second = self._reverse_allocation(receipt["id"], target.pk)
        self.assertEqual(second.status_code, 409)
        self.assertEqual(second.data["error_code"], "RECEIPT_ALREADY_REVERSED")
        # History retained: one original + one reversal row, no duplicates.
        self.assertEqual(
            ReceiptAllocation.objects.filter(receipt_id=receipt["id"], reversal_of_id=target.pk).count(),
            1,
        )

    def test_reversal_locked_by_lock_period(self):
        cache.clear()
        group = ParameterGroup.objects.create(code="REV_LOCK", name="Reversal Lock")
        SystemParameter.objects.create(
            group=group,
            code="RECEIPT_REVERSAL_LOCK_DAYS",
            name="Reversal lock days",
            value_type="INTEGER",
            integer_value=1,
            is_active=True,
        )
        receipt = self._create_and_post(receipt_date=date.today() - timedelta(days=30))
        response = self._reverse(receipt["id"])
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.data["error_code"], "RECEIPT_REVERSAL_LOCKED")
        self.assertTrue(response.data["resolution_steps"])
        self.assertEqual(ReceiptReversal.objects.filter(receipt_id=receipt["id"]).count(), 0)

    def test_reversal_within_lock_period_allowed(self):
        cache.clear()
        group = ParameterGroup.objects.create(code="REV_OK", name="Reversal Ok")
        SystemParameter.objects.create(
            group=group,
            code="RECEIPT_REVERSAL_LOCK_DAYS",
            name="Reversal lock days",
            value_type="INTEGER",
            integer_value=30,
            is_active=True,
        )
        receipt = self._create_and_post(receipt_date=date.today() - timedelta(days=2))
        response = self._reverse(receipt["id"])
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["data"]["status"], ReceiptStatus.REVERSED)

    # --- audit / events ------------------------------------------------------

    def test_reversal_audit_captures_state_actor_and_linked_references(self):
        receipt = self._create_and_post()
        self._allocate(receipt["id"], self.commitment.commitment_number, "100000.00")
        self._reverse(receipt["id"])

        receipt_id = receipt["id"]
        reversal_record = ReceiptReversal.objects.get(receipt_id=receipt_id)
        audit = AuditLog.objects.filter(
            entity_type="receiptreversal", entity_id=reversal_record.pk, action_type="CREATE"
        ).first()
        self.assertIsNotNone(audit, "ReceiptReversal must be audited on create")
        self.assertEqual(audit.user, self.admin)
        self.assertEqual(audit.after_state["reason"], "Collected in error.")
        self.assertTrue(audit.after_state["reversal_number"].startswith("RVR-"))
        self.assertIsInstance(audit.after_state["reversed_allocations"], list)
        self.assertEqual(len(audit.after_state["reversed_allocations"]), 1)

        original = ReceiptAllocation.objects.get(receipt_id=receipt_id, reversal_of__isnull=True)
        original_audit = AuditLog.objects.filter(
            entity_type="receiptallocation", entity_id=original.pk, action_type="UPDATE"
        ).first()
        self.assertIsNotNone(original_audit)
        self.assertEqual(original_audit.before_state["allocation_status"], "ACTIVE")
        self.assertEqual(original_audit.after_state["allocation_status"], "REVERSED")

        receipt_audit = AuditLog.objects.filter(
            entity_type="receipt", entity_id=receipt_id, action_type="UPDATE"
        ).first()
        self.assertIsNotNone(receipt_audit)
        self.assertIn("status", receipt_audit.changed_fields)
        self.assertEqual(receipt_audit.after_state["status"], "REVERSED")

        commitment_audit = AuditLog.objects.filter(
            app_label="ol_commitments", object_id=str(self.commitment.pk), action="UPDATE"
        ).first()
        self.assertIsNotNone(commitment_audit)
        self.assertIn("amount_paid", commitment_audit.changed_fields)

        ol_reversal = OLCommitmentAllocation.objects.get(
            commitment=self.commitment, reversal_of__isnull=False
        )
        ol_reversal_audit = AuditLog.objects.filter(
            app_label="ol_commitments", object_id=str(ol_reversal.pk), action="CREATE"
        ).first()
        self.assertIsNotNone(ol_reversal_audit)

        # The ReceiptReversal snapshot carries the linked commitment allocation
        # reversal reference (audit trail requirement).
        snapshot_entry = reversal_record.reversed_allocations[0]
        self.assertEqual(snapshot_entry["ol_reversal_allocation_id"], str(ol_reversal.pk))
