from django.contrib import admin

from .models import UserActivityLog


@admin.register(UserActivityLog)
class UserActivityLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'action_type', 'ip_address', 'timestamp']
    list_filter = ['action_type', 'timestamp']
    search_fields = ['user__username', 'user__email', 'ip_address']
    date_hierarchy = 'timestamp'
    readonly_fields = ['user', 'action_type', 'ip_address', 'user_agent', 'timestamp', 'details']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
