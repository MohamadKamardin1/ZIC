from django.apps import AppConfig


class GroupCreditConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.group_credit"
    label = "group_credit"
    verbose_name = "Group Credit"

    def ready(self):
        from apps.group_credit.audit_receivers import register_receivers

        register_receivers()
