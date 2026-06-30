from django.db import migrations

def update_user_type_choices(apps, schema_editor):
    ChoiceList = apps.get_model('system_parameters', 'ChoiceList')
    ChoiceOption = apps.get_model('system_parameters', 'ChoiceOption')
    
    cl = ChoiceList.objects.filter(code='USER_TYPE_CHOICES').first()
    if cl:
        option = ChoiceOption.objects.filter(choice_list=cl, code='AIMS_GROUP').first()
        if option:
            option.code = 'ZIC_GROUP'
            option.label = 'ZIC Group'
            option.save()

def reverse_user_type_choices(apps, schema_editor):
    ChoiceList = apps.get_model('system_parameters', 'ChoiceList')
    ChoiceOption = apps.get_model('system_parameters', 'ChoiceOption')
    
    cl = ChoiceList.objects.filter(code='USER_TYPE_CHOICES').first()
    if cl:
        option = ChoiceOption.objects.filter(choice_list=cl, code='ZIC_GROUP').first()
        if option:
            option.code = 'AIMS_GROUP'
            option.label = 'AIMS Group'
            option.save()

class Migration(migrations.Migration):
    dependencies = [
        ('system_parameters', '0010_clear_app_status_choices'),
    ]

    operations = [
        migrations.RunPython(update_user_type_choices, reverse_user_type_choices),
    ]
