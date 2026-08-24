from datetime import date

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import override_settings
from rest_framework.test import APITestCase

from apps.common.models import DomainEvent
from apps.front_office.receipts.models import Receipt, ReceiptStatus, ReceiptStatusHistory
from apps.governance.models import AuditLog
from apps.partner_onboarding.models import Branch
from apps.partners.models import Partner, PartnerBankAccount

User = get_user_model()

BASE = "/api/v1/front-office/receipts"


def make_partner(seq=1, **overrides):
    defaults = {
        "partner_number": f"PN{seq:04d}",
        "partner_type": "INDIVIDUAL",
        "party_type": "INDIVIDUAL",
        "first_name": "Jane",
        "surname": "Doe",
        "email": f"jane{seq}@zic.tz",
        "mobile_number": f"2557000000{seq}",
    }
    defaults.update(overrides)
    return Partner.objects.create(**defaults)


class ReceiptPostingApiTests(APITestCase):
    def setUp(self):
        call_command("seed_receipt_parameters")
        self.admin = User.objects.create_superuser(
            username="post_admin", password="Password@12345", email="post_admin@zic.tz"
        )
        self.plain = User.objects.create_user(
            username="post_plain", password="Password@12345", email="post_plain@zic.tz"
        )
        self.client.force_authenticate(self.admin)
        self.branch = Branch.objects.create(code="DAR", name="Dar es Salaam")
        self.partner = make_partner()

    def _create_draft(self, **overrides):
        payload = {
            "payer_name": "Jane Doe",
            "receipt_date": date(2026, 8, 24).isoformat(),
            "receipt_amount": "100000.00",
            "currency": "TZS",
            "branch": str(self.branch.pk),
            "partner": str(self.partner.pk),
        }
        payload.update(overrides)
        return self.client.post(f"{BASE}/", payload, format="json")

    def _post(self, receipt_id, **overrides):
        payload = {"reason": "Money confirmed."}
        payload.update(overrides)
        return self.client.post(f"{BASE}/{receipt_id}/post/", payload, format="json")

    def test_create_draft_has_no_number_until_posted(self):
        response = self._create_draft()
        self.assertEqual(response.status_code, 201)
        data = response.data["data"]
        self.assertEqual(data["status"], ReceiptStatus.DRAFT)
        self.assertIsNone(data["receipt_number"])

    def test_edit_draft_updates_editable_fields(self):
        created = self._create_draft().data["data"]
        response = self.client.patch(
            f"{BASE}/{created['id']}/",
            {
                "narration": "Payer will deposit cash today.",
                "receipt_amount": "150000.00",
                "payment_reference": "",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.data["data"]
        self.assertEqual(data["narration"], "Payer will deposit cash today.")
        self.assertEqual(data["receipt_amount"], "150000.00")
        self.assertEqual(data["status"], ReceiptStatus.DRAFT)

    def test_post_assigns_number_and_sets_posted_fields(self):
        created = self._create_draft().data["data"]
        response = self._post(created["id"])
        self.assertEqual(response.status_code, 200)
        data = response.data["data"]
        self.assertRegex(data["receipt_number"], r"^RCT-\d{4}-\d{6}$")
        self.assertEqual(data["status"], ReceiptStatus.POSTED)
        self.assertIsNotNone(data["posted_at"])
        self.assertEqual(data["posted_by"], self.admin.pk)
        self.assertEqual(data["posted_by_display"], "post_admin")

    def test_post_response_includes_display_fields(self):
        created = self._create_draft().data["data"]
        data = self._post(created["id"]).data["data"]
        self.assertEqual(data["branch_display"], "Dar es Salaam")
        self.assertEqual(data["partner_display"], str(self.partner))
        self.assertEqual(data["currency_display"], "TZS")
        self.assertEqual(data["payment_mode_display"], "Cash")
        self.assertEqual(data["created_by_display"], "post_admin")
        self.assertEqual(data["posted_by_display"], "post_admin")

    def test_post_twice_returns_409_already_posted(self):
        created = self._create_draft().data["data"]
        self._post(created["id"])
        second = self._post(created["id"])
        self.assertEqual(second.status_code, 409)
        self.assertEqual(second.data["error_code"], "RECEIPT_ALREADY_POSTED")

    def test_posted_receipt_core_fields_immutable(self):
        created = self._create_draft().data["data"]
        self._post(created["id"])
        response = self.client.patch(
            f"{BASE}/{created['id']}/",
            {"receipt_amount": "200000.00", "payment_mode": "BANK_TRANSFER"},
            format="json",
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.data["error_code"], "RECEIPT_INVALID_STATUS")

    def test_missing_payment_reference_blocked_when_mode_requires_it(self):
        created = self._create_draft(payment_mode="BANK_TRANSFER").data["data"]
        response = self._post(created["id"])
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.data["error_code"], "RECEIPT_PAYMENT_REFERENCE_REQUIRED")
        self.assertIn("payment_reference", response.data["field_errors"])

    def test_bank_transfer_with_reference_and_bank_account_succeeds(self):
        account = PartnerBankAccount.objects.create(
            partner=self.partner,
            bank_name="CRDB Bank PLC",
            account_name="Jane Doe",
            account_number="015031929999",
        )
        created = self._create_draft(
            payment_mode="BANK_TRANSFER",
            payment_reference="TXN-987654",
            bank_account=str(account.pk),
        ).data["data"]
        response = self._post(created["id"])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["status"], ReceiptStatus.POSTED)
        self.assertEqual(response.data["data"]["bank_account_display"], str(account))

    def test_post_rejects_inactive_branch(self):
        inactive = Branch.objects.create(code="ZNZ", name="Zanzibar", is_active=False)
        created = self._create_draft(branch=str(inactive.pk)).data["data"]
        response = self._post(created["id"])
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.data["error_code"], "RECEIPT_PARAMETER_MISSING")
        self.assertEqual(
            response.data["error"]["details"]["navigation_path"],
            "System Parameters > Branches",
        )

    def test_post_rejects_inactive_partner(self):
        inactive = make_partner(seq=9, is_active=False)
        created = self._create_draft(partner=str(inactive.pk)).data["data"]
        response = self._post(created["id"])
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.data["error_code"], "RECEIPT_PARAMETER_MISSING")
        self.assertEqual(
            response.data["error"]["details"]["navigation_path"],
            "Partners > Partner Records",
        )

    def test_post_rejects_unconfigured_payment_mode(self):
        created = self._create_draft(payment_mode="OTHER").data["data"]
        response = self._post(created["id"])
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.data["error_code"], "RECEIPT_PARAMETER_MISSING")
        self.assertEqual(
            response.data["error"]["details"]["navigation_path"],
            "System Parameters > Payment Modes",
        )

    def test_post_rejects_amount_below_payment_mode_minimum(self):
        created = self._create_draft(receipt_amount="500.00").data["data"]  # CASH minimum is 1000.00
        response = self._post(created["id"])
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.data["error_code"], "RECEIPT_AMOUNT_INVALID")
        self.assertIn("receipt_amount", response.data["field_errors"])

    def test_create_idempotency_header_returns_same_receipt(self):
        payload = {
            "payer_name": "Jane Doe",
            "receipt_date": date(2026, 8, 24).isoformat(),
            "receipt_amount": "100000.00",
            "currency": "TZS",
        }
        first = self.client.post(f"{BASE}/", payload, format="json", HTTP_X_IDEMPOTENCY_KEY="idem-header-1")
        second = self.client.post(f"{BASE}/", payload, format="json", HTTP_X_IDEMPOTENCY_KEY="idem-header-1")
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.data["data"]["id"], second.data["data"]["id"])
        self.assertEqual(Receipt.objects.count(), 1)

    def test_post_requires_post_permission(self):
        created = self._create_draft().data["data"]
        self.client.force_authenticate(self.plain)
        response = self._post(created["id"])
        self.assertEqual(response.status_code, 403)

    def test_post_emits_event_audit_and_status_history(self):
        created = self._create_draft().data["data"]
        self._post(created["id"])
        receipt = Receipt.objects.get(pk=created["id"])

        event = DomainEvent.objects.get(event_type="ReceiptPosted", aggregate_id=created["id"])
        self.assertEqual(event.payload["receipt_number"], receipt.receipt_number)
        self.assertEqual(event.payload["from_status"], "DRAFT")
        self.assertEqual(event.payload["to_status"], "POSTED")
        self.assertEqual(event.payload["actor_id"], str(self.admin.pk))

        history = ReceiptStatusHistory.objects.get(receipt=receipt, to_status="POSTED")
        self.assertEqual(history.from_status, "DRAFT")
        self.assertEqual(history.changed_by_id, self.admin.pk)

        update_row = (
            AuditLog.objects.filter(entity_type="receipt", entity_id=receipt.pk, action_type="UPDATE")
            .order_by("timestamp")
            .last()
        )
        self.assertIsNotNone(update_row, "posting must write an UPDATE audit row")
        self.assertIn("status", update_row.changed_fields)
        self.assertIn("posted_at", update_row.changed_fields)

    @override_settings(
        STORAGES={
            "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
            "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
        }
    )
    def test_admin_action_posts_draft_with_reason(self):
        created = self._create_draft().data["data"]
        self.client.force_login(self.admin)
        changelist = "/admin/front_office/receipt/"

        first = self.client.post(
            changelist,
            {"action": "post_draft_receipt", "_selected_action": [created["id"]], "index": "0"},
            follow=True,
        )
        self.assertEqual(first.status_code, 200)
        self.assertContains(first, "Post selected draft receipts")

        second = self.client.post(
            changelist,
            {
                "action": "post_draft_receipt",
                "_selected_action": [created["id"]],
                "index": "0",
                "apply": "1",
                "reason": "Admin confirmed the cash deposit.",
            },
            follow=True,
        )
        self.assertEqual(second.status_code, 200)
        receipt = Receipt.objects.get(pk=created["id"])
        self.assertEqual(receipt.status, ReceiptStatus.POSTED)
        self.assertEqual(receipt.posted_by_id, self.admin.pk)

        history = ReceiptStatusHistory.objects.get(receipt=receipt, to_status="POSTED")
        self.assertIn("Admin confirmed the cash deposit.", history.reason)
