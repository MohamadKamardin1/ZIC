"""OL Commitments structured error helpers.

Prompt 1 establishes the shared structured error shape and the domain exception
used by the module. The full Error Coach taxonomy (12+ registry codes) is added
in Prompt 6; the codes introduced here are the ones surfaced by the foundation
(model validation, parameter catalogs, permission, not-found).
"""

from apps.core.exceptions import ZICAPIException

DOC_REF = "docs/OL_COMMITMENTS_DESIGN.md"

PARAMETER_NAVIGATION = [
    "Ordinary Life Parameters > Policy Setup > OL Commitment Statuses",
    "Ordinary Life Parameters > Policy Setup > OL Grace Period",
    "Ordinary Life Parameters > Policy Setup > Grace Period Notification Schedule",
]


class CommitmentError(ZICAPIException):
    """Base structured exception for the OL Commitments module."""

    def __init__(
        self,
        message,
        *,
        error_code="COMMITMENT_ERROR",
        status_code=400,
        resolution_steps=None,
        field_errors=None,
        doc_ref=DOC_REF,
        details=None,
    ):
        super().__init__(
            message=message,
            code=error_code,
            status_code=status_code,
            details=details,
            error_code=error_code,
            resolution_steps=resolution_steps,
            field_errors=field_errors,
            doc_ref=doc_ref,
        )


def parameter_missing(parameter_label, navigation_path=None):
    """Structured ``PARAMETER_MISSING`` error with the exact navigation path."""
    path = navigation_path or "Ordinary Life Parameters > Policy Setup"
    steps = [
        f"Configure the '{parameter_label}' parameter in the OL Parameters module.",
        path,
        "Re-run the commitment operation once the parameter is active and effective.",
    ]
    return CommitmentError(
        f"The required parameter '{parameter_label}' is missing or inactive. Configure it under {path}.",
        error_code="PARAMETER_MISSING",
        status_code=422,
        resolution_steps=steps,
        details={"parameter": parameter_label, "navigation_path": path},
    )


def not_found(commitment_number=None):
    identifier = commitment_number or "the requested commitment"
    return CommitmentError(
        f"Commitment {identifier} could not be found.",
        error_code="COMMITMENT_NOT_FOUND",
        status_code=404,
        resolution_steps=[
            "Verify the commitment number is correct.",
            "Check list filters for source type and status.",
            "Contact operations if the record was cancelled.",
        ],
    )


def permission_denied(action):
    return CommitmentError(
        f"You do not have permission to {action.replace('_', ' ')} commitments.",
        error_code="PERMISSION_DENIED",
        status_code=403,
        resolution_steps=[
            f"Request the 'ol_commitments.{action}' permission from an administrator.",
            "Ask your administrator to assign the appropriate role group under User Management.",
        ],
    )
