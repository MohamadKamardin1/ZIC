from django.core.management.base import BaseCommand
from django.db import transaction

from apps.users.models import PermissionGroup, UserGroup, UserPermission

from ...permissions import ACTIONS


def _permission_payloads():
    return [
        {
            "name": f"OL Commitments {action.replace('_', ' ').title()}",
            "codename": f"ol_commitments.{action}",
            "module": "ol_commitments",
            "action": action.upper(),
            "resource_type": "OL_COMMITMENT",
            "description": f"OL Commitments {action.replace('_', ' ')}.",
        }
        for action in ACTIONS
    ]


ROLE_SEEDS = [
    {
        "name": "OL Commitment Viewer",
        "code": "OL_COMMITMENT_VIEWER",
        "group_type": UserGroup.GroupType.INTERNAL,
        "description": "Read-only access to Ordinary Life commitments.",
        "permission_codes": ["ol_commitments.view"],
    },
    {
        "name": "OL Commitment Handler",
        "code": "OL_COMMITMENT_HANDLER",
        "group_type": UserGroup.GroupType.INTERNAL,
        "description": "Day-to-day commitment operations: generate, record payments, reschedule.",
        "permission_codes": [
            "ol_commitments.view",
            "ol_commitments.create",
            "ol_commitments.generate",
            "ol_commitments.record_payment",
            "ol_commitments.suspend",
            "ol_commitments.reschedule",
        ],
    },
    {
        "name": "OL Commitment Administrator",
        "code": "OL_COMMITMENT_ADMINISTRATOR",
        "group_type": UserGroup.GroupType.ADMINISTRATIVE,
        "description": "Full commitment lifecycle including reversal, waive, and cancel.",
        "permission_codes": [f"ol_commitments.{action}" for action in ACTIONS],
    },
]


class Command(BaseCommand):
    help = "Seed OL Commitments permissions, permission group, and role groups idempotently."

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
            module_code="OL_COMMITMENTS",
            name="OL Commitments Configuration",
            defaults={
                "description": "Canonical permission bundle for Ordinary Life commitments.",
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
                "OL Commitments permissions seeded: "
                f"{len(permission_map)} permissions, {created_roles} roles created, "
                f"{updated_roles} roles updated."
            )
        )
