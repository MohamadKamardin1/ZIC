from rest_framework.permissions import SAFE_METHODS, BasePermission

OL_MATURITY_INSTALLMENTS_MODULE = "ol_maturity_installments"
ACTIONS = (
    "view",
    "create",
    "process_payment",
    "cancel",
    "print",
    "configure",
)


class OLMaturityInstallmentPermission:
    VIEW = "ol_maturity_installments.view"
    CREATE = "ol_maturity_installments.create"
    PROCESS_PAYMENT = "ol_maturity_installments.process_payment"
    CANCEL = "ol_maturity_installments.cancel"
    PRINT = "ol_maturity_installments.print"
    CONFIGURE = "ol_maturity_installments.configure"

    ACTION_TO_CODE = {
        "list": VIEW,
        "retrieve": VIEW,
        "view": VIEW,
        "create": CREATE,
        "process_payment": PROCESS_PAYMENT,
        "cancel": CANCEL,
        "print": PRINT,
        "configure": CONFIGURE,
    }

    @classmethod
    def code_for(cls, action):
        action = (action or "view").lower()
        return cls.ACTION_TO_CODE.get(action, f"{OL_MATURITY_INSTALLMENTS_MODULE}.{action}")

    @classmethod
    def allowed_codes(cls):
        return tuple(f"{OL_MATURITY_INSTALLMENTS_MODULE}.{action}" for action in ACTIONS)


def has_ol_maturity_installment_permission(actor, action="view"):
    """Return whether an actor may perform an OL Maturity Installments action."""
    if not actor or not getattr(actor, "is_authenticated", False):
        return False
    if getattr(actor, "is_superuser", False):
        return True

    code = OLMaturityInstallmentPermission.code_for(action)
    if hasattr(actor, "has_permission") and actor.has_permission(code):
        return True

    if action in {"list", "retrieve", "view"}:
        return bool(
            hasattr(actor, "has_module_permission")
            and actor.has_module_permission(OL_MATURITY_INSTALLMENTS_MODULE, "READ")
        )

    module_action = code.rsplit(".", 1)[-1].upper()
    return bool(
        hasattr(actor, "has_module_permission")
        and any(
            actor.has_module_permission(OL_MATURITY_INSTALLMENTS_MODULE, candidate)
            for candidate in (module_action, "CONFIGURE")
        )
    )


class HasOLMaturityInstallmentPermission(BasePermission):
    """Authorize an endpoint using the view action's OL Maturity Installments entitlement."""

    def has_permission(self, request, view):
        action = getattr(view, "action", None)
        if not action:
            action = "view" if request.method in SAFE_METHODS else request.method.lower()
        return has_ol_maturity_installment_permission(request.user, action)
