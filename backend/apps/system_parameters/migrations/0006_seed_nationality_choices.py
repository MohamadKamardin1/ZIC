"""Seed NATIONALITY_CHOICES choice list."""
from django.db import migrations

NATIONALITIES = [
    ("TANZANIAN", "Tanzanian"),
    ("UGANDAN", "Ugandan"),
    ("KENYAN", "Kenyan"),
    ("RWANDAN", "Rwandan"),
    ("BURUNDIAN", "Burundian"),
    ("SOUTH_SUDANESE", "South Sudanese"),
    ("ETHIOPIAN", "Ethiopian"),
    ("SOMALI", "Somali"),
    ("CONGOLESE", "Congolese (DRC)"),
    ("ZAMBIAN", "Zambian"),
    ("MALAWI", "Malawian"),
    ("MOZAMBICAN", "Mozambican"),
    ("ZIMBABWEAN", "Zimbabwean"),
    ("BOTSWANAN", "Botswanan"),
    ("NAMIBIAN", "Namibian"),
    ("SOUTH_AFRICAN", "South African"),
    ("NIGERIAN", "Nigerian"),
    ("GHANAIAN", "Ghanaian"),
    ("INDIAN", "Indian"),
    ("PAKISTANI", "Pakistani"),
    ("BANGLADESHI", "Bangladeshi"),
    ("CHINESE", "Chinese"),
    ("BRITISH", "British"),
    ("AMERICAN", "American"),
    ("CANADIAN", "Canadian"),
    ("GERMAN", "German"),
    ("FRENCH", "French"),
    ("DUTCH", "Dutch"),
    ("ITALIAN", "Italian"),
    ("SPANISH", "Spanish"),
    ("PORTUGUESE", "Portuguese"),
    ("SWEDISH", "Swedish"),
    ("NORWEGIAN", "Norwegian"),
    ("SWISS", "Swiss"),
    ("EMIRATI", "Emirati"),
    ("SAUDI", "Saudi Arabian"),
    ("QATARI", "Qatari"),
    ("OMANI", "Omani"),
    ("KUWAITI", "Kuwaiti"),
    ("OTHER", "Other"),
]

def seed_nationalities(apps, schema_editor):
    ChoiceList = apps.get_model("system_parameters", "ChoiceList")
    ChoiceOption = apps.get_model("system_parameters", "ChoiceOption")
    ParameterGroup = apps.get_model("system_parameters", "ParameterGroup")

    partner = ParameterGroup.objects.get(code="PARTNER")

    natl, _ = ChoiceList.objects.get_or_create(
        code="NATIONALITY_CHOICES",
        defaults={"group": partner, "name": "Nationalities"},
    )
    for code, label in NATIONALITIES:
        ChoiceOption.objects.get_or_create(
            choice_list=natl, code=code, defaults={"label": label, "sort_order": 0},
        )

def unseed_nationalities(apps, schema_editor):
    ChoiceList = apps.get_model("system_parameters", "ChoiceList")
    ChoiceList.objects.filter(code="NATIONALITY_CHOICES").delete()

class Migration(migrations.Migration):
    dependencies = [
        ("system_parameters", "0005_seed_commission_parameters"),
    ]
    operations = [
        migrations.RunPython(seed_nationalities, unseed_nationalities),
    ]
