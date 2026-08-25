"""Front Office Receipts — structured error registry (Error Coach shape).

Every user-facing fault resolves to a registry code with a human message,
HTTP status, and resolution steps. The registry is the single catalog the
views/services raise from; the global exception handler
(``apps.core.exceptions.custom_exception_handler``) renders each entry in the
standard structured shape.
"""

from apps.core.exceptions import ZICAPIException

DOC_REF = "docs/FRONT_OFFICE_RECEIPTS_DESIGN.md"

# Deep-link navigation paths for parameter-driven behavior. Each key is a
# parameter label that ``parameter_missing`` resolves to a configured location.
RECEIPT_PARAMETER_NAVIGATION = {
    "RECEIPT_BRANCHES": "System Parameters > Branches",
    "RECEIPT_CURRENCIES": "System Parameters > Currencies",
    "RECEIPT_PAYMENT_MODES": "System Parameters > Payment Modes",
    "RECEIPT_PARTNERS": "Partners > Partner Records",
    "RECEIPT_NUMBERING_RULE": "Front Office Parameters > Receipt Numbering",
    "RECEIPT_COMPANY_BANK_ACCOUNTS": "Front Office Parameters > Company Bank Accounts",
}


class ReceiptError(ZICAPIException):
    """Base structured exception for the Front Office Receipts module."""

    def __init__(
        self,
        message,
        *,
        error_code="RECEIPT_ERROR",
        status_code=400,
        resolution_steps=None,
        field_errors=None,
        details=None,
        doc_ref=DOC_REF,
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


# Registry contract: code -> (message, status_code, resolution_steps).
RECEIPT_ERROR_REGISTRY = {
    "RECEIPT_NOT_FOUND": (
        "The requested receipt could not be found.",
        404,
        [
            "Verify the receipt number or identifier is correct.",
            "Check list filters for status and branch.",
            "Contact operations if the record was cancelled or reversed.",
        ],
    ),
    "RECEIPT_INVALID_STATUS": (
        "The receipt is not in a state that allows this action.",
        422,
        [
            "Review the current receipt status and the allowed actions.",
            "Choose the action permitted for the current status.",
        ],
    ),
    "RECEIPT_AMOUNT_INVALID": (
        "The receipt amount is not valid.",
        422,
        [
            "Enter an amount greater than zero.",
            "Confirm the amount matches the confirmed collection amount.",
        ],
    ),
    "RECEIPT_ALLOCATION_INVALID": (
        "The allocation details are not valid.",
        422,
        [
            "Confirm the allocation target and amount.",
            "Ensure the allocation amount is greater than zero.",
        ],
    ),
    "RECEIPT_OVERALLOCATION": (
        "The allocation exceeds the receipt unallocated balance.",
        422,
        [
            "Reduce the allocation amount to the unallocated balance.",
            "Create an additional receipt for the remaining amount.",
        ],
    ),
    "RECEIPT_ALREADY_POSTED": (
        "The receipt has already been posted.",
        409,
        [
            "Posting is allowed only once per receipt.",
            "Create a new receipt if an additional collection is required.",
        ],
    ),
    "RECEIPT_ALREADY_REVERSED": (
        "The receipt has already been reversed.",
        409,
        [
            "A reversed receipt is closed.",
            "Create a new receipt if a re-collection is required.",
        ],
    ),
    "RECEIPT_REASON_REQUIRED": (
        "A reason is required for this receipt action.",
        422,
        [
            "Provide the reason for the reversal or cancellation.",
            "Reasons are mandatory for all financial reversals and cancellations.",
        ],
    ),
    "RECEIPT_REVERSAL_LOCKED": (
        "The receipt is outside the configured reversal window.",
        422,
        [
            "Review the configured reversal lock period (system parameter RECEIPT_REVERSAL_LOCK_DAYS).",
            "Contact operations if the reversal must still be processed.",
        ],
    ),
    "RECEIPT_PAYMENT_REFERENCE_REQUIRED": (
        "A payment reference is required for this payment mode.",
        422,
        [
            "Provide the reference provided by the payer (e.g. M-PESA transaction ID or bank transfer reference).",
            "Confirm the payment mode rule for the selected payment mode.",
        ],
    ),
    "RECEIPT_BANK_ACCOUNT_REQUIRED": (
        "A bank account is required for this payment mode.",
        422,
        [
            "Attach the payer's bank account to the receipt.",
            "Confirm the payment mode rule for the selected payment mode.",
        ],
    ),
    "RECEIPT_CURRENCY_MISMATCH": (
        "The payment currency does not match the receipt currency.",
        422,
        [
            "Confirm the collection currency.",
            "Provide an exchange rate when the payment currency differs.",
        ],
    ),
    "RECEIPT_PERMISSION_DENIED": (
        "You do not have permission to perform this receipt action.",
        403,
        [
            "Request the relevant 'front_office.receipts.<action>' permission from an administrator.",
            "Ask your administrator to assign the appropriate role group under User Management.",
        ],
    ),
    "RECEIPT_PARAMETER_MISSING": (
        "A required parameter is missing or inactive.",
        422,
        [
            "Configure the referenced parameter under System Parameters / OL Parameters.",
            "Re-run the receipt operation once the parameter is active.",
        ],
    ),
    "RECEIPT_DOCUMENT_NOT_FOUND": (
        "The requested receipt document could not be found.",
        404,
        [
            "Verify the document identifier is correct.",
            "Generate the receipt printout again and retry the download.",
        ],
    ),
    "RECEIPT_TICKET_INVALID": (
        "The download ticket is invalid or has expired.",
        403,
        [
            "Re-open the receipt printout and use the fresh download link.",
            "If the link was shared, request a new one from the receipt print screen.",
        ],
    ),
    "RECEIPT_FILE_MISSING": (
        "The generated file is missing from storage.",
        404,
        [
            "Regenerate the receipt printout.",
            "Contact operations if the media file was removed.",
        ],
    ),
    "RECEIPT_IMPORT_ROW_INVALID": (
        "The import row could not be processed.",
        422,
        [
            "Review the field-level errors for the row.",
            "Correct the CSV and re-upload, or fix the underlying reference data.",
        ],
    ),
    "RECEIPT_IMPORT_DUPLICATE": (
        "The import contains duplicate rows.",
        409,
        [
            "Remove the duplicated rows from the CSV.",
            "Keep one row per distinct payment event.",
        ],
    ),
    "RECEIPT_IMPORT_PARTIAL_FAILURE": (
        "The import committed with some rows failing.",
        422,
        [
            "Review the failed rows and their error messages.",
            "Re-commit the batch to reprocess the failed rows once the underlying issue is resolved.",
        ],
    ),
    "RECEIPT_IMPORT_BATCH_NOT_FOUND": (
        "The import batch could not be found.",
        404,
        [
            "Verify the batch identifier.",
            "List import batches to find the correct identifier.",
        ],
    ),
}


def raise_registry_error(error_code, *, message=None, field_errors=None, details=None):
    """Raise a structured error from the registry, with optional overrides."""
    if error_code not in RECEIPT_ERROR_REGISTRY:
        raise ReceiptError(message or f"Unknown receipt error code '{error_code}'.", error_code=error_code)
    default_message, status_code, steps = RECEIPT_ERROR_REGISTRY[error_code]
    raise ReceiptError(
        message or default_message,
        error_code=error_code,
        status_code=status_code,
        resolution_steps=list(steps),
        field_errors=field_errors,
        details=details,
    )


def registry_error(error_code, *, message=None, field_errors=None, details=None):
    """Return (but do not raise) the structured exception for an error code."""
    default_message, status_code, steps = RECEIPT_ERROR_REGISTRY[error_code]
    return ReceiptError(
        message or default_message,
        error_code=error_code,
        status_code=status_code,
        resolution_steps=list(steps),
        field_errors=field_errors,
        details=details,
    )


def not_found(receipt_number=None):
    identifier = receipt_number or "the requested receipt"
    return registry_error("RECEIPT_NOT_FOUND", message=f"Receipt {identifier} could not be found.")


def invalid_status(action, status):
    return registry_error(
        "RECEIPT_INVALID_STATUS",
        message=f"'{action}' is not allowed while the receipt is '{status}'.",
    )


def permission_denied(action):
    return registry_error(
        "RECEIPT_PERMISSION_DENIED",
        message=f"You do not have permission to {action.replace('_', ' ')} receipts.",
    )


def parameter_missing(parameter_label, navigation_path=None):
    path = (
        navigation_path
        or RECEIPT_PARAMETER_NAVIGATION.get(parameter_label, "System Parameters")
    )
    return registry_error(
        "RECEIPT_PARAMETER_MISSING",
        message=f"The required parameter '{parameter_label}' is missing or inactive. Configure it under {path}.",
        details={"parameter": parameter_label, "navigation_path": path},
    )


def already_posted():
    return registry_error("RECEIPT_ALREADY_POSTED")


def already_reversed(message=None):
    return registry_error("RECEIPT_ALREADY_REVERSED", message=message)


def reason_required(action="this action"):
    return registry_error(
        "RECEIPT_REASON_REQUIRED",
        message=f"A reason is required for {action}.",
        field_errors={"reason": ["A reason is required for reversal or cancellation."]},
    )


def reversal_locked(days, receipt_date=None):
    return registry_error(
        "RECEIPT_REVERSAL_LOCKED",
        message=f"The receipt is outside the configured {days} day reversal window.",
        details={"lock_days": days, "receipt_date": receipt_date.isoformat() if receipt_date else None},
    )


def allocation_invalid(message=None, field_errors=None):
    return registry_error("RECEIPT_ALLOCATION_INVALID", message=message, field_errors=field_errors)


def overallocation(*, available=None, field="amount", message=None, field_errors=None):
    if message is None:
        message = (
            f"The allocation exceeds the available balance of {available}."
            if available is not None
            else "The allocation exceeds the available balance."
        )
    if field_errors is None:
        field_errors = {field: [message]}
    return registry_error("RECEIPT_OVERALLOCATION", message=message, field_errors=field_errors)


def currency_mismatch(message=None, field_errors=None, resolution_steps=None):
    default_message, status_code, steps = RECEIPT_ERROR_REGISTRY["RECEIPT_CURRENCY_MISMATCH"]
    return ReceiptError(
        message or default_message,
        error_code="RECEIPT_CURRENCY_MISMATCH",
        status_code=status_code,
        resolution_steps=resolution_steps or list(steps),
        field_errors=field_errors,
    )


def payment_reference_required():
    return registry_error(
        "RECEIPT_PAYMENT_REFERENCE_REQUIRED",
        field_errors={"payment_reference": ["A payment reference is required for this payment mode."]},
    )


def bank_account_required():
    return registry_error(
        "RECEIPT_BANK_ACCOUNT_REQUIRED",
        field_errors={"bank_account": ["A bank account is required for this payment mode."]},
    )


def document_not_found():
    return registry_error("RECEIPT_DOCUMENT_NOT_FOUND")


def ticket_invalid(message=None):
    return registry_error("RECEIPT_TICKET_INVALID", message=message)


def file_missing():
    return registry_error("RECEIPT_FILE_MISSING")


def import_row_invalid(message=None, field_errors=None):
    return registry_error("RECEIPT_IMPORT_ROW_INVALID", message=message, field_errors=field_errors)


def import_duplicate(message=None, field_errors=None):
    return registry_error("RECEIPT_IMPORT_DUPLICATE", message=message, field_errors=field_errors)


def import_partial_failure(message=None, details=None):
    return registry_error("RECEIPT_IMPORT_PARTIAL_FAILURE", message=message, details=details)


def import_batch_not_found():
    return registry_error("RECEIPT_IMPORT_BATCH_NOT_FOUND")
