from rest_framework.permissions import BasePermission

OL_PROPOSALS_MODULE = "ol_proposals"

ACTIONS = ("view", "create", "enrich", "upload_documents", "mark_payment_ready", "convert", "cancel", "print")


class OLProposalPermission:
    VIEW = "ol_proposals.view"
    CREATE = "ol_proposals.create"
    ENRICH = "ol_proposals.enrich"
    UPLOAD_DOCUMENTS = "ol_proposals.upload_documents"
    MARK_PAYMENT_READY = "ol_proposals.mark_payment_ready"
    CONVERT = "ol_proposals.convert"
    CANCEL = "ol_proposals.cancel"
    PRINT = "ol_proposals.print"

    ACTION_TO_CODE = {
        "list": VIEW,
        "retrieve": VIEW,
        "view": VIEW,
        "export": VIEW,
        "create": CREATE,
        "enrich": ENRICH,
        "enrichment": ENRICH,
        "save_enrichment": ENRICH,
        "upload_documents": UPLOAD_DOCUMENTS,
        "documents": UPLOAD_DOCUMENTS,
        "mark_payment_ready": MARK_PAYMENT_READY,
        "payment_ready": MARK_PAYMENT_READY,
        "reactivate": ENRICH,
        "convert": CONVERT,
        "cancel": CANCEL,
        "print": PRINT,
    }

    @classmethod
    def code_for(cls, action):
        return cls.ACTION_TO_CODE.get((action or "").lower(), cls.VIEW)

    @classmethod
    def allowed_codes(cls):
        return tuple(f"{OL_PROPOSALS_MODULE}.{action}" for action in ACTIONS)


def has_ol_proposal_permission(actor, action="view"):
    if not actor or not getattr(actor, "is_authenticated", False):
        return False
    if getattr(actor, "is_superuser", False):
        return True
    code = OLProposalPermission.code_for(action)
    if hasattr(actor, "has_permission") and actor.has_permission(code):
        return True
    if action in {"list", "retrieve", "view", "export"}:
        if hasattr(actor, "has_module_permission") and actor.has_module_permission(OL_PROPOSALS_MODULE, "READ"):
            return True
    module_action = code.rsplit(".", 1)[-1].upper()
    return bool(
        hasattr(actor, "has_module_permission")
        and any(
            actor.has_module_permission(OL_PROPOSALS_MODULE, candidate)
            for candidate in (module_action, "CONFIGURE")
        )
    )


class HasOLProposalPermission(BasePermission):
    def has_permission(self, request, view):
        action = getattr(view, "action", None) or request.method.lower()
        return has_ol_proposal_permission(request.user, action)