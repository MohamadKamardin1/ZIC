from django.apps import AppConfig


class PartnerOnboardingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.partner_onboarding'
    label = 'partner_onboarding'
    verbose_name = 'Partner Onboarding'

    def ready(self):
        import apps.partner_onboarding.signals  # noqa: F401
