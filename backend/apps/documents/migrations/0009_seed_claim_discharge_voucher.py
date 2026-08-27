from django.db import migrations


TEMPLATE = {
    "code": "OL_CLAIM_DISCHARGE_VOUCHER_UNIFIED",
    "name": "OL Claim Discharge Voucher",
    "document_type": "DISCHARGE_VOUCHER",
    "layout_template_path": "documents/discharge_voucher.html",
    "variables_schema": {
        "claim": "object",
        "policy": "object",
        "policyholder": "object",
        "claimant": "object",
        "meta": "object",
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
    dependencies = [("documents", "0008_seed_ol_withdrawal_template")]
    operations = [migrations.RunPython(seed_template, unseed_template)]
