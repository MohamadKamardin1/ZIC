from django.apps import AppConfig


class OLProposalsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.ol_proposals"
    label = "ol_proposals"
    verbose_name = "OL Proposals"

    def ready(self):
        from apps.ol_proposals.audit_receivers import register_receivers

        register_receivers()
