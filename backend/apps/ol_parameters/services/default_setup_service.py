from django.core.exceptions import PermissionDenied
from django.db import transaction

from apps.governance.services.audit_service import AuditService

from ..audit_receivers import audit_suppressed
from ..permissions import has_ol_parameter_permission


class OLDefaultSetupService:
    """Transactional mutation service for the four OL Default Setup tables."""

    @staticmethod
    def _require(actor, action):
        if not has_ol_parameter_permission(actor, action):
            raise PermissionDenied(f"Missing OL Parameters permission: ol_parameters.{action}")

    @staticmethod
    def _assign_actor(instance, actor, *, creating=False):
        if creating and actor is not None:
            instance.created_by = actor
        if actor is not None:
            instance.updated_by = actor

    @classmethod
    @transaction.atomic
    def create(
        cls,
        *,
        model,
        actor,
        data,
        request=None,
        audit_reason=None,
        source_channel=None,
    ):
        cls._require(actor, "create")
        instance = model(**data)
        cls._assign_actor(instance, actor, creating=True)
        instance.full_clean()
        with audit_suppressed():
            instance.save()
        AuditService.log_create(
            instance,
            actor=actor,
            request=request,
            reason=audit_reason or f"OL Default Setup {model._meta.verbose_name} created.",
            source_channel=source_channel,
        )
        return instance

    @classmethod
    @transaction.atomic
    def update(cls, *, model, actor, instance, data, request=None):
        cls._require(actor, "update")
        before_state = AuditService.snapshot(instance)
        for field, value in data.items():
            setattr(instance, field, value)
        cls._assign_actor(instance, actor)
        instance.full_clean()
        with audit_suppressed():
            instance.save()
        after_state = AuditService.snapshot(instance)
        if before_state != after_state:
            AuditService.log_update(
                instance,
                before_state=before_state,
                changed_fields=AuditService.changed_fields(before_state, after_state),
                actor=actor,
                request=request,
                reason=f"OL Default Setup {model._meta.verbose_name} updated.",
            )
        return instance

    @classmethod
    @transaction.atomic
    def deactivate(cls, *, actor, instance, request=None):
        cls._require(actor, "deactivate")
        if not instance.is_active:
            return instance
        before_state = AuditService.snapshot(instance)
        instance.is_active = False
        cls._assign_actor(instance, actor)
        with audit_suppressed():
            instance.save(update_fields=["is_active", "updated_by", "updated_at"])
        AuditService.log_action(
            "DEACTIVATE",
            instance,
            before_state=before_state,
            after_state=AuditService.snapshot(instance),
            changed_fields=["is_active", "updated_by", "updated_at"],
            actor=actor,
            request=request,
            reason=f"OL Default Setup {instance._meta.verbose_name} deactivated.",
        )
        return instance
