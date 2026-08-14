import pyotp
import pytest
from apps.users.models import TwoFactorAuth, User, UserActivityLog, UserOTP, UserPasswordHistory
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def approved_user(db):
    return User.objects.create_user(
        username='iam-user',
        email='iam@example.com',
        password='StrongPass!123',
        first_name='IAM',
        last_name='User',
        user_type='PARTNER',
        partner_id='11111111-1111-1111-1111-111111111111',
        is_approved=True,
        status=User.AccountStatus.ACTIVE,
    )


def auth_url(name):
    return f'/api/v1/auth/{name}/'


def test_staff_and_partner_identity_fields(db):
    staff = User.objects.create_user(
        username='staff-iam', email='staff-iam@example.com', password='StrongPass!123',
        user_type='STAFF', is_staff=True, is_approved=True, mfa_required=True,
        sso_provider='OIDC', sso_subject='staff-subject',
    )
    partner = User.objects.create_user(
        username='partner-iam', email='partner-iam@example.com', password='StrongPass!123',
        user_type='PARTNER', partner_id='22222222-2222-2222-2222-222222222222', is_approved=True,
    )
    assert staff.user_type == 'STAFF'
    assert staff.mfa_required is True
    assert staff.sso_provider == 'OIDC'
    assert partner.user_type == 'PARTNER'
    assert str(partner.partner_id) == '22222222-2222-2222-2222-222222222222'


def test_login_success_returns_tokens_and_session(api_client, approved_user):
    response = api_client.post(auth_url('login'), {
        'username': approved_user.username,
        'password': 'StrongPass!123',
    }, format='json')
    assert response.status_code == 200
    assert response.data['success'] is True
    assert response.data['data']['access_token']
    assert response.data['data']['refresh_token']
    assert response.data['data']['user']['status'] == User.AccountStatus.ACTIVE
    assert approved_user.sessions.filter(is_active=True).exists()
    assert approved_user.activity_logs.filter(action_type=UserActivityLog.ActionType.LOGIN).exists()


def test_login_failure_and_lockout(api_client, approved_user, settings):
    settings.LOGIN_MAX_FAILED_ATTEMPTS = 5
    for _ in range(4):
        response = api_client.post(auth_url('login'), {
            'username': approved_user.username, 'password': 'WrongPass!123',
        }, format='json')
        assert response.status_code == 400
    response = api_client.post(auth_url('login'), {
        'username': approved_user.username, 'password': 'WrongPass!123',
    }, format='json')
    assert response.status_code == 400
    approved_user.refresh_from_db()
    assert approved_user.status == User.AccountStatus.LOCKED
    assert approved_user.failed_login_attempts == 5
    response = api_client.post(auth_url('login'), {
        'username': approved_user.username, 'password': 'StrongPass!123',
    }, format='json')
    assert response.status_code == 400


def test_password_change_enforces_history(api_client, approved_user):
    api_client.force_authenticate(approved_user)
    response = api_client.post(auth_url('change-password'), {
        'current_password': 'StrongPass!123',
        'new_password': 'AnotherStrong!456',
        'new_password_confirm': 'AnotherStrong!456',
    }, format='json')
    assert response.status_code == 200
    approved_user.refresh_from_db()
    assert approved_user.check_password('AnotherStrong!456')
    assert UserPasswordHistory.objects.filter(user=approved_user).exists()

    response = api_client.post(auth_url('change-password'), {
        'current_password': 'AnotherStrong!456',
        'new_password': 'StrongPass!123',
        'new_password_confirm': 'StrongPass!123',
    }, format='json')
    assert response.status_code == 400
    assert 'recently used' in str(response.data).lower()


def test_password_reset_request_and_confirm(api_client, approved_user):
    response = api_client.post(auth_url('reset-password'), {'email': approved_user.email}, format='json')
    assert response.status_code == 200
    otp = UserOTP.objects.filter(user=approved_user, otp_type=UserOTP.OTPType.PASSWORD_RESET).latest('created_at')
    response = api_client.post(auth_url('confirm-reset-password'), {
        'token': otp.otp_code,
        'new_password': 'ResetStrong!789',
        'new_password_confirm': 'ResetStrong!789',
    }, format='json')
    assert response.status_code == 200
    approved_user.refresh_from_db()
    assert approved_user.check_password('ResetStrong!789')
    assert UserOTP.objects.get(pk=otp.pk).is_used is True


def test_mfa_enrollment_and_verification(api_client, approved_user):
    api_client.force_authenticate(approved_user)
    response = api_client.post(auth_url('setup-2fa'), {}, format='json')
    assert response.status_code == 200
    secret = response.data['data']['secret']
    assert response.data['data']['qr_code_url'].startswith('data:image/png;base64,')
    assert len(response.data['data']['backup_codes']) == 8

    response = api_client.post(auth_url('verify-2fa'), {
        'otp_code': pyotp.TOTP(secret).now(),
    }, format='json')
    assert response.status_code == 200
    approved_user.refresh_from_db()
    assert approved_user.is_2fa_enabled is True
    assert TwoFactorAuth.objects.get(user=approved_user).is_active is True

    api_client.force_authenticate(None)
    response = api_client.post(auth_url('login'), {
        'username': approved_user.username,
        'password': 'StrongPass!123',
    }, format='json')
    assert response.status_code == 200
    assert response.data['data']['requires_2fa'] is True
    response = api_client.post(auth_url('login'), {
        'username': approved_user.username,
        'password': 'StrongPass!123',
        'otp_code': pyotp.TOTP(secret).now(),
    }, format='json')
    assert response.status_code == 200
    assert response.data['data']['access_token']


def test_admin_mfa_reset_is_audited(api_client, approved_user):
    admin = User.objects.create_superuser(
        username='iam-admin', email='iam-admin@example.com', password='AdminStrong!123',
    )
    factor = TwoFactorAuth.objects.create(user=approved_user, app_secret='JBSWY3DPEHPK3PXP', is_active=True)
    approved_user.is_2fa_enabled = True
    approved_user.mfa_required = True
    approved_user.save(update_fields=['is_2fa_enabled', 'mfa_required'])
    api_client.force_authenticate(admin)
    response = api_client.post(f'/api/v1/users/users/{approved_user.pk}/reset_mfa/', {}, format='json')
    assert response.status_code == 200
    approved_user.refresh_from_db()
    factor.refresh_from_db()
    assert approved_user.is_2fa_enabled is False
    assert approved_user.mfa_required is False
    assert factor.is_active is False
    assert approved_user.activity_logs.filter(action_type=UserActivityLog.ActionType.TWO_FA_DISABLE).exists()


def test_me_contains_iam_fields(api_client, approved_user):
    api_client.force_authenticate(approved_user)
    response = api_client.get(auth_url('me'))
    assert response.status_code == 200
    payload = response.data['data']['user']
    assert payload['status'] == User.AccountStatus.ACTIVE
    assert payload['partner_id'] == '11111111-1111-1111-1111-111111111111'
    assert 'mfa_required' in payload
    assert 'sso_provider' in payload
    assert 'last_password_changed_at' in payload


def test_unauthorized_access_returns_401(api_client):
    response = api_client.get(auth_url('me'))
    assert response.status_code == 401
