from django.apps import AppConfig


class SystemParametersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.system_parameters"
    label = "system_parameters"
    verbose_name = "System Parameters"
