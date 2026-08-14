import json
import logging
import threading
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from django.utils import timezone

from apps.governance.models import AuditLog

logger = logging.getLogger(__name__)

_thread_locals = threading.local()
_SENSITIVE_FIELDS = {
    "password",
    "otp_secret",
    "secret",
    "token",
    "access_token",
    "refresh_token",
    "backup_codes",
}


class AuditContext:
    """Request-scoped metadata used by all audit writers."""

    @staticmethod
    def set_request(request):
        _thread_locals.user = getattr(request, "user", None)
        _thread_locals.ip_address = AuditContext._get_client_ip(request)
        _thread_locals.user_agent = request.META.get("HTTP_USER_AGENT", "")[:500]
        correlation_id = getattr(request, "request_id", "") or request.META.get("HTTP_X_REQUEST_ID", "")
        _thread_locals.request_id = correlation_id[:100]
        _thread_locals.source_channel = AuditContext._source_channel(request)

    @staticmethod
    def clear():
        for name, value in (
            ("user", None),
            ("ip_address", None),
            ("user_agent", ""),
            ("request_id", ""),
            ("source_channel", AuditLog.SourceChannel.SYSTEM),
        ):
            setattr(_thread_locals, name, value)

    @staticmethod
    def get_context():
        return {
            "user": getattr(_thread_locals, "user", None),
            "ip_address": getattr(_thread_locals, "ip_address", None),
            "user_agent": getattr(_thread_locals, "user_agent", ""),
            "request_id": getattr(_thread_locals, "request_id", ""),
            "source_channel": getattr(
                _thread_locals, "source_channel", AuditLog.SourceChannel.SYSTEM
            ),
        }

    @staticmethod
    def _get_client_ip(request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")

    @staticmethod
    def _source_channel(request):
        requested = request.META.get("HTTP_X_SOURCE_CHANNEL", "").upper()
        allowed = {choice for choice, _label in AuditLog.SourceChannel.choices}
        if requested in allowed:
            return requested
        path = getattr(request, "path", "") or ""
        if path.startswith("/admin/"):
            return AuditLog.SourceChannel.ADMIN
        if path.startswith("/api/"):
            return AuditLog.SourceChannel.API
        return AuditLog.SourceChannel.WEB


class AuditService:
    """Central audit writer with compatibility for the legacy AuditLog contract."""

    @staticmethod
    def log(
        action_type,
        entity_type,
        entity_id,
        before_state=None,
        after_state=None,
        description="",
        entity_repr="",
        user=None,
        ip_address=None,
        user_agent="",
        request_id="",
        *,
        actor=None,
        action=None,
        app_label="",
        model_name="",
        object_id="",
        object_repr="",
        changed_fields=None,
        reason="",
        source_channel=None,
        request=None,
    ):
        context = AuditContext.get_context()
        actor = actor or user or context.get("user")
        if request is not None:
            AuditContext.set_request(request)
            context = AuditContext.get_context()
        if ip_address is None:
            ip_address = context.get("ip_address")
        if not user_agent:
            user_agent = context.get("user_agent", "")
        if not request_id:
            request_id = context.get("request_id", "")
        source_channel = source_channel or context.get(
            "source_channel", AuditLog.SourceChannel.SYSTEM
        )

        model_name = model_name or entity_type.rsplit(".", 1)[-1]
        app_label = app_label or (entity_type.split(".", 1)[0] if "." in entity_type else "")
        object_id = str(object_id or entity_id or "")
        object_repr = object_repr or entity_repr
        reason = reason or description
        action = action or action_type
        actor_type = AuditService._actor_type(actor, source_channel)
        legacy_entity_id = AuditService._uuid_or_none(entity_id or object_id)

        return AuditLog.objects.create(
            user=actor if actor and getattr(actor, "is_authenticated", False) else None,
            action_type=str(action_type)[:30],
            entity_type=str(entity_type)[:100],
            entity_id=legacy_entity_id,
            entity_repr=str(entity_repr or object_repr)[:255],
            before_state=AuditService._serialize(before_state),
            after_state=AuditService._serialize(after_state),
            description=str(description or reason)[:1000],
            ip_address=ip_address,
            user_agent=str(user_agent or "")[:500],
            request_id=str(request_id or "")[:50],
            actor_type=actor_type,
            action=str(action)[:50],
            app_label=str(app_label)[:100],
            model_name=str(model_name)[:100],
            object_id=object_id[:100],
            object_repr=str(object_repr or "")[:255],
            changed_fields=list(changed_fields or []),
            reason=str(reason or ""),
            source_channel=source_channel,
            correlation_id=str(request_id or "")[:100],
            created_at=timezone.now(),
        )

    @classmethod
    def log_create(cls, instance, actor=None, request=None, reason="", source_channel=None):
        state = cls.snapshot(instance)
        return cls.log(
            "CREATE",
            cls.entity_type(instance),
            instance.pk,
            after_state=state,
            entity_repr=str(instance),
            actor=actor,
            action="CREATE",
            reason=reason,
            source_channel=source_channel,
            request=request,
            **cls.model_metadata(instance),
        )

    @classmethod
    def log_update(
        cls,
        instance,
        before_state=None,
        actor=None,
        request=None,
        reason="",
        changed_fields=None,
        source_channel=None,
    ):
        after_state = cls.snapshot(instance)
        before_state = before_state or {}
        changed = changed_fields or cls.changed_fields(before_state, after_state)
        return cls.log(
            "UPDATE",
            cls.entity_type(instance),
            instance.pk,
            before_state=before_state,
            after_state=after_state,
            entity_repr=str(instance),
            actor=actor,
            action="UPDATE",
            changed_fields=changed,
            reason=reason,
            source_channel=source_channel,
            request=request,
            **cls.model_metadata(instance),
        )

    @classmethod
    def log_delete(cls, instance, actor=None, request=None, reason="", source_channel=None):
        return cls.log(
            "DELETE",
            cls.entity_type(instance),
            instance.pk,
            before_state=cls.snapshot(instance),
            entity_repr=str(instance),
            actor=actor,
            action="DELETE",
            reason=reason,
            source_channel=source_channel,
            request=request,
            **cls.model_metadata(instance),
        )

    @classmethod
    def log_soft_delete(cls, instance, before_state=None, actor=None, request=None, reason="", source_channel=None):
        return cls.log(
            "DEACTIVATE",
            cls.entity_type(instance),
            instance.pk,
            before_state=before_state or {},
            after_state=cls.snapshot(instance),
            entity_repr=str(instance),
            actor=actor,
            action="SOFT_DELETE",
            changed_fields=["is_active", "is_deleted"],
            reason=reason,
            source_channel=source_channel,
            request=request,
            **cls.model_metadata(instance),
        )

    @classmethod
    def log_action(
        cls,
        action,
        instance,
        actor=None,
        request=None,
        before_state=None,
        after_state=None,
        reason="",
        changed_fields=None,
        source_channel=None,
    ):
        return cls.log(
            str(action).upper()[:30],
            cls.entity_type(instance),
            instance.pk,
            before_state=before_state,
            after_state=after_state,
            entity_repr=str(instance),
            actor=actor,
            action=action,
            changed_fields=changed_fields,
            reason=reason,
            source_channel=source_channel,
            request=request,
            **cls.model_metadata(instance),
        )

    @staticmethod
    def entity_type(instance):
        # Preserve the legacy entity_type contract; app_label/model_name provide
        # the normalized central-audit provenance fields.
        return instance._meta.model_name

    @staticmethod
    def model_metadata(instance):
        return {
            "app_label": instance._meta.app_label,
            "model_name": instance._meta.model_name,
            "object_id": instance.pk,
            "object_repr": str(instance),
        }

    @staticmethod
    def snapshot(instance):
        data = {}
        for field in instance._meta.concrete_fields:
            name = field.name
            if name in _SENSITIVE_FIELDS:
                continue
            value = getattr(instance, name, None)
            if field.is_relation and value is not None:
                value = getattr(instance, f"{name}_id", value)
            data[name] = AuditService._json_value(value)
        return data

    @staticmethod
    def changed_fields(before_state, after_state):
        return sorted(
            key for key in set(before_state or {}) | set(after_state or {})
            if (before_state or {}).get(key) != (after_state or {}).get(key)
        )

    @staticmethod
    def _actor_type(actor, source_channel):
        if not actor or not getattr(actor, "is_authenticated", False):
            return AuditLog.ActorType.SYSTEM if source_channel == AuditLog.SourceChannel.SYSTEM else AuditLog.ActorType.ANONYMOUS
        return AuditLog.ActorType.USER

    @staticmethod
    def _uuid_or_none(value):
        try:
            return UUID(str(value)) if value else None
        except (TypeError, ValueError, AttributeError):
            return None

    @staticmethod
    def _serialize(value):
        if value is None:
            return None
        try:
            return json.loads(json.dumps(value, default=str))
        except (TypeError, ValueError):
            return {"value": str(value)}

    @staticmethod
    def _json_value(value):
        if isinstance(value, (UUID, datetime, date, Decimal)):
            return str(value)
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        return AuditService._serialize(value)

    @staticmethod
    def log_model_action(action, instance, before_state=None, after_state=None, description=""):
        return AuditService.log_action(
            action=action,
            instance=instance,
            before_state=before_state,
            after_state=after_state,
            reason=description,
        )

    @staticmethod
    def _legacy_log(
        action_type,
        entity_type,
        entity_id,
        before_state=None,
        after_state=None,
        description="",
        entity_repr="",
        user=None,
        ip_address=None,
        user_agent="",
        request_id="",
    ):
        return AuditService.log(
            action_type=action_type,
            entity_type=entity_type,
            entity_id=entity_id,
            before_state=before_state,
            after_state=after_state,
            description=description,
            entity_repr=entity_repr,
            user=user,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
        )
