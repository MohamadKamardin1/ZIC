import threading
from contextlib import contextmanager

from django.db.models.signals import post_save, pre_save

from apps.governance.services.audit_service import AuditContext, AuditService

from .models import OLLoan, OLLoanInterestAccrual, OLLoanOffset, OLLoanRepayment, OLLoanSchedule


AUDITED_MODELS = (OLLoan, OLLoanSchedule, OLLoanRepayment, OLLoanInterestAccrual, OLLoanOffset)
_state = threading.local()


def _is_suppressed():
    return bool(getattr(_state, "suppressed", False))


@contextmanager
def audit_suppressed():
    previous = _is_suppressed()
    _state.suppressed = True
    try:
        yield
    finally:
        _state.suppressed = previous


def _actor_for(instance):
    if getattr(instance, "updated_by_id", None):
        return instance.updated_by
    if getattr(instance, "created_by_id", None):
        return instance.created_by
    return AuditContext.get_context().get("user")


def _channel_for(instance):
    return getattr(instance, "source_channel", None) or AuditContext.get_context().get("source_channel")


def _capture_before_state(sender, instance, **kwargs):
    if _is_suppressed() or not instance.pk:
        return
    try:
        previous = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        previous = None
    if previous is not None:
        instance._ol_loans_before_state = AuditService.snapshot(previous)


def _audit_save(sender, instance, created, **kwargs):
    if _is_suppressed():
        return
    before = getattr(instance, "_ol_loans_before_state", None)
    actor = _actor_for(instance)
    channel = _channel_for(instance)
    label = str(instance._meta.verbose_name or "OL Loan record").replace("_", " ")
    if created:
        AuditService.log_create(
            instance,
            actor=actor,
            reason=f"{label} created.",
            source_channel=channel,
        )
    elif before is not None:
        after = AuditService.snapshot(instance)
        if before != after:
            AuditService.log_update(
                instance,
                before_state=before,
                actor=actor,
                changed_fields=AuditService.changed_fields(before, after),
                reason=f"{label} updated.",
                source_channel=channel,
            )
    if hasattr(instance, "_ol_loans_before_state"):
        delattr(instance, "_ol_loans_before_state")


def register_receivers():
    for model in AUDITED_MODELS:
        pre_save.connect(
            _capture_before_state,
            sender=model,
            dispatch_uid=f"ol_loans_{model.__name__.lower()}_before_save",
        )
        post_save.connect(
            _audit_save,
            sender=model,
            dispatch_uid=f"ol_loans_{model.__name__.lower()}_after_save",
        )
