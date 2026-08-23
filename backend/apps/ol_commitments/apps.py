from django.apps import AppConfig


class OLCommitmentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.ol_commitments"
    label = "ol_commitments"
    verbose_name = "OL Commitments"

    def ready(self):
        from apps.ol_commitments.audit_receivers import register_receivers

        register_receivers()
