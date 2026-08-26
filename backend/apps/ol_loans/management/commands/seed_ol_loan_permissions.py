from django.core.management.base import BaseCommand
from django.db import transaction

from apps.users.models import PermissionGroup, UserGroup, UserPermission

from ...permissions import ACTIONS


def _permission_payloads():
    return [
        {
            "name": f"OL Loans {action.replace('_', ' ').title()}",
            "codename": f"ol_loans.{action}",
            "module": "ol_loans",
            "action": action.upper(),
            "resource_type": "OL_LOAN",
            "description": f"Ordinary Life Loans {action.replace('_', ' ')}.",
        }
        for action in ACTIONS
    ]


ROLE_SEEDS = [
    {
        "name": "OL Loan Viewer",
        "code": "OL_LOAN_VIEWER",
        "group_type": UserGroup.GroupType.INTERNAL,
        "description": "Read-only access to Ordinary Life loans.",
        "permission_codes": ["ol_loans.view"],
    },
    {
        "name": "OL Loan Handler",
        "code": "OL_LOAN_HANDLER",
        "group_type": UserGroup.GroupType.INTERNAL,
        "description": "Day-to-day loan request, repayment, and servicing operations.",
        "permission_codes": [
            "ol_loans.view",
            "ol_loans.request",
            "ol_loans.repay",
            "ol_loans.print",
        ],
    },
    {
        "name": "OL Loan Administrator",
        "code": "OL_LOAN_ADMINISTRATOR",
        "group_type": UserGroup.GroupType.ADMINISTRATIVE,
        "description": "Full Ordinary Life Loan lifecycle and configuration access.",
        "permission_codes": [f"ol_loans.{action}" for action in ACTIONS],
    },
]


class Command(BaseCommand):
    help = "Seed OL Loans permissions, permission bundle, and system role groups idempotently."

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
            module_code="OL_LOANS",
            name="OL Loans Configuration",
            defaults={"description": "Canonical permission bundle for Ordinary Life loans."},
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
                f"OL Loans permissions seeded: {len(permission_map)} permissions, "
                f"{created_roles} roles created, {updated_roles} roles updated."
            )
        )
