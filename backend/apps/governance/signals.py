from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from apps.governance.services.audit_service import AuditService

AUDIT_MODELS = {}

_ALLOWED_ACTIONS = ["CREATE", "UPDATE", "DELETE"]


def _extract_state(instance):
    state = {}
    for field in instance._meta.get_fields():
        if hasattr(field, "name"):
            try:
                value = getattr(instance, field.name)
                if hasattr(value, "pk"):
                    state[field.name] = str(value.pk)
                elif hasattr(value, "isoformat"):
                    state[field.name] = value.isoformat() if value else None
                else:
                    state[field.name] = value
            except Exception:
                state[field.name] = None
    return state


def _clean_model_action(action):
    if action == "CREATE":
        return "CREATE"
    if action == "UPDATE":
        return "UPDATE"
    return "DELETE"


def register_audit_model(model_class):
    AUDIT_MODELS[model_class._meta.label] = model_class
    _pre_delete_connector(model_class)
    _post_save_connector(model_class)


def _post_save_connector(model_class):
    def handler(sender, instance, created, **kwargs):
        action = "CREATE" if created else "UPDATE"
        state = _extract_state(instance)
        before = kwargs.pop("_before_state", None)
        AuditService.log_model_action(
            action=action,
            instance=instance,
            before_state=before,
            after_state=state,
        )

    post_save.connect(handler, sender=model_class, weak=False)
    setattr(model_class, "_audit_post_save", handler)


def _pre_delete_connector(model_class):
    def handler(sender, instance, **kwargs):
        state = _extract_state(instance)
        AuditService.log_model_action(
            action="DELETE",
            instance=instance,
            before_state=state,
            after_state=None,
        )

    pre_delete.connect(handler, sender=model_class, weak=False)
    setattr(model_class, "_audit_pre_delete", handler)


def auto_audit_model(model_class):
    register_audit_model(model_class)
    return model_class
