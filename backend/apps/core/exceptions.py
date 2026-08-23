import copy
import logging
from datetime import datetime

from django.core.exceptions import PermissionDenied, ValidationError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger("apps.core.exceptions")

DEFAULT_DOC_REF = "docs/OL_COMMITMENTS_DESIGN.md"


def custom_exception_handler(exc, context):
    """Render every API fault into the global structured error shape.

    Shape required by the OL Commitments contract (Error Coach):

    .. code-block:: json

        {
          "error_code": "VALIDAITON_ERROR",
          "message": "...",
          "resolution_steps": [],
          "field_errors": {},
          "doc_ref": "docs/OL_COMMITMENTS_DESIGN.md"
        }

    Legacy keys are preserved for compatibility: ``success``, ``status_code``,
    ``error: {code, message, details}`` and ``meta: {timestamp, request_id,
    version}``. Django/DRF validation, permission, and not-found faults are
    mapped automatically into the same shape.
    """
    response = exception_handler(exc, context)
    handled_by_drf = response is not None

    if response is None and isinstance(exc, (ValidationError, PermissionDenied, ZICAPIException)):
        # Django/plain exceptions are not understood by the DRF handler; normalize them.
        if isinstance(exc, PermissionDenied):
            response = Response({}, status=status.HTTP_403_FORBIDDEN)
        elif isinstance(exc, ZICAPIException):
            response = Response({}, status=exc.status_code)
        else:
            response = Response({}, status=status.HTTP_400_BAD_REQUEST)

    if response is None:
        logger.exception("Unhandled exception: %s", exc)
        response = Response({}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    structured_code = getattr(exc, "error_code", None) or getattr(exc, "code", None)
    error_code = _structured(structured_code) or _get_error_code(response.status_code)

    message = _message_for(exc, response.data)
    resolution_steps = list(getattr(exc, "resolution_steps", None) or [])
    field_errors = getattr(exc, "field_errors", None)
    if not field_errors:
        field_errors = _extract_field_errors(exc, response.data)
    doc_ref = str(getattr(exc, "doc_ref", None) or DEFAULT_DOC_REF)
    request_id = _get_request_id(context.get("request"))
    meta = {
        "timestamp": datetime.now().isoformat() + "Z",
        "request_id": request_id,
        "version": "v1",
    }

    # Legacy `error.details` keeps the exact payload previous consumers rely on:
    # the raw DRF response data for DRF faults, the exception ``details`` for
    # ZICAPIException, and the flattened field map for Django validation faults.
    if handled_by_drf:
        error_details = _copy_data(response.data)
    elif isinstance(exc, ZICAPIException):
        error_details = getattr(exc, "details", None)
    else:
        error_details = field_errors or None

    response.data = {
        "success": False,
        "status_code": response.status_code,
        "error_code": error_code,
        "message": message,
        "resolution_steps": resolution_steps,
        "field_errors": field_errors,
        "doc_ref": doc_ref,
        "error": {
            "code": error_code,
            "message": message,
            "details": error_details,
        },
        "meta": meta,
    }

    _log_structured_error(error_code, message, request_id, response.status_code)
    return response


def _copy_data(value):
    try:
        return copy.deepcopy(value)
    except Exception:
        return None


def _structured(value):
    value = str(value or "").strip()
    return value.upper() if value else ""


def _message_for(exc, data):
    if isinstance(exc, ValidationError):
        messages = exc.messages
        if messages:
            return " ".join(str(message) for message in messages)
    return str(exc)


def _extract_field_errors(exc, data):
    """Build a ``{field: [messages]}`` map from DRF or Django validation faults."""
    if isinstance(exc, ValidationError):
        message_dict = getattr(exc, "message_dict", None) or {}
        return {str(field): [str(message) for message in messages] for field, messages in message_dict.items()}

    detail = getattr(exc, "detail", None)
    if isinstance(detail, dict):
        errors = {}
        for field, raw in detail.items():
            if isinstance(raw, (list, tuple)):
                errors[str(field)] = [str(message) for message in raw]
            else:
                errors[str(field)] = [str(raw)]
        return errors

    if isinstance(detail, (list, tuple)):
        return {"" if detail else "non_field_errors": [str(message) for message in detail]}

    if detail is not None:
        return {"detail": [str(detail)]}

    return {}


def _get_error_code(status_code):
    codes = {
        400: "VALIDATION_ERROR",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        409: "CONFLICT",
        429: "RATE_LIMITED",
        500: "INTERNAL_SERVER_ERROR",
        502: "BAD_GATEWAY",
        503: "SERVICE_UNAVAILABLE",
    }
    return codes.get(status_code, "UNKNOWN_ERROR")


def _get_request_id(request):
    if request and hasattr(request, "request_id"):
        return request.request_id
    return None


def _log_structured_error(error_code, message, request_id, status_code):
    logger.error(
        "Structured error code=%s status=%s request_id=%s message=%s",
        error_code,
        status_code,
        request_id,
        message[:300],
    )


class ZICAPIException(Exception):
    """Base structured exception for the ZIC API.

    Optional structured fields feed the global exception handler:
    ``error_code``, ``resolution_steps``, ``field_errors``, ``doc_ref``.
    """

    def __init__(
        self,
        message,
        code="ERROR",
        status_code=400,
        details=None,
        *,
        error_code=None,
        resolution_steps=None,
        field_errors=None,
        doc_ref=None,
    ):
        self.message = message
        self.code = error_code or code
        self.error_code = self.code
        self.status_code = status_code
        self.details = details
        self.resolution_steps = list(resolution_steps or [])
        self.field_errors = dict(field_errors or {})
        self.doc_ref = doc_ref
        super().__init__(self.message)
