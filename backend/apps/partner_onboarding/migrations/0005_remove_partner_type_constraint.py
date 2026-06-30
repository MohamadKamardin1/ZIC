# Generated manually for ONBOARDING.md remediation
# Remove partner_type database constraint to allow dynamic partner types

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('partner_onboarding', '0004_applicationfieldvalue'),
    ]

    operations = [
        # Remove the database constraint that only allows INDIVIDUAL/CORPORATE
        migrations.RemoveConstraint(
            model_name='partnerapplication',
            name='valid_partner_type',
        ),
    ]
