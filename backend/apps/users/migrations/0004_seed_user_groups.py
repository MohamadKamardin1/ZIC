# Generated manually for ONBOARDING.md remediation
# Seed user groups (roles) with permissions for compliance

from django.db import migrations


def seed_user_groups(apps, schema_editor):
    """Seed user groups for the 5 required compliance roles"""
    UserGroup = apps.get_model('users', 'UserGroup')
    UserPermission = apps.get_model('users', 'UserPermission')
    PermissionGroup = apps.get_model('users', 'PermissionGroup')

    # Create permission groups for better organization
    onboarding_group, _ = PermissionGroup.objects.get_or_create(
        name='Onboarding Operations',
        module_code='onboarding',
        defaults={'description': 'Permissions for partner onboarding'}
    )

    compliance_group, _ = PermissionGroup.objects.get_or_create(
        name='Compliance Operations',
        module_code='compliance',
        defaults={'description': 'Permissions for compliance activities'}
    )

    finance_group, _ = PermissionGroup.objects.get_or_create(
        name='Finance Operations',
        module_code='finance',
        defaults={'description': 'Permissions for financial operations'}
    )

    governance_group, _ = PermissionGroup.objects.get_or_create(
        name='Governance Operations',
        module_code='governance',
        defaults={'description': 'Permissions for governance activities'}
    )

    # Create the 5 required user groups (roles)
    # Note: Using existing GroupName choices or None for custom groups
    roles_data = [
        {
            'name': 'System Administrator',
            'description': 'Full system access and configuration',
            'permissions': ['system_parameters', 'users', 'partner_config', 'governance', 'audit', 'reports'],
        },
        {
            'name': 'Onboarding Clerk',
            'description': 'Can create and manage partner applications',
            'permissions': ['partner_onboarding'],
        },
        {
            'name': 'Compliance Officer',
            'description': 'Can review, approve, and perform compliance checks',
            'permissions': ['partner_onboarding', 'partners', 'governance'],
        },
        {
            'name': 'Finance Manager',
            'description': 'Can manage financial profiles and approve applications',
            'permissions': ['finance', 'partner_onboarding', 'partners', 'reports'],
        },
        {
            'name': 'ZIC Auditor',
            'description': 'Read-only access to audit and governance data',
            'permissions': ['audit', 'governance', 'reports', 'partner_onboarding', 'partners'],
        },
    ]

    for role_data in roles_data:
        # Find or create group (some may already exist)
        try:
            group = UserGroup.objects.get(name=role_data['name'])
        except UserGroup.DoesNotExist:
            # Create with first available choice or None
            group = UserGroup.objects.create(
                name=role_data['name'],
                description=role_data['description']
            )

        # Assign permissions to the group
        for module in role_data['permissions']:
            perms = UserPermission.objects.filter(module=module)
            if perms.exists():
                for perm in perms:
                    group.permissions.add(perm)

    # Assign permissions to permission groups
    onboarding_perms = UserPermission.objects.filter(module='partner_onboarding')
    for perm in onboarding_perms:
        onboarding_group.permissions.add(perm)

    compliance_perms = UserPermission.objects.filter(module__in=['partner_onboarding', 'partners', 'governance'])
    for perm in compliance_perms:
        compliance_group.permissions.add(perm)

    finance_perms = UserPermission.objects.filter(module__in=['finance', 'partner_onboarding', 'partners', 'reports'])
    for perm in finance_perms:
        finance_group.permissions.add(perm)

    governance_perms = UserPermission.objects.filter(module__in=['governance', 'audit', 'reports'])
    for perm in governance_perms:
        governance_group.permissions.add(perm)


def reverse_seed_user_groups(apps, schema_editor):
    """Reverse: remove seeded user groups and permission groups"""
    UserGroup = apps.get_model('users', 'UserGroup')
    PermissionGroup = apps.get_model('users', 'PermissionGroup')

    UserGroup.objects.filter(name__in=[
        'System Administrator',
        'Onboarding Clerk',
        'Compliance Officer',
        'Finance Manager',
        'ZIC Auditor',
    ]).delete()

    PermissionGroup.objects.filter(module_code__in=[
        'onboarding',
        'compliance',
        'finance',
        'governance',
    ]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('users', '0003_seed_rbac_permissions'),
    ]

    operations = [
        migrations.RunPython(seed_user_groups, reverse_seed_user_groups),
    ]
