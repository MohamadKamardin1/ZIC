from django.core.management.base import BaseCommand
from django.db import transaction

from apps.system_parameters.models import ParameterGroup, SystemParameter
from apps.users.models import PermissionGroup, UserGroup, UserPermission


PERMISSIONS = [
    {
        "name": "View OL Quotations",
        "codename": "ol_quotations.view",
        "module": "ol_quotations",
        "action": "VIEW",
        "resource_type": "OL_QUOTATION",
        "description": "List, search, filter, retrieve, and review Ordinary Life quotations.",
    },
    {
        "name": "Create OL Quotations",
        "codename": "ol_quotations.create",
        "module": "ol_quotations",
        "action": "CREATE",
        "resource_type": "OL_QUOTATION",
        "description": "Create Ordinary Life quotation drafts and wizard child records.",
    },
    {
        "name": "Update OL Quotations",
        "codename": "ol_quotations.update",
        "module": "ol_quotations",
        "action": "UPDATE",
        "resource_type": "OL_QUOTATION",
        "description": "Update draft quotations, wizard answers, and finalize or expire drafts.",
    },
    {
        "name": "Finalize OL Quotations",
        "codename": "ol_quotations.finalize",
        "module": "ol_quotations",
        "action": "FINALIZE",
        "resource_type": "OL_QUOTATION",
        "description": "Finalize complete quotation wizards and persist calculation and version snapshots.",
    },
    {
        "name": "Delete OL Quotations",
        "codename": "ol_quotations.delete",
        "module": "ol_quotations",
        "action": "DELETE",
        "resource_type": "OL_QUOTATION",
        "description": "Delete quotation records where policy permits deletion.",
    },
    {
        "name": "Configure OL Quotations",
        "codename": "ol_quotations.configure",
        "module": "ol_quotations",
        "action": "CONFIGURE",
        "resource_type": "OL_QUOTATION",
        "description": "Administer quotation wizard and calculation configuration integration points.",
    },
    {
        "name": "Print OL Quotations",
        "codename": "ol_quotations.print",
        "module": "ol_quotations",
        "action": "PRINT",
        "resource_type": "OL_QUOTATION",
        "description": "Print or export finalized quotation documents.",
    },
    {
        "name": "Convert OL Quotations",
        "codename": "ol_quotations.convert",
        "module": "ol_quotations",
        "action": "CONVERT",
        "resource_type": "OL_QUOTATION",
        "description": "Convert finalized quotations into future proposal or policy workflows.",
    },
]

ROLE_SEEDS = [
    {
        "name": "OL Quotation Viewer",
        "code": "OL_QUOTATION_VIEWER",
        "group_type": UserGroup.GroupType.INTERNAL,
        "description": "Read-only access to Ordinary Life quotations and wizard history.",
        "permission_codes": ["ol_quotations.view"],
    },
    {
        "name": "OL Quotation Officer",
        "code": "OL_QUOTATION_OFFICER",
        "group_type": UserGroup.GroupType.INTERNAL,
        "description": "Create and update Ordinary Life quotation drafts and complete the wizard.",
        "permission_codes": [
            "ol_quotations.view",
            "ol_quotations.create",
            "ol_quotations.update",
            "ol_quotations.finalize",
        ],
    },
    {
        "name": "OL Quotation Converter",
        "code": "OL_QUOTATION_CONVERTER",
        "group_type": UserGroup.GroupType.INTERNAL,
        "description": "Finalize and convert Ordinary Life quotations into future policy flows.",
        "permission_codes": [
            "ol_quotations.view",
            "ol_quotations.create",
            "ol_quotations.update",
            "ol_quotations.finalize",
            "ol_quotations.convert",
            "ol_quotations.print",
        ],
    },
    {
        "name": "OL Quotation Administrator",
        "code": "OL_QUOTATION_ADMINISTRATOR",
        "group_type": UserGroup.GroupType.ADMINISTRATIVE,
        "description": "Full Ordinary Life quotation lifecycle and configuration access.",
        "permission_codes": [permission["codename"] for permission in PERMISSIONS],
    },
]


class Command(BaseCommand):
    help = "Seed OL Quotation permissions, roles, and numbering configuration idempotently."

    @transaction.atomic
    def handle(self, *args, **options):
        permission_map = {}
        for payload in PERMISSIONS:
            permission, _ = UserPermission.objects.update_or_create(
                codename=payload["codename"], defaults=payload
            )
            permission_map[permission.codename] = permission

        permission_group, _ = PermissionGroup.objects.update_or_create(
            module_code="OL_QUOTATIONS",
            name="OL Quotations",
            defaults={
                "description": "Canonical permission bundle for Ordinary Life quotation workflows."
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

        system_group, _ = ParameterGroup.objects.get_or_create(
            code="SYSTEM_CONFIG",
            defaults={
                "name": "System Configuration",
                "description": "Core system configuration",
            },
        )
        SystemParameter.objects.update_or_create(
            code="OL_QUOTATION_PREFIX",
            defaults={
                "group": system_group,
                "name": "Ordinary Life Quotation Number Prefix",
                "description": "Prefix used by the canonical OL quotation numbering engine.",
                "value_type": "STRING",
                "string_value": "OLQ",
                "is_active": True,
            },
        )

        self.stdout.write(
            self.style.SUCCESS(
                "OL Quotations seeded: "
                f"{len(permission_map)} permissions, {created_roles} roles created, "
                f"{updated_roles} roles updated, numbering prefix configured."
            )
        )
