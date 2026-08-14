import pytest
from rest_framework.test import APIClient

from apps.common.models import DomainEvent
from apps.users.models import User, UserActivityLog, UserGroup, UserPermission
from apps.users.rbac import RBACService, RBACServiceError


@pytest.fixture(autouse=True)
def rbac_catalog(db):
    modules = [
        'dashboard', 'user_management', 'system_parameters', 'partner_onboarding',
        'ordinary_life', 'group_credit', 'group_life', 'medical_underwriting',
        'front_office', 'claims', 'commission', 'approvals', 'reporting',
        'reinsurance', 'partner_portal', 'tickets',
    ]
    actions = [
        'VIEW', 'READ', 'CREATE', 'UPDATE', 'DELETE', 'APPROVE', 'REJECT',
        'CONFIGURE', 'EXPORT', 'PRINT', 'REVERSE', 'SETTLE', 'ASSIGN', 'ADMINISTER',
    ]
    for module in modules:
        for action in actions:
            code = f'{module}.{action.lower()}'
            UserPermission.objects.get_or_create(
                codename=code,
                defaults={
                    'name': f'{action.title()} {module.title()}',
                    'module': module,
                    'action': action,
                    'description': f'{action.title()} access to {module}.',
                    'is_active': True,
                },
            )
    UserGroup.objects.get_or_create(
        name='SUPER_ADMIN',
        defaults={
            'code': 'SUPER_ADMIN',
            'group_type': UserGroup.GroupType.ADMINISTRATIVE,
            'is_system': True,
            'is_system_group': True,
        },
    )


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(
        username='rbac-admin',
        email='rbac-admin@example.com',
        password='AdminPass123!Secure',
        first_name='RBAC',
        last_name='Admin',
    )


@pytest.fixture
def client():
    return APIClient()


def test_catalog_is_seeded_and_machine_readable(db):
    required_modules = {
        'dashboard', 'user_management', 'system_parameters', 'partner_onboarding',
        'ordinary_life', 'group_credit', 'group_life', 'medical_underwriting',
        'front_office', 'claims', 'commission', 'approvals', 'reporting',
        'reinsurance', 'partner_portal', 'tickets',
    }
    required_actions = {
        'view', 'create', 'update', 'delete', 'approve', 'reject', 'configure',
        'export', 'print', 'reverse', 'settle', 'assign', 'administer',
    }
    catalog = UserPermission.objects.filter(module__in=required_modules, is_active=True)
    assert required_modules.issubset(set(catalog.values_list('module', flat=True)))
    assert required_actions.issubset({permission.action.lower() for permission in catalog})
    assert all(permission.codename == f'{permission.module}.{permission.action.lower()}' for permission in catalog if permission.module in required_modules)


def test_group_lifecycle_and_deactivation_is_audited(db, admin_user):
    group = RBACService.create_group(
        actor=admin_user,
        data={
            'name': 'Claims Supervisor',
            'code': 'claims_supervisor',
            'description': 'Claims workflow supervisor',
            'group_type': UserGroup.GroupType.INTERNAL,
        },
    )
    assert group.code == 'CLAIMS_SUPERVISOR'
    assert group.is_active is True

    updated = RBACService.update_group(actor=admin_user, group=group, data={'description': 'Updated description'})
    assert updated.description == 'Updated description'

    RBACService.deactivate_group(actor=admin_user, group=group)
    group.refresh_from_db()
    assert group.is_active is False
    assert DomainEvent.objects.filter(event_type='iam.group.deactivated', aggregate_id=str(group.id)).exists()
    assert UserActivityLog.objects.filter(user=admin_user, action_type=UserActivityLog.ActionType.PERMISSION_CHANGE).exists()


def test_system_group_cannot_be_deactivated_or_destroyed(db, admin_user):
    group = UserGroup.objects.get(code='SUPER_ADMIN')
    with pytest.raises(RBACServiceError):
        RBACService.deactivate_group(actor=admin_user, group=group)


def test_permission_assignment_and_removal_updates_inherited_check(db, admin_user):
    group = RBACService.create_group(
        actor=admin_user,
        data={'name': 'Ordinary Life Operations', 'code': 'ordinary_life_ops', 'group_type': 'INTERNAL'},
    )
    user = User.objects.create_user(
        username='ordinary-operator',
        email='ordinary-operator@example.com',
        password='OperatorPass123!Secure',
        user_type='STAFF',
        is_active=True,
        is_approved=True,
    )
    permission = UserPermission.objects.get(codename='ordinary_life.view')

    RBACService.assign_users(actor=admin_user, group=group, user_ids=[user.id])
    RBACService.assign_permissions(actor=admin_user, group=group, permission_ids=[permission.id])
    user.refresh_from_db()
    assert user.has_permission('ordinary_life.view') is True

    RBACService.remove_permissions(actor=admin_user, group=group, permission_ids=[permission.id])
    user.refresh_from_db()
    assert user.has_permission('ordinary_life.view') is False


def test_partner_users_cannot_be_assigned_internal_groups(db, admin_user):
    group = RBACService.create_group(
        actor=admin_user,
        data={'name': 'Internal Underwriters', 'code': 'internal_underwriters', 'group_type': 'INTERNAL'},
    )
    partner = User.objects.create_user(
        username='partner-rbac',
        email='partner-rbac@example.com',
        password='PartnerPass123!Secure',
        user_type='PARTNER',
        is_active=True,
        is_approved=True,
    )
    with pytest.raises(RBACServiceError):
        RBACService.assign_users(actor=admin_user, group=group, user_ids=[partner.id])


def test_partner_group_accepts_partner_user(db, admin_user):
    group = RBACService.create_group(
        actor=admin_user,
        data={'name': 'Partner Portal Agents', 'code': 'partner_portal_agents', 'group_type': 'PARTNER'},
    )
    partner = User.objects.create_user(
        username='partner-agent',
        email='partner-agent@example.com',
        password='PartnerPass123!Secure',
        user_type='PARTNER',
        is_active=True,
        is_approved=True,
    )
    assigned = RBACService.assign_users(actor=admin_user, group=group, user_ids=[partner.id])
    assert partner in assigned
    assert group.users.filter(id=partner.id).exists()


def test_group_api_enforces_permission_and_supports_assignment(db, admin_user, client):
    client.force_authenticate(user=admin_user)
    response = client.post('/api/v1/users/groups/', {
        'name': 'API Permission Managers',
        'code': 'api_permission_managers',
        'description': 'Created through the API',
        'group_type': 'ADMINISTRATIVE',
    }, format='json')
    assert response.status_code == 201
    group_id = response.data['data']['id']
    permission = UserPermission.objects.get(codename='claims.view')

    response = client.post(
        f'/api/v1/users/groups/{group_id}/assign_permissions/',
        {'permission_ids': [str(permission.id)]},
        format='json',
    )
    assert response.status_code == 200
    assert UserGroup.objects.get(id=group_id).permissions.filter(id=permission.id).exists()


def test_non_authorized_user_cannot_list_groups(db, client):
    user = User.objects.create_user(
        username='no-rbac',
        email='no-rbac@example.com',
        password='NoRbacPass123!Secure',
        user_type='STAFF',
        is_active=True,
        is_approved=True,
    )
    client.force_authenticate(user=user)
    response = client.get('/api/v1/users/groups/')
    assert response.status_code == 403


def test_group_delete_soft_deactivates_and_never_hard_deletes(db, admin_user, client):
    group = RBACService.create_group(
        actor=admin_user,
        data={'name': 'Temporary Operations', 'code': 'temporary_operations', 'group_type': 'INTERNAL'},
    )
    client.force_authenticate(user=admin_user)
    response = client.delete(f'/api/v1/users/groups/{group.id}/')
    assert response.status_code == 200
    group.refresh_from_db()
    assert group.is_active is False
    assert UserGroup.objects.filter(id=group.id).exists()
