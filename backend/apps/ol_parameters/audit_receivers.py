import threading
from contextlib import contextmanager

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from apps.governance.services.audit_service import AuditService

from .models import OLParameterTableRegistry


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


@receiver(pre_save, sender=OLParameterTableRegistry, dispatch_uid="ol_parameters_registry_before_save")
def capture_before_state(sender, instance, **kwargs):
    if _is_suppressed() or not instance.pk:
        return
    try:
        previous = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        previous = None
    if previous is not None:
        instance._ol_parameters_before_state = AuditService.snapshot(previous)


@receiver(post_save, sender=OLParameterTableRegistry, dispatch_uid="ol_parameters_registry_after_save")
def audit_registry_save(sender, instance, created, **kwargs):
    if _is_suppressed():
        return
    before = getattr(instance, "_ol_parameters_before_state", None)
    if created:
        AuditService.log_create(instance, reason="OL Parameters table registry created.")
    elif before is not None:
        after = AuditService.snapshot(instance)
        if before != after:
            AuditService.log_update(
                instance,
                before_state=before,
                changed_fields=AuditService.changed_fields(before, after),
                reason="OL Parameters table registry updated.",
            )
    if hasattr(instance, "_ol_parameters_before_state"):
        delattr(instance, "_ol_parameters_before_state")


def register_receivers():
    """Signals are connected by decorators; retained as an explicit app hook."""
    return None
