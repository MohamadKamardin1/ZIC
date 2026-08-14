from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from import_export import resources
from import_export.admin import ImportExportModelAdmin

from apps.authentication import services as iam_services

from .models import NotificationPreference, PermissionGroup, User, UserGroup, UserPermission


class UserResource(resources.ModelResource):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name',
                   'phone_number', 'user_type', 'status', 'partner_id', 'is_active', 'is_approved',
                   'mfa_required', 'sso_provider', 'sso_subject',
                   'date_joined', 'last_login', 'last_activity']


@admin.register(User)
class UserAdmin(ImportExportModelAdmin, admin.ModelAdmin):
    resource_class = UserResource
    list_display = [
        'username', 'email', 'first_name', 'last_name',
        'user_type', 'status', 'is_active', 'is_approved', 'is_2fa_enabled', 'mfa_required',
        'last_login', 'last_activity',
    ]
    list_filter = ['is_active', 'is_approved', 'is_2fa_enabled', 'mfa_required', 'status', 'user_type', 'date_joined']
    search_fields = ['username', 'email', 'first_name', 'last_name', 'phone_number']
    ordering = ['-date_joined']
    date_hierarchy = 'date_joined'
    readonly_fields = ['id', 'date_joined', 'last_login', 'last_activity',
                        'failed_login_attempts', 'account_locked_until',
                        'password_changed_at', 'last_password_changed_at', 'password']
    filter_horizontal = ['groups', 'user_permissions']

    fieldsets = (
        (None, {'fields': ('id', 'username', 'email', 'password')}),
        (_('Personal Info'), {'fields': ('first_name', 'last_name', 'phone_number')}),
        (_('Permissions'), {
            'fields': ('user_type', 'status', 'partner_id', 'is_active', 'is_approved',
                       'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Security'), {
            'fields': ('is_2fa_enabled', 'mfa_required', 'otp_method', 'sso_provider',
                       'sso_subject', 'failed_login_attempts', 'account_locked_until',
                       'password_changed_at', 'last_password_changed_at', 'must_change_password'),
        }),
        (_('Activity'), {
            'fields': ('last_login', 'last_activity', 'last_ip_address', 'user_agent', 'date_joined'),
        }),
    )

    actions = ['approve_users', 'activate_users', 'deactivate_users', 'reset_mfa']

    def approve_users(self, request, queryset):
        queryset.update(is_approved=True)
        self.message_user(request, f'{queryset.count()} users approved.')
    approve_users.short_description = 'Approve selected users'

    def activate_users(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, f'{queryset.count()} users activated.')
    activate_users.short_description = 'Activate selected users'

    def deactivate_users(self, request, queryset):
        queryset.update(is_active=False, status=User.AccountStatus.INACTIVE)
        self.message_user(request, f'{queryset.count()} users deactivated.')
    deactivate_users.short_description = 'Deactivate selected users'

    def reset_mfa(self, request, queryset):
        count = 0
        for user in queryset:
            iam_services.reset_user_mfa(actor=request.user, user=user, request=request)
            count += 1
        self.message_user(request, f'MFA reset for {count} selected users.')
    reset_mfa.short_description = 'Reset MFA for selected users'


@admin.register(UserGroup)
class UserGroupAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_system_group', 'created_at']
    list_filter = ['is_system_group']
    search_fields = ['name', 'description']
    filter_horizontal = ['permissions']


@admin.register(UserPermission)
class UserPermissionAdmin(admin.ModelAdmin):
    list_display = ['name', 'codename', 'module', 'action', 'resource_type']
    list_filter = ['module', 'action']
    search_fields = ['name', 'codename', 'module']


@admin.register(PermissionGroup)
class PermissionGroupAdmin(admin.ModelAdmin):
    list_display = ['name', 'module_code', 'created_at']
    list_filter = ['module_code']
    search_fields = ['name', 'module_code']
    filter_horizontal = ['permissions']


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ['user', 'email_notifications', 'sms_notifications',
                     'push_notifications', 'login_alerts', 'marketing_emails']
    list_filter = ['email_notifications', 'sms_notifications', 'login_alerts', 'marketing_emails']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['id', 'created_at', 'updated_at']
