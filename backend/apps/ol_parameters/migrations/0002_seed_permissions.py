from django.db import migrations


PERMISSIONS = (
    ("VIEW", "View", "ol_parameters.view"),
    ("CREATE", "Create", "ol_parameters.create"),
    ("UPDATE", "Update", "ol_parameters.update"),
    ("DEACTIVATE", "Deactivate", "ol_parameters.deactivate"),
    ("CONFIGURE", "Configure", "ol_parameters.configure"),
)


def seed_permissions(apps, schema_editor):
    UserPermission = apps.get_model("users", "UserPermission")
    for action, label, codename in PERMISSIONS:
        permission, _ = UserPermission.objects.get_or_create(
            module="ol_parameters",
            action=action,
            resource_type="",
            defaults={
                "name": f"{label} OL Parameters",
                "codename": codename,
                "description": f"{label} access to Ordinary Life parameter configuration.",
                "is_active": True,
            },
        )
        changed = []
        if permission.codename != codename:
            permission.codename = codename
            changed.append("codename")
        if not permission.name:
            permission.name = f"{label} OL Parameters"
            changed.append("name")
        if not permission.description:
            permission.description = f"{label} access to Ordinary Life parameter configuration."
            changed.append("description")
        if not permission.is_active:
            permission.is_active = True
            changed.append("is_active")
        if changed:
            permission.save(update_fields=changed + ["updated_at"])


def remove_permissions(apps, schema_editor):
    UserPermission = apps.get_model("users", "UserPermission")
    UserPermission.objects.filter(module="ol_parameters").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("ol_parameters", "0001_initial"),
        ("users", "0011_seed_report_categories"),
    ]

    operations = [migrations.RunPython(seed_permissions, remove_permissions)]
