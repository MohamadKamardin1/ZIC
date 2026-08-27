# ZIC Ordinary Life Loans Error Codes

## Structured error contract

Every user-facing OL Loans failure is returned in the platform Error Coach shape. The `error_code` is stable for programmatic handling; `message` explains the immediate issue; `field_errors` identifies fields to correct; `details` contains safe diagnostic values; `resolution_steps` teaches the user what to do next; and `doc_ref` points to the governing documentation.

```json
{
  "error_code": "LOAN_REPAYMENT_OVERPAYMENT",
  "message": "Repayment amount 750001.00 exceeds the loan outstanding balance of 750000.00 TZS.",
  "field_errors": {"amount": ["Enter no more than 750000.00 TZS."]},
  "details": {
    "requested_amount": "750001.00",
    "outstanding_balance": "750000.00",
    "currency": "TZS"
  },
  "resolution_steps": [
    "Reduce the repayment to 750000.00 TZS or less.",
    "Ask Finance to confirm the current balance before retrying."
  ],
  "doc_ref": "docs/OL_LOANS_DESIGN.md"
}
```

## Error catalogue

| Error code | HTTP | Meaning | User resolution |
| --- | ---: | --- | --- |
| `LOAN_NOT_FOUND` | 404 | The loan resource cannot be found or is not visible. | Verify the human-readable loan number, clear restrictive filters, and retry. |
| `PERMISSION_DENIED` | 403 | The current user lacks the required OL Loans action permission. | Ask User Management to assign the relevant `ol_loans.*` permission. |
| `LOAN_INELIGIBLE` | 422 | Policy state, product allowance, request amount, repayment mode, term, currency, or required field is invalid. | Follow the field error and confirm the effective policy/product/loan configuration. |
| `LOAN_EXCEEDS_LIMIT` | 422 | Requested amount is above the cash-value or configured maximum, or below the minimum. | Use the maximum/minimum shown in `details` and review OL Loan System Setup. |
| `LOAN_ACTIVE_EXISTS` | 409 | The policy already has an active or otherwise uncleared loan. | Review the existing loan; repay, settle, or offset it before requesting another loan. |
| `LOAN_INVALID_STATUS` | 409 | The action is not allowed from the current lifecycle state. | Complete the preceding lifecycle action or use the retry result for an existing record. |
| `LOAN_DISBURSEMENT_FAILED` | 422/409 | Payment mode, account, repayment schedule, or disbursement setup is missing or invalid. | Activate the payment rule/account and supported schedule method, then retry. |
| `LOAN_REPAYMENT_OVERPAYMENT` | 422 | Applied repayment would exceed the outstanding balance. | Reduce the amount to the current balance or less. |
| `LOAN_OFFSET_INVALID` | 409/422 | Payout reference, payout amount, loan state, or balance cannot support an offset. | Use a valid surrender, maturity, or claim reference and verify that the loan is unsettled. |
| `LOAN_PARAMETER_MISSING` | 422 | No effective Loan System Setup or Interest Control can be resolved. | Configure and activate both rows under Ordinary Life Parameters > Loan Setup / Interest Control. |

## Validation and retry rules

A failed transaction is rolled back. A validation failure must not create a loan, disbursement, repayment, accrual, or offset row. The response should be shown beside the affected form field and in the Error Coach panel.

A retry with the same idempotency key returns the original successful result when the original operation committed. It does not create a second financial record. A key reused for a different loan is rejected as an unsafe request.

The disbursement service checks for an existing release before creating a new requisition. The repayment service checks the idempotency key and receipt reference before allocation. The offset service checks the unique `(loan, source_type, source_id)` tuple before deduction.

## Release proof mapping

| Release proof | Captured code or result |
| --- | --- |
| Cancelled/ineligible policy request | `LOAN_INELIGIBLE` |
| Amount above cash-value limit | `LOAN_EXCEEDS_LIMIT` |
| Repayment above outstanding balance | `LOAN_REPAYMENT_OVERPAYMENT` |
| Offset against settled loan | `LOAN_OFFSET_INVALID` |
| Duplicate disbursement | `IDEMPOTENT_REPLAY` result with `created=false` and unchanged schedule count |

`IDEMPOTENT_REPLAY` is a release-evidence result label rather than a client error. The normal API response returns the existing disbursement resource and does not treat a safe retry as a failure.

## Security and information disclosure

Error details contain human-readable business references and safe configuration values only. They do not expose raw foreign-key UUIDs as labels, secrets, credentials, stack traces, or database statements. Portal access returns a sanitized not-found response when a partner cannot access a resource.

Unexpected settlement integration failures are logged with correlation metadata and re-raised so the surrounding transaction can roll back. A policy payout must not be committed while its required loan deduction has silently failed.
