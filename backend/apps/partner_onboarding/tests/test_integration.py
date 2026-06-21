"""
Integration tests for the complete partner onboarding workflow.
Tests end-to-end scenarios from application creation to partner conversion.
"""
import json
from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from apps.users.models import User
from apps.partners.models import Partner
from apps.partner_onboarding.models import PartnerApplication, PartnerApplicationDocument


def create_user(username, email, is_staff=False, is_superuser=False, user_type='PORTAL_USER'):
    return User.objects.create_user(
        username=username,
        email=email,
        password='testpass123',
        user_type=user_type,
        is_staff=is_staff,
        is_superuser=is_superuser,
    )


class IndividualPartnerFullWorkflowTest(TestCase):
    """Test complete workflow for individual partner onboarding."""

    def setUp(self):
        self.client = Client()
        self.applicant = create_user('applicant', 'applicant@example.com')
        self.reviewer = create_user('reviewer', 'reviewer@example.com', is_staff=True)
        self.compliance = create_user('compliance', 'compliance@example.com', is_staff=True)
        self.admin = create_user('admin', 'admin@example.com', is_superuser=True)

    def test_individual_full_workflow(self):
        """DRAFT → SUBMITTED → UNDER_REVIEW → COMPLIANCE_CHECK → APPROVED → CONVERTED"""
        # Step 1: Create draft
        self.client.force_login(self.applicant)
        data = {
            'partner_type': 'INDIVIDUAL',
            'first_name': 'John',
            'surname': 'Doe',
            'email': 'john.doe@example.com',
            'mobile_number': '+255712345678',
            'gender': 'MALE',
            'date_of_birth': '1985-05-15',
            'nationality': 'Tanzanian',
            'identification_type': 'NIN',
            'identification_number': 'NID123456789',
            'physical_address': '123 Main Street, Dar es Salaam',
        }
        response = self.client.post(
            reverse('v1:partner-applications-list'),
            data=json.dumps(data),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 201)
        app_id = response.json()['data']['id']

        app = PartnerApplication.objects.get(id=app_id)
        self.assertEqual(app.status, 'ACTIVE')

        # Step 2: Upload document
        doc_data = {
            'document_type': 'NID',
            'document_name': 'National ID Card',
            'file': SimpleUploadedFile('national_id.pdf', b'%PDF-1.4 content', content_type='application/pdf'),
        }
        response = self.client.post(
            reverse('v1:application-documents', kwargs={'application_pk': app_id}),
            data=doc_data,
            format='multipart',
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(app.documents.count(), 1)

        # Step 3: Submit
        response = self.client.post(
            reverse('v1:partner-applications-submit', args=[app_id]),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        app.refresh_from_db()
        self.assertEqual(app.status, 'SUBMITTED')

        # Step 4: Start review
        self.client.force_login(self.reviewer)
        response = self.client.post(
            reverse('v1:partner-applications-start-review', args=[app_id]),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        app.refresh_from_db()
        self.assertEqual(app.status, 'UNDER_REVIEW')

        # Step 5: Send to compliance
        response = self.client.post(
            reverse('v1:partner-applications-send-to-compliance', args=[app_id]),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        app.refresh_from_db()
        self.assertEqual(app.status, 'COMPLIANCE_CHECK')

        # Step 6: Approve
        self.client.force_login(self.compliance)
        response = self.client.post(
            reverse('v1:partner-applications-approve', args=[app_id]),
            data=json.dumps({'notes': 'All checks passed'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        app.refresh_from_db()
        self.assertEqual(app.status, 'APPROVED')

        # Step 7: Convert to partner
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('v1:partner-applications-convert', args=[app_id]),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        app.refresh_from_db()
        self.assertEqual(app.status, 'CONVERTED')

        partner = Partner.objects.filter(created_from_application=app).first()
        self.assertIsNotNone(partner)
        self.assertEqual(partner.partner_type, 'INDIVIDUAL')
        self.assertEqual(partner.first_name, 'John')
        self.assertEqual(partner.surname, 'Doe')
        self.assertTrue(partner.partner_number.startswith('PN-'))


class CorporatePartnerFullWorkflowTest(TestCase):
    """Test complete workflow for corporate partner onboarding."""

    def setUp(self):
        self.client = Client()
        self.applicant = create_user('corp_app', 'corp.app@example.com')
        self.reviewer = create_user('corp_rev', 'corp.rev@example.com', is_staff=True)
        self.compliance = create_user('corp_comp', 'corp.comp@example.com', is_staff=True)
        self.admin = create_user('corp_admin', 'corp.admin@example.com', is_superuser=True)

    def test_corporate_full_workflow(self):
        """DRAFT → SUBMITTED → UNDER_REVIEW → COMPLIANCE_CHECK → APPROVED → CONVERTED"""
        # Step 1: Create draft
        self.client.force_login(self.applicant)
        data = {
            'partner_type': 'CORPORATE',
            'company_name': 'Tech Solutions Ltd',
            'tin_number': 'TIN-987654321',
            'incorporation_date': '2020-01-15',
            'industry': 'TECHNOLOGY',
            'email': 'contact@techsolutions.co.tz',
            'mobile_number': '+255712345680',
            'telephone_number': '+255222123456',
            'physical_address': '789 Business Park, Dar es Salaam',
            'contact_person': 'Alice Johnson',
            'contact_person_phone': '+255712345681',
            'contact_person_email': 'alice@techsolutions.co.tz',
        }
        response = self.client.post(
            reverse('v1:partner-applications-list'),
            data=json.dumps(data),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 201)
        app_id = response.json()['data']['id']

        # Step 2: Upload documents
        for doc_type, doc_name in [
            ('INCORPORATION_CERT', 'Certificate of Incorporation'),
            ('TIN_CERTIFICATE', 'TIN Certificate'),
            ('BOARD_RESOLUTION', 'Board Resolution'),
        ]:
            doc_data = {
                'document_type': doc_type,
                'document_name': doc_name,
                'file': SimpleUploadedFile(f'{doc_type.lower()}.pdf', b'%PDF-1.4 content', content_type='application/pdf'),
            }
            response = self.client.post(
                reverse('v1:application-documents', kwargs={'application_pk': app_id}),
                data=doc_data,
                format='multipart',
            )
            self.assertEqual(response.status_code, 201)

        app = PartnerApplication.objects.get(id=app_id)
        self.assertEqual(app.documents.count(), 3)

        # Step 3: Submit
        response = self.client.post(
            reverse('v1:partner-applications-submit', args=[app_id]),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        app.refresh_from_db()
        self.assertEqual(app.status, 'SUBMITTED')

        # Step 4: Start review
        self.client.force_login(self.reviewer)
        self.client.post(
            reverse('v1:partner-applications-start-review', args=[app_id]),
            content_type='application/json',
        )

        # Step 5: Send to compliance
        self.client.post(
            reverse('v1:partner-applications-send-to-compliance', args=[app_id]),
            content_type='application/json',
        )

        # Step 6: Approve
        self.client.force_login(self.compliance)
        self.client.post(
            reverse('v1:partner-applications-approve', args=[app_id]),
            data=json.dumps({'notes': 'Corporate partner approved'}),
            content_type='application/json',
        )

        # Step 7: Convert
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('v1:partner-applications-convert', args=[app_id]),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)

        app.refresh_from_db()
        self.assertEqual(app.status, 'CONVERTED')

        partner = Partner.objects.filter(created_from_application=app).first()
        self.assertIsNotNone(partner)
        self.assertEqual(partner.partner_type, 'CORPORATE')
        self.assertEqual(partner.company_name, 'Tech Solutions Ltd')


class ApplicationRejectionWorkflowTest(TestCase):
    """Test rejection scenarios."""

    def setUp(self):
        self.client = Client()
        self.applicant = create_user('rej_app', 'rej.app@example.com')
        self.reviewer = create_user('rej_rev', 'rej.rev@example.com', is_staff=True)
        self.compliance = create_user('rej_comp', 'rej.comp@example.com', is_staff=True)

    def _create_and_submit_app(self):
        self.client.force_login(self.applicant)
        data = {
            'partner_type': 'INDIVIDUAL',
            'first_name': 'Rejected',
            'surname': 'Applicant',
            'email': 'rejected@example.com',
            'mobile_number': '+255712345682',
            'gender': 'MALE',
            'date_of_birth': '1980-01-01',
            'nationality': 'Tanzanian',
            'identification_type': 'NIN',
            'identification_number': 'NID999888777',
            'physical_address': '100 Test Street',
        }
        response = self.client.post(
            reverse('v1:partner-applications-list'),
            data=json.dumps(data),
            content_type='application/json',
        )
        app_id = response.json()['data']['id']

        doc_data = {
            'document_type': 'NID',
            'document_name': 'ID Card',
            'file': SimpleUploadedFile('id.pdf', b'%PDF-1.4 content', content_type='application/pdf'),
        }
        self.client.post(
            reverse('v1:application-documents', kwargs={'application_pk': app_id}),
            data=doc_data,
            format='multipart',
        )
        self.client.post(
            reverse('v1:partner-applications-submit', args=[app_id]),
            content_type='application/json',
        )
        return app_id

    def test_rejection_during_review(self):
        app_id = self._create_and_submit_app()
        self.client.force_login(self.reviewer)
        self.client.post(
            reverse('v1:partner-applications-start-review', args=[app_id]),
            content_type='application/json',
        )
        response = self.client.post(
            reverse('v1:partner-applications-reject', args=[app_id]),
            data=json.dumps({'rejection_reason': 'Incomplete documentation'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        app = PartnerApplication.objects.get(id=app_id)
        self.assertEqual(app.status, 'REJECTED')
        self.assertIn('Incomplete documentation', app.rejection_reason)

    def test_rejection_during_compliance(self):
        app_id = self._create_and_submit_app()
        self.client.force_login(self.reviewer)
        self.client.post(
            reverse('v1:partner-applications-start-review', args=[app_id]),
            content_type='application/json',
        )
        self.client.post(
            reverse('v1:partner-applications-send-to-compliance', args=[app_id]),
            content_type='application/json',
        )
        self.client.force_login(self.compliance)
        response = self.client.post(
            reverse('v1:partner-applications-reject', args=[app_id]),
            data=json.dumps({'rejection_reason': 'High risk identified'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        app = PartnerApplication.objects.get(id=app_id)
        self.assertEqual(app.status, 'REJECTED')


class ApplicationSuspensionWorkflowTest(TestCase):
    """Test suspension and resumption scenarios."""

    def setUp(self):
        self.client = Client()
        self.applicant = create_user('susp_app', 'susp.app@example.com')
        self.reviewer = create_user('susp_rev', 'susp.rev@example.com', is_staff=True)
        self.compliance = create_user('susp_comp', 'susp.comp@example.com', is_staff=True)
        self.admin = create_user('susp_admin', 'susp.admin@example.com', is_superuser=True)

    def test_suspension_and_resumption(self):
        # Create and submit
        self.client.force_login(self.applicant)
        data = {
            'partner_type': 'INDIVIDUAL',
            'first_name': 'Suspended',
            'surname': 'Applicant',
            'email': 'suspended@example.com',
            'mobile_number': '+255712345684',
            'gender': 'MALE',
            'date_of_birth': '1988-12-25',
            'nationality': 'Tanzanian',
            'identification_type': 'NIN',
            'identification_number': 'NID444555666',
            'physical_address': '300 Suspension Road',
        }
        response = self.client.post(
            reverse('v1:partner-applications-list'),
            data=json.dumps(data),
            content_type='application/json',
        )
        app_id = response.json()['data']['id']

        doc_data = {
            'document_type': 'NID',
            'document_name': 'ID',
            'file': SimpleUploadedFile('id.pdf', b'%PDF-1.4 content', content_type='application/pdf'),
        }
        self.client.post(
            reverse('v1:application-documents', kwargs={'application_pk': app_id}),
            data=doc_data,
            format='multipart',
        )
        self.client.post(
            reverse('v1:partner-applications-submit', args=[app_id]),
            content_type='application/json',
        )

        # Review → Compliance
        self.client.force_login(self.reviewer)
        self.client.post(
            reverse('v1:partner-applications-start-review', args=[app_id]),
            content_type='application/json',
        )
        self.client.post(
            reverse('v1:partner-applications-send-to-compliance', args=[app_id]),
            content_type='application/json',
        )

        # Suspend
        self.client.force_login(self.compliance)
        response = self.client.post(
            reverse('v1:partner-applications-suspend', args=[app_id]),
            data=json.dumps({'notes': 'Awaiting additional verification'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        app = PartnerApplication.objects.get(id=app_id)
        self.assertEqual(app.status, 'SUSPENDED')

        # Resume
        response = self.client.post(
            reverse('v1:partner-applications-resume', args=[app_id]),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        app.refresh_from_db()
        self.assertEqual(app.status, 'COMPLIANCE_CHECK')


class PartnerManagementTest(TestCase):
    """Test partner management after conversion."""

    def setUp(self):
        self.client = Client()
        self.admin = create_user('mgmt_admin', 'mgmt.admin@example.com', is_superuser=True)
        self.user = create_user('mgmt_user', 'mgmt.user@example.com')

    def test_admin_can_deactivate_and_reactivate_partner(self):
        partner = Partner.objects.create(
            partner_number='PN-2026-000001',
            partner_type='INDIVIDUAL',
            first_name='Test',
            surname='Partner',
            email='test.partner@example.com',
            mobile_number='+255712345692',
            status='ACTIVE',
        )

        # Deactivate
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('v1:partners-deactivate', args=[partner.id]),
            data=json.dumps({'reason': 'Violation of terms'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        partner.refresh_from_db()
        self.assertEqual(partner.status, 'INACTIVE')
        self.assertIsNotNone(partner.deactivated_at)

        # Reactivate
        response = self.client.post(
            reverse('v1:partners-activate', args=[partner.id]),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        partner.refresh_from_db()
        self.assertEqual(partner.status, 'ACTIVE')
        self.assertIsNone(partner.deactivated_at)

    def test_non_admin_cannot_deactivate(self):
        partner = Partner.objects.create(
            partner_number='PN-2026-000002',
            partner_type='INDIVIDUAL',
            email='test2@example.com',
            mobile_number='+255712345693',
            status='ACTIVE',
        )
        self.client.force_login(self.user)
        response = self.client.post(
            reverse('v1:partners-deactivate', args=[partner.id]),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 403)
