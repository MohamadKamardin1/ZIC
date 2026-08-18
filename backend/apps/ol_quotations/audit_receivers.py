from threading import local

from django.db.models.signals import post_save, pre_save

from apps.governance.services.audit_service import AuditService
from . import models

_state = local()


def tracked_models():
    return (
        models.OLQuotation,
        models.OLQuotationVersion,
        models.OLQuotationBenefit,
        models.OLQuotationFinancialSummary,
        models.OLQuotationDocument,
        models.OLQuotationProduct,
        models.OLQuotationPlanConfiguration,
        models.OLQuotationMember,
        models.OLQuotationInstallmentConfiguration,
        models.OLQuotationInstallmentRateRow,
        models.OLQuotationFundAllocation,
        models.OLQuotationRiderSelection,
        models.OLQuotationPaymentDetail,
        models.OLQuotationUnderwriting,
        models.OLQuotationBeneficiary,
    )


def capture_before_state(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        previous = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return
    cache = getattr(_state, "before", {})
    cache[(sender._meta.label, str(instance.pk))] = AuditService.snapshot(previous)
    _state.before = cache


def audit_quotation_material_change(sender, instance, created, **kwargs):
    cache = getattr(_state, "before", {})
    key = (sender._meta.label, str(instance.pk))
    before = cache.pop(key, {})
    _state.before = cache
    if created:
        AuditService.log_create(instance, reason="Ordinary Life quotation record created.")
        return
    after = AuditService.snapshot(instance)
    if before != after:
        AuditService.log_update(
            instance,
            before_state=before,
            changed_fields=AuditService.changed_fields(before, after),
            reason="Ordinary Life quotation record updated.",
        )


def register_receivers():
    for model in tracked_models():
        label = model._meta.label_lower
        pre_save.connect(
            capture_before_state,
            sender=model,
            dispatch_uid=f"ol-quotations-before-{label}",
        )
        post_save.connect(
            audit_quotation_material_change,
            sender=model,
            dispatch_uid=f"ol-quotations-audit-{label}",
        )
