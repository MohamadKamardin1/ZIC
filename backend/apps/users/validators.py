import re
import hashlib

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
    def __init__(self, history_count=5):
        self.history_count = history_count

    def validate(self, password, user=None):
        if user is None:
            return
        if user.pk is None:
            return

        from .models import UserActivityLog
        recent_changes = UserActivityLog.objects.filter(
            user=user,
            action_type='PASSWORD_CHANGE',
        ).order_by('-timestamp')[:self.history_count]

        for log in recent_changes:
            if log.details and 'password_hash' in log.details:
                old_hash = log.details['password_hash']
                if hashlib.sha256(password.encode()).hexdigest() == old_hash:
                    raise ValidationError(
                        _('You cannot reuse a recently used password.'),
                        code='password_reused',
                    )

    def get_help_text(self):
        return _(f'You cannot reuse any of your last {self.history_count} passwords.')
