from rest_framework.permissions import BasePermission


OL_QUOTATIONS_MODULE = "ol_quotations"


class OLQuotationPermission:
    VIEW = "ol_quotations.view"
    CREATE = "ol_quotations.create"
    UPDATE = "ol_quotations.update"
    DELETE = "ol_quotations.delete"
    CONFIGURE = "ol_quotations.configure"
    PRINT = "ol_quotations.print"
    CONVERT = "ol_quotations.convert"
    FINALIZE = "ol_quotations.finalize"

    ACTION_TO_CODE = {
        "list": VIEW,
        "retrieve": VIEW,
        "view": VIEW,
        "create": CREATE,
        "update": UPDATE,
        "partial_update": UPDATE,
        "destroy": DELETE,
        "finalize": FINALIZE,
        "expire": UPDATE,
        "convert": CONVERT,
        "print": PRINT,
        "configure": CONFIGURE,
        "personal_details": UPDATE,
        "personal_details_options": VIEW,
    }

    @classmethod
    def code_for(cls, action):
        return cls.ACTION_TO_CODE.get((action or "").lower(), cls.VIEW)


def has_quotation_permission(actor, action="view"):
    if not actor or not getattr(actor, "is_authenticated", False):
        return False
    if getattr(actor, "is_superuser", False):
        return True
    code = OLQuotationPermission.code_for(action)
    if hasattr(actor, "has_permission") and actor.has_permission(code):
        return True
    if action in {"list", "retrieve", "view"} and hasattr(actor, "has_permission"):
        if actor.has_permission(OLQuotationPermission.CONFIGURE):
            return True
    if hasattr(actor, "has_module_permission"):
        action_code = code.rsplit(".", 1)[-1].upper()
        candidates = (action_code, "CONFIGURE") if action in {"list", "retrieve", "view"} else (action_code,)
        return any(actor.has_module_permission(OL_QUOTATIONS_MODULE, candidate) for candidate in candidates)
    return False


class HasOLQuotationPermission(BasePermission):
    def has_permission(self, request, view):
        action = getattr(view, "action", None) or request.method.lower()
        return has_quotation_permission(request.user, action)
