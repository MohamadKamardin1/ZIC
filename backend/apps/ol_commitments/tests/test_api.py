from datetime import date, timedelta

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.ol_commitments.models import OLCommitment
from apps.ol_parameters.models import OLCommitmentStatus

User = get_user_model()


class CommitmentApiTests(APITestCase):
    def setUp(self):
        self.today = date.today()
        self.user = User.objects.create_superuser(username="api_admin", password="Password@12345", email="api_admin@zic.tz")
        self.operator = User.objects.create_user(username="api_operator", password="Password@12345", email="api_operator@zic.tz")
        for code, name, terminal in (
            ("PENDING", "Pending", False),
            ("PARTIALLY_PAID", "Partially Paid", False),
            ("COMPLETED", "Completed", True),
            ("CANCELLED", "Cancelled", True),
            ("OVERDUE", "Overdue", False),
        ):
            OLCommitmentStatus.objects.create(code=code, name=name, applies_to="COMMITMENT", display_order=10, is_terminal=terminal, is_active=True, effective_from=self.today - timedelta(days=365))
        self.commitment = OLCommitment.objects.create(
            commitment_number="OLC-API-0001",
            source_type="MANUAL",
            currency="TZS",
            due_date=self.today,
            premium_amount="100000.00",
            amount_paid="0.00",
            status="PENDING",
            source_channel="API",
        )
        self.base = "/api/v1/ol-commitments"

    def test_list_kpis_options_retrieve(self):
        self.client.force_authenticate(self.user)
        list_response = self.client.get(f"{self.base}/commitments/")
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.data["data"]["count"], 1)
        self.assertEqual(list_response.data["data"]["results"][0]["commitment_number"], "OLC-API-0001")

        kpis = self.client.get(f"{self.base}/commitments/kpis/")
        self.assertEqual(kpis.status_code, 200)
        self.assertEqual(float(kpis.data["data"]["total_outstanding"]), 100000.0)

        options = self.client.get(f"{self.base}/options/")
        self.assertEqual(options.status_code, 200)
        codes = {status["code"] for status in options.data["data"]["statuses"]}
        self.assertIn("PENDING", codes)
        self.assertIn("TZS", options.data["data"]["currencies"])

        detail = self.client.get(f"{self.base}/commitments/{self.commitment.pk}/")
        self.assertEqual(detail.status_code, 200)
        self.assertIn("record_payment", detail.data["data"]["allowed_actions"])

    def test_record_payment_partial_and_overpayment(self):
        self.client.force_authenticate(self.user)
        pay = self.client.post(
            f"{self.base}/commitments/{self.commitment.pk}/record_payment/",
            {"amount": "40000.00", "currency": "TZS", "payment_mode": "CASH", "receipt_reference": "RCT-API-1"},
            format="json",
        )
        self.assertEqual(pay.status_code, 200, pay.data)
        data = pay.data["data"]
        self.assertEqual(data["amount_paid"], "40000.00")
        self.assertEqual(data["balance"], "60000.00")

        over = self.client.post(
            f"{self.base}/commitments/{self.commitment.pk}/record_payment/",
            {"amount": "999999", "currency": "TZS", "payment_mode": "CASH", "receipt_reference": "RCT-API-2"},
            format="json",
        )
        self.assertEqual(over.status_code, 422)
        self.assertEqual(over.data["error_code"], "COMMITMENT_OVERPAYMENT")
        self.assertTrue(over.data["resolution_steps"])

    def test_cancel_lifecycle_and_invalid_transition(self):
        self.client.force_authenticate(self.user)
        cancel = self.client.post(
            f"{self.base}/commitments/{self.commitment.pk}/cancel/",
            {"reason": "Client surrendered the cover"},
            format="json",
        )
        self.assertEqual(cancel.status_code, 200, cancel.data)
        self.assertEqual(cancel.data["data"]["status"], "CANCELLED")

        # A cancelled commitment cannot be suspended.
        suspend = self.client.post(
            f"{self.base}/commitments/{self.commitment.pk}/suspend/",
            {"reason": "Trying again"},
            format="json",
        )
        self.assertEqual(suspend.status_code, 422)
        self.assertEqual(suspend.data["error_code"], "COMMITMENT_INVALID_TRANSITION")
        self.assertTrue(any("view" in step for step in suspend.data["resolution_steps"]))

    def test_permission_required(self):
        self.client.force_authenticate(self.operator)
        response = self.client.get(f"{self.base}/commitments/")
        self.assertIn(response.status_code, (401, 403))