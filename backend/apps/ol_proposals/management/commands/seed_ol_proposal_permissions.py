from django.core.management.base import BaseCommand
from django.db import transaction

from apps.users.models import PermissionGroup, UserGroup, UserPermission

from ...permissions import ACTIONS


def _permission_payloads():
    return [
        {
            "name": f"OL Proposals {action.replace('_', ' ').title()}",
            "codename": f"ol_proposals.{action}",
            "module": "ol_proposals",
            "action": action.upper(),
            "resource_type": "OL_PROPOSAL",
            "description": f"OL Proposals {action.replace('_', ' ')}.",
        }
        for action in ACTIONS
    ]


ROLE_SEEDS = [
    {
        "name": "OL Proposal Viewer",
        "code": "OL_PROPOSAL_VIEWER",
        "group_type": UserGroup.GroupType.INTERNAL,
        "description": "Read-only access to Ordinary Life proposals.",
        "permission_codes": ["ol_proposals.view"],
    },
    {
        "name": "OL Proposal Handler",
        "code": "OL_PROPOSAL_HANDLER",
        "group_type": UserGroup.GroupType.INTERNAL,
        "description": "Day-to-day proposal operations: create, enrich, upload documents, payment readiness.",
        "permission_codes": [
            "ol_proposals.view",
            "ol_proposals.create",
            "ol_proposals.enrich",
            "ol_proposals.upload_documents",
            "ol_proposals.mark_payment_ready",
            "ol_proposals.cancel",
            "ol_proposals.print",
        ],
    },
    {
        "name": "OL Proposal Administrator",
        "code": "OL_PROPOSAL_ADMINISTRATOR",
        "group_type": UserGroup.GroupType.ADMINISTRATIVE,
        "description": "Full proposal lifecycle including conversion.",
        "permission_codes": [f"ol_proposals.{action}" for action in ACTIONS],
    },
]


class Command(BaseCommand):
    help = "Seed OL Proposals permissions, permission group, and role groups idempotently."

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
            module_code="OL_PROPOSALS",
            name="OL Proposals Configuration",
            defaults={"description": "Canonical permission bundle for Ordinary Life proposals."},
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
                "OL Proposals permissions seeded: "
                f"{len(permission_map)} permissions, {created_roles} roles created, {updated_roles} roles updated."
            )
        )