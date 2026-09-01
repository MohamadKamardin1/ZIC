from django.apps import AppConfig


class OLMaturityInstallmentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.ol_maturity_installments"
    label = "ol_maturity_installments"
    verbose_name = "Ordinary Life Maturity Installments"

    def ready(self):
        from apps.ol_maturity_installments.integration_receivers import route_installment_notifications

        # Importing the receiver registers its idempotent DomainEvent hook.
        route_installment_notifications  # noqa: B018
