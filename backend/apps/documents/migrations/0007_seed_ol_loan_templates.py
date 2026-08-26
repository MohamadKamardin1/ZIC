from django.db import migrations


TEMPLATES = [
    {
        "code": "OL_LOAN_AGREEMENT_UNIFIED",
        "name": "OL Loan Agreement",
        "document_type": "OL_LOAN_AGREEMENT",
        "layout_template_path": "documents/ol_loan_agreement.html",
        "variables_schema": {
            "loan": "object",
            "policy": "object",
            "parties": "object",
            "principal": "string",
            "interest_rate": "string",
            "term": "string",
            "schedule": "array",
            "signatures": "array",
            "branding": "object",
        },
    },
    {
        "code": "OL_LOAN_SCHEDULE_UNIFIED",
        "name": "OL Loan Repayment Schedule",
        "document_type": "OL_LOAN_SCHEDULE",
        "layout_template_path": "documents/ol_loan_schedule.html",
        "variables_schema": {
            "loan": "object",
            "policy": "object",
            "parties": "object",
            "schedule": "array",
            "schedule_summary": "object",
            "signatures": "array",
            "branding": "object",
        },
    },
]


def seed_templates(apps, schema_editor):
    DocumentTemplate = apps.get_model("documents", "DocumentTemplate")
    for definition in TEMPLATES:
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
    DocumentTemplate.objects.filter(code__in=[item["code"] for item in TEMPLATES], version=1).delete()


class Migration(migrations.Migration):
    dependencies = [("documents", "0006_seed_policy_templates")]
    operations = [migrations.RunPython(seed_templates, unseed_templates)]
