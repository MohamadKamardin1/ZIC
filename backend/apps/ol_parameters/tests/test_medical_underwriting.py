from datetime import date
from decimal import Decimal

from django.contrib import admin
from django.core import management
from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework.test import APIClient

from apps.governance.models import AuditLog
from apps.ol_parameters.models import (
    OLMedicalCode,
    OLMedicalFacility,
    OLMedicalHistory,
    OLMedicalLimit,
    OLMedicalPractitioner,
    OLParameterTableRegistry,
    OLPersonalHabit,
    OLPlanType,
    OLProduct,
)
from apps.partners.models import Partner
from apps.users.models import User


class OLMedicalUnderwritingTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="ol-medical-uw-admin",
            email="ol-medical-uw-admin@example.com",
            password="Strong-pass-123!",
            is_superuser=True,
            is_staff=True,
            is_active=True,
            is_approved=True,
        )
        self.client.force_authenticate(self.user)
        self.plan_type = OLPlanType.objects.create(
            code="ENDOWMENT",
            name="Endowment",
            description="Endowment plan type.",
            plan_category="INDIVIDUAL",
            effective_from=date(2026, 1, 1),
        )
        self.product = OLProduct.objects.create(
            code="STANDARD_ENDOWMENT",
            name="Standard Endowment",
            description="Standard endowment product.",
            plan_type=self.plan_type,
            insurance_class="INDIVIDUAL",
            currency="TZS",
            min_entry_age=18,
            max_entry_age=65,
            min_term=5,
            max_term=30,
            min_sum_assured=Decimal("1000000.00"),
            max_sum_assured=Decimal("1000000000.00"),
            premium_frequencies=["MONTHLY", "ANNUAL"],
            allow_riders=True,
            allow_loans=True,
            allow_surrender=True,
            allow_paidup=True,
            allow_bonus=True,
            effective_from=date(2026, 1, 1),
        )
        self.partner = Partner.objects.create(
            partner_number="MED-PT-001",
            partner_type="SERVICE_PROVIDER",
            first_name="Medical",
            surname="Partner",
            email="medical.partner@example.com",
            mobile_number="+255711000111",
            status="ACTIVE",
            is_active=True,
        )

    def medical_code_payload(self, code="BASIC_MEDICAL_EXAMINATION"):
        return {
            "code": code,
            "name": "Basic Medical Examination",
            "medical_category": "EXAMINATION",
            "description": "Medical examination catalog code.",
            "effective_from": "2026-01-01",
            "effective_to": None,
            "is_active": True,
        }

    def medical_limit_payload(self, medical_code_id, code="BASIC_MEDICAL_LIMIT"):
        return {
            "code": code,
            "name": "Basic Medical Limit",
            "description": "Medical limit configuration.",
            "medical_code": str(medical_code_id),
            "product": str(self.product.pk),
            "plan": None,
            "age_from": 18,
            "age_to": 65,
            "sum_assured_from": "0.00",
            "sum_assured_to": "50000000.00",
            "limit_type": "MEDICAL",
            "limit_amount": "50000.00",
            "required_frequency": "ANNUAL",
            "mandatory_flag": True,
            "effective_from": "2026-01-01",
            "effective_to": None,
            "is_active": True,
        }

    def habit_payload(self, code="SMOKING_HISTORY"):
        return {
            "code": code,
            "name": "Smoking History",
            "description": "Personal habit underwriting question.",
            "habit_category": "SMOKING",
            "question_text": "Have you used tobacco or nicotine products during the last twelve months?",
            "underwriting_impact": "HIGH",
            "requires_evidence": True,
            "effective_from": "2026-01-01",
            "effective_to": None,
            "is_active": True,
        }

    def history_payload(self, code="HYPERTENSION_HISTORY"):
        return {
            "code": code,
            "name": "Hypertension History",
            "description": "Medical history condition.",
            "condition_category": "CARDIOVASCULAR",
            "severity": "MODERATE",
            "waiting_period_days": 0,
            "exclusion_flag": False,
            "loading_flag": True,
            "underwriting_note": "Obtain recent medical evidence and treatment history.",
            "effective_from": "2026-01-01",
            "effective_to": None,
            "is_active": True,
        }

    def facility_payload(self, code="DAR_ES_SALAAM_MEDICAL_CENTRE", partner=None):
        return {
            "code": code,
            "name": "Dar es Salaam Medical Centre",
            "description": "Approved medical facility configuration.",
            "partner": str(partner.pk) if partner else None,
            "facility_code": code,
            "facility_type": "HOSPITAL",
            "registration_number": "REG-MED-001",
            "address": "Dar es Salaam",
            "city": "Dar es Salaam",
            "country": "TZ",
            "contact_email": "facility@example.com",
            "contact_phone": "+255711000222",
            "approval_status": "APPROVED",
            "effective_from": "2026-01-01",
            "effective_to": None,
            "is_active": True,
        }

    def practitioner_payload(self, facility_id=None, partner=None, code="DR_MEDICAL_001"):
        return {
            "code": code,
            "name": "Dr Medical Practitioner",
            "description": "Approved medical practitioner configuration.",
            "partner": str(partner.pk) if partner else None,
            "practitioner_code": code,
            "first_name": "Medical",
            "last_name": "Practitioner",
            "specialty": "GENERAL_MEDICINE",
            "license_number": "TZ-MED-001",
            "medical_facility": str(facility_id) if facility_id else None,
            "email": "practitioner@example.com",
            "phone": "+255711000333",
            "approval_status": "APPROVED",
            "effective_from": "2026-01-01",
            "effective_to": None,
            "is_active": True,
        }

    def test_all_six_entities_support_crud_filters_export_and_deactivation(self):
        code_response = self.client.post(
            "/api/v1/ol-parameters/medical-codes/",
            self.medical_code_payload(),
            format="json",
            HTTP_X_REQUEST_ID="medical-code-create",
        )
        self.assertEqual(code_response.status_code, 201, code_response.data)
        medical_code = OLMedicalCode.objects.get(code="BASIC_MEDICAL_EXAMINATION")

        limit_response = self.client.post(
            "/api/v1/ol-parameters/medical-limits/",
            self.medical_limit_payload(medical_code.pk),
            format="json",
        )
        self.assertEqual(limit_response.status_code, 201, limit_response.data)
        limit = OLMedicalLimit.objects.get(code="BASIC_MEDICAL_LIMIT")

        habit_response = self.client.post(
            "/api/v1/ol-parameters/personal-habits/",
            self.habit_payload(),
            format="json",
        )
        self.assertEqual(habit_response.status_code, 201, habit_response.data)

        history_response = self.client.post(
            "/api/v1/ol-parameters/medical-history/",
            self.history_payload(),
            format="json",
        )
        self.assertEqual(history_response.status_code, 201, history_response.data)

        facility_response = self.client.post(
            "/api/v1/ol-parameters/medical-facilities/",
            self.facility_payload(partner=self.partner),
            format="json",
        )
        self.assertEqual(facility_response.status_code, 201, facility_response.data)
        facility = OLMedicalFacility.objects.get(facility_code="DAR_ES_SALAAM_MEDICAL_CENTRE")

        practitioner_response = self.client.post(
            "/api/v1/ol-parameters/medical-practitioners/",
            self.practitioner_payload(facility.pk, partner=self.partner),
            format="json",
        )
        self.assertEqual(practitioner_response.status_code, 201, practitioner_response.data)
        practitioner = OLMedicalPractitioner.objects.get(practitioner_code="DR_MEDICAL_001")

        self.assertEqual(
            self.client.get(f"/api/v1/ol-parameters/medical-codes/{medical_code.pk}/").status_code,
            200,
        )
        self.assertEqual(
            self.client.get(f"/api/v1/ol-parameters/medical-limits/{limit.pk}/").status_code,
            200,
        )
        self.assertEqual(
            self.client.get(f"/api/v1/ol-parameters/medical-practitioners/{practitioner.pk}/").status_code,
            200,
        )

        listing = self.client.get(
            "/api/v1/ol-parameters/medical-limits/"
            f"?medical_code={medical_code.pk}&product={self.product.pk}&limit_type=MEDICAL&required_frequency=ANNUAL"
        )
        self.assertEqual(listing.status_code, 200, listing.data)
        self.assertEqual(listing.data["pagination"]["total"], 1)
        self.assertEqual(listing.data["data"][0]["code"], "BASIC_MEDICAL_LIMIT")

        search = self.client.get("/api/v1/ol-parameters/medical-practitioners/?search=DR_MEDICAL_001")
        self.assertEqual(search.status_code, 200, search.data)
        self.assertEqual(search.data["pagination"]["total"], 1)

        export = self.client.get("/api/v1/ol-parameters/medical-facilities/export/?approval_status=APPROVED")
        self.assertEqual(export.status_code, 200)
        self.assertIn("text/csv", export["Content-Type"])
        self.assertIn("DAR_ES_SALAAM_MEDICAL_CENTRE", export.content.decode())

        deactivate = self.client.post(
            f"/api/v1/ol-parameters/medical-history/{OLMedicalHistory.objects.get(code='HYPERTENSION_HISTORY').pk}/deactivate/",
            {},
            format="json",
        )
        self.assertEqual(deactivate.status_code, 200, deactivate.data)
        self.assertFalse(OLMedicalHistory.objects.get(code="HYPERTENSION_HISTORY").is_active)

    def test_medical_limit_range_amount_and_dates_are_rejected(self):
        medical_code = OLMedicalCode.objects.create(
            code="RANGE_MEDICAL_CODE",
            name="Range Medical Code",
            description="Range test code.",
            medical_category="EXAMINATION",
            effective_from=date(2026, 1, 1),
        )
        invalid_instances = [
            OLMedicalLimit(
                **{
                    **self.medical_limit_payload(medical_code.pk, "INVALID_AGE_RANGE"),
                    "medical_code": medical_code,
                    "product": self.product,
                    "plan": None,
                    "effective_from": date(2026, 1, 1),
                    "effective_to": None,
                    "sum_assured_from": Decimal("0"),
                    "sum_assured_to": Decimal("100000"),
                    "age_from": 70,
                    "age_to": 65,
                    "limit_amount": Decimal("50000"),
                }
            ),
            OLMedicalLimit(
                **{
                    **self.medical_limit_payload(medical_code.pk, "INVALID_SA_RANGE"),
                    "medical_code": medical_code,
                    "product": self.product,
                    "effective_from": date(2026, 1, 1),
                    "sum_assured_from": Decimal("500000"),
                    "sum_assured_to": Decimal("100000"),
                    "limit_amount": Decimal("50000"),
                }
            ),
            OLMedicalLimit(
                **{
                    **self.medical_limit_payload(medical_code.pk, "INVALID_LIMIT_AMOUNT"),
                    "medical_code": medical_code,
                    "product": self.product,
                    "effective_from": date(2026, 1, 1),
                    "limit_amount": Decimal("0"),
                }
            ),
            OLMedicalLimit(
                **{
                    **self.medical_limit_payload(medical_code.pk, "INVALID_EFFECTIVE_DATES"),
                    "medical_code": medical_code,
                    "product": self.product,
                    "effective_from": date(2026, 12, 31),
                    "effective_to": date(2026, 1, 1),
                    "limit_amount": Decimal("50000"),
                }
            ),
        ]
        for instance in invalid_instances:
            with self.assertRaises(ValidationError):
                instance.full_clean()

    def test_overlapping_medical_limits_in_same_scope_are_rejected(self):
        medical_code = OLMedicalCode.objects.create(
            code="OVERLAP_MEDICAL_CODE",
            name="Overlap Medical Code",
            description="Overlap test code.",
            medical_category="EXAMINATION",
            effective_from=date(2026, 1, 1),
        )
        first = OLMedicalLimit(
            code="OVERLAP_LIMIT_1",
            name="Overlap Limit One",
            description="Overlap one.",
            medical_code=medical_code,
            product=self.product,
            age_from=18,
            age_to=65,
            sum_assured_from=Decimal("0"),
            sum_assured_to=Decimal("1000000"),
            limit_type="MEDICAL",
            limit_amount=Decimal("50000"),
            required_frequency="ANNUAL",
            effective_from=date(2026, 1, 1),
            effective_to=date(2026, 12, 31),
        )
        first.full_clean()
        first.save()
        second = OLMedicalLimit(
            code="OVERLAP_LIMIT_2",
            name="Overlap Limit Two",
            description="Overlap two.",
            medical_code=medical_code,
            product=self.product,
            age_from=30,
            age_to=50,
            sum_assured_from=Decimal("500000"),
            sum_assured_to=Decimal("1500000"),
            limit_type="MEDICAL",
            limit_amount=Decimal("75000"),
            required_frequency="ANNUAL",
            effective_from=date(2026, 6, 1),
            effective_to=date(2027, 5, 31),
        )
        with self.assertRaises(ValidationError):
            second.full_clean()

    def test_partner_linkage_accepts_active_partner_and_rejects_inactive_partner(self):
        facility = OLMedicalFacility(
            code="LINKED_FACILITY",
            name="Linked Facility",
            description="Linked facility.",
            partner=self.partner,
            facility_code="LINKED_FACILITY_CODE",
            facility_type="HOSPITAL",
            registration_number="REG-LINKED",
            country="TZ",
            approval_status="APPROVED",
            effective_from=date(2026, 1, 1),
        )
        facility.full_clean()
        facility.save()
        self.assertEqual(facility.partner_id, self.partner.pk)

        inactive_partner = Partner.objects.create(
            partner_number="MED-PT-INACTIVE",
            partner_type="SERVICE_PROVIDER",
            first_name="Inactive",
            surname="Partner",
            email="inactive.medical.partner@example.com",
            mobile_number="+255711000444",
            status="INACTIVE",
            is_active=False,
        )
        invalid_facility = OLMedicalFacility(
            code="INACTIVE_LINKED_FACILITY",
            name="Inactive Linked Facility",
            description="Invalid linked facility.",
            partner=inactive_partner,
            facility_code="INACTIVE_LINKED_FACILITY_CODE",
            facility_type="HOSPITAL",
            registration_number="REG-INACTIVE",
            country="TZ",
            approval_status="APPROVED",
            effective_from=date(2026, 1, 1),
        )
        with self.assertRaises(ValidationError):
            invalid_facility.full_clean()

    def test_permissions_and_audit_logs_are_enforced(self):
        created = self.client.post(
            "/api/v1/ol-parameters/medical-codes/",
            self.medical_code_payload("AUDITED_MEDICAL_CODE"),
            format="json",
            HTTP_X_REQUEST_ID="medical-audit-create",
        )
        self.assertEqual(created.status_code, 201, created.data)
        record = OLMedicalCode.objects.get(code="AUDITED_MEDICAL_CODE")
        self.assertTrue(
            AuditLog.objects.filter(
                app_label="ol_parameters",
                model_name="olmedicalcode",
                object_id=str(record.pk),
                action="CREATE",
                correlation_id="medical-audit-create",
            ).exists()
        )

        restricted_user = User.objects.create_user(
            username="ol-medical-uw-viewer",
            email="ol-medical-uw-viewer@example.com",
            password="Strong-pass-123!",
            is_active=True,
            is_approved=True,
        )
        restricted_client = APIClient()
        restricted_client.force_authenticate(restricted_user)
        self.assertEqual(
            restricted_client.get("/api/v1/ol-parameters/medical-codes/").status_code,
            403,
        )

    def test_seed_is_idempotent_and_registers_all_six_contracts(self):
        management.call_command("seed_ol_medical_underwriting", verbosity=0)
        first_counts = (
            OLMedicalCode.objects.count(),
            OLMedicalLimit.objects.count(),
            OLPersonalHabit.objects.count(),
            OLMedicalHistory.objects.count(),
            OLMedicalFacility.objects.count(),
            OLMedicalPractitioner.objects.count(),
            OLParameterTableRegistry.objects.filter(parameter_group="MEDICAL_UNDERWRITING").count(),
        )
        management.call_command("seed_ol_medical_underwriting", verbosity=0)
        second_counts = (
            OLMedicalCode.objects.count(),
            OLMedicalLimit.objects.count(),
            OLPersonalHabit.objects.count(),
            OLMedicalHistory.objects.count(),
            OLMedicalFacility.objects.count(),
            OLMedicalPractitioner.objects.count(),
            OLParameterTableRegistry.objects.filter(parameter_group="MEDICAL_UNDERWRITING").count(),
        )
        self.assertEqual(first_counts, second_counts)
        self.assertEqual(first_counts, (1, 1, 1, 1, 1, 1, 6))

    def test_admin_registration_and_table_columns_exist_for_all_six_entities(self):
        models_and_columns = {
            OLMedicalCode: "medical_category",
            OLMedicalLimit: "limit_amount",
            OLPersonalHabit: "habit_category",
            OLMedicalHistory: "condition_category",
            OLMedicalFacility: "facility_code",
            OLMedicalPractitioner: "practitioner_code",
        }
        for model, column in models_and_columns.items():
            self.assertIn(model, admin.site._registry)
            model_admin = admin.site._registry[model]
            self.assertTrue(model_admin.list_display)
            self.assertIn(column, model_admin.list_display)
