from django.core.management.base import BaseCommand
from django.db import transaction

from apps.users.models import PermissionGroup, UserGroup, UserPermission

from ...permissions import ACTIONS

MODULE = "ol_maturity_installments"
RESOURCE_TYPE = "OL_MATURITY_INSTALLMENT"


def _permission_payloads():
    return [
        {
            "name": f"OL Maturity Installments {action.replace('_', ' ').title()}",
            "codename": f"{MODULE}.{action}",
            "module": MODULE,
            "action": action.upper(),
            "resource_type": RESOURCE_TYPE,
            "description": f"{action.replace('_', ' ').title()} access to Ordinary Life maturity installments.",
            "is_active": True,
        }
        for action in ACTIONS
    ]


ROLE_SEEDS = [
    {
        "name": "OL Maturity Installments Viewer",
        "code": "OL_MATURITY_INSTALLMENTS_VIEWER",
        "group_type": UserGroup.GroupType.INTERNAL,
        "description": "Read-only access to Ordinary Life maturity installments.",
        "permission_codes": ["ol_maturity_installments.view"],
    },
    {
        "name": "OL Maturity Installments Handler",
        "code": "OL_MATURITY_INSTALLMENTS_HANDLER",
        "group_type": UserGroup.GroupType.INTERNAL,
        "description": "Create installment plans, process payments, and print maturity installment documents.",
        "permission_codes": [
            "ol_maturity_installments.view",
            "ol_maturity_installments.create",
            "ol_maturity_installments.process_payment",
            "ol_maturity_installments.print",
        ],
    },
    {
        "name": "OL Maturity Installments Administrator",
        "code": "OL_MATURITY_INSTALLMENTS_ADMINISTRATOR",
        "group_type": UserGroup.GroupType.ADMINISTRATIVE,
        "description": "Full Ordinary Life maturity installments lifecycle access.",
        "permission_codes": [f"{MODULE}.{action}" for action in ACTIONS],
    },
]


class Command(BaseCommand):
    help = "Seed OL Maturity Installments permissions and role groups idempotently."

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
            module_code="OL_MATURITY_INSTALLMENTS",
            name="OL Maturity Installments Workflow",
            defaults={
                "description": "Canonical permission bundle for Ordinary Life maturity installments.",
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
                f"OL Maturity Installments permissions seeded: {len(permission_map)} permissions, "
                f"{created_roles} roles created, {updated_roles} roles updated."
            )
        )
