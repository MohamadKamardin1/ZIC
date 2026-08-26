# Ordinary Life Loans Domain Design

## Purpose

The `ol_loans` bounded context manages policy-backed borrowing for Ordinary Life policies. A loan is secured against the policy cash or surrender value and remains financially traceable from request through repayment, settlement, default, or offset against a policy payout. Policy, product, and OL Loan Setup parameters remain authoritative for eligibility, limits, interest, penalties, and repayment terms.

## Lifecycle

```text
REQUESTED
  ├── APPROVED
  │     └── DISBURSED -> ACTIVE
  │                       ├── PARTIALLY_REPAID -> ACTIVE
  │                       ├── SETTLED
  │                       ├── DEFAULTED
  │                       ├── OFFSET_ON_SURRENDER
  │                       ├── OFFSET_ON_MATURITY
  │                       └── OFFSET_ON_CLAIM
  └── REJECTED

ACTIVE or PARTIALLY_REPAID -> CLOSED
```

`DISBURSED` records the financial release and `ACTIVE` is the operating state after a schedule exists. A partial repayment returns the loan to `PARTIALLY_REPAID`; a zero outstanding balance becomes `SETTLED`. `DEFAULTED` is a batch-detected servicing state. An offset state identifies the payout source and preserves the residual payout. `CLOSED` is reserved for an explicitly completed administrative or financial closure. State changes are append-only in audit and event records.

## Core aggregates

| Model | Responsibility | Traceability |
| --- | --- | --- |
| `OLLoan` | Principal loan contract, policy/partner link, terms, balances, approval flag, and lifecycle status | Unique loan number, policy reference, partner, actor timestamps, reason, source channel |
| `OLLoanSchedule` | One contractual repayment installment | Due date, principal, interest, penalty, paid amount, balance, installment status |
| `OLLoanRepayment` | One received repayment and its allocation | Optional receipt seam reference, currency/rate, allocation JSON, reason, actor timestamps |
| `OLLoanInterestAccrual` | One idempotent interest/penalty calculation period | Period uniqueness, principal base, interest, penalty, cumulative interest, actor timestamps |
| `OLLoanOffset` | One deduction from surrender, maturity, or claim proceeds | Source type/id, offset amount, residual payout, actor timestamps |

## Integration map

| Integration | Contract |
| --- | --- |
| Policies | `OLLoan.policy_ref` links the loan to the issued policy and reads policy status, product flags, and current cash/surrender value through a service seam. |
| OL Parameters | Loan System Setup supplies eligibility flags, percentage and amount limits, repayment terms, and payout effects. Loan Interest Control supplies rate, compounding, grace, penalty, and capitalization rules. |
| Commitments | Disbursement and repayment scheduling can create or stop premium/loan commitments through an integration service; Prompt 1 only establishes the seam. |
| Receipts / Front Office | `receipt_ref` is an optional stable reference to a receipt allocation. The loan context does not duplicate receipt ownership. |
| Claims | Claim settlement calls the offset service with `source_type=CLAIM`, source ID, and payout amount. |
| Surrender / Maturity | Surrender and maturity settlement call the same offset service and receive the remaining payable amount. |
| Approval Engine | Requests above the configured auto-approval threshold become approval-required and can link to a shared `ApprovalRequest` in a later prompt. |
| Audit | Every aggregate/child write carries actor fields and source channel; receivers write immutable central `AuditLog` rows. |
| Outbox events | `DomainEvent` stores typed Loan* events for reliable downstream publication. |

## Financial logic

`principal_amount` is the approved loan principal. `disbursed_amount` is the amount actually released. `outstanding_balance` is the current amount due, including any accrued interest and penalty not yet allocated. `total_repaid` is the cumulative posted repayment amount. All stored money values are decimal strings at two decimal places and are accompanied by a three-letter currency code.

Interest accrual is parameter-driven. The accrual engine will select the effective rate and compounding frequency for each period, calculate against the documented principal base, and write one `OLLoanInterestAccrual` row per loan and period. Penalty begins only after the configured grace and penalty window. A repeated period request must return the existing accrual rather than create a duplicate.

Repayment allocation is strict and ordered: **fees/penalties → interest → principal**. Each repayment stores the exact allocation breakdown so reconciliation can reconstruct the balance movement. Amounts above the outstanding balance are rejected with a structured `LOAN_REPAYMENT_OVERPAYMENT` error unless a later configuration explicitly enables a credit-hold workflow.

An offset is atomic with the payout settlement. Its amount is `min(outstanding_balance, payout_amount)`. The remaining payout is `payout_amount - offset_amount`; the loan transitions to a source-specific offset status when fully covered, or to `CLOSED` when the surrounding settlement service explicitly closes it. Settled and closed loans cannot be offset again.

## Idempotency, permissions, and errors

Financial action endpoints will require an `X-Idempotency-Key` or an equivalent source reference. The key and action identity must be unique for retry-safe processing. Every action is permission-gated through the `ol_loans.*` permission family and writes before/after state, actor, reason, source channel, and correlation metadata.

The structured Error Coach shape is:

```json
{
  "error_code": "LOAN_INVALID_STATUS",
  "message": "The loan cannot be disbursed from its current status.",
  "resolution_steps": [
    "Review the loan status and approval history.",
    "Complete the preceding lifecycle action before retrying."
  ],
  "field_errors": {},
  "doc_ref": "docs/OL_LOANS_DESIGN.md"
}
```

Prompt 1 registers the stable error taxonomy: `LOAN_INELIGIBLE`, `LOAN_EXCEEDS_LIMIT`, `LOAN_ACTIVE_EXISTS`, `LOAN_INVALID_STATUS`, `LOAN_DISBURSEMENT_FAILED`, `LOAN_REPAYMENT_OVERPAYMENT`, `LOAN_OFFSET_INVALID`, and `LOAN_PARAMETER_MISSING`. Action-specific validation is introduced in the later numbered prompts; no client is permitted to infer eligibility from a hardcoded rule.

## Prompt 1 assumptions

The existing `Policy`, `Partner`, `DomainEvent`, `AuditLog`, IAM permission, and structured-exception infrastructure are reused. Receipt and approval relationships remain loose references in the foundation so the loans app does not create circular migrations or duplicate ownership. The loan currency defaults to TZS for the Zanzibar operating environment but is validated as a three-letter code and remains editable from the parameter-driven service layer. No financial action is executed in the foundation prompt; list and retrieve are read-only and expose stable display fields for policy and partner names.
