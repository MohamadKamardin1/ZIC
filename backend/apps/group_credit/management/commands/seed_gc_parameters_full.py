"""
Seed the complete GC Parameters catalog to support the Group Credit workflow.

Runs the Prompt-1 scheme-setup base (``seed_gc_parameters``), then idempotently
seeds the remaining categories: products + product-scoped unit rates, riders and
rider rates, medical underwriting catalogs (conditions, ICD-10 codes, limits,
decisions, habits, facilities, practitioners), and claim setup (types, reasons,
statuses, discharge types, correspondent types).

Reference ``EFFECTIVE_FROM`` applies to every dated row so a re-run converges on
the same seed rather than appending new effective windows.

``python manage.py seed_gc_parameters_full``  — idempotent; safe to run any time.
"""

from datetime import date

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction

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
    GCProduct,
    GCRider,
    GCRiderRate,
    GCSchemePremiumRate,
    GCSchemeType,
    GCSubProduct,
    GCUnderwritingDecision,
)
from apps.partners.models import Partner

EFFECTIVE_FROM = date(2026, 1, 1)


def upsert(model, lookup, defaults):
    """get_or_create on the natural key, then apply defaults so re-runs converge."""
    record, _ = model.objects.get_or_create(**lookup, defaults=defaults)
    for field_name, value in defaults.items():
        setattr(record, field_name, value)
    record.full_clean()
    record.save()
    return record


def upsert_partner(payload):
    """Create/update a Partner. Partners bypass full_clean (mirrors test helpers)."""
    defaults = {key: value for key, value in payload.items() if key != "partner_number"}
    partner, _ = Partner.objects.get_or_create(
        partner_number=payload["partner_number"], defaults=defaults
    )
    for field_name, value in defaults.items():
        setattr(partner, field_name, value)
    partner.save()
    return partner


SUB_PRODUCTS = [
    {"code": "GROUP_CREDIT_LIFE", "name": "Group Credit Life"},
]

PRODUCTS = [
    {
        "code": "CREDIT_LIFE_A",
        "name": "Credit Life Plan A",
        "description": "Standard credit-life plan for bank personal and asset loans, terms up to 20 years.",
        "sub_product_code": "GROUP_CREDIT_LIFE",
        "scheme_type_code": "BANK_LOAN",
        "insurance_class": "CREDIT_LIFE",
        "currency": "TZS",
        "min_members": 1,
        "max_members": 500,
        "min_loan_amount": "100000.00",
        "max_loan_amount": "100000000.00",
        "min_loan_term": 6,
        "max_loan_term": 240,
        "min_entry_age": 18,
        "max_entry_age": 65,
        "max_cover_age": 70,
        "free_cover_limit": "2000000.00",
        "premium_basis": "SINGLE",
        "requires_medical": False,
    },
    {
        "code": "CREDIT_LIFE_B",
        "name": "Credit Life Plan B",
        "description": "Enhanced credit-life plan for corporate salary lending, terms up to 30 years with medical underwriting.",
        "sub_product_code": "GROUP_CREDIT_LIFE",
        "scheme_type_code": "CORPORATE_SALARY",
        "insurance_class": "CREDIT_LIFE",
        "currency": "TZS",
        "min_members": 1,
        "max_members": 2000,
        "min_loan_amount": "100000.00",
        "max_loan_amount": "200000000.00",
        "min_loan_term": 12,
        "max_loan_term": 360,
        "min_entry_age": 18,
        "max_entry_age": 60,
        "max_cover_age": 70,
        "free_cover_limit": "5000000.00",
        "premium_basis": "SINGLE",
        "requires_medical": True,
    },
]

# Product-scoped standard unit rates (per mille of sum assured). The unit rate is
# term-independent: it prices any loan term inside the product's 1-30 year window.
PRODUCT_PREMIUM_RATES = [
    {
        "name": "Credit Life Plan A - Standard Unit Rate",
        "scheme_type_code": "BANK_LOAN",
        "product_code": "CREDIT_LIFE_A",
        "rate_type": "UNIT",
        "rate_value": "3.200000",
        "currency": "TZS",
        "age_band_start": 18,
        "age_band_end": 65,
        "gender": "U",
    },
    {
        "name": "Credit Life Plan B - Standard Unit Rate",
        "scheme_type_code": "CORPORATE_SALARY",
        "product_code": "CREDIT_LIFE_B",
        "rate_type": "UNIT",
        "rate_value": "2.000000",
        "currency": "TZS",
        "age_band_start": 18,
        "age_band_end": 60,
        "gender": "U",
    },
]

RIDERS = [
    {
        "code": "ACCIDENTAL_DEATH_BENEFIT",
        "name": "Accidental Death Benefit",
        "description": "Pays an additional sum assured on death caused by accident.",
        "rider_category": "ACCIDENTAL_DEATH",
        "benefit_type": "PERCENTAGE",
        "requires_underwriting": False,
        "is_mandatory": False,
    },
    {
        "code": "PERMANENT_DISABILITY",
        "name": "Permanent Disability",
        "description": "Pays a percentage of sum assured on permanent total disability.",
        "rider_category": "DISABILITY",
        "benefit_type": "PERCENTAGE",
        "requires_underwriting": True,
        "is_mandatory": False,
    },
]

# One rate per rider per flagship product. PERCENTAGE rates are a share of the
# base sum assured and are identical across age bands in this standard catalog.
RIDER_RATES = [
    {"rider_code": "ACCIDENTAL_DEATH_BENEFIT", "product_code": "CREDIT_LIFE_A", "rate_value": "100.000000", "age_band_start": 18, "age_band_end": 65},
    {"rider_code": "ACCIDENTAL_DEATH_BENEFIT", "product_code": "CREDIT_LIFE_B", "rate_value": "100.000000", "age_band_start": 18, "age_band_end": 60},
    {"rider_code": "PERMANENT_DISABILITY", "product_code": "CREDIT_LIFE_A", "rate_value": "100.000000", "age_band_start": 18, "age_band_end": 65},
    {"rider_code": "PERMANENT_DISABILITY", "product_code": "CREDIT_LIFE_B", "rate_value": "100.000000", "age_band_start": 18, "age_band_end": 60},
]

MEDICAL_HISTORIES = [
    {"code": "HYPERTENSION", "name": "Hypertension", "condition_category": "CARDIOVASCULAR", "severity": "MEDIUM", "waiting_period_days": 0, "exclusion_flag": False, "risk_impact": "MEDIUM"},
    {"code": "DIABETES", "name": "Diabetes Mellitus", "condition_category": "METABOLIC", "severity": "HIGH", "waiting_period_days": 0, "exclusion_flag": False, "risk_impact": "HIGH"},
    {"code": "ISCHEMIC_HEART_DISEASE", "name": "Ischaemic Heart Disease", "condition_category": "CARDIOVASCULAR", "severity": "HIGH", "waiting_period_days": 0, "exclusion_flag": False, "risk_impact": "HIGH"},
    {"code": "CANCER", "name": "Cancer", "condition_category": "ONCOLOGY", "severity": "CRITICAL", "waiting_period_days": 0, "exclusion_flag": True, "risk_impact": "DECLINE"},
]

MEDICAL_CODES = [
    {"code": "I10", "name": "Essential (primary) hypertension", "icd10_code": "I10", "category": "ICD_10", "description": "ICD-10 code for high blood pressure."},
    {"code": "E11", "name": "Type 2 diabetes mellitus", "icd10_code": "E11", "category": "ICD_10", "description": "ICD-10 code for non-insulin-dependent diabetes."},
    {"code": "I21", "name": "Acute myocardial infarction", "icd10_code": "I21", "category": "ICD_10", "description": "ICD-10 code for heart attack."},
    {"code": "C50", "name": "Malignant neoplasm of breast", "icd10_code": "C50", "category": "ICD_10", "description": "ICD-10 code for breast cancer."},
]

MEDICAL_LIMITS = [
    {"scheme_type_code": "BANK_LOAN", "medical_code_code": "I10", "limit_amount": "5000000.00", "age_min": 18, "age_max": 65, "description": "Standard hypertension cover limit."},
    {"scheme_type_code": "BANK_LOAN", "medical_code_code": "E11", "limit_amount": "3000000.00", "age_min": 18, "age_max": 65, "description": "Standard diabetes cover limit."},
]

UW_DECISIONS = [
    {"code": "STANDARD", "name": "Standard", "description": "Accept at standard rates.", "requires_review": False, "display_order": 10},
    {"code": "LOADING", "name": "Rate Loading", "description": "Accept with a premium loading.", "requires_review": True, "display_order": 20},
    {"code": "DECLINE", "name": "Decline", "description": "Decline cover on disclosed risk.", "requires_review": True, "display_order": 30},
]

PERSONAL_HABITS = [
    {"code": "SMOKING", "name": "Smoking", "habit_category": "SMOKING", "underwriting_impact": "HIGH", "risk_level": "HIGH"},
    {"code": "ALCOHOL", "name": "Alcohol Consumption", "habit_category": "ALCOHOL", "underwriting_impact": "MEDIUM", "risk_level": "MEDIUM"},
]

PARTNERS = [
    {
        "partner_number": "PTN-DSM-GENERAL-HOSP",
        "partner_type": "CORPORATE",
        "partner_category": "CORPORATE",
        "party_type": "CORPORATE",
        "legal_name": "Dar es Salaam General Hospital Ltd",
        "company_name": "Dar es Salaam General Hospital Ltd",
        "email": "ptn-dsm-general-hosp@test.local",
        "mobile_number": "+255700000111",
        "phone": "+255222111000",
        "physical_address": "Ocean Road, Dar es Salaam",
        "industry": "HEALTHCARE",
    },
    {
        "partner_number": "PTN-UHURU-CLINIC",
        "partner_type": "CORPORATE",
        "partner_category": "CORPORATE",
        "party_type": "CORPORATE",
        "legal_name": "Uhuru Medical Clinic",
        "company_name": "Uhuru Medical Clinic",
        "email": "ptn-uhuru-clinic@test.local",
        "mobile_number": "+255700000222",
        "phone": "+255222111222",
        "physical_address": "Uhuru Street, Dar es Salaam",
        "industry": "HEALTHCARE",
    },
]

FACILITIES = [
    {
        "code": "DSM-GENERAL-HOSP",
        "name": "Dar es Salaam General Hospital",
        "facility_type": "HOSPITAL",
        "approval_status": "APPROVED",
        "partner_number": "PTN-DSM-GENERAL-HOSP",
        "address": "Ocean Road, Dar es Salaam",
        "city": "Dar es Salaam",
        "region": "Dar es Salaam",
        "phone": "+255222111000",
        "contact_person": "Hospital Administrator",
    },
    {
        "code": "UHURU-CLINIC",
        "name": "Uhuru Medical Clinic",
        "facility_type": "CLINIC",
        "approval_status": "APPROVED",
        "partner_number": "PTN-UHURU-CLINIC",
        "address": "Uhuru Street, Dar es Salaam",
        "city": "Dar es Salaam",
        "region": "Dar es Salaam",
        "phone": "+255222111222",
        "contact_person": "Clinic Manager",
    },
]

PRACTITIONERS = [
    {
        "code": "DR-J-MWANZA",
        "first_name": "Jane",
        "last_name": "Mwanza",
        "name": "Jane Mwanza",
        "specialization": "CARDIOLOGY",
        "license_number": "TZ-MED-001234",
        "facility_code": "DSM-GENERAL-HOSP",
        "approval_status": "APPROVED",
        "email": "dr.jane.mwanza@test.local",
        "phone": "+255700111333",
    },
    {
        "code": "DR-P-KAVISHE",
        "first_name": "Peter",
        "last_name": "Kavishe",
        "name": "Peter Kavishe",
        "specialization": "GENERAL_PRACTICE",
        "license_number": "TZ-MED-002345",
        "facility_code": "UHURU-CLINIC",
        "approval_status": "APPROVED",
        "email": "dr.peter.kavishe@test.local",
        "phone": "+255700111444",
    },
]

CLAIM_TYPES = [
    {"code": "DEATH", "name": "Death", "description": "Benefit on the death of a covered member.", "category": "DEATH", "calculation_basis": "SUM_ASSURED", "requires_document_check": True, "requires_medical_report": True},
    {"code": "PTD", "name": "Permanent Total Disability", "description": "Benefit on permanent total disability of a covered member.", "category": "PERMANENT_DISABILITY", "calculation_basis": "PERCENTAGE_OF_SUM_ASSURED", "requires_document_check": True, "requires_medical_report": True},
]

CLAIM_REASONS = [
    {"code": "DEATH_NATURAL", "name": "Natural Causes", "claim_type_code": "DEATH", "category": "ILLNESS", "description": "Death from natural causes or illness."},
    {"code": "DEATH_ACCIDENT", "name": "Accident", "claim_type_code": "DEATH", "category": "ACCIDENT", "description": "Death caused by accident."},
    {"code": "PTD_ACCIDENT", "name": "Accident", "claim_type_code": "PTD", "category": "ACCIDENT", "description": "Permanent disability caused by accident."},
    {"code": "PTD_ILLNESS", "name": "Illness", "claim_type_code": "PTD", "category": "ILLNESS", "description": "Permanent disability caused by illness."},
]

CLAIM_STATUSES = [
    {"code": "REGISTERED", "name": "Registered", "description": "Claim has been registered.", "display_order": 10, "is_terminal": False},
    {"code": "UNDER_REVIEW", "name": "Under Review", "description": "Claim is being assessed.", "display_order": 20, "is_terminal": False},
    {"code": "APPROVED", "name": "Approved", "description": "Claim has been approved for payment.", "display_order": 30, "is_terminal": False},
    {"code": "PAID", "name": "Paid", "description": "Claim has been paid.", "display_order": 40, "is_terminal": True},
    {"code": "REJECTED", "name": "Rejected", "description": "Claim has been rejected.", "display_order": 50, "is_terminal": True},
]

DISCHARGE_TYPES = [
    {"code": "SETTLEMENT", "name": "Settlement", "description": "Discharge letter for a settled claim.", "template_code": "DISCHARGE_DEFAULT", "variables": {"clause": "full_final_settlement"}},
    {"code": "REJECTION", "name": "Rejection", "description": "Discharge letter for a rejected claim.", "template_code": "REJECTION_LETTER", "variables": {}},
]

CORRESPONDENT_TYPES = [
    {"code": "MEMBER_EMAIL", "name": "Member email", "description": "Email to the member or beneficiary.", "category": "MEMBER", "communication_channel": "EMAIL", "purpose": "CLAIM_NOTIFICATION"},
    {"code": "PARTNER_EMAIL", "name": "Partner email", "description": "Email to the scheme partner (bank/corporate).", "category": "PARTNER", "communication_channel": "EMAIL", "purpose": "DOCUMENT_REQUEST"},
]


class Command(BaseCommand):
    help = "Seed the complete GC Parameters catalog for the Group Credit workflow."

    @transaction.atomic
    def handle(self, *args, **options):
        call_command("seed_gc_parameters", verbosity=0)

        scheme_types = {
            code: GCSchemeType.objects.get(code=code) for code in
            ("BANK_LOAN", "CORPORATE_SALARY", "MORTGAGE_PROTECTION", "HIRE_PURCHASE")
        }

        # --- Products (require a sub-product and a scheme type) ---
        sub_products = {
            p["code"]: upsert(GCSubProduct, {"code": p["code"]}, p) for p in SUB_PRODUCTS
        }
        products = {}
        for payload in PRODUCTS:
            defaults = {k: v for k, v in payload.items() if k not in ("sub_product_code", "scheme_type_code")}
            defaults["sub_product"] = sub_products[payload["sub_product_code"]]
            defaults["scheme_type_ref"] = scheme_types[payload["scheme_type_code"]]
            product = upsert(GCProduct, {"code": payload["code"]}, defaults)
            products[payload["code"]] = product

        # --- Product-scoped unit rates bind a rate to each flagship product ---
        for payload in PRODUCT_PREMIUM_RATES:
            defaults = {k: v for k, v in payload.items() if k not in ("scheme_type_code", "product_code")}
            defaults["scheme_type"] = scheme_types[payload["scheme_type_code"]]
            defaults["product_ref"] = products[payload["product_code"]]
            defaults["effective_date"] = EFFECTIVE_FROM
            defaults["effective_from"] = EFFECTIVE_FROM
            defaults["effective_to"] = None
            defaults["expiry_date"] = None
            upsert(GCSchemePremiumRate, {"name": payload["name"]}, defaults)

        # --- Riders and their product-scoped rates ---
        riders = {}
        for payload in RIDERS:
            riders[payload["code"]] = upsert(GCRider, {"code": payload["code"]}, payload)
        for payload in RIDER_RATES:
            defaults = {k: v for k, v in payload.items() if k not in ("rider_code", "product_code")}
            defaults["rider"] = riders[payload["rider_code"]]
            defaults["product_ref"] = products[payload["product_code"]]
            defaults["rate_type"] = "PERCENTAGE"
            defaults["currency"] = "TZS"
            defaults["gender"] = "U"
            defaults["effective_date"] = EFFECTIVE_FROM
            defaults["effective_from"] = EFFECTIVE_FROM
            defaults["effective_to"] = None
            defaults["expiry_date"] = None
            upsert(
                GCRiderRate,
                {"rider": defaults["rider"], "product_ref": defaults["product_ref"]},
                defaults,
            )

        # --- Medical underwriting catalogs ---
        for payload in MEDICAL_HISTORIES:
            upsert(GCMedicalHistory, {"code": payload["code"]}, payload)

        medical_codes = {}
        for payload in MEDICAL_CODES:
            medical_codes[payload["code"]] = upsert(GCMedicalCode, {"code": payload["code"]}, payload)

        for payload in MEDICAL_LIMITS:
            defaults = {k: v for k, v in payload.items() if k not in ("scheme_type_code", "medical_code_code")}
            defaults["scheme_type_ref"] = scheme_types[payload["scheme_type_code"]]
            defaults["medical_code_ref"] = medical_codes[payload["medical_code_code"]]
            upsert(
                GCMedicalLimit,
                {"scheme_type_ref": defaults["scheme_type_ref"], "medical_code_ref": defaults["medical_code_ref"]},
                defaults,
            )

        for payload in UW_DECISIONS:
            upsert(GCUnderwritingDecision, {"code": payload["code"]}, payload)

        for payload in PERSONAL_HABITS:
            upsert(GCPersonalHabit, {"code": payload["code"]}, payload)

        # --- Medical facilities and practitioners (need Partner rows) ---
        partner_by_number = {p["partner_number"]: upsert_partner(p) for p in PARTNERS}
        facilities = {}
        for payload in FACILITIES:
            defaults = {k: v for k, v in payload.items() if k != "partner_number"}
            defaults["partner_ref"] = partner_by_number[payload["partner_number"]]
            facilities[payload["code"]] = upsert(GCMedicalFacility, {"code": payload["code"]}, defaults)

        for payload in PRACTITIONERS:
            defaults = {k: v for k, v in payload.items() if k != "facility_code"}
            defaults["facility"] = facilities[payload["facility_code"]]
            upsert(GCMedicalPractitioner, {"code": payload["code"]}, defaults)

        # --- Claim setup ---
        claim_types = {}
        for payload in CLAIM_TYPES:
            claim_types[payload["code"]] = upsert(GCClaimType, {"code": payload["code"]}, payload)

        for payload in CLAIM_REASONS:
            defaults = {k: v for k, v in payload.items() if k != "claim_type_code"}
            defaults["claim_type"] = claim_types[payload["claim_type_code"]]
            upsert(GCClaimReason, {"code": payload["code"]}, defaults)

        for payload in CLAIM_STATUSES:
            upsert(GCClaimStatus, {"code": payload["code"]}, payload)

        for payload in DISCHARGE_TYPES:
            upsert(GCDischargeType, {"code": payload["code"]}, payload)

        for payload in CORRESPONDENT_TYPES:
            upsert(GCCorrespondentType, {"code": payload["code"]}, payload)

        self.stdout.write(
            self.style.SUCCESS(
                f"GC Parameters full seed complete: {len(sub_products)} sub-products, "
                f"{len(PRODUCTS)} products, {len(RIDERS)} riders, "
                f"{len(MEDICAL_HISTORIES)} medical conditions, {len(MEDICAL_CODES)} ICD-10 codes, "
                f"{len(MEDICAL_LIMITS)} medical limits, {len(UW_DECISIONS)} UW decisions, "
                f"{len(FACILITIES)} facilities, {len(PRACTITIONERS)} practitioners, "
                f"{len(CLAIM_TYPES)} claim types, {len(CLAIM_REASONS)} claim reasons, "
                f"{len(CLAIM_STATUSES)} claim statuses, {len(DISCHARGE_TYPES)} discharge types, "
                f"{len(CORRESPONDENT_TYPES)} correspondent types."
            )
        )
