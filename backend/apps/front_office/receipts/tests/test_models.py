from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.front_office.receipts.models import (
    Receipt,
    ReceiptAllocation,
    ReceiptPaymentMode,
    ReceiptReversal,
    ReceiptSourceModule,
    ReceiptStatus,
    is_valid_receipt_status,
    receipt_status_for_amounts,
)
from apps.partner_onboarding.models import Branch
from apps.partners.models import Partner

User = get_user_model()


def make_branch(code="DAR", name="Dar es Salaam"):
    return Branch.objects.create(code=code, name=name)


def make_partner(seq=1):
    return Partner.objects.create(
        partner_number=f"PN{seq:04d}",
        partner_type="INDIVIDUAL",
        party_type="INDIVIDUAL",
        first_name="Jane",
        surname="Doe",
        email=f"jane{seq}@zic.tz",
        mobile_number=f"2557000000{seq}",
    )


def make_receipt(**overrides):
    defaults = {
        "receipt_number": "RCT-2026-000001",
        "receipt_date": date(2026, 8, 24),
        "payer_name": "Jane Doe",
        "currency": "TZS",
        "receipt_amount": Decimal("100000.00"),
    }
    defaults.update(overrides)
    return Receipt.objects.create(**defaults)


class ReceiptModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="receipt_ops", password="Password@12345", email="receipt_ops@zic.tz"
        )
        self.branch = make_branch()
        self.partner = make_partner()

    def test_receipt_creation_defaults(self):
        receipt = make_receipt(
            receipt_number="RCT-2026-000042",
            branch=self.branch,
            partner=self.partner,
            payer_name="Jane Doe",
            receipt_amount=Decimal("50000.00"),
        )
        self.assertEqual(receipt.status, ReceiptStatus.DRAFT)
        self.assertEqual(receipt.allocated_amount, Decimal("0.00"))
        self.assertEqual(receipt.unallocated_amount, Decimal("50000.00"))
        self.assertEqual(receipt.source_module, ReceiptSourceModule.MANUAL)
        self.assertEqual(receipt.payment_mode, ReceiptPaymentMode.CASH)
        self.assertEqual(receipt.branch_name_snapshot, "Dar es Salaam")
        self.assertEqual(receipt.partner_name_snapshot, str(self.partner))

    def test_amount_computations_with_allocations(self):
        receipt = make_receipt(receipt_amount=Decimal("100000.00"))
        ReceiptAllocation.objects.create(
            receipt=receipt, target_type="OL_COMMITMENT", target_id="OLC-1", amount=Decimal("60000.00")
        )
        ReceiptAllocation.objects.create(
            receipt=receipt, target_type="OL_COMMITMENT", target_id="OLC-2", amount=Decimal("40000.00")
        )
        receipt.recompute_allocated()
        self.assertEqual(receipt.allocated_amount, Decimal("100000.00"))
        self.assertEqual(receipt.unallocated_amount, Decimal("0.00"))

    def test_reversed_allocations_excluded_from_computation(self):
        receipt = make_receipt(receipt_amount=Decimal("100000.00"))
        active = ReceiptAllocation.objects.create(
            receipt=receipt, target_type="OL_COMMITMENT", target_id="OLC-1", amount=Decimal("60000.00")
        )
        ReceiptAllocation.objects.create(
            receipt=receipt,
            target_type="OL_COMMITMENT",
            target_id="OLC-1",
            amount=Decimal("60000.00"),
            reversal_of=active,
        )
        receipt.recompute_allocated()
        self.assertEqual(receipt.allocated_amount, Decimal("60000.00"))
        self.assertEqual(receipt.unallocated_amount, Decimal("40000.00"))

    def test_posted_status_derivation(self):
        from django.utils import timezone

        receipt = make_receipt(receipt_amount=Decimal("100000.00"))
        receipt.posted_at = timezone.now()
        receipt._derive_status()
        self.assertEqual(receipt.status, ReceiptStatus.POSTED)

        ReceiptAllocation.objects.create(receipt=receipt, target_type="OL_COMMITMENT", target_id="OLC-1", amount=Decimal("40000.00"))
        receipt.recompute_allocated()
        receipt._derive_status()
        self.assertEqual(receipt.status, ReceiptStatus.PARTIALLY_ALLOCATED)

        ReceiptAllocation.objects.create(receipt=receipt, target_type="OL_COMMITMENT", target_id="OLC-2", amount=Decimal("60000.00"))
        receipt.recompute_allocated()
        receipt._derive_status()
        self.assertEqual(receipt.status, ReceiptStatus.FULLY_ALLOCATED)

    def test_status_helper_functions(self):
        self.assertTrue(is_valid_receipt_status("DRAFT"))
        self.assertTrue(is_valid_receipt_status("fully_allocated"))
        self.assertFalse(is_valid_receipt_status("NOT_A_STATUS"))
        self.assertEqual(receipt_status_for_amounts(Decimal("1"), Decimal("0")), ReceiptStatus.FULLY_ALLOCATED)
        self.assertEqual(receipt_status_for_amounts(Decimal("1"), Decimal("1")), ReceiptStatus.PARTIALLY_ALLOCATED)
        self.assertEqual(receipt_status_for_amounts(Decimal("0"), Decimal("10")), ReceiptStatus.POSTED)

    def test_clean_rejects_negative_amount(self):
        receipt = Receipt(
            receipt_number="RCT-BAD-1",
            payer_name="Jane Doe",
            receipt_date=date(2026, 8, 24),
            receipt_amount=Decimal("-5.00"),
        )
        with self.assertRaises(ValidationError) as ctx:
            receipt.full_clean_ex()
        self.assertIn("receipt_amount", ctx.exception.message_dict)

    def test_clean_rejects_bad_currency(self):
        receipt = Receipt(
            receipt_number="RCT-BAD-2",
            payer_name="Jane Doe",
            receipt_date=date(2026, 8, 24),
            receipt_amount=Decimal("100000.00"),
            currency="TANX",
        )
        with self.assertRaises(ValidationError) as ctx:
            receipt.full_clean_ex()
        self.assertIn("currency", ctx.exception.message_dict)

    def test_clean_requires_source_reference_for_proposal_module(self):
        receipt = make_receipt(
            receipt_number="RCT-BAD-3",
            source_module=ReceiptSourceModule.OL_PROPOSAL,
            source_reference_type="",
            source_reference_id="",
        )
        with self.assertRaises(ValidationError) as ctx:
            receipt.full_clean_ex()
        self.assertIn("source_reference_id", ctx.exception.message_dict)

    def test_proposal_source_reference_must_exist(self):
        receipt = make_receipt(
            receipt_number="RCT-BAD-4",
            source_module=ReceiptSourceModule.OL_PROPOSAL,
            source_reference_type="PROPOSAL_NUMBER",
            source_reference_id="OLP-DOES-NOT-EXIST",
        )
        with self.assertRaises(ValidationError):
            receipt.full_clean_ex()

    def test_allocation_clean_rules(self):
        receipt = make_receipt()
        bad = ReceiptAllocation(receipt=receipt, target_type="OL_COMMITMENT", target_id="OLC-1", amount=Decimal("0"))
        with self.assertRaises(ValidationError):
            bad.full_clean()
        bad_currency = ReceiptAllocation(
            receipt=receipt, target_type="OL_COMMITMENT", target_id="OLC-1", amount=Decimal("10"), currency="XY"
        )
        with self.assertRaises(ValidationError):
            bad_currency.full_clean()

    def test_reversal_clean_requires_reason(self):
        receipt = make_receipt()
        reversal = ReceiptReversal(receipt=receipt, reversal_number="RRV-1", reason="")
        with self.assertRaises(ValidationError):
            reversal.full_clean()

    def test_receipt_number_unique(self):
        make_receipt(receipt_number="RCT-DUP-1")
        with self.assertRaises(Exception):
            make_receipt(receipt_number="RCT-DUP-1")
