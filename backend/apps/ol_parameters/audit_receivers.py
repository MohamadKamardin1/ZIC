import threading
from contextlib import contextmanager

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from apps.governance.services.audit_service import AuditService

from .models import (
    OLAnticipatedEndowmentInstallmentRate,
    OLBeneficialType,
    OLComputationApproach,
    OLDefaultSystemParameter,
    OLGracePeriod,
    OLMaturityClaimSetup,
    OLMemberCoverConfiguration,
    OLOverrideCommissionSetup,
    OLPaidUpRate,
    OLPaidUpSetup,
    OLCommitmentStatus,
    OLSurrenderSetup,
    OLSurrenderValueRate,
    OLParameterTableRegistry,
    OLPolicyRenewalStatus,
    OLPolicyStatus,
)


AUDITED_MODELS = (
    OLParameterTableRegistry,
    OLDefaultSystemParameter,
    OLOverrideCommissionSetup,
    OLComputationApproach,
    OLMaturityClaimSetup,
    OLAnticipatedEndowmentInstallmentRate,
    OLGracePeriod,
    OLPolicyStatus,
    OLPolicyRenewalStatus,
    OLBeneficialType,
    OLMemberCoverConfiguration,
    OLSurrenderSetup,
    OLPaidUpSetup,
    OLSurrenderValueRate,
    OLPaidUpRate,
    OLCommitmentStatus,
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


def _capture_before_state(sender, instance, **kwargs):
    if _is_suppressed() or not instance.pk:
        return
    try:
        previous = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        previous = None
    if previous is not None:
        instance._ol_parameters_before_state = AuditService.snapshot(previous)


def _audit_save(sender, instance, created, **kwargs):
    if _is_suppressed():
        return
    before = getattr(instance, "_ol_parameters_before_state", None)
    label = sender._meta.verbose_name.replace("_", " ")
    if created:
        AuditService.log_create(instance, reason=f"OL Parameters {label} created.")
    elif before is not None:
        after = AuditService.snapshot(instance)
        if before != after:
            AuditService.log_update(
                instance,
                before_state=before,
                changed_fields=AuditService.changed_fields(before, after),
                reason=f"OL Parameters {label} updated.",
            )
    if hasattr(instance, "_ol_parameters_before_state"):
        delattr(instance, "_ol_parameters_before_state")


for _model in AUDITED_MODELS:
    pre_save.connect(
        _capture_before_state,
        sender=_model,
        dispatch_uid=f"ol_parameters_{_model.__name__.lower()}_before_save",
    )
    post_save.connect(
        _audit_save,
        sender=_model,
        dispatch_uid=f"ol_parameters_{_model.__name__.lower()}_after_save",
    )


def register_receivers():
    """Signals are connected by decorators; retained as an explicit app hook."""
    return None
