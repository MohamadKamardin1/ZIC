import base64
import hashlib
import logging
import random
import string
import uuid

from cryptography.fernet import Fernet
from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone

logger = logging.getLogger('apps.users.models')


def encrypt_value(value, key=None):
    if not value:
        return value
    if key is None:
        key = getattr(settings, 'OTP_SECRET_KEY', settings.SECRET_KEY)
    if isinstance(key, str):
        key_bytes = hashlib.sha256(key.encode()).digest()
        key_b64 = base64.urlsafe_b64encode(key_bytes)
    else:
        key_b64 = key
    f = Fernet(key_b64)
    return f.encrypt(value.encode() if isinstance(value, str) else value).decode()


def decrypt_value(encrypted_value, key=None):
    if not encrypted_value:
        return encrypted_value
    if key is None:
        key = getattr(settings, 'OTP_SECRET_KEY', settings.SECRET_KEY)
    if isinstance(key, str):
        key_bytes = hashlib.sha256(key.encode()).digest()
        key_b64 = base64.urlsafe_b64encode(key_bytes)
    else:
        key_b64 = key
    f = Fernet(key_b64)
    return f.decrypt(encrypted_value.encode() if isinstance(encrypted_value, str) else encrypted_value).decode()


class UserManager(BaseUserManager):
    def create_user(self, username, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        if not username:
            raise ValueError('Username is required')
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        # A newly provisioned account has no verified password-change event yet;
        # IAM records timestamps when the password is changed after creation.
        user.password_changed_at = None
        user.last_password_changed_at = None
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_approved', True)
        extra_fields.setdefault('status', User.AccountStatus.ACTIVE)
        extra_fields.setdefault('user_type', 'SUPER_ADMIN')
        return self.create_user(username, email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    class UserType(models.TextChoices):
        PORTAL_USER = 'PORTAL_USER', 'Portal User'
        MANAGER = 'MANAGER', 'Manager'
        QUOTATION_ONLY = 'QUOTATION_ONLY', 'Quotation Only'
        UNDERWRITER = 'UNDERWRITER', 'Underwriter'
        SYSTEM_MANAGER = 'SYSTEM_MANAGER', 'System Manager'
        ZIC_GROUP = 'ZIC_GROUP', 'ZIC Group'
        SUPER_ADMIN = 'SUPER_ADMIN', 'Super Admin'

    class OTPMethod(models.TextChoices):
        AUTH_APP = 'AUTH_APP', 'Authenticator App'
        SMS = 'SMS', 'SMS'
        EMAIL = 'EMAIL', 'Email'

    class AccountStatus(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        INACTIVE = 'INACTIVE', 'Inactive'
        LOCKED = 'LOCKED', 'Locked'
        PENDING_ACTIVATION = 'PENDING_ACTIVATION', 'Pending activation'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    user_type = models.CharField(
        max_length=30,
        choices=[
            ('STAFF', 'Staff'),
            ('PARTNER', 'Partner'),
            *UserType.choices,
        ],
        default=UserType.PORTAL_USER,
    )
    status = models.CharField(
        max_length=30,
        choices=AccountStatus.choices,
        default=AccountStatus.ACTIVE,
        db_index=True,
    )
    # UUID link avoids a migration cycle because partners already depends on users.
    partner_id = models.UUIDField(null=True, blank=True, db_index=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=False)
    is_2fa_enabled = models.BooleanField(default=False)
    mfa_required = models.BooleanField(default=False)
    otp_secret = models.TextField(blank=True, null=True)
    sso_provider = models.CharField(max_length=100, blank=True, default='')
    sso_subject = models.CharField(max_length=255, blank=True, default='', db_index=True)
    otp_method = models.CharField(
        max_length=20, choices=OTPMethod.choices, default=OTPMethod.EMAIL
    )
    failed_login_attempts = models.IntegerField(default=0)
    account_locked_until = models.DateTimeField(null=True, blank=True)
    password_changed_at = models.DateTimeField(null=True, blank=True)
    last_password_changed_at = models.DateTimeField(null=True, blank=True)
    must_change_password = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='created_users',
    )
    updated_by = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='updated_users',
    )
    last_ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.CharField(max_length=500, blank=True)
    last_activity = models.DateTimeField(null=True, blank=True)
    date_joined = models.DateTimeField(default=timezone.now)

    # Verification
    email_verified = models.BooleanField(default=False)
    email_verified_at = models.DateTimeField(null=True, blank=True)
    phone_verified = models.BooleanField(default=False)
    phone_verified_at = models.DateTimeField(null=True, blank=True)

    # Profile
    avatar = models.TextField(blank=True, default='')
    date_of_birth = models.DateField(null=True, blank=True)
    department = models.CharField(max_length=200, blank=True, default='')
    job_title = models.CharField(max_length=200, blank=True, default='')
    employee_id = models.CharField(max_length=50, blank=True, default='')

    # Compliance
    terms_accepted_at = models.DateTimeField(null=True, blank=True)
    last_password_change_reminded = models.DateTimeField(null=True, blank=True)

    groups = models.ManyToManyField(
        'users.UserGroup',
        related_name='users',
        blank=True,
    )

    objects = UserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email', 'first_name', 'last_name']

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-date_joined']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['username']),
            models.Index(fields=['is_active']),
            models.Index(fields=['user_type']),
            models.Index(fields=['email_verified']),
            models.Index(fields=['department']),
            models.Index(fields=['employee_id']),
        ]

    def __str__(self):
        return f'{self.username} ({self.email})'

    def clean(self):
        if self.email:
            self.email = self.__class__.objects.normalize_email(self.email)

    def set_password(self, raw_password):
        super().set_password(raw_password)
        now = timezone.now()
        self.password_changed_at = now
        self.last_password_changed_at = now

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        if self.status == self.AccountStatus.LOCKED and self.account_locked_until is None and self.is_active:
            self.status = self.AccountStatus.ACTIVE
        super().save(*args, **kwargs)
        if is_new:
            logger.info(f'User created: {self.email} (ID: {self.id})')

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'.strip()

    @property
    def locked_until(self):
        return self.account_locked_until

    @locked_until.setter
    def locked_until(self, value):
        self.account_locked_until = value

    @property
    def mfa_enabled(self):
        return self.is_2fa_enabled

    @mfa_enabled.setter
    def mfa_enabled(self, value):
        self.is_2fa_enabled = value

    @property
    def is_account_locked(self):
        lock_until = self.account_locked_until
        if lock_until:
            return timezone.now() < lock_until
        return self.status == self.AccountStatus.LOCKED

    @property
    def active_sessions_count(self):
        return self.sessions.filter(is_active=True).count()

    @property
    def is_password_expired(self):
        if not self.password_changed_at:
            return True
        expiry_days = getattr(settings, 'PASSWORD_EXPIRY_DAYS', 90)
        return timezone.now() > self.password_changed_at + timezone.timedelta(days=expiry_days)

    @property
    def is_email_verified(self):
        return self.email_verified

    @property
    def is_phone_verified(self):
        return self.phone_verified

    def has_module_permission(self, module_code, action='READ'):
        if self.is_superuser:
            return True
        return self.groups.filter(
            permissions__module=module_code,
            permissions__action=action,
        ).exists()

    def record_failed_login(self):
        self.failed_login_attempts += 1
        update_fields = ['failed_login_attempts']
        max_attempts = getattr(settings, 'LOGIN_MAX_FAILED_ATTEMPTS', 5)
        lockout_minutes = getattr(settings, 'LOGIN_LOCKOUT_MINUTES', 15)
        if self.failed_login_attempts >= max_attempts:
            self.account_locked_until = timezone.now() + timezone.timedelta(minutes=lockout_minutes)
            self.status = self.AccountStatus.LOCKED
            update_fields.extend(['account_locked_until', 'status'])
            logger.warning('Account locked after repeated failed login attempts', extra={'user_id': str(self.id)})
        self.save(update_fields=update_fields)

    def reset_failed_login(self):
        self.failed_login_attempts = 0
        self.account_locked_until = None
        if self.status == self.AccountStatus.LOCKED:
            self.status = self.AccountStatus.ACTIVE if self.is_active else self.AccountStatus.INACTIVE
        self.save(update_fields=['failed_login_attempts', 'account_locked_until', 'status'])


class UserPermission(models.Model):
    class Action(models.TextChoices):
        CREATE = 'CREATE', 'Create'
        READ = 'READ', 'Read'
        UPDATE = 'UPDATE', 'Update'
        DELETE = 'DELETE', 'Delete'
        APPROVE = 'APPROVE', 'Approve'
        EXPORT = 'EXPORT', 'Export'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    codename = models.CharField(max_length=100, unique=True)
    module = models.CharField(max_length=100, db_index=True)
    action = models.CharField(max_length=20, choices=Action.choices, default=Action.READ)
    resource_type = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Permission'
        verbose_name_plural = 'Permissions'
        ordering = ['module', 'name']
        unique_together = ['module', 'action', 'resource_type']

    def __str__(self):
        return f'{self.name} ({self.codename})'


class PermissionGroup(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    module_code = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    permissions = models.ManyToManyField(UserPermission, related_name='permission_groups', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Permission Group'
        verbose_name_plural = 'Permission Groups'
        ordering = ['module_code', 'name']

    def __str__(self):
        return self.name


class UserGroup(models.Model):
    class GroupName(models.TextChoices):
        PORTAL_USER = 'PORTAL_USER', 'Portal User'
        MANAGER = 'MANAGER', 'Manager'
        QUOTATION_ONLY = 'QUOTATION_ONLY', 'Quotation Only'
        UNDERWRITER = 'UNDERWRITER', 'Underwriter'
        SYSTEM_MANAGER = 'SYSTEM_MANAGER', 'System Manager'
        ZIC_GROUP = 'ZIC_GROUP', 'ZIC Group'
        SUPER_ADMIN = 'SUPER_ADMIN', 'Super Admin'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=30, choices=GroupName.choices, unique=True)
    description = models.TextField(blank=True)
    is_system_group = models.BooleanField(default=False)
    permissions = models.ManyToManyField(UserPermission, related_name='groups', blank=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='created_groups'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'User Group'
        verbose_name_plural = 'User Groups'
        ordering = ['name']

    def __str__(self):
        return self.get_name_display()

    def save(self, *args, **kwargs):
        if self.name in [choice[0] for choice in self.GroupName.choices]:
            self.is_system_group = True
        super().save(*args, **kwargs)


class UserSession(models.Model):
    class DeviceType(models.TextChoices):
        WEB = 'WEB', 'Web Browser'
        MOBILE = 'MOBILE', 'Mobile'
        TABLET = 'TABLET', 'Tablet'
        API = 'API', 'API Client'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    session_key = models.CharField(max_length=100, blank=True, default='')
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.CharField(max_length=500, blank=True)
    login_time = models.DateTimeField(default=timezone.now)
    last_activity = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)
    device_type = models.CharField(
        max_length=20, choices=DeviceType.choices, default=DeviceType.WEB
    )

    class Meta:
        verbose_name = 'User Session'
        verbose_name_plural = 'User Sessions'
        ordering = ['-last_activity']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['session_key']),
        ]

    def __str__(self):
        return f'{self.user.username} - {self.device_type} ({self.login_time})'


class UserActivityLog(models.Model):
    class ActionType(models.TextChoices):
        LOGIN = 'LOGIN', 'Login'
        LOGOUT = 'LOGOUT', 'Logout'
        PASSWORD_CHANGE = 'PASSWORD_CHANGE', 'Password Change'
        PROFILE_UPDATE = 'PROFILE_UPDATE', 'Profile Update'
        PERMISSION_CHANGE = 'PERMISSION_CHANGE', 'Permission Change'
        ACCOUNT_LOCKED = 'ACCOUNT_LOCKED', 'Account Locked'
        TWO_FA_SETUP = 'TWO_FA_SETUP', '2FA Setup'
        TWO_FA_DISABLE = 'TWO_FA_DISABLE', '2FA Disabled'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activity_logs')
    action_type = models.CharField(max_length=30, choices=ActionType.choices)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.CharField(max_length=500, blank=True)
    timestamp = models.DateTimeField(default=timezone.now)
    details = models.JSONField(blank=True, null=True)

    class Meta:
        verbose_name = 'User Activity Log'
        verbose_name_plural = 'User Activity Logs'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['action_type']),
        ]

    def __str__(self):
        return f'{self.user.username} - {self.action_type} ({self.timestamp})'

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if is_new:
            logger.info(
                f'[{self.action_type}] {self.user.email} '
                f'from {self.ip_address or "unknown"}'
            )


class UserOTP(models.Model):
    class OTPType(models.TextChoices):
        LOGIN = 'LOGIN', 'Login Verification'
        PASSWORD_RESET = 'PASSWORD_RESET', 'Password Reset'
        EMAIL_VERIFICATION = 'EMAIL_VERIFICATION', 'Email Verification'
        PHONE_VERIFICATION = 'PHONE_VERIFICATION', 'Phone Verification'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='otps')
    otp_code = models.CharField(max_length=8)
    otp_type = models.CharField(max_length=30, choices=OTPType.choices)
    is_used = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'User OTP'
        verbose_name_plural = 'User OTPs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'otp_type', 'is_used']),
        ]

    def __str__(self):
        return f'{self.user.username} - {self.otp_type} ({self.created_at})'

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    @property
    def is_valid(self):
        return not self.is_used and not self.is_expired

    @classmethod
    def generate_otp(cls, user, otp_type, length=6, expiry_minutes=10):
        otp_code = ''.join(random.choices(string.digits, k=length))
        otp = cls.objects.create(
            user=user,
            otp_code=otp_code,
            otp_type=otp_type,
            expires_at=timezone.now() + timezone.timedelta(minutes=expiry_minutes),
        )
        return otp


class TwoFactorAuth(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='two_factor_auth')
    app_secret = models.TextField(blank=True, null=True)
    backup_codes = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=False)
    setup_completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Two Factor Auth'
        verbose_name_plural = 'Two Factor Auths'

    def __str__(self):
        return f'{self.user.username} - 2FA: {self.is_active}'

    def generate_backup_codes(self, count=8):
        plaintext_codes = []
        hashed_codes = []
        for _ in range(count):
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
            plaintext_codes.append(code)
            hashed_codes.append(hashlib.sha256(code.encode()).hexdigest())
        self.backup_codes = hashed_codes
        self.save(update_fields=['backup_codes'])
        return plaintext_codes

    def verify_backup_code(self, code):
        hashed = hashlib.sha256(code.encode()).hexdigest()
        if hashed in self.backup_codes:
            self.backup_codes.remove(hashed)
            self.save(update_fields=['backup_codes'])
            return True
        return False


class NotificationPreference(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='notification_preferences'
    )
    email_notifications = models.BooleanField(default=True)
    sms_notifications = models.BooleanField(default=True)
    push_notifications = models.BooleanField(default=False)
    login_alerts = models.BooleanField(default=True)
    marketing_emails = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Notification Preference'
        verbose_name_plural = 'Notification Preferences'

    def __str__(self):
        return f'{self.user.username} preferences'


class UserPasswordHistory(models.Model):
    """One-way password history used to prevent recent password reuse."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='password_history')
    password_hash = models.CharField(max_length=256)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['user', '-created_at'])]

    def __str__(self):
        return f'{self.user.username} password history ({self.created_at})'


class SSOProviderConfig(models.Model):
    """Database-backed OIDC/SAML readiness configuration; disabled by default."""

    class Provider(models.TextChoices):
        OIDC = 'OIDC', 'OpenID Connect'
        SAML = 'SAML', 'SAML 2.0'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    provider = models.CharField(max_length=20, choices=Provider.choices, default=Provider.OIDC)
    enabled = models.BooleanField(default=False)
    issuer_url = models.URLField(blank=True, default='')
    authorization_url = models.URLField(blank=True, default='')
    token_url = models.URLField(blank=True, default='')
    client_id = models.CharField(max_length=255, blank=True, default='')
    client_secret_encrypted = models.TextField(blank=True, default='')
    scopes = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_sso_configs'
    )
    updated_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='updated_sso_configs'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.provider})'

    @property
    def is_configured(self):
        return bool(self.enabled and self.client_id and self.issuer_url)
