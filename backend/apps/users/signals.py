import logging

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import User, NotificationPreference, TwoFactorAuth

logger = logging.getLogger('apps.users.signals')


@receiver(post_save, sender=User)
def create_notification_preferences(sender, instance, created, **kwargs):
    if created:
        NotificationPreference.objects.get_or_create(user=instance)
        logger.debug(f'Notification preferences created for {instance.email}')


@receiver(pre_save, sender=User)
def handle_2fa_auto_create(sender, instance, **kwargs):
    if instance.pk and instance.is_2fa_enabled:
        try:
            original = sender.objects.get(pk=instance.pk)
            if not original.is_2fa_enabled:
                TwoFactorAuth.objects.get_or_create(user=instance)
        except sender.DoesNotExist:
            pass


@receiver(post_save, sender=User)
def handle_user_activity_log(sender, instance, created, **kwargs):
    if created:
        try:
            from .models import UserActivityLog
            UserActivityLog.objects.create(
                user=instance,
                action_type='LOGIN',
            )
        except Exception as e:
            logger.warning(f'Could not create activity log for new user: {e}')
