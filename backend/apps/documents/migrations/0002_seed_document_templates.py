from django.db import migrations


DEFAULT_VARIABLES_SCHEMA = {
    "quote": "object",
    "prospect": "object",
    "plans": "array",
    "riders": "array",
    "benefits": "array",
    "installments": "array",
    "financial": "object",
    "agent": "object",
    "branding": "object",
}


def seed_templates(apps, schema_editor):
    DocumentTemplate = apps.get_model("documents", "DocumentTemplate")
    DocumentTemplate.objects.get_or_create(
        code="OL_QUOTATION_UNIFIED",
        version=1,
        defaults={
            "name": "Ordinary Life Quotation",
            "document_type": "OL_QUOTATION",
            "layout_template_path": "documents/ol_quotation.html",
            "variables_schema": DEFAULT_VARIABLES_SCHEMA,
            "branding_config_reference": "COMPANY_BRANDING",
            "is_active": True,
        },
    )


def unseed_templates(apps, schema_editor):
    DocumentTemplate = apps.get_model("documents", "DocumentTemplate")
    DocumentTemplate.objects.filter(code="OL_QUOTATION_UNIFIED", version=1).delete()


class Migration(migrations.Migration):
    dependencies = [("documents", "0001_initial")]

    operations = [migrations.RunPython(seed_templates, unseed_templates)]
