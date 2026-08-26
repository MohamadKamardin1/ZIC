from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from apps.common.models import DomainEvent
from apps.front_office.receipts import events as receipt_events
from apps.front_office.receipts.models import ReceiptStatus, ReceiptStatusHistory
from apps.front_office.receipts.services.receipt_service import create_draft, update_draft
from apps.governance.models import AuditLog

User = get_user_model()


class ReceiptEventTests(TestCase):
    def setUp(self):
        call_command("seed_receipt_parameters")
        self.user = User.objects.create_user(
            username="receipt_eventer", password="Password@12345", email="receipt_eventer@zic.tz"
        )

    def test_create_draft_emits_receipt_created_event(self):
        receipt, created = create_draft(
            actor=self.user,
            payer_name="Jane Doe",
            receipt_date=date(2026, 8, 24),
            receipt_amount=Decimal("100000.00"),
        )
        self.assertTrue(created)
        event = DomainEvent.objects.get(event_type="ReceiptCreated", aggregate_id=str(receipt.pk))
        self.assertEqual(event.aggregate_type, "Receipt")
        self.assertEqual(event.payload["receipt_number"], receipt.receipt_number)
        self.assertEqual(event.payload["amount"], "100000.00")
        self.assertEqual(event.payload["to_status"], "DRAFT")
        self.assertEqual(event.payload["actor_id"], str(self.user.pk))

    def test_event_type_constants_exposed(self):
        self.assertEqual(receipt_events.AGGREGATE_TYPE, "Receipt")
        self.assertEqual(
            set(receipt_events.EVENT_TYPES),
            {
                "ReceiptCreated",
                "ReceiptPosted",
                "ReceiptAllocated",
                "ReceiptFullyAllocated",
                "ReceiptReversed",
                "ReceiptCancelled",
                "ReceiptPrintGenerated",
                "PremiumReceived",
                "FirstPremiumReceived",
            },
        )

    def test_emit_helpers_write_durable_outbox(self):
        receipt, _ = create_draft(actor=self.user, payer_name="Jane Doe", receipt_amount=Decimal("50000.00"))
        receipt_events.emit_posted(receipt, actor=self.user, from_status="DRAFT", reason="Money confirmed.")
        event = DomainEvent.objects.filter(event_type="ReceiptPosted", aggregate_id=str(receipt.pk)).first()
        self.assertIsNotNone(event)
        self.assertEqual(event.payload["from_status"], "DRAFT")

    def test_idempotency_key_returns_existing_receipt(self):
        first, created_first = create_draft(
            actor=self.user,
            payer_name="Jane Doe",
            idempotency_key="idem-1",
            receipt_amount=Decimal("100000.00"),
        )
        second, created_second = create_draft(
            actor=self.user,
            payer_name="Jane Doe",
            idempotency_key="idem-1",
            receipt_amount=Decimal("100000.00"),
        )
        self.assertTrue(created_first)
        self.assertFalse(created_second)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(DomainEvent.objects.filter(event_type="ReceiptCreated", aggregate_id=str(first.pk)).count(), 1)


class ReceiptAuditTests(TestCase):
    def setUp(self):
        call_command("seed_receipt_parameters")
        self.user = User.objects.create_user(
            username="receipt_auditor", password="Password@12345", email="receipt_auditor@zic.tz"
        )

    def _audit_rows(self, receipt):
        return AuditLog.objects.filter(entity_type="receipt", entity_id=receipt.pk).order_by("timestamp")

    def test_create_draft_writes_create_audit_row(self):
        receipt, _ = create_draft(actor=self.user, payer_name="Jane Doe", receipt_amount=Decimal("100000.00"))
        rows = self._audit_rows(receipt)
        self.assertTrue(rows.exists())
        create_row = rows.filter(action_type="CREATE").first()
        self.assertIsNotNone(create_row)
        self.assertEqual(create_row.entity_type, "receipt")
        self.assertEqual(create_row.entity_id, receipt.pk)
        self.assertEqual(create_row.user_id, self.user.pk)

    def test_update_draft_writes_update_audit_row(self):
        receipt, _ = create_draft(actor=self.user, payer_name="Jane Doe", receipt_amount=Decimal("100000.00"))
        update_draft(receipt, actor=self.user, narration="Client confirmed cash deposit.")
        rows = self._audit_rows(receipt)
        update_row = rows.filter(action_type="UPDATE").first()
        self.assertIsNotNone(update_row, "an UPDATE audit row should be recorded")
        self.assertIn("narration", update_row.changed_fields)

    def test_status_history_recorded_on_create(self):
        receipt, _ = create_draft(actor=self.user, payer_name="Jane Doe", receipt_amount=Decimal("100000.00"))
        entry = ReceiptStatusHistory.objects.get(receipt=receipt)
        self.assertEqual(entry.to_status, ReceiptStatus.DRAFT)
        self.assertEqual(entry.changed_by_id, self.user.pk)
        self.assertEqual(entry.source_channel, "API")


class FirstPremiumEventTests(TestCase):
    def setUp(self):
        call_command("seed_receipt_parameters")
        self.user = User.objects.create_user(
            username="receipt_premium", password="Password@12345", email="receipt_premium@zic.tz"
        )

    def test_emit_first_premium_received_contract(self):
        receipt, _ = create_draft(actor=self.user, payer_name="Jane Doe", receipt_amount=Decimal("100000.00"))
        event = receipt_events.emit_first_premium_received(
            receipt,
            allocation=None,
            actor=self.user,
            from_status="POSTED",
            to_status="PARTIALLY_ALLOCATED",
            reason="First premium for OL proposal OLP-2026-0001.",
        )
        self.assertEqual(event.event_type, "FirstPremiumReceived")
        self.assertEqual(event.aggregate_type, "Receipt")
        self.assertEqual(event.payload["receipt_reference"], receipt.receipt_number)
        self.assertEqual(event.payload["amount"], "100000.00")
        self.assertEqual(event.payload["currency"], receipt.currency)
        self.assertEqual(event.payload["payment_mode"], receipt.payment_mode)
        self.assertEqual(event.payload["reverse_of"], None)
        self.assertEqual(event.payload["from_status"], "POSTED")
