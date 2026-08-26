from django.apps import AppConfig


class OLLoansConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.ol_loans"
    label = "ol_loans"
    verbose_name = "Ordinary Life Loans"

    def ready(self):
        from apps.ol_loans.audit_receivers import register_receivers

        register_receivers()
