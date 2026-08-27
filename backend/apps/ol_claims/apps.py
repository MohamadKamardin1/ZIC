from django.apps import AppConfig


class OLClaimsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.ol_claims"
    label = "ol_claims"
    verbose_name = "Ordinary Life Claims"

    def ready(self):
        from apps.ol_claims import approval_receivers  # noqa: F401
