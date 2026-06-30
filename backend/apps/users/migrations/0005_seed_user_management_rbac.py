from django.db import migrations

def rename_and_seed_rbac(apps, schema_editor):
    User = apps.get_model('users', 'User')
    UserGroup = apps.get_model('users', 'UserGroup')
    UserPermission = apps.get_model('users', 'UserPermission')

    # 1. Rename existing 'AIMS_GROUP' in User.user_type and UserGroup.name
    # Since model choices changed to ZIC_GROUP, we must migrate existing data
    User.objects.filter(user_type='AIMS_GROUP').update(user_type='ZIC_GROUP')
    
    aims_group = UserGroup.objects.filter(name='AIMS_GROUP').first()
    if aims_group:
        aims_group.name = 'ZIC_GROUP'
        aims_group.save()

    # 2. Clear old compliance groups that were seeded in 0004
    old_roles = [
        'System Administrator',
        'Onboarding Clerk',
        'Compliance Officer',
        'Finance Manager',
        'ZIC Auditor'
    ]
    UserGroup.objects.filter(name__in=old_roles).delete()

    # 3. Create or update the 7 standard user groups
    groups_config = {
        'SUPER_ADMIN': {
            'description': 'Super Administrator - Full access to all modules and configurations',
            'modules': ['system_parameters', 'users', 'partner_onboarding', 'partners', 'partner_config', 'governance', 'finance', 'reports', 'audit']
        },
        'ZIC_GROUP': {
            'description': 'ZIC Groups - Senior administrators and executives with platform-wide visibility and action authority',
            'modules': ['system_parameters', 'users', 'partner_onboarding', 'partners', 'partner_config', 'governance', 'finance', 'reports', 'audit']
        },
        'SYSTEM_MANAGER': {
            'description': 'System Managers - Focuses on platform management, parameter adjustments, and user controls',
            'modules': ['system_parameters', 'users', 'partner_config', 'reports', 'audit']
        },
        'MANAGER': {
            'description': 'Managers - Operations managers with permissions to review, approve, and manage partner listings',
            'modules': ['partner_onboarding', 'partners', 'governance', 'finance', 'reports']
        },
        'UNDERWRITER': {
            'description': 'Underwriters - Evaluates applications, conducts risk assessments, and runs compliance checks',
            'modules': ['partner_onboarding', 'partners', 'finance', 'reports']
        },
        'QUOTATION_ONLY': {
            'description': 'Quotations Only - Restrictive role focused on creating and editing initial quotation drafts',
            'modules': ['partner_onboarding']
        },
        'PORTAL_USER': {
            'description': 'Portal Users - External partners and agents, restricted to their own submitted drafts',
            'modules': ['partner_onboarding']
        }
    }

    all_permissions = list(UserPermission.objects.all())

    for name, config in groups_config.items():
        group, created = UserGroup.objects.get_or_create(
            name=name,
            defaults={'description': config['description'], 'is_system_group': True}
        )
        if not created:
            group.description = config['description']
            group.is_system_group = True
            group.save()

        # Clear existing permissions to seed fresh ones
        group.permissions.clear()

        # Gather relevant permissions
        if name in ['SUPER_ADMIN', 'ZIC_GROUP']:
            group.permissions.add(*all_permissions)
        else:
            # Map modules to specific action rules for fine-grained access control
            for perm in all_permissions:
                if perm.module not in config['modules']:
                    continue

                # Granular scoping rules
                if name == 'SYSTEM_MANAGER':
                    # Full control of parameters, users, config, read/export audit & reports
                    if perm.module in ['system_parameters', 'users', 'partner_config']:
                        group.permissions.add(perm)
                    elif perm.module in ['reports', 'audit'] and perm.action in ['READ', 'EXPORT']:
                        group.permissions.add(perm)

                elif name == 'MANAGER':
                    # Manage onboarding and partners, perform approvals
                    if perm.module in ['partner_onboarding', 'partners', 'governance', 'finance']:
                        group.permissions.add(perm)
                    elif perm.module == 'reports' and perm.action in ['READ', 'EXPORT']:
                        group.permissions.add(perm)

                elif name == 'UNDERWRITER':
                    # Only read/update partners, review/check compliance, assess finance, read reports
                    if perm.module == 'partner_onboarding' and perm.action in ['READ', 'UPDATE', 'REVIEW', 'COMPLIANCE']:
                        group.permissions.add(perm)
                    elif perm.module == 'partners' and perm.action in ['READ', 'UPDATE']:
                        group.permissions.add(perm)
                    elif perm.module == 'finance' and perm.action in ['READ', 'UPDATE', 'ASSESS']:
                        group.permissions.add(perm)
                    elif perm.module == 'reports' and perm.action == 'READ':
                        group.permissions.add(perm)

                elif name in ['QUOTATION_ONLY', 'PORTAL_USER']:
                    # Restricted to creating/reading/updating applications
                    if perm.module == 'partner_onboarding' and perm.action in ['READ', 'CREATE', 'UPDATE']:
                        group.permissions.add(perm)

def reverse_seed_rbac(apps, schema_editor):
    UserGroup = apps.get_model('users', 'UserGroup')
    User = apps.get_model('users', 'User')

    # Delete the seeded groups
    group_names = ['SUPER_ADMIN', 'ZIC_GROUP', 'SYSTEM_MANAGER', 'MANAGER', 'UNDERWRITER', 'QUOTATION_ONLY', 'PORTAL_USER']
    UserGroup.objects.filter(name__in=group_names).delete()

    # Revert user type field renaming
    User.objects.filter(user_type='ZIC_GROUP').update(user_type='AIMS_GROUP')

class Migration(migrations.Migration):
    dependencies = [
        ('users', '0004_seed_user_groups'),
    ]

    operations = [
        migrations.RunPython(rename_and_seed_rbac, reverse_seed_rbac),
    ]
