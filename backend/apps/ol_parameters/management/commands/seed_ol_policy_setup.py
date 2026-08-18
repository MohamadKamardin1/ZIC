from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.ol_parameters.models import (
    OLAnticipatedEndowmentInstallmentRate,
    OLBeneficialType,
    OLGracePeriod,
    OLGracePeriodNotificationSchedule,
    OLHealthQuestion,
    OLHealthQuestionnaire,
    OLHealthQuestionnaireItem,
    OLMemberCoverConfiguration,
    OLParameterTableRegistry,
    OLCommitmentStatus,
    OLPaidUpRate,
    OLPaidUpSetup,
    OLSurrenderSetup,
    OLSurrenderValueRate,
    OLPolicyRenewalStatus,
    OLPolicyStatus,
    OLReinstatementWindow,
)
from apps.ordinary_life.models import OLPlan, OLProduct


EFFECTIVE_FROM = date(2026, 1, 1)

POLICY_STATUS_SEEDS = [
    ("DRAFT", "Draft", False, "NEUTRAL", ["ACTIVE", "CANCELLED"]),
    ("ACTIVE", "Active", False, "POSITIVE", ["LAPSED", "SURRENDERED", "PAID_UP", "MATURED", "CANCELLED", "CLAIMED"]),
    ("LAPSED", "Lapsed", False, "WARNING", ["ACTIVE", "CANCELLED", "SURRENDERED", "CLAIMED"]),
    ("SURRENDERED", "Surrendered", True, "NEUTRAL", []),
    ("PAID_UP", "Paid up", False, "POSITIVE", ["MATURED", "SURRENDERED", "CLAIMED"]),
    ("MATURED", "Matured", True, "POSITIVE", []),
    ("CANCELLED", "Cancelled", True, "NEGATIVE", []),
    ("CLAIMED", "Claimed", True, "POSITIVE", []),
]

RENEWAL_STATUS_SEEDS = [
    ("NOT_DUE", "Not due", "NONE"),
    ("DUE", "Due", "RENEWAL_REQUIRED"),
    ("RENEWED", "Renewed", "RENEWAL_CREATED"),
    ("NOT_RENEWED", "Not renewed", "LAPSE_POLICY"),
]

BENEFICIAL_TYPE_SEEDS = [
    ("SPOUSE", "Spouse", "BENEFICIARY", "PERCENTAGE", Decimal("0"), True),
    ("CHILD", "Child", "BENEFICIARY", "PERCENTAGE", Decimal("0"), True),
    ("PARENT", "Parent", "BENEFICIARY", "PERCENTAGE", Decimal("0"), True),
    ("TRUSTEE", "Trustee", "BENEFICIARY", "PERCENTAGE", Decimal("0"), False),
    ("OTHER", "Other", "BENEFICIARY", "PERCENTAGE", Decimal("0"), True),
    ("DEATH_BENEFIT", "Death benefit", "BENEFIT", "SUM_ASSURED", Decimal("100"), False),
    ("MATURITY_BENEFIT", "Maturity benefit", "BENEFIT", "SUM_ASSURED", Decimal("100"), False),
]

REGISTRY_SEEDS = [
    {
        "slug": "anticipated-endowment-rates",
        "label": "Anticipated Endowment Installment Rates",
        "description": "Effective-dated product, plan, age, term, policy-year, frequency, and currency rate factors.",
        "model_label": "ol_parameters.OLAnticipatedEndowmentInstallmentRate",
        "visible_columns": ["code", "name", "product", "plan", "frequency", "rate_factor", "effective_from", "effective_to", "is_active"],
        "searchable_fields": ["code", "name", "description", "installment_type", "frequency", "currency"],
        "filter_fields": ["is_active", "product", "plan", "installment_type", "frequency", "currency", "effective_from", "effective_to"],
        "default_ordering": ["product", "plan", "frequency", "age_from", "term_from", "code"],
    },
    {
        "slug": "grace-periods",
        "label": "Grace Periods",
        "description": "Premium grace, warning, pre-lapse, and lapse timing by optional product and plan scope.",
        "model_label": "ol_parameters.OLGracePeriod",
        "visible_columns": ["code", "name", "product", "plan", "premium_frequency", "grace_days", "warning_days", "pre_lapse_days", "lapse_days", "is_active"],
        "searchable_fields": ["code", "name", "description", "premium_frequency"],
        "filter_fields": ["is_active", "product", "plan", "premium_frequency", "effective_from", "effective_to"],
        "default_ordering": ["product", "plan", "premium_frequency", "-effective_from", "code"],
    },
    {
        "slug": "policy-statuses",
        "label": "Policy Statuses",
        "description": "Configurable policy lifecycle status catalog with terminal flags and allowed transitions.",
        "model_label": "ol_parameters.OLPolicyStatus",
        "visible_columns": ["display_order", "code", "name", "badge_type", "is_terminal", "allowed_transitions", "is_active"],
        "searchable_fields": ["code", "name", "description", "badge_type"],
        "filter_fields": ["is_active", "is_terminal", "badge_type", "display_order"],
        "default_ordering": ["display_order", "name", "code"],
    },
    {
        "slug": "policy-renewal-statuses",
        "label": "Policy Renewal Statuses",
        "description": "Renewal status catalog and operational renewal action codes.",
        "model_label": "ol_parameters.OLPolicyRenewalStatus",
        "visible_columns": ["display_order", "code", "name", "renewal_action", "is_active"],
        "searchable_fields": ["code", "name", "description", "renewal_action"],
        "filter_fields": ["is_active", "renewal_action", "display_order"],
        "default_ordering": ["display_order", "name", "code"],
    },
    {
        "slug": "beneficial-types",
        "label": "Beneficial Types",
        "description": "Beneficiary, benefit, and coverage type catalog used by policy and claims configuration.",
        "model_label": "ol_parameters.OLBeneficialType",
        "visible_columns": ["category", "code", "name", "calculation_basis", "default_ratio", "allows_multiple", "is_active"],
        "searchable_fields": ["code", "name", "description", "category", "calculation_basis"],
        "filter_fields": ["is_active", "category", "calculation_basis", "allows_multiple"],
        "default_ordering": ["category", "name", "code"],
    },
    {
        "slug": "member-cover-configurations",
        "label": "Member Cover Configurations",
        "description": "Effective-dated member or dependent eligibility and cover limits by optional product and plan scope.",
        "model_label": "ol_parameters.OLMemberCoverConfiguration",
        "visible_columns": ["code", "name", "product", "plan", "cover_type", "member_relation", "min_age", "max_age", "waiting_period_days", "is_active"],
        "searchable_fields": ["code", "name", "description", "cover_type", "member_relation", "premium_basis", "coverage_basis"],
        "filter_fields": ["is_active", "product", "plan", "cover_type", "member_relation", "effective_from", "effective_to"],
        "default_ordering": ["product", "plan", "cover_type", "member_relation", "min_age", "code"],
    },
]

PART2_COMMITMENT_STATUS_SEEDS = [
    ("PENDING", "Pending", "COMMITMENT", False),
    ("ACTIVE", "Active", "COMMITMENT", False),
    ("COMPLETED", "Completed", "COMMITMENT", True),
    ("CANCELLED", "Cancelled", "COMMITMENT", True),
]

PART2_REGISTRY_SEEDS = [
    {
        "slug": "surrender-setups",
        "label": "Surrender Setups",
        "description": "Effective-dated surrender eligibility, charges, approval, and payout timing.",
        "model_label": "ol_parameters.OLSurrenderSetup",
        "visible_columns": ["code", "name", "product", "plan", "minimum_premiums_paid", "surrender_charge_type", "partial_surrender_allowed", "is_active"],
        "searchable_fields": ["code", "name", "description", "surrender_charge_type"],
        "filter_fields": ["is_active", "product", "plan", "surrender_charge_type", "partial_surrender_allowed", "effective_from", "effective_to"],
        "default_ordering": ["product", "plan", "-effective_from", "code"],
    },
    {
        "slug": "paid-up-setups",
        "label": "Paid-Up Setups",
        "description": "Effective-dated paid-up eligibility, conversion basis, and effective timing.",
        "model_label": "ol_parameters.OLPaidUpSetup",
        "visible_columns": ["code", "name", "product", "plan", "minimum_premiums_paid", "minimum_policy_months", "paidup_conversion_basis", "allow_paidup", "is_active"],
        "searchable_fields": ["code", "name", "description", "paidup_conversion_basis", "paidup_effective_rule"],
        "filter_fields": ["is_active", "product", "plan", "paidup_conversion_basis", "allow_paidup", "effective_from", "effective_to"],
        "default_ordering": ["product", "plan", "-effective_from", "code"],
    },
    {
        "slug": "surrender-value-rates",
        "label": "Surrender Value Rates",
        "description": "Versioned surrender-value factors by product, plan, demographic, age, term, and policy year.",
        "model_label": "ol_parameters.OLSurrenderValueRate",
        "visible_columns": ["code", "table_code", "rate_table_version", "product", "plan", "age_from", "age_to", "policy_year_from", "policy_year_to", "rate_factor", "is_active"],
        "searchable_fields": ["code", "name", "description", "table_code", "rate_table_version", "gender", "smoker_status"],
        "filter_fields": ["is_active", "product", "plan", "table_code", "rate_table_version", "gender", "smoker_status", "effective_from", "effective_to"],
        "default_ordering": ["table_code", "rate_table_version", "product", "plan", "row_order", "code"],
    },
    {
        "slug": "paid-up-rates",
        "label": "Paid-Up Rates",
        "description": "Versioned paid-up factors by product, plan, demographic, age, term, and policy year.",
        "model_label": "ol_parameters.OLPaidUpRate",
        "visible_columns": ["code", "table_code", "rate_table_version", "product", "plan", "age_from", "age_to", "policy_year_from", "policy_year_to", "rate_factor", "is_active"],
        "searchable_fields": ["code", "name", "description", "table_code", "rate_table_version", "gender", "smoker_status"],
        "filter_fields": ["is_active", "product", "plan", "table_code", "rate_table_version", "gender", "smoker_status", "effective_from", "effective_to"],
        "default_ordering": ["table_code", "rate_table_version", "product", "plan", "row_order", "code"],
    },
    {
        "slug": "commitment-statuses",
        "label": "Commitment Statuses",
        "description": "Commitment status catalog kept separate from policy transaction lifecycle state.",
        "model_label": "ol_parameters.OLCommitmentStatus",
        "visible_columns": ["display_order", "code", "name", "applies_to", "is_terminal", "is_active"],
        "searchable_fields": ["code", "name", "description", "applies_to"],
        "filter_fields": ["is_active", "applies_to", "is_terminal", "display_order"],
        "default_ordering": ["applies_to", "display_order", "name", "code"],
    },
]


PART3_REGISTRY_SEEDS = [
    {
        "slug": "health-questions",
        "label": "Health Questions",
        "description": "Reusable typed health-question catalog with underwriting impact and medical follow-up flags.",
        "model_label": "ol_parameters.OLHealthQuestion",
        "visible_columns": ["category", "code", "name", "question_text", "answer_type", "underwriting_impact", "requires_medical_followup", "is_active"],
        "searchable_fields": ["code", "name", "description", "question_text", "category", "answer_type", "underwriting_impact"],
        "filter_fields": ["is_active", "category", "answer_type", "underwriting_impact", "requires_medical_followup"],
        "default_ordering": ["category", "name", "code"],
    },
    {
        "slug": "health-questionnaires",
        "label": "Health Questionnaires",
        "description": "Versioned health questionnaire headers scoped globally, by product, plan, or scheme.",
        "model_label": "ol_parameters.OLHealthQuestionnaire",
        "visible_columns": ["code", "name", "version", "applies_to_scope", "product", "plan", "age_threshold", "is_active"],
        "searchable_fields": ["code", "name", "description", "scheme_code", "version", "product", "plan"],
        "filter_fields": ["is_active", "applies_to_scope", "product", "plan", "version", "effective_from", "effective_to"],
        "default_ordering": ["code", "-effective_from", "version"],
    },
    {
        "slug": "health-questionnaire-items",
        "label": "Health Questionnaire Items",
        "description": "Ordered question membership for questionnaire versions, including mandatory and medical-trigger flags.",
        "model_label": "ol_parameters.OLHealthQuestionnaireItem",
        "visible_columns": ["questionnaire", "sequence", "code", "health_question", "mandatory", "trigger_medical_requirement", "score", "is_active"],
        "searchable_fields": ["code", "name", "description", "questionnaire", "health_question"],
        "filter_fields": ["is_active", "questionnaire", "health_question", "mandatory", "trigger_medical_requirement"],
        "default_ordering": ["questionnaire", "sequence", "code"],
    },
    {
        "slug": "grace-period-notification-schedules",
        "label": "Grace Period Notification Schedules",
        "description": "Effective-dated notification events, offsets, channels, recipients, and template codes for premium/grace lifecycle events.",
        "model_label": "ol_parameters.OLGracePeriodNotificationSchedule",
        "visible_columns": ["event_type", "days_offset", "code", "notification_channel", "recipient_type", "template_code", "is_active"],
        "searchable_fields": ["code", "name", "description", "event_type", "notification_channel", "recipient_type", "template_code"],
        "filter_fields": ["is_active", "event_type", "notification_channel", "recipient_type", "effective_from", "effective_to"],
        "default_ordering": ["event_type", "days_offset", "code"],
    },
    {
        "slug": "reinstatement-windows",
        "label": "Reinstatement Windows",
        "description": "Effective-dated lapse reinstatement eligibility, financial requirements, and underwriting controls.",
        "model_label": "ol_parameters.OLReinstatementWindow",
        "visible_columns": ["code", "name", "product", "plan", "days_after_lapse", "maximum_reinstatements", "require_medical_underwriting", "interest_rate", "penalty_rate", "is_active"],
        "searchable_fields": ["code", "name", "description", "product", "plan"],
        "filter_fields": ["is_active", "product", "plan", "require_medical_underwriting", "require_outstanding_premium_payment", "effective_from", "effective_to"],
        "default_ordering": ["product", "plan", "-effective_from", "code"],
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
    help = "Seed idempotent OL Policy Setup Part 1, Part 2, and Part 3 catalogs and safe starter configuration."

    @transaction.atomic
    def handle(self, *args, **options):
        created = 0
        updated = 0
        for index, (code, name, terminal, badge_type, transitions) in enumerate(POLICY_STATUS_SEEDS):
            record, was_created = upsert(
                OLPolicyStatus,
                {"code": code},
                {
                    "name": name,
                    "description": f"Ordinary Life policy lifecycle status: {name}.",
                    "display_order": index + 1,
                    "badge_type": badge_type,
                    "is_terminal": terminal,
                    "allowed_transitions": [],
                    "effective_from": EFFECTIVE_FROM,
                    "is_active": True,
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1

        for index, (code, name, action) in enumerate(RENEWAL_STATUS_SEEDS):
            _, was_created = upsert(
                OLPolicyRenewalStatus,
                {"code": code},
                {
                    "name": name,
                    "description": f"Ordinary Life renewal status: {name}.",
                    "display_order": index + 1,
                    "renewal_action": action,
                    "effective_from": EFFECTIVE_FROM,
                    "is_active": True,
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1

        status_by_code = {record.code: record for record in OLPolicyStatus.objects.filter(code__in=[seed[0] for seed in POLICY_STATUS_SEEDS])}
        for code, _, _, _, transitions in POLICY_STATUS_SEEDS:
            record = status_by_code[code]
            record.allowed_transitions = transitions
            record.full_clean()
            record.save(update_fields=["allowed_transitions", "updated_at"])

        for code, name, category, basis, ratio, allows_multiple in BENEFICIAL_TYPE_SEEDS:
            _, was_created = upsert(
                OLBeneficialType,
                {"code": code},
                {
                    "name": name,
                    "description": f"Ordinary Life {name.lower()} beneficial type.",
                    "category": category,
                    "calculation_basis": basis,
                    "default_ratio": ratio,
                    "allows_multiple": allows_multiple,
                    "effective_from": EFFECTIVE_FROM,
                    "is_active": True,
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1

        _, was_created = upsert(
            OLGracePeriod,
            {"code": "STANDARD_30_DAYS"},
            {
                "name": "Standard 30-Day Grace Period",
                "description": "Standard Ordinary Life premium grace period.",
                "effective_from": EFFECTIVE_FROM,
                "premium_frequency": "",
                "grace_days": 30,
                "warning_days": 15,
                "pre_lapse_days": 7,
                "lapse_days": 30,
                "minimum_due_amount": Decimal("0.00"),
                "is_active": True,
            },
        )
        if was_created:
            created += 1
        else:
            updated += 1

        _, was_created = upsert(
            OLMemberCoverConfiguration,
            {"code": "INDIVIDUAL"},
            {
                "name": "Individual Member Cover",
                "description": "Standard individual member cover configuration.",
                "effective_from": EFFECTIVE_FROM,
                "cover_type": "INDIVIDUAL",
                "member_relation": "MEMBER",
                "min_age": 18,
                "max_age": 65,
                "waiting_period_days": 0,
                "benefit_limit": None,
                "premium_basis": "MEMBER_PREMIUM",
                "coverage_basis": "SUM_ASSURED",
                "is_active": True,
            },
        )
        if was_created:
            created += 1
        else:
            updated += 1

        for index, (code, name, applies_to, terminal) in enumerate(PART2_COMMITMENT_STATUS_SEEDS):
            _, was_created = upsert(
                OLCommitmentStatus,
                {"code": code},
                {
                    "name": name,
                    "description": f"Ordinary Life commitment status: {name}.",
                    "display_order": index + 1,
                    "applies_to": applies_to,
                    "is_terminal": terminal,
                    "effective_from": EFFECTIVE_FROM,
                    "is_active": True,
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1

        _, was_created = upsert(
            OLSurrenderSetup,
            {"code": "STANDARD_SURRENDER"},
            {
                "name": "Standard Surrender Setup",
                "description": "Global starter surrender eligibility and payout configuration.",
                "effective_from": EFFECTIVE_FROM,
                "minimum_premiums_paid": 24,
                "minimum_policy_months": 24,
                "minimum_premium_paid_ratio": Decimal("100.0000"),
                "surrender_charge_type": "PERCENTAGE",
                "surrender_charge_value": Decimal("5.00000000"),
                "partial_surrender_allowed": False,
                "surrender_payout_days": 30,
                "require_approval": True,
                "is_active": True,
            },
        )
        if was_created:
            created += 1
        else:
            updated += 1

        _, was_created = upsert(
            OLPaidUpSetup,
            {"code": "STANDARD_PAID_UP"},
            {
                "name": "Standard Paid-Up Setup",
                "description": "Global starter paid-up conversion configuration.",
                "effective_from": EFFECTIVE_FROM,
                "minimum_premiums_paid": 12,
                "minimum_policy_months": 12,
                "paidup_conversion_basis": "PROPORTIONAL",
                "allow_paidup": True,
                "paidup_effective_rule": "NEXT_ANNIVERSARY",
                "is_active": True,
            },
        )
        if was_created:
            created += 1
        else:
            updated += 1

        _, was_created = upsert(
            OLHealthQuestion,
            {"code": "SMOKING_HISTORY"},
            {
                "name": "Smoking History",
                "description": "Starter health question for tobacco or nicotine use history.",
                "question_text": "Have you used tobacco or nicotine products within the last five years?",
                "category": "LIFESTYLE",
                "answer_type": "BOOLEAN",
                "underwriting_impact": "MEDIUM",
                "requires_medical_followup": False,
                "effective_from": EFFECTIVE_FROM,
                "is_active": True,
            },
        )
        if was_created:
            created += 1
        else:
            updated += 1

        questionnaire, was_created = upsert(
            OLHealthQuestionnaire,
            {"code": "STANDARD_UW_QUESTIONNAIRE", "version": "1.0"},
            {
                "name": "Standard Underwriting Questionnaire",
                "description": "Starter global underwriting questionnaire; extend through the configuration tables.",
                "applies_to_scope": "GLOBAL",
                "product": None,
                "plan": None,
                "scheme_code": "",
                "sum_assured_threshold": None,
                "age_threshold": 18,
                "version": "1.0",
                "effective_from": EFFECTIVE_FROM,
                "is_active": True,
            },
        )
        if was_created:
            created += 1
        else:
            updated += 1

        health_question = OLHealthQuestion.objects.get(code="SMOKING_HISTORY")
        _, was_created = upsert(
            OLHealthQuestionnaireItem,
            {"code": "STANDARD_UW_SMOKING"},
            {
                "name": "Smoking History Item",
                "description": "Starter mandatory smoking-history question.",
                "questionnaire": questionnaire,
                "health_question": health_question,
                "sequence": 1,
                "mandatory": True,
                "trigger_medical_requirement": False,
                "score": None,
                "is_active": True,
            },
        )
        if was_created:
            created += 1
        else:
            updated += 1

        for code, name, event_type, days_offset, channel, recipient, template in (
            ("PREMIUM_DUE_EMAIL", "Premium Due Email", "PREMIUM_DUE", -5, "EMAIL", "POLICYHOLDER", "OL_PREMIUM_DUE"),
            ("GRACE_WARNING_SMS", "Grace Warning SMS", "GRACE_WARNING", 7, "SMS", "POLICYHOLDER", "OL_GRACE_WARNING"),
            ("PRE_LAPSE_AGENT_EMAIL", "Pre-Lapse Agent Email", "PRE_LAPSE", -3, "EMAIL", "AGENT", "OL_PRE_LAPSE"),
        ):
            _, was_created = upsert(
                OLGracePeriodNotificationSchedule,
                {"code": code},
                {
                    "name": name,
                    "description": f"Starter Ordinary Life notification schedule: {name}.",
                    "event_type": event_type,
                    "days_offset": days_offset,
                    "notification_channel": channel,
                    "recipient_type": recipient,
                    "template_code": template,
                    "effective_from": EFFECTIVE_FROM,
                    "is_active": True,
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1

        _, was_created = upsert(
            OLReinstatementWindow,
            {"code": "STANDARD_REINSTATEMENT"},
            {
                "name": "Standard Reinstatement Window",
                "description": "Starter global reinstatement eligibility after policy lapse.",
                "product": None,
                "plan": None,
                "days_after_lapse": 730,
                "maximum_reinstatements": 2,
                "require_medical_underwriting": False,
                "require_outstanding_premium_payment": True,
                "interest_rate": Decimal("8.0000"),
                "penalty_rate": Decimal("5.0000"),
                "effective_from": EFFECTIVE_FROM,
                "is_active": True,
            },
        )
        if was_created:
            created += 1
        else:
            updated += 1

        for registry_seed in REGISTRY_SEEDS + PART2_REGISTRY_SEEDS + PART3_REGISTRY_SEEDS:
            defaults = {
                **registry_seed,
                "parameter_group": "Policy Setup",
                "allowed_actions": ["list", "retrieve", "create", "update", "deactivate", "export"],
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
            _, was_created = upsert(OLParameterTableRegistry, {"slug": registry_seed["slug"]}, defaults)
            if was_created:
                created += 1
            else:
                updated += 1

        product = OLProduct.objects.filter(is_active=True).order_by("code").first()
        if product:
            plan = OLPlan.objects.filter(product_version__product=product, is_active=True).order_by("code").first()
            _, was_created = upsert(
                OLAnticipatedEndowmentInstallmentRate,
                {"code": "BASE_ANTICIPATED_ENDOWMENT"},
                {
                    "name": "Base Anticipated Endowment Rate",
                    "description": "Starter rate factor; replace with approved actuarial rate-table data before production use.",
                    "effective_from": EFFECTIVE_FROM,
                    "product": product,
                    "plan": plan,
                    "installment_type": "ANTICIPATED_ENDOWMENT",
                    "frequency": "ANNUAL",
                    "rate_factor": Decimal("1.00000000"),
                    "currency": "",
                    "is_active": True,
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1
            for model, code, name, description, factor in (
                (
                    OLSurrenderValueRate,
                    "BASE_SURRENDER_VALUE_RATE",
                    "Base Surrender Value Rate",
                    "Starter surrender-value rate factor; replace with approved actuarial data before production use.",
                    Decimal("0.50000000"),
                ),
                (
                    OLPaidUpRate,
                    "BASE_PAID_UP_RATE",
                    "Base Paid-Up Rate",
                    "Starter paid-up rate factor; replace with approved actuarial data before production use.",
                    Decimal("0.75000000"),
                ),
            ):
                _, was_created = upsert(
                    model,
                    {"code": code},
                    {
                        "name": name,
                        "description": description,
                        "effective_from": EFFECTIVE_FROM,
                        "table_code": "STANDARD",
                        "rate_table_version": "V1",
                        "product": product,
                        "plan": plan,
                        "gender": "",
                        "smoker_status": "",
                        "policy_year_from": 1,
                        "policy_year_to": 100,
                        "rate_factor": factor,
                        "row_order": 1,
                        "is_active": True,
                    },
                )
                if was_created:
                    created += 1
                else:
                    updated += 1
            rate_message = "one product-scoped starter anticipated-endowment, surrender-value, and paid-up rate per table"
        else:
            rate_message = "no anticipated-endowment rate (active product configuration is required)"

        self.stdout.write(
            self.style.SUCCESS(
                f"OL Policy Setup seeded: {created} created, {updated} updated; {rate_message}."
            )
        )
