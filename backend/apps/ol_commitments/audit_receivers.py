import threading
from contextlib import contextmanager

from django.db.models.signals import post_save, pre_save

from apps.governance.services.audit_service import AuditContext, AuditService

from .models import OLCommitment, OLCommitmentAllocation, OLCommitmentNotificationLog

AUDITED_MODELS = (
    OLCommitment,
    OLCommitmentAllocation,
    OLCommitmentNotificationLog,
)

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
    if hasattr(instance, "updated_by") and instance.updated_by_id:
        return instance.updated_by
    if hasattr(instance, "created_by") and instance.created_by_id:
        return instance.created_by
    return AuditContext.get_context().get("user")


def _channel_for(instance):
    return getattr(instance, "source_channel", None) or AuditContext.get_context().get("source_channel")


def _reason_for(instance, existing=""):
    if existing:
        return existing
    reason_code = getattr(instance, "reason_code", "") or ""
    reason_text = getattr(instance, "reason_text", "") or ""
    label = str(instance._meta.verbose_name or "").replace("_", " ")
    if reason_text:
        return f"{label}: {reason_text}"
    if reason_code:
        return f"{label} changed with reason code {reason_code}."
    return f"{label} saved."


def _capture_before_state(sender, instance, **kwargs):
    if _is_suppressed() or not instance.pk:
        return
    try:
        previous = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        previous = None
    if previous is not None:
        instance._ol_commitments_before_state = AuditService.snapshot(previous)


def _audit_save(sender, instance, created, **kwargs):
    if _is_suppressed():
        return
    before = getattr(instance, "_ol_commitments_before_state", None)
    actor = _actor_for(instance)
    channel = _channel_for(instance)
    label = str(instance._meta.verbose_name or "").replace("_", " ")
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
                reason=_reason_for(instance),
                source_channel=channel,
            )
    if hasattr(instance, "_ol_commitments_before_state"):
        delattr(instance, "_ol_commitments_before_state")


for _model in AUDITED_MODELS:
    pre_save.connect(
        _capture_before_state,
        sender=_model,
        dispatch_uid=f"ol_commitments_{_model.__name__.lower()}_before_save",
    )
    post_save.connect(
        _audit_save,
        sender=_model,
        dispatch_uid=f"ol_commitments_{_model.__name__.lower()}_after_save",
    )


def register_receivers():
    """Signals are connected by the module import; explicit app hook retained."""
    return None
