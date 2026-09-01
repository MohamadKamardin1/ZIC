from datetime import date

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase

from apps.governance.models import AuditLog
from apps.group_credit.models import (
    GCHealthQuestion,
    GCHealthQuestionnaire,
    GCSchemeMemberStatus,
    GCSchemePremiumRate,
    GCSchemeRenewalStatus,
    GCSchemeStatus,
    GCSchemeType,
)
from apps.users.models import PermissionGroup, UserGroup, UserPermission


class GCSchemeSetupModelTests(TestCase):
    """Prompt 1 — model creation and relationships for Scheme Setup."""

    def test_scheme_type_and_premium_rate_relationships(self):
        scheme_type = GCSchemeType.objects.create(
            code="BANK_LOAN",
            name="Bank Loan",
            description="Credit life cover for bank loans.",
            partner_type_restriction="BANK",
        )
        rate = GCSchemePremiumRate.objects.create(
            name="Standard Unit Rate - Bank Loan",
            scheme_type=scheme_type,
            rate_type="UNIT",
            rate_value="3.000000",
            currency="TZS",
            age_band_start=18,
            age_band_end=65,
            gender="U",
            effective_date=date(2026, 1, 1),
            effective_from=date(2026, 1, 1),
            effective_to=None,
        )
        self.assertEqual(rate.scheme_type, scheme_type)
        self.assertEqual(scheme_type.premium_rates.count(), 1)
        self.assertEqual(scheme_type.partner_type_restriction, "BANK")

    def test_questionnaire_links_scheme_type_and_questions(self):
        scheme_type = GCSchemeType.objects.create(
            code="CORPORATE_SALARY",
            name="Corporate Salary",
            partner_type_restriction="CORPORATE",
        )
        question = GCHealthQuestion.objects.create(
            code="SMOKING",
            question_text="Do you smoke?",
            answer_type="BOOLEAN",
            required=True,
            category="LIFESTYLE",
        )
        questionnaire = GCHealthQuestionnaire.objects.create(
            code="GC_HQ_V1",
            name="GC Health Questionnaire",
            version="1.0",
            scheme_type_ref=scheme_type,
            threshold_trigger_amount="50000000.00",
            effective_date=date(2026, 1, 1),
            effective_from=date(2026, 1, 1),
        )
        questionnaire.questions.add(question)
        self.assertEqual(questionnaire.scheme_type_ref, scheme_type)
        self.assertEqual(questionnaire.questions.count(), 1)
        self.assertEqual(question.questionnaires.count(), 1)

    def test_status_models_create_with_parameterised_flags(self):
        scheme_status = GCSchemeStatus.objects.create(
            code="TERMINATED",
            name="Terminated",
            display_order=40,
            is_terminal=True,
        )
        self.assertTrue(scheme_status.is_terminal)
        self.assertTrue(scheme_status.is_active)

        member_status = GCSchemeMemberStatus.objects.create(
            code="DECEASED",
            name="Deceased",
            display_order=40,
            is_terminal=True,
            allows_claims=True,
        )
        self.assertTrue(member_status.is_terminal)
        self.assertTrue(member_status.allows_claims)

        renewal_status = GCSchemeRenewalStatus.objects.create(
            code="APPROVED",
            name="Approved",
            display_order=20,
        )
        self.assertEqual(renewal_status.display_order, 20)
        self.assertTrue(renewal_status.is_active)


class GCSchemeSetupValidationTests(TestCase):
    """Prompt 1 — status enum and parameter validation."""

    def test_scheme_type_rejects_invalid_partner_restriction(self):
        scheme_type = GCSchemeType(
            code="INVALID",
            name="Invalid",
            partner_type_restriction="INSURER",
        )
        with self.assertRaises(ValidationError):
            scheme_type.full_clean()

    def test_scheme_type_requires_code(self):
        scheme_type = GCSchemeType(code="  ", name="Blank code")
        with self.assertRaises(ValidationError):
            scheme_type.full_clean()

    def test_premium_rate_rejects_negative_rate_value(self):
        scheme_type = GCSchemeType.objects.create(code="TEST", name="Test")
        rate = GCSchemePremiumRate(
            name="Negative rate",
            scheme_type=scheme_type,
            rate_type="UNIT",
            rate_value="-1.000000",
            age_band_start=18,
            age_band_end=65,
            effective_date=date(2026, 1, 1),
        )
        with self.assertRaises(ValidationError):
            rate.full_clean()

    def test_premium_rate_rejects_invalid_effective_window(self):
        scheme_type = GCSchemeType.objects.create(code="TEST2", name="Test Two")
        rate = GCSchemePremiumRate(
            name="Bad window",
            scheme_type=scheme_type,
            rate_type="FLAT",
            rate_value="100000.000000",
            age_band_start=18,
            age_band_end=65,
            effective_date=date(2026, 1, 1),
            effective_from=date(2026, 12, 31),
            effective_to=date(2026, 1, 1),
        )
        with self.assertRaises(ValidationError):
            rate.full_clean()


class GCSchemeSetupAuditTests(TestCase):
    """Prompt 1 — audit logging on all parameter creates and updates."""

    def test_create_and_update_are_audited(self):
        scheme_type = GCSchemeType.objects.create(
            code="MORTGAGE",
            name="Mortgage Protection",
            partner_type_restriction="BANK",
        )
        self.assertTrue(
            AuditLog.objects.filter(action="CREATE", entity_id=scheme_type.pk).exists()
        )

        scheme_type.name = "Mortgage Protection (Revised)"
        scheme_type.save()
        self.assertTrue(
            AuditLog.objects.filter(action="UPDATE", entity_id=scheme_type.pk).exists()
        )
        update_log = (
            AuditLog.objects.filter(action="UPDATE", entity_id=scheme_type.pk)
            .order_by("-timestamp")
            .first()
        )
        self.assertIn("name", update_log.changed_fields)
        self.assertIsNotNone(update_log.before_state)
        self.assertEqual(update_log.before_state.get("name"), "Mortgage Protection")
        self.assertEqual(update_log.after_state.get("name"), "Mortgage Protection (Revised)")


class GCSchemePermissionRegistrationTests(TestCase):
    """Prompt 1 — gc_parameters permission codes, group, and roles registered."""

    def test_permission_seed_registers_codes_group_and_roles(self):
        call_command("seed_gc_parameters_permissions", verbosity=0)

        for codename in (
            "gc_parameters.view",
            "gc_parameters.manage",
            "gc_parameters.configure",
            "gc_parameters.scheme_types.create",
            "gc_parameters.scheme_rates.update",
            "gc_parameters.health_questionnaires.deactivate",
        ):
            self.assertTrue(
                UserPermission.objects.filter(codename=codename).exists(),
                f"expected permission {codename} to be registered",
            )

        self.assertTrue(
            PermissionGroup.objects.filter(module_code="GC_PARAMETERS").exists()
        )
        for role_code in (
            "GC_PARAMETER_VIEWER",
            "GC_PARAMETER_MANAGER",
            "GC_PARAMETER_ADMINISTRATOR",
        ):
            self.assertTrue(
                UserGroup.objects.filter(code=role_code).exists(),
                f"expected role {role_code} to be registered",
            )

    def test_seed_gc_parameters_creates_reference_data(self):
        call_command("seed_gc_parameters", verbosity=0)

        self.assertTrue(GCSchemeType.objects.filter(code="MORTGAGE_PROTECTION").exists())
        self.assertTrue(GCSchemeType.objects.filter(code="BANK_LOAN").exists())
        self.assertTrue(GCSchemeStatus.objects.filter(code="PENDING_MEDICAL").exists())
        self.assertTrue(GCSchemeMemberStatus.objects.filter(code="DECEASED").exists())
        self.assertTrue(GCSchemeRenewalStatus.objects.filter(code="RENEWED").exists())
        self.assertEqual(GCSchemePremiumRate.objects.filter(rate_type="UNIT").count(), 4)
        self.assertTrue(GCSchemePremiumRate.objects.filter(rate_type="FLAT").exists())

        questionnaire = GCHealthQuestionnaire.objects.get(code="GC_CREDIT_LIFE_HQ_V1")
        self.assertEqual(questionnaire.version, "1.0")
        self.assertEqual(questionnaire.questions.count(), 5)
        self.assertIsNotNone(questionnaire.scheme_type_ref)
