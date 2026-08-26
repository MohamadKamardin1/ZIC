from apps.core.exceptions import ZICAPIException


DOC_REF = "docs/OL_LOANS_DESIGN.md"

LOAN_ERROR_CODES = (
    "LOAN_INELIGIBLE",
    "LOAN_EXCEEDS_LIMIT",
    "LOAN_ACTIVE_EXISTS",
    "LOAN_INVALID_STATUS",
    "LOAN_DISBURSEMENT_FAILED",
    "LOAN_REPAYMENT_OVERPAYMENT",
    "LOAN_OFFSET_INVALID",
    "LOAN_PARAMETER_MISSING",
)


class LoanError(ZICAPIException):
    """Base structured exception for the OL Loans bounded context."""

    def __init__(
        self,
        message,
        *,
        error_code="LOAN_ERROR",
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


def loan_not_found(identifier=None):
    label = identifier or "the requested loan"
    return LoanError(
        f"Loan {label} could not be found.",
        error_code="LOAN_NOT_FOUND",
        status_code=404,
        resolution_steps=[
            "Verify the loan number or identifier is correct.",
            "Clear restrictive list filters and search again.",
            "Contact Loan Operations if the record has been closed or archived.",
        ],
    )


def permission_denied(action):
    action_label = (action or "view").replace("_", " ")
    return LoanError(
        f"You do not have permission to {action_label} OL Loans.",
        error_code="PERMISSION_DENIED",
        status_code=403,
        resolution_steps=[
            f"Request the 'ol_loans.{action}' permission from an administrator.",
            "Ask User Management to assign the appropriate OL Loans role group.",
        ],
    )


def parameter_missing(parameter_label, navigation_path="Ordinary Life Parameters > Loan Setup"):
    return LoanError(
        f"The required loan parameter '{parameter_label}' is missing or inactive.",
        error_code="LOAN_PARAMETER_MISSING",
        status_code=422,
        resolution_steps=[
            f"Configure '{parameter_label}' in the OL Parameters module.",
            f"Open {navigation_path} and activate an effective configuration.",
            "Retry the loan operation after the parameter is saved and effective.",
        ],
        details={"parameter": parameter_label, "navigation_path": navigation_path},
    )
