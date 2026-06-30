# Generated manually for ONBOARDING.md remediation
# Seed all RBAC permissions (CORRECTED for actual model fields)

from django.db import migrations


def seed_rbac_permissions(apps, schema_editor):
    """Seed all RBAC permissions for dynamic access control"""
    UserPermission = apps.get_model('users', 'UserPermission')

    permissions = [
        # System Parameters
        ('system_parameters', 'READ', 'View System Parameters', 'view_system_parameters'),
        ('system_parameters', 'CREATE', 'Create System Parameters', 'create_system_parameters'),
        ('system_parameters', 'UPDATE', 'Update System Parameters', 'update_system_parameters'),
        ('system_parameters', 'DELETE', 'Delete System Parameters', 'delete_system_parameters'),
        ('system_parameters', 'MANAGE', 'Full Management of System Parameters', 'manage_system_parameters'),

        # User Management
        ('users', 'READ', 'View Users', 'view_users'),
        ('users', 'CREATE', 'Create Users', 'create_users'),
        ('users', 'UPDATE', 'Update Users', 'update_users'),
        ('users', 'DELETE', 'Delete Users', 'delete_users'),
        ('users', 'MANAGE', 'Full Management of Users', 'manage_users'),

        # Partner Onboarding
        ('partner_onboarding', 'READ', 'View Applications', 'view_applications'),
        ('partner_onboarding', 'CREATE', 'Create Applications', 'create_applications'),
        ('partner_onboarding', 'UPDATE', 'Update Applications', 'update_applications'),
        ('partner_onboarding', 'DELETE', 'Delete Applications', 'delete_applications'),
        ('partner_onboarding', 'REVIEW', 'Review Submitted Applications', 'review_applications'),
        ('partner_onboarding', 'APPROVE', 'Approve/Reject Applications', 'approve_applications'),
        ('partner_onboarding', 'COMPLIANCE', 'Perform Compliance Checks', 'compliance_checks'),
        ('partner_onboarding', 'CONVERT', 'Convert Applications to Partners', 'convert_applications'),
        ('partner_onboarding', 'BULK_IMPORT', 'Bulk Import Applications', 'bulk_import_applications'),

        # Partner Management
        ('partners', 'READ', 'View Partners', 'view_partners'),
        ('partners', 'CREATE', 'Create Partners', 'create_partners'),
        ('partners', 'UPDATE', 'Update Partners', 'update_partners'),
        ('partners', 'DELETE', 'Delete Partners', 'delete_partners'),
        ('partners', 'SUSPEND', 'Suspend Partners', 'suspend_partners'),
        ('partners', 'MANAGE', 'Full Management of Partners', 'manage_partners'),

        # Partner Configuration
        ('partner_config', 'READ', 'View Partner Configuration', 'view_partner_config'),
        ('partner_config', 'CREATE', 'Create Partner Configuration', 'create_partner_config'),
        ('partner_config', 'UPDATE', 'Update Partner Configuration', 'update_partner_config'),
        ('partner_config', 'DELETE', 'Delete Partner Configuration', 'delete_partner_config'),
        ('partner_config', 'MANAGE', 'Full Management of Partner Configuration', 'manage_partner_config'),

        # Governance
        ('governance', 'READ', 'View Approvals', 'view_approvals'),
        ('governance', 'APPROVE', 'Approve/Reject Requests', 'approve_requests'),
        ('governance', 'MANAGE', 'Full Management of Governance', 'manage_governance'),

        # Finance
        ('finance', 'READ', 'View Financial Profiles', 'view_financial_profiles'),
        ('finance', 'UPDATE', 'Update Financial Profiles', 'update_financial_profiles'),
        ('finance', 'ASSESS', 'Assess Financial Suitability', 'assess_financial_suitability'),
        ('finance', 'MANAGE', 'Full Management of Finance', 'manage_finance'),

        # Reports
        ('reports', 'READ', 'View Reports', 'view_reports'),
        ('reports', 'EXPORT', 'Export Reports', 'export_reports'),

        # Audit
        ('audit', 'READ', 'View Audit Logs', 'view_audit_logs'),
        ('audit', 'EXPORT', 'Export Audit Logs', 'export_audit_logs'),
    ]

    for module, action, name, codename in permissions:
        UserPermission.objects.get_or_create(
            module=module,
            action=action,
            defaults={
                'name': name,
                'codename': codename,
            }
        )


def reverse_seed_rbac_permissions(apps, schema_editor):
    """Reverse: remove all seeded permissions"""
    UserPermission = apps.get_model('users', 'UserPermission')
    UserPermission.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ('users', '0002_notificationpreference_user_avatar_and_more'),
    ]

    operations = [
        migrations.RunPython(seed_rbac_permissions, reverse_seed_rbac_permissions),
    ]
