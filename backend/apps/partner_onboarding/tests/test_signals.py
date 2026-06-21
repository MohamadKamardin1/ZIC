from unittest.mock import patch, MagicMock
from django.test import TestCase

from apps.partner_onboarding.models import PartnerApplication, PartnerApplicationDocument
from apps.partner_onboarding.signals import (
    track_status_change,
    handle_application_status_change,
    log_document_upload,
)


class SignalTests(TestCase):
    def setUp(self):
        from apps.users.models import User
        self.user = User.objects.create_user(
            email="test@example.com",
            username="testuser",
            password="testpass123",
            first_name="Test",
            last_name="User",
        )
        self.application = PartnerApplication.objects.create(
            application_number="APP-SIG-001",
            partner_type="INDIVIDUAL",
            first_name="John",
            surname="Doe",
            email="john@example.com",
            mobile_number="+255700000000",
            status="DRAFT",
            submitted_by=self.user,
        )

    def test_track_status_change_on_new_application(self):
        new_app = PartnerApplication(
            application_number="APP-SIG-002",
            partner_type="INDIVIDUAL",
            first_name="Jane",
            surname="Smith",
            email="jane@example.com",
            mobile_number="+255700000001",
            status="DRAFT",
            submitted_by=self.user,
        )
        track_status_change(PartnerApplication, new_app)
        self.assertIsNone(new_app._old_status)

    def test_track_status_change_on_existing_application(self):
        track_status_change(PartnerApplication, self.application)
        self.assertEqual(self.application._old_status, "DRAFT")

    @patch("apps.partner_onboarding.tasks.notify_reviewers.delay")
    def test_handle_status_change_to_submitted(self, mock_delay):
        self.application._old_status = "DRAFT"
        self.application.status = "SUBMITTED"
        handle_application_status_change(
            PartnerApplication, self.application, created=False
        )
        mock_delay.assert_called_once_with(str(self.application.pk))

    @patch("apps.partner_onboarding.tasks.run_compliance_check.delay")
    def test_handle_status_change_to_compliance_check(self, mock_delay):
        self.application._old_status = "UNDER_REVIEW"
        self.application.status = "COMPLIANCE_CHECK"
        handle_application_status_change(
            PartnerApplication, self.application, created=False
        )
        mock_delay.assert_called_once_with(str(self.application.pk))

    @patch("apps.partner_onboarding.tasks.send_application_notification.delay")
    def test_handle_status_change_to_approved(self, mock_delay):
        self.application._old_status = "COMPLIANCE_CHECK"
        self.application.status = "APPROVED"
        handle_application_status_change(
            PartnerApplication, self.application, created=False
        )
        mock_delay.assert_called_once_with(str(self.application.pk), "approved")

    @patch("apps.partner_onboarding.tasks.send_application_notification.delay")
    def test_handle_status_change_to_rejected(self, mock_delay):
        self.application._old_status = "COMPLIANCE_CHECK"
        self.application.status = "REJECTED"
        handle_application_status_change(
            PartnerApplication, self.application, created=False
        )
        mock_delay.assert_called_once_with(str(self.application.pk), "rejected")

    @patch("apps.partner_onboarding.tasks.send_application_notification.delay")
    def test_handle_status_change_to_suspended(self, mock_delay):
        self.application._old_status = "COMPLIANCE_CHECK"
        self.application.status = "SUSPENDED"
        handle_application_status_change(
            PartnerApplication, self.application, created=False
        )
        mock_delay.assert_called_once_with(str(self.application.pk), "suspended")

    @patch("apps.partner_onboarding.tasks.send_application_notification.delay")
    def test_handle_status_change_to_converted(self, mock_delay):
        self.application._old_status = "APPROVED"
        self.application.status = "CONVERTED"
        handle_application_status_change(
            PartnerApplication, self.application, created=False
        )
        mock_delay.assert_called_once_with(str(self.application.pk), "converted")

    def test_handle_status_change_no_change(self):
        self.application._old_status = "DRAFT"
        self.application.status = "DRAFT"
        with patch("apps.partner_onboarding.tasks.notify_reviewers.delay") as mock_delay:
            handle_application_status_change(
                PartnerApplication, self.application, created=False
            )
            mock_delay.assert_not_called()

    def test_handle_status_change_on_creation(self):
        self.application._old_status = None
        with patch("apps.partner_onboarding.tasks.notify_reviewers.delay") as mock_delay:
            handle_application_status_change(
                PartnerApplication, self.application, created=True
            )
            mock_delay.assert_not_called()

    def test_log_document_upload(self):
        document = PartnerApplicationDocument.objects.create(
            application=self.application,
            document_type="NID",
            document_name="National ID",
            file="documents/test.pdf",
            file_size=1024,
            mime_type="application/pdf",
            uploaded_by=self.user,
        )
        with patch("apps.partner_onboarding.signals.logger") as mock_logger:
            log_document_upload(PartnerApplicationDocument, document, created=True)
            mock_logger.info.assert_called_once()
