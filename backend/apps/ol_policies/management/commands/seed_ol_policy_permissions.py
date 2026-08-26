from django.core.management.base import BaseCommand
from django.db import transaction

from apps.users.models import PermissionGroup, UserGroup, UserPermission

from ...permissions import ACTIONS


def permission_payloads():
    return [
        {
            "name": f"OL Policies {action.replace('_', ' ').title()}",
            "codename": f"ol_policies.{action}",
            "module": "ol_policies",
            "action": action.upper(),
            "resource_type": "OL_POLICY",
            "description": f"Ordinary Life Policies {action.replace('_', ' ')}.",
        }
        for action in ACTIONS
    ]


ROLE_SEEDS = [
    {
        "name": "OL Policy Viewer",
        "code": "OL_POLICY_VIEWER",
        "group_type": UserGroup.GroupType.INTERNAL,
        "description": "Read-only access to Ordinary Life policy records.",
        "permission_codes": ["ol_policies.view"],
    },
    {
        "name": "OL Policy Servicing Officer",
        "code": "OL_POLICY_SERVICING_OFFICER",
        "group_type": UserGroup.GroupType.INTERNAL,
        "description": "Day-to-day Ordinary Life policy servicing access.",
        "permission_codes": [
            "ol_policies.view",
            "ol_policies.service",
            "ol_policies.endorse",
            "ol_policies.print",
            "ol_policies.reinstate",
        ],
    },
    {
        "name": "OL Policy Administrator",
        "code": "OL_POLICY_ADMINISTRATOR",
        "group_type": UserGroup.GroupType.ADMINISTRATIVE,
        "description": "Full Ordinary Life policy lifecycle and configuration access.",
        "permission_codes": [f"ol_policies.{action}" for action in ACTIONS],
    },
]


class Command(BaseCommand):
    help = "Seed OL Policies permissions, permission group, and role groups idempotently."

    @transaction.atomic
    def handle(self, *args, **options):
        permission_map = {}
        for payload in permission_payloads():
            permission, _ = UserPermission.objects.update_or_create(
                codename=payload["codename"],
                defaults=payload,
            )
            permission_map[permission.codename] = permission

        permission_group, _ = PermissionGroup.objects.update_or_create(
            module_code="OL_POLICIES",
            name="OL Policies Configuration",
            defaults={
                "description": "Canonical permission bundle for Ordinary Life policies.",
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
                "OL Policies permissions seeded: "
                f"{len(permission_map)} permissions, {created_roles} roles created, "
                f"{updated_roles} roles updated."
            )
        )
