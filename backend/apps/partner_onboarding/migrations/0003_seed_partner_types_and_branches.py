from django.db import migrations


def seed_partner_types(apps, schema_editor):
    PartnerType = apps.get_model("partners", "PartnerType")
    defaults = [
        ("CLIENT", "Client", "Standard client partner"),
        ("INTERMEDIARY", "Intermediary", "Intermediary partner"),
        ("SERVICE_PROVIDER", "Service Provider", "Service provider partner"),
        ("BROKER", "Broker", "Broker partner"),
        ("MEDICAL_PRACTITIONER", "Medical Practitioner", "Medical practitioner partner"),
    ]
    for code, name, desc in defaults:
        PartnerType.objects.get_or_create(
            code=code,
            defaults={"name": name, "description": desc, "is_active": True},
        )


def seed_default_branch(apps, schema_editor):
    Branch = apps.get_model("partner_onboarding", "Branch")
    Branch.objects.get_or_create(
        code="HQ",
        defaults={"name": "Head Office", "is_active": True},
    )


class Migration(migrations.Migration):

    dependencies = [
        ("partners", "__first__"),
        ("partner_onboarding", "0002_branch_alter_partnerapplication_status_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_partner_types),
        migrations.RunPython(seed_default_branch),
    ]
