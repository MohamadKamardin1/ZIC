from django.db import migrations


READY_TEMPLATES = [
    {
        "code": "PROPOSAL_SUMMARY_UNIFIED",
        "name": "Proposal Summary",
        "document_type": "PROPOSAL_SUMMARY",
        "layout_template_path": "documents/proposal_summary.html",
        "variables_schema": {
            "proposal": "object",
            "quote": "object",
            "prospect": "object",
            "plans": "array",
            "financial": "object",
            "branding": "object",
        },
    },
    {
        "code": "COMMITMENT_STATEMENT_UNIFIED",
        "name": "Commitment Statement",
        "document_type": "COMMITMENT_STATEMENT",
        "layout_template_path": "documents/commitment_statement.html",
        "variables_schema": {
            "commitment": "object",
            "meta": "object",
            "financial": "object",
            "allocations": "array",
            "branding": "object",
        },
    },
]

PENDING_TEMPLATES = [
    ("RECEIPT", "Receipt"),
    ("POLICY_CONTRACT", "Policy Contract"),
    ("DISCHARGE_VOUCHER", "Discharge Voucher"),
    ("COMMISSION_STATEMENT", "Commission Statement"),
    ("DEBIT_NOTE", "Debit Note"),
    ("PREMIUM_STATEMENT", "Premium Statement"),
]


def seed_templates(apps, schema_editor):
    DocumentTemplate = apps.get_model("documents", "DocumentTemplate")
    for definition in READY_TEMPLATES:
        DocumentTemplate.objects.get_or_create(
            code=definition["code"],
            version=1,
            defaults={
                **definition,
                "branding_config_reference": "COMPANY_BRANDING",
                "is_active": True,
            },
        )
    for document_type, name in PENDING_TEMPLATES:
        DocumentTemplate.objects.get_or_create(
            code=f"{document_type}_PENDING",
            version=1,
            defaults={
                "name": f"{name} template pending",
                "document_type": document_type,
                "layout_template_path": "documents/pending.html",
                "variables_schema": {},
                "branding_config_reference": "COMPANY_BRANDING",
                "is_active": False,
            },
        )


def unseed_templates(apps, schema_editor):
    DocumentTemplate = apps.get_model("documents", "DocumentTemplate")
    codes = [definition["code"] for definition in READY_TEMPLATES]
    codes.extend(f"{document_type}_PENDING" for document_type, _name in PENDING_TEMPLATES)
    DocumentTemplate.objects.filter(code__in=codes, version=1).delete()


class Migration(migrations.Migration):
    dependencies = [("documents", "0002_seed_document_templates")]

    operations = [migrations.RunPython(seed_templates, unseed_templates)]
