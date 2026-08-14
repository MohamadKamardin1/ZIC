import re

from django.conf import settings
from django.contrib.auth.hashers import check_password
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class ComplexPasswordValidator:
    def validate(self, password, user=None):
        if not re.search(r'[A-Z]', password):
            raise ValidationError(
                _('Password must contain at least one uppercase letter.'),
                code='password_no_upper',
            )
        if not re.search(r'[a-z]', password):
            raise ValidationError(
                _('Password must contain at least one lowercase letter.'),
                code='password_no_lower',
            )
        if not re.search(r'[0-9]', password):
            raise ValidationError(
                _('Password must contain at least one number.'),
                code='password_no_number',
            )
        if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\;/]', password):
            raise ValidationError(
                _('Password must contain at least one special character.'),
                code='password_no_special',
            )

    def get_help_text(self):
        return _(
            'Password must contain at least one uppercase letter, '
            'one lowercase letter, one number, and one special character.'
        )


class PasswordHistoryValidator:
    def __init__(self, history_count=None):
        self.history_count = history_count or getattr(settings, 'PASSWORD_HISTORY_COUNT', 5)

    def validate(self, password, user=None):
        if user is None or user.pk is None:
            return

        from .models import UserPasswordHistory

        recent_changes = UserPasswordHistory.objects.filter(
            user=user,
        ).order_by('-created_at')[:self.history_count]

        if any(check_password(password, password_hash) for password_hash in recent_changes.values_list('password_hash', flat=True)):
            raise ValidationError(
                _('You cannot reuse a recently used password.'),
                code='password_reused',
            )

    def get_help_text(self):
        return _(f'You cannot reuse any of your last {self.history_count} passwords.')
