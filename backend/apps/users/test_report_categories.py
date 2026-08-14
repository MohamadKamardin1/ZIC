import pytest
from rest_framework.test import APIClient

from apps.common.models import DomainEvent
from apps.users.models import ReportCategory, User, UserGroup, UserPermission
from apps.users.rbac import RBACService


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(
        username='reports-admin',
        email='reports-admin@example.com',
        password='ReportsAdminPass123!Secure',
        first_name='Reports',
        last_name='Admin',
    )


@pytest.fixture
def report_categories(db):
    categories = {}
    values = [
        ('ordinary_life', 'Ordinary Life', 'ordinary_life'),
        ('claims', 'Claims', 'claims'),
        ('finance', 'Finance', 'finance'),
    ]
    for code, name, business_area in values:
        categories[code], _ = ReportCategory.objects.update_or_create(
            code=code,
            defaults={
                'name': name,
                'description': f'{name} reports',
                'business_area': business_area,
                'is_active': True,
                'is_system': True,
            },
        )
    return categories


def make_internal_user(username='report-user'):
    return User.objects.create_user(
        username=username,
        email=f'{username}@example.com',
        password='ReportUserPass123!Secure',
        user_type='STAFF',
        is_active=True,
        is_approved=True,
    )


def make_group(admin_user):
    return RBACService.create_group(
        actor=admin_user,
        data={
            'name': 'Claims Report Viewers',
            'code': 'claims_report_viewers',
            'group_type': UserGroup.GroupType.INTERNAL,
        },
    )


def test_report_category_creation_is_independent_from_permissions(db):
    category = ReportCategory.objects.create(
        code='underwriting',
        name='Underwriting',
        description='Underwriting reports',
        business_area='underwriting',
        is_active=True,
        is_system=False,
    )
    assert category.code == 'underwriting'
    assert not UserPermission.objects.filter(codename='underwriting.view').exists()


def test_group_assignment_controls_current_user_visibility(db, admin_user, report_categories):
    group = make_group(admin_user)
    user = make_internal_user()

    RBACService.assign_users(actor=admin_user, group=group, user_ids=[user.id])
    assert user.visible_report_categories().count() == 0
    assert user.can_view_report_category('claims') is False

    RBACService.assign_report_categories(
        actor=admin_user,
        group=group,
        category_ids=[report_categories['claims'].id],
    )
    user.refresh_from_db()
    assert list(user.visible_report_categories().values_list('code', flat=True)) == ['claims']
    assert user.can_view_report_category('CLAIMS') is True
    assert DomainEvent.objects.filter(
        event_type='iam.group.report_categories_assigned',
        aggregate_id=str(group.id),
    ).exists()

    RBACService.remove_report_categories(
        actor=admin_user,
        group=group,
        category_ids=[report_categories['claims'].id],
    )
    user.refresh_from_db()
    assert user.can_view_report_category('claims') is False
    assert DomainEvent.objects.filter(
        event_type='iam.group.report_categories_removed',
        aggregate_id=str(group.id),
    ).exists()


def test_user_without_category_cannot_see_it(db, admin_user, report_categories):
    group = make_group(admin_user)
    user = make_internal_user('without-category')
    RBACService.assign_users(actor=admin_user, group=group, user_ids=[user.id])
    assert user.can_view_report_category('finance') is False
    assert list(user.visible_report_categories()) == []


def test_report_visibility_is_separate_from_module_permissions(db, admin_user, report_categories):
    group = make_group(admin_user)
    user = make_internal_user('separation-user')
    permission = UserPermission.objects.create(
        name='Claims view',
        codename='claims.view',
        module='claims',
        action='VIEW',
        description='Access claims processes',
        is_active=True,
    )
    RBACService.assign_users(actor=admin_user, group=group, user_ids=[user.id])
    RBACService.assign_permissions(actor=admin_user, group=group, permission_ids=[permission.id])
    user.refresh_from_db()

    assert user.has_permission('claims.view') is True
    assert user.can_view_report_category('claims') is False

    RBACService.assign_report_categories(
        actor=admin_user,
        group=group,
        category_ids=[report_categories['claims'].id],
    )
    user.refresh_from_db()
    assert user.can_view_report_category('claims') is True

    RBACService.remove_permissions(actor=admin_user, group=group, permission_ids=[permission.id])
    user.refresh_from_db()
    assert user.has_permission('claims.view') is False
    assert user.can_view_report_category('claims') is True


def test_report_category_api_and_current_user_payload(db, admin_user, report_categories, client):
    group = make_group(admin_user)
    user = make_internal_user('api-report-user')
    RBACService.assign_users(actor=admin_user, group=group, user_ids=[user.id])
    RBACService.assign_report_categories(
        actor=admin_user,
        group=group,
        category_ids=[report_categories['ordinary_life'].id],
    )

    client.force_authenticate(user=admin_user)
    response = client.get('/api/v1/users/report-categories/')
    assert response.status_code == 200
    assert response.data['success'] is True
    assert any(item['code'] == 'ordinary_life' for item in response.data['data'])

    client.force_authenticate(user=user)
    response = client.get('/api/v1/users/users/visible-report-categories/')
    assert response.status_code == 200
    assert [item['code'] for item in response.data['data']] == ['ordinary_life']

    response = client.get('/api/v1/auth/me/')
    assert response.status_code == 200
    assert [item['code'] for item in response.data['data']['user']['visible_report_categories']] == ['ordinary_life']
