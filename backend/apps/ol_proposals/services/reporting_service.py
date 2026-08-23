"""Reporting module seam: register the proposals report category + dataset.

The reporting module discovers allowed report visibility through
``users.ReportCategory`` and consumes the table contract from
``ol_parameters.OLParameterTableRegistry`` (parameter_group ``REPORT``). This
module registers both idempotently so the reports UI can render the "Ordinary
Life Proposals" dataset (status, product, agent, premium, dates) immediately.
"""

from apps.ol_parameters.models import OLParameterTableRegistry
from apps.users.models import ReportCategory

CATEGORY_CODE = "OL_PROPOSALS"
CATEGORY_NAME = "Ordinary Life Proposals"
BUSINESS_AREA = "ORDINARY_LIFE"
REGISTRY_SLUG = "ol-proposals-report"

# field, label, json_type, filterable, sortable
DATASET_FIELDS = (
    ("proposal_number", "Proposal Number", "string", True, True),
    ("status", "Status", "string", True, True),
    ("product", "Product", "string", True, True),
    ("plan", "Plan", "string", True, True),
    ("agent", "Agent", "string", True, True),
    ("policyholder", "Policyholder", "string", True, True),
    ("total_premium", "Total Premium", "number", True, True),
    ("currency", "Currency", "string", True, True),
    ("expiry_date", "Expiry Date", "date", True, True),
    ("created_at", "Created At", "date", True, True),
    ("updated_at", "Updated At", "date", True, True),
)


def dataset_contract():
    """Dataset field contract exposed to the reporting module."""
    return {
        "category": {"code": CATEGORY_CODE, "name": CATEGORY_NAME, "business_area": BUSINESS_AREA},
        "resource": "ol_proposals.OLProposal",
        "fields": [
            {
                "field": field,
                "label": label,
                "type": json_type,
                "filterable": filterable,
                "sortable": sortable,
            }
            for field, label, json_type, filterable, sortable in DATASET_FIELDS
        ],
        "filters": ["status", "product", "agent", "premium"],
        "default_ordering": ["-created_at"],
    }


def register_report_category():
    category, _ = ReportCategory.objects.update_or_create(
        code=CATEGORY_CODE,
        defaults={
            "name": CATEGORY_NAME,
            "description": "Ordinary Life proposal register for the reporting module.",
            "business_area": BUSINESS_AREA,
            "is_active": True,
            "is_system": True,
        },
    )
    return category


def register_dataset_registry():
    fields = [entry[0] for entry in DATASET_FIELDS]
    registry, _ = OLParameterTableRegistry.objects.update_or_create(
        slug=REGISTRY_SLUG,
        defaults={
            "label": CATEGORY_NAME,
            "description": "OL proposal register dataset for the reporting module.",
            "parameter_group": "REPORT",
            "model_label": "ol_proposals.OLProposal",
            "visible_columns": fields,
            "searchable_fields": ["proposal_number", "policyholder", "agent"],
            "filter_fields": ["status", "product", "plan", "agent", "currency", "expiry_date", "created_at"],
            "default_ordering": ["-created_at"],
            "allowed_actions": ["view", "export"],
            "export_support": True,
            "permission_code": "ol_proposals.view",
            "permission_requirements": {"view": "ol_proposals.view", "export": "ol_proposals.view"},
            "is_active": True,
        },
    )
    return registry


def register():
    """Idempotently register the report category and dataset registry."""
    register_report_category()
    register_dataset_registry()
    return dataset_contract()