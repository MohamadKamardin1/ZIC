from django.db import migrations


TEMPLATE = {
    "code": "OL_WITHDRAWAL_STATEMENT_UNIFIED",
    "name": "OL Withdrawal Statement",
    "document_type": "OL_WITHDRAWAL_STATEMENT",
    "layout_template_path": "documents/ol_withdrawal_statement.html",
    "variables_schema": {
        "withdrawal": "object",
        "policy": "object",
        "parties": "object",
        "financial": "object",
        "signatures": "array",
        "branding": "object",
    },
}


def seed_template(apps, schema_editor):
    DocumentTemplate = apps.get_model("documents", "DocumentTemplate")
    DocumentTemplate.objects.update_or_create(
        code=TEMPLATE["code"],
        version=1,
        defaults={
            **TEMPLATE,
            "branding_config_reference": "COMPANY_BRANDING",
            "is_active": True,
        },
    )


def unseed_template(apps, schema_editor):
    DocumentTemplate = apps.get_model("documents", "DocumentTemplate")
    DocumentTemplate.objects.filter(code=TEMPLATE["code"], version=1).delete()


class Migration(migrations.Migration):
    dependencies = [("documents", "0007_seed_ol_loan_templates")]
    operations = [migrations.RunPython(seed_template, unseed_template)]
