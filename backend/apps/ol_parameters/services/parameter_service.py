from django.core.exceptions import PermissionDenied
from django.db import transaction

from apps.governance.services.audit_service import AuditService

from ..audit_receivers import audit_suppressed
from ..models import OLParameterTableRegistry
from ..permissions import has_ol_parameter_permission


class OLParameterService:
    """Application service for controlled mutations of OL parameter metadata."""

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
    def create_registry(cls, *, actor, data, request=None):
        cls._require(actor, "create")
        instance = OLParameterTableRegistry(**data)
        cls._assign_actor(instance, actor, creating=True)
        with audit_suppressed():
            instance.save()
        AuditService.log_create(
            instance,
            actor=actor,
            request=request,
            reason="OL Parameters table registry created.",
        )
        return instance

    @classmethod
    @transaction.atomic
    def update_registry(cls, *, actor, instance, data, request=None):
        cls._require(actor, "update")
        before_state = AuditService.snapshot(instance)
        for field, value in data.items():
            setattr(instance, field, value)
        cls._assign_actor(instance, actor)
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
                reason="OL Parameters table registry updated.",
            )
        return instance

    @classmethod
    @transaction.atomic
    def deactivate_registry(cls, *, actor, instance, request=None):
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
            reason="OL Parameters table registry deactivated.",
        )
        return instance
