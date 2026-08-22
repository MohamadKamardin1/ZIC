from datetime import date, timedelta

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.ol_commitments.models import OLCommitment
from apps.ol_parameters.models import OLCommitmentStatus, OLGracePeriod, OLGracePeriodNotificationSchedule

User = get_user_model()


class OverdueProcessingEndpointTests(APITestCase):
    def setUp(self):
        self.today = date.today()
        self.superuser = User.objects.create_superuser(
            username="overdue_admin",
            password="Password@12345",
            email="overdue_admin@zic.tz",
        )
        self.operator = User.objects.create_user(
            username="overdue_operator",
            password="Password@12345",
            email="overdue_operator@zic.tz",
        )
        OLCommitmentStatus.objects.create(
            code="PENDING", name="Pending", applies_to="COMMITMENT", display_order=10, is_active=True,
            effective_from=self.today - timedelta(days=365),
        )
        OLCommitmentStatus.objects.create(
            code="OVERDUE", name="Overdue", applies_to="COMMITMENT", display_order=20, is_active=True,
            effective_from=self.today - timedelta(days=365),
        )
        OLGracePeriod.objects.create(
            code="BATCH_GRACE",
            name="Batch grace",
            premium_frequency="MONTHLY",
            grace_days=5,
            warning_days=2,
            pre_lapse_days=1,
            lapse_days=10,
            effective_from=self.today - timedelta(days=365),
            is_active=True,
        )
        OLGracePeriodNotificationSchedule.objects.create(
            code="BATCH_NOTIFY",
            name="Batch notify",
            event_type="PREMIUM_DUE",
            days_offset=1,
            notification_channel="SYSTEM",
            recipient_type="POLICYHOLDER",
            effective_from=self.today - timedelta(days=365),
            is_active=True,
        )
        self.commitment = OLCommitment.objects.create(
            commitment_number="OLC-OVERDUE-0001",
            source_type="MANUAL",
            currency="TZS",
            due_date=self.today - timedelta(days=15),
            premium_amount="100000.00",
            amount_paid="0.00",
            status="PENDING",
            source_channel="API",
        )

        self.url = "/api/v1/ol-commitments/commitments/process-overdue/"

    def test_process_overdue_marks_flags_and_notifies(self):
        self.client.force_authenticate(self.superuser)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 200)
        data = response.data["data"]
        self.assertEqual(data["overdue"], 1)
        self.assertEqual(data["lapse_reviews"], 1)
        self.assertEqual(data["notified"], 1)
        self.assertEqual(data["processed"], 1)

        self.commitment.refresh_from_db()
        self.assertEqual(self.commitment.status, "OVERDUE")
        self.assertTrue(self.commitment.lapse_review_flag)

    def test_rerun_is_idempotent(self):
        self.client.force_authenticate(self.superuser)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 200)
        rerun = self.client.post(self.url)
        data = rerun.data["data"]
        self.assertEqual(data["overdue"], 0)
        self.assertEqual(data["lapse_reviews"], 0)
        self.assertEqual(data["notified"], 0)

    def test_process_overdue_requires_generate_permission(self):
        self.client.force_authenticate(self.operator)
        response = self.client.post(self.url)
        self.assertIn(response.status_code, (401, 403))