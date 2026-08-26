from django.core.management.base import BaseCommand
from django.db import transaction

from apps.users.models import PermissionGroup, UserGroup, UserPermission

PERMISSIONS = [
    {
        "name": "View OL Parameters",
        "codename": "ol_parameters.view",
        "module": "ol_parameters",
        "action": "VIEW",
        "resource_type": "OL_PARAMETER",
        "description": "View, list, retrieve, search, filter, and export OL parameter catalogs.",
    },
    {
        "name": "Create OL Parameters",
        "codename": "ol_parameters.create",
        "module": "ol_parameters",
        "action": "CREATE",
        "resource_type": "OL_PARAMETER",
        "description": "Create OL parameter configuration records.",
    },
    {
        "name": "Update OL Parameters",
        "codename": "ol_parameters.update",
        "module": "ol_parameters",
        "action": "UPDATE",
        "resource_type": "OL_PARAMETER",
        "description": "Update OL parameter configuration records.",
    },
    {
        "name": "Deactivate OL Parameters",
        "codename": "ol_parameters.deactivate",
        "module": "ol_parameters",
        "action": "DEACTIVATE",
        "resource_type": "OL_PARAMETER",
        "description": "Soft-deactivate OL parameter configuration records.",
    },
    {
        "name": "Configure OL Parameters",
        "codename": "ol_parameters.configure",
        "module": "ol_parameters",
        "action": "CONFIGURE",
        "resource_type": "OL_PARAMETER",
        "description": "Configure and administer OL parameter catalogs and registry metadata.",
    },
]


ROLE_SEEDS = [
    {
        "name": "OL Parameter Viewer",
        "code": "OL_PARAMETER_VIEWER",
        "group_type": UserGroup.GroupType.INTERNAL,
        "description": "Read-only access to all Ordinary Life parameter catalogs.",
        "permission_codes": ["ol_parameters.view"],
    },
    {
        "name": "OL Parameter Configurator",
        "code": "OL_PARAMETER_CONFIGURATOR",
        "group_type": UserGroup.GroupType.INTERNAL,
        "description": "Create and update Ordinary Life parameter catalogs without lifecycle deactivation.",
        "permission_codes": [
            "ol_parameters.view",
            "ol_parameters.create",
            "ol_parameters.update",
        ],
    },
    {
        "name": "OL Parameter Administrator",
        "code": "OL_PARAMETER_ADMINISTRATOR",
        "group_type": UserGroup.GroupType.ADMINISTRATIVE,
        "description": "Full lifecycle and registry administration for Ordinary Life parameters.",
        "permission_codes": [
            "ol_parameters.view",
            "ol_parameters.create",
            "ol_parameters.update",
            "ol_parameters.deactivate",
            "ol_parameters.configure",
        ],
    },
]


class Command(BaseCommand):
    help = "Seed OL Parameters permissions, permission group, and role groups idempotently."

    @transaction.atomic
    def handle(self, *args, **options):
        permission_map = {}
        for payload in PERMISSIONS:
            permission, _ = UserPermission.objects.update_or_create(
                codename=payload["codename"],
                defaults=payload,
            )
            permission_map[permission.codename] = permission

        permission_group, _ = PermissionGroup.objects.update_or_create(
            module_code="OL_PARAMETERS",
            name="OL Parameters Configuration",
            defaults={
                "description": "Canonical permission bundle for Ordinary Life parameter configuration.",
            },
        )
        permission_group.permissions.set(permission_map.values())

        created_roles = 0
        updated_roles = 0
        for role in ROLE_SEEDS:
            group, was_created = UserGroup.objects.update_or_create(
                code=role["code"],
                defaults={
                    "name": role["name"],
                    "description": role["description"],
                    "group_type": role["group_type"],
                    "is_active": True,
                    "is_system": True,
                    "is_system_group": True,
                },
            )
            group.permissions.set(
                [permission_map[codename] for codename in role["permission_codes"]]
            )
            if was_created:
                created_roles += 1
            else:
                updated_roles += 1

        self.stdout.write(
            self.style.SUCCESS(
                "OL Parameters permissions seeded: "
                f"{len(permission_map)} permissions, {created_roles} roles created, "
                f"{updated_roles} roles updated."
            )
        )
