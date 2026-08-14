from django.apps import AppConfig


class GovernanceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.governance"
    verbose_name = "Enterprise Governance"

    def ready(self):
        import apps.governance.audit_receivers  # noqa: F401
        import apps.governance.services.audit_service  # noqa: F401
        import apps.governance.signals  # noqa: F401
