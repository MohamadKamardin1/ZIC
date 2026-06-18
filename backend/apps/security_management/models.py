from apps.users.models import UserSession as BaseUserSession
from apps.users.models import UserOTP as BaseUserOTP
from apps.users.models import TwoFactorAuth as BaseTwoFactorAuth


class UserSession(BaseUserSession):
    class Meta:
        proxy = True
        app_label = 'security_management'
        verbose_name = 'User Session'
        verbose_name_plural = 'User Sessions'


class UserOTP(BaseUserOTP):
    class Meta:
        proxy = True
        app_label = 'security_management'
        verbose_name = 'User OTP'
        verbose_name_plural = 'User OTPs'


class TwoFactorAuth(BaseTwoFactorAuth):
    class Meta:
        proxy = True
        app_label = 'security_management'
        verbose_name = 'Two Factor Auth'
        verbose_name_plural = 'Two Factor Auths'
