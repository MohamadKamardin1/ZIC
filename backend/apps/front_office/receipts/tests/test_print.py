"""Prompt 8 — receipt printout generation, document integration, and signed download.

Covers the unified print/PDF pipeline for receipts: template registration
(``RECEIPT``), PDF generation with the required receipt blocks, pypdf text
extraction, reversal/cancellation watermarks, the print permission gate, the
DRAFT preview rule, the document register, and the authenticated signed-ticket
download with its audit trail.
"""

import io
from datetime import date

from django.contrib.auth import get_user_model
from django.core.files.storage import default_storage
from django.core.management import call_command
from pypdf import PdfReader
from rest_framework.test import APITestCase

from apps.front_office.receipts.errors import ReceiptError
from apps.front_office.receipts.models import Receipt, ReceiptDocument, ReceiptDocumentStatus
from apps.front_office.receipts.services.amount_in_words import amount_in_words
from apps.front_office.receipts.services.print_ticket import issue_download_ticket
from apps.governance.models import AuditLog
from apps.ol_commitments.models import OLCommitment
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
        email=f"print{seq}@zic.tz",
        mobile_number=f"2557009999{seq}",
        is_active=True,
        status="ACTIVE",
    )


def pdf_text(document):
    content = default_storage.open(document.file_reference, "rb").read()
    reader = PdfReader(io.BytesIO(content))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


class ReceiptPrintApiTests(APITestCase):
    def setUp(self):
        call_command("seed_receipt_parameters")
        call_command("seed_receipt_permissions")
        seed_commitment_statuses()
        self.admin = User.objects.create_superuser(
            username="print_admin", password="Password@12345", email="print_admin@zic.tz"
        )
        self.handler = User.objects.create_user(
            username="print_handler", password="Password@12345", email="print_handler@zic.tz"
        )
        UserGroup.objects.get(code="RECEIPT_HANDLER").users.add(self.handler)
        self.viewer = User.objects.create_user(
            username="print_viewer", password="Password@12345", email="print_viewer@zic.tz"
        )
        UserGroup.objects.get(code="RECEIPT_VIEWER").users.add(self.viewer)
        self.client.force_authenticate(self.admin)
        self.branch = Branch.objects.create(code="DAR", name="Dar es Salaam")
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

    def _create_draft(self, payer_name="Jane Doe", amount="100000.00", **overrides):
        payload = {
            "payer_name": payer_name,
            "receipt_date": date(2026, 8, 20).isoformat(),
            "receipt_amount": amount,
            "currency": "TZS",
            "payment_mode": "CASH",
            "branch": str(self.branch.pk),
            "partner": str(self.partner.pk),
        }
        payload.update(overrides)
        return self.client.post(f"{BASE}/", payload, format="json").data["data"]

    def _create_and_post(self, payer_name="Jane Doe", amount="100000.00", **overrides):
        created = self._create_draft(payer_name=payer_name, amount=amount, **overrides)
        posted = self.client.post(f"{BASE}/{created['id']}/post/", {"reason": "Money confirmed."}, format="json")
        self.assertEqual(posted.status_code, 200, posted.data)
        return posted.data["data"]

    def _allocate(self, receipt_id, target_id, amount):
        return self.client.post(
            f"{BASE}/{receipt_id}/allocate/",
            {"target_type": "OL_COMMITMENT", "target_id": target_id, "amount": str(amount)},
            format="json",
        )

    def _reverse(self, receipt_id, reason="Collected in error."):
        return self.client.post(f"{BASE}/{receipt_id}/reverse/", {"reason": reason}, format="json")

    def _print(self, receipt_id, **payload):
        return self.client.post(f"{BASE}/{receipt_id}/print/", payload, format="json")

    # --- PDF generation & document linkage ------------------------------------

    def test_receipt_pdf_generated_and_linked(self):
        receipt = self._create_and_post()
        response = self._print(receipt["id"])
        self.assertEqual(response.status_code, 201, response.data)
        data = response.data["data"]
        self.assertEqual(data["document_type"], "RECEIPT")
        self.assertEqual(data["status"], ReceiptDocumentStatus.GENERATED)

        document = ReceiptDocument.objects.get(pk=data["id"])
        self.assertEqual(str(document.receipt_id), receipt["id"])
        self.assertEqual(document.template_version, document.template.version)
        self.assertEqual((document.metadata or {})["template_code"], "RECEIPT")
        self.assertFalse((document.metadata or {})["preview"])
        self.assertEqual((document.metadata or {})["watermark"], "")
        self.assertTrue(default_storage.exists(document.file_reference))
        self.assertTrue(default_storage.exists(document.html_reference))
        self.assertIsNotNone(document.generated_by_id)
        self.assertIsNotNone(document.generated_at)
        self.assertIn("/api/v1/front-office/receipts/documents/", data["urls"]["pdf_url"])
        self.assertIn("ticket=", data["urls"]["pdf_url"])

    def test_pypdf_extraction_verifies_required_blocks(self):
        receipt = self._create_and_post()
        self._allocate(receipt["id"], self.commitment.commitment_number, "100000.00")
        data = self._print(receipt["id"]).data["data"]
        text = pdf_text(ReceiptDocument.objects.get(pk=data["id"]))

        self.assertIn("OFFICIAL RECEIPT", text)
        self.assertIn(receipt["receipt_number"], text)
        self.assertIn("Jane Doe", text)
        self.assertIn("Zanzibar Insurance Corporation", text)
        self.assertIn("Dar es Salaam", text)
        self.assertIn("100,000.00", text)
        self.assertIn("One Hundred Thousand", text)
        self.assertIn("Cash", text)
        self.assertIn(OLCommitment.objects.get(pk=self.commitment.pk).commitment_number, text)
        self.assertIn("Generated By", text)

    # --- watermarks -----------------------------------------------------------

    def test_reversed_receipt_prints_reversal_watermark(self):
        receipt = self._create_and_post()
        self._allocate(receipt["id"], self.commitment.commitment_number, "100000.00")
        reversed_data = self._reverse(receipt["id"], reason="Client requested refund.").data["data"]
        self.assertEqual(reversed_data["status"], "REVERSED")

        data = self._print(reversed_data["id"]).data["data"]
        self.assertEqual(data["watermark"], "REVERSED")
        text = pdf_text(ReceiptDocument.objects.get(pk=data["id"]))
        self.assertIn("REVERSED", text)

    def test_cancelled_receipt_prints_cancelled_watermark(self):
        draft = self._create_draft()
        cancelled = self.client.post(
            f"{BASE}/{draft['id']}/cancel/", {"reason": "Withdrawn by the payer."}, format="json"
        ).data["data"]
        self.assertEqual(cancelled["status"], "CANCELLED")

        data = self._print(cancelled["id"]).data["data"]
        self.assertEqual(data["watermark"], "CANCELLED")
        text = pdf_text(ReceiptDocument.objects.get(pk=data["id"]))
        self.assertIn("CANCELLED", text)

    def test_posted_official_receipt_has_no_watermark(self):
        receipt = self._create_and_post()
        data = self._print(receipt["id"]).data["data"]
        self.assertEqual(data["watermark"], "")
        text = pdf_text(ReceiptDocument.objects.get(pk=data["id"]))
        self.assertNotIn("REVERSED", text)
        self.assertNotIn("CANCELLED", text)

    # --- permission gate & preview rule ---------------------------------------

    def test_print_permission_denied_for_viewer(self):
        receipt = self._create_and_post()
        self.client.force_authenticate(self.viewer)
        response = self._print(receipt["id"])
        self.assertEqual(response.status_code, 403)

    def test_print_allowed_for_handler(self):
        receipt = self._create_and_post()
        self.client.force_authenticate(self.handler)
        response = self._print(receipt["id"])
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["data"]["document_type"], "RECEIPT")

    def test_draft_preview_rule(self):
        draft = self._create_draft()
        blocked = self._print(draft["id"])
        self.assertEqual(blocked.status_code, 422)
        self.assertEqual(blocked.data["error_code"], "RECEIPT_INVALID_STATUS")

        preview = self._print(draft["id"], preview=True)
        self.assertEqual(preview.status_code, 201, preview.data)
        document = ReceiptDocument.objects.get(pk=preview.data["data"]["id"])
        self.assertTrue((document.metadata or {})["preview"])

    # --- document register ----------------------------------------------------

    def test_documents_endpoint_lists_generated_document_with_template(self):
        receipt = self._create_and_post()
        self._print(receipt["id"])
        response = self.client.get(f"{BASE}/{receipt['id']}/documents/")
        self.assertEqual(response.status_code, 200)
        results = response.data["data"]["results"]
        self.assertEqual(len(results), 1)
        row = results[0]
        self.assertEqual(row["document_type"], "RECEIPT")
        self.assertEqual(row["template_code"], "RECEIPT")
        self.assertIsNotNone(row["template_version"])
        self.assertIn("ticket=", row["urls"]["pdf_url"])

    # --- signed ticket download & audit ---------------------------------------

    def test_signed_download_streams_pdf_and_audits(self):
        receipt = self._create_and_post()
        data = self._print(receipt["id"]).data["data"]
        pdf_url = data["urls"]["pdf_url"]

        response = self.client.get(pdf_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertTrue(response.content.startswith(b"%PDF"))

        audits = AuditLog.objects.filter(
            action_type="DOWNLOAD",
            entity_type="receipt",
            object_id=receipt["id"],
        )
        self.assertEqual(audits.count(), 1)
        self.assertEqual(audits.first().after_state.get("document_id"), data["id"])
        self.assertEqual(audits.first().after_state.get("template_version"), data["template_version"])

    def test_signed_download_rejects_wrong_user(self):
        receipt = self._create_and_post()
        data = self._print(receipt["id"]).data["data"]
        pdf_url = data["urls"]["pdf_url"]

        # A different user with the print permission cannot use the admin's ticket.
        self.client.force_authenticate(self.handler)
        response = self.client.get(pdf_url)
        self.assertEqual(response.status_code, 403)

    def test_signed_download_rejects_expired_ticket(self):
        receipt = self._create_and_post()
        data = self._print(receipt["id"]).data["data"]
        stale = issue_download_ticket(
            document_id=data["id"], user_id=self.admin.pk, ttl_seconds=-1
        )
        response = self.client.get(
            f"{BASE}/documents/{data['id']}/download/", {"ticket": stale}
        )
        self.assertEqual(response.status_code, 403)

    def test_download_missing_document_is_404(self):
        receipt = self._create_and_post()
        data = self._print(receipt["id"]).data["data"]
        other = Receipt.objects.create(
            payer_name="Ghost Payer",
            receipt_date=date(2026, 8, 20),
            receipt_amount="1000.00",
            currency="TZS",
            payment_mode="CASH",
        )
        other_doc = ReceiptDocument.objects.create(
            receipt=other,
            document_type="RECEIPT",
            file_reference="front_office_receipts/missing/nowhere.pdf",
            mime_type="application/pdf",
            status=ReceiptDocumentStatus.GENERATED,
        )
        ticket = issue_download_ticket(document_id=other_doc.pk, user_id=self.admin.pk)
        response = self.client.get(f"{BASE}/documents/{other_doc.pk}/download/", {"ticket": ticket})
        self.assertEqual(response.status_code, 404)

    # --- amount in words ------------------------------------------------------

    def test_amount_in_words(self):
        self.assertEqual(
            amount_in_words("100000.00", "TZS"),
            "One Hundred Thousand Tanzanian Shillings Only",
        )
        self.assertEqual(
            amount_in_words("100000.50", "TZS"),
            "One Hundred Thousand Tanzanian Shillings And Fifty Senti Only",
        )
        self.assertEqual(amount_in_words("0", "TZS"), "Zero Tanzanian Shillings Only")
        self.assertEqual(
            amount_in_words("1234567.89", "USD"),
            "One Million Two Hundred And Thirty Four Thousand Five Hundred And Sixty Seven United States Dollars And Eighty Nine Cents Only",
        )

    def test_validate_ticket_raises_structured_error_on_tampering(self):
        from apps.front_office.receipts.services.print_ticket import validate_download_ticket

        ticket = issue_download_ticket(document_id="00000000-0000-0000-0000-000000000001", user_id=self.admin.pk)
        with self.assertRaises(ReceiptError) as ctx:
            validate_download_ticket(ticket[:-2] + "zz", document_id="00000000-0000-0000-0000-000000000001", user_id=self.admin.pk)
        self.assertEqual(ctx.exception.error_code, "RECEIPT_TICKET_INVALID")
