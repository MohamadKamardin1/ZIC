from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.group_credit.models import (
    GCHealthQuestion,
    GCHealthQuestionnaire,
    GCSchemeMemberStatus,
    GCSchemePremiumRate,
    GCSchemeRenewalStatus,
    GCSchemeStatus,
    GCSchemeType,
)

EFFECTIVE_FROM = date(2026, 1, 1)

SCHEME_TYPES = [
    {"code": "MORTGAGE_PROTECTION", "name": "Mortgage Protection", "description": "Credit life cover on mortgage loans disbursed by banks.", "partner_type_restriction": "BANK"},
    {"code": "BANK_LOAN", "name": "Bank Loan", "description": "Credit life cover on personal and asset loans issued by banks.", "partner_type_restriction": "BANK"},
    {"code": "CORPORATE_SALARY", "name": "Corporate Salary", "description": "Credit life and loan protection for corporate salary-based lending.", "partner_type_restriction": "CORPORATE"},
    {"code": "HIRE_PURCHASE", "name": "Hire Purchase", "description": "Cover for hire purchase and asset finance schemes.", "partner_type_restriction": "BANK"},
]

SCHEME_STATUSES = [
    {"code": "PENDING_MEDICAL", "name": "Pending Medical", "description": "Scheme awaits medical underwriting completion.", "display_order": 10, "is_terminal": False},
    {"code": "ACTIVE", "name": "Active", "description": "Scheme is active and issuing business.", "display_order": 20, "is_terminal": False},
    {"code": "INACTIVE", "name": "Inactive", "description": "Scheme is temporarily suspended.", "display_order": 30, "is_terminal": False},
    {"code": "TERMINATED", "name": "Terminated", "description": "Scheme has been terminated and no new business is written.", "display_order": 40, "is_terminal": True},
]

MEMBER_STATUSES = [
    {"code": "PENDING_MEDICAL", "name": "Pending Medical", "description": "Member awaits medical underwriting.", "display_order": 10, "is_terminal": False, "allows_claims": False},
    {"code": "ACTIVE", "name": "Active", "description": "Member cover is in force.", "display_order": 20, "is_terminal": False, "allows_claims": True},
    {"code": "INACTIVE", "name": "Inactive", "description": "Member cover is suspended.", "display_order": 30, "is_terminal": False, "allows_claims": False},
    {"code": "DECEASED", "name": "Deceased", "description": "Member has passed away; claims are eligible.", "display_order": 40, "is_terminal": True, "allows_claims": True},
]

RENEWAL_STATUSES = [
    {"code": "PENDING", "name": "Pending", "description": "Renewal has been raised and awaits review.", "display_order": 10},
    {"code": "APPROVED", "name": "Approved", "description": "Renewal has been approved.", "display_order": 20},
    {"code": "DECLINED", "name": "Declined", "description": "Renewal has been declined.", "display_order": 30},
    {"code": "RENEWED", "name": "Renewed", "description": "Scheme has been renewed for a further term.", "display_order": 40},
]

PREMIUM_RATES = [
    {"name": "Standard Unit Rate - Mortgage", "scheme_type_code": "MORTGAGE_PROTECTION", "rate_type": "UNIT", "rate_value": "2.500000", "currency": "TZS", "age_band_start": 18, "age_band_end": 60, "gender": "U"},
    {"name": "Standard Unit Rate - Bank Loan", "scheme_type_code": "BANK_LOAN", "rate_type": "UNIT", "rate_value": "3.000000", "currency": "TZS", "age_band_start": 18, "age_band_end": 65, "gender": "U"},
    {"name": "Standard Unit Rate - Corporate Salary", "scheme_type_code": "CORPORATE_SALARY", "rate_type": "UNIT", "rate_value": "2.250000", "currency": "TZS", "age_band_start": 18, "age_band_end": 55, "gender": "U"},
    {"name": "Standard Unit Rate - Hire Purchase", "scheme_type_code": "HIRE_PURCHASE", "rate_type": "UNIT", "rate_value": "3.750000", "currency": "TZS", "age_band_start": 18, "age_band_end": 60, "gender": "U"},
    {"name": "Standard Flat Rate - Bank Loan", "scheme_type_code": "BANK_LOAN", "rate_type": "FLAT", "rate_value": "150000.000000", "currency": "TZS", "age_band_start": 18, "age_band_end": 65, "gender": "U"},
]

HEALTH_QUESTIONS = [
    {"code": "SMOKING", "question_text": "Do you currently smoke or use tobacco products?", "answer_type": "BOOLEAN", "required": True, "category": "LIFESTYLE", "sort_order": 10},
    {"code": "ALCOHOL", "question_text": "Do you regularly consume alcohol?", "answer_type": "BOOLEAN", "required": False, "category": "LIFESTYLE", "sort_order": 20},
    {"code": "HYPERTENSION", "question_text": "Have you ever been diagnosed with high blood pressure?", "answer_type": "BOOLEAN", "required": True, "category": "SPECIFIC", "sort_order": 30},
    {"code": "DIABETES", "question_text": "Have you ever been diagnosed with diabetes?", "answer_type": "BOOLEAN", "required": True, "category": "SPECIFIC", "sort_order": 40},
    {"code": "OCCUPATION", "question_text": "Describe your current occupation.", "answer_type": "TEXT", "required": False, "category": "GENERAL", "sort_order": 50},
]

QUESTIONNAIRE = {
    "code": "GC_CREDIT_LIFE_HQ_V1",
    "name": "GC Credit Life Health Questionnaire",
    "description": "Standard medical questionnaire for Group Credit credit-life underwriting.",
    "version": "1.0",
    "scheme_type_code": "BANK_LOAN",
    "threshold_trigger_amount": "50000000.00",
    "question_codes": ["SMOKING", "ALCOHOL", "HYPERTENSION", "DIABETES", "OCCUPATION"],
}


def upsert(model, lookup, defaults):
    record, _ = model.objects.get_or_create(**lookup, defaults=defaults)
    for field_name, value in defaults.items():
        setattr(record, field_name, value)
    record.full_clean()
    record.save()
    return record


class Command(BaseCommand):
    help = "Seed idempotent GC Parameters (scheme setup) reference data."

    @transaction.atomic
    def handle(self, *args, **options):
        scheme_types = {}
        for payload in SCHEME_TYPES:
            scheme_types[payload["code"]] = upsert(
                GCSchemeType,
                {"code": payload["code"]},
                payload,
            )

        for payload in SCHEME_STATUSES:
            upsert(GCSchemeStatus, {"code": payload["code"]}, payload)

        for payload in MEMBER_STATUSES:
            upsert(GCSchemeMemberStatus, {"code": payload["code"]}, payload)

        for payload in RENEWAL_STATUSES:
            upsert(GCSchemeRenewalStatus, {"code": payload["code"]}, payload)

        for payload in PREMIUM_RATES:
            scheme = scheme_types[payload["scheme_type_code"]]
            defaults = {key: value for key, value in payload.items() if key != "scheme_type_code"}
            defaults["scheme_type"] = scheme
            defaults["effective_from"] = EFFECTIVE_FROM
            defaults["effective_to"] = None
            defaults["effective_date"] = EFFECTIVE_FROM
            defaults["expiry_date"] = None
            upsert(
                GCSchemePremiumRate,
                {"name": payload["name"], "scheme_type": scheme},
                defaults,
            )

        questions = {}
        for payload in HEALTH_QUESTIONS:
            questions[payload["code"]] = upsert(
                GCHealthQuestion,
                {"code": payload["code"]},
                payload,
            )

        questionnaire = upsert(
            GCHealthQuestionnaire,
            {"code": QUESTIONNAIRE["code"]},
            {
                "name": QUESTIONNAIRE["name"],
                "description": QUESTIONNAIRE["description"],
                "version": QUESTIONNAIRE["version"],
                "scheme_type_ref": scheme_types[QUESTIONNAIRE["scheme_type_code"]],
                "threshold_trigger_amount": QUESTIONNAIRE["threshold_trigger_amount"],
                "effective_date": EFFECTIVE_FROM,
                "effective_from": EFFECTIVE_FROM,
                "is_active": True,
            },
        )
        questionnaire.questions.set([questions[code] for code in QUESTIONNAIRE["question_codes"]])

        self.stdout.write(
            self.style.SUCCESS(
                f"GC Parameters seeded: {len(scheme_types)} scheme types, "
                f"{len(SCHEME_STATUSES)} scheme statuses, {len(MEMBER_STATUSES)} member statuses, "
                f"{len(RENEWAL_STATUSES)} renewal statuses, {len(PREMIUM_RATES)} premium rates, "
                f"{len(HEALTH_QUESTIONS)} health questions, 1 questionnaire."
            )
        )
