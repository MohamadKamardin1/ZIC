from django.db import migrations

REPORT_CATEGORIES = [
    ('ordinary_life', 'Ordinary Life', 'Ordinary Life insurance reports.', 'ordinary_life'),
    ('group_credit', 'Group Credit', 'Group Credit insurance reports.', 'group_credit'),
    ('group_life', 'Group Life', 'Group Life insurance reports.', 'group_life'),
    ('claims', 'Claims', 'Claims and claims-settlement reports.', 'claims'),
    ('commission', 'Commission', 'Commission and remuneration reports.', 'commission'),
    ('finance', 'Finance', 'Financial and accounting reports.', 'finance'),
    ('underwriting', 'Underwriting', 'Underwriting and risk reports.', 'underwriting'),
    ('reinsurance', 'Reinsurance', 'Reinsurance and treaty reports.', 'reinsurance'),
    ('audit', 'Audit', 'Audit, compliance, and control reports.', 'audit'),
    ('ifrs17', 'IFRS 17', 'IFRS 17 measurement and disclosure reports.', 'ifrs17'),
]


def seed_report_categories(apps, schema_editor):
    ReportCategory = apps.get_model('users', 'ReportCategory')
    for code, name, description, business_area in REPORT_CATEGORIES:
        category, _ = ReportCategory.objects.get_or_create(
            code=code,
            defaults={
                'name': name,
                'description': description,
                'business_area': business_area,
                'is_active': True,
                'is_system': True,
            },
        )
        category.name = name
        category.description = description
        category.business_area = business_area
        category.is_active = True
        category.is_system = True
        category.save(update_fields=[
            'name', 'description', 'business_area', 'is_active', 'is_system', 'updated_at',
        ])


def reverse_report_categories(apps, schema_editor):
    ReportCategory = apps.get_model('users', 'ReportCategory')
    ReportCategory.objects.filter(code__in=[item[0] for item in REPORT_CATEGORIES]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('users', '0010_reportcategory_usergroupreportcategory_and_more'),
    ]

    operations = [
        migrations.RunPython(seed_report_categories, reverse_report_categories),
    ]
