from django.apps import AppConfig


class OLQuotationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.ol_quotations"
    label = "ol_quotations"

    def ready(self):
        from apps.ol_quotations.audit_receivers import register_receivers

        register_receivers()
