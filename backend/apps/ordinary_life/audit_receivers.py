from threading import local

from django.db.models.signals import post_save, pre_save

from apps.governance.services.audit_service import AuditService
from apps.ordinary_life import models

_state = local()


def tracked_models():
    return (
        models.OLProduct,
        models.OLProductVersion,
        models.OLPlan,
        models.OLBenefit,
        models.OLRider,
        models.OLProductBenefit,
        models.OLProductRider,
        models.OLRateBand,
        models.OLGracePeriod,
        models.OLReinstatementWindow,
        models.OLSurrenderSetup,
        models.OLPaidUpSetup,
    )


def capture_before_state(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        previous = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return
    before = AuditService.snapshot(previous)
    cache = getattr(_state, "before", {})
    cache[(sender._meta.label, str(instance.pk))] = before
    _state.before = cache


def audit_material_configuration(sender, instance, created, **kwargs):
    cache = getattr(_state, "before", {})
    key = (sender._meta.label, str(instance.pk))
    before = cache.pop(key, {})
    _state.before = cache
    if created:
        AuditService.log_create(instance, reason="Ordinary Life reference configuration created.")
        return
    after = AuditService.snapshot(instance)
    if before != after:
        AuditService.log_update(
            instance,
            before_state=before,
            changed_fields=AuditService.changed_fields(before, after),
            reason="Ordinary Life reference configuration updated.",
        )


def register_receivers():
    for model in tracked_models():
        label = model._meta.label_lower
        pre_save.connect(capture_before_state, sender=model, dispatch_uid=f"ordinary-life-before-{label}")
        post_save.connect(audit_material_configuration, sender=model, dispatch_uid=f"ordinary-life-audit-{label}")
