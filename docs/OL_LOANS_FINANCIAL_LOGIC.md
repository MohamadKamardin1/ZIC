# ZIC Ordinary Life Loans Financial Logic

## Accounting basis

The OL Loans ledger stores money as decimal values with two fractional places and stores the currency code beside every amount. The Zanzibar operating seed uses TZS. A cross-currency repayment retains the original repayment amount and currency, the approved exchange rate, and the converted amount applied to the loan currency.

| Field | Definition |
| --- | --- |
| `principal_amount` | Approved loan principal before repayment |
| `cash_value_snapshot` | Policy cash or surrender value captured at request time |
| `disbursed_amount` | Principal actually released |
| `total_repaid` | Cumulative converted repayments applied to the loan |
| `outstanding_balance` | Current unpaid loan amount used by action validation |
| `offset_amount` | Deduction from a policy payout |
| `remaining_payout` | Gross payout less the offset deduction |

The ledger is append-oriented. Repayment, accrual, disbursement, and offset rows are retained; a correction is a separately authorized action rather than an overwrite of financial history.

## Eligibility and limit formula

The effective Loan System Setup is selected by policy product/plan scope and operation date. The request amount must be positive, at least the configured minimum, and no greater than the lower of the cash-value limit and configured maximum:

`available loan limit = cash value snapshot × max loan percentage ÷ 100`

`maximum request = minimum(available loan limit, configured maximum loan amount)`

The request is rejected when the policy is not Active or Paid-up, the product does not allow loans, another active loan exists, the repayment mode or term is not configured, or the amount is outside these limits. There is no client-side or undocumented limit fallback.

## Disbursement and schedule

Disbursement is atomic. It creates the front-office requisition, immutable `OLLoanDisbursement`, contractual `OLLoanSchedule` rows, and the Active state in one transaction. A release retry finds the existing disbursement first and returns it without a second requisition or schedule.

Loan terms are stored in months. For an equal-principal schedule, principal is divided across the term and monthly interest is calculated on opening principal. For an equal-installment schedule, the monthly annuity amount is:

`installment = principal × r × (1+r)^n ÷ ((1+r)^n - 1)`

where `r` is the nominal annual rate divided by 12 and `n` is the number of months. The final schedule row absorbs two-decimal rounding differences so scheduled principal equals the disbursed principal exactly. A lump-sum schedule has one principal-and-interest due row at maturity.

## Interest and penalty accrual

The accrual service resolves the effective Interest Control as of the period end. A period is unique by `(loan, period_start, period_end)`, so replaying a period does not add interest twice. The stored accrual includes principal base, interest, penalty, and cumulative interest.

For simple or actual-day calculations:

`interest = principal base × annual rate ÷ 100 × elapsed days ÷ denominator`

The denominator is 365 unless the effective basis is `ACTUAL_360`. Compound calculations use the configured compounding frequency. Stored amounts are rounded half-up only at the persistence boundary.

Penalty starts only after the schedule due date plus the configured grace period. Default eligibility requires overdue days strictly greater than grace days plus penalty period days. A batch transition records the qualifying installment numbers, threshold, maximum overdue days, as-of date, and correlation ID.

## Repayment allocation

The allocation waterfall is fixed and reconstructable:

| Priority | Component |
| ---: | --- |
| 1 | Penalty and fees |
| 2 | Accrued or scheduled interest |
| 3 | Principal |

The service locks the loan and schedules, validates the converted amount against current outstanding balance, updates schedule paid components, and records an immutable JSON breakdown. A full balance repayment sets `outstanding_balance=0.00` and status `SETTLED`; otherwise status is `PARTIALLY_REPAID`.

A repayment in a different currency requires a positive approved exchange rate. For example, a USD 250,000 repayment at a 2.00000000 rate applies TZS 500,000.00 while preserving USD 250,000.00 and the rate in the repayment record. The release seed uses this path for the multi-currency scenario.

## Policy payout offsets

Surrender, maturity, and claim settlement use the same atomic offset service:

`offset amount = minimum(outstanding balance, gross payout)`

`remaining payout = gross payout - offset amount`

The unique source tuple `(loan, source_type, source_id)` makes a settlement retry safe. If the deduction leaves a positive balance, the loan receives the source-specific status `OFFSET_ON_SURRENDER`, `OFFSET_ON_MATURITY`, or `OFFSET_ON_CLAIM`. If the balance reaches zero, it becomes Closed through the offset path. Settled and closed loans cannot be offset again.

## Invariants and reconciliation checks

The following invariants must hold for every active release and operational record:

| Invariant | Check |
| --- | --- |
| Positive principal | `principal_amount > 0` |
| Non-negative balance | `outstanding_balance >= 0` |
| Disbursed equality | A released loan has one disbursement and `disbursed_amount = principal_amount` |
| Schedule principal | Sum of contractual principal due equals disbursed principal |
| Repayment waterfall | Allocation components sum to the converted applied amount |
| Balance movement | New balance equals prior balance less converted applied repayment or offset |
| Offset math | `offset_amount + remaining_payout = gross payout` |
| Idempotency | Replays do not add financial rows or alter balance twice |
| Audit completeness | Every financial write has actor, before/after, reason, source, and correlation data |
| Event consistency | Financial transitions have the corresponding durable `DomainEvent` |

`verify_loan_audit --json` is the operational consistency check for audit coverage and orphan records. It is read-only and should be included in release and reconciliation runbooks.

## Release assumptions

The final seed uses explicit dates of 2026-01-15 for disbursement and 2026-08-27 for the verification as-of date. It uses the seeded TZS product and monthly compounding configuration, with an 80% cash-value limit, a TZS 100,000 minimum, a TZS 10,000,000 maximum, and equal monthly installments for six- or twelve-month terms. These are demonstration parameters, not a replacement for approved production rates.
