from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from import_export.admin import ImportExportModelAdmin
from import_export import resources

from .models import User, UserGroup, UserPermission, PermissionGroup, NotificationPreference


class UserResource(resources.ModelResource):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name',
                   'phone_number', 'user_type', 'is_active', 'is_approved',
                   'date_joined', 'last_login', 'last_activity']


@admin.register(User)
class UserAdmin(ImportExportModelAdmin, admin.ModelAdmin):
    resource_class = UserResource
    list_display = [
        'username', 'email', 'first_name', 'last_name',
        'user_type', 'is_active', 'is_approved', 'is_2fa_enabled',
        'last_login', 'last_activity',
    ]
    list_filter = ['is_active', 'is_approved', 'is_2fa_enabled', 'user_type', 'date_joined']
    search_fields = ['username', 'email', 'first_name', 'last_name', 'phone_number']
    ordering = ['-date_joined']
    date_hierarchy = 'date_joined'
    readonly_fields = ['id', 'date_joined', 'last_login', 'last_activity',
                        'failed_login_attempts', 'account_locked_until',
                        'password_changed_at', 'password']
    filter_horizontal = ['groups', 'user_permissions']

    fieldsets = (
        (None, {'fields': ('id', 'username', 'email', 'password')}),
        (_('Personal Info'), {'fields': ('first_name', 'last_name', 'phone_number')}),
        (_('Permissions'), {
            'fields': ('user_type', 'is_active', 'is_approved', 'is_staff', 'is_superuser',
                       'groups', 'user_permissions'),
        }),
        (_('Security'), {
            'fields': ('is_2fa_enabled', 'otp_method', 'failed_login_attempts',
                       'account_locked_until', 'password_changed_at', 'must_change_password'),
        }),
        (_('Activity'), {
            'fields': ('last_login', 'last_activity', 'last_ip_address', 'user_agent', 'date_joined'),
        }),
    )

    actions = ['approve_users', 'activate_users', 'deactivate_users']

    def approve_users(self, request, queryset):
        queryset.update(is_approved=True)
        self.message_user(request, f'{queryset.count()} users approved.')
    approve_users.short_description = 'Approve selected users'

    def activate_users(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, f'{queryset.count()} users activated.')
    activate_users.short_description = 'Activate selected users'

    def deactivate_users(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, f'{queryset.count()} users deactivated.')
    deactivate_users.short_description = 'Deactivate selected users'


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
