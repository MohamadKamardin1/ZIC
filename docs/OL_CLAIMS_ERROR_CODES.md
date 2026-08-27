# ZIC Ordinary Life Claims Error Codes

## Error Coach contract

Every Claims API failure is returned as a structured Error Coach response. Clients should display `message`, render `field_errors` next to the relevant input, and show `resolution_steps` as the next actions. The `error_code` is stable for programmatic handling. `details` may contain operational values such as claim number, allowed amount, or current status; it must not be treated as client-side authority.

```json
{
  "success": false,
  "error_code": "CLAIM_ASSESSMENT_AMOUNT_INVALID",
  "message": "The assessed amount is invalid or exceeds the calculated claim limit.",
  "resolution_steps": ["Enter an amount through the calculated maximum."],
  "field_errors": {"assessed_amount": ["Review the claim benefit breakdown."]},
  "details": {"claim_number": "CLM-...", "calculated_maximum": "50000000.00"}
}
```

## Registration and eligibility

| Code | Meaning | Resolution |
|---|---|---|
| `CLAIM_INVALID_REGISTRATION` | The registration payload is incomplete or malformed. | Correct the named fields and resubmit. |
| `CLAIM_IDEMPOTENCY_REQUIRED` | Registration did not include an idempotency key. | Send a stable `X-Idempotency-Key` for the intended submission. |
| `CLAIM_IDEMPOTENCY_CONFLICT` | The same idempotency key was used with a different payload. | Use a new key only for a genuinely new claim; otherwise restore the original payload. |
| `CLAIM_CLAIMANT_REQUIRED` | A claimant could not be identified or the claimant details are incomplete. | Select a policy member or provide the required claimant details. |
| `CLAIM_POLICY_REQUIRED` | No policy was selected. | Select the eligible policy identified by policy number. |
| `CLAIM_POLICY_NOT_FOUND` | The supplied policy number or reference does not exist. | Confirm the policy number and access scope. |
| `CLAIM_POLICY_INACTIVE` | The policy is not eligible for a new claim. | Confirm policy status, premium position, or configured lapsed grace. |
| `CLAIM_TYPE_NOT_CONFIGURED` | No effective active claim type matches the selection. | Ask an authorized administrator to configure an effective claim type. |
| `CLAIM_INVALID_DATE` | The claim date is missing or invalid. | Enter a valid claim date in the required format. |
| `CLAIM_DUPLICATE` | A settled claim already matches the configured duplicate rule. | Review the existing claim before starting another submission. |
| `CLAIM_WAITING_PERIOD_ACTIVE` | The claim date falls within the configured waiting period. | Confirm the policy risk commencement date and submit only after the effective eligibility date, unless an authorized exception applies. |
| `CLAIM_BENEFIT_NOT_COVERED` | The selected claim benefit is not covered by the policy. | Select a covered benefit or review the policy coverage configuration. |

## Evidence, medical, and assessment

| Code | Meaning | Resolution |
|---|---|---|
| `CLAIM_DOCUMENT_REQUIRED` | A document upload did not identify a document type or file. | Choose a configured document type and attach the evidence. |
| `CLAIM_DOCUMENT_TOO_LARGE` | The uploaded file exceeds the configured size limit. | Compress the file or upload an accepted smaller document. |
| `CLAIM_MANDATORY_DOC_MISSING` | Assessment or progression is blocked by missing mandatory evidence. | Upload every document listed in the readiness response. |
| `CLAIM_MEDICAL_REVIEW_REQUIRED` | Medical review must be completed before assessment. | Complete the Medical Review section and record an outcome. |
| `CLAIM_MEDICAL_REJECTED` | The medical decision rejects progression. | Review the medical reason and follow the authorized escalation process. |
| `CLAIM_INVALID_MEDICAL_STATUS` | The requested medical state is unsupported. | Choose a configured medical status. |
| `CLAIM_INVALID_MEDICAL_RESULT` | The medical result is incomplete or unsupported. | Choose Cleared, Loading, or Rejected and provide any required reason or factor. |
| `CLAIM_LOADING_FACTOR_INVALID` | The medical loading factor is outside the configured range. | Enter a valid configured loading factor. |
| `CLAIM_ASSESSMENT_REQUIRED` | Assessment notes or amount are missing. | Enter findings and the benefit assessment before saving. |
| `CLAIM_ASSESSMENT_AMOUNT_INVALID` | The assessed amount is negative, malformed, or above the calculated maximum. | Review the item-level calculated amount and enter an amount from zero through that maximum. |
| `CLAIM_AMOUNT_EXCEEDS_LIMIT` | A requested or approved amount exceeds a configured benefit limit. | Reduce the amount or correct the policy/benefit configuration. |
| `CLAIM_FRAUD_REASON_REQUIRED` | Fraud review is enabled without a reason. | Record the evidence or control exception that triggered review. |
| `CLAIM_WAIVER_INPUT_INVALID` | Waiver-of-premium input is invalid or not permitted. | Enter a non-negative permitted period and verify the claim type allows waiver. |
| `CLAIM_NOTE_REQUIRED` | An internal note is empty. | Record the operational observation or decision to retain in the claim file. |

## Payment requisition and settlement

| Code | Meaning | Resolution |
|---|---|---|
| `CLAIM_REQUISITION_REQUIRED` | A payment requisition is required before settlement. | Raise and submit the claim payment requisition. |
| `CLAIM_REQUISITION_NET_ZERO` | No positive amount remains payable after loan offset. | Review the approved amount and outstanding loan balances; do not raise a zero-value payment request. |
| `CLAIM_REQUISITION_BANK_DETAILS_REQUIRED` | Payment bank details are missing. | Provide verified claimant or partner bank details. |
| `CLAIM_REQUISITION_ALREADY_EXISTS` | A requisition already exists for the claim. | Open the existing requisition instead of creating a second one. |
| `CLAIM_SETTLEMENT_NOT_READY` | The current claim status does not permit settlement. | Complete assessment, requisition, approval, and payment steps in order. |
| `CLAIM_SETTLEMENT_REQUISITION_REQUIRED` | Settlement has no linked payment requisition. | Raise a requisition and confirm its Front Office link. |
| `CLAIM_SETTLEMENT_APPROVAL_REQUIRED` | The configured payment approval is still pending. | Complete the linked Governance approval request. |
| `CLAIM_SETTLEMENT_PAYMENT_NOT_CONFIRMED` | Front Office has not confirmed the payment. | Wait for or record a confirmed payment status from Front Office. |
| `CLAIM_SETTLEMENT_PAYMENT_REFERENCE_REQUIRED` | Settlement has no payment reference. | Enter the reference generated by the payment process. |
| `CLAIM_APPROVAL_OUTCOME_INVALID` | Approval outcome cannot be applied from the current state. | Refresh the linked approval request and apply only the permitted outcome. |
| `CLAIM_INVALID_STATUS` | The requested action is not allowed in the current claim state. | Review the lifecycle state and complete its preceding action. |

## Financial summary and access

| Code | Meaning | Resolution |
|---|---|---|
| `CLAIM_FINANCIAL_SUMMARY_UNAVAILABLE` | No positive approved amount exists for a meaningful financial summary. | Complete assessment and approve a positive item amount, then refresh Financial Summary. |
| `CLAIM_NOT_FOUND` | The requested claim is not available. | Confirm the claim number and user access. |
| `PORTAL_RESOURCE_NOT_FOUND` | A partner portal user requested a claim or policy outside its linked partner scope. | Confirm the partner relationship and use a claim or policy belonging to that partner. |

## Error handling rules

A frontend must not replace a structured response with a generic “Something went wrong” message. If the response includes `field_errors`, map those errors to fields. If the error is a state or integration failure, show the main `message`, list the `resolution_steps`, preserve the correlation/request ID for support, and refresh the claim before retrying.

A repeated request should first be checked for an existing result. Registration, loan offset, requisition creation, approval outcome, and settlement are designed to be idempotent or conflict-safe. Never retry a financial action by changing the payload merely to bypass an idempotency conflict.

## Escalation information

When escalation is required, provide the claim number, policy number, error code, request/correlation ID, source channel, timestamp, and the last visible lifecycle state. Do not send passwords, access tokens, or raw UUIDs in email or support notes. Administrators can use the central audit timeline and DomainEvent outbox to investigate the complete transition history.
