import logging

from django.db.models.signals import post_save, pre_save, m2m_changed
from django.dispatch import receiver

from .models import User, NotificationPreference, TwoFactorAuth, UserGroup

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


@receiver(post_save, sender=User)
def auto_assign_group_from_user_type(sender, instance, created, **kwargs):
    """
    Ensure the user's groups ManyToMany contains the group matching their user_type
    whenever they are saved (e.g. createsuperuser).
    """
    try:
        group = UserGroup.objects.filter(name=instance.user_type).first()
        if group and not instance.groups.filter(id=group.id).exists():
            # To prevent m2m_changed triggering recursion during save, add silently
            instance.groups.add(group)
    except Exception as e:
        logger.warning(f'Could not auto-assign group from user type: {e}')


@receiver(m2m_changed, sender=User.groups.through)
def sync_user_roles_and_flags(sender, instance, action, reverse, model, pk_set, **kwargs):
    """
    Synchronize is_superuser, is_staff, and user_type based on the assigned groups.
    """
    if action in ["post_add", "post_remove", "post_clear"] and not reverse:
        try:
            assigned_groups = instance.groups.all()
            group_names = [g.name for g in assigned_groups]

            # Determine highest priority user_type
            if "SUPER_ADMIN" in group_names:
                instance.user_type = "SUPER_ADMIN"
                instance.is_superuser = True
                instance.is_staff = True
            elif "ZIC_GROUP" in group_names:
                instance.user_type = "ZIC_GROUP"
                instance.is_staff = True
                instance.is_superuser = False
            elif "SYSTEM_MANAGER" in group_names:
                instance.user_type = "SYSTEM_MANAGER"
                instance.is_staff = True
                instance.is_superuser = False
            elif "UNDERWRITER" in group_names:
                instance.user_type = "UNDERWRITER"
                instance.is_staff = False
                instance.is_superuser = False
            elif "QUOTATION_ONLY" in group_names:
                instance.user_type = "QUOTATION_ONLY"
                instance.is_staff = False
                instance.is_superuser = False
            elif "MANAGER" in group_names:
                instance.user_type = "MANAGER"
                instance.is_staff = True
                instance.is_superuser = False
            elif "PORTAL_USER" in group_names:
                instance.user_type = "PORTAL_USER"
                instance.is_staff = False
                instance.is_superuser = False

            # Update DB directly to avoid triggering post_save signals recursion
            User.objects.filter(pk=instance.pk).update(
                user_type=instance.user_type,
                is_superuser=instance.is_superuser,
                is_staff=instance.is_staff
            )
        except Exception as e:
            logger.warning(f'Could not sync user roles and flags: {e}')
