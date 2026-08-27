from django.core.management.base import BaseCommand
from django.db import transaction

from apps.users.models import PermissionGroup, UserGroup, UserPermission

from ...permissions import ACTIONS


MODULE = "ol_claims"
RESOURCE_TYPE = "OL_CLAIM"


def _permission_payloads():
    return [
        {
            "name": f"OL Claims {action.replace('_', ' ').title()}",
            "codename": f"{MODULE}.{action}",
            "module": MODULE,
            "action": action.upper(),
            "resource_type": RESOURCE_TYPE,
            "description": f"{action.replace('_', ' ').title()} access to Ordinary Life claims.",
            "is_active": True,
        }
        for action in ACTIONS
    ]


ROLE_SEEDS = [
    {
        "name": "OL Claims Viewer",
        "code": "OL_CLAIMS_VIEWER",
        "group_type": UserGroup.GroupType.INTERNAL,
        "description": "Read-only access to Ordinary Life claims.",
        "permission_codes": ["ol_claims.view"],
    },
    {
        "name": "OL Claims Handler",
        "code": "OL_CLAIMS_HANDLER",
        "group_type": UserGroup.GroupType.INTERNAL,
        "description": "Register and assess Ordinary Life claims.",
        "permission_codes": ["ol_claims.view", "ol_claims.register", "ol_claims.assess", "ol_claims.print"],
    },
    {
        "name": "OL Claims Administrator",
        "code": "OL_CLAIMS_ADMINISTRATOR",
        "group_type": UserGroup.GroupType.ADMINISTRATIVE,
        "description": "Full Ordinary Life claims lifecycle access.",
        "permission_codes": [f"{MODULE}.{action}" for action in ACTIONS],
    },
]


class Command(BaseCommand):
    help = "Seed OL Claims permissions, permission group, and role groups idempotently."

    @transaction.atomic
    def handle(self, *args, **options):
        permission_map = {}
        for payload in _permission_payloads():
            permission, _ = UserPermission.objects.update_or_create(
                codename=payload["codename"],
                defaults=payload,
            )
            permission_map[permission.codename] = permission

        permission_group, _ = PermissionGroup.objects.update_or_create(
            module_code="OL_CLAIMS",
            name="OL Claims Workflow",
            defaults={
                "description": "Canonical permission bundle for Ordinary Life claims.",
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
            group.permissions.set([permission_map[code] for code in role["permission_codes"]])
            if was_created:
                created_roles += 1
            else:
                updated_roles += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"OL Claims permissions seeded: {len(permission_map)} permissions, "
                f"{created_roles} roles created, {updated_roles} roles updated."
            )
        )
