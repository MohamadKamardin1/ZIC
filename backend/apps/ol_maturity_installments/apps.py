from django.apps import AppConfig


class OLMaturityInstallmentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.ol_maturity_installments"
    label = "ol_maturity_installments"
    verbose_name = "Ordinary Life Maturity Installments"

    def ready(self):
        # Receiver wiring for audit/notifications is introduced in later prompts
        # of the series once financial actions are implemented.
        return None
