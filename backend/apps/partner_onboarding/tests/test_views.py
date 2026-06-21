from datetime import date

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.users.models import User
from apps.partners.models import Partner
from apps.partner_onboarding.models import (
    PartnerApplication,
    PartnerApplicationDocument,
    PartnerApplicationTask,
)


def create_test_user(**kwargs):
    defaults = {
        "email": "test@example.com",
        "username": "testuser",
        "password": "TestPassword123!",
        "first_name": "Test",
        "last_name": "User",
    }
    defaults.update(kwargs)
    return User.objects.create_user(**defaults)


def create_admin_user(**kwargs):
    defaults = {
        "email": "admin@example.com",
        "username": "adminuser",
        "password": "AdminPassword123!",
        "first_name": "Admin",
        "last_name": "User",
        "is_superuser": True,
    }
    defaults.update(kwargs)
    return User.objects.create_user(**defaults)


def create_individual_app(user, **overrides):
    defaults = {
        "partner_type": "INDIVIDUAL",
        "identification_type": "NIN",
        "identification_number": "NIN12345",
        "first_name": "John",
        "surname": "Doe",
        "gender": "MALE",
        "date_of_birth": date(1990, 5, 15),
        "nationality": "Tanzanian",
        "email": "john@example.com",
        "mobile_number": "+255700000001",
    }
    defaults.update(overrides)
    from apps.partner_onboarding.services import ApplicationService
    app_num = ApplicationService.generate_application_number(defaults.get("partner_type"))
    return PartnerApplication.objects.create(
        application_number=app_num,
        submitted_by=user,
        **defaults,
    )


def add_document(application, user):
    return PartnerApplicationDocument.objects.create(
        application=application,
        document_type="NID",
        document_name="national_id.pdf",
        file="partner_documents/test.pdf",
        uploaded_by=user,
    )


class PartnerApplicationListViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = create_test_user()
        self.client.force_authenticate(user=self.user)

    def test_list_applications(self):
        create_individual_app(self.user)
        url = reverse("v1:partner-applications-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])
        self.assertIn("data", response.data)

    def test_unauthenticated_list_rejected(self):
        self.client.force_authenticate(user=None)
        url = reverse("v1:partner-applications-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 401)


class PartnerApplicationCreateViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = create_test_user()
        self.client.force_authenticate(user=self.user)

    def test_create_individual_draft(self):
        url = reverse("v1:partner-applications-list")
        data = {
            "partner_type": "INDIVIDUAL",
            "first_name": "Alice",
            "surname": "Brown",
            "email": "alice@example.com",
            "mobile_number": "+255700000010",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"]["status"], "ACTIVE")

    def test_create_corporate_draft(self):
        url = reverse("v1:partner-applications-list")
        data = {
            "partner_type": "CORPORATE",
            "company_name": "Test Corp",
            "email": "test@corp.com",
            "mobile_number": "+255700000011",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["data"]["status"], "ACTIVE")


class PartnerApplicationRetrieveViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = create_test_user()
        self.client.force_authenticate(user=self.user)
        self.app = create_individual_app(self.user)

    def test_retrieve_application(self):
        url = reverse("v1:partner-applications-detail", args=[self.app.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])
        self.assertIn("documents", response.data["data"])
        self.assertIn("tasks", response.data["data"])


class PartnerApplicationUpdateViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = create_test_user()
        self.client.force_authenticate(user=self.user)
        self.app = create_individual_app(self.user)

    def test_update_draft(self):
        url = reverse("v1:partner-applications-detail", args=[self.app.id])
        data = {"first_name": "Updated"}
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])
        self.app.refresh_from_db()
        self.assertEqual(self.app.first_name, "Updated")

    def test_update_non_draft_fails(self):
        self.app.status = "SUBMITTED"
        self.app.save()
        url = reverse("v1:partner-applications-detail", args=[self.app.id])
        data = {"first_name": "Updated"}
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, 400)


class PartnerApplicationDestroyViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = create_test_user()
        self.client.force_authenticate(user=self.user)
        self.app = create_individual_app(self.user)

    def test_destroy_draft(self):
        url = reverse("v1:partner-applications-detail", args=[self.app.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 204)
        self.assertFalse(PartnerApplication.objects.filter(id=self.app.id).exists())

    def test_destroy_non_draft_fails(self):
        self.app.status = "SUBMITTED"
        self.app.save()
        url = reverse("v1:partner-applications-detail", args=[self.app.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 400)


class PartnerApplicationSubmitViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = create_test_user()
        self.client.force_authenticate(user=self.user)

    def test_submit_complete_application(self):
        app = create_individual_app(self.user)
        add_document(app, self.user)
        url = reverse("v1:partner-applications-submit", args=[app.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])
        app.refresh_from_db()
        self.assertEqual(app.status, "SUBMITTED")

    def test_submit_without_documents_succeeds(self):
        app = create_individual_app(self.user)
        url = reverse("v1:partner-applications-submit", args=[app.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])


class PartnerApplicationWorkflowViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = create_admin_user()
        self.client.force_authenticate(user=self.admin)

    def test_start_review(self):
        app = create_individual_app(self.admin)
        add_document(app, self.admin)
        from apps.partner_onboarding.services import ApplicationService
        ApplicationService.submit(app, self.admin)
        url = reverse("v1:partner-applications-start-review", args=[app.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        app.refresh_from_db()
        self.assertEqual(app.status, "UNDER_REVIEW")

    def test_request_documents(self):
        app = create_individual_app(self.admin)
        add_document(app, self.admin)
        from apps.partner_onboarding.services import ApplicationService
        ApplicationService.submit(app, self.admin)
        ApplicationService.start_review(app, self.admin)
        url = reverse("v1:partner-applications-request-documents", args=[app.id])
        data = {"requested_documents": ["TIN Certificate", "Business License"]}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 200)
        app.refresh_from_db()
        self.assertEqual(app.status, "PENDING_DOCUMENTS")
        self.assertEqual(app.tasks.count(), 2)

    def test_send_to_compliance(self):
        app = create_individual_app(self.admin)
        add_document(app, self.admin)
        from apps.partner_onboarding.services import ApplicationService
        ApplicationService.submit(app, self.admin)
        ApplicationService.start_review(app, self.admin)
        url = reverse("v1:partner-applications-send-to-compliance", args=[app.id])
        data = {"notes": "Sending to compliance for review"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 200)
        app.refresh_from_db()
        self.assertEqual(app.status, "COMPLIANCE_CHECK")

    def test_approve(self):
        app = create_individual_app(self.admin)
        add_document(app, self.admin)
        from apps.partner_onboarding.services import ApplicationService
        ApplicationService.submit(app, self.admin)
        ApplicationService.start_review(app, self.admin)
        ApplicationService.send_to_compliance(app, self.admin)
        url = reverse("v1:partner-applications-approve", args=[app.id])
        data = {"notes": "All checks passed"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 200)
        app.refresh_from_db()
        self.assertEqual(app.status, "APPROVED")

    def test_reject(self):
        app = create_individual_app(self.admin)
        add_document(app, self.admin)
        from apps.partner_onboarding.services import ApplicationService
        ApplicationService.submit(app, self.admin)
        ApplicationService.start_review(app, self.admin)
        ApplicationService.send_to_compliance(app, self.admin)
        url = reverse("v1:partner-applications-reject", args=[app.id])
        data = {"reason": "Incomplete documentation", "notes": "Missing TIN"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 200)
        app.refresh_from_db()
        self.assertEqual(app.status, "REJECTED")

    def test_suspend(self):
        app = create_individual_app(self.admin)
        add_document(app, self.admin)
        from apps.partner_onboarding.services import ApplicationService
        ApplicationService.submit(app, self.admin)
        ApplicationService.start_review(app, self.admin)
        ApplicationService.send_to_compliance(app, self.admin)
        url = reverse("v1:partner-applications-suspend", args=[app.id])
        data = {"notes": "Awaiting additional information"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 200)
        app.refresh_from_db()
        self.assertEqual(app.status, "SUSPENDED")

    def test_convert(self):
        app = create_individual_app(self.admin)
        add_document(app, self.admin)
        from apps.partner_onboarding.services import ApplicationService
        ApplicationService.submit(app, self.admin)
        ApplicationService.start_review(app, self.admin)
        ApplicationService.send_to_compliance(app, self.admin)
        ApplicationService.approve(app, self.admin)
        url = reverse("v1:partner-applications-convert", args=[app.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        app.refresh_from_db()
        self.assertEqual(app.status, "CONVERTED")
        self.assertTrue(
            Partner.objects.filter(
                created_from_application=app
            ).exists()
        )

    def test_run_compliance(self):
        app = create_individual_app(self.admin, political_risk="HIGH", aml_risk="HIGH")
        add_document(app, self.admin)
        from apps.partner_onboarding.services import ApplicationService
        ApplicationService.submit(app, self.admin)
        ApplicationService.start_review(app, self.admin)
        ApplicationService.send_to_compliance(app, self.admin)
        url = reverse("v1:partner-applications-run-compliance", args=[app.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("risk_score", response.data["data"])
        self.assertIn("is_high_risk", response.data["data"])


class PartnerApplicationDocumentViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = create_test_user()
        self.client.force_authenticate(user=self.user)
        self.app = create_individual_app(self.user)

    def test_list_documents(self):
        add_document(self.app, self.user)
        url = reverse("v1:application-documents", args=[self.app.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["data"]), 1)

    def test_upload_document(self):
        url = reverse("v1:application-documents", args=[self.app.id])
        pdf_file = SimpleUploadedFile(
            "test.pdf", b"%PDF-1.4 content",
            content_type="application/pdf",
        )
        data = {
            "document_type": "NID",
            "document_name": "national_id.pdf",
            "file": pdf_file,
        }
        response = self.client.post(url, data, format="multipart")
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data["success"])

    def test_verify_document(self):
        doc = add_document(self.app, self.user)
        admin = create_admin_user()
        self.client.force_authenticate(user=admin)
        url = reverse("v1:application-document-verify", args=[self.app.id, doc.id])
        data = {"verification_notes": "Document verified"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 200)
        doc.refresh_from_db()
        self.assertTrue(doc.is_verified)


class PartnerApplicationTaskViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = create_test_user()
        self.client.force_authenticate(user=self.user)
        self.app = create_individual_app(self.user)

    def test_list_tasks(self):
        PartnerApplicationTask.objects.create(
            application=self.app,
            task_type="REVIEW",
            title="Initial Review",
        )
        url = reverse("v1:application-tasks", args=[self.app.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["data"]), 1)

    def test_create_task(self):
        url = reverse("v1:application-tasks", args=[self.app.id])
        data = {
            "task_type": "DOCUMENT_REQUEST",
            "title": "Upload TIN",
            "description": "Please provide TIN certificate",
            "priority": "HIGH",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data["success"])

    def test_complete_task(self):
        task = PartnerApplicationTask.objects.create(
            application=self.app,
            task_type="REVIEW",
            title="Review application",
        )
        url = reverse("v1:application-task-complete", args=[self.app.id, task.id])
        data = {"notes": "Task completed"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 200)
        task.refresh_from_db()
        self.assertEqual(task.status, "COMPLETED")
        self.assertEqual(task.completed_by, self.user)
