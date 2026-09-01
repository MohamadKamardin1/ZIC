from apps.core.exceptions import ZICAPIException

DOC_REF = "docs/GC_PARAMETERS_DESIGN.md"


GC_PARAMETERS_ERROR_REGISTRY = {
    "SCHEME_NOT_FOUND": {
        "message": "The scheme type could not be found.",
        "status_code": 404,
        "resolution_steps": [
            "Select an existing scheme type from the Scheme Setup catalog.",
            "Ask Scheme Configuration to verify the scheme type reference if it was recently migrated.",
        ],
    },
    "PRODUCT_INVALID_SCHEME": {
        "message": "A GC product must reference a valid, active scheme type.",
        "status_code": 422,
        "resolution_steps": [
            "Choose an active scheme type from the Scheme Setup catalog.",
            "If the scheme type was deactivated, reactivate it before assigning it to a product.",
        ],
    },
    "RATE_MISMATCH": {
        "message": "The rider or premium rate value is inconsistent with its rate type or effective window.",
        "status_code": 422,
        "resolution_steps": [
            "Enter a non-negative rate value; a PERCENTAGE rate must be above zero and no greater than 100.",
            "Confirm the effective-from date is on or before the effective-to date.",
        ],
    },
    "PRODUCT_NOT_FOUND": {
        "message": "The requested GC product could not be found.",
        "status_code": 404,
        "resolution_steps": [
            "Return to the Product catalog and select an existing product.",
            "Verify the product reference if it was recently migrated.",
        ],
    },
    "RIDER_NOT_FOUND": {
        "message": "The requested GC rider could not be found.",
        "status_code": 404,
        "resolution_steps": [
            "Return to the Rider catalog and select an existing rider.",
            "Verify the rider reference if it was recently migrated.",
        ],
    },
    "PRODUCT_CODE_CONFLICT": {
        "message": "A GC product with this code already exists.",
        "status_code": 409,
        "resolution_steps": [
            "Use a unique product code for the new product.",
            "Open the existing product if a correction or follow-up is required.",
        ],
    },
    "SCHEME_RATE_OVERLAP": {
        "message": "The premium rate effective window overlaps an existing rate for the same scheme type.",
        "status_code": 409,
        "resolution_steps": [
            "Choose an effective-from/effective-to window that does not overlap an existing active rate.",
            "Amend the effective dates of the conflicting rate before saving the new one.",
        ],
    },
    "PRODUCT_INVALID_LIMITS": {
        "message": "The product's entry-age band or free-cover limit is inconsistent with its cover limits.",
        "status_code": 422,
        "resolution_steps": [
            "Ensure min_entry_age does not exceed max_entry_age.",
            "Ensure the free cover limit does not exceed the maximum loan amount.",
        ],
    },
    "CLAIM_TYPE_DUPLICATE": {
        "message": "An active claim type with the same name already exists.",
        "status_code": 409,
        "resolution_steps": [
            "Use a distinct claim type name.",
            "Open the existing claim type if a correction or follow-up is required.",
        ],
    },
}


class GCParameterError(ZICAPIException):
    """Structured exception for the GC Parameters bounded context."""

    def __init__(
        self,
        message=None,
        *,
        error_code="GC_PARAMETERS_ERROR",
        status_code=400,
        resolution_steps=None,
        field_errors=None,
        details=None,
    ):
        definition = GC_PARAMETERS_ERROR_REGISTRY.get(error_code, {})
        super().__init__(
            message=message or definition.get("message", "The GC parameters request could not be completed."),
            code=error_code,
            status_code=status_code if status_code != 400 or not definition else definition["status_code"],
            details=details,
            error_code=error_code,
            resolution_steps=resolution_steps if resolution_steps is not None else definition.get("resolution_steps", []),
            field_errors=field_errors,
            doc_ref=DOC_REF,
        )


def registry_error(error_code, *, message=None, details=None, resolution_steps=None, field_errors=None):
    definition = GC_PARAMETERS_ERROR_REGISTRY.get(error_code)
    if not definition:
        raise ValueError(f"Unknown GC parameters error code: {error_code}")
    return GCParameterError(
        message=message,
        error_code=error_code,
        status_code=definition["status_code"],
        resolution_steps=resolution_steps,
        field_errors=field_errors,
        details=details,
    )


def scheme_not_found():
    return registry_error("SCHEME_NOT_FOUND")


def product_invalid_scheme():
    return registry_error("PRODUCT_INVALID_SCHEME")


def rate_mismatch():
    return registry_error("RATE_MISMATCH")


def scheme_rate_overlap(*, details=None):
    return registry_error("SCHEME_RATE_OVERLAP", details=details)


def product_invalid_limits(*, details=None):
    return registry_error("PRODUCT_INVALID_LIMITS", details=details)


def claim_type_duplicate(*, details=None):
    return registry_error("CLAIM_TYPE_DUPLICATE", details=details)
