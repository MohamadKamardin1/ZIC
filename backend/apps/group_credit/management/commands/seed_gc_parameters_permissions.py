from django.core.management.base import BaseCommand
from django.db import transaction

from apps.users.models import PermissionGroup, UserGroup, UserPermission

MODULE = "gc_parameters"

PERMISSIONS = [
    {
        "name": "View GC Parameters",
        "codename": "gc_parameters.view",
        "module": MODULE,
        "action": "VIEW",
        "resource_type": "GC_PARAMETER",
        "description": "View, list, retrieve, search, filter, and export GC parameter catalogs.",
    },
    {
        "name": "Manage GC Parameters",
        "codename": "gc_parameters.manage",
        "module": MODULE,
        "action": "MANAGE",
        "resource_type": "GC_PARAMETER",
        "description": "Create and update GC parameter configuration records.",
    },
    {
        "name": "Configure GC Parameters",
        "codename": "gc_parameters.configure",
        "module": MODULE,
        "action": "CONFIGURE",
        "resource_type": "GC_PARAMETER",
        "description": "Configure and administer GC parameter catalogs, lifecycle, and registry metadata.",
    },
]

ENTITY_CODES = [
    "scheme_types",
    "scheme_rates",
    "member_statuses",
    "scheme_statuses",
    "renewal_statuses",
    "health_questions",
    "health_questionnaires",
    "sub_products",
    "products",
    "riders",
    "rider_rates",
    "medical_codes",
    "medical_limits",
    "underwriting_decisions",
    "personal_habits",
    "medical_histories",
    "medical_facilities",
    "medical_practitioners",
    "claim_types",
    "claim_reasons",
    "claim_statuses",
    "discharge_types",
    "correspondent_types",
]

ENTITY_ACTIONS = ["view", "create", "update", "deactivate"]

ENTITY_LABELS = {
    "scheme_types": "Scheme Types",
    "scheme_rates": "Scheme Premium Rates",
    "member_statuses": "Scheme Member Statuses",
    "scheme_statuses": "Scheme Statuses",
    "renewal_statuses": "Scheme Renewal Statuses",
    "health_questions": "Health Questions",
    "health_questionnaires": "Health Questionnaires",
    "sub_products": "Sub Products",
    "products": "Products",
    "riders": "Riders",
    "rider_rates": "Rider Rates",
    "medical_codes": "Medical Codes",
    "medical_limits": "Medical Limits",
    "underwriting_decisions": "Underwriting Decisions",
    "personal_habits": "Personal Habits",
    "medical_histories": "Medical Histories",
    "medical_facilities": "Medical Facilities",
    "medical_practitioners": "Medical Practitioners",
    "claim_types": "Claim Types",
    "claim_reasons": "Claim Reasons",
    "claim_statuses": "Claim Statuses",
    "discharge_types": "Discharge Types",
    "correspondent_types": "Correspondent Types",
}

ENTITY_ACTION_LABELS = {
    "view": "View",
    "create": "Create",
    "update": "Update",
    "deactivate": "Deactivate",
}


def _build_permissions():
    payloads = list(PERMISSIONS)
    for entity in ENTITY_CODES:
        for action in ENTITY_ACTIONS:
            payloads.append(
                {
                    "name": f"{ENTITY_ACTION_LABELS[action]} {ENTITY_LABELS[entity]}",
                    "codename": f"{MODULE}.{entity}.{action}",
                    "module": MODULE,
                    "action": action.upper(),
                    "resource_type": f"GC_{entity.upper()}",
                    "description": (
                        f"{ENTITY_ACTION_LABELS[action]} access to Group Credit {ENTITY_LABELS[entity]}."
                    ),
                }
            )
    return payloads


ROLE_SEEDS = [
    {
        "name": "GC Parameter Viewer",
        "code": "GC_PARAMETER_VIEWER",
        "group_type": UserGroup.GroupType.INTERNAL,
        "description": "Read-only access to all Group Credit parameter catalogs.",
        "permission_codes": ["gc_parameters.view"],
    },
    {
        "name": "GC Parameter Manager",
        "code": "GC_PARAMETER_MANAGER",
        "group_type": UserGroup.GroupType.INTERNAL,
        "description": "Create and update Group Credit parameter catalogs without lifecycle deactivation.",
        "permission_codes": [
            "gc_parameters.view",
            "gc_parameters.manage",
            *[f"{MODULE}.{entity}.view" for entity in ENTITY_CODES],
            *[f"{MODULE}.{entity}.create" for entity in ENTITY_CODES],
            *[f"{MODULE}.{entity}.update" for entity in ENTITY_CODES],
        ],
    },
    {
        "name": "GC Parameter Administrator",
        "code": "GC_PARAMETER_ADMINISTRATOR",
        "group_type": UserGroup.GroupType.ADMINISTRATIVE,
        "description": "Full lifecycle and registry administration for Group Credit parameters.",
        "permission_codes": [
            "gc_parameters.view",
            "gc_parameters.manage",
            "gc_parameters.configure",
            *[
                f"{MODULE}.{entity}.{action}"
                for entity in ENTITY_CODES
                for action in ENTITY_ACTIONS
            ],
        ],
    },
]


class Command(BaseCommand):
    help = "Seed GC Parameters permissions, permission group, and role groups idempotently."

    @transaction.atomic
    def handle(self, *args, **options):
        permission_map = {}
        for payload in _build_permissions():
            permission, _ = UserPermission.objects.update_or_create(
                codename=payload["codename"],
                defaults=payload,
            )
            permission_map[permission.codename] = permission

        permission_group, _ = PermissionGroup.objects.update_or_create(
            module_code="GC_PARAMETERS",
            name="GC Parameters Configuration",
            defaults={
                "description": "Canonical permission bundle for Group Credit parameter configuration.",
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
                "GC Parameters permissions seeded: "
                f"{len(permission_map)} permissions, {created_roles} roles created, "
                f"{updated_roles} roles updated."
            )
        )
