from datetime import date

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.front_office.receipts.models import Receipt

User = get_user_model()

BASE = "/api/v1/front-office/receipts"


class ReceiptApiTests(APITestCase):
    def setUp(self):
        call_command("seed_receipt_parameters")
        self.admin = User.objects.create_superuser(
            username="receipt_admin", password="Password@12345", email="receipt_admin@zic.tz"
        )
        self.plain = User.objects.create_user(
            username="receipt_plain", password="Password@12345", email="receipt_plain@zic.tz"
        )

    def _create(self, **overrides):
        payload = {
            "payer_name": "Jane Doe",
            "receipt_date": date(2026, 8, 24).isoformat(),
            "receipt_amount": "100000.00",
            "currency": "TZS",
        }
        payload.update(overrides)
        return self.client.post(f"{BASE}/", payload, format="json")

    def test_superuser_list_create_retrieve_update(self):
        self.client.force_authenticate(self.admin)

        create_response = self._create(narration="First premium deposit.")
        self.assertEqual(create_response.status_code, 201)
        data = create_response.data["data"]
        self.assertIsNone(data["receipt_number"])
        self.assertEqual(data["status"], "DRAFT")
        self.assertEqual(data["unallocated_amount"], "100000.00")
        self.assertIn("update", data["allowed_actions"])
        receipt_id = data["id"]

        update_response = self.client.patch(
            f"{BASE}/{receipt_id}/", {"narration": "Client confirmed deposit."}, format="json"
        )
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.data["data"]["narration"], "Client confirmed deposit.")

        post_response = self.client.post(f"{BASE}/{receipt_id}/post/", {"reason": "Money confirmed."}, format="json")
        self.assertEqual(post_response.status_code, 200)
        posted = post_response.data["data"]
        self.assertTrue(posted["receipt_number"])
        self.assertEqual(posted["status"], "POSTED")
        self.assertEqual(posted["posted_by_display"], "receipt_admin")

        list_response = self.client.get(f"{BASE}/")
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.data["data"]["count"], 1)
        self.assertEqual(list_response.data["data"]["results"][0]["receipt_number"], posted["receipt_number"])

        detail_response = self.client.get(f"{BASE}/{receipt_id}/")
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(detail_response.data["data"]["payer_name"], "Jane Doe")
        self.assertEqual(detail_response.data["data"]["payment_mode_label"], "Cash")
        self.assertEqual(detail_response.data["data"]["currency_display"], "TZS")
        self.assertEqual(detail_response.data["data"]["payment_mode_display"], "Cash")

    def test_create_with_nonpositive_amount_fails(self):
        self.client.force_authenticate(self.admin)
        response = self._create(receipt_amount="0")
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.data["error_code"], "RECEIPT_AMOUNT_INVALID")
        self.assertEqual(response.data["field_errors"]["receipt_amount"][0], "Amount must be greater than zero.")

    def test_update_posted_receipt_is_rejected(self):
        self.client.force_authenticate(self.admin)
        created = self._create()
        receipt = Receipt.objects.get(pk=created.data["data"]["id"])
        receipt.posted_at = timezone.now()
        receipt.save()

        response = self.client.patch(f"{BASE}/{receipt.pk}/", {"narration": "Too late."}, format="json")
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.data["error_code"], "RECEIPT_INVALID_STATUS")

    def test_unauthenticated_request_is_forbidden(self):
        response = self.client.get(f"{BASE}/")
        self.assertEqual(response.status_code, 401)
        # Teachable Error Coach envelope: a resolution step explains how to authenticate.
        self.assertFalse(response.data["success"])
        self.assertIn("resolution_steps", response.data)
        self.assertTrue(response.data["resolution_steps"])
        self.assertIn("resolutionSteps", response.data)

    def test_plain_user_without_permission_is_forbidden(self):
        self.client.force_authenticate(self.plain)
        response = self.client.get(f"{BASE}/")
        self.assertEqual(response.status_code, 403)
        self.assertFalse(response.data["success"])

    def test_list_filters_and_pagination(self):
        self.client.force_authenticate(self.admin)
        self._create(payer_name="Jane Doe", currency="TZS")
        self._create(payer_name="John Smith", currency="USD", receipt_amount="250000.00")

        filtered = self.client.get(f"{BASE}/", {"currency": "USD"})
        self.assertEqual(filtered.data["data"]["count"], 1)
        self.assertEqual(filtered.data["data"]["results"][0]["payer_name"], "John Smith")

        unallocated = self.client.get(f"{BASE}/", {"unallocated_only": "true"})
        self.assertEqual(unallocated.data["data"]["count"], 2)

    def test_options_endpoint_returns_parameterized_catalogs(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get(f"{BASE}/options/")
        self.assertEqual(response.status_code, 200)
        data = response.data["data"]
        status_values = {entry["value"] for entry in data["receipt_statuses"]}
        self.assertIn("DRAFT", status_values)
        currency_values = {entry["value"] for entry in data["currencies"]}
        self.assertIn("TZS", currency_values)
        mode_values = {entry["value"] for entry in data["payment_modes"]}
        self.assertIn("CASH", mode_values)
