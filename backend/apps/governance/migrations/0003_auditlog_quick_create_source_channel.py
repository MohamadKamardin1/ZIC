from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("governance", "0002_auditlog_action_auditlog_actor_type_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="auditlog",
            name="source_channel",
            field=models.CharField(
                choices=[
                    ("WEB", "Web"),
                    ("API", "API"),
                    ("ADMIN", "Admin"),
                    ("SYSTEM", "System"),
                    ("IMPORT", "Import"),
                    ("PORTAL", "Portal"),
                    ("BATCH", "Batch"),
                    ("QUICK_CREATE", "Quick create"),
                ],
                default="SYSTEM",
                db_index=True,
                max_length=20,
            ),
        ),
    ]
