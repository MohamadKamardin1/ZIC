from rest_framework.permissions import SAFE_METHODS, BasePermission


OL_CLAIMS_MODULE = "ol_claims"
ACTIONS = (
    "view",
    "register",
    "assess",
    "requisition",
    "approve",
    "settle",
    "cancel",
    "print",
)


class OLClaimPermission:
    VIEW = "ol_claims.view"
    REGISTER = "ol_claims.register"
    ASSESS = "ol_claims.assess"
    REQUISITION = "ol_claims.requisition"
    APPROVE = "ol_claims.approve"
    SETTLE = "ol_claims.settle"
    CANCEL = "ol_claims.cancel"
    PRINT = "ol_claims.print"

    ACTION_TO_CODE = {
        "list": VIEW,
        "retrieve": VIEW,
        "view": VIEW,
        "export": VIEW,
        "kpi": VIEW,
        "register": REGISTER,
        "create": REGISTER,
        "assess": ASSESS,
        "requisition": REQUISITION,
        "approve": APPROVE,
        "settle": SETTLE,
        "cancel": CANCEL,
        "print": PRINT,
    }

    @classmethod
    def code_for(cls, action):
        action = (action or "view").lower()
        return cls.ACTION_TO_CODE.get(action, f"{OL_CLAIMS_MODULE}.{action}")

    @classmethod
    def allowed_codes(cls):
        return tuple(f"{OL_CLAIMS_MODULE}.{action}" for action in ACTIONS)


def has_ol_claim_permission(actor, action="view"):
    """Return whether an actor may perform an OL Claims action."""
    if not actor or not getattr(actor, "is_authenticated", False):
        return False
    if getattr(actor, "is_superuser", False):
        return True

    code = OLClaimPermission.code_for(action)
    if hasattr(actor, "has_permission") and actor.has_permission(code):
        return True

    if action in {"list", "retrieve", "view", "export", "kpi"}:
        return bool(
            hasattr(actor, "has_module_permission")
            and actor.has_module_permission(OL_CLAIMS_MODULE, "READ")
        )

    module_action = code.rsplit(".", 1)[-1].upper()
    return bool(
        hasattr(actor, "has_module_permission")
        and any(
            actor.has_module_permission(OL_CLAIMS_MODULE, candidate)
            for candidate in (module_action, "CONFIGURE")
        )
    )


class HasOLClaimPermission(BasePermission):
    """Authorize an endpoint using the view action's OL Claims entitlement."""

    def has_permission(self, request, view):
        action = getattr(view, "action", None)
        if not action:
            action = "view" if request.method in SAFE_METHODS else request.method.lower()
        return has_ol_claim_permission(request.user, action)
