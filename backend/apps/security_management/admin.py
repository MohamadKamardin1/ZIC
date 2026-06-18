from django.contrib import admin

from .models import UserSession, UserOTP, TwoFactorAuth


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ['user', 'device_type', 'ip_address', 'login_time', 'last_activity', 'is_active']
    list_filter = ['is_active', 'device_type']
    search_fields = ['user__username', 'user__email', 'ip_address']
    date_hierarchy = 'login_time'
    readonly_fields = ['user', 'session_key', 'ip_address', 'user_agent',
                        'login_time', 'last_activity', 'device_type']

    def has_add_permission(self, request):
        return False


@admin.register(UserOTP)
class UserOTPAdmin(admin.ModelAdmin):
    list_display = ['user', 'otp_type', 'is_used', 'expires_at', 'created_at']
    list_filter = ['otp_type', 'is_used']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['user', 'otp_code', 'otp_type', 'is_used', 'expires_at', 'created_at']

    def has_add_permission(self, request):
        return False


@admin.register(TwoFactorAuth)
class TwoFactorAuthAdmin(admin.ModelAdmin):
    list_display = ['user', 'is_active', 'setup_completed_at']
    list_filter = ['is_active']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['user', 'app_secret', 'setup_completed_at', 'created_at', 'updated_at']
