# OL Maturity Installments — Error Codes

Every error returned by the OL Maturity Installments module uses the structured
Error Coach envelope:

```json
{
  "error_code": "PLAN_POLICY_NOT_MATURED",
  "message": "An installment plan can only be created against a matured policy.",
  "status_code": 422,
  "details": { "policyNumber": "POL-SC-0001", "policyStatus": "ACTIVE" },
  "resolutionSteps": [
    "Confirm the policy status is Matured or Matured pending payment before creating an installment plan.",
    "Ask Policy Administration to process the maturity event if the policy has not been matured yet."
  ]
}
```

| Code | Status | When it is raised |
|------|--------|-------------------|
| `PLAN_POLICY_NOT_MATURED` | 422 | Creating a plan against a policy that is not matured, or whose maturity date is in the future. |
| `PLAN_CALCULATION_MISMATCH` | 422 | The generated schedule does not reconcile to the maturity value to the penny. |
| `INSTALLMENT_ALREADY_PAID` | 409 | A disbursement is attempted for an installment that is already paid. |
| `INSTALLMENT_PAYOUT_FAILED` | 502 | The Front Office disbursement for an installment could not complete. |
| `PLAN_PARAMETER_MISSING` | 422 | No active/effective installment or paid-up rate row applies to the policy/product/plan for the requested frequency and term. |
| `INSTALLMENT_PLAN_NOT_FOUND` | 404 | The requested plan id does not exist. |
| `INSTALLMENT_ITEM_NOT_FOUND` | 404 | The requested installment item id does not exist. |
| `INSTALLMENT_PLAN_INVALID_STATUS` | 422 | A plan-level action is not allowed in the plan's current lifecycle status. |
| `INSTALLMENT_ITEM_INVALID_STATUS` | 422 | An item-level action is not allowed in the item's current status (e.g. processing a `PAID` item). |
| `INSTALLMENT_INVALID_FILTER` | 400 | A list filter (date, page, page size, sort field) is malformed or out of range. |
| `INSTALLMENT_INVALID_FREQUENCY` | 400 | The requested payout frequency is not one of the supported options. |
| `INSTALLMENT_INVALID_TERM` | 400 | The requested term is not a supported whole-year term. |
| `INSTALLMENT_INVALID_AMOUNT` | 400 | The maturity value supplied is not a valid non-negative amount. |
| `INSTALLMENT_IDEMPOTENCY_REQUIRED` | 400 | Plan creation was called without an `X-Idempotency-Key`. |
| `INSTALLMENT_IDEMPOTENCY_CONFLICT` | 409 | The same idempotency key was reused with a different plan payload. |
| `INSTALLMENT_POLICY_NOT_FOUND` | 404 | The selected policy id does not exist. |
| `INSTALLMENT_CLAIM_NOT_FOUND` | 404 | The selected maturity claim id does not exist. |
| `INSTALLMENT_CLAIM_MISMATCH` | 422 | The selected maturity claim does not belong to the selected policy. |
| `INSTALLMENT_CLAIM_NOT_SETTLED` | 422 | The linked maturity claim is not `APPROVED`/`PAID`. |
| `INSTALLMENT_INVALID_CREATION` | 400 | The create-plan payload failed serializer validation. |
| `INSTALLMENT_PAYMENT_NOT_DUE` | 422 | A disbursement is attempted before the installment due date. |
| `INSTALLMENT_BANK_DETAILS_MISSING` | 422 | The policyholder has no valid (verified/primary) bank account on record. |
| `INSTALLMENT_REVERSAL_REASON_REQUIRED` | 400 | Reversal was called without a `reason`. |
| `INSTALLMENT_REVERSAL_NOT_ALLOWED` | 422 | Reversal was attempted on an item that is not `PAID` (including an already-reversed item). |
| `INSTALLMENT_REVERSAL_WINDOW_EXPIRED` | 422 | The paid installment is older than `INSTALLMENT_REVERSAL_WINDOW_DAYS`. |
| `INSTALLMENT_CANCELLATION_REASON_REQUIRED` | 400 | Plan cancellation was called without a `reason`. |
| `INSTALLMENT_PLAN_CANNOT_CANCEL` | 422 | The plan is terminal (completed, terminated, or already cancelled) or fully paid. |
| `INSTALLMENT_PLAN_IRREVOCABLE` | 409 | The plan has paid installments and `INSTALLMENT_PAYMENT_IRREVOCABLE` is enabled. |

## Failure proofs (seeded)

The seed command `seed_ol_maturity_installment_scenarios` exercises four of
these codes against real data and captures the proof payloads:

| Attempt | Expected code | Observed |
|---------|---------------|----------|
| Create plan for an immature policy | `PLAN_POLICY_NOT_MATURED` | 422, `policyStatus: "ACTIVE"` |
| Process payment for an already paid item | `INSTALLMENT_ITEM_INVALID_STATUS` | 422, `currentStatus: "PAID"` |
| Reverse a payment outside the window | `INSTALLMENT_REVERSAL_WINDOW_EXPIRED` | 422, `daysSincePaid` > `windowDays` |
| Duplicate idempotent creation | idempotent replay | same plan returned, zero new rows |
