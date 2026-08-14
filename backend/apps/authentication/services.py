import logging
from dataclasses import dataclass

import pyotp
from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.models import (
    TwoFactorAuth,
    User,
    UserActivityLog,
    UserOTP,
    UserPasswordHistory,
    UserSession,
)

logger = logging.getLogger('apps.authentication.services')


class IAMServiceError(Exception):
    def __init__(self, message, code='authentication_error'):
        self.message = message
        self.code = code
        super().__init__(message)


class MFARequiredError(IAMServiceError):
    def __init__(self):
        super().__init__('A one-time password is required.', 'mfa_required')


class AccountLockedError(IAMServiceError):
    def __init__(self, locked_until=None):
        message = 'Account is temporarily locked.'
        if locked_until:
            message = f'Account locked until {locked_until.strftime("%Y-%m-%d %H:%M")}. '
        super().__init__(message, 'account_locked')


@dataclass(frozen=True)
class LoginResult:
    user: User
    requires_mfa: bool = False


def response_meta():
    return {'timestamp': timezone.now().isoformat(), 'version': 'v1'}


def tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'access_token': str(refresh.access_token),
        'refresh_token': str(refresh),
        'access_expires_in': settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'].total_seconds(),
        'refresh_expires_in': settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds(),
    }


def _find_user(identifier):
    normalized = (identifier or '').strip()
    if not normalized:
        return None
    return User.objects.filter(username__iexact=normalized).first() or User.objects.filter(email__iexact=normalized).first()


def _unlock_if_expired(user):
    if user.account_locked_until and user.account_locked_until <= timezone.now():
        user.account_locked_until = None
        user.failed_login_attempts = 0
        if user.status == User.AccountStatus.LOCKED:
            user.status = User.AccountStatus.ACTIVE if user.is_active else User.AccountStatus.INACTIVE
        user.save(update_fields=['account_locked_until', 'failed_login_attempts', 'status'])


def _audit(user, action, request=None, details=None):
    UserActivityLog.objects.create(
        user=user,
        action_type=action,
        ip_address=(request.META.get('REMOTE_ADDR') if request else None),
        user_agent=(request.META.get('HTTP_USER_AGENT', '')[:500] if request else ''),
        details=details or None,
    )


def _verify_mfa(user, otp_code, active_only=True):
    factor_query = TwoFactorAuth.objects.filter(user=user)
    if active_only:
        factor_query = factor_query.filter(is_active=True)
    factor = factor_query.first()
    if factor is None or not factor.app_secret:
        return False
    if otp_code and pyotp.TOTP(factor.app_secret).verify(otp_code, valid_window=1):
        return True
    return bool(otp_code and factor.verify_backup_code(otp_code))


def authenticate_login(identifier, password, request=None, otp_code=''):
    user = _find_user(identifier)
    if user is None or not user.check_password(password):
        if user is not None:
            user.record_failed_login()
            if user.is_account_locked:
                _audit(user, UserActivityLog.ActionType.ACCOUNT_LOCKED, request)
        raise IAMServiceError('Invalid credentials.', 'invalid_credentials')

    _unlock_if_expired(user)
    if user.is_account_locked:
        raise AccountLockedError(user.account_locked_until)
    if not user.is_active or user.status == User.AccountStatus.INACTIVE:
        raise IAMServiceError('Account is disabled.', 'account_disabled')
    if user.status == User.AccountStatus.PENDING_ACTIVATION or not user.is_approved:
        raise IAMServiceError('Account pending approval.', 'account_pending')

    mfa_required = bool(user.is_2fa_enabled or user.mfa_required or (
        user.user_type in {'STAFF', 'SUPER_ADMIN'} and getattr(settings, 'MFA_REQUIRED_FOR_STAFF', False)
    ))
    if mfa_required:
        if not otp_code:
            return LoginResult(user=user, requires_mfa=True)
        if not _verify_mfa(user, otp_code):
            user.record_failed_login()
            raise IAMServiceError('Invalid OTP code.', 'invalid_mfa')

    with transaction.atomic():
        user = User.objects.select_for_update().get(pk=user.pk)
        user.reset_failed_login()
        now = timezone.now()
        user.last_login = now
        user.last_activity = now
        if request:
            user.last_ip_address = request.META.get('REMOTE_ADDR')
            user.user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
        user.save(update_fields=['last_login', 'last_activity', 'last_ip_address', 'user_agent'])
        _audit(user, UserActivityLog.ActionType.LOGIN, request, {'mfa_verified': mfa_required})
    return LoginResult(user=user, requires_mfa=False)


def create_session(request, user):
    return UserSession.objects.create(
        user=user,
        session_key=getattr(request.session, 'session_key', '') or '',
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
        device_type=detect_device_type(request),
    )


def detect_device_type(request):
    user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
    if any(token in user_agent for token in ('mobile', 'android', 'iphone')):
        return UserSession.DeviceType.MOBILE
    if any(token in user_agent for token in ('tablet', 'ipad')):
        return UserSession.DeviceType.TABLET
    return UserSession.DeviceType.WEB


def logout_user(request, refresh_token=None):
    with transaction.atomic():
        if refresh_token:
            try:
                RefreshToken(refresh_token).blacklist()
            except Exception:
                logger.info('Refresh token was already invalid or expired during logout')
        UserSession.objects.filter(user=request.user, is_active=True).update(is_active=False, last_activity=timezone.now())
        _audit(request.user, UserActivityLog.ActionType.LOGOUT, request)


def _record_password_history(user, old_hash):
    if not old_hash or old_hash == '!':
        return
    UserPasswordHistory.objects.create(user=user, password_hash=old_hash)
    keep = getattr(settings, 'PASSWORD_HISTORY_COUNT', 5)
    stale_ids = list(
        UserPasswordHistory.objects.filter(user=user).order_by('-created_at').values_list('id', flat=True)[keep:]
    )
    if stale_ids:
        UserPasswordHistory.objects.filter(id__in=stale_ids).delete()


def set_password(user, raw_password, request=None, action=UserActivityLog.ActionType.PASSWORD_CHANGE):
    validate_password(raw_password, user)
    with transaction.atomic():
        locked_user = User.objects.select_for_update().get(pk=user.pk)
        if locked_user.check_password(raw_password):
            raise IAMServiceError('New password cannot be the same as current password.', 'password_reused')
        recent = UserPasswordHistory.objects.filter(user=locked_user).order_by('-created_at')[:getattr(settings, 'PASSWORD_HISTORY_COUNT', 5)]
        from django.contrib.auth.hashers import check_password
        if any(check_password(raw_password, item.password_hash) for item in recent):
            raise IAMServiceError('Password was recently used.', 'password_reused')
        old_hash = locked_user.password
        locked_user.set_password(raw_password)
        locked_user.must_change_password = False
        locked_user.save(update_fields=['password', 'password_changed_at', 'last_password_changed_at', 'must_change_password'])
        _record_password_history(locked_user, old_hash)
        _audit(locked_user, action, request, {'password_history_recorded': bool(old_hash)})
        return locked_user


def request_password_reset(email):
    user = User.objects.filter(email__iexact=email).first()
    if user:
        otp = UserOTP.generate_otp(user, UserOTP.OTPType.PASSWORD_RESET)
        logger.info('Password reset requested', extra={'user_id': str(user.id), 'otp_id': str(otp.id)})
    return None


def confirm_password_reset(token, raw_password, request=None):
    validate_password(raw_password)
    with transaction.atomic():
        otp = UserOTP.objects.select_for_update().filter(
            otp_code=token,
            otp_type=UserOTP.OTPType.PASSWORD_RESET,
            is_used=False,
            expires_at__gt=timezone.now(),
        ).select_related('user').first()
        if otp is None:
            raise IAMServiceError('Invalid or expired token.', 'invalid_reset_token')
        user = otp.user
        _record_password_history(user, user.password)
        user.set_password(raw_password)
        user.must_change_password = False
        user.failed_login_attempts = 0
        user.account_locked_until = None
        if user.status == User.AccountStatus.LOCKED:
            user.status = User.AccountStatus.ACTIVE if user.is_active else User.AccountStatus.INACTIVE
        user.save(update_fields=['password', 'password_changed_at', 'last_password_changed_at', 'must_change_password', 'failed_login_attempts', 'account_locked_until', 'status'])
        otp.is_used = True
        otp.save(update_fields=['is_used'])
        _audit(user, UserActivityLog.ActionType.PASSWORD_CHANGE, request, {'reset': True})


def setup_totp(user, issuer='ZIC Insurance'):
    secret = pyotp.random_base32()
    uri = pyotp.TOTP(secret).provisioning_uri(name=user.email, issuer_name=issuer)
    factor, _ = TwoFactorAuth.objects.get_or_create(user=user)
    factor.app_secret = secret
    factor.is_active = False
    factor.setup_completed_at = None
    factor.save(update_fields=['app_secret', 'is_active', 'setup_completed_at', 'updated_at'])
    backup_codes = factor.generate_backup_codes()
    return secret, uri, backup_codes


def verify_totp(user, otp_code, request=None):
    with transaction.atomic():
        factor = TwoFactorAuth.objects.select_for_update().filter(user=user).first()
        if factor is None or not factor.app_secret:
            raise IAMServiceError('2FA is not set up. Call setup-2fa first.', 'mfa_not_setup')
        if not _verify_mfa(user, otp_code, active_only=False):
            raise IAMServiceError('Invalid OTP code.', 'invalid_mfa')
        factor.is_active = True
        factor.setup_completed_at = timezone.now()
        factor.save(update_fields=['is_active', 'setup_completed_at', 'updated_at'])
        user.is_2fa_enabled = True
        user.save(update_fields=['is_2fa_enabled'])
        _audit(user, UserActivityLog.ActionType.TWO_FA_SETUP, request)
        return factor


def disable_totp(user, request=None):
    with transaction.atomic():
        TwoFactorAuth.objects.filter(user=user).update(is_active=False, app_secret=None, backup_codes=[])
        user.is_2fa_enabled = False
        user.save(update_fields=['is_2fa_enabled'])
        _audit(user, UserActivityLog.ActionType.TWO_FA_DISABLE, request)


def reset_user_mfa(actor, user, request=None):
    if not actor.is_staff and not actor.is_superuser:
        raise IAMServiceError('Only administrators can reset MFA.', 'forbidden')
    with transaction.atomic():
        TwoFactorAuth.objects.filter(user=user).update(is_active=False, app_secret=None, backup_codes=[])
        user.is_2fa_enabled = False
        user.mfa_required = False
        user.updated_by = actor
        user.save(update_fields=['is_2fa_enabled', 'mfa_required', 'updated_by'])
        _audit(user, UserActivityLog.ActionType.TWO_FA_DISABLE, request, {'reset_by': str(actor.id)})
