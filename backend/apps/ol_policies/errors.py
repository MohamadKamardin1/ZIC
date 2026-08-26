from apps.core.exceptions import ZICAPIException

DOC_REF = "docs/OL_POLICIES_DESIGN.md"


POLICY_ERROR_REGISTRY = {
    "POLICY_NOT_FOUND": {
        "message": "The requested policy could not be found.",
        "status_code": 404,
        "resolution_steps": [
            "Verify the policy identifier or policy number.",
            "Clear restrictive list filters and search again.",
            "Contact Policy Administration if the policy was archived or migrated.",
        ],
    },
    "POLICY_ALREADY_ISSUED": {
        "message": "This proposal has already been issued as a policy.",
        "status_code": 409,
        "resolution_steps": [
            "Open the existing policy linked to the proposal.",
            "Do not retry issuance unless the existing policy link is verified as incorrect.",
        ],
    },
    "POLICY_INVALID_STATUS": {
        "message": "The requested policy action is not allowed in the current status.",
        "status_code": 422,
        "resolution_steps": [
            "Review the policy status and its permitted lifecycle actions.",
            "Complete any required payment, approval, or reinstatement step first.",
        ],
    },
    "POLICY_SURRENDER_BLOCKED": {
        "message": "The policy is not eligible for surrender under the active policy parameters.",
        "status_code": 422,
        "resolution_steps": [
            "Review the policy surrender eligibility parameters.",
            "Settle any active loan or other blocking financial obligation.",
        ],
    },
    "POLICY_LOAN_BLOCKED": {
        "message": "A loan action is not allowed for this policy.",
        "status_code": 422,
        "resolution_steps": [
            "Confirm that the product supports policy loans.",
            "Confirm that the policy is in an eligible in-force status and has sufficient cash value.",
        ],
    },
    "POLICY_LAPSED": {
        "message": "The policy is lapsed and cannot complete this action without reinstatement.",
        "status_code": 422,
        "resolution_steps": [
            "Review outstanding commitments and the applicable grace period.",
            "Use the reinstatement process if the policy is still within its permitted window.",
        ],
    },
    "POLICY_NOT_MATURED": {
        "message": "The policy has not reached its maturity date.",
        "status_code": 422,
        "resolution_steps": [
            "Check the risk commencement date and maturity date on the policy.",
            "Wait until the configured maturity date before processing maturity benefits.",
        ],
    },
    "POLICY_ENDORSEMENT_INVALID": {
        "message": "The requested policy endorsement is invalid.",
        "status_code": 422,
        "resolution_steps": [
            "Review the endorsement type and effective date.",
            "Provide the required before-and-after values and confirm the policy is eligible for servicing.",
        ],
    },
}


class PolicyError(ZICAPIException):
    """Structured exception for the OL Policies bounded context."""

    def __init__(
        self,
        message=None,
        *,
        error_code="POLICY_ERROR",
        status_code=400,
        resolution_steps=None,
        field_errors=None,
        details=None,
    ):
        definition = POLICY_ERROR_REGISTRY.get(error_code, {})
        super().__init__(
            message=message or definition.get("message", "The policy request could not be completed."),
            code=error_code,
            status_code=status_code if status_code != 400 or not definition else definition["status_code"],
            details=details,
            error_code=error_code,
            resolution_steps=resolution_steps if resolution_steps is not None else definition.get("resolution_steps", []),
            field_errors=field_errors,
            doc_ref=DOC_REF,
        )


def registry_error(error_code, *, message=None, details=None, resolution_steps=None, field_errors=None):
    definition = POLICY_ERROR_REGISTRY.get(error_code)
    if not definition:
        raise ValueError(f"Unknown policy error code: {error_code}")
    return PolicyError(
        message=message,
        error_code=error_code,
        status_code=definition["status_code"],
        resolution_steps=resolution_steps,
        field_errors=field_errors,
        details=details,
    )


def not_found(policy_id=None):
    identifier = f" ({policy_id})" if policy_id else ""
    return registry_error(
        "POLICY_NOT_FOUND",
        message=f"Policy{identifier} could not be found.",
    )


def invalid_status(current_status, action):
    return registry_error(
        "POLICY_INVALID_STATUS",
        message=f"Policy status '{current_status}' does not allow the action '{action}'.",
        details={"current_status": current_status, "action": action},
    )
