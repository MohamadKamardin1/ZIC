# Generated manually for ONBOARDING.md remediation
# Seed partner types dynamically via ChoiceList

from django.db import migrations


def seed_partner_types(apps, schema_editor):
    """Seed partner types into ChoiceList for dynamic management"""
    ChoiceList = apps.get_model('system_parameters', 'ChoiceList')
    ChoiceOption = apps.get_model('system_parameters', 'ChoiceOption')

    # Create ChoiceList for partner types
    partner_type_list, _ = ChoiceList.objects.get_or_create(
        code='PARTNER_TYPE_CHOICES',
        defaults={
            'name': 'Partner Types',
            'description': 'Dynamic partner type options',
            'is_active': True,
        }
    )

    types = [
        ('INDIVIDUAL', 'Individual', 1),
        ('CORPORATE', 'Corporate', 2),
        ('AGENT', 'Agent', 3),
        ('BROKER', 'Broker', 4),
        ('BANCASSURER', 'Bancassurer', 5),
        ('SERVICE_PROVIDER', 'Service Provider', 6),
    ]

    for code, label, order in types:
        ChoiceOption.objects.get_or_create(
            choice_list=partner_type_list,
            code=code,
            defaults={
                'label': label,
                'sort_order': order,
                'is_active': True,
            }
        )


def reverse_seed_partner_types(apps, schema_editor):
    """Reverse: remove seeded partner types"""
    ChoiceList = apps.get_model('system_parameters', 'ChoiceList')
    ChoiceList.objects.filter(code='PARTNER_TYPE_CHOICES').delete()


class Migration(migrations.Migration):
    dependencies = [
        ('partner_onboarding', '0005_remove_partner_type_constraint'),
    ]

    operations = [
        migrations.RunPython(seed_partner_types, reverse_seed_partner_types),
    ]
