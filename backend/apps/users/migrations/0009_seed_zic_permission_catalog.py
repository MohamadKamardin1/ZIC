from django.db import migrations


MODULES = [
    'dashboard',
    'user_management',
    'system_parameters',
    'partner_onboarding',
    'ordinary_life',
    'group_credit',
    'group_life',
    'medical_underwriting',
    'front_office',
    'claims',
    'commission',
    'approvals',
    'reporting',
    'reinsurance',
    'partner_portal',
    'tickets',
    'audit',
]
ACTIONS = [
    ('VIEW', 'View'),
    ('READ', 'Read'),
    ('CREATE', 'Create'),
    ('UPDATE', 'Update'),
    ('DELETE', 'Delete'),
    ('APPROVE', 'Approve'),
    ('REJECT', 'Reject'),
    ('CONFIGURE', 'Configure'),
    ('EXPORT', 'Export'),
    ('PRINT', 'Print'),
    ('REVERSE', 'Reverse'),
    ('SETTLE', 'Settle'),
    ('ASSIGN', 'Assign'),
    ('ADMINISTER', 'Administer'),
]


def seed_catalog(apps, schema_editor):
    UserPermission = apps.get_model('users', 'UserPermission')
    UserGroup = apps.get_model('users', 'UserGroup')

    permissions_by_module = {}
    for module in MODULES:
        permissions_by_module[module] = []
        for action, label in ACTIONS:
            code = f'{module}.{action.lower()}'
            permission, _ = UserPermission.objects.get_or_create(
                module=module,
                action=action,
                resource_type='',
                defaults={
                    'name': f'{label} {module.replace("_", " ").title()}',
                    'codename': code,
                    'description': f'{label} access to the {module.replace("_", " ")} domain.',
                    'is_active': True,
                },
            )
            changed = []
            if permission.codename != code:
                permission.codename = code
                changed.append('codename')
            if not permission.description:
                permission.description = f'{label} access to the {module.replace("_", " ")} domain.'
                changed.append('description')
            if not permission.is_active:
                permission.is_active = True
                changed.append('is_active')
            if changed:
                permission.save(update_fields=changed + ['updated_at'])
            permissions_by_module[module].append(permission)

    group_types = {
        'PORTAL_USER': 'PARTNER',
        'QUOTATION_ONLY': 'PARTNER',
        'SUPER_ADMIN': 'ADMINISTRATIVE',
        'ZIC_GROUP': 'ADMINISTRATIVE',
        'SYSTEM_MANAGER': 'ADMINISTRATIVE',
        'MANAGER': 'INTERNAL',
        'UNDERWRITER': 'INTERNAL',
    }
    for name, group_type in group_types.items():
        group = UserGroup.objects.filter(name=name).first()
        if group is None:
            continue
        group.group_type = group_type
        group.is_system = True
        group.is_system_group = True
        group.code = group.code or name
        group.save(update_fields=['group_type', 'is_system', 'is_system_group', 'code', 'updated_at'])

    audit_group, _ = UserGroup.objects.get_or_create(
        code='ZIC_AUDIT',
        defaults={
            'name': 'ZIC Audit',
            'description': 'Read-only audit and reporting access.',
            'group_type': 'AUDIT',
            'is_system': True,
            'is_system_group': True,
        },
    )
    audit_group.group_type = 'AUDIT'
    audit_group.is_system = True
    audit_group.is_system_group = True
    audit_group.is_active = True
    audit_group.save(update_fields=['group_type', 'is_system', 'is_system_group', 'is_active', 'updated_at'])
    audit_permissions = []
    for module in ('audit', 'reporting'):
        audit_permissions.extend(permissions_by_module.get(module, []))
    if audit_permissions:
        audit_group.permissions.add(*audit_permissions)


def reverse_catalog(apps, schema_editor):
    UserPermission = apps.get_model('users', 'UserPermission')
    UserGroup = apps.get_model('users', 'UserGroup')
    UserPermission.objects.filter(module__in=MODULES).delete()
    UserGroup.objects.filter(code='ZIC_AUDIT').delete()


class Migration(migrations.Migration):
    dependencies = [
        ('users', '0008_alter_userpermission_options_and_more'),
    ]

    operations = [
        migrations.RunPython(seed_catalog, reverse_catalog),
    ]
