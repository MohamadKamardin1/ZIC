"""Front Office Receipts — receipt numbering service.

Branch-aware, concurrency-safe receipt number generation backed by
``ReceiptNumberingRule``. The rule carries the prefix, padding, and sequence
counter; this service serializes increments (in-process lock + row lock) so a
number is never issued twice, and it raises a structured ``RECEIPT_PARAMETER_MISSING``
error when no active rule is configured.
"""

import threading
from datetime import date

from django.db import models, transaction

from apps.front_office.receipts.config_models import ReceiptNumberingRule, ResetFrequency
from apps.front_office.receipts.errors import parameter_missing

NUMBERING_NAVIGATION = "Front Office Parameters > Receipt Numbering"

# Serializes the read-increment-write critical section in-process. The row lock
# (``select_for_update``) covers cross-process production concurrency; SQLite
# test/single-host deployments rely on this lock to keep increments atomic.
_number_lock = threading.Lock()


def _period_key(value, frequency):
    """Return the reset-period key for a date under a frequency (None for NEVER)."""
    if not value or frequency == ResetFrequency.NEVER:
        return None
    if frequency == ResetFrequency.YEARLY:
        return f"{value.year}"
    if frequency == ResetFrequency.MONTHLY:
        return f"{value.year}-{value.month:02d}"
    if frequency == ResetFrequency.DAILY:
        return f"{value.year}-{value.month:02d}-{value.day:02d}"
    return None


class ReceiptNumberingService:
    @staticmethod
    def resolve_rule(branch_id=None):
        """Active effective rule: branch-specific first, then the generic rule."""
        today = date.today()
        queryset = ReceiptNumberingRule.objects.filter(is_active=True).filter(
            models.Q(effective_from__isnull=True) | models.Q(effective_from__lte=today)
        ).filter(
            models.Q(effective_to__isnull=True) | models.Q(effective_to__gte=today)
        )
        if branch_id:
            branch_rule = (
                queryset.filter(branch_id=branch_id)
                .order_by("-effective_from", "-created_at")
                .first()
            )
            if branch_rule:
                return branch_rule
        rule = (
            queryset.filter(branch__isnull=True)
            .order_by("-effective_from", "-created_at")
            .first()
        )
        if not rule:
            raise parameter_missing("RECEIPT_NUMBERING_RULE", navigation_path=NUMBERING_NAVIGATION)
        return rule

    @classmethod
    def next_number(cls, branch_id=None):
        """Generate the next receipt number for a branch (default rule when no branch)."""
        with _number_lock:
            return cls._next_number_locked(branch_id)

    @classmethod
    def _next_number_locked(cls, branch_id=None):
        rule = cls.resolve_rule(branch_id)
        with transaction.atomic():
            locked = ReceiptNumberingRule.objects.select_for_update().get(pk=rule.pk)
            cls._maybe_reset(locked)
            number = cls._format_number(locked)
            locked.next_sequence = (locked.next_sequence or 1) + 1
            locked.save(update_fields=["next_sequence", "last_reset_at", "updated_at"])
        return number

    @staticmethod
    def _maybe_reset(rule):
        if rule.reset_frequency == ResetFrequency.NEVER:
            return
        today = date.today()
        current_key = _period_key(today, rule.reset_frequency)
        last_key = _period_key(rule.last_reset_at, rule.reset_frequency)
        if current_key != last_key:
            rule.next_sequence = 1
            rule.last_reset_at = today

    @staticmethod
    def _format_number(rule):
        now = date.today()
        sequence = rule.next_sequence or 1
        padded = str(sequence).zfill(rule.sequence_padding or 6)
        return f"{rule.prefix}-{now.year}-{padded}"
