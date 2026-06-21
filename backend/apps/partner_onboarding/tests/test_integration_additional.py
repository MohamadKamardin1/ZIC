"""
Additional integration tests for edge cases, security, and specialized workflows.
Tests unauthorized access, document verification, task management, and compliance checks.
"""
import json
from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from apps.users.models import User
from apps.partners.models import Partner
from apps.partner_onboarding.models import (
    PartnerApplication,
    PartnerApplicationDocument,
    PartnerApplicationTask
)


def create_user(username, email, is_staff=False, is_superuser=False, user_type='PORTAL_USER'):
    return User.objects.create_user(
        username=username,
        email=email,
        password='testpass123',
        user_type=user_type,
        is_staff=is_staff,
        is_superuser=is_superuser,
    )


def create_draft_app(client, user, **overrides):
    """Helper to create a draft application and return its ID."""
    client.force_login(user)
    data = {
        'partner_type': 'INDIVIDUAL',
        'first_name': 'Test',
        'surname': 'User',
        'email': 'test.user@example.com',
        'mobile_number': '+255712345600',
        'gender': 'MALE',
        'date_of_birth': '1990-01-01',
        'nationality': 'Tanzanian',
        'identification_type': 'NIN',
        'identification_number': 'NID000000000',
        'physical_address': '100 Test Street',
    }
    data.update(overrides)
    response = client.post(
        reverse('v1:partner-applications-list'),
        data=json.dumps(data),
        content_type='application/json',
    )
    return response.json()['data']['id']


def upload_doc_and_submit(client, app_id):
    """Helper to upload a document and submit the application."""
    doc_data = {
        'document_type': 'NID',
        'document_name': 'National ID',
        'file': SimpleUploadedFile('nid.pdf', b'%PDF-1.4 content', content_type='application/pdf'),
    }
    client.post(
        reverse('v1:application-documents', kwargs={'application_pk': app_id}),
        data=doc_data,
        format='multipart',
    )
    client.post(
        reverse('v1:partner-applications-submit', args=[app_id]),
        content_type='application/json',
    )


class UnauthorizedAccessTest(TestCase):
    """Test that unauthorized users cannot perform restricted actions."""

    def setUp(self):
        self.client = Client()
        self.applicant = create_user('unauth_app', 'unauth.app@example.com')
        self.other_applicant = create_user('other_app', 'other.app@example.com')
        self.reviewer = create_user('unauth_rev', 'unauth.rev@example.com', is_staff=True)

        self.app_id = create_draft_app(
            self.client, self.applicant,
            email='unauth.app@example.com',
            mobile_number='+255712345685',
            identification_number='NID111222333',
        )
        upload_doc_and_submit(self.client, self.app_id)

    def test_applicant_cannot_view_other_applications(self):
        self.client.force_login(self.other_applicant)
        response = self.client.get(
            reverse('v1:partner-applications-detail', args=[self.app_id]),
            content_type='application/json',
        )
        # Should return 403 (owner-only) or 404
        self.assertIn(response.status_code, [403, 404])

    def test_applicant_cannot_update_submitted_application(self):
        self.client.force_login(self.applicant)
        response = self.client.patch(
            reverse('v1:partner-applications-detail', args=[self.app_id]),
            data=json.dumps({'first_name': 'Updated'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    def test_applicant_cannot_submit_already_submitted(self):
        self.client.force_login(self.applicant)
        response = self.client.post(
            reverse('v1:partner-applications-submit', args=[self.app_id]),
            content_type='application/json',
        )
        # Permission check returns 403 for non-DRAFT applications
        self.assertEqual(response.status_code, 403)

    def test_reviewer_cannot_approve_without_compliance_check(self):
        self.client.force_login(self.reviewer)
        self.client.post(
            reverse('v1:partner-applications-start-review', args=[self.app_id]),
            content_type='application/json',
        )
        response = self.client.post(
            reverse('v1:partner-applications-approve', args=[self.app_id]),
            data=json.dumps({'notes': 'Trying to approve directly'}),
            content_type='application/json',
        )
        # Permission check returns 403 for non-COMPLIANCE_CHECK applications
        self.assertEqual(response.status_code, 403)

    def test_unauthenticated_user_cannot_access_endpoints(self):
        self.client.logout()
        response = self.client.get(
            reverse('v1:partner-applications-list'),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 401)


class DocumentManagementTest(TestCase):
    """Test document upload and verification workflows."""

    def setUp(self):
        self.client = Client()
        self.applicant = create_user('doc_app', 'doc.app@example.com')
        self.reviewer = create_user('doc_rev', 'doc.rev@example.com', is_staff=True)
        self.admin = create_user('doc_admin', 'doc.admin@example.com', is_superuser=True)

    def test_upload_and_verify_document(self):
        app_id = create_draft_app(
            self.client, self.applicant,
            email='doc.app@example.com',
            mobile_number='+255712345687',
            identification_number='NID555666777',
        )

        # Upload document
        doc_data = {
            'document_type': 'NID',
            'document_name': 'National ID Card',
            'file': SimpleUploadedFile('nid.pdf', b'%PDF-1.4 content', content_type='application/pdf'),
        }
        response = self.client.post(
            reverse('v1:application-documents', kwargs={'application_pk': app_id}),
            data=doc_data,
            format='multipart',
        )
        self.assertEqual(response.status_code, 201)
        doc_id = response.json()['data']['id']

        # Verify document (admin only)
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('v1:application-document-verify', kwargs={'application_pk': app_id, 'pk': doc_id}),
            data=json.dumps({'verification_notes': 'Verified successfully'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)

        doc = PartnerApplicationDocument.objects.get(id=doc_id)
        self.assertTrue(doc.is_verified)

    def test_upload_invalid_file_type_rejected(self):
        app_id = create_draft_app(
            self.client, self.applicant,
            email='doc.app2@example.com',
            mobile_number='+255712345787',
            identification_number='NID555666778',
        )
        doc_data = {
            'document_type': 'OTHER',
            'document_name': 'Malware',
            'file': SimpleUploadedFile('malware.exe', b'MZ\x90\x00', content_type='application/x-msdownload'),
        }
        response = self.client.post(
            reverse('v1:application-documents', kwargs={'application_pk': app_id}),
            data=doc_data,
            format='multipart',
        )
        self.assertEqual(response.status_code, 400)


class TaskManagementTest(TestCase):
    """Test task creation and completion workflows."""

    def setUp(self):
        self.client = Client()
        self.applicant = create_user('task_app', 'task.app@example.com')
        self.reviewer = create_user('task_rev', 'task.rev@example.com', is_staff=True)

    def test_create_and_complete_task(self):
        app_id = create_draft_app(
            self.client, self.applicant,
            email='task.app@example.com',
            mobile_number='+255712345688',
            identification_number='NID777888999',
        )
        upload_doc_and_submit(self.client, app_id)

        # Start review and create task
        self.client.force_login(self.reviewer)
        self.client.post(
            reverse('v1:partner-applications-start-review', args=[app_id]),
            content_type='application/json',
        )

        task_data = {
            'task_type': 'REVIEW',
            'title': 'Verify background',
            'description': 'Check applicant background',
            'priority': 'HIGH',
        }
        response = self.client.post(
            reverse('v1:application-tasks', kwargs={'application_pk': app_id}),
            data=json.dumps(task_data),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 201)
        task_id = response.json()['data']['id']

        # Complete task
        response = self.client.post(
            reverse('v1:application-task-complete', kwargs={'application_pk': app_id, 'pk': task_id}),
            data=json.dumps({'notes': 'Background check passed'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)

        task = PartnerApplicationTask.objects.get(id=task_id)
        self.assertEqual(task.status, 'COMPLETED')


class ApplicationDeletionTest(TestCase):
    """Test application deletion scenarios."""

    def setUp(self):
        self.client = Client()
        self.applicant = create_user('del_app', 'del.app@example.com')

    def test_applicant_can_delete_draft(self):
        app_id = create_draft_app(
            self.client, self.applicant,
            email='del.app@example.com',
            mobile_number='+255712345690',
            identification_number='NID222333444',
        )
        response = self.client.delete(
            reverse('v1:partner-applications-detail', args=[app_id]),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 204)
        self.assertFalse(PartnerApplication.objects.filter(id=app_id).exists())

    def test_applicant_cannot_delete_submitted(self):
        app_id = create_draft_app(
            self.client, self.applicant,
            email='del.app2@example.com',
            mobile_number='+255712345691',
            identification_number='NID888999000',
        )
        upload_doc_and_submit(self.client, app_id)

        response = self.client.delete(
            reverse('v1:partner-applications-detail', args=[app_id]),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertTrue(PartnerApplication.objects.filter(id=app_id).exists())


class ComplianceCheckTest(TestCase):
    """Test automated compliance check workflow."""

    def setUp(self):
        self.client = Client()
        self.applicant = create_user('comp_app', 'comp.app@example.com')
        self.reviewer = create_user('comp_rev', 'comp.rev@example.com', is_staff=True)
        self.compliance = create_user('comp_off', 'comp.off@example.com', is_staff=True)

    def test_high_risk_application_flagged(self):
        app_id = create_draft_app(
            self.client, self.applicant,
            email='comp.app@example.com',
            mobile_number='+255712345689',
            identification_number='NID999000111',
            political_risk='HIGH',
            aml_risk='HIGH',
        )
        upload_doc_and_submit(self.client, app_id)

        # Move to compliance
        self.client.force_login(self.reviewer)
        self.client.post(
            reverse('v1:partner-applications-start-review', args=[app_id]),
            content_type='application/json',
        )
        self.client.post(
            reverse('v1:partner-applications-send-to-compliance', args=[app_id]),
            content_type='application/json',
        )

        # Run compliance check
        self.client.force_login(self.compliance)
        response = self.client.post(
            reverse('v1:partner-applications-run-compliance', args=[app_id]),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)

        app = PartnerApplication.objects.get(id=app_id)
        self.assertIn('COMPLIANCE', app.compliance_notes)
