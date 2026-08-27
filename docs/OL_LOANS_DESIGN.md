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


## Prompt 7 repayment and allocation rules

Repayment is an atomic financial action. The service locks the loan and all of its schedule rows, validates the lifecycle state and currency, and refuses any amount above the current outstanding balance with `LOAN_REPAYMENT_OVERPAYMENT`. When repayment and loan currencies differ, an explicit positive exchange rate is required; the converted amount is compared with and applied to the loan balance while the original amount, currency, and rate remain in the repayment record.

Allocation is strictly ordered **penalty → interest → principal**. Penalty and interest are allocated against due schedule components plus any unallocated amounts produced by `OLLoanInterestAccrual`; principal can be prepaid against all remaining schedule principal. Each schedule stores paid components, amount paid, recalculated balance, and status. A schedule is `PAID` when all components are cleared, `PARTIALLY_PAID` when a current installment has an outstanding amount, or `OVERDUE` when its due date has passed with an outstanding amount. Accrual-only interest or penalty is attached to the earliest schedule for a reconstructable ledger trail.

The service persists one `OLLoanRepayment` row with an immutable JSON allocation breakdown containing penalty, interest, principal, original amount, converted amount, currency, exchange rate, receipt reference, and allocation order. If `receipt_ref` is supplied, it must identify an active front-office `ReceiptAllocation` in the same repayment currency, and the repayment stores the protected foreign-key link plus the human-readable receipt number. A receipt allocation cannot be applied to more than one loan repayment.

Repayment retries are safe. A caller-supplied `X-Idempotency-Key` is unique to the loan action and cannot be replayed for another loan. Without a key, the service derives a deterministic loan/date/amount/currency key; a repeated active receipt reference also returns its original repayment. Idempotent replays return the existing repayment without modifying schedule, balance, audit, or event state.

A partial repayment transitions the loan to `PARTIALLY_REPAID`. When the outstanding balance reaches exactly `0.00`, the loan transitions to `SETTLED`, and both `LoanRepaid` and `LoanSettled` outbox events are written. Every new repayment writes an audit row with actor, before/after state, allocation breakdown, receipt link, reason, source channel, and correlation metadata.


## Prompt 8 default detection and payout offsets

Default detection is batch-driven and processes only `ACTIVE` and `PARTIALLY_REPAID` loans with unpaid, partially paid, or overdue schedule rows. A schedule defaults only when its overdue age is strictly greater than the sum of the effective `grace_period_days` and `penalty_period_days` from OL Loan Interest Control. `penalty_period_days` is maintained as an effective-dated parameter in Ordinary Life Parameters > Loan Interest Control; no time-window fallback is applied. Missing effective configuration is reported per loan and does not cause the batch to guess a threshold.

The `detect_loan_defaults` command accepts `--as-of`, optional `--loan-id`, and optional `--correlation-id`. Each qualifying loan is locked before transition to `DEFAULTED`, and `LoanDefaulted` plus a `LOAN_DEFAULTED` audit row carry the overdue installment numbers, overdue age, threshold days, actor, source channel, and correlation ID. Rerunning after the first transition finds no eligible ACTIVE/PARTIALLY_REPAID row and therefore emits no duplicate default event or transition audit. Every run also writes one batch audit summary with processed, defaulted, skipped, and error counts under the system actor.

`process_loan_offset` is the atomic payout deduction seam used by surrender, maturity, and death-claim settlement workflows. It locks the loan, validates a positive payout and a human-readable source reference, and computes `offset_amount = min(outstanding_balance, payout_amount)` using half-up two-decimal money rounding. The stored `remaining_payout` is the exact payout amount after the deduction. Surrender, maturity, and claim sources transition a loan to `OFFSET_ON_SURRENDER`, `OFFSET_ON_MATURITY`, or `OFFSET_ON_CLAIM` when a balance remains; a zero balance transitions to `CLOSED`.

The offset source tuple `(loan, source_type, source_id)` is unique, so a retry returns the original offset without deducting the balance twice. Settled and closed loans, zero or negative payouts, missing references, invalid source types, and loans with no outstanding balance are rejected with `LOAN_OFFSET_INVALID` and teachable field-level resolution steps. New offsets write an immutable `OLLoanOffset` row, a `LOAN_OFFSET` audit record with payout and remaining-payout values, and a `LoanOffset` outbox event for accounting and reinsurance synchronization.


## Prompt 9 loan reporting APIs

The canonical loan table endpoint is `GET /api/v1/ol/loans/`. It returns the existing `{"data": {"results": [], "count", "page", "page_size", "next", "previous"}}` envelope and human-readable columns for loan number, policy number, policyholder, product/plan, agent, branch, principal, outstanding balance, dates, status, and `allowed_actions`. Search accepts `q` or `search` across loan number, policy number, and policyholder name/number. Supported filters include status, currency, product code/reference, agent ID/name/number, branch snapshot reference/name/code, disbursement date range, maturity date range, `overdue_only`, and `balance_gt_zero`/`balance_only`. Ordering is allow-listed and supports `-` for descending sort.

`GET /api/v1/ol/loans/{id}/` returns the same human-readable header plus disbursement, schedules, repayments, interest accruals, offsets, `allowed_actions`, and an immutable audit timeline. Timeline entries contain action, before/after status, actor name, timestamp, reason, source channel, and correlation ID. Raw policy, partner, approval, and user foreign-key UUID fields are intentionally not returned in table/detail display payloads; the loan `id` remains the API resource identifier.

`GET /api/v1/ol/loans/kpis/` applies the same filters and returns real-time active, defaulted, and settled/closed counts plus disbursed-period and outstanding totals. A single-currency response returns decimal strings and the currency code; a multi-currency response returns per-currency maps under `amounts_by_currency` and marks the aggregate currency as `MULTI`. The payload includes a server timestamp. `GET /api/v1/ol/loans/export/` applies the same filters and ordering and returns a UTF-8 CSV with the display columns and allowed action codes. Both reporting endpoints require `ol_loans.view` and write an audit read/export record.


## Prompt 10 loan documents and audit consistency

The OL Loans document contract is implemented through the unified `apps.documents` engine. `OL_LOAN_AGREEMENT` uses `OL_LOAN_AGREEMENT_UNIFIED` and `OL_LOAN_SCHEDULE` uses `OL_LOAN_SCHEDULE_UNIFIED`; both retain `source_type=ol_loans.olloan`, `source_object_id`, template code/version, checksum, page count, generated actor, and correlation ID in `DocumentInstance`. The templates inherit `documents/base_print.html`, so company branding, blue title bands, repeating table headers, page X of Y, generation metadata, template version, and signature blocks are consistent with the rest of the platform.

The agreement context includes safe human-readable loan, policy, product, policyholder, agent, principal, rate, term, and schedule-summary values. The schedule context includes every installment's due date, principal, interest, penalty, amount due, amount paid, balance, and paid/unpaid status. Neither context builder falls back to a foreign-key UUID. A `DEFAULTED` or `SETTLED` loan receives a matching uppercase watermark in the document.

Authenticated staff use `POST /api/v1/ol/loans/{id}/print-agreement/` or `POST /api/v1/ol/loans/{id}/print-schedule/`. The response follows the shared document contract and includes `instance`, `preview_url`, `preview_blob_base64_or_url`, `signed_download_url`, and `download_url_expires_at`. The Bearer-authenticated preview/download pipeline remains primary; the signed URL is a single-purpose five-minute ticket revalidated against document type, source, active user, and print permission. Generation, ticket issuance, and streaming access are recorded in central audit rows.

`python3 manage.py verify_loan_audit --json` performs a read-only consistency check across current OL Loan resources and normalized `ol_loans.olloan` audit rows. It reports pass/fail, coverage counts, missing loan trails, and orphan audit records; a failed report exits non-zero for operational monitoring and reconciliation.


## Prompt 11 cross-module integrations

OL Loan integrations are exposed through narrow service seams rather than direct model coupling. Policy reinstatement calls `reinstatement_loan_guard(policy_id)` and blocks only when a `DEFAULTED` OL Loan still has a positive outstanding balance; a cleared, settled, closed, or payout-offset loan does not block the policy lifecycle. Policy detail responses now include `ol_loan_summary` with counts, balances, statuses, policy numbers, and policyholder names while the existing legacy PolicyLoan payload remains intact.

The `DomainEvent` receiver routes `PolicyClaimSettledApplied`, `PolicyMaturityPaid`, and supported surrender settlement events into `apply_settlement_event()`. The service resolves a human-readable source reference, locks the policy and each unsettled OL Loan, calls the existing idempotent offset service, records `POLICY_LOAN_NET_PAYOUT`, and returns gross payout, total loan deduction, remaining net payout, and offset details. Replaying a settlement event or source reference does not create a duplicate offset. Automatic offsets use the valid OL Loan `SYSTEM` source channel for ledger persistence.

Partner portal routes are read-only at `GET /api/v1/ol/loans/portal/` and `GET /api/v1/ol/loans/portal/<loan-id>/`. They scope through `request.user.visible_partners()`, expose loan numbers, policy numbers, names, statuses, financial values, and schedule details, and never expose internal approve, disburse, repay, offset, or print actions. Cross-partner records return a sanitized `PORTAL_RESOURCE_NOT_FOUND` response without echoing the requested UUID.

`LoanDisbursed`, `LoanDefaulted`, `LoanSettled`, and `LoanOffset` events feed the notification center. Email/SMS policy notification rows and dashboard notifications use a stable `loan:<loan-id>:<event>` idempotency key, preventing duplicate alerts when a lifecycle event is retried. The dashboard hook service and `GET /api/v1/ol/loans/dashboard/` expose outstanding balances grouped by branch and product, total loan count, defaulted count, default rate, and a timestamp.
