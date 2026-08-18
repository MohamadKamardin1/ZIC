from datetime import date

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.ol_parameters.models import (
    OLMedicalCode,
    OLMedicalFacility,
    OLMedicalHistory,
    OLMedicalLimit,
    OLMedicalPractitioner,
    OLParameterTableRegistry,
    OLPersonalHabit,
    OLProduct,
)


EFFECTIVE_FROM = date(2026, 1, 1)

REGISTRY_SEEDS = [
    {
        "slug": "medical-codes",
        "label": "OL Medical Codes",
        "description": "Reusable medical examination, evidence, and underwriting code catalog.",
        "model_label": "ol_parameters.OLMedicalCode",
        "visible_columns": ["code", "name", "medical_category", "effective_from", "effective_to", "is_active"],
        "searchable_fields": ["code", "name", "description", "medical_category"],
        "filter_fields": ["is_active", "medical_category", "effective_from", "effective_to"],
        "default_ordering": ["medical_category", "name", "code"],
    },
    {
        "slug": "medical-limits",
        "label": "OL Medical Limits",
        "description": "Product, plan, age, and sum-assured medical evidence limits.",
        "model_label": "ol_parameters.OLMedicalLimit",
        "visible_columns": [
            "code", "medical_code", "product", "plan", "age_from", "age_to", "sum_assured_from",
            "sum_assured_to", "limit_type", "limit_amount", "required_frequency", "mandatory_flag",
            "effective_from", "effective_to", "is_active",
        ],
        "searchable_fields": [
            "code", "name", "description", "medical_code__code", "medical_code__name",
            "limit_type", "required_frequency", "product__code", "plan__code",
        ],
        "filter_fields": [
            "is_active", "medical_code", "product", "plan", "limit_type", "required_frequency",
            "mandatory_flag", "age_from", "age_to", "effective_from", "effective_to",
        ],
        "default_ordering": ["medical_code", "product", "plan", "age_from", "sum_assured_from", "-effective_from", "code"],
    },
    {
        "slug": "personal-habits",
        "label": "OL Personal Habits",
        "description": "Personal-habit underwriting questions and evidence requirements.",
        "model_label": "ol_parameters.OLPersonalHabit",
        "visible_columns": ["code", "name", "habit_category", "underwriting_impact", "requires_evidence", "effective_from", "effective_to", "is_active"],
        "searchable_fields": ["code", "name", "description", "habit_category", "question_text", "underwriting_impact"],
        "filter_fields": ["is_active", "habit_category", "underwriting_impact", "requires_evidence", "effective_from", "effective_to"],
        "default_ordering": ["habit_category", "name", "code"],
    },
    {
        "slug": "medical-history",
        "label": "OL Medical History",
        "description": "Medical condition history catalog with default underwriting consequences.",
        "model_label": "ol_parameters.OLMedicalHistory",
        "visible_columns": ["code", "name", "condition_category", "severity", "waiting_period_days", "exclusion_flag", "loading_flag", "effective_from", "effective_to", "is_active"],
        "searchable_fields": ["code", "name", "description", "condition_category", "severity", "underwriting_note"],
        "filter_fields": ["is_active", "condition_category", "severity", "waiting_period_days", "exclusion_flag", "loading_flag", "effective_from", "effective_to"],
        "default_ordering": ["condition_category", "severity", "name", "code"],
    },
    {
        "slug": "medical-facilities",
        "label": "OL Medical Facilities",
        "description": "Medical facility catalog with optional partner master linkage.",
        "model_label": "ol_parameters.OLMedicalFacility",
        "visible_columns": ["facility_code", "name", "facility_type", "partner", "city", "country", "approval_status", "effective_from", "effective_to", "is_active"],
        "searchable_fields": [
            "code", "name", "description", "facility_code", "facility_type", "registration_number",
            "address", "city", "country", "contact_email", "contact_phone", "partner__code", "partner__legal_name",
        ],
        "filter_fields": ["is_active", "partner", "facility_type", "approval_status", "city", "country", "effective_from", "effective_to"],
        "default_ordering": ["name", "facility_code"],
    },
    {
        "slug": "medical-practitioners",
        "label": "OL Medical Practitioners",
        "description": "Medical practitioner catalog with optional partner and facility linkage.",
        "model_label": "ol_parameters.OLMedicalPractitioner",
        "visible_columns": ["practitioner_code", "first_name", "last_name", "specialty", "license_number", "medical_facility", "partner", "approval_status", "effective_from", "effective_to", "is_active"],
        "searchable_fields": [
            "code", "name", "description", "practitioner_code", "first_name", "last_name", "specialty",
            "license_number", "email", "phone", "partner__code", "partner__legal_name", "medical_facility__facility_code",
        ],
        "filter_fields": ["is_active", "partner", "medical_facility", "specialty", "approval_status", "effective_from", "effective_to"],
        "default_ordering": ["last_name", "first_name", "practitioner_code"],
    },
]


def upsert(model, lookup, defaults):
    record, created = model.objects.get_or_create(**lookup, defaults=defaults)
    for field_name, value in defaults.items():
        setattr(record, field_name, value)
    record.full_clean()
    record.save()
    return record, created


class Command(BaseCommand):
    help = "Seed idempotent OL Medical Underwriting parameters."

    @transaction.atomic
    def handle(self, *args, **options):
        product = OLProduct.objects.filter(code="STANDARD_ENDOWMENT").first()
        if product is None:
            call_command("seed_ol_product_setup", verbosity=0)
            product = OLProduct.objects.get(code="STANDARD_ENDOWMENT")

        medical_code, medical_code_created = upsert(
            OLMedicalCode,
            {"code": "BASIC_MEDICAL_EXAMINATION"},
            {
                "name": "Basic Medical Examination",
                "description": "Starter medical evidence code pending underwriting governance approval.",
                "medical_category": "EXAMINATION",
                "effective_from": EFFECTIVE_FROM,
                "effective_to": None,
                "is_active": True,
            },
        )

        medical_limit, medical_limit_created = upsert(
            OLMedicalLimit,
            {"code": "STANDARD_ENDOWMENT_BASIC_MEDICAL_LIMIT"},
            {
                "name": "Standard Endowment Basic Medical Limit",
                "description": "Starter medical examination limit pending product and underwriting approval.",
                "medical_code": medical_code,
                "product": product,
                "plan": None,
                "age_from": 18,
                "age_to": 65,
                "sum_assured_from": 0,
                "sum_assured_to": 50000000,
                "limit_type": "MEDICAL",
                "limit_amount": 50000,
                "required_frequency": "ANNUAL",
                "mandatory_flag": True,
                "effective_from": EFFECTIVE_FROM,
                "effective_to": None,
                "is_active": True,
            },
        )

        habit, habit_created = upsert(
            OLPersonalHabit,
            {"code": "SMOKING_HISTORY"},
            {
                "name": "Smoking History",
                "description": "Starter smoking-history question pending underwriting governance approval.",
                "habit_category": "SMOKING",
                "question_text": "Have you used tobacco or nicotine products during the last twelve months?",
                "underwriting_impact": "HIGH",
                "requires_evidence": True,
                "effective_from": EFFECTIVE_FROM,
                "effective_to": None,
                "is_active": True,
            },
        )

        history, history_created = upsert(
            OLMedicalHistory,
            {"code": "HYPERTENSION_HISTORY"},
            {
                "name": "Hypertension History",
                "description": "Starter medical-history condition pending underwriting governance approval.",
                "condition_category": "CARDIOVASCULAR",
                "severity": "MODERATE",
                "waiting_period_days": 0,
                "exclusion_flag": False,
                "loading_flag": True,
                "underwriting_note": "Obtain recent medical evidence and treatment history.",
                "effective_from": EFFECTIVE_FROM,
                "effective_to": None,
                "is_active": True,
            },
        )

        facility, facility_created = upsert(
            OLMedicalFacility,
            {"code": "DAR_ES_SALAAM_MEDICAL_CENTRE"},
            {
                "name": "Dar es Salaam Medical Centre",
                "description": "Starter medical facility pending partner onboarding and approval.",
                "partner": None,
                "facility_code": "FAC_DSM_MEDICAL_CENTRE",
                "facility_type": "HOSPITAL",
                "registration_number": "STARTER-FACILITY-001",
                "address": "Dar es Salaam",
                "city": "Dar es Salaam",
                "country": "TZ",
                "contact_email": "medical.centre@example.invalid",
                "contact_phone": "+255000000000",
                "approval_status": "PENDING",
                "effective_from": EFFECTIVE_FROM,
                "effective_to": None,
                "is_active": True,
            },
        )

        practitioner, practitioner_created = upsert(
            OLMedicalPractitioner,
            {"code": "DR_STARTER_UNDERWRITING"},
            {
                "name": "Dr Starter Underwriting",
                "description": "Starter medical practitioner pending partner onboarding and approval.",
                "partner": None,
                "practitioner_code": "PRAC_STARTER_001",
                "first_name": "Starter",
                "last_name": "Underwriting",
                "specialty": "GENERAL_MEDICINE",
                "license_number": "TZ-MED-STARTER-001",
                "medical_facility": facility,
                "email": "practitioner@example.invalid",
                "phone": "+255000000001",
                "approval_status": "PENDING",
                "effective_from": EFFECTIVE_FROM,
                "effective_to": None,
                "is_active": True,
            },
        )

        registry_defaults = {
            "parameter_group": "MEDICAL_UNDERWRITING",
            "allowed_actions": ["view", "create", "update", "deactivate", "configure"],
            "export_support": True,
            "permission_code": "ol_parameters.view",
            "permission_requirements": {
                "view": "ol_parameters.view",
                "create": "ol_parameters.create",
                "update": "ol_parameters.update",
                "deactivate": "ol_parameters.deactivate",
                "configure": "ol_parameters.configure",
            },
            "is_active": True,
        }
        for metadata in REGISTRY_SEEDS:
            upsert(OLParameterTableRegistry, {"slug": metadata["slug"]}, {**metadata, **registry_defaults})

        self.stdout.write(
            self.style.SUCCESS(
                "Seeded OL Medical Underwriting: "
                f"medical_code_created={medical_code_created}, "
                f"medical_limit_created={medical_limit_created}, "
                f"habit_created={habit_created}, "
                f"history_created={history_created}, "
                f"facility_created={facility_created}, "
                f"practitioner_created={practitioner_created}, "
                f"registry_contracts={len(REGISTRY_SEEDS)}."
            )
        )
