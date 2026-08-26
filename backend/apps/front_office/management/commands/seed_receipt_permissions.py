from django.core.management.base import BaseCommand
from django.db import transaction

from apps.front_office.receipts.permissions import ACTIONS
from apps.users.models import PermissionGroup, UserGroup, UserPermission

MODULE = "front_office.receipts"


def _permission_payloads():
    return [
        {
            "name": f"Front Office Receipts {action.replace('_', ' ').title()}",
            "codename": f"{MODULE}.{action}",
            "module": MODULE,
            "action": action.upper(),
            "resource_type": "RECEIPT",
            "description": f"Front Office Receipts {action.replace('_', ' ')}.",
        }
        for action in ACTIONS
    ]


ROLE_SEEDS = [
    {
        "name": "Receipt Viewer",
        "code": "RECEIPT_VIEWER",
        "group_type": UserGroup.GroupType.INTERNAL,
        "description": "Read-only access to Front Office receipts.",
        "permission_codes": ["front_office.receipts.view"],
    },
    {
        "name": "Receipt Handler",
        "code": "RECEIPT_HANDLER",
        "group_type": UserGroup.GroupType.INTERNAL,
        "description": "Day-to-day receipt operations: create, post, allocate, and print receipts.",
        "permission_codes": [
            "front_office.receipts.view",
            "front_office.receipts.create",
            "front_office.receipts.post",
            "front_office.receipts.allocate",
            "front_office.receipts.print",
        ],
    },
    {
        "name": "Receipt Administrator",
        "code": "RECEIPT_ADMINISTRATOR",
        "group_type": UserGroup.GroupType.ADMINISTRATIVE,
        "description": "Full receipt lifecycle including reversal, cancellation, import, and configuration.",
        "permission_codes": [f"{MODULE}.{action}" for action in ACTIONS],
    },
]


class Command(BaseCommand):
    help = "Seed Front Office Receipts permissions, permission group, and role groups idempotently."

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
            module_code="FRONT_OFFICE_RECEIPTS",
            name="Front Office Receipts Configuration",
            defaults={
                "description": "Canonical permission bundle for Front Office receipts.",
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
            group.permissions.set([permission_map[codename] for codename in role["permission_codes"]])
            if was_created:
                created_roles += 1
            else:
                updated_roles += 1

        self.stdout.write(
            self.style.SUCCESS(
                "Front Office Receipts permissions seeded: "
                f"{len(permission_map)} permissions, {created_roles} roles created, "
                f"{updated_roles} roles updated."
            )
        )
