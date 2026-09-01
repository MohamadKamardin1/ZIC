from apps.core.exceptions import ZICAPIException

DOC_REF = "docs/OL_MATURITY_INSTALLMENTS_DESIGN.md"


INSTALLMENT_ERROR_REGISTRY = {
    "PLAN_POLICY_NOT_MATURED": {
        "message": "An installment plan can only be created against a matured policy.",
        "status_code": 422,
        "resolution_steps": [
            "Confirm the policy status is Matured or Matured pending payment before creating an installment plan.",
            "Ask Policy Administration to process the maturity event if the policy has not been matured yet.",
        ],
    },
    "PLAN_CALCULATION_MISMATCH": {
        "message": "The installment schedule does not reconcile to the maturity value.",
        "status_code": 422,
        "resolution_steps": [
            "Verify that the sum of all installment amounts equals the total payable amount and the maturity value.",
            "Review the calculation basis snapshot and the installment rate parameters, then regenerate the schedule.",
        ],
    },
    "INSTALLMENT_ALREADY_PAID": {
        "message": "This installment has already been paid and cannot be processed again.",
        "status_code": 409,
        "resolution_steps": [
            "Open the paid installment record to review its payment reference and Front Office requisition.",
            "Raise a new disbursement only for an installment that is still payable.",
        ],
    },
    "INSTALLMENT_PAYOUT_FAILED": {
        "message": "The Front Office disbursement for this installment could not be completed.",
        "status_code": 502,
        "resolution_steps": [
            "Check the linked Front Office requisition status and correct the bank or payment details.",
            "Retry the disbursement once the Front Office requisition is ready, or contact Finance Operations.",
        ],
    },
    "PLAN_PARAMETER_MISSING": {
        "message": "A required installment or paid-up rate parameter is missing for this policy.",
        "status_code": 422,
        "resolution_steps": [
            "Open OL Policy Setup > Product Rating and add the installment rate or paid-up rate for the product and plan.",
            "Confirm the effective date covers the plan start date, then retry plan creation.",
        ],
    },
    "INSTALLMENT_PLAN_NOT_FOUND": {
        "message": "The requested maturity installment plan could not be found.",
        "status_code": 404,
        "resolution_steps": [
            "Return to the installment plans register and search by plan number.",
            "Contact Policy Administration if the plan was recently migrated or archived.",
        ],
    },
    "INSTALLMENT_ITEM_NOT_FOUND": {
        "message": "The requested installment item could not be found.",
        "status_code": 404,
        "resolution_steps": [
            "Open the parent installment plan and select a valid installment item.",
            "Refresh the plan to confirm the current list of installments before retrying.",
        ],
    },
    "INSTALLMENT_PLAN_INVALID_STATUS": {
        "message": "This installment plan action is not allowed in its current status.",
        "status_code": 422,
        "resolution_steps": [
            "Refresh the plan and review its current lifecycle status.",
            "Complete the required preceding workflow step before retrying.",
        ],
    },
    "INSTALLMENT_ITEM_INVALID_STATUS": {
        "message": "This installment item action is not allowed in its current status.",
        "status_code": 422,
        "resolution_steps": [
            "Refresh the installment item and review its current status.",
            "Process the item only when it is scheduled, payment pending, or missed.",
        ],
    },
    "INSTALLMENT_INVALID_FILTER": {
        "message": "The installment plan list filter is invalid.",
        "status_code": 400,
        "resolution_steps": [
            "Correct the highlighted date, page, or page-size filter.",
            "Retry the search using the documented format and supported range.",
        ],
    },
    "INSTALLMENT_INVALID_FREQUENCY": {
        "message": "The requested installment payout frequency is not supported.",
        "status_code": 400,
        "resolution_steps": [
            "Choose a frequency from the maturity installments options endpoint.",
            "Confirm the frequency is a valid maturity payout option (single, monthly, quarterly, half yearly, or annual).",
        ],
    },
    "INSTALLMENT_INVALID_TERM": {
        "message": "The requested installment payout term is not valid.",
        "status_code": 400,
        "resolution_steps": [
            "Choose a term in whole years from the maturity installments options endpoint.",
            "Confirm the term is covered by the installment rate table for the product and plan.",
        ],
    },
    "INSTALLMENT_INVALID_AMOUNT": {
        "message": "The maturity value provided for the installment schedule is not a valid amount.",
        "status_code": 400,
        "resolution_steps": [
            "Provide the maturity value as a non-negative numeric amount.",
            "Confirm the amount against the approved maturity claim, then retry.",
        ],
    },
    "INSTALLMENT_IDEMPOTENCY_REQUIRED": {
        "message": "An idempotency key is required to create a maturity installment plan.",
        "status_code": 400,
        "resolution_steps": [
            "Send a unique X-Idempotency-Key header with the creation request.",
            "Reuse that same key only for the same unchanged submission.",
        ],
    },
    "INSTALLMENT_IDEMPOTENCY_CONFLICT": {
        "message": "The idempotency key was already used for a different maturity installment plan.",
        "status_code": 409,
        "resolution_steps": [
            "Use a new X-Idempotency-Key for this different submission.",
            "Retrieve the existing plan when you intended to resubmit the original request.",
        ],
    },
    "INSTALLMENT_POLICY_NOT_FOUND": {
        "message": "The selected policy could not be found.",
        "status_code": 404,
        "resolution_steps": [
            "Confirm the policy id and retry plan creation.",
            "Contact Policy Administration if the policy was recently migrated or archived.",
        ],
    },
    "INSTALLMENT_CLAIM_NOT_FOUND": {
        "message": "The selected maturity claim could not be found.",
        "status_code": 404,
        "resolution_steps": [
            "Confirm the maturity claim id and retry plan creation.",
            "Open the policy to review the maturity claims register.",
        ],
    },
    "INSTALLMENT_CLAIM_MISMATCH": {
        "message": "The selected maturity claim does not belong to the selected policy.",
        "status_code": 422,
        "resolution_steps": [
            "Choose a maturity claim that belongs to the selected policy.",
            "Retry plan creation with a matching policy and claim pair.",
        ],
    },
    "INSTALLMENT_CLAIM_NOT_SETTLED": {
        "message": "The selected maturity claim has not been settled yet.",
        "status_code": 422,
        "resolution_steps": [
            "Approve or settle the maturity claim before creating an installment plan.",
            "Ask Policy Administration to complete the claim settlement, then retry.",
        ],
    },
    "INSTALLMENT_INVALID_CREATION": {
        "message": "The maturity installment plan creation request needs correction.",
        "status_code": 400,
        "resolution_steps": [
            "Correct each highlighted plan field.",
            "Select a matured policy and a supported frequency and term before retrying.",
        ],
    },
    "INSTALLMENT_PAYMENT_NOT_DUE": {
        "message": "This installment cannot be paid before its due date.",
        "status_code": 422,
        "resolution_steps": [
            "Wait until the installment due date before raising the disbursement.",
            "Review the plan schedule to confirm the correct installment is being paid.",
        ],
    },
    "INSTALLMENT_BANK_DETAILS_MISSING": {
        "message": "No valid bank account is on record for the policyholder's disbursement.",
        "status_code": 422,
        "resolution_steps": [
            "Add or verify a primary bank account for the policyholder before processing the payment.",
            "Ask the policyholder to provide correct bank details, then retry the disbursement.",
        ],
    },
    "INSTALLMENT_REVERSAL_REASON_REQUIRED": {
        "message": "A reason is required to reverse an installment payment.",
        "status_code": 400,
        "resolution_steps": [
            "Explain why the paid installment is being reversed.",
            "Reference the correction, dispute, or processing error that triggered the reversal.",
        ],
    },
    "INSTALLMENT_REVERSAL_NOT_ALLOWED": {
        "message": "Only a paid installment within the configured window can be reversed.",
        "status_code": 422,
        "resolution_steps": [
            "Confirm the installment status is Paid before reversing it.",
            "An installment that was already reversed is no longer paid and cannot be reversed again.",
            "Re-process the installment after the reversal if the disbursement must go ahead.",
        ],
    },
    "INSTALLMENT_REVERSAL_WINDOW_EXPIRED": {
        "message": "This installment payment is outside the configured reversal window.",
        "status_code": 422,
        "resolution_steps": [
            "Review the reversal window configured for maturity installments in System Parameters.",
            "Raise a correction request through Finance Operations when the window has closed.",
        ],
    },
    "INSTALLMENT_CANCELLATION_REASON_REQUIRED": {
        "message": "A reason is required to cancel a maturity installment plan.",
        "status_code": 400,
        "resolution_steps": [
            "Explain why the entire installment plan is being cancelled.",
            "Reference the underlying policy event or the operator decision that triggered the cancellation.",
        ],
    },
    "INSTALLMENT_PLAN_CANNOT_CANCEL": {
        "message": "This maturity installment plan cannot be cancelled in its current state.",
        "status_code": 422,
        "resolution_steps": [
            "Refresh the plan and review its current lifecycle status.",
            "A completed, terminated, or already-cancelled plan is terminal and cannot be cancelled.",
        ],
    },
    "INSTALLMENT_PLAN_IRREVOCABLE": {
        "message": "This plan has paid installments that are irrevocable under the configured parameters.",
        "status_code": 409,
        "resolution_steps": [
            "Review the irrevocable-payment parameter configured for maturity installments in System Parameters.",
            "Ask an authorised administrator to adjust the parameter or to handle the correction manually.",
        ],
    },
}


class MaturityInstallmentError(ZICAPIException):
    """Structured exception for the OL Maturity Installments bounded context."""

    def __init__(
        self,
        message=None,
        *,
        error_code="INSTALLMENT_ERROR",
        status_code=400,
        resolution_steps=None,
        field_errors=None,
        details=None,
    ):
        definition = INSTALLMENT_ERROR_REGISTRY.get(error_code, {})
        super().__init__(
            message=message or definition.get("message", "The installment request could not be completed."),
            code=error_code,
            status_code=status_code if status_code != 400 or not definition else definition["status_code"],
            details=details,
            error_code=error_code,
            resolution_steps=resolution_steps
            if resolution_steps is not None
            else definition.get("resolution_steps", []),
            field_errors=field_errors,
            doc_ref=DOC_REF,
        )


def registry_error(error_code, *, message=None, details=None, resolution_steps=None, field_errors=None):
    definition = INSTALLMENT_ERROR_REGISTRY.get(error_code)
    if not definition:
        raise ValueError(f"Unknown maturity installment error code: {error_code}")
    return MaturityInstallmentError(
        message=message,
        error_code=error_code,
        status_code=definition["status_code"],
        resolution_steps=resolution_steps,
        field_errors=field_errors,
        details=details,
    )


def not_found():
    return registry_error("INSTALLMENT_PLAN_NOT_FOUND")
