from rest_framework.permissions import BasePermission


OL_LOANS_MODULE = "ol_loans"
ACTIONS = ("view", "request", "approve", "disburse", "repay", "reverse", "offset", "print", "configure")


class OLLoanPermission:
    VIEW = "ol_loans.view"
    REQUEST = "ol_loans.request"
    APPROVE = "ol_loans.approve"
    DISBURSE = "ol_loans.disburse"
    REPAY = "ol_loans.repay"
    REVERSE = "ol_loans.reverse"
    OFFSET = "ol_loans.offset"
    PRINT = "ol_loans.print"
    CONFIGURE = "ol_loans.configure"

    ACTION_TO_CODE = {
        "list": VIEW,
        "retrieve": VIEW,
        "view": VIEW,
        "export": VIEW,
        "request": REQUEST,
        "create": REQUEST,
        "approve": APPROVE,
        "reject": APPROVE,
        "disburse": DISBURSE,
        "repay": REPAY,
        "reverse": REVERSE,
        "offset": OFFSET,
        "print": PRINT,
        "configure": CONFIGURE,
    }

    @classmethod
    def code_for(cls, action):
        return cls.ACTION_TO_CODE.get((action or "").lower(), cls.VIEW)

    @classmethod
    def allowed_codes(cls):
        return tuple(f"{OL_LOANS_MODULE}.{action}" for action in ACTIONS)


def has_ol_loan_permission(actor, action="view"):
    """Return whether an authenticated actor may perform an OL Loans action."""
    if not actor or not getattr(actor, "is_authenticated", False):
        return False
    if getattr(actor, "is_superuser", False):
        return True
    code = OLLoanPermission.code_for(action)
    if hasattr(actor, "has_permission") and actor.has_permission(code):
        return True
    if action in {"list", "retrieve", "view", "export"} and hasattr(actor, "has_module_permission"):
        if actor.has_module_permission(OL_LOANS_MODULE, "READ"):
            return True
    module_action = code.rsplit(".", 1)[-1].upper()
    return bool(
        hasattr(actor, "has_module_permission")
        and any(actor.has_module_permission(OL_LOANS_MODULE, candidate) for candidate in (module_action, "CONFIGURE"))
    )


class HasOLLoanPermission(BasePermission):
    """DRF permission using the view action's OL Loans entitlement."""

    def has_permission(self, request, view):
        action = getattr(view, "action", None) or request.method.lower()
        return has_ol_loan_permission(request.user, action)
