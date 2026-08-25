"""Prompt 9 — bulk receipt import: CSV template, safe idempotent dry-run/commit.

Covers template generation, per-row validation that explains every field error,
duplicate detection, commit that creates (and optionally posts/allocates)
receipts, idempotent re-commit, partial-failure behavior with reprocessing, and
the row-level error payload contract.
"""

import csv
import io
from datetime import date

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from rest_framework.test import APITestCase

from apps.front_office.receipts.models import (
    Receipt,
    ReceiptImportBatch,
    ReceiptImportBatchStatus,
    ReceiptImportRow,
    ReceiptImportRowStatus,
    ReceiptStatus,
)
from apps.front_office.receipts.services.import_service import IMPORT_COLUMNS
from apps.ol_commitments.models import OLCommitment, OLCommitmentAllocation
from apps.ol_parameters.models import OLCommitmentStatus
from apps.partner_onboarding.models import Branch
from apps.partners.models import Partner
from apps.users.models import UserGroup

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


def make_partner(seq=1):
    return Partner.objects.create(
        partner_number=f"PRT{seq:04d}",
        partner_type="INDIVIDUAL",
        party_type="INDIVIDUAL",
        first_name="Jane",
        surname="Doe",
        email=f"import{seq}@zic.tz",
        mobile_number=f"2557009999{seq}",
        is_active=True,
        status="ACTIVE",
    )


def make_csv(rows, columns=None):
    columns = columns or IMPORT_COLUMNS
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=columns)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return SimpleUploadedFile("receipts.csv", buf.getvalue().encode("utf-8"), content_type="text/csv")


def make_row(**overrides):
    base = {
        "receipt_date": "2026-08-20",
        "branch_code": "DAR",
        "payer_partner_number": "PRT0001",
        "currency_code": "TZS",
        "payment_mode_code": "CASH",
        "amount": "100000.00",
        "payment_reference": "",
        "source_module": "MANUAL",
        "target_commitment_number": "",
        "narration": "Bulk import test",
    }
    base.update(overrides)
    return base


class ReceiptImportApiTests(APITestCase):
    def setUp(self):
        call_command("seed_receipt_parameters")
        call_command("seed_receipt_permissions")
        seed_commitment_statuses()
        self.admin = User.objects.create_superuser(
            username="import_admin", password="Password@12345", email="import_admin@zic.tz"
        )
        self.handler = User.objects.create_user(
            username="import_handler", password="Password@12345", email="import_handler@zic.tz"
        )
        UserGroup.objects.get(code="RECEIPT_HANDLER").users.add(self.handler)
        self.viewer = User.objects.create_user(
            username="import_viewer", password="Password@12345", email="import_viewer@zic.tz"
        )
        UserGroup.objects.get(code="RECEIPT_VIEWER").users.add(self.viewer)
        self.client.force_authenticate(self.admin)
        self.branch = Branch.objects.create(code="DAR", name="Dar es Salaam")
        self.branch_aru = Branch.objects.create(code="ARU", name="Arusha")
        self.partner = make_partner()
        self.commitment = OLCommitment.objects.create(
            commitment_number="OLC-PRT-0001",
            source_type="MANUAL",
            currency="TZS",
            due_date=date(2026, 9, 1),
            premium_amount="100000.00",
            status="PENDING",
            partner=self.partner,
            partner_name_snapshot=str(self.partner),
            source_channel="API",
        )

    def _dry_run(self, rows, import_mode="DRAFT", columns=None):
        file = make_csv(rows, columns=columns)
        return self.client.post(
            f"{BASE}/import/dry-run/", {"file": file, "import_mode": import_mode}, format="multipart"
        )

    def _commit(self, batch_id):
        return self.client.post(f"{BASE}/import/commit/", {"batch_id": batch_id}, format="json")

    # --- CSV template --------------------------------------------------------

    def test_csv_template_generation(self):
        response = self.client.get(f"{BASE}/import/template/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn("filename=\"receipt_import_template.csv\"", response["Content-Disposition"])

        content = response.content.decode("utf-8")
        reader = csv.DictReader(io.StringIO(content))
        self.assertEqual(reader.fieldnames, IMPORT_COLUMNS)

    # --- dry-run -------------------------------------------------------------

    def test_dry_run_valid_rows_explain_no_errors(self):
        response = self._dry_run(
            [make_row(narration="First payment"), make_row(amount="200000.00", narration="Second payment")]
        )
        self.assertEqual(response.status_code, 200, response.data)
        data = response.data["data"]
        batch = ReceiptImportBatch.objects.get(pk=data["batch"]["id"])
        self.assertEqual(batch.status, ReceiptImportBatchStatus.VALIDATED)
        self.assertEqual(batch.valid_rows, 2)
        self.assertEqual(batch.invalid_rows, 0)
        self.assertEqual(Receipt.objects.count(), 0, "dry-run must not create receipts")
        self.assertEqual([row["status"] for row in data["rows"]], ["VALID", "VALID"])
        self.assertTrue(all(row["error_code"] is None for row in data["rows"]))

    def test_dry_run_invalid_rows_explain_every_field_error(self):
        rows = [
            make_row(receipt_date="not-a-date"),
            make_row(branch_code="XXX"),
            make_row(payer_partner_number="NOPE"),
            make_row(currency_code="ZZZ"),
            make_row(payment_mode_code="FOO"),
            make_row(amount="0"),
            make_row(source_module="OL_PROPOSAL"),
            make_row(target_commitment_number="NOPE"),
        ]
        response = self._dry_run(rows)
        self.assertEqual(response.status_code, 200, response.data)
        data = response.data["data"]
        self.assertEqual(data["summary"]["valid"], 0)
        self.assertEqual(data["summary"]["invalid"], 8)
        self.assertEqual(Receipt.objects.count(), 0)

        errors_by_row = {row["row_number"]: row["errors"] for row in data["rows"]}
        self.assertEqual(errors_by_row[1], {"receipt_date": ["'not-a-date' is not a valid date. Use YYYY-MM-DD."]})
        self.assertIn("XXX", errors_by_row[2]["branch_code"][0])
        self.assertIn("NOPE", errors_by_row[3]["payer_partner_number"][0])
        self.assertIn("ZZZ", errors_by_row[4]["currency_code"][0])
        self.assertIn("FOO", errors_by_row[5]["payment_mode_code"][0])
        self.assertIn("greater than zero", errors_by_row[6]["amount"][0])
        self.assertIn("MANUAL", errors_by_row[7]["source_module"][0])
        self.assertIn("NOPE", errors_by_row[8]["target_commitment_number"][0])
        self.assertTrue(all(row["error_code"] == "RECEIPT_IMPORT_ROW_INVALID" for row in data["rows"]))

    def test_dry_run_post_mode_enforces_payment_rule(self):
        response = self._dry_run(
            [make_row(payment_mode_code="BANK_TRANSFER")], import_mode="POST"
        )
        self.assertEqual(response.status_code, 200, response.data)
        row = response.data["data"]["rows"][0]
        self.assertEqual(row["status"], "INVALID")
        self.assertIn("payment_reference", row["errors"])
        self.assertIn("payment_mode_code", row["errors"])

    def test_dry_run_detects_duplicate_rows(self):
        response = self._dry_run([make_row(), make_row()])
        self.assertEqual(response.status_code, 200, response.data)
        data = response.data["data"]
        self.assertEqual(data["summary"]["invalid"], 1)
        rows = sorted(data["rows"], key=lambda r: r["row_number"])
        self.assertEqual(rows[0]["status"], "VALID")
        self.assertEqual(rows[1]["status"], "DUPLICATE")
        self.assertEqual(rows[1]["error_code"], "RECEIPT_IMPORT_DUPLICATE")
        self.assertIn("Duplicate row", rows[1]["errors"]["__row__"][0])

    def test_dry_run_requires_a_file(self):
        response = self.client.post(f"{BASE}/import/dry-run/", {"import_mode": "DRAFT"}, format="multipart")
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.data["error_code"], "RECEIPT_IMPORT_ROW_INVALID")
        self.assertIn("file", response.data["field_errors"])

    # --- commit --------------------------------------------------------------

    def test_commit_creates_draft_receipts(self):
        response = self._dry_run(
            [make_row(narration="First"), make_row(amount="200000.00", narration="Second")]
        )
        batch_id = response.data["data"]["batch"]["id"]

        committed = self._commit(batch_id)
        self.assertEqual(committed.status_code, 200, committed.data)
        data = committed.data["data"]
        self.assertEqual(data["status"], ReceiptImportBatchStatus.COMMITTED)
        self.assertEqual(data["summary"]["committed"], 2)
        self.assertFalse(data["partial_failure"])

        receipts = Receipt.objects.order_by("receipt_amount")
        self.assertEqual(receipts.count(), 2)
        self.assertTrue(all(r.status == ReceiptStatus.DRAFT for r in receipts))
        self.assertEqual(receipts[0].payer_name, self.partner.display_name)
        self.assertEqual(receipts[0].branch_name_snapshot, "Dar es Salaam")
        self.assertEqual(receipts[0].source_module, "MANUAL")
        self.assertEqual(receipts[0].source_reference_id.startswith("IMP-"), True)

        for row in data["rows"]:
            self.assertEqual(row["status"], "COMMITTED")
            self.assertIsNotNone(row["receipt_id"])
            self.assertIsNone(row["error_code"])

    def test_commit_post_mode_posts_receipts(self):
        response = self._dry_run([make_row()], import_mode="POST")
        batch_id = response.data["data"]["batch"]["id"]
        committed = self._commit(batch_id)
        self.assertEqual(committed.status_code, 200, committed.data)
        self.assertEqual(committed.data["data"]["summary"]["committed"], 1)

        receipt = Receipt.objects.get()
        self.assertEqual(receipt.status, ReceiptStatus.POSTED)
        self.assertTrue(receipt.receipt_number)
        self.assertIsNotNone(receipt.posted_at)

    def test_commit_allocate_mode_allocates_and_writes_commitment_ledger(self):
        response = self._dry_run(
            [make_row(amount="100000.00", target_commitment_number=self.commitment.commitment_number)],
            import_mode="ALLOCATE",
        )
        self.assertEqual(response.data["data"]["summary"]["valid"], 1, response.data)
        batch_id = response.data["data"]["batch"]["id"]

        committed = self._commit(batch_id)
        self.assertEqual(committed.status_code, 200, committed.data)
        receipt = Receipt.objects.get()
        self.assertEqual(receipt.status, ReceiptStatus.FULLY_ALLOCATED)
        self.commitment.refresh_from_db()
        self.assertEqual(str(self.commitment.balance), "0.00")
        self.assertTrue(
            OLCommitmentAllocation.objects.filter(commitment=self.commitment).exists(),
            "the commitments-side allocation ledger must be written",
        )

    def test_recommit_is_idempotent_and_does_not_duplicate(self):
        response = self._dry_run(
            [make_row(narration="First"), make_row(amount="200000.00", narration="Second")]
        )
        batch_id = response.data["data"]["batch"]["id"]
        self.assertEqual(self._commit(batch_id).status_code, 200)
        first_count = Receipt.objects.count()

        second = self._commit(batch_id)
        self.assertEqual(second.status_code, 200, second.data)
        self.assertEqual(Receipt.objects.count(), first_count, "re-commit must not duplicate receipts")
        self.assertEqual(second.data["data"]["summary"]["committed"], 2)
        self.assertEqual(
            ReceiptImportBatch.objects.get(pk=batch_id).status, ReceiptImportBatchStatus.COMMITTED
        )

    def test_partial_failure_and_safe_reprocessing(self):
        rows = [
            make_row(branch_code="DAR", amount="100000.00"),
            make_row(branch_code="ARU", amount="200000.00"),
        ]
        response = self._dry_run(rows, import_mode="POST")
        self.assertEqual(response.data["data"]["summary"]["valid"], 2, response.data)
        batch_id = response.data["data"]["batch"]["id"]

        # Deactivate one branch so its row fails at posting time.
        Branch.objects.filter(code="ARU").update(is_active=False)
        committed = self._commit(batch_id)
        self.assertEqual(committed.status_code, 200, committed.data)
        data = committed.data["data"]
        self.assertEqual(data["status"], ReceiptImportBatchStatus.PARTIAL)
        self.assertTrue(data["partial_failure"])
        self.assertEqual(data["error_code"], "RECEIPT_IMPORT_PARTIAL_FAILURE")
        self.assertEqual(data["summary"]["committed"], 1)
        self.assertEqual(data["summary"]["failed"], 1)
        self.assertEqual(Receipt.objects.count(), 1, "the failed row's draft must roll back")

        rows_by_number = {row["row_number"]: row for row in data["rows"]}
        self.assertEqual(rows_by_number[1]["status"], "COMMITTED")
        self.assertEqual(rows_by_number[2]["status"], "FAILED")
        self.assertEqual(rows_by_number[2]["error_code"], "RECEIPT_IMPORT_ROW_INVALID")
        self.assertIsNone(rows_by_number[2]["receipt_id"])
        self.assertIn("branch could not be resolved", rows_by_number[2]["message"])
        self.assertEqual(rows_by_number[2]["errors"], {"branch_code": ["Branch not found or inactive."]})

        # Fix the underlying cause and re-commit — only the failed row retries.
        Branch.objects.filter(code="ARU").update(is_active=True)
        retried = self._commit(batch_id)
        self.assertEqual(retried.status_code, 200, retried.data)
        retried_data = retried.data["data"]
        self.assertEqual(retried_data["status"], ReceiptImportBatchStatus.COMMITTED)
        self.assertEqual(retried_data["summary"]["committed"], 2)
        self.assertEqual(retried_data["summary"]["failed"], 0)
        self.assertEqual(Receipt.objects.count(), 2, "reprocessing must not duplicate committed rows")
        self.assertTrue(Receipt.objects.filter(branch=self.branch_aru).exists())

    def test_commit_rejects_unknown_batch(self):
        response = self._commit("00000000-0000-0000-0000-000000000001")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["error_code"], "RECEIPT_IMPORT_BATCH_NOT_FOUND")

    # --- payload contract & register ----------------------------------------

    def test_row_level_error_payload_shape(self):
        response = self._dry_run([make_row(branch_code="XXX"), make_row()])
        row = response.data["data"]["rows"][0]
        self.assertEqual(
            set(row),
            {"row_number", "status", "data", "error_code", "errors", "message", "receipt_id", "receipt_number", "committed_at"},
        )
        self.assertEqual(row["receipt_id"], None)
        self.assertEqual(row["receipt_number"], None)
        self.assertEqual(row["committed_at"], None)
        self.assertTrue(row["message"])

    def test_import_batches_register_list_and_detail(self):
        self._dry_run([make_row()])
        batch = ReceiptImportBatch.objects.get()

        listing = self.client.get(f"{BASE}/imports/")
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.data["data"]["count"], 1)
        self.assertEqual(listing.data["data"]["results"][0]["id"], str(batch.pk))

        detail = self.client.get(f"{BASE}/imports/{batch.pk}/")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(len(detail.data["data"]["rows"]), 1)
        self.assertEqual(detail.data["data"]["batch"]["batch_number"], batch.batch_number)

    # --- permissions ---------------------------------------------------------

    def test_import_permission_denied_for_handler_and_viewer(self):
        self.client.force_authenticate(self.handler)
        self.assertEqual(self.client.get(f"{BASE}/import/template/").status_code, 403)
        self.assertEqual(self._dry_run([make_row()]).status_code, 403)
        self.assertEqual(self._commit("00000000-0000-0000-0000-000000000001").status_code, 403)

        self.client.force_authenticate(self.viewer)
        self.assertEqual(self.client.get(f"{BASE}/import/template/").status_code, 403)
        self.assertEqual(self._dry_run([make_row()]).status_code, 403)

    def test_import_register_visible_to_handler(self):
        self._dry_run([make_row()])
        self.client.force_authenticate(self.handler)
        listing = self.client.get(f"{BASE}/imports/")
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.data["data"]["count"], 1)

    def test_import_rows_persist_validation_trail(self):
        response = self._dry_run([make_row(branch_code="XXX")])
        row = ReceiptImportRow.objects.get()
        self.assertEqual(row.status, ReceiptImportRowStatus.INVALID)
        self.assertEqual(row.error_code, "RECEIPT_IMPORT_ROW_INVALID")
        self.assertEqual(row.validation_errors, {"branch_code": ["Branch 'XXX' was not found or is inactive."]})
        self.assertEqual(row.error_message, "Branch 'XXX' was not found or is inactive.")
