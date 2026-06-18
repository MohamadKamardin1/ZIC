from apps.users.models import UserActivityLog as BaseUserActivityLog


class UserActivityLog(BaseUserActivityLog):
    class Meta:
        proxy = True
        app_label = 'audit_management'
        verbose_name = 'User Activity Log'
        verbose_name_plural = 'User Activity Logs'
