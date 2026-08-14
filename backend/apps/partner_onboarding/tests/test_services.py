from datetime import date
from unittest.mock import MagicMock

from django.test import TestCase
from django.utils import timezone

from apps.users.models import User
from apps.partners.models import Partner, PartnerType
from apps.partner_onboarding.models import PartnerApplication, PartnerApplicationDocument, ApplicationPartnerType
from apps.partner_onboarding.services import ApplicationService, ComplianceService
from apps.system_parameters.services.workflow_service import WorkflowEngine
from apps.partner_onboarding.exceptions import (
    ApplicationTransitionError,
    ApplicationValidationError,
    PartnerConversionError,
)


def create_test_user(email="svc@example.com", username="svcuser", **kwargs):
    return User.objects.create_user(
        email=email,
        username=username,
        password="TestPassword123!",
        first_name="Service",
        last_name="User",
        **kwargs,
    )


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
    app_num = ApplicationService.generate_application_number(defaults.get("partner_type"))
    application = PartnerApplication.objects.create(
        application_number=app_num,
        submitted_by=user,
        **defaults,
    )
    partner_type, _ = PartnerType.objects.get_or_create(
        code="TEST_SERVICE",
        defaults={"name": "Test Service Partner Type", "is_active": True},
    )
    ApplicationPartnerType.objects.get_or_create(
        application=application,
        partner_type=partner_type,
    )
    return application


def create_corporate_app(user, **overrides):
    defaults = {
        "partner_type": "CORPORATE",
        "company_name": "Acme Corp",
        "tin_number": "TIN-654321",
        "incorporation_date": date(2020, 1, 1),
        "industry": "TECHNOLOGY",
        "email": "info@acme.co.tz",
        "mobile_number": "+255700000002",
        "contact_person": "Jane Smith",
        "contact_person_phone": "+255700000003",
        "contact_person_email": "jane@acme.co.tz",
        "physical_address": "123 Main Street, Dar es Salaam",
    }
    defaults.update(overrides)
    app_num = ApplicationService.generate_application_number(defaults.get("partner_type"))
    application = PartnerApplication.objects.create(
        application_number=app_num,
        submitted_by=user,
        **defaults,
    )
    partner_type, _ = PartnerType.objects.get_or_create(
        code="TEST_SERVICE_CORPORATE",
        defaults={"name": "Test Service Corporate Partner Type", "is_active": True},
    )
    ApplicationPartnerType.objects.get_or_create(
        application=application,
        partner_type=partner_type,
    )
    return application


def add_document(application, user):
    return PartnerApplicationDocument.objects.create(
        application=application,
        document_type="NID",
        document_name="national_id.pdf",
        file="partner_documents/test.pdf",
        uploaded_by=user,
    )


class GenerateApplicationNumberTest(TestCase):
    def setUp(self):
        self.user = create_test_user()

    def test_first_number_individual(self):
        num = ApplicationService.generate_application_number("INDIVIDUAL")
        year = date.today().year
        self.assertEqual(num, f"PA-{year}-000001")

    def test_first_number_corporate(self):
        num = ApplicationService.generate_application_number("CORPORATE")
        year = date.today().year
        self.assertEqual(num, f"CO-{year}-000001")

    def test_sequential_individual(self):
        app = create_individual_app(self.user)
        self.assertTrue(app.application_number.startswith(f"PA-{date.today().year}-"))
        year = date.today().year
        num2 = ApplicationService.generate_application_number("INDIVIDUAL")
        self.assertEqual(num2, f"PA-{year}-000002")

    def test_increments_correctly_after_multiple(self):
        for _ in range(5):
            create_individual_app(self.user)
        num = ApplicationService.generate_application_number("INDIVIDUAL")
        year = date.today().year
        self.assertEqual(num, f"PA-{year}-000006")

    def test_corporate_uses_separate_sequence(self):
        num1 = ApplicationService.generate_application_number("CORPORATE")
        year = date.today().year
        self.assertTrue(num1.startswith(f"CO-{year}-"))
        self.assertEqual(len(num1), len(f"CO-{year}-") + 6)

    def test_individual_and_corporate_sequences_independent(self):
        ind = ApplicationService.generate_application_number("INDIVIDUAL")
        corp = ApplicationService.generate_application_number("CORPORATE")
        year = date.today().year
        self.assertTrue(ind.startswith(f"PA-{year}-"))
        self.assertTrue(corp.startswith(f"CO-{year}-"))


class CreateDraftTest(TestCase):
    def setUp(self):
        self.user = create_test_user()

    def test_create_individual_draft(self):
        data = {
            "partner_type": "INDIVIDUAL",
            "first_name": "Alice",
            "surname": "Brown",
            "email": "alice@example.com",
            "mobile_number": "+255700000010",
        }
        app = ApplicationService.create_draft(self.user, data)
        self.assertEqual(app.status, "ACTIVE")
        self.assertEqual(app.first_name, "Alice")
        self.assertTrue(app.application_number.startswith("PA-"))
        self.assertEqual(app.submitted_by, self.user)

    def test_create_corporate_draft(self):
        data = {
            "partner_type": "CORPORATE",
            "company_name": "Test Corp",
            "email": "test@corp.com",
            "mobile_number": "+255700000011",
        }
        app = ApplicationService.create_draft(self.user, data)
        self.assertEqual(app.status, "ACTIVE")
        self.assertEqual(app.company_name, "Test Corp")


class SubmitTest(TestCase):
    def setUp(self):
        self.user = create_test_user()

    def test_submit_complete_individual(self):
        app = create_individual_app(self.user)
        add_document(app, self.user)
        result = ApplicationService.submit(app, self.user)
        self.assertEqual(result.status, "SUBMITTED")
        self.assertIsNotNone(result.submitted_at)

    def test_submit_without_documents(self):
        app = create_individual_app(self.user)
        result = ApplicationService.submit(app, self.user)
        self.assertEqual(result.status, "SUBMITTED")

    def test_submit_missing_required_field(self):
        app = create_individual_app(self.user, first_name="")
        add_document(app, self.user)
        with self.assertRaises(ApplicationValidationError):
            ApplicationService.submit(app, self.user)

    def test_submit_non_draft_fails(self):
        app = create_individual_app(self.user)
        app.status = "SUBMITTED"
        app.save()
        with self.assertRaises(ApplicationTransitionError):
            ApplicationService.submit(app, self.user)

    def test_submit_corporate_complete(self):
        app = create_corporate_app(self.user)
        add_document(app, self.user)
        result = ApplicationService.submit(app, self.user)
        self.assertEqual(result.status, "SUBMITTED")


class StateTransitionTest(TestCase):
    def setUp(self):
        self.user = create_test_user()

    def test_draft_to_submitted(self):
        app = create_individual_app(self.user)
        add_document(app, self.user)
        result = ApplicationService.submit(app, self.user)
        self.assertEqual(result.status, "SUBMITTED")

    def test_submitted_to_under_review(self):
        app = create_individual_app(self.user)
        add_document(app, self.user)
        ApplicationService.submit(app, self.user)
        result = ApplicationService.start_review(app, self.user)
        self.assertEqual(result.status, "UNDER_REVIEW")

    def test_under_review_to_pending_documents(self):
        app = create_individual_app(self.user)
        add_document(app, self.user)
        ApplicationService.submit(app, self.user)
        ApplicationService.start_review(app, self.user)
        result = ApplicationService.request_documents(app, self.user)
        self.assertEqual(result.status, "PENDING_DOCUMENTS")

    def test_under_review_to_compliance_check(self):
        app = create_individual_app(self.user)
        add_document(app, self.user)
        ApplicationService.submit(app, self.user)
        ApplicationService.start_review(app, self.user)
        result = ApplicationService.send_to_compliance(app, self.user)
        self.assertEqual(result.status, "COMPLIANCE_CHECK")

    def test_compliance_check_to_approved(self):
        app = create_individual_app(self.user)
        add_document(app, self.user)
        ApplicationService.submit(app, self.user)
        ApplicationService.start_review(app, self.user)
        ApplicationService.send_to_compliance(app, self.user)
        result = ApplicationService.approve(app, self.user)
        self.assertEqual(result.status, "APPROVED")

    def test_compliance_check_to_rejected(self):
        app = create_individual_app(self.user)
        add_document(app, self.user)
        ApplicationService.submit(app, self.user)
        ApplicationService.start_review(app, self.user)
        ApplicationService.send_to_compliance(app, self.user)
        result = ApplicationService.reject(app, self.user, reason="Incomplete")
        self.assertEqual(result.status, "REJECTED")
        self.assertEqual(result.rejection_reason, "Incomplete")

    def test_compliance_check_to_suspended(self):
        app = create_individual_app(self.user)
        add_document(app, self.user)
        ApplicationService.submit(app, self.user)
        ApplicationService.start_review(app, self.user)
        ApplicationService.send_to_compliance(app, self.user)
        result = ApplicationService.suspend(app, self.user, notes="Awaiting info")
        self.assertEqual(result.status, "SUSPENDED")

    def test_suspended_to_compliance_check(self):
        app = create_individual_app(self.user)
        add_document(app, self.user)
        ApplicationService.submit(app, self.user)
        ApplicationService.start_review(app, self.user)
        ApplicationService.send_to_compliance(app, self.user)
        ApplicationService.suspend(app, self.user)
        result = ApplicationService.send_to_compliance(app, self.user)
        self.assertEqual(result.status, "COMPLIANCE_CHECK")

    def test_invalid_transition_draft_to_approved(self):
        app = create_individual_app(self.user)
        with self.assertRaises(ApplicationTransitionError):
            ApplicationService.approve(app, self.user)

    def test_invalid_transition_submitted_to_approved(self):
        app = create_individual_app(self.user)
        add_document(app, self.user)
        ApplicationService.submit(app, self.user)
        with self.assertRaises(ApplicationTransitionError):
            ApplicationService.approve(app, self.user)

    def test_invalid_transition_rejected_to_approved(self):
        app = create_individual_app(self.user)
        add_document(app, self.user)
        ApplicationService.submit(app, self.user)
        ApplicationService.start_review(app, self.user)
        ApplicationService.send_to_compliance(app, self.user)
        ApplicationService.reject(app, self.user, reason="Rejected for testing")
        with self.assertRaises(ApplicationTransitionError):
            ApplicationService.approve(app, self.user)

    def test_submitted_to_draft_recall(self):
        app = create_individual_app(self.user)
        add_document(app, self.user)
        submitted = ApplicationService.submit(app, self.user)
        self.assertIsNone(ApplicationService._validate_transition(submitted, "DRAFT"))
        self.assertEqual(submitted.status, "SUBMITTED")

    def test_rejected_is_terminal(self):
        app = create_individual_app(self.user)
        add_document(app, self.user)
        ApplicationService.submit(app, self.user)
        ApplicationService.start_review(app, self.user)
        ApplicationService.send_to_compliance(app, self.user)
        ApplicationService.reject(app, self.user, reason="Rejected for testing")
        self.assertTrue(WorkflowEngine.is_terminal("REJECTED"))

    def test_converted_is_terminal(self):
        self.assertTrue(WorkflowEngine.is_terminal("CONVERTED"))


class ConvertToPartnerTest(TestCase):
    def setUp(self):
        self.user = create_test_user()

    def test_convert_individual_to_partner(self):
        app = create_individual_app(self.user)
        add_document(app, self.user)
        ApplicationService.submit(app, self.user)
        ApplicationService.start_review(app, self.user)
        ApplicationService.send_to_compliance(app, self.user)
        ApplicationService.approve(app, self.user)

        partner = ApplicationService.convert_to_partner(app, self.user)

        self.assertIsInstance(partner, Partner)
        self.assertTrue(partner.partner_number.startswith("PN-"))
        self.assertEqual(partner.partner_type, "INDIVIDUAL")
        self.assertEqual(partner.status, "ACTIVE")
        self.assertEqual(partner.first_name, app.first_name)
        self.assertEqual(partner.email, app.email)
        self.assertEqual(partner.created_from_application, app)
        self.assertIsNotNone(partner.activated_at)

        app.refresh_from_db()
        self.assertEqual(app.status, "CONVERTED")
        self.assertIsNotNone(app.converted_at)

    def test_convert_corporate_to_partner(self):
        app = create_corporate_app(self.user)
        add_document(app, self.user)
        ApplicationService.submit(app, self.user)
        ApplicationService.start_review(app, self.user)
        ApplicationService.send_to_compliance(app, self.user)
        ApplicationService.approve(app, self.user)

        partner = ApplicationService.convert_to_partner(app, self.user)

        self.assertEqual(partner.partner_type, "CORPORATE")
        self.assertEqual(partner.company_name, app.company_name)
        self.assertEqual(partner.tin_number, app.tin_number)

    def test_convert_non_approved_fails(self):
        app = create_individual_app(self.user)
        add_document(app, self.user)
        ApplicationService.submit(app, self.user)
        with self.assertRaises(ApplicationTransitionError):
            ApplicationService.convert_to_partner(app, self.user)

    def test_convert_duplicate_email_fails(self):
        Partner.objects.create(
            partner_number="PN-2026-999999",
            partner_type="INDIVIDUAL",
            email="john@example.com",
            mobile_number="+255799999999",
        )
        app = create_individual_app(self.user)
        add_document(app, self.user)
        ApplicationService.submit(app, self.user)
        ApplicationService.start_review(app, self.user)
        ApplicationService.send_to_compliance(app, self.user)
        ApplicationService.approve(app, self.user)
        with self.assertRaises(PartnerConversionError):
            ApplicationService.convert_to_partner(app, self.user)

    def test_partner_number_sequential(self):
        app1 = create_individual_app(self.user)
        add_document(app1, self.user)
        ApplicationService.submit(app1, self.user)
        ApplicationService.start_review(app1, self.user)
        ApplicationService.send_to_compliance(app1, self.user)
        ApplicationService.approve(app1, self.user)
        p1 = ApplicationService.convert_to_partner(app1, self.user)

        app2 = create_corporate_app(self.user)
        add_document(app2, self.user)
        ApplicationService.submit(app2, self.user)
        ApplicationService.start_review(app2, self.user)
        ApplicationService.send_to_compliance(app2, self.user)
        ApplicationService.approve(app2, self.user)
        p2 = ApplicationService.convert_to_partner(app2, self.user)

        year = date.today().year
        self.assertEqual(p1.partner_number, f"PN-{year}-000001")
        self.assertEqual(p2.partner_number, f"PN-{year}-000002")


class ComplianceServiceTest(TestCase):
    def setUp(self):
        self.user = create_test_user()

    def test_low_risk_score(self):
        app = create_individual_app(self.user, political_risk="LOW", aml_risk="LOW")
        score = ComplianceService.calculate_risk_score(app)
        self.assertEqual(score, 0)

    def test_medium_risk_score(self):
        app = create_individual_app(
            self.user, political_risk="MEDIUM", aml_risk="MEDIUM"
        )
        score = ComplianceService.calculate_risk_score(app)
        self.assertEqual(score, 20)

    def test_high_risk_score(self):
        app = create_individual_app(
            self.user, political_risk="HIGH", aml_risk="HIGH"
        )
        score = ComplianceService.calculate_risk_score(app)
        self.assertEqual(score, 50)

    def test_pep_individual_bonus(self):
        app = create_individual_app(self.user, political_risk="PEP")
        score = ComplianceService.calculate_risk_score(app)
        self.assertEqual(score, 50)

    def test_pep_corporate_no_bonus(self):
        app = create_corporate_app(
            self.user, political_risk="PEP", industry="TECHNOLOGY"
        )
        score = ComplianceService.calculate_risk_score(app)
        self.assertEqual(score, 40)

    def test_high_risk_industry_adds_score(self):
        app = create_individual_app(
            self.user, industry="FINANCIAL_SERVICES"
        )
        score = ComplianceService.calculate_risk_score(app)
        self.assertEqual(score, 15)

    def test_combined_risk_score(self):
        app = create_individual_app(
            self.user,
            political_risk="HIGH",
            aml_risk="MEDIUM",
            industry="OIL_GAS",
        )
        score = ComplianceService.calculate_risk_score(app)
        self.assertEqual(score, 50)

    def test_score_capped_at_100(self):
        app = create_individual_app(
            self.user,
            political_risk="PEP",
            aml_risk="HIGH",
            industry="FINANCIAL_SERVICES",
        )
        score = ComplianceService.calculate_risk_score(app)
        self.assertLessEqual(score, 100)

    def test_flag_high_risk_individual(self):
        app = create_individual_app(
            self.user, political_risk="HIGH", aml_risk="HIGH"
        )
        result = ComplianceService.flag_high_risk(app)
        self.assertTrue(result["is_high_risk"])
        self.assertEqual(result["risk_score"], 50)
        self.assertEqual(result["threshold"], 50)
        app.refresh_from_db()
        self.assertIn("[COMPLIANCE] High risk flagged", app.compliance_notes)

    def test_flag_low_risk_individual(self):
        app = create_individual_app(
            self.user, political_risk="LOW", aml_risk="LOW"
        )
        result = ComplianceService.flag_high_risk(app)
        self.assertFalse(result["is_high_risk"])
        self.assertEqual(result["risk_score"], 0)

    def test_flag_high_risk_corporate(self):
        app = create_corporate_app(
            self.user,
            political_risk="HIGH",
            aml_risk="HIGH",
            industry="FINANCIAL_SERVICES",
        )
        result = ComplianceService.flag_high_risk(app)
        self.assertTrue(result["is_high_risk"])
        self.assertEqual(result["risk_score"], 65)
        self.assertEqual(result["threshold"], 60)

    def test_flag_preserves_existing_notes(self):
        app = create_individual_app(
            self.user, political_risk="HIGH", aml_risk="HIGH"
        )
        app.compliance_notes = "Existing notes"
        app.save()
        ComplianceService.flag_high_risk(app)
        app.refresh_from_db()
        self.assertIn("Existing notes", app.compliance_notes)
        self.assertIn("[COMPLIANCE] High risk flagged", app.compliance_notes)
