import uuid
import random
import string
import logging

from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
from django.core.validators import MinLengthValidator
from django.conf import settings

from cryptography.fernet import Fernet
import base64
import hashlib

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
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_approved', True)
        extra_fields.setdefault('user_type', 'SUPER_ADMIN')
        return self.create_user(username, email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    class UserType(models.TextChoices):
        PORTAL_USER = 'PORTAL_USER', 'Portal User'
        MANAGER = 'MANAGER', 'Manager'
        QUOTATION_ONLY = 'QUOTATION_ONLY', 'Quotation Only'
        UNDERWRITER = 'UNDERWRITER', 'Underwriter'
        SYSTEM_MANAGER = 'SYSTEM_MANAGER', 'System Manager'
        AIMS_GROUP = 'AIMS_GROUP', 'AIMS Group'
        SUPER_ADMIN = 'SUPER_ADMIN', 'Super Admin'

    class OTPMethod(models.TextChoices):
        AUTH_APP = 'AUTH_APP', 'Authenticator App'
        SMS = 'SMS', 'SMS'
        EMAIL = 'EMAIL', 'Email'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    user_type = models.CharField(
        max_length=30, choices=UserType.choices, default=UserType.PORTAL_USER
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=False)
    is_2fa_enabled = models.BooleanField(default=False)
    otp_secret = models.TextField(blank=True, null=True)
    otp_method = models.CharField(
        max_length=20, choices=OTPMethod.choices, default=OTPMethod.EMAIL
    )
    failed_login_attempts = models.IntegerField(default=0)
    account_locked_until = models.DateTimeField(null=True, blank=True)
    password_changed_at = models.DateTimeField(null=True, blank=True)
    must_change_password = models.BooleanField(default=False)
    last_ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.CharField(max_length=500, blank=True)
    last_activity = models.DateTimeField(null=True, blank=True)
    date_joined = models.DateTimeField(default=timezone.now)
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
        ]

    def __str__(self):
        return f'{self.username} ({self.email})'

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.email:
            self.email = self.__class__.objects.normalize_email(self.email)

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if is_new:
            logger.info(f'User created: {self.email} (ID: {self.id})')

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'.strip()

    @property
    def is_account_locked(self):
        if self.account_locked_until and timezone.now() < self.account_locked_until:
            return True
        return False

    @property
    def active_sessions_count(self):
        return self.sessions.filter(is_active=True).count()

    def has_module_permission(self, module_code, action='READ'):
        if self.is_superuser:
            return True
        return self.groups.filter(
            permissions__module=module_code,
            permissions__action=action,
        ).exists()

    def record_failed_login(self):
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= 5:
            self.account_locked_until = timezone.now() + timezone.timedelta(minutes=15)
            logger.warning(f'Account locked for {self.email} due to 5 failed login attempts')
        self.save(update_fields=['failed_login_attempts', 'account_locked_until'])

    def reset_failed_login(self):
        self.failed_login_attempts = 0
        self.account_locked_until = None
        self.save(update_fields=['failed_login_attempts', 'account_locked_until'])


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
        AIMS_GROUP = 'AIMS_GROUP', 'AIMS Group'
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
        codes = []
        for _ in range(count):
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
            codes.append(hashlib.sha256(code.encode()).hexdigest())
        self.backup_codes = codes
        self.save(update_fields=['backup_codes'])
        return codes

    def verify_backup_code(self, code):
        hashed = hashlib.sha256(code.encode()).hexdigest()
        if hashed in self.backup_codes:
            self.backup_codes.remove(hashed)
            self.save(update_fields=['backup_codes'])
            return True
        return False
