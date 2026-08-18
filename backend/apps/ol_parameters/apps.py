from django.apps import AppConfig


class OLParametersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.ol_parameters"
    label = "ol_parameters"
    verbose_name = "Ordinary Life Parameters"

    def ready(self):
        from apps.ol_parameters.audit_receivers import register_receivers

        register_receivers()
