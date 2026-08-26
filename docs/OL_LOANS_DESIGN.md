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


## Prompt 5 disbursement and schedule rules

Disbursement is an outgoing financial action. The loan context creates one `OLLoanDisbursement` record linked to the existing front-office `FORequisition`; the requisition remains the platform's financial payment seam and is not duplicated as a receipt. The disbursement record stores the released amount, currency, configured payment mode, selected active company bank account code, source channel, reason, and a unique idempotency key. The operation locks the loan and creates the disbursement, all schedule rows, and the `APPROVED -> ACTIVE` transition in one database transaction. A retry returns the existing disbursement and schedule without creating another requisition or any duplicate schedule rows.

The active effective Loan System Setup must contain the loan's repayment mode, and the active Receipt Payment Mode Rule must contain the requested outgoing payment mode. Bank account selection is parameter-driven: an explicitly supplied active company account is used; otherwise the active default account is selected when the configured payment rule requires a bank account. The account currency must match the loan currency. Missing or inactive configuration returns `LOAN_DISBURSEMENT_FAILED` with field-level resolution instructions rather than silently applying a fallback.

Repayment options may explicitly declare `schedule_method` (or `calculation_method`/`repayment_method`) as `EQUAL_PRINCIPAL`, `EQUAL_INSTALLMENT`, or `LUMP_SUM`. The platform also recognizes those standard method codes directly, and `PAYMENT_SCHEDULE`/`SCHEDULE` use the configured equal-installment method. Equal-principal schedules divide the principal across the configured term and calculate monthly interest on the opening principal. Equal-installment schedules use the standard monthly annuity formula. Lump-sum schedules create one maturity installment. The captured loan interest rate, compounding frequency, and interest basis remain authoritative inputs for the later interest-accrual engine; disbursement schedule rows contain only the contractual initial interest projection.

Loan terms are stored in months. The first due date is one calendar month after disbursement when no grace period is configured; when grace days are configured, it is the disbursement date plus the effective grace-day count. All monetary schedule values are rounded half-up to two decimal places. The final principal installment absorbs accumulated fractional-cent differences so the principal total equals the disbursed principal exactly and the final schedule balance is `0.00`. Each schedule balance represents the amount remaining after that installment, while the loan's initial outstanding balance is the released principal.

Disbursement audit records include actor, before/after loan state, amount, schedule count, payment mode, bank account code, requisition number, reason, source channel, and request correlation metadata. The `LoanDisbursed` outbox event carries the same stable financial references for downstream commitments, payments, and reconciliation services.

The API accepts an optional `X-Idempotency-Key`; when a caller omits it, the service derives a deterministic loan-scoped action key (`loan-disbursement-{loan_id}`), so a browser retry for the same loan cannot create a second financial release. Clients should still send a unique key for explicit retry and reconciliation control.


## Prompt 6 interest accrual and balance rules

`accrue_loan_interest` processes only loans in `ACTIVE` status. A period is identified by `(loan, period_start, period_end)` and is protected by the existing unique constraint on `OLLoanInterestAccrual`; a repeated request returns the existing accrual without changing the balance again. `SETTLED` and `CLOSED` loans are rejected with `LOAN_INVALID_STATUS`, and no accrual row is written.

The service resolves the active, effective-dated `OLLoanSystemSetup` and `OLLoanInterestControl` for the policy as of the period end. This means a rate or basis change takes effect on the first period whose effective date includes the period end; previously stored accrual rows remain immutable. The interest principal base is the current loan outstanding balance when capitalization is enabled. When capitalization is disabled, the service derives the remaining principal from the disbursed principal less posted repayment allocations.

For `SIMPLE`, `ACTUAL_365`, and `ACTUAL_360` bases, unrounded interest is `principal_base × annual_rate ÷ 100 × elapsed_days ÷ denominator`, where the denominator is 365 except for `ACTUAL_360`, which uses 360. For compound bases, the effective compounding frequency supplies periods per year and interest is `principal_base × ((1 + annual_rate ÷ 100 ÷ periods_per_year) ^ (elapsed_days × periods_per_year ÷ denominator) − 1)`. Stored interest and penalty amounts are rounded half-up to two decimal places only after the calculation. This preserves exact fractional-period compounding while keeping stored money values deterministic.

Penalty accrues only for an unpaid, partially paid, or overdue schedule after `due_date + grace_days`. The penalty base is the schedule's remaining principal, interest, and prior penalty less amount paid. Penalty uses the configured penalty rate and the same actual-day denominator as the interest control. Each accrual updates the loan outstanding balance by `interest_amount + penalty_amount`; the balance endpoint exposes principal, cumulative accrued interest, cumulative penalty, total outstanding, currency, status, and as-of date.

The `accrue_loan_interest` management command supports `--frequency daily|monthly`, explicit `--period-start`/`--period-end`, `--as-of`, an optional `--loan-id`, and `--correlation-id`. Daily periods use the preceding day through the as-of date; monthly periods use the prior complete calendar month when as-of is the first day of a month, otherwise the current month through as-of. Every batch obtains or reuses the `system` actor, writes a batch audit row with the correlation ID, and reports created, replayed, and per-loan error counts.
