from datetime import date, timedelta
from unittest.mock import MagicMock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from apps.users.models import User
from apps.partner_onboarding.models import (
    PartnerApplication,
    PartnerApplicationDocument,
    PartnerApplicationTask,
)
from apps.partner_onboarding.serializers import (
    PartnerApplicationListSerializer,
    PartnerApplicationDetailSerializer,
    PartnerApplicationCreateSerializer,
    PartnerApplicationUpdateSerializer,
    PartnerApplicationSubmitSerializer,
    PartnerApplicationReviewSerializer,
    PartnerApplicationComplianceSerializer,
    PartnerConvertSerializer,
    PartnerApplicationDocumentSerializer,
    PartnerApplicationDocumentUploadSerializer,
    PartnerApplicationTaskSerializer,
    ChoicesSerializer,
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


def individual_data(**overrides):
    data = {
        "partner_type": "INDIVIDUAL",
        "identification_type": "NIN",
        "identification_number": "NIN12345",
        "title": "Mr",
        "first_name": "John",
        "other_name": "",
        "surname": "Doe",
        "gender": "MALE",
        "date_of_birth": "1990-05-15",
        "marital_status": "SINGLE",
        "occupation": "Engineer",
        "nationality": "Tanzanian",
        "email": "john@example.com",
        "mobile_number": "+255700000001",
    }
    data.update(overrides)
    return data


def corporate_data(**overrides):
    data = {
        "partner_type": "CORPORATE",
        "company_name": "Acme Corp",
        "tin_number": "TIN-654321",
        "incorporation_date": "2020-01-01",
        "industry": "TECHNOLOGY",
        "email": "info@acme.co.tz",
        "mobile_number": "+255700000002",
        "contact_person": "Jane Smith",
        "contact_person_phone": "+255700000003",
        "contact_person_email": "jane@acme.co.tz",
        "physical_address": "123 Main Street, Dar es Salaam",
    }
    data.update(overrides)
    return data


class PartnerApplicationCreateSerializerTest(TestCase):
    def setUp(self):
        self.user = create_test_user()

    def test_valid_individual_creation(self):
        serializer = PartnerApplicationCreateSerializer(data=individual_data())
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_valid_corporate_creation(self):
        serializer = PartnerApplicationCreateSerializer(data=corporate_data())
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_individual_missing_surname_allowed_for_draft(self):
        data = individual_data(surname="")
        serializer = PartnerApplicationCreateSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_individual_missing_first_name_allowed_for_draft(self):
        data = individual_data(first_name="")
        serializer = PartnerApplicationCreateSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_individual_missing_identification_type_allowed_for_draft(self):
        data = individual_data(identification_type="")
        serializer = PartnerApplicationCreateSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_individual_age_under_18(self):
        recent_dob = (date.today() - timedelta(days=365 * 17)).isoformat()
        data = individual_data(date_of_birth=recent_dob)
        serializer = PartnerApplicationCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("date_of_birth", serializer.errors)

    def test_individual_exactly_18(self):
        today = date.today()
        dob_18 = today.replace(year=today.year - 18)
        data = individual_data(date_of_birth=dob_18.isoformat())
        serializer = PartnerApplicationCreateSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_corporate_missing_tin_number_allowed_for_draft(self):
        data = corporate_data(tin_number="")
        serializer = PartnerApplicationCreateSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_corporate_missing_company_name_allowed_for_draft(self):
        data = corporate_data(company_name="")
        serializer = PartnerApplicationCreateSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_corporate_missing_physical_address_allowed_for_draft(self):
        data = corporate_data(physical_address="")
        serializer = PartnerApplicationCreateSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_corporate_missing_contact_person_allowed_for_draft(self):
        data = corporate_data(contact_person="")
        serializer = PartnerApplicationCreateSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_duplicate_email_from_partner(self):
        from apps.partners.models import Partner
        Partner.objects.create(
            partner_number="PN-2026-999999",
            partner_type="INDIVIDUAL",
            email="existing@example.com",
            mobile_number="+255799999999",
        )
        data = individual_data(email="existing@example.com")
        serializer = PartnerApplicationCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)

    def test_duplicate_email_from_active_application(self):
        PartnerApplication.objects.create(
            application_number="PA-2026-999999",
            partner_type="INDIVIDUAL",
            email="active@example.com",
            mobile_number="+255788888888",
            status="SUBMITTED",
            submitted_by=self.user,
        )
        data = individual_data(email="active@example.com")
        serializer = PartnerApplicationCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)


class PartnerApplicationUpdateSerializerTest(TestCase):
    def setUp(self):
        self.user = create_test_user()
        self.app = PartnerApplication.objects.create(
            application_number="PA-2026-000100",
            partner_type="INDIVIDUAL",
            email="update@example.com",
            mobile_number="+255700000100",
            status="DRAFT",
            submitted_by=self.user,
            first_name="Old",
            surname="Name",
            identification_type="NIN",
            identification_number="NIN999",
            date_of_birth=date(1990, 1, 1),
            gender="MALE",
            nationality="Tanzanian",
        )

    def test_update_draft_allowed(self):
        serializer = PartnerApplicationUpdateSerializer(
            self.app,
            data={"first_name": "New"},
            partial=True,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_update_non_draft_rejected(self):
        self.app.status = "SUBMITTED"
        self.app.save()
        serializer = PartnerApplicationUpdateSerializer(
            self.app,
            data={"first_name": "New"},
            partial=True,
        )
        self.assertFalse(serializer.is_valid())


class PartnerApplicationSubmitSerializerTest(TestCase):
    def setUp(self):
        self.user = create_test_user()
        self.app = PartnerApplication.objects.create(
            application_number="PA-2026-000110",
            partner_type="INDIVIDUAL",
            email="submit@example.com",
            mobile_number="+255700000110",
            status="DRAFT",
            submitted_by=self.user,
            identification_type="NIN",
            identification_number="NIN111",
            first_name="John",
            surname="Doe",
            date_of_birth=date(1990, 1, 1),
            gender="MALE",
            nationality="Tanzanian",
        )

    def test_submit_without_documents_passes(self):
        serializer = PartnerApplicationSubmitSerializer(instance=self.app, data={})
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_submit_with_document_passes(self):
        PartnerApplicationDocument.objects.create(
            application=self.app,
            document_type="NID",
            document_name="id.pdf",
            file="partner_documents/test.pdf",
            uploaded_by=self.user,
        )
        serializer = PartnerApplicationSubmitSerializer(instance=self.app, data={})
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_submit_non_draft_fails(self):
        self.app.status = "SUBMITTED"
        self.app.save()
        serializer = PartnerApplicationSubmitSerializer(instance=self.app, data={})
        self.assertFalse(serializer.is_valid())


class PartnerApplicationReviewSerializerTest(TestCase):
    def setUp(self):
        self.user = create_test_user()
        self.app = PartnerApplication.objects.create(
            application_number="PA-2026-000120",
            partner_type="INDIVIDUAL",
            email="review@example.com",
            mobile_number="+255700000120",
            status="SUBMITTED",
            submitted_by=self.user,
        )

    def test_review_submitted_application(self):
        serializer = PartnerApplicationReviewSerializer(
            instance=self.app, data={"notes": "Looks good"}
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_review_draft_application_fails(self):
        self.app.status = "DRAFT"
        self.app.save()
        serializer = PartnerApplicationReviewSerializer(
            instance=self.app, data={}
        )
        self.assertFalse(serializer.is_valid())


class PartnerApplicationComplianceSerializerTest(TestCase):
    def setUp(self):
        self.user = create_test_user()
        self.app = PartnerApplication.objects.create(
            application_number="PA-2026-000130",
            partner_type="INDIVIDUAL",
            email="compliance@example.com",
            mobile_number="+255700000130",
            status="COMPLIANCE_CHECK",
            submitted_by=self.user,
        )

    def test_compliance_on_valid_status(self):
        serializer = PartnerApplicationComplianceSerializer(
            instance=self.app, data={"notes": "All clear"}
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_compliance_on_wrong_status(self):
        self.app.status = "SUBMITTED"
        self.app.save()
        serializer = PartnerApplicationComplianceSerializer(
            instance=self.app, data={}
        )
        self.assertFalse(serializer.is_valid())


class PartnerConvertSerializerTest(TestCase):
    def setUp(self):
        self.user = create_test_user()
        self.app = PartnerApplication.objects.create(
            application_number="PA-2026-000140",
            partner_type="INDIVIDUAL",
            email="convert@example.com",
            mobile_number="+255700000140",
            status="APPROVED",
            submitted_by=self.user,
        )

    def test_convert_approved_application(self):
        serializer = PartnerConvertSerializer(instance=self.app, data={})
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_convert_non_approved_fails(self):
        self.app.status = "COMPLIANCE_CHECK"
        self.app.save()
        serializer = PartnerConvertSerializer(instance=self.app, data={})
        self.assertFalse(serializer.is_valid())

    def test_convert_duplicate_email_fails(self):
        from apps.partners.models import Partner
        Partner.objects.create(
            partner_number="PN-2026-888888",
            partner_type="INDIVIDUAL",
            email="convert@example.com",
            mobile_number="+255777777777",
        )
        serializer = PartnerConvertSerializer(instance=self.app, data={})
        self.assertFalse(serializer.is_valid())


class PartnerApplicationListSerializerTest(TestCase):
    def setUp(self):
        self.user = create_test_user()
        self.app = PartnerApplication.objects.create(
            application_number="PA-2026-000150",
            partner_type="INDIVIDUAL",
            first_name="List",
            surname="Test",
            email="list@example.com",
            mobile_number="+255700000150",
            submitted_by=self.user,
        )

    def test_list_serializer_fields(self):
        serializer = PartnerApplicationListSerializer(self.app)
        data = serializer.data
        self.assertIn("id", data)
        self.assertIn("application_number", data)
        self.assertIn("display_name", data)
        self.assertIn("status", data)
        self.assertNotIn("documents", data)
        self.assertNotIn("tasks", data)


class PartnerApplicationDetailSerializerTest(TestCase):
    def setUp(self):
        self.user = create_test_user()
        self.app = PartnerApplication.objects.create(
            application_number="PA-2026-000160",
            partner_type="INDIVIDUAL",
            first_name="Detail",
            surname="Test",
            email="detail@example.com",
            mobile_number="+255700000160",
            submitted_by=self.user,
        )

    def test_detail_serializer_includes_nested(self):
        serializer = PartnerApplicationDetailSerializer(self.app)
        data = serializer.data
        self.assertIn("documents", data)
        self.assertIn("tasks", data)
        self.assertIn("submitted_by", data)
        self.assertIn("identification_type", data)


class PartnerApplicationTaskSerializerTest(TestCase):
    def setUp(self):
        self.user = create_test_user()
        self.app = PartnerApplication.objects.create(
            application_number="PA-2026-000170",
            partner_type="INDIVIDUAL",
            email="task@example.com",
            mobile_number="+255700000170",
            submitted_by=self.user,
        )

    def test_create_task(self):
        future = (date.today() + timedelta(days=7)).isoformat()
        data = {
            "task_type": "DOCUMENT_REQUEST",
            "title": "Upload TIN",
            "description": "Please provide TIN certificate",
            "priority": "HIGH",
            "due_date": future,
        }
        serializer = PartnerApplicationTaskSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_past_due_date_rejected(self):
        past = (date.today() - timedelta(days=1)).isoformat()
        data = {
            "task_type": "REVIEW",
            "title": "Review app",
            "due_date": past,
        }
        serializer = PartnerApplicationTaskSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("due_date", serializer.errors)


class PartnerApplicationDocumentUploadSerializerTest(TestCase):
    def test_file_size_limit(self):
        big_file = SimpleUploadedFile(
            "big.pdf", b"x" * (10 * 1024 * 1024 + 1),
            content_type="application/pdf",
        )
        data = {
            "document_type": "NID",
            "document_name": "big.pdf",
            "file": big_file,
        }
        serializer = PartnerApplicationDocumentUploadSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("file", serializer.errors)

    def test_invalid_mime_type(self):
        bad_file = SimpleUploadedFile(
            "malware.exe", b"x" * 100,
            content_type="application/x-msdownload",
        )
        data = {
            "document_type": "OTHER",
            "document_name": "malware.exe",
            "file": bad_file,
        }
        serializer = PartnerApplicationDocumentUploadSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("file", serializer.errors)

    def test_valid_pdf_upload(self):
        pdf_file = SimpleUploadedFile(
            "doc.pdf", b"%PDF-1.4 content",
            content_type="application/pdf",
        )
        data = {
            "document_type": "NID",
            "document_name": "national_id.pdf",
            "file": pdf_file,
        }
        serializer = PartnerApplicationDocumentUploadSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)


class ChoicesSerializerTest(TestCase):
    def test_choices_structure(self):
        serializer = ChoicesSerializer({})
        data = serializer.data
        self.assertIn("partner_types", data)
        self.assertIn("identification_types", data)
        self.assertIn("industries", data)
        self.assertIn("application_statuses", data)
        self.assertIn("nationalities", data)
        # Verify structure
        for item in data["partner_types"]:
            self.assertIn("value", item)
            self.assertIn("label", item)
        # Verify application statuses count
        self.assertEqual(len(data["application_statuses"]), 10)
