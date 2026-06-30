# Generated manually for ONBOARDING.md remediation
# Seed system parameters for dynamic configuration (CORRECTED)

from django.db import migrations
import json


def seed_system_parameters(apps, schema_editor):
    """Seed system parameters for dynamic configuration"""
    SystemParameter = apps.get_model('system_parameters', 'SystemParameter')
    ParameterGroup = apps.get_model('system_parameters', 'ParameterGroup')

    # Create parameter groups
    system_group, _ = ParameterGroup.objects.get_or_create(
        code='SYSTEM_CONFIG',
        defaults={'name': 'System Configuration', 'description': 'Core system configuration'}
    )

    dashboard_group, _ = ParameterGroup.objects.get_or_create(
        code='DASHBOARD_CONFIG',
        defaults={'name': 'Dashboard Configuration', 'description': 'Dashboard display configuration'}
    )

    agency_group, _ = ParameterGroup.objects.get_or_create(
        code='AGENCY_CONFIG',
        defaults={'name': 'Agency Configuration', 'description': 'Agent hierarchy configuration'}
    )

    financial_group, _ = ParameterGroup.objects.get_or_create(
        code='FINANCIAL_CONFIG',
        defaults={'name': 'Financial Configuration', 'description': 'Financial profiling configuration'}
    )

    # System parameters
    SystemParameter.objects.get_or_create(
        group=system_group,
        code='DEFAULT_CURRENCY',
        defaults={
            'name': 'Default Currency',
            'value_type': 'STRING',
            'string_value': 'TZS',
            'description': 'Default operational currency',
            'is_active': True,
        }
    )

    SystemParameter.objects.get_or_create(
        group=system_group,
        code='MIN_PARTNER_AGE',
        defaults={
            'name': 'Minimum Partner Age',
            'value_type': 'INTEGER',
            'integer_value': 18,
            'description': 'Minimum age for individual partners',
            'is_active': True,
        }
    )

    # Dashboard mapping
    SystemParameter.objects.get_or_create(
        group=dashboard_group,
        code='PARTNER_TYPE_MAPPING',
        defaults={
            'name': 'Partner Type Dashboard Mapping',
            'value_type': 'JSON',
            'json_value': {
                'INDIVIDUAL': 'client',
                'CORPORATE': 'intermediary',
                'AGENT': 'serviceProvider',
                'BROKER': 'coInsurer',
                'BANCASSURER': 'coInsurer',
                'SERVICE_PROVIDER': 'serviceProvider',
            },
            'description': 'Mapping of partner types to dashboard categories',
            'is_active': True,
        }
    )

    # Agency config
    SystemParameter.objects.get_or_create(
        group=agency_group,
        code='MAX_SUBORDINATES_PER_MASTER_AGENT',
        defaults={
            'name': 'Max Subordinates per Master Agent',
            'value_type': 'INTEGER',
            'integer_value': 50,
            'description': 'Maximum number of subordinate agents per master agent',
            'is_active': True,
        }
    )

    # Financial config
    SystemParameter.objects.get_or_create(
        group=financial_group,
        code='FINANCIAL_SUITABILITY_THRESHOLD',
        defaults={
            'name': 'Financial Suitability Threshold',
            'value_type': 'INTEGER',
            'integer_value': 60,
            'description': 'Minimum score for financial suitability approval',
            'is_active': True,
        }
    )

    SystemParameter.objects.get_or_create(
        group=financial_group,
        code='MIN_ANNUAL_INCOME_TZS',
        defaults={
            'name': 'Minimum Annual Income (TZS)',
            'value_type': 'INTEGER',
            'integer_value': 5000000,
            'description': 'Minimum annual income for partner approval',
            'is_active': True,
        }
    )


def reverse_seed_system_parameters(apps, schema_editor):
    """Reverse: remove seeded system parameters"""
    SystemParameter = apps.get_model('system_parameters', 'SystemParameter')
    SystemParameter.objects.filter(code__in=[
        'DEFAULT_CURRENCY',
        'MIN_PARTNER_AGE',
        'PARTNER_TYPE_MAPPING',
        'MAX_SUBORDINATES_PER_MASTER_AGENT',
        'FINANCIAL_SUITABILITY_THRESHOLD',
        'MIN_ANNUAL_INCOME_TZS',
    ]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('system_parameters', '0007_seed_all_choice_lists'),
    ]

    operations = [
        migrations.RunPython(seed_system_parameters, reverse_seed_system_parameters),
    ]
