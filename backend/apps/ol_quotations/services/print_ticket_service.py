from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlencode
from uuid import UUID

from django.conf import settings
from django.core import signing
from django.core.files.storage import default_storage
from django.http import FileResponse, Http404
from django.utils import timezone

from apps.governance.services.audit_service import AuditService
from apps.users.models import User

from ..permissions import has_quotation_permission


class PrintTicketError(Exception):
    """Raised when a document ticket is missing, invalid, expired, or unauthorized."""

    def __init__(self, message: str, *, status_code: int = 403):
        super().__init__(message)
        self.status_code = status_code


class PrintTicketService:
    """Issue and validate short-lived, single-purpose document download tickets."""

    PURPOSE = "ol_quotation_document_download"
    SALT = "zic.ol_quotations.document-download.v1"
    MAX_AGE_SECONDS = 5 * 60
    FORMATS = {"pdf", "html"}

    @classmethod
    def _signer(cls) -> signing.TimestampSigner:
        # TimestampSigner uses Django's HMAC signing implementation and the
        # project SECRET_KEY. The dedicated salt prevents cross-purpose reuse.
        return signing.TimestampSigner(key=settings.SECRET_KEY, salt=cls.SALT)

    @classmethod
    def issue(cls, *, document, actor, request=None, content_format: str = "pdf") -> tuple[str, datetime]:
        content_format = (content_format or "pdf").strip().lower()
        if content_format not in cls.FORMATS:
            raise PrintTicketError("Unsupported document format.", status_code=400)
        if not actor or not getattr(actor, "is_authenticated", False):
            raise PrintTicketError("Authentication is required to issue a document ticket.", status_code=401)
        if not has_quotation_permission(actor, "print"):
            raise PrintTicketError("You do not have permission to download quotation documents.", status_code=403)
        if not cls._in_scope(actor, document.quotation):
            raise PrintTicketError("You are not allowed to access this quotation document.", status_code=403)

        expires_at = timezone.now() + timedelta(seconds=cls.MAX_AGE_SECONDS)
        payload = {
            "v": 1,
            "purpose": cls.PURPOSE,
            "document_id": str(document.pk),
            "quotation_id": str(document.quotation_id),
            "user_id": str(actor.pk),
            "format": content_format,
        }
        ticket = cls._signer().sign_object(payload)
        AuditService.log_action(
            action="PRINT_TICKET_ISSUED",
            instance=document.quotation,
            actor=actor,
            request=request,
            before_state={"document_id": str(document.pk)},
            after_state={
                "document_id": str(document.pk),
                "format": content_format,
                "expires_at": expires_at.isoformat(),
            },
            reason="Short-lived quotation document download ticket issued.",
            changed_fields=[],
            source_channel="API",
        )
        return ticket, expires_at

    @classmethod
    def unsign(cls, ticket: str) -> dict[str, Any]:
        if not ticket or len(ticket) > 4096:
            raise PrintTicketError("The document ticket is missing or invalid.", status_code=403)
        try:
            payload = cls._signer().unsign_object(ticket, max_age=cls.MAX_AGE_SECONDS)
        except signing.SignatureExpired as exc:
            raise PrintTicketError("The document ticket has expired. Generate a new printout.", status_code=403) from exc
        except signing.BadSignature as exc:
            raise PrintTicketError("The document ticket is invalid.", status_code=403) from exc
        if not isinstance(payload, dict):
            raise PrintTicketError("The document ticket is invalid.", status_code=403)
        if payload.get("purpose") != cls.PURPOSE or payload.get("v") != 1:
            raise PrintTicketError("The document ticket is invalid for this resource.", status_code=403)
        if payload.get("format") not in cls.FORMATS:
            raise PrintTicketError("The document ticket has an invalid format.", status_code=403)
        for key in ("document_id", "quotation_id", "user_id"):
            try:
                UUID(str(payload[key]))
            except (KeyError, TypeError, ValueError, AttributeError) as exc:
                raise PrintTicketError("The document ticket is invalid.", status_code=403) from exc
        return payload

    @classmethod
    def protected_path(cls, document, content_format: str = "pdf") -> str:
        content_format = (content_format or "pdf").strip().lower()
        suffix = "html" if content_format == "html" else "download"
        return f"/api/v1/ol-quotations/documents/{document.pk}/{suffix}/"

    @classmethod
    def ticket_url(cls, *, document, ticket: str, content_format: str, request=None) -> str:
        query = urlencode({"ticket": ticket})
        path = f"{cls.protected_path(document, content_format)}?{query}"
        return request.build_absolute_uri(path) if request is not None else path

    @classmethod
    def _ticket_actor(cls, payload, request):
        actor = User.objects.filter(pk=payload["user_id"], is_active=True, status=User.AccountStatus.ACTIVE).first()
        if actor is None or not has_quotation_permission(actor, "print"):
            raise PrintTicketError("The document ticket owner is no longer authorized.", status_code=403)
        if getattr(request.user, "is_authenticated", False) and request.user.pk != actor.pk:
            raise PrintTicketError("This document ticket belongs to another authenticated user.", status_code=403)
        return actor

    @classmethod
    def _in_scope(cls, actor, quotation) -> bool:
        if getattr(actor, "is_superuser", False):
            return True
        if not hasattr(actor, "visible_partners"):
            return False
        return actor.visible_partners().filter(pk=quotation.partner_id).exists()

    @classmethod
    def stream(cls, *, document, payload=None, request=None, actor=None, expected_format=None):
        via_ticket = payload is not None
        if payload is not None:
            actor = cls._ticket_actor(payload, request)
            if str(payload.get("document_id")) != str(document.pk) or str(payload.get("quotation_id")) != str(document.quotation_id):
                raise PrintTicketError("The document ticket does not match this resource.", status_code=403)
            content_format = payload["format"]
            if expected_format and content_format != expected_format:
                raise PrintTicketError("The document ticket is for a different document format.", status_code=403)
        else:
            actor = actor or getattr(request, "user", None)
            if not actor or not getattr(actor, "is_authenticated", False):
                raise PrintTicketError("Authentication credentials are required to access this document.", status_code=401)
            if not has_quotation_permission(actor, "print"):
                raise PrintTicketError("You do not have permission to download quotation documents.", status_code=403)
            content_format = expected_format or (
                "html" if request and request.path.rstrip("/").endswith("/html") else "pdf"
            )
        if not cls._in_scope(actor, document.quotation):
            raise PrintTicketError("You are not allowed to access this quotation document.", status_code=403)

        reference = document.html_reference if content_format == "html" else document.file_reference
        content_type = "text/html; charset=utf-8" if content_format == "html" else (document.mime_type or "application/pdf")
        if not reference or not default_storage.exists(reference):
            raise Http404("The requested quotation document is no longer available.")
        try:
            file_handle = default_storage.open(reference, "rb")
        except FileNotFoundError as exc:
            raise Http404("The requested quotation document is no longer available.") from exc

        response = FileResponse(file_handle, content_type=content_type)
        response["Content-Disposition"] = f"inline; filename=quotation-{document.quotation.quote_number}.{content_format}"
        response["Cache-Control"] = "private, no-store, max-age=0"
        response["Pragma"] = "no-cache"
        response["X-Content-Type-Options"] = "nosniff"
        AuditService.log_action(
            action="PRINT_TICKET_DOWNLOADED" if via_ticket else "PRINT_DOCUMENT_DOWNLOADED",
            instance=document.quotation,
            actor=actor,
            request=request,
            before_state={"document_id": str(document.pk), "format": content_format},
            after_state={"document_id": str(document.pk), "format": content_format},
            reason=(
                "Quotation document accessed with a short-lived download ticket."
                if via_ticket
                else "Quotation document accessed with an authenticated bearer request."
            ),
            changed_fields=[],
            source_channel="API",
        )
        return response


def protected_document_url(document, content_format: str = "pdf") -> str:
    return PrintTicketService.protected_path(document, content_format)


def document_download_url(document, *, request=None, actor=None, content_format: str = "pdf", issue_ticket: bool = False) -> dict[str, Any]:
    result = {"url": protected_document_url(document, content_format)}
    if issue_ticket and actor is not None:
        ticket, expires_at = PrintTicketService.issue(
            document=document,
            actor=actor,
            request=request,
            content_format=content_format,
        )
        result.update({"url": PrintTicketService.ticket_url(document=document, ticket=ticket, content_format=content_format, request=request), "expires_at": expires_at})
    return result


__all__ = [
    "PrintTicketError",
    "PrintTicketService",
    "document_download_url",
    "protected_document_url",
]
