"""Front Office Receipts — signed download ticket (Prompt 8).

Generated receipt PDFs are not exposed at the public media URL; they are only
reachable through the authenticated print pipeline. The print/download views
issue a short-lived, HMAC-signed ticket bound to the requesting user, the
document, and the download purpose. ``validate_download_ticket`` refuses forged,
expired, or mismatched tickets with a structured error.
"""

import base64
import hashlib
import hmac
import json
import time

from django.conf import settings

from apps.front_office.receipts.errors import ticket_invalid

DEFAULT_TICKET_TTL_SECONDS = 15 * 60  # 15 minutes
DOWNLOAD_PURPOSE = "download"


def _sign(raw):
    return hmac.new(settings.SECRET_KEY.encode("utf-8"), raw, hashlib.sha256).hexdigest()


def _b64url_encode(payload_bytes):
    return base64.urlsafe_b64encode(payload_bytes).decode("ascii").rstrip("=")


def _b64url_decode(raw):
    padding = "=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode(raw + padding)


def issue_download_ticket(*, document_id, user_id, purpose=DOWNLOAD_PURPOSE, ttl_seconds=DEFAULT_TICKET_TTL_SECONDS):
    """Return a signed ticket permitting the user to download the document."""
    payload = {
        "purpose": purpose,
        "document_id": str(document_id),
        "user_id": str(user_id),
        "expires": int(time.time()) + int(ttl_seconds),
    }
    raw = _b64url_encode(json.dumps(payload, sort_keys=True).encode("utf-8"))
    return f"{raw}.{_sign(raw.encode('ascii'))}"


def validate_download_ticket(token, *, purpose=DOWNLOAD_PURPOSE, document_id=None, user_id=None):
    """Validate a ticket; return its payload or raise ``RECEIPT_TICKET_INVALID``."""
    if not token or "." not in token:
        raise ticket_invalid()
    raw, signature = token.rsplit(".", 1)
    if not hmac.compare_digest(signature, _sign(raw.encode("ascii"))):
        raise ticket_invalid()
    try:
        payload = json.loads(_b64url_decode(raw).decode("utf-8"))
    except (ValueError, TypeError, UnicodeDecodeError):
        raise ticket_invalid()
    if not isinstance(payload, dict):
        raise ticket_invalid()
    if payload.get("purpose") != purpose:
        raise ticket_invalid()
    if document_id is not None and str(payload.get("document_id")) != str(document_id):
        raise ticket_invalid()
    if user_id is not None and str(payload.get("user_id")) != str(user_id):
        raise ticket_invalid()
    try:
        expires = int(payload.get("expires", 0))
    except (TypeError, ValueError):
        expires = 0
    if expires < int(time.time()):
        raise ticket_invalid()
    return payload
