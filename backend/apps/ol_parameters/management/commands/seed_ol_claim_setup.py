from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.ol_parameters.models import (
    OLClaimReason,
    OLClaimStatus,
    OLClaimType,
    OLCorrespondentType,
    OLDischargeType,
    OLParameterTableRegistry,
)

EFFECTIVE_FROM = date(2026, 1, 1)

REGISTRY_SEEDS = [
    {
        "slug": "claim-types",
        "label": "OL Claim Types",
        "description": "Effective-dated claim type configuration and payment/document rules.",
        "model_label": "ol_parameters.OLClaimType",
        "visible_columns": [
            "code", "name", "claim_category", "calculation_basis", "duplicate_check_rule",
            "waiting_period_days", "require_approval", "effective_from", "effective_to", "is_active",
        ],
        "searchable_fields": ["code", "name", "description", "claim_category", "calculation_basis", "duplicate_check_rule"],
        "filter_fields": [
            "is_active", "claim_category", "calculation_basis", "duplicate_check_rule",
            "allow_waiver_of_premium", "require_approval", "effective_from", "effective_to",
        ],
        "default_ordering": ["claim_category", "name", "code"],
    },
    {
        "slug": "claim-reasons",
        "label": "OL Claim Reasons",
        "description": "Claim reason catalog optionally scoped to a claim type.",
        "model_label": "ol_parameters.OLClaimReason",
        "visible_columns": ["code", "name", "claim_type", "reason_category", "effective_from", "effective_to", "is_active"],
        "searchable_fields": ["code", "name", "description", "reason_category", "claim_type__code", "claim_type__name"],
        "filter_fields": ["is_active", "claim_type", "reason_category", "effective_from", "effective_to"],
        "default_ordering": ["reason_category", "claim_type", "name", "code"],
    },
    {
        "slug": "claim-statuses",
        "label": "OL Claim Statuses",
        "description": "Claim workflow statuses and allowed outgoing transitions.",
        "model_label": "ol_parameters.OLClaimStatus",
        "visible_columns": ["display_order", "code", "name", "badge_type", "is_payable", "is_terminal", "effective_from", "effective_to", "is_active"],
        "searchable_fields": ["code", "name", "description", "badge_type"],
        "filter_fields": ["is_active", "badge_type", "is_terminal", "is_payable", "effective_from", "effective_to"],
        "default_ordering": ["display_order", "name", "code"],
    },
    {
        "slug": "discharge-types",
        "label": "OL Discharge Types",
        "description": "Claim discharge/release document types and template variables.",
        "model_label": "ol_parameters.OLDischargeType",
        "visible_columns": ["code", "name", "discharge_category", "template_code", "effective_from", "effective_to", "is_active"],
        "searchable_fields": ["code", "name", "description", "discharge_category", "template_code"],
        "filter_fields": ["is_active", "discharge_category", "template_code", "effective_from", "effective_to"],
        "default_ordering": ["discharge_category", "name", "code"],
    },
    {
        "slug": "correspondent-types",
        "label": "OL Correspondent Types",
        "description": "Claim correspondence purpose and communication-channel catalog.",
        "model_label": "ol_parameters.OLCorrespondentType",
        "visible_columns": ["code", "name", "correspondence_category", "communication_channel", "purpose", "effective_from", "effective_to", "is_active"],
        "searchable_fields": ["code", "name", "description", "correspondence_category", "communication_channel", "purpose"],
        "filter_fields": ["is_active", "correspondence_category", "communication_channel", "effective_from", "effective_to"],
        "default_ordering": ["correspondence_category", "name", "code"],
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
    help = "Seed idempotent OL Claim Setup parameters."

    @transaction.atomic
    def handle(self, *args, **options):
        claim_type_specs = [
            {
                "code": "DEATH_CLAIM",
                "name": "Death Claim",
                "claim_category": "DEATH",
                "calculation_basis": "SUM_ASSURED",
                "duplicate_check_rule": "POLICY_AND_TYPE",
                "waiting_period_days": 0,
                "payable_to_rules": {"default": "beneficiary", "requires_verified_beneficiary": True},
                "allow_waiver_of_premium": False,
                "require_documents": ["DEATH_CERTIFICATE", "IDENTITY_DOCUMENT", "POLICY_DOCUMENT"],
                "require_approval": True,
            },
            {
                "code": "CRITICAL_ILLNESS_CLAIM",
                "name": "Critical Illness Claim",
                "claim_category": "CRITICAL_ILLNESS",
                "calculation_basis": "SUM_ASSURED",
                "duplicate_check_rule": "POLICY_AND_REASON",
                "waiting_period_days": 90,
                "payable_to_rules": {"default": "policyholder"},
                "allow_waiver_of_premium": True,
                "require_documents": ["MEDICAL_REPORT", "IDENTITY_DOCUMENT", "POLICY_DOCUMENT"],
                "require_approval": True,
            },
            {
                "code": "DISABILITY_CLAIM",
                "name": "Disability Claim",
                "claim_category": "DISABILITY",
                "calculation_basis": "BENEFIT_AMOUNT",
                "duplicate_check_rule": "POLICY_AND_EVENT_DATE",
                "waiting_period_days": 30,
                "payable_to_rules": {"default": "policyholder"},
                "allow_waiver_of_premium": True,
                "require_documents": ["DISABILITY_ASSESSMENT", "MEDICAL_REPORT", "IDENTITY_DOCUMENT"],
                "require_approval": True,
            },
            {
                "code": "SURRENDER_CLAIM",
                "name": "Surrender Claim",
                "claim_category": "SURRENDER",
                "calculation_basis": "CASH_VALUE",
                "duplicate_check_rule": "POLICY_AND_TYPE",
                "waiting_period_days": 0,
                "payable_to_rules": {"default": "policyholder", "requires_identity_match": True},
                "allow_waiver_of_premium": False,
                "require_documents": ["SURRENDER_REQUEST", "IDENTITY_DOCUMENT"],
                "require_approval": True,
            },
            {
                "code": "MATURITY_CLAIM",
                "name": "Maturity Claim",
                "claim_category": "MATURITY",
                "calculation_basis": "BENEFIT_AMOUNT",
                "duplicate_check_rule": "POLICY_AND_TYPE",
                "waiting_period_days": 0,
                "payable_to_rules": {"default": "policyholder"},
                "allow_waiver_of_premium": False,
                "require_documents": ["IDENTITY_DOCUMENT", "BANK_DETAILS"],
                "require_approval": True,
            },
            {
                "code": "MEDICAL_CLAIM",
                "name": "Medical Claim",
                "claim_category": "MEDICAL",
                "calculation_basis": "FIXED_AMOUNT",
                "duplicate_check_rule": "POLICY_AND_REASON",
                "waiting_period_days": 30,
                "payable_to_rules": {"default": "provider_or_policyholder"},
                "allow_waiver_of_premium": False,
                "require_documents": ["MEDICAL_REPORT", "INVOICE", "IDENTITY_DOCUMENT"],
                "require_approval": True,
            },
        ]
        claim_types = {}
        created_counts = {"claim_types": 0, "claim_reasons": 0, "statuses": 0, "discharges": 0, "correspondents": 0}
        for spec in claim_type_specs:
            claim_type, created = upsert(
                OLClaimType,
                {"code": spec["code"]},
                {**spec, "description": f"Starter {spec['name']} configuration pending claims governance approval.", "effective_from": EFFECTIVE_FROM, "effective_to": None, "is_active": True},
            )
            claim_types[claim_type.code] = claim_type
            created_counts["claim_types"] += int(created)

        reason_specs = [
            ("NATURAL_DEATH", "Natural death", "DEATH_CLAIM", "EVENT"),
            ("ACCIDENTAL_DEATH", "Accidental death", "DEATH_CLAIM", "EVENT"),
            ("DIAGNOSED_CRITICAL_ILLNESS", "Diagnosed critical illness", "CRITICAL_ILLNESS_CLAIM", "MEDICAL"),
            ("TOTAL_PERMANENT_DISABILITY", "Total permanent disability", "DISABILITY_CLAIM", "MEDICAL"),
            ("VOLUNTARY_SURRENDER", "Voluntary surrender", "SURRENDER_CLAIM", "ADMINISTRATIVE"),
            ("POLICY_MATURITY", "Policy maturity", "MATURITY_CLAIM", "EVENT"),
        ]
        for code, name, claim_code, category in reason_specs:
            _, created = upsert(
                OLClaimReason,
                {"code": code},
                {
                    "name": name,
                    "description": f"Starter claim reason for {claim_code.lower()}.",
                    "claim_type": claim_types[claim_code],
                    "reason_category": category,
                    "effective_from": EFFECTIVE_FROM,
                    "effective_to": None,
                    "is_active": True,
                },
            )
            created_counts["claim_reasons"] += int(created)

        status_specs = [
            ("REGISTERED", "Registered", 10, "NEUTRAL", False, False),
            ("DOCUMENTS_PENDING", "Documents Pending", 20, "WARNING", False, False),
            ("UNDER_ASSESSMENT", "Under Assessment", 30, "INFO", False, False),
            ("PENDING_APPROVAL", "Pending Approval", 40, "WARNING", False, False),
            ("APPROVED", "Approved", 50, "SUCCESS", False, True),
            ("REJECTED", "Rejected", 60, "DANGER", False, False),
            ("PAYMENT_PENDING", "Payment Pending", 70, "INFO", False, True),
            ("SETTLED", "Settled", 80, "SUCCESS", False, True),
            ("CLOSED", "Closed", 90, "NEUTRAL", True, False),
        ]
        for code, name, display_order, badge_type, is_terminal, is_payable in status_specs:
            _, created = upsert(
                OLClaimStatus,
                {"code": code},
                {
                    "name": name,
                    "description": f"Starter OL claim workflow status: {name}.",
                    "display_order": display_order,
                    "badge_type": badge_type,
                    "is_terminal": is_terminal,
                    "is_payable": is_payable,
                    "allowed_transitions": [],
                    "effective_from": EFFECTIVE_FROM,
                    "effective_to": None,
                    "is_active": True,
                },
            )
            created_counts["statuses"] += int(created)

        transitions = {
            "REGISTERED": ["DOCUMENTS_PENDING", "UNDER_ASSESSMENT"],
            "DOCUMENTS_PENDING": ["UNDER_ASSESSMENT"],
            "UNDER_ASSESSMENT": ["PENDING_APPROVAL", "REJECTED"],
            "PENDING_APPROVAL": ["APPROVED", "REJECTED"],
            "APPROVED": ["PAYMENT_PENDING"],
            "REJECTED": ["CLOSED"],
            "PAYMENT_PENDING": ["SETTLED"],
            "SETTLED": ["CLOSED"],
            "CLOSED": [],
        }
        for code, allowed_transitions in transitions.items():
            OLClaimStatus.objects.get(code=code)
            upsert(OLClaimStatus, {"code": code}, {"allowed_transitions": allowed_transitions})

        discharge_specs = [
            ("FULL_FINAL_DISCHARGE", "Full and Final Discharge", "FULL_AND_FINAL", "OL_CLAIM_FULL_FINAL"),
            ("PARTIAL_DISCHARGE", "Partial Discharge", "PARTIAL", "OL_CLAIM_PARTIAL"),
            ("BENEFICIARY_RELEASE", "Beneficiary Release", "RELEASE", "OL_CLAIM_BENEFICIARY_RELEASE"),
        ]
        for code, name, category, template_code in discharge_specs:
            _, created = upsert(
                OLDischargeType,
                {"code": code},
                {
                    "name": name,
                    "description": f"Starter discharge document type: {name}.",
                    "discharge_category": category,
                    "template_code": template_code,
                    "variables": {"claim_number": "string", "policy_number": "string", "payee_name": "string"},
                    "effective_from": EFFECTIVE_FROM,
                    "effective_to": None,
                    "is_active": True,
                },
            )
            created_counts["discharges"] += int(created)

        correspondent_specs = [
            ("CLAIM_ACKNOWLEDGEMENT_EMAIL", "Claim Acknowledgement Email", "CLAIM_ACKNOWLEDGEMENT", "EMAIL", "Acknowledge claim registration"),
            ("DOCUMENT_REQUEST_LETTER", "Document Request Letter", "DOCUMENT_REQUEST", "LETTER", "Request outstanding claim documents"),
            ("CLAIM_DECISION_EMAIL", "Claim Decision Email", "DECISION", "EMAIL", "Communicate claim decision"),
            ("PAYMENT_NOTIFICATION_SMS", "Payment Notification SMS", "PAYMENT", "SMS", "Notify payee of payment processing"),
        ]
        for code, name, category, channel, purpose in correspondent_specs:
            _, created = upsert(
                OLCorrespondentType,
                {"code": code},
                {
                    "name": name,
                    "description": f"Starter correspondence type: {name}.",
                    "correspondence_category": category,
                    "communication_channel": channel,
                    "purpose": purpose,
                    "effective_from": EFFECTIVE_FROM,
                    "effective_to": None,
                    "is_active": True,
                },
            )
            created_counts["correspondents"] += int(created)

        registry_defaults = {
            "parameter_group": "CLAIM_SETUP",
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
                "Seeded OL Claim Setup: "
                + ", ".join(f"{key}_created={value}" for key, value in created_counts.items())
                + f", registry_contracts={len(REGISTRY_SEEDS)}."
            )
        )
