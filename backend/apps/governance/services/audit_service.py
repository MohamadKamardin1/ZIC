import json
import threading
import logging

from django.utils import timezone

from apps.governance.models import AuditLog

logger = logging.getLogger(__name__)

_thread_locals = threading.local()


class AuditContext:
    @staticmethod
    def set_request(request):
        _thread_locals.user = getattr(request, "user", None)
        _thread_locals.ip_address = AuditContext._get_client_ip(request)
        _thread_locals.user_agent = request.META.get("HTTP_USER_AGENT", "")[:500]
        _thread_locals.request_id = getattr(request, "request_id", "")

    @staticmethod
    def clear():
        _thread_locals.user = None
        _thread_locals.ip_address = None
        _thread_locals.user_agent = ""
        _thread_locals.request_id = ""

    @staticmethod
    def get_context():
        return {
            "user": getattr(_thread_locals, "user", None),
            "ip_address": getattr(_thread_locals, "ip_address", None),
            "user_agent": getattr(_thread_locals, "user_agent", ""),
            "request_id": getattr(_thread_locals, "request_id", ""),
        }

    @staticmethod
    def _get_client_ip(request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")


class AuditService:

    @staticmethod
    def log(
        action_type, entity_type, entity_id,
        before_state=None, after_state=None,
        description="", entity_repr="",
        user=None, ip_address=None, user_agent="", request_id="",
    ):
        ctx = AuditContext.get_context()
        if not user:
            user = ctx.get("user")
        if not ip_address:
            ip_address = ctx.get("ip_address")
        if not user_agent:
            user_agent = ctx.get("user_agent", "")
        if not request_id:
            request_id = ctx.get("request_id", "")

        log_entry = AuditLog.objects.create(
            user=user if user and not user.is_anonymous else None,
            action_type=action_type,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_repr=str(entity_repr)[:255] if entity_repr else "",
            before_state=AuditService._serialize(before_state),
            after_state=AuditService._serialize(after_state),
            description=str(description)[:1000] if description else "",
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
        )
        logger.debug(
            "Audit: %s %s[%s] by %s",
            action_type, entity_type, entity_id,
            user.email if user and not user.is_anonymous else "system",
        )
        return log_entry

    @staticmethod
    def log_model_action(action, instance, before_state=None, after_state=None, description=""):
        return AuditService.log(
            action_type=action,
            entity_type=instance._meta.model_name,
            entity_id=instance.pk,
            entity_repr=str(instance),
            before_state=before_state,
            after_state=after_state,
            description=description,
        )

    @staticmethod
    def _serialize(value):
        if value is None:
            return None
        if isinstance(value, dict):
            return value
        if hasattr(value, "__dict__"):
            return {k: str(v) for k, v in value.__dict__.items() if not k.startswith("_")}
        try:
            return json.loads(json.dumps(value, default=str))
        except (TypeError, ValueError):
            return {"value": str(value)}
