"""Permission helpers for the GC Parameters bounded context.

The GC Parameters context lives inside the ``group_credit`` app (Layer 1 —
Setup & Parameters) but exposes its own logical permission namespace
``gc_parameters`` so entitlements read naturally regardless of the physical
Django app that hosts the models.
"""

from rest_framework.permissions import BasePermission

GC_PARAMETERS_MODULE = "gc_parameters"


class GCParameterPermission:
    VIEW = "gc_parameters.view"
    MANAGE = "gc_parameters.manage"
    CONFIGURE = "gc_parameters.configure"

    ACTION_TO_CODE = {
        "view": VIEW,
        "list": VIEW,
        "retrieve": VIEW,
        "create": MANAGE,
        "update": MANAGE,
        "partial_update": MANAGE,
        "deactivate": CONFIGURE,
        "destroy": CONFIGURE,
        "configure": CONFIGURE,
    }

    @classmethod
    def code_for(cls, action):
        return cls.ACTION_TO_CODE.get((action or "").lower(), cls.VIEW)

    @classmethod
    def allowed_codes(cls):
        return tuple(cls.ACTION_TO_CODE.values())


def has_gc_parameter_permission(actor, action="view"):
    """Return whether an actor can perform a GC Parameters action."""
    if not actor or not getattr(actor, "is_authenticated", False):
        return False
    if getattr(actor, "is_superuser", False):
        return True
    code = GCParameterPermission.code_for(action)
    if hasattr(actor, "has_permission") and actor.has_permission(code):
        return True
    if action in {"view", "list", "retrieve"}:
        if hasattr(actor, "has_permission") and actor.has_permission(GCParameterPermission.CONFIGURE):
            return True
    module_action = code.rsplit(".", 1)[-1].upper()
    if action in {"view", "list", "retrieve"}:
        module_actions = (module_action, "CONFIGURE")
    else:
        module_actions = (module_action,)
    return bool(
        hasattr(actor, "has_module_permission")
        and any(actor.has_module_permission(GC_PARAMETERS_MODULE, candidate) for candidate in module_actions)
    )


class HasGCParameterPermission(BasePermission):
    """DRF permission using the view action's GC Parameters entitlement."""

    def has_permission(self, request, view):
        action = getattr(view, "action", None) or request.method.lower()
        return has_gc_parameter_permission(request.user, action)
