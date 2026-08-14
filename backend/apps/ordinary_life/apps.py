from django.apps import AppConfig


class OrdinaryLifeConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.ordinary_life"

    def ready(self):
        from apps.ordinary_life.audit_receivers import register_receivers

        register_receivers()
