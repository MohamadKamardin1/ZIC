"""Reporting module seam: register the Front Office Receipts report category + dataset.

The reporting module discovers allowed report visibility through
``users.ReportCategory`` and consumes the table contract from
``ol_parameters.OLParameterTableRegistry`` (parameter_group ``REPORT``). This
module registers both idempotently so the reports UI can render the "Front
Office Receipts" dataset (receipt number, date, branch, payer, payment mode,
currency, amount, allocated/unallocated split, status, cashier, source module)
immediately.
"""

from apps.ol_parameters.models import OLParameterTableRegistry
from apps.users.models import ReportCategory

CATEGORY_CODE = "FRONT_OFFICE_RECEIPTS"
CATEGORY_NAME = "Front Office Receipts"
BUSINESS_AREA = "FRONT_OFFICE"
REGISTRY_SLUG = "front-office-receipts-report"

# field, label, json_type, filterable, sortable
DATASET_FIELDS = (
    ("receipt_number", "Receipt Number", "string", True, True),
    ("date", "Receipt Date", "date", True, True),
    ("branch", "Branch", "string", True, True),
    ("payer", "Payer", "string", True, True),
    ("payment_mode", "Payment Mode", "string", True, True),
    ("currency", "Currency", "string", True, True),
    ("amount", "Amount", "number", True, True),
    ("allocated", "Allocated", "number", True, True),
    ("unallocated", "Unallocated", "number", True, True),
    ("status", "Status", "string", True, True),
    ("cashier", "Cashier", "string", True, True),
    ("source_module", "Source Module", "string", True, True),
)

_SEARCHABLE = ("receipt_number", "payer", "branch", "source_module", "status")
_FILTERABLE = [field for field, _, _, filterable, _ in DATASET_FIELDS if filterable]


def dataset_contract():
    """Dataset field contract exposed to the reporting module."""
    return {
        "category": {"code": CATEGORY_CODE, "name": CATEGORY_NAME, "business_area": BUSINESS_AREA},
        "resource": "front_office.Receipt",
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
        "filters": _FILTERABLE,
        "default_ordering": ["-date"],
    }


def register_report_category():
    category, _ = ReportCategory.objects.update_or_create(
        code=CATEGORY_CODE,
        defaults={
            "name": CATEGORY_NAME,
            "description": "Front Office receipts register for the reporting module.",
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
            "description": "Front Office receipts dataset for the reporting module.",
            "parameter_group": "REPORT",
            "model_label": "front_office.Receipt",
            "visible_columns": fields,
            "searchable_fields": list(_SEARCHABLE),
            "filter_fields": _FILTERABLE,
            "default_ordering": ["-date"],
            "allowed_actions": ["view", "export"],
            "export_support": True,
            "permission_code": "front_office.receipts.view",
            "permission_requirements": {"view": "front_office.receipts.view", "export": "front_office.receipts.view"},
            "is_active": True,
        },
    )
    return registry


def register():
    """Idempotently register the report category and dataset registry."""
    register_report_category()
    register_dataset_registry()
    return dataset_contract()
