from rest_framework.permissions import SAFE_METHODS, BasePermission

OL_POLICIES_MODULE = "ol_policies"
ACTIONS = (
    "view",
    "create",
    "service",
    "endorse",
    "cancel",
    "reinstate",
    "print",
    "configure",
)


class OLPolicyPermission:
    VIEW = "ol_policies.view"
    CREATE = "ol_policies.create"
    SERVICE = "ol_policies.service"
    ENDORSE = "ol_policies.endorse"
    CANCEL = "ol_policies.cancel"
    REINSTATE = "ol_policies.reinstate"
    PRINT = "ol_policies.print"
    CONFIGURE = "ol_policies.configure"

    ACTION_TO_CODE = {
        "list": VIEW,
        "retrieve": VIEW,
        "view": VIEW,
        "export": VIEW,
        "kpi": VIEW,
        "create": CREATE,
        "service": SERVICE,
        "endorse": ENDORSE,
        "cancel": CANCEL,
        "reinstate": REINSTATE,
        "print": PRINT,
        "configure": CONFIGURE,
    }

    @classmethod
    def code_for(cls, action):
        return cls.ACTION_TO_CODE.get((action or "").lower(), cls.VIEW)

    @classmethod
    def allowed_codes(cls):
        return tuple(f"{OL_POLICIES_MODULE}.{action}" for action in ACTIONS)


def has_ol_policy_permission(actor, action="view"):
    """Return whether an actor may perform an OL Policies action."""
    if not actor or not getattr(actor, "is_authenticated", False):
        return False
    if getattr(actor, "is_superuser", False):
        return True

    code = OLPolicyPermission.code_for(action)
    if hasattr(actor, "has_permission") and actor.has_permission(code):
        return True

    if action in {"list", "retrieve", "view", "export", "kpi"}:
        if hasattr(actor, "has_module_permission") and actor.has_module_permission(OL_POLICIES_MODULE, "READ"):
            return True

    module_action = code.rsplit(".", 1)[-1].upper()
    return bool(
        hasattr(actor, "has_module_permission")
        and any(
            actor.has_module_permission(OL_POLICIES_MODULE, candidate)
            for candidate in (module_action, "CONFIGURE")
        )
    )


class HasOLPolicyPermission(BasePermission):
    """DRF permission using the view action’s OL Policies entitlement."""

    def has_permission(self, request, view):
        action = getattr(view, "action", None)
        if not action:
            action = "view" if request.method in SAFE_METHODS else request.method.lower()
        return has_ol_policy_permission(request.user, action)
