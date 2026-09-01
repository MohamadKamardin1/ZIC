from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase

from apps.governance.models import AuditLog
from apps.group_credit.models import (
    GCClaimReason,
    GCClaimStatus,
    GCClaimType,
    GCCorrespondentType,
    GCDischargeType,
    GCMedicalCode,
    GCMedicalFacility,
    GCMedicalHistory,
    GCMedicalLimit,
    GCMedicalPractitioner,
    GCPersonalHabit,
    GCSchemeType,
    GCUnderwritingDecision,
)
from apps.partners.models import Partner
from apps.users.models import UserPermission


def _make_partner(partner_number, name="Test Partner Ltd"):
    return Partner.objects.create(
        partner_number=partner_number,
        partner_type="CORPORATE",
        partner_category="CORPORATE",
        party_type="CORPORATE",
        legal_name=name,
        email=f"{partner_number.lower()}@test.local",
        mobile_number="+255700000000",
    )


class GCMedicalSetupTests(TestCase):
    """Prompt 3 — medical codes and limits CRUD with scheme/medical-code linkage."""

    def setUp(self):
        self.scheme_type = GCSchemeType.objects.create(
            code="BANK_LOAN", name="Bank Loan", partner_type_restriction="BANK"
        )
        self.code = GCMedicalCode.objects.create(
            code="CVD001", name="Cardiovascular condition", category="ICD_10"
        )

    def test_medical_code_creation(self):
        self.assertEqual(self.code.category, "ICD_10")
        self.assertTrue(self.code.is_active)
        self.assertEqual(
            GCMedicalCode.objects.filter(category="ICD_10").count(), 1
        )

    def test_medical_code_update(self):
        self.code.name = "Cardiovascular condition (revised)"
        self.code.is_active = False
        self.code.save()
        self.code.refresh_from_db()
        self.assertEqual(self.code.name, "Cardiovascular condition (revised)")
        self.assertFalse(self.code.is_active)

    def test_medical_code_rejects_blank_name(self):
        code = GCMedicalCode(code="X1", name="  ")
        with self.assertRaises(ValidationError):
            code.full_clean()

    def test_medical_limit_links_scheme_type_and_medical_code(self):
        limit = GCMedicalLimit.objects.create(
            scheme_type_ref=self.scheme_type,
            medical_code_ref=self.code,
            limit_amount="5000000.00",
            age_min=18,
            age_max=65,
        )
        self.assertEqual(limit.scheme_type_ref, self.scheme_type)
        self.assertEqual(limit.medical_code_ref, self.code)
        self.assertEqual(self.scheme_type.medical_limits.count(), 1)
        self.assertEqual(self.code.medical_limits.count(), 1)

    def test_medical_limit_requires_scheme_type(self):
        limit = GCMedicalLimit(
            medical_code_ref=self.code, limit_amount="5000000.00"
        )
        with self.assertRaises(ValidationError) as ctx:
            limit.full_clean()
        self.assertIn("SCHEME_NOT_FOUND", str(ctx.exception))

    def test_medical_limit_rejects_negative_amount(self):
        limit = GCMedicalLimit(
            scheme_type_ref=self.scheme_type,
            medical_code_ref=self.code,
            limit_amount="-100.00",
        )
        with self.assertRaises(ValidationError) as ctx:
            limit.full_clean()
        self.assertIn("RATE_MISMATCH", str(ctx.exception))

    def test_medical_limit_rejects_inverted_age_window(self):
        limit = GCMedicalLimit(
            scheme_type_ref=self.scheme_type,
            medical_code_ref=self.code,
            limit_amount="5000000.00",
            age_min=70,
            age_max=40,
        )
        with self.assertRaises(ValidationError):
            limit.full_clean()


class GCUnderwritingSetupTests(TestCase):
    """Prompt 3 — underwriting decisions, personal habits, and medical histories CRUD."""

    def test_underwriting_decision_creation(self):
        decision = GCUnderwritingDecision.objects.create(
            code="LOADING", name="Loading", requires_review=True, display_order=20
        )
        self.assertTrue(decision.requires_review)
        self.assertEqual(decision.display_order, 20)
        self.assertEqual(GCUnderwritingDecision.objects.count(), 1)

    def test_underwriting_decision_update(self):
        decision = GCUnderwritingDecision.objects.create(
            code="DECLINE", name="Decline", requires_review=False, display_order=30
        )
        decision.requires_review = True
        decision.save()
        decision.refresh_from_db()
        self.assertTrue(decision.requires_review)

    def test_personal_habit_creation(self):
        habit = GCPersonalHabit.objects.create(
            code="SMOKING",
            name="Smoking",
            habit_category="SMOKING",
            underwriting_impact="HIGH",
        )
        self.assertEqual(habit.habit_category, "SMOKING")
        self.assertEqual(habit.underwriting_impact, "HIGH")
        self.assertTrue(habit.is_active)

    def test_personal_habit_rejects_invalid_category(self):
        habit = GCPersonalHabit(
            code="BAD", name="Bad", habit_category="TRAVELLING"
        )
        with self.assertRaises(ValidationError):
            habit.full_clean()

    def test_medical_history_creation(self):
        history = GCMedicalHistory.objects.create(
            code="DM2",
            name="Type 2 Diabetes",
            condition_category="METABOLIC",
            severity="HIGH",
            waiting_period_days=90,
            exclusion_flag=True,
        )
        self.assertEqual(history.condition_category, "METABOLIC")
        self.assertEqual(history.severity, "HIGH")
        self.assertEqual(history.waiting_period_days, 90)
        self.assertTrue(history.exclusion_flag)

    def test_medical_history_rejects_negative_waiting_period(self):
        history = GCMedicalHistory(
            code="HT",
            name="Hypertension",
            waiting_period_days=-5,
        )
        with self.assertRaises(ValidationError):
            history.full_clean()


class GCClaimSetupTests(TestCase):
    """Prompt 3 — claim types, reasons, statuses, discharge and correspondent types CRUD."""

    def test_claim_type_and_reason_linking(self):
        claim_type = GCClaimType.objects.create(
            code="DEATH",
            name="Death",
            category="DEATH",
            calculation_basis="SUM_ASSURED",
            requires_document_check=True,
        )
        reason = GCClaimReason.objects.create(
            code="NATURAL", name="Natural causes", claim_type=claim_type, category="ILLNESS"
        )
        self.assertEqual(reason.claim_type, claim_type)
        self.assertEqual(claim_type.reasons.count(), 1)
        self.assertEqual(reason.category, "ILLNESS")
        self.assertTrue(claim_type.requires_document_check)

    def test_claim_type_update(self):
        claim_type = GCClaimType.objects.create(
            code="CI", name="Critical Illness", category="CRITICAL_ILLNESS"
        )
        claim_type.requires_document_check = True
        claim_type.save()
        claim_type.refresh_from_db()
        self.assertTrue(claim_type.requires_document_check)

    def test_claim_status_with_display_order_and_terminal(self):
        status = GCClaimStatus.objects.create(
            code="PAID", name="Paid", is_terminal=True, display_order=50
        )
        self.assertTrue(status.is_terminal)
        self.assertEqual(status.display_order, 50)

    def test_discharge_type_requires_template_code(self):
        discharge = GCDischargeType(code="MEMO", name="Memo", template_code="")
        with self.assertRaises(ValidationError) as ctx:
            discharge.full_clean()
        self.assertIn("A template code is required.", str(ctx.exception))

    def test_discharge_type_default_template_and_variables(self):
        discharge = GCDischargeType.objects.create(
            code="SETTLEMENT", name="Settlement", template_code="DEFAULT_MEMO"
        )
        self.assertEqual(discharge.template_code, "DEFAULT_MEMO")
        self.assertEqual(discharge.variables, {})
        self.assertTrue(discharge.is_active)

    def test_correspondent_type_creation(self):
        correspondent = GCCorrespondentType.objects.create(
            code="MEMBER_EMAIL",
            name="Member email",
            category="MEMBER",
            communication_channel="EMAIL",
            purpose="CLAIM_NOTIFICATION",
        )
        self.assertEqual(correspondent.category, "MEMBER")
        self.assertEqual(correspondent.communication_channel, "EMAIL")
        self.assertEqual(correspondent.purpose, "CLAIM_NOTIFICATION")


class GCMedicalPartnerLinkageTests(TestCase):
    """Prompt 3 — facilities and practitioners link to the Partner model."""

    def setUp(self):
        self.partner = _make_partner("PTN-MED-001", name="Medcare Hospital Ltd")

    def test_facility_links_partner(self):
        facility = GCMedicalFacility.objects.create(
            partner_ref=self.partner,
            code="MC-HOSP",
            name="Medcare Central Hospital",
            facility_type="HOSPITAL",
            approval_status="APPROVED",
        )
        self.assertEqual(facility.partner_ref, self.partner)
        self.assertEqual(self.partner.gc_medical_facilities.count(), 1)
        self.assertEqual(facility.facility_type, "HOSPITAL")
        self.assertEqual(facility.approval_status, "APPROVED")

    def test_facility_rejects_invalid_facility_type(self):
        facility = GCMedicalFacility(
            partner_ref=self.partner, code="MC-X", name="Bad facility", facility_type="PHARMACY"
        )
        with self.assertRaises(ValidationError):
            facility.full_clean()

    def test_practitioner_links_partner_and_facility(self):
        facility = GCMedicalFacility.objects.create(
            partner_ref=self.partner,
            code="MC-HOSP",
            name="Medcare Central Hospital",
            facility_type="HOSPITAL",
        )
        practitioner_partner = _make_partner(
            "PTN-MED-002", name="Dr Practice Ltd"
        )
        practitioner = GCMedicalPractitioner.objects.create(
            partner_ref=practitioner_partner,
            code="DR-MW",
            first_name="Mary",
            last_name="Williams",
            specialization="CARDIOLOGY",
            license_number="TZ-MED-0001",
            facility=facility,
            approval_status="PENDING",
        )
        self.assertEqual(practitioner.partner_ref, practitioner_partner)
        self.assertEqual(practitioner.facility, facility)
        self.assertEqual(practitioner.approval_status, "PENDING")
        self.assertEqual(facility.practitioners.count(), 1)

    def test_practitioner_requires_name_or_first_last(self):
        practitioner = GCMedicalPractitioner(code="DR-X")
        with self.assertRaises(ValidationError) as ctx:
            practitioner.full_clean()
        self.assertIn("practitioner name", str(ctx.exception))


class GCMedicalClaimAuditTests(TestCase):
    """Prompt 3 — audit rows created for medical and claim parameter changes."""

    def test_medical_and_claim_changes_are_audited(self):
        code = GCMedicalCode.objects.create(code="HTN", name="Hypertension")
        self.assertTrue(AuditLog.objects.filter(action="CREATE", entity_id=code.pk).exists())

        code.name = "Hypertension (revised)"
        code.save()
        self.assertTrue(AuditLog.objects.filter(action="UPDATE", entity_id=code.pk).exists())
        update_log = (
            AuditLog.objects.filter(action="UPDATE", entity_id=code.pk)
            .order_by("-timestamp")
            .first()
        )
        self.assertIn("name", update_log.changed_fields)
        self.assertEqual(update_log.before_state.get("name"), "Hypertension")
        self.assertEqual(update_log.after_state.get("name"), "Hypertension (revised)")

        claim_type = GCClaimType.objects.create(code="DEATH", name="Death", category="DEATH")
        self.assertTrue(
            AuditLog.objects.filter(action="CREATE", entity_id=claim_type.pk).exists()
        )

        facility = GCMedicalFacility.objects.create(
            partner_ref=_make_partner("PTN-MED-AUD"),
            code="MC-AUD",
            name="Audit Hospital",
            facility_type="HOSPITAL",
        )
        self.assertTrue(
            AuditLog.objects.filter(action="CREATE", entity_id=facility.pk).exists()
        )


class GCMedicalPermissionRegistrationTests(TestCase):
    """Prompt 3 — gc_parameters permission seed covers medical and claim entities."""

    def test_permission_seed_registers_medical_and_claim_codes(self):
        call_command("seed_gc_parameters_permissions", verbosity=0)

        for codename in (
            "gc_parameters.medical_codes.create",
            "gc_parameters.medical_limits.update",
            "gc_parameters.underwriting_decisions.view",
            "gc_parameters.personal_habits.deactivate",
            "gc_parameters.medical_histories.create",
            "gc_parameters.medical_facilities.view",
            "gc_parameters.medical_practitioners.update",
            "gc_parameters.claim_types.create",
            "gc_parameters.claim_reasons.view",
            "gc_parameters.claim_statuses.deactivate",
            "gc_parameters.discharge_types.update",
            "gc_parameters.correspondent_types.create",
        ):
            self.assertTrue(
                UserPermission.objects.filter(codename=codename).exists(),
                f"expected permission {codename} to be registered",
            )
