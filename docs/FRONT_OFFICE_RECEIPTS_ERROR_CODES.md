# Front Office Receipts — Error Codes

**Registry:** `apps.front_office.receipts.errors.RECEIPT_ERROR_REGISTRY`
**Shape:** every error renders through the global exception handler
(`apps.core.exceptions.custom_exception_handler`) in the standard structured
Error Coach format.

Errors raised by the receipts module use the `ReceiptError` base exception with a
stable `error_code`. The BR-03 gate also surfaces a proposals-module error code
(`PROPOSAL_FIRST_PREMIUM_NOT_POSTED`) documented below.

---

## Standard structured shape

```json
{
  "error": {
    "code": "RECEIPT_OVERALLOCATION",
    "status_code": 422,
    "message": "The allocation exceeds the available balance of 100000.00.",
    "field_errors": {
      "amount": ["The allocation exceeds the available balance of 100000.00."]
    },
    "resolution_steps": [
      "Reduce the allocation amount to the unallocated balance.",
      "Create an additional receipt for the remaining amount."
    ],
    "details": {},
    "doc_ref": "docs/FRONT_OFFICE_RECEIPTS_DESIGN.md"
  }
}
```

- `field_errors` — per-field messages when the fault is input-bound.
- `resolution_steps` — operator guidance, always present.
- `details` — optional machine-readable context (parameter name, lock days, etc.).

---

## Receipt error registry

| Code | HTTP | Meaning |
| --- | --- | --- |
| `RECEIPT_NOT_FOUND` | 404 | The requested receipt does not exist. |
| `RECEIPT_INVALID_STATUS` | 422 | The action is not allowed in the current status. |
| `RECEIPT_AMOUNT_INVALID` | 422 | Amount is missing, zero, or negative. |
| `RECEIPT_ALLOCATION_INVALID` | 422 | Allocation details are invalid (target/amount). |
| `RECEIPT_OVERALLOCATION` | 422 | Allocation exceeds the receipt unallocated balance **or** the commitment outstanding balance. |
| `RECEIPT_ALREADY_POSTED` | 409 | Posting attempted on an already-posted receipt. |
| `RECEIPT_ALREADY_REVERSED` | 409 | Reversal attempted on a reversed receipt. |
| `RECEIPT_REASON_REQUIRED` | 422 | Reason missing for reversal/cancellation. |
| `RECEIPT_REVERSAL_LOCKED` | 422 | Receipt is older than `RECEIPT_REVERSAL_LOCK_DAYS` — outside the reversal window. |
| `RECEIPT_PAYMENT_REFERENCE_REQUIRED` | 422 | Payment mode rule requires a payment reference (e.g. bank transfer, M-PESA). |
| `RECEIPT_BANK_ACCOUNT_REQUIRED` | 422 | Payment mode rule requires the payer's bank account (e.g. bank transfer). |
| `RECEIPT_CURRENCY_MISMATCH` | 422 | Cross-currency allocation with no explicit or configured exchange rate. |
| `RECEIPT_PERMISSION_DENIED` | 403 | Actor lacks `front_office.receipts.<action>`. |
| `RECEIPT_PARAMETER_MISSING` | 422 | A required parameter/catalog entry is missing or inactive (deep link in `details`). |
| `RECEIPT_DOCUMENT_NOT_FOUND` | 404 | Receipt document does not exist. |
| `RECEIPT_TICKET_INVALID` | 403 | Download ticket invalid or expired. |
| `RECEIPT_FILE_MISSING` | 404 | Generated file absent from storage. |
| `RECEIPT_IMPORT_ROW_INVALID` | 422 | Import row failed validation (field errors included). |
| `RECEIPT_IMPORT_DUPLICATE` | 409 | Import contains duplicate rows. |
| `RECEIPT_IMPORT_PARTIAL_FAILURE` | 422 | Batch committed with some rows failing; failed rows are reprocessable. |
| `RECEIPT_IMPORT_BATCH_NOT_FOUND` | 404 | Import batch does not exist. |

---

## BR-03 gate error (proposals module)

| Code | HTTP | Meaning |
| --- | --- | --- |
| `PROPOSAL_FIRST_PREMIUM_NOT_POSTED` | 409 | The proposal cannot convert: the linked first-premium commitment is not `COMPLETED` (balance zero). Record and fully allocate the first-premium receipt, then retry. |

Raised by `apps.ol_proposals.services.first_premium_service.ensure_first_premium_posted`.
See [OL_PROPOSALS_RECEIPTS_SEAM.md](OL_PROPOSALS_RECEIPTS_SEAM.md) §3.

---

## Failure-proof payloads (Prompt 12)

The `receipt_failure_proofs` command captures each guard in action. Verified
payloads from the release seed:

| Proof | Outcome | Error payload |
| --- | --- | --- |
| Missing payment reference | caught | `RECEIPT_PAYMENT_REFERENCE_REQUIRED` (422), field `payment_reference`. |
| Over-allocation | caught | `RECEIPT_OVERALLOCATION` (422), "The allocation exceeds the available balance of 100000.00." |
| Cross-currency without rate | caught | `RECEIPT_CURRENCY_MISMATCH` (422), "No active exchange rate is configured from KES to TZS." |
| Allocation to completed commitment | caught | `RECEIPT_OVERALLOCATION` (422), "Amount cannot exceed balance of 0.00." |
| Reversal after lock period | caught | `RECEIPT_REVERSAL_LOCKED` (422), "The receipt is outside the configured 5 day reversal window." |

All five proofs are pinned in
`apps/front_office/receipts/tests/test_release_br03.py::FailureProofTests`.
