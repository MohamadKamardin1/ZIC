from rest_framework.permissions import BasePermission

OL_PARAMETERS_MODULE = "ol_parameters"


class OLParameterPermission:
    VIEW = "ol_parameters.view"
    CREATE = "ol_parameters.create"
    UPDATE = "ol_parameters.update"
    DEACTIVATE = "ol_parameters.deactivate"
    CONFIGURE = "ol_parameters.configure"

    ACTION_TO_CODE = {
        "view": VIEW,
        "list": VIEW,
        "retrieve": VIEW,
        "create": CREATE,
        "update": UPDATE,
        "partial_update": UPDATE,
        "deactivate": DEACTIVATE,
        "destroy": DEACTIVATE,
        "configure": CONFIGURE,
    }

    @classmethod
    def code_for(cls, action):
        return cls.ACTION_TO_CODE.get((action or "").lower(), cls.VIEW)

    @classmethod
    def allowed_codes(cls):
        return tuple(cls.ACTION_TO_CODE.values())


def has_ol_parameter_permission(actor, action="view"):
    """Return whether an actor can perform an OL Parameters action."""
    if not actor or not getattr(actor, "is_authenticated", False):
        return False
    if getattr(actor, "is_superuser", False):
        return True
    code = OLParameterPermission.code_for(action)
    if hasattr(actor, "has_permission") and actor.has_permission(code):
        return True
    if action in {"view", "list", "retrieve"}:
        if hasattr(actor, "has_permission") and actor.has_permission(OLParameterPermission.CONFIGURE):
            return True
    module_action = code.rsplit(".", 1)[-1].upper()
    if action in {"view", "list", "retrieve"}:
        module_actions = (module_action, "CONFIGURE")
    else:
        module_actions = (module_action,)
    return bool(
        hasattr(actor, "has_module_permission")
        and any(actor.has_module_permission(OL_PARAMETERS_MODULE, candidate) for candidate in module_actions)
    )


class HasOLParameterPermission(BasePermission):
    """DRF permission using the view action's OL Parameters entitlement."""

    def has_permission(self, request, view):
        action = getattr(view, "action", None) or request.method.lower()
        return has_ol_parameter_permission(request.user, action)
