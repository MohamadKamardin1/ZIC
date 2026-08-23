"""OL Proposals structured error helpers.

Follows the OL Commitments error convention; the shared handler in
``apps.core.exceptions`` renders the flat structured shape.
"""

from apps.core.exceptions import ZICAPIException
from apps.ol_commitments.errors import parameter_missing as commitments_parameter_missing

DOC_REF = "docs/OL_PROPOSALS_DESIGN.md"


class ProposalError(ZICAPIException):
    def __init__(
        self,
        message,
        *,
        error_code="PROPOSAL_ERROR",
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


def _error(code, message, *, status_code=422, steps=None, field_errors=None, details=None):
    return ProposalError(
        message,
        error_code=code,
        status_code=status_code,
        resolution_steps=steps,
        field_errors=field_errors,
        details=details,
    )


def partner_not_verified(partner_name="the policyholder"):
    return _error(
        "PROPOSAL_PARTNER_NOT_VERIFIED",
        f"{partner_name.capitalize()} is not partner-verified for this quotation.",
        steps=["Verify the partner under Partner Onboarding.", "Re-run the preference after verification."],
    )


def beneficiary_shares_invalid(total):
    return _error(
        "PROPOSAL_BENEFICIARY_SHARES_INVALID",
        f"Beneficiary shares must total 100%, currently {total:.2f}%.",
        steps=["Adjust each beneficiary share so the total is exactly 100%.", "Mark one beneficiary as primary."],
        field_errors={"beneficiaries": ["Shares must total 100%."]},
    )


def mandatory_documents_missing(missing):
    return _error(
        "PROPOSAL_MANDATORY_DOCUMENTS_MISSING",
        f"Missing mandatory documents: {', '.join(missing) or 'one or more items'}.",
        steps=["Upload each required document in the Documents step.", "Retry the action once all documents are uploaded."],
    )


def underwriting_pending():
    return _error(
        "PROPOSAL_UNDERWRITING_PENDING",
        "Underwriting has not cleared for this proposal.",
        steps=["Complete the underwriting review (medical requirements if raised).", "Clear the underwriting decision, then retry."],
    )


def not_payment_ready():
    return _error(
        "PROPOSAL_NOT_PAYMENT_READY",
        "This proposal is not payment-ready.",
        steps=["Complete enrichment and mandatory documents.", "Mark the proposal payment-ready, then retry."],
    )


def first_premium_not_posted():
    return _error(
        "PROPOSAL_FIRST_PREMIUM_NOT_POSTED",
        "The first premium has not been posted against this proposal.",
        steps=["Open the proposal commitment in OL Commitments.", "Record the first-premium payment, then retry conversion."],
    )


def expired():
    return _error(
        "PROPOSAL_EXPIRED",
        "This proposal has expired and can no longer proceed.",
        steps=["Create a fresh proposal from a current quotation.", "Cancel this proposal to close it out."],
    )


def already_converted():
    return _error(
        "PROPOSAL_ALREADY_CONVERTED",
        "This proposal has already been converted to a policy.",
        steps=["Open the converted policy to continue servicing."],
    )


def invalid_transition(action, status, allowed=None):
    allowed_list = allowed or []
    steps = []
    if allowed_list:
        steps.append(f"Allowed next states for '{status}': {', '.join(allowed_list)}.")
    steps.append(f"'{action}' is not allowed while the proposal is '{status}'.")
    return _error(
        "PROPOSAL_INVALID_TRANSITION",
        f"Cannot '{action}' from proposal status '{status}'.",
        steps=steps,
    )


def parameter_missing(parameter_label, navigation_path=None):
    return commitments_parameter_missing(parameter_label, navigation_path)