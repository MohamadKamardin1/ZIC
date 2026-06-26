import logging

from django.db import migrations


logger = logging.getLogger(__name__)


def populate_partner_category(apps, schema_editor):
    Partner = apps.get_model("partners", "Partner")
    count = 0
    for partner in Partner.objects.filter(partner_category=""):
        if partner.partner_type in ("INDIVIDUAL", "CORPORATE"):
            partner.partner_category = partner.partner_type
        elif partner.first_name:
            partner.partner_category = "INDIVIDUAL"
        elif partner.company_name:
            partner.partner_category = "CORPORATE"
        else:
            partner.partner_category = partner.partner_type or "INDIVIDUAL"
        partner.save(update_fields=["partner_category"])
        count += 1
    if count:
        logger.info("Populated partner_category for %s partner(s)", count)


def populate_individual_profiles(apps, schema_editor):
    Partner = apps.get_model("partners", "Partner")
    IndividualProfile = apps.get_model("partners", "IndividualProfile")
    created = 0
    for partner in Partner.objects.filter(
        partner_category__in=("INDIVIDUAL", ""),
    ).exclude(first_name="", surname=""):
        IndividualProfile.objects.get_or_create(
            partner=partner,
            defaults={
                "identification_type": partner.identification_type,
                "identification_number": partner.identification_number,
                "title": partner.title,
                "first_name": partner.first_name,
                "other_name": partner.other_name,
                "surname": partner.surname,
                "gender": partner.gender,
                "date_of_birth": partner.date_of_birth,
                "marital_status": partner.marital_status,
                "occupation": partner.occupation,
                "nationality": partner.nationality,
            },
        )
        created += 1
    if created:
        logger.info("Created IndividualProfile for %s partner(s)", created)


def populate_corporate_profiles(apps, schema_editor):
    Partner = apps.get_model("partners", "Partner")
    CorporateProfile = apps.get_model("partners", "CorporateProfile")
    created = 0
    for partner in Partner.objects.filter(
        partner_category__in=("CORPORATE", ""),
    ).exclude(company_name=""):
        CorporateProfile.objects.get_or_create(
            partner=partner,
            defaults={
                "company_name": partner.company_name,
                "tin_number": partner.tin_number,
                "incorporation_date": partner.incorporation_date,
                "industry": partner.industry,
                "contact_person": partner.contact_person,
                "contact_person_phone": partner.contact_person_phone,
                "contact_person_email": partner.contact_person_email,
            },
        )
        created += 1
    if created:
        logger.info("Created CorporateProfile for %s partner(s)", created)


def reverse_func(apps, schema_editor):
    IndividualProfile = apps.get_model("partners", "IndividualProfile")
    CorporateProfile = apps.get_model("partners", "CorporateProfile")
    IndividualProfile.objects.all().delete()
    CorporateProfile.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0004_partner_partner_category_corporateprofile_and_more'),
    ]

    operations = [
        migrations.RunPython(populate_partner_category, migrations.RunPython.noop),
        migrations.RunPython(populate_individual_profiles, reverse_func),
        migrations.RunPython(populate_corporate_profiles, reverse_func),
    ]
