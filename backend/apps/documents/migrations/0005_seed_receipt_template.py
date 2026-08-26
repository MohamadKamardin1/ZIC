from django.db import migrations


RECEIPT_TEMPLATE = {
    "code": "RECEIPT_UNIFIED",
    "name": "Receipt",
    "document_type": "RECEIPT",
    "layout_template_path": "documents/receipt.html",
    "variables_schema": {
        "receipt": "object",
        "meta": "object",
        "financial": "object",
        "branding": "object",
    },
}


def seed_receipt_template(apps, schema_editor):
    DocumentTemplate = apps.get_model("documents", "DocumentTemplate")
    DocumentTemplate.objects.filter(document_type="RECEIPT", is_active=True).update(is_active=False)
    DocumentTemplate.objects.update_or_create(
        code=RECEIPT_TEMPLATE["code"],
        version=1,
        defaults={
            **RECEIPT_TEMPLATE,
            "branding_config_reference": "COMPANY_BRANDING",
            "is_active": True,
        },
    )


def unseed_receipt_template(apps, schema_editor):
    DocumentTemplate = apps.get_model("documents", "DocumentTemplate")
    DocumentTemplate.objects.filter(code=RECEIPT_TEMPLATE["code"], version=1).delete()


class Migration(migrations.Migration):
    dependencies = [("documents", "0004_brandingconfiguration_and_more")]

    operations = [migrations.RunPython(seed_receipt_template, unseed_receipt_template)]
