from datetime import timedelta
from django.test import TestCase
from django.utils import timezone

from apps.partner_onboarding.models import PartnerApplication
from apps.partner_onboarding.tasks import (
    send_application_notification,
    notify_reviewers,
    run_compliance_check,
    cleanup_expired_drafts,
    send_pending_document_reminders,
    generate_compliance_report,
)


class TaskTests(TestCase):
    def setUp(self):
        """Create test applications."""
        from apps.users.models import User
        self.user = User.objects.create_user(
            email="test@example.com",
            username="testuser",
            password="testpass123",
            first_name="Test",
            last_name="User",
        )

        self.application = PartnerApplication.objects.create(
            application_number="APP-2026-001",
            partner_type="INDIVIDUAL",
            first_name="John",
            surname="Doe",
            email="john@example.com",
            mobile_number="+255700000000",
            status="DRAFT",
            submitted_by=self.user,
        )

    def test_send_application_notification_success(self):
        """Test sending notification for application status change."""
        result = send_application_notification(str(self.application.pk), "submitted")

        self.assertTrue(result["success"])
        self.assertEqual(result["application_number"], "APP-2026-001")
        self.assertEqual(result["notification_type"], "submitted")

    def test_send_application_notification_not_found(self):
        """Test notification for non-existent application."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        result = send_application_notification(fake_id, "submitted")

        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "Application not found")

    def test_notify_reviewers_success(self):
        """Test notifying reviewers about new application."""
        result = notify_reviewers(str(self.application.pk))

        self.assertTrue(result["success"])
        self.assertEqual(result["application_number"], "APP-2026-001")
        self.assertEqual(result["submitted_by"], "test@example.com")

    def test_notify_reviewers_not_found(self):
        """Test notifying reviewers for non-existent application."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        result = notify_reviewers(fake_id)

        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "Application not found")

    def test_run_compliance_check_success(self):
        """Test running compliance check on application."""
        self.application.political_risk = "LOW"
        self.application.aml_risk = "LOW"
        self.application.save()

        result = run_compliance_check(str(self.application.pk))

        self.assertTrue(result["success"])
        self.assertEqual(result["application_number"], "APP-2026-001")
        self.assertIn("risk_score", result)
        self.assertIn("is_flagged", result)
        self.assertEqual(result["risk_score"], 0)
        self.assertFalse(result["is_flagged"]["is_high_risk"])

    def test_run_compliance_check_high_risk(self):
        """Test compliance check flags high-risk application."""
        self.application.political_risk = "HIGH"
        self.application.aml_risk = "HIGH"
        self.application.save()

        result = run_compliance_check(str(self.application.pk))

        self.assertTrue(result["success"])
        self.assertGreaterEqual(result["risk_score"], 50)
        self.assertTrue(result["is_flagged"])

    def test_run_compliance_check_not_found(self):
        """Test compliance check for non-existent application."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        result = run_compliance_check(fake_id)

        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "Application not found")

    def test_cleanup_expired_drafts(self):
        """Test cleanup of old draft applications."""
        from datetime import timedelta
        from django.utils import timezone

        old_app = PartnerApplication.objects.create(
            application_number="APP-2026-002",
            partner_type="INDIVIDUAL",
            first_name="Old",
            surname="Draft",
            email="old@example.com",
            mobile_number="+255700000001",
            status="DRAFT",
            submitted_by=self.user,
        )
        PartnerApplication.objects.filter(pk=old_app.pk).update(
            created_at=timezone.now() - timedelta(days=31)
        )

        count = cleanup_expired_drafts()

        self.assertEqual(count, 1)
        self.assertFalse(
            PartnerApplication.objects.filter(pk=old_app.pk).exists()
        )
        self.assertTrue(
            PartnerApplication.objects.filter(pk=self.application.pk).exists()
        )

    def test_cleanup_expired_drafts_no_expired(self):
        """Test cleanup when no drafts are expired."""
        count = cleanup_expired_drafts()
        self.assertEqual(count, 0)

    def test_send_pending_document_reminders(self):
        """Test sending reminders for pending documents."""
        from datetime import timedelta
        from django.utils import timezone

        PartnerApplication.objects.filter(pk=self.application.pk).update(
            status="PENDING_DOCUMENTS",
            updated_at=timezone.now() - timedelta(days=8),
        )

        count = send_pending_document_reminders()

        self.assertEqual(count, 1)

    def test_send_pending_document_reminders_recent(self):
        """Test no reminders for recent pending applications."""
        self.application.status = "PENDING_DOCUMENTS"
        self.application.save()

        count = send_pending_document_reminders()

        self.assertEqual(count, 0)

    def test_generate_compliance_report(self):
        """Test weekly compliance report generation."""
        self.application.status = "SUBMITTED"
        self.application.submitted_at = timezone.now() - timedelta(days=3)
        self.application.save()

        result = generate_compliance_report()

        self.assertIn("submitted", result)
        self.assertIn("approved", result)
        self.assertIn("rejected", result)
        self.assertIn("converted", result)
        self.assertEqual(result["submitted"], 1)
