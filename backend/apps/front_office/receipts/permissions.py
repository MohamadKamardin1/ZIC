from rest_framework.permissions import BasePermission

RECEIPTS_MODULE = "front_office.receipts"

ACTIONS = ("view", "create", "post", "allocate", "reverse", "cancel", "print", "import", "configure")


class ReceiptPermission:
    VIEW = "front_office.receipts.view"
    CREATE = "front_office.receipts.create"
    POST = "front_office.receipts.post"
    ALLOCATE = "front_office.receipts.allocate"
    REVERSE = "front_office.receipts.reverse"
    CANCEL = "front_office.receipts.cancel"
    PRINT = "front_office.receipts.print"
    IMPORT = "front_office.receipts.import"
    CONFIGURE = "front_office.receipts.configure"

    ACTION_TO_CODE = {
        "list": VIEW,
        "retrieve": VIEW,
        "view": VIEW,
        "export": VIEW,
        "options": VIEW,
        "create": CREATE,
        "draft": CREATE,
        "update": CREATE,
        "post": POST,
        "allocate": ALLOCATE,
        "reverse": REVERSE,
        "cancel": CANCEL,
        "print": PRINT,
        "import": IMPORT,
        "configure": CONFIGURE,
    }

    @classmethod
    def code_for(cls, action):
        return cls.ACTION_TO_CODE.get((action or "").lower(), cls.VIEW)

    @classmethod
    def allowed_codes(cls):
        return tuple(f"{RECEIPTS_MODULE}.{action}" for action in ACTIONS)


def has_receipt_permission(actor, action="view"):
    """Return whether an actor may perform a Front Office Receipts action."""
    if not actor or not getattr(actor, "is_authenticated", False):
        return False
    if getattr(actor, "is_superuser", False):
        return True
    code = ReceiptPermission.code_for(action)
    if hasattr(actor, "has_permission") and actor.has_permission(code):
        return True
    if action in {"list", "retrieve", "view", "export"}:
        if hasattr(actor, "has_module_permission") and actor.has_module_permission(RECEIPTS_MODULE, "READ"):
            return True
    module_action = code.rsplit(".", 1)[-1].upper()
    return bool(
        hasattr(actor, "has_module_permission")
        and any(
            actor.has_module_permission(RECEIPTS_MODULE, candidate) for candidate in (module_action, "CONFIGURE")
        )
    )


class HasReceiptPermission(BasePermission):
    """DRF permission using the view action's Front Office Receipts entitlement."""

    def has_permission(self, request, view):
        action = getattr(view, "action", None) or request.method.lower()
        return has_receipt_permission(request.user, action)
