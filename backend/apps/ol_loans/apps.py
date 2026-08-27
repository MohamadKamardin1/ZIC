from django.apps import AppConfig


class OLLoansConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.ol_loans"
    label = "ol_loans"
    verbose_name = "Ordinary Life Loans"

    def ready(self):
        from apps.ol_loans.audit_receivers import register_receivers
        from apps.ol_loans.integration_receivers import route_loan_integrations
        from apps.ol_loans.services.parameter_cache import register_parameter_cache_receivers

        register_receivers()
        register_parameter_cache_receivers()
        # Importing the receiver registers its idempotent DomainEvent hook.
        route_loan_integrations
