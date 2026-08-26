OL LOANS BACKEND — FULL PROMPT SERIES (12 Prompts)

## [x] Prompt 1/12 — Save Series File + Loan Domain Foundation

```text
You are a senior Django insurance platform engineer. Build the ZIC Ordinary Life Loans backend. The user pasted the FULL 12-prompt series at once.

META-INSTRUCTION (HIGHEST PRIORITY):
1. Before coding, create docs/prompts/OL_LOANS_BACKEND_PROMPTS.md and save ALL 12 prompts EXACTLY as provided, each with a checkbox "[ ] Prompt N — title".
2. Commit and push that file immediately.
3. Execute ONLY Prompt 1 now; when green, tick its checkbox, commit, then proceed to Prompt 2. Never merge or skip prompts.

MANDATORY RULES:
- No blocking questions; make senior insurance/finance assumptions and document them.
- Everything must be parameterized via existing OL Loan Setup & Interest Control parameters.
- Every financial action must be idempotent, permission-controlled, and audited with actor, before/after, reason, source channel.
- All user-facing errors must use the structured Error Coach shape with resolution steps.
- Commit and push at the end of each prompt.

OBJECTIVE:
Create the OL Loans bounded context and core domain foundation.

BUSINESS CONTEXT:
Policy loans allow policyholders to borrow against cash/surrender value. Loans accrue interest, require repayment schedules, and are automatically offset against surrender, maturity, or death claim payouts. Product parameters dictate eligibility, limits, interest factors, grace/penalty rules, and repayment terms.

SCOPE:
1. Produce docs/OL_LOANS_DESIGN.md defining:
   - Loan lifecycle: REQUESTED -> APPROVED -> DISBURSED/ACTIVE -> PARTIALLY_REPAID -> SETTLED, DEFAULTED, OFFSET_ON_SURRENDER, OFFSET_ON_CLAIM, CLOSED
   - Integration map: Policies, Commitments, Receipts, Claims, Surrender/Maturity, Approval Engine, Audit
   - Financial logic: principal, interest accrual, compounding, penalty, allocation order (fees -> interest -> principal), offset deduction
2. Create Django app `ol_loans`.
3. Implement core models:
   - OLLoan: loan_number unique, policy_ref, partner, currency, principal_amount, disbursed_amount, interest_rate, compounding_frequency, term_months, disbursement_date, maturity_date, status, total_repaid, outstanding_balance, approval_required, reason, audit fields
   - OLLoanSchedule: loan, installment_number, due_date, principal_due, interest_due, penalty_due, amount_paid, balance, status
   - OLLoanRepayment: loan, receipt_ref optional, amount, currency, exchange_rate, allocation_breakdown JSON, reason, audit fields
   - OLLoanInterestAccrual: loan, period_start, period_end, principal_base, interest_amount, penalty_amount, cumulative_interest, audit fields
   - OLLoanOffset: loan, source_type (SURRENDER|MATURITY|CLAIM), source_id, offset_amount, remaining_payout, audit fields
4. Register permissions: ol_loans.view, request, approve, disburse, repay, reverse, offset, print, configure.
5. Register domain events: LoanRequested, LoanApproved, LoanDisbursed, LoanInterestAccrued, LoanRepaid, LoanDefaulted, LoanOffset, LoanSettled.
6. Add structured error registry: LOAN_INELIGIBLE, LOAN_EXCEEDS_LIMIT, LOAN_ACTIVE_EXISTS, LOAN_INVALID_STATUS, LOAN_DISBURSEMENT_FAILED, LOAN_REPAYMENT_OVERPAYMENT, LOAN_OFFSET_INVALID, LOAN_PARAMETER_MISSING.
7. Add base API skeleton: list, retrieve.
8. Add admin table-first registration.

TESTS:
- model creation and relationships
- status enum validation
- error shape contract
- permissions registered

GIT:
- commit: "feat(ol-loans): save prompt series and create loan domain foundation"
- push; if blocked create feature/ol-loans-foundation and push; tick checkbox

FINAL OUTPUT: design summary, models, permissions, events, error codes, tests, commit hash, pushed branch.
```

---

## [x] Prompt 2/12 — Parameter Validation & Configuration Engine

```text
You are a senior Django finance configuration engineer. Continue the ZIC OL Loans backend. Execute ONLY Prompt 2 from the saved series file.

MANDATORY RULES:
- Loan behavior must be strictly driven by existing OL Loan System Setup and OL Loan Interest Control parameters.
- Commit and push; tick checkbox.

OBJECTIVE:
Implement parameter consumption, validation, and configuration resolution for loans.

SCOPE:
1. Create loan parameter resolver service:
   - get_loan_config(policy): reads product/plan flags, max_loan_percentage, min_amount, max_amount, interest_rate, compounding_frequency, grace_days, penalty_rate, repayment_terms
   - validates parameter existence; returns PARAMETER_MISSING with deep links to OL Parameters > Loan Setup / Interest Control
   - caches safely with invalidation on parameter change
2. Implement options endpoints for UI:
   - GET /api/v1/ol/loans/options/repayment-terms/
   - GET /api/v1/ol/loans/options/compounding-frequencies/
   - GET /api/v1/ol/loans/options/offset-rules/
3. Seed validation rules:
   - max_loan_percentage must be between 0 and 100
   - interest_rate must be positive
   - grace_days >= 0
   - penalty_rate >= 0
4. Add admin views for parameter diagnostics (read-only).
5. Ensure all parameter reads are audit-logged for compliance.

TESTS:
- resolver returns correct config for product
- missing parameter returns teachable error with deep link
- validation rules enforce boundaries
- cache invalidation on parameter update

GIT:
- commit: "feat(ol-loans): implement parameter validation and configuration engine"
- push; tick checkbox

FINAL OUTPUT: resolver service, options endpoints, validation rules, tests, commit hash, pushed branch.
```

---

## [ ] Prompt 3/12 — Loan Eligibility & Request Creation

```text
You are a senior Django insurance engineer. Continue the ZIC OL Loans backend. Execute ONLY Prompt 3.

MANDATORY RULES:
- Eligibility must be deterministic and parameter-driven.
- Requests must be idempotent.
- Commit and push; tick checkbox.

OBJECTIVE:
Implement loan request creation with strict eligibility validation.

SCOPE:
1. POST /api/v1/ol/policies/{id}/loans/request/
   - Payload: requested_amount, term_months, repayment_mode, reason
   - Idempotency key: X-Idempotency-Key
2. Validation rules:
   - Policy status must be ACTIVE or PAID_UP
   - Product must allow loans (OL Product Setup flag)
   - No blocking active loans (unless product allows multiple; document assumption)
   - requested_amount <= max_loan_percentage * current_cash_surrender_value
   - requested_amount within min/max from parameters
   - term_months within allowed range
3. On success:
   - Create OLLoan in REQUESTED status
   - Store policy cash value snapshot at request time
   - Emit LoanRequested
   - Audit with actor, amount, policy_ref, timestamp
4. Return structured error on failure with resolution steps.

TESTS:
- successful request creates loan with correct status
- ineligible policy (lapsed/cancelled) blocked
- amount exceeds limit blocked with teachable error
- idempotent duplicate returns same loan
- audit row created

GIT:
- commit: "feat(ol-loans): implement loan eligibility and request creation"
- push; tick checkbox

FINAL OUTPUT: endpoint, validation logic, idempotency, tests, commit hash, pushed branch.
```

---

## [ ] Prompt 4/12 — Approval Workflow & Limit Checking

```text
You are a senior Django insurance workflow engineer. Continue the ZIC OL Loans backend. Execute ONLY Prompt 4.

MANDATORY RULES:
- Approval must integrate with existing approval engine or threshold rules.
- Status transitions must be audited.
- Commit and push; tick checkbox.

OBJECTIVE:
Implement loan approval, rejection, and threshold escalation.

SCOPE:
1. POST /api/v1/ol/loans/{id}/approve/
   - Permission: ol_loans.approve
   - Validation: status REQUESTED, approval_required flag
   - Action: status -> APPROVED, set approved_by/at, emit LoanApproved
2. POST /api/v1/ol/loans/{id}/reject/
   - Reason mandatory
   - Status -> REJECTED, audit reason
3. Threshold escalation:
   - If requested_amount > configured_auto_approve_limit, set approval_required = true
   - Integrate with approval engine seam: create ApprovalRequest for loan disbursement
4. Add bulk approve/reject for operational efficiency (permission-gated).
5. Audit all approval actions with before/after status and actor.

TESTS:
- approval transitions status correctly
- rejection requires reason and audits
- threshold escalation sets approval_required
- bulk actions respect permissions
- audit consistency

GIT:
- commit: "feat(ol-loans): implement approval workflow and limit checking"
- push; tick checkbox

FINAL OUTPUT: approval endpoints, threshold logic, tests, commit hash, pushed branch.
```

---

## [ ] Prompt 5/12 — Disbursement & Financial Transaction Integration

```text
You are a senior Django finance transaction engineer. Continue the ZIC OL Loans backend. Execute ONLY Prompt 5.

MANDATORY RULES:
- Disbursement is a financial event; must integrate with receipts/bank seam.
- Repayment schedule must be generated atomically.
- Commit and push; tick checkbox.

OBJECTIVE:
Implement loan disbursement and repayment schedule generation.

SCOPE:
1. POST /api/v1/ol/loans/{id}/disburse/
   - Permission: ol_loans.disburse
   - Validation: status APPROVED, bank account/payment mode configured
   - Action:
     - Create financial disbursement record (links to front office seam)
     - Generate OLLoanSchedule rows based on term, interest rate, compounding, repayment mode
     - Status -> DISBURSED/ACTIVE
     - Set disbursement_date, update outstanding_balance = principal
     - Emit LoanDisbursed
   - Idempotent: repeated call returns existing disbursement
2. Schedule generation logic:
   - Equal principal or equal installment modes
   - First payment due after grace period from parameters
   - Rounding rules documented
3. Audit disbursement with actor, amount, schedule count, bank ref.

TESTS:
- disbursement creates schedule correctly
- schedule math matches term and interest
- idempotent disbursement safe
- financial seam record created
- audit row complete

GIT:
- commit: "feat(ol-loans): implement disbursement and schedule generation"
- push; tick checkbox

FINAL OUTPUT: disbursement service, schedule math, tests, commit hash, pushed branch.
```

---

## [ ] Prompt 6/12 — Interest Accrual Engine & Balance Calculation

```text
You are a senior Django actuarial/finance engineer. Continue the ZIC OL Loans backend. Execute ONLY Prompt 6.

MANDATORY RULES:
- Accrual must be daily/monthly, idempotent, and auditable.
- Compounding and penalty logic must be exact.
- Commit and push; tick checkbox.

OBJECTIVE:
Implement interest accrual engine and outstanding balance calculation.

SCOPE:
1. Management command: accrue_loan_interest
   - Runs daily/monthly based on parameter
   - For each ACTIVE loan:
     - Calculate interest for period using principal_base, rate, compounding_frequency
     - Apply penalty if overdue schedule installments exist (grace_days from parameters)
     - Create OLLoanInterestAccrual record
     - Update cumulative_interest, outstanding_balance
   - Idempotent: running twice for same period produces no duplicates
2. Real-time balance service:
   - GET /api/v1/ol/loans/{id}/balance/ returns principal, accrued_interest, penalty, total_outstanding
3. Validation:
   - No accrual on SETTLED/CLOSED loans
   - Rate changes mid-term handled via parameter effective dating
4. Audit accrual batches with system actor and correlation ID.

TESTS:
- accrual math correct for simple/compound cases
- penalty applied after grace period
- idempotent rerun produces no duplicates
- balance endpoint matches accrual records
- audit batch logged

GIT:
- commit: "feat(ol-loans): implement interest accrual engine and balance calculation"
- push; tick checkbox

FINAL OUTPUT: accrual command, balance service, tests, commit hash, pushed branch.
```

---

## [ ] Prompt 7/12 — Repayment & Allocation Logic

```text
You are a senior Django finance allocation engineer. Continue the ZIC OL Loans backend. Execute ONLY Prompt 7.

MANDATORY RULES:
- Allocation order must be strict: fees/penalties -> interest -> principal.
- Must integrate with receipts seam.
- Commit and push; tick checkbox.

OBJECTIVE:
Implement loan repayment processing and allocation logic.

SCOPE:
1. POST /api/v1/ol/loans/{id}/repay/
   - Payload: amount, currency, exchange_rate optional, receipt_ref optional, reason
   - Allocation order: penalty -> interest -> principal
   - Update schedule rows: mark installments paid, reduce balances
   - Create OLLoanRepayment record with allocation_breakdown JSON
   - If outstanding_balance == 0: status -> SETTLED, emit LoanSettled
   - Else: status -> PARTIALLY_REPAID
2. Overpayment handling:
   - If amount > outstanding_balance: return LOAN_REPAYMENT_OVERPAYMENT with resolution (adjust amount or hold as credit)
3. Integration with receipts:
   - If receipt_ref provided, link to front_office receipt allocation
   - Emit LoanRepaid event
4. Audit repayment with actor, amount, breakdown, receipt link.

TESTS:
- allocation order correct
- partial repayment updates balances correctly
- full repayment sets SETTLED and emits event
- overpayment returns teachable error
- receipt linkage works
- audit complete

GIT:
- commit: "feat(ol-loans): implement repayment and allocation logic"
- push; tick checkbox

FINAL OUTPUT: repayment endpoint, allocation math, tests, commit hash, pushed branch.
```

---

## [ ] Prompt 8/12 — Lifecycle: Default, Offset on Surrender/Claim/Maturity

```text
You are a senior Django insurance lifecycle engineer. Continue the ZIC OL Loans backend. Execute ONLY Prompt 8.

MANDATORY RULES:
- Offset logic must be atomic and financially precise.
- Default detection must be batch-driven and auditable.
- Commit and push; tick checkbox.

OBJECTIVE:
Implement loan default detection and automatic offset against policy payouts.

SCOPE:
1. Management command: detect_loan_defaults
   - Checks loans with overdue installments > grace_days + penalty_period
   - Sets status -> DEFAULTED
   - Emits LoanDefaulted
   - Idempotent
2. Offset service: process_loan_offset(loan, source_type, source_id, payout_amount)
   - Called by Surrender, Maturity, or Death Claim settlement
   - Calculates offset_amount = min(outstanding_balance, payout_amount)
   - Creates OLLoanOffset record
   - Deducts from payout, updates loan status to OFFSET_ON_* or CLOSED
   - Audit offset with source reference and remaining payout
3. Validation:
   - Cannot offset already SETTLED/CLOSED loans
   - Payout must be positive
4. Emit LoanOffset event for accounting/reinsurance sync.

TESTS:
- default command updates status correctly
- offset deducts correct amount and updates payout
- already settled loan blocked from offset
- audit records created
- events emitted

GIT:
- commit: "feat(ol-loans): implement default detection and offset lifecycle"
- push; tick checkbox

FINAL OUTPUT: default command, offset service, tests, commit hash, pushed branch.
```

---

## [ ] Prompt 9/12 — List, Detail, KPI & Export APIs

```text
You are a senior Django API engineer. Continue the ZIC OL Loans backend. Execute ONLY Prompt 9.

MANDATORY RULES:
- Table-first; names never UUIDs.
- KPIs must be real-time and filterable.
- Commit and push; tick checkbox.

OBJECTIVE:
Implement complete loan list, detail, dashboard, and export APIs.

SCOPE:
1. GET /api/v1/ol/loans/ list:
   - Columns: loan_number, policy_number, policyholder_name, product, principal, outstanding_balance, status, disbursement_date, maturity_date, agent, allowed_actions
   - Filters: status, product, agent, branch, date range, overdue_only, balance>0
   - Search: loan_number, policy_number, policyholder_name
   - Pagination, sorting
2. GET /api/v1/ol/loans/{id}/ detail:
   - Header, schedule, repayments, accrual history, offsets, audit timeline
   - Allowed actions based on status/permission
3. GET /api/v1/ol/loans/kpis/ dashboard:
   - total_disbursed_period, total_outstanding, active_count, defaulted_count, settled_count
   - Currency-aware formatting
4. CSV export respecting filters.
5. Admin tables mirror key columns.

TESTS:
- list columns and display names
- filters/search work
- KPI math correct
- detail includes children and allowed actions
- export respects filters

GIT:
- commit: "feat(ol-loans): implement loan list detail KPI and export APIs"
- push; tick checkbox

FINAL OUTPUT: endpoint contract, KPI rules, tests, commit hash, pushed branch.
```

---

## [ ] Prompt 10/12 — Documents, Print Engine & Audit Consistency

```text
You are a senior Django document & compliance engineer. Continue the ZIC OL Loans backend. Execute ONLY Prompt 10.

MANDATORY RULES:
- Use unified print engine; retain source/template version.
- Audit must be verifiable end-to-end.
- Commit and push; tick checkbox.

OBJECTIVE:
Implement loan document generation and audit consistency verification.

SCOPE:
1. Loan Agreement Template:
   - Variables: loan_number, policy, parties, principal, interest_rate, term, schedule summary, signatures, company header/footer
2. Repayment Schedule Printout:
   - Table of installments, due dates, amounts, paid/unpaid status
3. POST /api/v1/ol/loans/{id}/print-agreement/, /print-schedule/
   - Uses authenticated print pipeline + signed ticket
   - Stores document instance with template version
4. Audit Consistency Utility:
   - Verifies every loan action has audit row
   - Flags orphan records
   - Returns pass/fail report
5. Permission-gated print actions; watermark for DEFAULTED/SETTLED.

TESTS:
- PDF generates with required blocks
- pypdf extraction verifies fields
- audit utility passes on seeded data
- permission denial works
- watermark logic correct

GIT:
- commit: "feat(ol-loans): implement loan documents and audit consistency"
- push; tick checkbox

FINAL OUTPUT: templates, print endpoints, audit utility, tests, commit hash, pushed branch.
```

---

## [ ] Prompt 11/12 — Integrations: Policy Servicing, Claims, Portal, Notifications

```text
You are a senior Django integration engineer. Continue the ZIC OL Loans backend. Execute ONLY Prompt 11.

MANDATORY RULES:
- Clean seams; no tight coupling.
- Portal strictly read-only and scoped.
- Commit and push; tick checkbox.

OBJECTIVE:
Complete integrations around loans.

SCOPE:
1. Policy Servicing Integration:
   - Block loan request if policy lapsed/cancelled
   - Allow reinstatement only if loan default cleared or offset handled
   - Expose loan summary in policy detail payload
2. Claims/Surrender/Maturity Integration:
   - Listen to settlement events; trigger offset service automatically
   - Return net payout after loan deduction
3. Partner Portal:
   - Read-only endpoints scoped to linked partner
   - Own loans list/detail only
   - No internal actions; sanitized errors
4. Notifications:
   - LoanDisbursed, LoanDefaulted, LoanSettled, LoanOffset events
   - Hook into notification center for SMS/Email alerts
5. Dashboard Hooks:
   - Outstanding loans by branch/product
   - Default rate KPI

TESTS:
- policy status blocks loan correctly
- claim settlement triggers offset
- portal scoping denies other partners
- notification events emitted once
- dashboard KPI math

GIT:
- commit: "feat(ol-loans): integrate policy servicing claims portal and notifications"
- push; tick checkbox

FINAL OUTPUT: integration map, events, tests, commit hash, pushed branch.
```

---

## [ ] Prompt 12/12 — Seed Scenarios, Full Test Matrix, Docs & Release

```text
You are a senior Django release engineer. Complete the ZIC OL Loans backend. Execute ONLY Prompt 12.

MANDATORY RULES:
- Seed realistic data across all states.
- Prove every financial path and error is caught.
- Commit and push; tick final checkbox; all 12 checkboxes ticked at the end.

OBJECTIVE:
Seed scenarios, run full test matrix, document, and release.

SCOPE:
1. Seed exactly 10 loans via different paths:
   1 standard active loan
   2 partially repaid
   3 fully settled
   4 defaulted (overdue)
   5 offset on surrender
   6 offset on death claim
   7 multi-currency repayment
   8 rejected request
   9 pending approval
   10 CSV/imported loan (if import supported; otherwise manual batch)
2. Attempt and catch failure scenarios with proof payloads:
   - ineligible policy
   - exceeds cash value limit
   - overpayment
   - offset on already settled loan
   - duplicate disbursement
3. Documentation:
   - docs/OL_LOANS_USER_GUIDE.md
   - docs/OL_LOANS_ADMIN_GUIDE.md
   - docs/OL_LOANS_API.md
   - docs/OL_LOANS_ERROR_CODES.md
   - docs/OL_LOANS_FINANCIAL_LOGIC.md
4. Final verification: backend lint/typecheck/tests green; mark series complete in saved prompt file.

GIT:
- commit: "feat(ol-loans): seed scenarios docs and release"
- push; if blocked create feature/ol-loans-complete and push
- tag v1.4.0-ol-loans-backend if tagging convention exists

FINAL OUTPUT:
Return the FULL loans backend summary:
- models
- endpoints
- financial logic
- integration points
- seed results
- failure proofs
- audit consistency
- docs added
- all 12 checkboxes ticked
- commit hash/tag
- pushed branch
- next recommended module: OL Loans UI, then Group Credit Backend.
```

---

# If manus gives partial work

```text
Follow the saved series file strictly: execute only the current prompt, complete it fully with production-quality code, migrations, APIs, validation, tests, documentation, audit logging, and GitHub push, then tick its checkbox before continuing. Do not merge prompts, do not skip tests, and do not leave placeholders. If anything is ambiguous, make senior-level insurance and finance assumptions, document them, and continue.
```

