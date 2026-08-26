from django.db import migrations


READY_TEMPLATES = [
    {
        "code": "POLICY_CONTRACT_UNIFIED",
        "name": "Policy Contract",
        "document_type": "POLICY_CONTRACT",
        "layout_template_path": "documents/policy_contract.html",
        "variables_schema": {
            "policy": "object",
            "prospect": "object",
            "agent": "object",
            "plans": "array",
            "members": "array",
            "benefits": "array",
            "riders": "array",
            "premium_schedule": "array",
            "financial": "object",
            "legal_clauses": "array",
            "signatures": "array",
            "branding": "object",
            "quote": "object",
        },
    },
    {
        "code": "POLICY_SCHEDULE_UNIFIED",
        "name": "Schedule of Benefits",
        "document_type": "POLICY_SCHEDULE",
        "layout_template_path": "documents/policy_schedule.html",
        "variables_schema": {
            "policy": "object",
            "prospect": "object",
            "plans": "array",
            "members": "array",
            "benefits": "array",
            "riders": "array",
            "branding": "object",
            "quote": "object",
        },
    },
]


def seed_templates(apps, schema_editor):
    DocumentTemplate = apps.get_model("documents", "DocumentTemplate")
    for definition in READY_TEMPLATES:
        DocumentTemplate.objects.update_or_create(
            code=definition["code"],
            version=1,
            defaults={
                **definition,
                "branding_config_reference": "COMPANY_BRANDING",
                "is_active": True,
            },
        )


def unseed_templates(apps, schema_editor):
    DocumentTemplate = apps.get_model("documents", "DocumentTemplate")
    DocumentTemplate.objects.filter(code__in=[item["code"] for item in READY_TEMPLATES], version=1).delete()


class Migration(migrations.Migration):
    dependencies = [("documents", "0005_seed_receipt_template")]
    operations = [migrations.RunPython(seed_templates, unseed_templates)]
