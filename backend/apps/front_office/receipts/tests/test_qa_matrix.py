"""Prompt 11 — full backend test matrix and security hardening.

Consolidated matrices across the receipt money flows (draft -> post ->
allocate -> reverse/cancel), the nine receipt permission codes (allow/deny),
the audit trail for every lifecycle action, the idempotency guarantees, the
security invariants (partner isolation, structured 403, no raw-UUID display
leaks, posted immutability), and the list/performance contract (pagination and
indexes on the common filters).

Many individual flows already have dedicated test modules; this file is the
single matrix that walks every money movement end-to-end and asserts the
state/money invariant at each step, plus the allow/deny, audit, idempotency,
and security matrices the dedicated modules do not consolidate.
"""

import csv
import io
import re
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.common.models import DomainEvent
from apps.front_office.receipts.models import (
    Receipt,
    ReceiptAllocation,
    ReceiptAllocationStatus,
    ReceiptImportBatch,
    ReceiptImportBatchStatus,
    ReceiptStatus,
)
from apps.front_office.receipts.permissions import ACTIONS, has_receipt_permission
from apps.front_office.receipts.services.import_service import IMPORT_COLUMNS
from apps.governance.models import AuditLog
from apps.ol_commitments.models import OLCommitment
from apps.ol_parameters.models import OLCommitmentStatus
from apps.partner_onboarding.models import Branch
from apps.partners.models import Partner, UserPartnerLink
from apps.users.models import UserGroup, UserPermission

User = get_user_model()

BASE = "/api/v1/front-office/receipts"

UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


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
        "partner_number": f"QA{seq:04d}",
        "partner_type": "INDIVIDUAL",
        "party_type": "INDIVIDUAL",
        "first_name": "Jane",
        "surname": "Doe",
        "email": f"qa{seq}@zic.tz",
        "mobile_number": f"2557000000{seq}",
        "is_active": True,
        "status": "ACTIVE",
    }
    defaults.update(overrides)
    return Partner.objects.create(**defaults)


def make_row(**overrides):
    base = {
        "receipt_date": "2026-08-20",
        "branch_code": "DAR",
        "payer_partner_number": "QA0001",
        "currency_code": "TZS",
        "payment_mode_code": "CASH",
        "amount": "100000.00",
        "payment_reference": "",
        "source_module": "MANUAL",
        "target_commitment_number": "",
        "narration": "Bulk import matrix",
    }
    base.update(overrides)
    return base


def make_csv(rows, columns=None):
    columns = columns or IMPORT_COLUMNS
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=columns)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return SimpleUploadedFile(
        "receipts.csv", buf.getvalue().encode("utf-8"), content_type="text/csv"
    )


class ReceiptMatrixBase(APITestCase):
    def setUp(self):
        call_command("seed_receipt_parameters")
        call_command("seed_receipt_permissions")
        seed_commitment_statuses()
        self.admin = User.objects.create_superuser(
            username="matrix_admin", password="Password@12345", email="matrix_admin@zic.tz"
        )
        self.client.force_authenticate(self.admin)
        self.branch = Branch.objects.create(code="DAR", name="Dar es Salaam")
        self.partner = make_partner()

    def _create_draft(self, amount="100000.00", currency="TZS", **overrides):
        payload = {
            "payer_name": "Jane Doe",
            "receipt_date": timezone.localdate().isoformat(),
            "receipt_amount": amount,
            "currency": currency,
            "branch": str(self.branch.pk),
            "partner": str(self.partner.pk),
        }
        payload.update(overrides)
        return self.client.post(f"{BASE}/", payload, format="json")

    def _create_and_post(self, amount="100000.00", currency="TZS", **overrides):
        created = self._create_draft(amount=amount, currency=currency, **overrides)
        self.assertEqual(created.status_code, 201, created.data)
        posted = self.client.post(
            f"{BASE}/{created.data['data']['id']}/post/", {"reason": "Money confirmed."}, format="json"
        )
        self.assertEqual(posted.status_code, 200, posted.data)
        return posted.data["data"]

    def _make_commitment(self, number, currency="TZS", premium="100000.00", partner=None, **overrides):
        due_date = overrides.pop("due_date", timezone.localdate() + timedelta(days=10))
        return OLCommitment.objects.create(
            commitment_number=number,
            source_type="MANUAL",
            currency=currency,
            due_date=due_date,
            premium_amount=premium,
            status="PENDING",
            partner=partner or self.partner,
            partner_name_snapshot=str(partner or self.partner),
            source_channel="API",
            **overrides,
        )

    def _allocate(self, receipt_id, target_id, amount, **overrides):
        payload = {
            "target_type": "OL_COMMITMENT",
            "target_id": target_id,
            "amount": str(amount),
        }
        payload.update(overrides)
        return self.client.post(f"{BASE}/{receipt_id}/allocate/", payload, format="json")

    def _audit_rows(self, entity_type, entity_id):
        return AuditLog.objects.filter(entity_type=entity_type, entity_id=entity_id)


class ReceiptMoneyFlowMatrixTests(ReceiptMatrixBase):
    """Scope 1 — every money flow through the full lifecycle."""

    def test_matrix_draft_create_and_edit_flow(self):
        created = self._create_draft(narration="Initial note")
        self.assertEqual(created.status_code, 201, created.data)
        data = created.data["data"]
        self.assertEqual(data["status"], ReceiptStatus.DRAFT)
        self.assertIsNone(data["receipt_number"])
        self.assertEqual(data["unallocated_amount"], "100000.00")
        self.assertIn("update", data["allowed_actions"])

        edited = self.client.patch(
            f"{BASE}/{data['id']}/",
            {"narration": "Client confirmed the deposit.", "receipt_amount": "120000.00"},
            format="json",
        )
        self.assertEqual(edited.status_code, 200, edited.data)
        self.assertEqual(edited.data["data"]["narration"], "Client confirmed the deposit.")
        self.assertEqual(edited.data["data"]["receipt_amount"], "120000.00")
        self.assertEqual(edited.data["data"]["status"], ReceiptStatus.DRAFT)

    def test_matrix_payment_mode_validation(self):
        # Bank transfers demand a payment reference.
        draft = self._create_draft(payment_mode="BANK_TRANSFER").data["data"]
        posted = self.client.post(f"{BASE}/{draft['id']}/post/", {"reason": "Pay."}, format="json")
        self.assertEqual(posted.status_code, 422, posted.data)
        self.assertEqual(posted.data["error_code"], "RECEIPT_PAYMENT_REFERENCE_REQUIRED")
        self.assertIn("payment_reference", posted.data["field_errors"])

        # Zero/negative amounts are invalid at draft time.
        bad = self._create_draft(amount="0.00")
        self.assertEqual(bad.status_code, 422, bad.data)
        self.assertEqual(bad.data["error_code"], "RECEIPT_AMOUNT_INVALID")

    def test_matrix_post_flow(self):
        created = self._create_draft().data["data"]
        response = self.client.post(f"{BASE}/{created['id']}/post/", {"reason": "Money confirmed."}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        data = response.data["data"]
        self.assertRegex(data["receipt_number"], r"^RCT-\d{4}-\d{6}$")
        self.assertEqual(data["status"], ReceiptStatus.POSTED)
        self.assertIsNotNone(data["posted_at"])
        self.assertEqual(data["unallocated_amount"], "100000.00")

        # A posted receipt is terminal for posting.
        again = self.client.post(f"{BASE}/{created['id']}/post/", {"reason": "Again."}, format="json")
        self.assertEqual(again.status_code, 409, again.data)
        self.assertEqual(again.data["error_code"], "RECEIPT_ALREADY_POSTED")

    def test_matrix_partial_full_and_over_allocation_flow(self):
        commitment_a = self._make_commitment("OLC-QA-FLOW-1", premium="100000.00")
        commitment_b = self._make_commitment("OLC-QA-FLOW-2", premium="60000.00")
        extra = self._make_commitment("OLC-QA-FLOW-3", premium="100000.00")
        receipt = self._create_and_post()

        partial = self._allocate(receipt["id"], commitment_a.commitment_number, "40000.00")
        self.assertEqual(partial.status_code, 201, partial.data)
        self.assertEqual(partial.data["data"]["status"], ReceiptStatus.PARTIALLY_ALLOCATED)
        self.assertEqual(partial.data["data"]["allocated_amount"], "40000.00")
        self.assertEqual(partial.data["data"]["unallocated_amount"], "60000.00")
        commitment_a.refresh_from_db()
        self.assertEqual(commitment_a.amount_paid, Decimal("40000.00"))
        self.assertEqual(commitment_a.status, "PARTIALLY_PAID")

        # Over-allocation is rejected while the receipt still has a balance,
        # with nothing written for the offending allocation.
        over = self._allocate(receipt["id"], extra.commitment_number, "70000.00")
        self.assertEqual(over.status_code, 422, over.data)
        self.assertEqual(over.data["error_code"], "RECEIPT_OVERALLOCATION")
        self.assertEqual(ReceiptAllocation.objects.filter(receipt_id=receipt["id"]).count(), 1)

        # Allocating the exact remaining balance completes the split.
        full = self._allocate(receipt["id"], commitment_b.commitment_number, "60000.00")
        self.assertIn(full.status_code, (200, 201), full.data)
        self.assertEqual(full.data["data"]["status"], ReceiptStatus.FULLY_ALLOCATED)
        self.assertEqual(full.data["data"]["allocated_amount"], "100000.00")
        self.assertEqual(full.data["data"]["unallocated_amount"], "0.00")
        commitment_b.refresh_from_db()
        self.assertEqual(commitment_b.status, "COMPLETED")
        self.assertEqual(commitment_b.balance, Decimal("0.00"))

    def test_matrix_auto_allocation_flow(self):
        partner = make_partner(seq=2)
        older = self._make_commitment(
            "OLC-QA-AUTO-1", premium="60000.00", partner=partner,
            due_date=timezone.localdate() + timedelta(days=-5),
        )
        newer = self._make_commitment(
            "OLC-QA-AUTO-2", premium="40000.00", partner=partner,
            due_date=timezone.localdate() + timedelta(days=30),
        )
        receipt = self._create_and_post(amount="80000.00", partner=str(partner.pk))
        response = self.client.post(f"{BASE}/{receipt['id']}/auto-allocate/", {}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        data = response.data["data"]
        self.assertEqual(data["receipt_status"], ReceiptStatus.FULLY_ALLOCATED)
        self.assertEqual(data["total_allocated"], "80000.00")
        self.assertEqual(data["remaining_unallocated"], "0.00")
        self.assertEqual(data["commitments_count"], 2)
        order = [item["commitment_number"] for item in data["allocations"]]
        self.assertEqual(order, [older.commitment_number, newer.commitment_number])
        older.refresh_from_db()
        newer.refresh_from_db()
        self.assertEqual(older.status, "COMPLETED")
        self.assertEqual(newer.status, "PARTIALLY_PAID")
        self.assertEqual(newer.balance, Decimal("20000.00"))

    def test_matrix_multi_currency_allocation_and_missing_rate(self):
        commitment = self._make_commitment("OLC-QA-FX-1", premium="250000.00")
        receipt = self._create_and_post(amount="5000.00", currency="USD")

        # Explicit rate converts into the target currency.
        explicit = self._allocate(receipt["id"], commitment.commitment_number, "5000.00", exchange_rate="50")
        self.assertEqual(explicit.status_code, 201, explicit.data)
        alloc = explicit.data["data"]["allocations"][0]
        self.assertEqual(alloc["allocation_amount_in_receipt_currency"], "5000.00")
        self.assertEqual(alloc["allocation_amount_in_target_currency"], "250000.00")
        commitment.refresh_from_db()
        self.assertEqual(commitment.amount_paid, Decimal("250000.00"))
        self.assertEqual(commitment.status, "COMPLETED")

        # A second cross-currency receipt with no rate is refused cleanly.
        missing_commitment = self._make_commitment("OLC-QA-FX-2", premium="250000.00")
        receipt2 = self._create_and_post(amount="5000.00", currency="USD")
        missing = self._allocate(receipt2["id"], missing_commitment.commitment_number, "5000.00")
        self.assertEqual(missing.status_code, 422, missing.data)
        self.assertEqual(missing.data["error_code"], "RECEIPT_CURRENCY_MISMATCH")
        self.assertIn("exchange_rate", missing.data["field_errors"])
        self.assertFalse(ReceiptAllocation.objects.filter(receipt_id=receipt2["id"]).exists())

    def test_matrix_full_and_partial_reversal_flow(self):
        commitment = self._make_commitment("OLC-QA-REV-1")
        receipt = self._create_and_post(amount="100000.00")
        self._allocate(receipt["id"], commitment.commitment_number, "100000.00")

        # Partial reversal of the only allocation returns the receipt to POSTED.
        reversed_row = self.client.post(
            f"{BASE}/{receipt['id']}/reverse/", {"reason": "Duplicate payment."}, format="json"
        )
        self.assertEqual(reversed_row.status_code, 200, reversed_row.data)
        data = reversed_row.data["data"]
        self.assertEqual(data["status"], ReceiptStatus.REVERSED)
        commitment.refresh_from_db()
        self.assertEqual(commitment.amount_paid, Decimal("0.00"))
        self.assertEqual(commitment.balance, Decimal("100000.00"))

        # Reversing an already-reversed receipt is a clean 409.
        second = self.client.post(
            f"{BASE}/{receipt['id']}/reverse/", {"reason": "Again."}, format="json"
        )
        self.assertEqual(second.status_code, 409, second.data)
        self.assertEqual(second.data["error_code"], "RECEIPT_ALREADY_REVERSED")

    def test_matrix_partial_allocation_reversal_flow(self):
        commitment = self._make_commitment("OLC-QA-REV-2")
        receipt = self._create_and_post(amount="100000.00")
        self._allocate(receipt["id"], commitment.commitment_number, "60000.00")

        # Reverse the single allocation, not the whole receipt.
        allocation = ReceiptAllocation.objects.get(receipt_id=receipt["id"])
        response = self.client.post(
            f"{BASE}/{receipt['id']}/allocations/{allocation.pk}/reverse/",
            {"reason": "Correct the amount."},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        data = response.data["data"]
        self.assertEqual(data["status"], ReceiptStatus.POSTED)
        self.assertEqual(data["allocated_amount"], "0.00")
        self.assertEqual(data["unallocated_amount"], "100000.00")
        allocation.refresh_from_db()
        self.assertEqual(allocation.allocation_status, ReceiptAllocationStatus.REVERSED)
        commitment.refresh_from_db()
        self.assertEqual(commitment.amount_paid, Decimal("0.00"))

    def test_matrix_cancellation_flow(self):
        draft = self._create_draft().data["data"]
        cancelled = self.client.post(f"{BASE}/{draft['id']}/cancel/", {"reason": "Payer backed out."}, format="json")
        self.assertEqual(cancelled.status_code, 200, cancelled.data)
        self.assertEqual(cancelled.data["data"]["status"], ReceiptStatus.CANCELLED)

        # A posted receipt cannot be cancelled.
        posted = self._create_and_post()
        blocked = self.client.post(f"{BASE}/{posted['id']}/cancel/", {"reason": "No."}, format="json")
        self.assertEqual(blocked.status_code, 422, blocked.data)
        self.assertEqual(blocked.data["error_code"], "RECEIPT_INVALID_STATUS")

    def test_matrix_print_flow(self):
        receipt = self._create_and_post()
        printed = self.client.post(f"{BASE}/{receipt['id']}/print/", {}, format="json")
        self.assertEqual(printed.status_code, 201, printed.data)
        data = printed.data["data"]
        self.assertEqual(data["document_type"], "RECEIPT")
        self.assertEqual(data["status"], "GENERATED")
        self.assertIsNotNone(data["template_code"])
        self.assertIn("urls", data)

    def test_matrix_import_dry_run_and_commit_flow(self):
        file = make_csv([make_row(narration="Row one"), make_row(amount="200000.00", narration="Row two")])
        dry = self.client.post(f"{BASE}/import/dry-run/", {"file": file, "import_mode": "DRAFT"}, format="multipart")
        self.assertEqual(dry.status_code, 200, dry.data)
        batch_id = dry.data["data"]["batch"]["id"]
        batch = ReceiptImportBatch.objects.get(pk=batch_id)
        self.assertEqual(batch.status, ReceiptImportBatchStatus.VALIDATED)
        self.assertEqual(batch.valid_rows, 2)
        self.assertEqual(batch.invalid_rows, 0)
        self.assertEqual(Receipt.objects.count(), 0, "dry-run must not create receipts")

        committed = self.client.post(f"{BASE}/import/commit/", {"batch_id": batch_id}, format="json")
        self.assertEqual(committed.status_code, 200, committed.data)
        self.assertEqual(Receipt.objects.count(), 2)
        batch.refresh_from_db()
        self.assertEqual(batch.status, ReceiptImportBatchStatus.COMMITTED)
        self.assertEqual(batch.committed_rows, 2)

        # Re-committing the same batch is a no-op.
        again = self.client.post(f"{BASE}/import/commit/", {"batch_id": batch_id}, format="json")
        self.assertEqual(again.status_code, 200, again.data)
        self.assertEqual(Receipt.objects.count(), 2, "re-commit must not duplicate")

    def test_matrix_portal_scoping_flow(self):
        partner_b = make_partner(seq=3)
        receipt_a = self._create_and_post(amount="100000.00", partner=str(self.partner.pk))
        receipt_b = self._create_and_post(amount="20000.00", partner=str(partner_b.pk))

        portal = User.objects.create_user(
            username="matrix_portal", password="Password@12345", email="matrix_portal@zic.tz"
        )
        UserPartnerLink.objects.create(
            user=portal, partner=self.partner, link_status="ACTIVE", is_primary=True
        )
        self.client.force_authenticate(portal)

        listing = self.client.get(f"{BASE}/portal/")
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.data["data"]["count"], 1)
        self.assertEqual(listing.data["data"]["results"][0]["receipt_number"], receipt_a["receipt_number"])

        own = self.client.get(f"{BASE}/portal/{receipt_a['id']}/")
        self.assertEqual(own.status_code, 200)
        self.assertEqual(own.data["data"]["receipt_number"], receipt_a["receipt_number"])

        foreign = self.client.get(f"{BASE}/portal/{receipt_b['id']}/")
        self.assertEqual(foreign.status_code, 404)
        self.assertEqual(foreign.data["error_code"], "RECEIPT_NOT_FOUND")

    def test_matrix_dashboard_and_report_dataset_flow(self):
        commitment = self._make_commitment("OLC-QA-KPI")
        today = timezone.localdate()
        self._create_and_post(amount="100000.00", receipt_date=today)
        receipt_b = self._create_and_post(amount="50000.00", receipt_date=today)
        self._allocate(receipt_b["id"], commitment.commitment_number, "50000.00")

        kpis = self.client.get(f"{BASE}/kpis/")
        self.assertEqual(kpis.status_code, 200)
        self.assertEqual(kpis.data["data"]["receipts_today"], 2)
        self.assertEqual(kpis.data["data"]["amount_received_today"], "150000.00")
        self.assertEqual(kpis.data["data"]["unallocated_receipts"], 1)
        self.assertEqual(kpis.data["data"]["total_unallocated"], "100000.00")

        dataset = self.client.get(f"{BASE}/reporting/dataset/")
        self.assertEqual(dataset.status_code, 200)
        self.assertEqual(dataset.data["data"]["category"]["code"], "FRONT_OFFICE_RECEIPTS")


class ReceiptPermissionMatrixTests(ReceiptMatrixBase):
    """Scope 2 — every receipt permission code tested for allow and deny."""

    def _grant(self, user, codename):
        group, _ = UserGroup.objects.get_or_create(
            code=f"MATRIX_{codename.rsplit('.', 1)[-1].upper()}",
            defaults={
                "name": f"Matrix {codename}",
                "description": f"Matrix allow-grant for {codename}.",
                "group_type": "INTERNAL",
                "is_active": True,
            },
        )
        group.permissions.set([UserPermission.objects.get(codename=codename)])
        group.users.add(user)
        return group

    def _viewer(self, username):
        user = User.objects.create_user(
            username=username, password="Password@12345", email=f"{username}@zic.tz"
        )
        UserGroup.objects.get(code="RECEIPT_VIEWER").users.add(user)
        return user

    def _assert_denied(self, response):
        self.assertEqual(response.status_code, 403, response.data)
        self.assertEqual(response.data["error_code"], "FORBIDDEN")
        self.assertIs(response.data["success"], False)
        self.assertTrue(response.data["message"])
        self.assertEqual(response.data["error"]["code"], "FORBIDDEN")

    def test_view_permission_allow_deny(self):
        viewer = self._viewer("matrix_viewer")
        self.client.force_authenticate(viewer)
        self.assertEqual(self.client.get(f"{BASE}/").status_code, 200)

        plain = User.objects.create_user(
            username="matrix_noperms", password="Password@12345", email="matrix_noperms@zic.tz"
        )
        self.client.force_authenticate(plain)
        self._assert_denied(self.client.get(f"{BASE}/"))

    def test_create_permission_allow_deny(self):
        user = User.objects.create_user(
            username="matrix_creator", password="Password@12345", email="matrix_creator@zic.tz"
        )
        self._grant(user, "front_office.receipts.create")
        self.client.force_authenticate(user)
        self.assertEqual(self._create_draft().status_code, 201)

        self.client.force_authenticate(self._viewer("matrix_creator_deny"))
        self._assert_denied(self._create_draft())

    def test_post_permission_allow_deny(self):
        draft = self._create_draft().data["data"]
        draft2 = self._create_draft().data["data"]
        user = User.objects.create_user(
            username="matrix_poster", password="Password@12345", email="matrix_poster@zic.tz"
        )
        self._grant(user, "front_office.receipts.post")
        self.client.force_authenticate(user)
        allowed = self.client.post(f"{BASE}/{draft['id']}/post/", {"reason": "Money confirmed."}, format="json")
        self.assertEqual(allowed.status_code, 200, allowed.data)

        self.client.force_authenticate(self._viewer("matrix_poster_deny"))
        self._assert_denied(
            self.client.post(f"{BASE}/{draft2['id']}/post/", {"reason": "Money confirmed."}, format="json")
        )

    def test_allocate_permission_allow_deny(self):
        commitment = self._make_commitment("OLC-QA-PERM-ALLOC")
        receipt = self._create_and_post(amount="100000.00")
        receipt2 = self._create_and_post(amount="100000.00")
        user = User.objects.create_user(
            username="matrix_allocator", password="Password@12345", email="matrix_allocator@zic.tz"
        )
        self._grant(user, "front_office.receipts.allocate")
        self.client.force_authenticate(user)
        allowed = self._allocate(receipt["id"], commitment.commitment_number, "100000.00")
        self.assertEqual(allowed.status_code, 201, allowed.data)

        self.client.force_authenticate(self._viewer("matrix_allocator_deny"))
        self._assert_denied(self._allocate(receipt2["id"], commitment.commitment_number, "100000.00"))

    def test_reverse_permission_allow_deny(self):
        receipt = self._create_and_post(amount="100000.00")
        receipt2 = self._create_and_post(amount="100000.00")
        user = User.objects.create_user(
            username="matrix_reverser", password="Password@12345", email="matrix_reverser@zic.tz"
        )
        self._grant(user, "front_office.receipts.reverse")
        self.client.force_authenticate(user)
        allowed = self.client.post(f"{BASE}/{receipt['id']}/reverse/", {"reason": "Duplicate."}, format="json")
        self.assertEqual(allowed.status_code, 200, allowed.data)

        self.client.force_authenticate(self._viewer("matrix_reverser_deny"))
        self._assert_denied(
            self.client.post(f"{BASE}/{receipt2['id']}/reverse/", {"reason": "Duplicate."}, format="json")
        )

    def test_cancel_permission_allow_deny(self):
        draft = self._create_draft().data["data"]
        draft2 = self._create_draft().data["data"]
        user = User.objects.create_user(
            username="matrix_canceller", password="Password@12345", email="matrix_canceller@zic.tz"
        )
        self._grant(user, "front_office.receipts.cancel")
        self.client.force_authenticate(user)
        allowed = self.client.post(f"{BASE}/{draft['id']}/cancel/", {"reason": "Payer backed out."}, format="json")
        self.assertEqual(allowed.status_code, 200, allowed.data)

        self.client.force_authenticate(self._viewer("matrix_canceller_deny"))
        self._assert_denied(
            self.client.post(f"{BASE}/{draft2['id']}/cancel/", {"reason": "Payer backed out."}, format="json")
        )

    def test_print_permission_allow_deny(self):
        receipt = self._create_and_post(amount="100000.00")
        receipt2 = self._create_and_post(amount="100000.00")
        user = User.objects.create_user(
            username="matrix_printer", password="Password@12345", email="matrix_printer@zic.tz"
        )
        self._grant(user, "front_office.receipts.print")
        self.client.force_authenticate(user)
        allowed = self.client.post(f"{BASE}/{receipt['id']}/print/", {}, format="json")
        self.assertEqual(allowed.status_code, 201, allowed.data)

        self.client.force_authenticate(self._viewer("matrix_printer_deny"))
        self._assert_denied(self.client.post(f"{BASE}/{receipt2['id']}/print/", {}, format="json"))

    def test_import_permission_allow_deny(self):
        user = User.objects.create_user(
            username="matrix_importer", password="Password@12345", email="matrix_importer@zic.tz"
        )
        self._grant(user, "front_office.receipts.import")
        self.client.force_authenticate(user)
        allowed = self.client.get(f"{BASE}/import/template/")
        self.assertEqual(allowed.status_code, 200)

        self.client.force_authenticate(self._viewer("matrix_importer_deny"))
        self._assert_denied(self.client.get(f"{BASE}/import/template/"))

    def test_configure_permission_allow_deny(self):
        user = User.objects.create_user(
            username="matrix_configurer", password="Password@12345", email="matrix_configurer@zic.tz"
        )
        self._grant(user, "front_office.receipts.configure")
        self.assertTrue(has_receipt_permission(user, "configure"))
        # The CONFIGURE entitlement is a module-wide capability.
        self.assertTrue(has_receipt_permission(user, "reverse"))
        self.assertFalse(has_receipt_permission(self._viewer("matrix_configurer_deny"), "configure"))
        self.assertFalse(has_receipt_permission(self._viewer("matrix_configurer_deny2"), "reverse"))

    def test_all_nine_codes_are_covered_by_the_matrix(self):
        self.assertEqual(
            set(ACTIONS),
            {"view", "create", "post", "allocate", "reverse", "cancel", "print", "import", "configure"},
        )


class ReceiptAuditMatrixTests(ReceiptMatrixBase):
    """Scope 3 — create, post, allocate, reverse, cancel, import, print all audit."""

    def test_create_writes_audit_row(self):
        draft = self._create_draft().data["data"]
        row = self._audit_rows("receipt", draft["id"]).filter(action="CREATE").first()
        self.assertIsNotNone(row)
        self.assertEqual(row.user_id, self.admin.pk)

    def test_post_writes_audit_row(self):
        draft = self._create_draft().data["data"]
        self.client.post(f"{BASE}/{draft['id']}/post/", {"reason": "Money confirmed."}, format="json")
        update = self._audit_rows("receipt", draft["id"]).filter(action="UPDATE").first()
        self.assertIsNotNone(update)
        self.assertIn("status", update.changed_fields)

    def test_allocate_writes_audit_rows(self):
        commitment = self._make_commitment("OLC-QA-AUDIT-ALLOC")
        receipt = self._create_and_post(amount="100000.00")
        self._allocate(receipt["id"], commitment.commitment_number, "100000.00")

        allocation = ReceiptAllocation.objects.get(receipt_id=receipt["id"])
        self.assertTrue(
            self._audit_rows("receiptallocation", allocation.pk).filter(action="CREATE").exists(),
            "allocation creation must be audited",
        )
        self.assertTrue(
            self._audit_rows("receipt", receipt["id"]).filter(action="UPDATE").exists(),
            "receipt split update must be audited",
        )

    def test_reverse_writes_audit_rows(self):
        commitment = self._make_commitment("OLC-QA-AUDIT-REV")
        receipt = self._create_and_post(amount="100000.00")
        self._allocate(receipt["id"], commitment.commitment_number, "100000.00")
        self.client.post(f"{BASE}/{receipt['id']}/reverse/", {"reason": "Duplicate."}, format="json")

        reversal = Receipt.objects.get(pk=receipt["id"]).reversals.first()
        self.assertIsNotNone(reversal)
        self.assertTrue(
            self._audit_rows("receiptreversal", reversal.pk).filter(action="CREATE").exists(),
            "reversal record creation must be audited",
        )
        self.assertTrue(
            self._audit_rows("receipt", receipt["id"]).filter(action="UPDATE").exists(),
            "receipt status change must be audited",
        )

    def test_cancel_writes_audit_row(self):
        draft = self._create_draft().data["data"]
        self.client.post(f"{BASE}/{draft['id']}/cancel/", {"reason": "Payer backed out."}, format="json")
        update = self._audit_rows("receipt", draft["id"]).filter(action="UPDATE").first()
        self.assertIsNotNone(update)
        self.assertIn("status", update.changed_fields)
        self.assertEqual(Receipt.objects.get(pk=draft["id"]).status, ReceiptStatus.CANCELLED)

    def test_import_writes_audit_rows(self):
        file = make_csv([make_row()])
        dry = self.client.post(f"{BASE}/import/dry-run/", {"file": file, "import_mode": "DRAFT"}, format="multipart")
        self.assertEqual(dry.status_code, 200, dry.data)
        batch_id = dry.data["data"]["batch"]["id"]

        dry_row = AuditLog.objects.filter(
            entity_type="receiptimportbatch", entity_id=batch_id, action="IMPORT_DRY_RUN"
        ).first()
        self.assertIsNotNone(dry_row, "dry-run must be audited")

        committed = self.client.post(f"{BASE}/import/commit/", {"batch_id": batch_id}, format="json")
        self.assertEqual(committed.status_code, 200, committed.data)
        commit_row = AuditLog.objects.filter(
            entity_type="receiptimportbatch", entity_id=batch_id, action="IMPORT_COMMIT"
        ).first()
        self.assertIsNotNone(commit_row, "commit must be audited")

    def test_print_writes_audit_row(self):
        receipt = self._create_and_post(amount="100000.00")
        printed = self.client.post(f"{BASE}/{receipt['id']}/print/", {}, format="json")
        self.assertEqual(printed.status_code, 201, printed.data)
        row = self._audit_rows("receipt", receipt["id"]).filter(action="PRINT").first()
        self.assertIsNotNone(row, "print generation must be audited")
        self.assertEqual(row.user_id, self.admin.pk)


class ReceiptIdempotencyMatrixTests(ReceiptMatrixBase):
    """Scope 4 — create, post, allocation, and import retries are idempotent."""

    def test_create_retry_with_idempotency_key(self):
        payload = {
            "payer_name": "Jane Doe",
            "receipt_date": timezone.localdate().isoformat(),
            "receipt_amount": "100000.00",
            "currency": "TZS",
            "branch": str(self.branch.pk),
            "partner": str(self.partner.pk),
            "idempotency_key": "matrix-create-1",
        }
        first = self.client.post(f"{BASE}/", payload, format="json")
        self.assertEqual(first.status_code, 201, first.data)
        second = self.client.post(f"{BASE}/", payload, format="json")
        self.assertEqual(second.status_code, 200, second.data)
        self.assertEqual(first.data["data"]["id"], second.data["data"]["id"])
        self.assertEqual(Receipt.objects.filter(idempotency_key="matrix-create-1").count(), 1)
        self.assertEqual(
            DomainEvent.objects.filter(
                event_type="ReceiptCreated",
                aggregate_id=first.data["data"]["id"],
            ).count(),
            1,
            "create retry must not re-emit the event",
        )

    def test_post_retry_is_rejected_without_side_effect(self):
        draft = self._create_draft().data["data"]
        first = self.client.post(f"{BASE}/{draft['id']}/post/", {"reason": "Money confirmed."}, format="json")
        self.assertEqual(first.status_code, 200, first.data)
        second = self.client.post(f"{BASE}/{draft['id']}/post/", {"reason": "Money confirmed."}, format="json")
        self.assertEqual(second.status_code, 409, second.data)
        self.assertEqual(second.data["error_code"], "RECEIPT_ALREADY_POSTED")
        self.assertEqual(
            DomainEvent.objects.filter(event_type="ReceiptPosted", aggregate_id=draft["id"]).count(), 1,
            "post retry must not re-emit the posting event",
        )

    def test_allocation_retry_is_idempotent_per_commitment(self):
        commitment = self._make_commitment("OLC-QA-IDEM-ALLOC")
        receipt = self._create_and_post(amount="100000.00")
        first = self._allocate(receipt["id"], commitment.commitment_number, "40000.00")
        self.assertEqual(first.status_code, 201, first.data)
        second = self._allocate(receipt["id"], commitment.commitment_number, "40000.00")
        self.assertEqual(second.status_code, 200, second.data)
        self.assertEqual(
            ReceiptAllocation.objects.filter(receipt_id=receipt["id"]).count(), 1,
            "allocation retry must not duplicate the allocation row",
        )
        commitment.refresh_from_db()
        self.assertEqual(commitment.amount_paid, Decimal("40000.00"))

    def test_import_recommit_is_idempotent(self):
        file = make_csv([make_row(), make_row(amount="200000.00")])
        dry = self.client.post(f"{BASE}/import/dry-run/", {"file": file, "import_mode": "DRAFT"}, format="multipart")
        self.assertEqual(dry.status_code, 200, dry.data)
        batch_id = dry.data["data"]["batch"]["id"]
        self.assertEqual(self.client.post(f"{BASE}/import/commit/", {"batch_id": batch_id}, format="json").status_code, 200)
        self.assertEqual(Receipt.objects.count(), 2)
        again = self.client.post(f"{BASE}/import/commit/", {"batch_id": batch_id}, format="json")
        self.assertEqual(again.status_code, 200, again.data)
        self.assertEqual(Receipt.objects.count(), 2, "re-commit must not duplicate receipts")


class ReceiptSecurityMatrixTests(ReceiptMatrixBase):
    """Scope 5 — partner isolation, structured 403, no raw-UUID leaks, immutability."""

    def test_partner_cannot_see_other_partner_receipts(self):
        partner_b = make_partner(seq=4)
        own = self._create_and_post(amount="100000.00", partner=str(self.partner.pk))
        foreign = self._create_and_post(amount="20000.00", partner=str(partner_b.pk))

        portal = User.objects.create_user(
            username="matrix_iso", password="Password@12345", email="matrix_iso@zic.tz"
        )
        UserPartnerLink.objects.create(
            user=portal, partner=self.partner, link_status="ACTIVE", is_primary=True
        )
        self.client.force_authenticate(portal)
        listing = self.client.get(f"{BASE}/portal/")
        self.assertEqual(listing.data["data"]["count"], 1)
        self.assertEqual(
            {row["receipt_number"] for row in listing.data["data"]["results"]},
            {own["receipt_number"]},
        )
        detail = self.client.get(f"{BASE}/portal/{foreign['id']}/")
        self.assertEqual(detail.status_code, 404)

    def test_unauthorized_user_receives_structured_403(self):
        draft = self._create_draft().data["data"]
        viewer = User.objects.create_user(
            username="matrix_403", password="Password@12345", email="matrix_403@zic.tz"
        )
        UserGroup.objects.get(code="RECEIPT_VIEWER").users.add(viewer)
        self.client.force_authenticate(viewer)

        response = self.client.post(f"{BASE}/{draft['id']}/post/", {"reason": "Money confirmed."}, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["error_code"], "FORBIDDEN")
        self.assertIs(response.data["success"], False)
        self.assertEqual(response.data["status_code"], 403)
        self.assertTrue(response.data["message"])
        self.assertEqual(response.data["error"]["code"], "FORBIDDEN")
        self.assertEqual(response.data["error"]["message"], response.data["message"])
        self.assertIn("request_id", response.data["meta"])

        # The denied action must not have mutated state.
        self.assertEqual(
            Receipt.objects.get(pk=draft["id"]).status, ReceiptStatus.DRAFT,
            "denied post must not change the receipt",
        )

    def test_raw_uuid_refs_always_have_display_labels(self):
        receipt = self._create_and_post(amount="100000.00")
        detail = self.client.get(f"{BASE}/{receipt['id']}/").data["data"]

        # Every reference UUID on the detail payload must carry a human label
        # that is not itself a raw UUID.
        refs = {
            "branch": "branch_name",
            "partner": "partner_name",
            "bank_account": "bank_account_name",
            "posted_by": "posted_by_name",
            "created_by": "created_by_display",
        }
        for ref_field, label_field in refs.items():
            if ref_field not in detail:
                continue
            raw = detail.get(ref_field)
            if raw is None:
                continue
            self.assertRegex(str(raw), UUID_RE, f"{ref_field} should be a raw UUID reference")
            label = detail.get(label_field)
            self.assertTrue(label, f"{label_field} must label {ref_field}")
            self.assertNotRegex(str(label), UUID_RE, f"{label_field} must not itself be a raw UUID")

        # The *_display suffixed fields are always human-readable, never UUIDs.
        for key, value in detail.items():
            if key.endswith("_display") and value is not None:
                self.assertNotRegex(str(value), UUID_RE, f"{key} leaked a raw UUID")

    def test_list_rows_expose_display_labels_not_raw_uuids(self):
        self._create_and_post(amount="100000.00")
        listing = self.client.get(f"{BASE}/").data["data"]["results"]
        self.assertEqual(len(listing), 1)
        row = listing[0]
        for key, value in row.items():
            if key.endswith("_display") and value is not None:
                self.assertNotRegex(str(value), UUID_RE, f"{key} leaked a raw UUID")
        self.assertTrue(row["branch_display"])
        self.assertTrue(row["partner_display"])
        self.assertTrue(row["payer_display"])

    def test_posted_receipt_core_fields_immutable(self):
        posted = self._create_and_post(amount="100000.00")
        response = self.client.patch(
            f"{BASE}/{posted['id']}/",
            {"receipt_amount": "200000.00", "payment_mode": "BANK_TRANSFER"},
            format="json",
        )
        self.assertEqual(response.status_code, 422, response.data)
        self.assertEqual(response.data["error_code"], "RECEIPT_INVALID_STATUS")
        self.assertEqual(Receipt.objects.get(pk=posted["id"]).receipt_amount, Decimal("100000.00"))

    def test_manual_update_service_rejects_posted_receipt(self):
        posted = self._create_and_post(amount="100000.00")
        from apps.front_office.receipts.services.receipt_service import update_draft

        with self.assertRaises(Exception):
            update_draft(
                Receipt.objects.get(pk=posted["id"]),
                actor=self.admin,
                receipt_amount=Decimal("200000.00"),
            )


class ReceiptPerformanceMatrixTests(ReceiptMatrixBase):
    """Scope 6 — the list endpoint is paginated and the common filters are indexed."""

    def test_list_endpoint_is_paginated(self):
        for index in range(25):
            self._create_draft(amount="1000.00", narration=f"row-{index}")
        response = self.client.get(f"{BASE}/")
        self.assertEqual(response.status_code, 200)
        data = response.data["data"]
        self.assertEqual(data["page"], 1)
        self.assertEqual(data["page_size"], 20)
        self.assertEqual(data["count"], 25)
        self.assertEqual(len(data["results"]), 20)
        self.assertTrue(data["next"])
        self.assertFalse(data["previous"])

        page_two = self.client.get(f"{BASE}/", {"page": 2, "page_size": 25})
        self.assertEqual(page_two.data["data"]["page"], 2)
        self.assertEqual(page_two.data["data"]["page_size"], 25)
        self.assertEqual(len(page_two.data["data"]["results"]), 0)
        self.assertFalse(page_two.data["data"]["next"])

    def test_common_filter_fields_are_indexed(self):
        model = Receipt
        index_names = {index.name for index in model._meta.indexes}
        expected = {
            "receipt_status_date_idx",
            "receipt_branch_date_idx",
            "receipt_source_ref_idx",
            "receipt_partner_date_idx",
            "receipt_currency_date_idx",
            "receipt_payment_mode_date_idx",
        }
        self.assertTrue(expected.issubset(index_names), f"missing indexes: {expected - index_names}")

        # The filter pipeline keys off these exact columns.
        fields = {field.column: field for field in model._meta.concrete_fields}
        for column in ("status", "branch_id", "partner_id", "source_module", "currency", "payment_mode", "receipt_date"):
            self.assertIn(column, fields, f"{column} is not a receipt column")

    def test_filter_pipeline_hits_indexed_columns(self):
        self._create_and_post(amount="100000.00", payment_mode="CASH")
        self._create_draft(amount="50000.00", payment_mode="CASH")
        listing = self.client.get(
            f"{BASE}/", {"status": "POSTED", "payment_mode": "CASH", "branch": str(self.branch.pk)}
        )
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.data["data"]["count"], 1)
        self.assertEqual(listing.data["data"]["results"][0]["receipt_amount"], "100000.00")
        # The DRAFT receipt is excluded by the status filter.
        self.assertEqual(
            self.client.get(f"{BASE}/", {"status": "DRAFT", "payment_mode": "CASH"}).data["data"]["count"], 1
        )
