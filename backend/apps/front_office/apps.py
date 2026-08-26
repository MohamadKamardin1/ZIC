from django.apps import AppConfig


class FrontOfficeConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.front_office'
    label = 'front_office'
    verbose_name = 'Front Office'

    def ready(self):
        from apps.front_office.receipts.audit_receivers import register_receivers

        register_receivers()
