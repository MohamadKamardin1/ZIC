# Generated manually for ONBOARDING.md remediation
# Remove partner_type database constraint to allow dynamic partner types

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('partner_onboarding', '0004_applicationfieldvalue'),
    ]

    operations = [
        # SQLite rebuilds the table when removing a constraint. A stale view from
        # an older local database can reference onboarding_partner_application
        # while the table is being renamed, causing SQLite to abort the rebuild
        # with: "error in view onboarding_unified_record". The canonical view is
        # recreated by migration 0008, so it is safe to remove it here first.
        migrations.RunSQL(
            sql="DROP VIEW IF EXISTS onboarding_unified_record;",
            reverse_sql=migrations.RunSQL.noop,
        ),
        # Remove the database constraint that only allows INDIVIDUAL/CORPORATE
        migrations.RemoveConstraint(
            model_name='partnerapplication',
            name='valid_partner_type',
        ),
    ]
