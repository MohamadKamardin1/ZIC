from apps.core.exceptions import ZICAPIException


DOC_REF = "docs/OL_CLAIMS_DESIGN.md"


CLAIM_ERROR_REGISTRY = {
    "CLAIM_INVALID_REGISTRATION": {
        "message": "The claim registration form needs correction before it can be submitted.",
        "status_code": 400,
        "resolution_steps": [
            "Correct each highlighted claim field.",
            "Select a configured claim type and provide claimant information before retrying.",
        ],
    },
    "CLAIM_IDEMPOTENCY_REQUIRED": {
        "message": "An idempotency key is required to register a claim safely.",
        "status_code": 400,
        "resolution_steps": [
            "Retry the request with a unique X-Idempotency-Key header.",
            "Reuse the same key when retrying the same submission so the original claim is returned.",
        ],
    },
    "CLAIM_IDEMPOTENCY_CONFLICT": {
        "message": "This idempotency key was already used for a different claim submission.",
        "status_code": 409,
        "resolution_steps": [
            "Use the existing claim returned for the original key, or generate a new key for a new submission.",
            "Do not reuse a key after changing policy, claim type, or claim date.",
        ],
    },
    "CLAIM_CLAIMANT_REQUIRED": {
        "message": "Claimant information is required before the claim can be registered.",
        "status_code": 400,
        "resolution_steps": [
            "Select an issued policy member or provide claimant_details with a name and claimant_type.",
            "Verify the claimant relationship and identity information before retrying.",
        ],
    },
    "CLAIM_TYPE_NOT_CONFIGURED": {
        "message": "The selected claim type is not configured for current use.",
        "status_code": 422,
        "resolution_steps": [
            "Choose an active claim type from the Claims parameters catalog.",
            "Ask Claims Configuration to activate or effective-date the required claim type.",
        ],
    },
    "CLAIM_INVALID_DATE": {
        "message": "The claim date is invalid.",
        "status_code": 400,
        "resolution_steps": [
            "Enter a real calendar date in the policy service period.",
            "Use the date format YYYY-MM-DD when calling the API.",
        ],
    },
    "CLAIM_POLICY_REQUIRED": {
        "message": "A policy is required to load claim-specific options.",
        "status_code": 400,
        "resolution_steps": [
            "Select a policy before loading covered benefits or members.",
            "Retry the options request with the policy_id query parameter.",
        ],
    },
    "CLAIM_POLICY_NOT_FOUND": {
        "message": "The requested policy could not be found for claim options.",
        "status_code": 404,
        "resolution_steps": [
            "Select an existing policy from the policy search results.",
            "Ask Policy Administration to verify the policy reference if it was recently migrated.",
        ],
    },
    "CLAIM_POLICY_INACTIVE": {
        "message": "This policy is not active and cannot receive a new claim.",
        "status_code": 422,
        "resolution_steps": [
            "Review the policy status and effective dates.",
            "Reinstate or correct the policy before registering a claim if the contract permits it.",
        ],
    },
    "CLAIM_DUPLICATE": {
        "message": "A claim of this type has already been settled for this claimant and policy.",
        "status_code": 409,
        "resolution_steps": [
            "Search the policy claim history before creating another request.",
            "Open the existing claim if a correction or follow-up is required.",
        ],
    },
    "CLAIM_WAITING_PERIOD_ACTIVE": {
        "message": "The claim date falls within the configured waiting period.",
        "status_code": 422,
        "resolution_steps": [
            "Check the policy risk commencement date and the selected claim date.",
            "Retry only after the waiting period has ended, unless an approved exception applies.",
        ],
    },
    "CLAIM_BENEFIT_NOT_COVERED": {
        "message": "The selected claim type or benefit is not covered by this policy.",
        "status_code": 422,
        "resolution_steps": [
            "Review the policy benefits and select a covered claim type.",
            "Ask Product Administration to verify the policy benefit configuration if the coverage is expected.",
        ],
    },
    "CLAIM_MANDATORY_DOC_MISSING": {
        "message": "One or more mandatory claim documents are missing.",
        "status_code": 422,
        "resolution_steps": [
            "Open the claim Documents section and upload every required document.",
            "Verify that each uploaded file is linked to the correct document type before continuing.",
        ],
    },
    "CLAIM_AMOUNT_EXCEEDS_LIMIT": {
        "message": "The requested claim amount exceeds the calculated benefit limit.",
        "status_code": 422,
        "resolution_steps": [
            "Review the calculated amount for each claim item.",
            "Enter an assessed amount at or below the calculated maximum, or document an approved adjustment.",
        ],
    },
    "CLAIM_INVALID_FILTER": {
        "message": "The claim list filter is invalid.",
        "status_code": 400,
        "resolution_steps": [
            "Correct the highlighted date, page, or page-size filter.",
            "Retry the search using the documented format and supported range.",
        ],
    },
    "CLAIM_NOT_FOUND": {
        "message": "The requested claim could not be found.",
        "status_code": 404,
        "resolution_steps": [
            "Return to the Claims register and search by claim number.",
            "Contact Claims Administration if the claim was recently migrated or archived.",
        ],
    },
    "CLAIM_INVALID_STATUS": {
        "message": "This claim action is not allowed in its current status.",
        "status_code": 422,
        "resolution_steps": [
            "Refresh the claim and review its current lifecycle status.",
            "Complete the required preceding workflow step before retrying.",
        ],
    },
}


class ClaimError(ZICAPIException):
    """Structured exception for the OL Claims bounded context."""

    def __init__(
        self,
        message=None,
        *,
        error_code="CLAIM_ERROR",
        status_code=400,
        resolution_steps=None,
        field_errors=None,
        details=None,
    ):
        definition = CLAIM_ERROR_REGISTRY.get(error_code, {})
        super().__init__(
            message=message or definition.get("message", "The claim request could not be completed."),
            code=error_code,
            status_code=status_code if status_code != 400 or not definition else definition["status_code"],
            details=details,
            error_code=error_code,
            resolution_steps=resolution_steps if resolution_steps is not None else definition.get("resolution_steps", []),
            field_errors=field_errors,
            doc_ref=DOC_REF,
        )


def registry_error(error_code, *, message=None, details=None, resolution_steps=None, field_errors=None):
    definition = CLAIM_ERROR_REGISTRY.get(error_code)
    if not definition:
        raise ValueError(f"Unknown claim error code: {error_code}")
    return ClaimError(
        message=message,
        error_code=error_code,
        status_code=definition["status_code"],
        resolution_steps=resolution_steps,
        field_errors=field_errors,
        details=details,
    )


def not_found():
    return registry_error("CLAIM_NOT_FOUND")
