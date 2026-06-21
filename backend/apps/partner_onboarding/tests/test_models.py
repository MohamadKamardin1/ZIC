import uuid
from datetime import date

from django.test import TestCase

from apps.users.models import User
from apps.partner_onboarding.models import (
    PartnerApplication,
    PartnerApplicationDocument,
    PartnerApplicationTask,
    APPLICATION_STATUS_CHOICES,
    DOCUMENT_TYPE_CHOICES,
    TASK_TYPE_CHOICES,
    TASK_STATUS_CHOICES,
    TASK_PRIORITY_CHOICES,
)


def create_test_user(email="test@example.com", username="testuser", **kwargs):
    return User.objects.create_user(
        email=email,
        username=username,
        password="TestPassword123!",
        first_name="Test",
        last_name="User",
        **kwargs,
    )


class PartnerApplicationModelTest(TestCase):
    def setUp(self):
        self.user = create_test_user()

    def test_create_individual_application(self):
        app = PartnerApplication.objects.create(
            application_number="PA-2026-000001",
            partner_type="INDIVIDUAL",
            first_name="John",
            surname="Doe",
            email="john@example.com",
            mobile_number="+255700000001",
            identification_type="NIN",
            identification_number="NIN12345",
            date_of_birth=date(1990, 5, 15),
            gender="MALE",
            nationality="Tanzanian",
            submitted_by=self.user,
        )
        self.assertEqual(app.status, "ACTIVE")
        self.assertEqual(str(app), "Application PA-2026-000001 - Active")
        self.assertEqual(app.display_name, "John Doe")
        self.assertIsInstance(app.id, uuid.UUID)

    def test_create_corporate_application(self):
        app = PartnerApplication.objects.create(
            application_number="PA-2026-000002",
            partner_type="CORPORATE",
            company_name="Acme Corp",
            tin_number="TIN-654321",
            incorporation_date=date(2020, 1, 1),
            industry="TECHNOLOGY",
            email="info@acme.co.tz",
            mobile_number="+255700000002",
            contact_person="Jane Smith",
            contact_person_phone="+255700000003",
            contact_person_email="jane@acme.co.tz",
            physical_address="Dar es Salaam",
            submitted_by=self.user,
        )
        self.assertEqual(app.display_name, "Acme Corp")
        self.assertEqual(app.status, "ACTIVE")

    def test_application_number_unique(self):
        PartnerApplication.objects.create(
            application_number="PA-2026-000010",
            partner_type="INDIVIDUAL",
            email="a@example.com",
            mobile_number="+255700000010",
            submitted_by=self.user,
        )
        with self.assertRaises(Exception):
            PartnerApplication.objects.create(
                application_number="PA-2026-000010",
                partner_type="INDIVIDUAL",
                email="b@example.com",
                mobile_number="+255700000011",
                submitted_by=self.user,
            )

    def test_db_table(self):
        self.assertEqual(
            PartnerApplication._meta.db_table,
            "onboarding_partner_application",
        )

    def test_ordering(self):
        self.assertEqual(PartnerApplication._meta.ordering, ["-created_at"])

    def test_previous_status_tracking(self):
        app = PartnerApplication.objects.create(
            application_number="PA-2026-000020",
            partner_type="INDIVIDUAL",
            email="track@example.com",
            mobile_number="+255700000020",
            submitted_by=self.user,
        )
        self.assertEqual(app.previous_status, "ACTIVE")
        app.status = "SUBMITTED"
        app.save()
        self.assertEqual(app.previous_status, "SUBMITTED")

    def test_status_choices_count(self):
        self.assertEqual(len(APPLICATION_STATUS_CHOICES), 10)

    def test_all_statuses_present(self):
        codes = [c[0] for c in APPLICATION_STATUS_CHOICES]
        for expected in [
            "ACTIVE", "DRAFT", "SUBMITTED", "UNDER_REVIEW", "PENDING_DOCUMENTS",
            "COMPLIANCE_CHECK", "APPROVED", "CONVERTED", "REJECTED", "SUSPENDED",
        ]:
            self.assertIn(expected, codes)


class PartnerApplicationDocumentModelTest(TestCase):
    def setUp(self):
        self.user = create_test_user()
        self.application = PartnerApplication.objects.create(
            application_number="PA-2026-000030",
            partner_type="INDIVIDUAL",
            email="doc@example.com",
            mobile_number="+255700000030",
            submitted_by=self.user,
        )

    def test_create_document(self):
        doc = PartnerApplicationDocument.objects.create(
            application=self.application,
            document_type="NID",
            document_name="national_id.pdf",
            file="partner_documents/2026/06/national_id.pdf",
            file_size=1024000,
            mime_type="application/pdf",
            uploaded_by=self.user,
        )
        self.assertEqual(str(doc), "National ID - national_id.pdf")
        self.assertFalse(doc.is_verified)
        self.assertIsNotNone(doc.id)

    def test_document_cascade_delete(self):
        PartnerApplicationDocument.objects.create(
            application=self.application,
            document_type="PASSPORT",
            document_name="passport.pdf",
            file="partner_documents/2026/06/passport.pdf",
            uploaded_by=self.user,
        )
        self.assertEqual(PartnerApplicationDocument.objects.count(), 1)
        self.application.delete()
        self.assertEqual(PartnerApplicationDocument.objects.count(), 0)

    def test_document_db_table(self):
        self.assertEqual(
            PartnerApplicationDocument._meta.db_table,
            "onboarding_partner_application_document",
        )

    def test_document_type_choices_count(self):
        self.assertEqual(len(DOCUMENT_TYPE_CHOICES), 12)


class PartnerApplicationTaskModelTest(TestCase):
    def setUp(self):
        self.user = create_test_user()
        self.application = PartnerApplication.objects.create(
            application_number="PA-2026-000040",
            partner_type="CORPORATE",
            company_name="Task Corp",
            email="task@example.com",
            mobile_number="+255700000040",
            submitted_by=self.user,
        )

    def test_create_task(self):
        task = PartnerApplicationTask.objects.create(
            application=self.application,
            task_type="DOCUMENT_REQUEST",
            title="Upload TIN Certificate",
            description="Please provide the TIN certificate",
            priority="HIGH",
        )
        self.assertEqual(str(task), "Document Request - Upload TIN Certificate")
        self.assertEqual(task.status, "PENDING")
        self.assertIsNotNone(task.id)

    def test_task_cascade_delete(self):
        PartnerApplicationTask.objects.create(
            application=self.application,
            task_type="REVIEW",
            title="Initial Review",
        )
        self.assertEqual(PartnerApplicationTask.objects.count(), 1)
        self.application.delete()
        self.assertEqual(PartnerApplicationTask.objects.count(), 0)

    def test_task_db_table(self):
        self.assertEqual(
            PartnerApplicationTask._meta.db_table,
            "onboarding_partner_application_task",
        )

    def test_task_type_choices(self):
        self.assertEqual(len(TASK_TYPE_CHOICES), 5)

    def test_task_status_choices(self):
        self.assertEqual(len(TASK_STATUS_CHOICES), 4)

    def test_task_priority_choices(self):
        self.assertEqual(len(TASK_PRIORITY_CHOICES), 4)
