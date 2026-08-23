from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.common.models import DomainEvent
from apps.governance.models import AuditLog
from apps.ol_commitments import events
from apps.ol_commitments.events import (
    COMMITMENT_GENERATED,
    COMMITMENT_PAYMENT_ALLOCATED,
)
from apps.ol_commitments.models import CommitmentSourceChannel, OLCommitment, OLCommitmentAllocation
from apps.ol_parameters.models import OLCommitmentStatus

User = get_user_model()


class CommitmentEventTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="event_ops",
            password="Password@12345",
            email="event_ops@zic.tz",
        )
        OLCommitmentStatus.objects.create(
            code="PENDING", name="Pending", applies_to="COMMITMENT", display_order=10, is_active=True
        )
        self.commitment = OLCommitment.objects.create(
            commitment_number="OLC-2026-00001",
            source_type="MANUAL",
            currency="TZS",
            due_date=date(2026, 9, 1),
            premium_amount=Decimal("100000.00"),
            status="PENDING",
            source_channel=CommitmentSourceChannel.API,
            created_by=self.user,
        )

    def test_generated_event_wired_to_outbox(self):
        event = events.emit_generated(
            self.commitment,
            actor=self.user,
            reason="Proposal approved to payment",
            source_channel=CommitmentSourceChannel.API,
        )
        self.assertEqual(event.event_type, COMMITMENT_GENERATED)
        self.assertEqual(event.aggregate_type, "OLCommitment")
        self.assertEqual(event.aggregate_id, str(self.commitment.pk))
        self.assertEqual(event.status, DomainEvent.Status.PENDING)
        self.assertEqual(event.payload["commitment_number"], "OLC-2026-00001")
        self.assertEqual(event.payload["source_channel"], "API")
        self.assertEqual(event.payload["actor_id"], str(self.user.pk))

    def test_allocation_event_includes_allocation_metadata(self):
        allocation = OLCommitmentAllocation.objects.create(
            commitment=self.commitment,
            receipt_reference="RCT-2026-0001",
            amount=Decimal("50000.00"),
            currency="TZS",
            payment_mode="CASH",
            allocated_by=self.user,
            source_channel=CommitmentSourceChannel.API,
        )
        event = events.emit_payment_allocated(
            self.commitment,
            allocation=allocation,
            actor=self.user,
            from_status="PENDING",
            source_channel=CommitmentSourceChannel.API,
        )
        self.assertEqual(event.event_type, COMMITMENT_PAYMENT_ALLOCATED)
        self.assertEqual(event.payload["receipt_reference"], "RCT-2026-0001")
        self.assertEqual(event.payload["amount"], "50000.00")


class CommitmentAuditTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="audit_ops",
            password="Password@12345",
            email="audit_ops@zic.tz",
        )
        OLCommitmentStatus.objects.create(
            code="PENDING", name="Pending", applies_to="COMMITMENT", display_order=10, is_active=True
        )

    def test_commitment_and_allocation_writes_audit_rows(self):
        commitment = OLCommitment.objects.create(
            commitment_number="OLC-2026-00002",
            source_type="MANUAL",
            currency="TZS",
            due_date=date(2026, 9, 1),
            premium_amount=Decimal("100000.00"),
            status="PENDING",
            source_channel=CommitmentSourceChannel.MANUAL,
            created_by=self.user,
        )
        OLCommitmentAllocation.objects.create(
            commitment=commitment,
            receipt_reference="RCT-2026-0002",
            amount=Decimal("25000.00"),
            currency="TZS",
            payment_mode="CASH",
            allocated_by=self.user,
            reason="First installment",
            source_channel=CommitmentSourceChannel.MANUAL,
        )

        commitment_logs = AuditLog.objects.filter(
            app_label="ol_commitments", model_name="olcommitment", object_id=str(commitment.pk)
        )
        self.assertTrue(commitment_logs.exists())
        self.assertEqual(commitment_logs.first().user, self.user)
        self.assertEqual(commitment_logs.first().source_channel, CommitmentSourceChannel.MANUAL)
        self.assertEqual(commitment_logs.first().action_type, "CREATE")

        allocation_logs = AuditLog.objects.filter(app_label="ol_commitments", model_name="olcommitmentallocation")
        self.assertTrue(allocation_logs.exists())

    def test_update_captures_before_after_and_reason(self):
        commitment = OLCommitment.objects.create(
            commitment_number="OLC-2026-00003",
            source_type="MANUAL",
            currency="TZS",
            due_date=date(2026, 9, 1),
            premium_amount=Decimal("100000.00"),
            status="PENDING",
            source_channel=CommitmentSourceChannel.API,
            created_by=self.user,
        )
        commitment.amount_paid = Decimal("40000.00")
        commitment.reason_text = "Cash payment posted"
        commitment.save(update_fields=["amount_paid", "reason_text", "balance"])

        logs = AuditLog.objects.filter(
            app_label="ol_commitments",
            model_name="olcommitment",
            action="UPDATE",
        )
        self.assertTrue(logs.exists())
        log = logs.first()
        self.assertIn("amount_paid", log.changed_fields)
        self.assertEqual(log.reason, "OL Commitment: Cash payment posted")
        self.assertIsNotNone(log.before_state)
        self.assertIsNotNone(log.after_state)
        self.assertEqual(log.actor_type, AuditLog.ActorType.USER)
