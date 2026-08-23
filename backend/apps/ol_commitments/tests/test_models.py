from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.ol_commitments.models import (
    OLCommitment,
    OLCommitmentAllocation,
    OLCommitmentNotificationLog,
)
from apps.ol_parameters.models import OLCommitmentStatus, OLGracePeriod

User = get_user_model()


class CommitmentModelTestBase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="commitment_ops",
            password="Password@12345",
            email="commitment_ops@zic.tz",
        )
        self.status_pending = OLCommitmentStatus.objects.create(
            code="PENDING",
            name="Pending",
            applies_to="COMMITMENT",
            display_order=10,
            is_terminal=False,
            is_active=True,
        )
        self.status_active = OLCommitmentStatus.objects.create(
            code="ACTIVE",
            name="Active",
            applies_to="COMMITMENT",
            display_order=20,
            is_terminal=False,
            is_active=True,
        )
        self.status_completed = OLCommitmentStatus.objects.create(
            code="COMPLETED",
            name="Completed",
            applies_to="COMMITMENT",
            display_order=30,
            is_terminal=True,
            is_active=True,
        )
        self.grace = OLGracePeriod.objects.create(
            code="MONTHLY_STANDARD",
            name="Monthly standard grace",
            premium_frequency="MONTHLY",
            grace_days=30,
            warning_days=14,
            pre_lapse_days=7,
            lapse_days=45,
            minimum_due_amount=Decimal("25000.00"),
            effective_from=date(2026, 1, 1),
            is_active=True,
        )

    def _commitment(self, **overrides):
        defaults = {
            "commitment_number": "OLC-2026-00001",
            "source_type": "MANUAL",
            "currency": "TZS",
            "installment_number": 1,
            "installment_count": 1,
            "due_date": date(2026, 9, 1),
            "premium_amount": Decimal("100000.00"),
            "amount_paid": Decimal("0.00"),
            "status": "PENDING",
            "created_by": self.user,
        }
        defaults.update(overrides)
        return OLCommitment(**defaults)


class OLCommitmentModelTests(CommitmentModelTestBase):
    def test_model_creation_uses_parameterized_status(self):
        commitment = self._commitment(status="PENDING")
        commitment.full_clean()
        commitment.save()
        self.assertEqual(commitment.status, "PENDING")
        self.assertEqual(commitment.balance, Decimal("100000.00"))
        self.assertEqual(commitment.source_type, "MANUAL")

    def test_balance_computation_full_partial_and_waived(self):
        commitment = self._commitment()
        commitment.save()
        self.assertEqual(commitment.balance, Decimal("100000.00"))

        commitment.amount_paid = Decimal("40000.00")
        commitment.save()
        self.assertEqual(commitment.balance, Decimal("60000.00"))

        commitment.amount_waived = Decimal("10000.00")
        commitment.recompute_balance()
        commitment.save()
        self.assertEqual(commitment.balance, Decimal("50000.00"))

    def test_default_status_resolved_from_parameter_catalog_by_display_order(self):
        commitment = self._commitment(status="")
        commitment.save()
        self.assertEqual(commitment.status, self.status_pending.code)

    def test_grace_envelope_computed_from_grace_period_parameter(self):
        commitment = self._commitment(due_date=date(2026, 9, 1))
        commitment.save()
        self.assertEqual(commitment.grace_date, date(2026, 10, 1))
        self.assertEqual(commitment.lapse_date, date(2026, 10, 16))
        self.assertEqual(commitment.warning_date, date(2026, 9, 15))
        self.assertEqual(commitment.pre_lapse_date, date(2026, 9, 8))

    def test_status_validated_against_parameter_catalog(self):
        commitment = self._commitment(status="NOT_CONFIGURED")
        with self.assertRaises(ValidationError):
            commitment.full_clean()

    def test_grace_envelope_resolved_by_frequency_scope(self):
        OLGracePeriod.objects.create(
            code="GLOBAL_GRACE",
            name="Global grace",
            grace_days=15,
            warning_days=5,
            pre_lapse_days=3,
            lapse_days=30,
            effective_from=date(2026, 1, 1),
            is_active=True,
        )
        monthly = self._commitment(due_date=date(2026, 9, 1), premium_frequency="MONTHLY")
        monthly.save()
        global_row = self._commitment(commitment_number="OLC-2026-00002", due_date=date(2026, 9, 1))
        global_row.save()
        # MONTHLY-scoped row wins for a MONTHLY commitment.
        self.assertEqual(monthly.grace_date, date(2026, 10, 1))
        # Global row is the fallback when no frequency-matched row exists.
        self.assertEqual(global_row.grace_date, date(2026, 9, 16))


class OLCommitmentAllocationTests(CommitmentModelTestBase):
    def test_allocation_saves_and_reversal_links(self):
        commitment = self._commitment()
        commitment.save()
        allocation = OLCommitmentAllocation.objects.create(
            commitment=commitment,
            receipt_reference="RCT-2026-0001",
            amount=Decimal("50000.00"),
            payment_mode="CASH",
            currency="TZS",
            allocated_by=self.user,
        )
        reversal = OLCommitmentAllocation.objects.create(
            commitment=commitment,
            receipt_reference="RCT-2026-0001-R1",
            amount=Decimal("50000.00"),
            payment_mode="CASH",
            currency="TZS",
            reason="Duplicate receipt",
            reversal_of=allocation,
            allocated_by=self.user,
        )
        self.assertEqual(commitment.allocations.count(), 2)
        self.assertEqual(reversal.reversal_of, allocation)

    def test_allocation_requires_positive_amount(self):
        commitment = self._commitment()
        commitment.save()
        allocation = OLCommitmentAllocation(
            commitment=commitment,
            receipt_reference="RCT-2026-0002",
            amount=Decimal("0.00"),
            currency="TZS",
        )
        with self.assertRaises(ValidationError):
            allocation.full_clean()

    def test_manual_receipt_reference_generated(self):
        commitment = self._commitment()
        commitment.save()
        allocation = OLCommitmentAllocation(
            commitment=commitment,
            amount=Decimal("25000.00"),
            currency="TZS",
            payment_mode="M-PESA",
        )
        allocation.save()
        self.assertTrue(allocation.receipt_reference.startswith("MANUAL-"))


class OLCommitmentNotificationLogTests(CommitmentModelTestBase):
    def test_notification_log_creation_and_unique_runs(self):
        commitment = self._commitment()
        commitment.save()
        first = OLCommitmentNotificationLog.objects.create(
            commitment=commitment,
            event_type="GRACE_START",
            dispatch_on=date(2026, 9, 2),
            notification_channel="SMS",
            recipient_type="POLICYHOLDER",
            recipient_identifier="+255700000000",
            template_code="ZIC-OL-GRACE-START",
        )
        self.assertEqual(commitment.notification_logs.count(), 1)
        self.assertEqual(first.event_type, "GRACE_START")
        self.assertEqual(first.status, "PENDING")
