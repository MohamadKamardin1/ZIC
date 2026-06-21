import logging

from celery import shared_task
from django.utils import timezone
from django.conf import settings
from datetime import timedelta

logger = logging.getLogger('apps.users.tasks')


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_otp_email(self, user_email, otp_code, otp_type):
    try:
        logger.info(f'[EMAIL OTP] To: {user_email} | Type: {otp_type} | Code: {otp_code}')
        return {'success': True, 'email': user_email, 'otp_type': otp_type}
    except Exception as exc:
        logger.error(f'Failed to send OTP email to {user_email}: {exc}')
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_otp_sms(self, phone_number, otp_code, otp_type):
    try:
        logger.info(f'[SMS OTP] To: {phone_number} | Type: {otp_type} | Code: {otp_code}')
        return {'success': True, 'phone': phone_number, 'otp_type': otp_type}
    except Exception as exc:
        logger.error(f'Failed to send OTP SMS to {phone_number}: {exc}')
        raise self.retry(exc=exc)


@shared_task
def cleanup_expired_sessions():
    from .models import UserSession
    cutoff = timezone.now() - timedelta(
        hours=getattr(settings, 'SESSION_EXPIRY_HOURS', 24)
    )
    expired = UserSession.objects.filter(
        last_activity__lt=cutoff, is_active=True
    )
    count = expired.update(is_active=False)
    if count:
        logger.info(f'Cleaned up {count} expired sessions')
    return count


@shared_task
def cleanup_expired_otps():
    from .models import UserOTP
    expired = UserOTP.objects.filter(
        expires_at__lt=timezone.now(), is_used=False
    )
    count = expired.update(is_used=True)
    if count:
        logger.info(f'Cleaned up {count} expired OTPs')
    return count


@shared_task
def password_expiry_reminder():
    from .models import User
    from django.conf import settings
    expiry_days = getattr(settings, 'PASSWORD_EXPIRY_DAYS', 90)
    reminder_days = getattr(settings, 'PASSWORD_EXPIRY_REMINDER_DAYS', 7)
    threshold = timezone.now() - timedelta(days=expiry_days - reminder_days)
    users = User.objects.filter(
        password_changed_at__lt=threshold,
        last_password_change_reminded__isnull=True,
        is_active=True,
    )
    count = 0
    for user in users:
        logger.info(f'[PASSWORD EXPIRY REMINDER] User: {user.email}')
        user.last_password_change_reminded = timezone.now()
        user.save(update_fields=['last_password_change_reminded'])
        count += 1
    if count:
        logger.info(f'Sent password expiry reminders to {count} users')
    return count


@shared_task
def send_welcome_email(user_email, username):
    try:
        logger.info(f'[WELCOME EMAIL] To: {user_email} | User: {username}')
        return {'success': True, 'email': user_email}
    except Exception as exc:
        logger.error(f'Failed to send welcome email to {user_email}: {exc}')
        return {'success': False, 'email': user_email}
