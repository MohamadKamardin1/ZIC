 OL LOANS UI — FULL SERIES (10 Prompts)

## [x] Prompt 1/10 — Save Series File + Foundation + Contract-First API Layer

```text
You are a senior frontend engineer for the ZIC Life Insurance Platform. The OL Loans backend is complete. Build the Loans UI. The user pasted the FULL 10-prompt series at once.

META-INSTRUCTION (HIGHEST PRIORITY):
1. Before coding, create docs/prompts/OL_LOANS_UI_PROMPTS.md and save ALL 10 prompts EXACTLY as provided, each with a checkbox "[ ] Prompt N — title".
2. Commit and push that file immediately.
3. Execute ONLY Prompt 1 now; when green, tick its checkbox, commit, then proceed to Prompt 2. Never merge or skip prompts.

MANDATORY RULES:
- Use the established design system, DataTable, SmartSelect, ErrorCoach, and StatusBadge kits.
- Names never UUIDs; every failure teaches the user what happened and how to resolve it.
- Commit and push at the end of each prompt.

SCOPE:
1. Register route Ordinary Life > Loans gated by `ol_loans.view`.
2. Implement API hooks (TanStack Query) for the full Loans contract:
   - list, kpis, options
   - create_request, disburse, repay, offset, reverse
   - detail (with nested tabs data: schedule, repayments, accruals)
   - print_agreement, print_schedule
3. Build Loan-specific primitives:
   - LoanStatusBadge (colors for Active, Defaulted, Settled, Offset).
   - MoneyCell (formats principal, interest, balance).
   - ProgressCell (visualizes loan balance vs principal).
   - ActionButtonGroup (gated by permission and loan status).
4. Implement MSW mock handlers mirroring the backend contract.
5. Unit tests for primitives rendering.

GIT:
- commit: "feat(web): loans UI foundation and contract-first API layer"
- push; if blocked create feature/web-loans-foundation and push; tick checkbox

FINAL OUTPUT: hooks, primitives, tests, commit hash, pushed branch.
```

---

## [x] Prompt 2/10 — Loans Dashboard KPIs & List Page

```text
You are a senior frontend engineer. Continue the ZIC Loans UI. Execute ONLY Prompt 2 from the saved series file.

MANDATORY RULES:
- Table-first; actions gated by allowed actions + permissions.
- Commit and push; tick checkbox.

SCOPE:
1. Dashboard KPIs:
   - Total Loans Outstanding (Amount).
   - Active Loans Count.
   - Defaulted Loans Count.
   - Loans Disbursed (This Month).
2. Loans DataTable:
   - Columns: Loan Number, Policy Number (clickable), Policyholder Name, Product, Principal Amount, Outstanding Balance, Interest Rate, Disbursement Date, Status Badge, Allowed Actions.
   - Filters: Status, Product, Branch, Date Range, Defaulted Only.
   - Search: Loan Number, Policy Number, Policyholder Name.
3. Row Actions: View, Disburse (if Pending), Repay, Offset, Print.
4. Buttons: "Request Loan" (opens policy search modal).
5. States: Skeleton, Empty, ErrorCoach.

TESTS:
- KPI display and math
- action visibility (e.g., no Repay button for Settled loan)
- filters and search work
- no UUID leaks in table

GIT:
- commit: "feat(web): loans list page and dashboard KPIs"
- push; tick checkbox

FINAL OUTPUT: page behavior, tests, commit hash, pushed branch.
```

---

## [x] Prompt 3/10 — Loan Detail Page: Header & Overview Tab

```text
You are a senior frontend engineer. Continue the ZIC Loans UI. Execute ONLY Prompt 3.

MANDATORY RULES:
- Master-Detail pattern; clear visibility of financial facts.
- Commit and push; tick checkbox.

SCOPE:
1. Header:
   - Loan Number (Copyable), Status Badge.
   - Policy Link (Policy Number + Name).
   - Policyholder Name.
   - Principal Amount, Disbursed Amount, Outstanding Balance (Large, prominent font).
   - Interest Rate, Term, Maturity Date.
   - Action Bar: Request Loan, Repay, Offset, Disburse (gated by status).
2. Tabs: Overview, Repayment Schedule, Repayments, Offsets, Documents, Audit.
3. Overview Tab:
   - Loan Terms: Product, Disbursement Date, Effective Interest Rate.
   - Linked Policy Details snippet.
   - Offset History summary (if any).
   - Status Timeline (Requested -> Approved -> Disbursed).

TESTS:
- header renders all key financial fields
- action buttons visibility based on status
- policy link navigates correctly
- status timeline displays correctly

GIT:
- commit: "feat(web): loan detail header and overview tab"
- push; tick checkbox

FINAL OUTPUT: page structure, tests, commit hash, pushed branch.
```

---

## [x] Prompt 4/10 — Repayment Schedule Tab & Visualization

```text
You are a senior frontend engineer. Continue the ZIC Loans UI. Execute ONLY Prompt 4.

MANDATORY RULES:
- Schedules must be easy to read; highlight overdue rows.
- Commit and push; tick checkbox.

SCOPE:
1. Repayment Schedule Tab:
   - Table: Installment #, Due Date, Principal Due, Interest Due, Penalty Due, Total Due, Amount Paid, Balance, Status (Paid, Due, Overdue).
   - Visuals: Overdue rows highlighted in red. Paid rows in green.
   - Aggregates row at top: Total Scheduled, Total Paid, Remaining Balance.
   - Export CSV button for schedule.
2. Integration:
   - Data fetched from `/api/v1/ol/loans/{id}/schedule/`.
   - Infinite scroll or pagination if long terms (e.g., 30+ years).

TESTS:
- schedule table renders correctly
- overdue highlighting works
- aggregate row sums are correct
- pagination works for long lists

GIT:
- commit: "feat(web): loan repayment schedule tab"
- push; tick checkbox

FINAL OUTPUT: table behavior, tests, commit hash, pushed branch.
```

---

## [x] Prompt 5/10 — Repayments & Accrual History Tabs

```text
You are a senior frontend engineer. Continue the ZIC Loans UI. Execute ONLY Prompt 5.

MANDATORY RULES:
- Financial history must be immutable and precise.
- Commit and push; tick checkbox.

SCOPE:
1. Repayments Tab:
   - List of payments made against the loan.
   - Columns: Payment Date, Receipt Reference, Amount Paid, Allocation (Principal/Interest/Penalty), Source (Manual/Auto).
   - Link to Front Office Receipt if applicable.
2. Accruals Tab:
   - List of interest accrual periods.
   - Columns: Period Start, Period End, Interest Amount, Penalty Amount, Cumulative Interest.
   - Used for auditing and dispute resolution.
3. Data Source:
   - Fetched from `/api/v1/ol/loans/{id}/repayments/` and `/accruals/`.

TESTS:
- repayments list renders allocation breakdown
- accruals list renders period data
- correct empty states when no history exists

GIT:
- commit: "feat(web): loan repayments and accrual history tabs"
- push; tick checkbox

FINAL OUTPUT: tabs behavior, tests, commit hash, pushed branch.
```

---

## [x] Prompt 6/10 — Loan Request Modal (Creation Flow)

```text
You are a senior frontend engineer. Continue the ZIC Loans UI. Execute ONLY Prompt 6.

MANDATORY RULES:
- Request flow must validate limits before submission.
- Commit and push; tick checkbox.

SCOPE:
1. "Request Loan" Modal:
   - Step 1: Select Policy
     - Search active policies eligible for loans (flags for products that allow loans).
     - On selection, show "Available Loan Limit" (Calculated from backend or parameter estimate).
   - Step 2: Loan Details
     - Input: Requested Amount (validates <= Limit).
     - Input: Term (Months/Years) via SmartSelect.
     - Input: Repayment Mode (e.g., Deduction from Maturity, Monthly).
     - Input: Reason (Mandatory).
   - Step 3: Summary & Submit
     - Show Estimated Monthly Payment (if available).
     - "Submit Request" button.
2. Validation Feedback:
   - If amount > Limit: Show ErrorCoach "Loan amount exceeds available cash value limit."
   - If policy lapsed: Show ErrorCoach "Policy is not eligible for loans."
3. Success:
   - Toast "Loan Request Created. Status: Pending Approval."
   - Navigate to Loan Detail.

TESTS:
- policy search filters eligible policies
- amount validation against limit
- modal flow completion
- error coach display on validation failure

GIT:
- commit: "feat(web): loan request modal and validation flow"
- push; tick checkbox

FINAL OUTPUT: modal behavior, validation logic, tests, commit hash, pushed branch.
```

---

## [ ] Prompt 7/10 — Repay, Disburse & Offset Action Modals

```text
You are a senior frontend engineer. Continue the ZIC Loans UI. Execute ONLY Prompt 7.

MANDATORY RULES:
- These are high-impact financial actions; require strict confirmation.
- Commit and push; tick checkbox.

SCOPE:
1. "Repay Loan" Modal:
   - Input: Repayment Amount.
   - Input: Payment Mode / Receipt Reference.
   - Validation: Amount <= Outstanding Balance (unless partial payment allowed by parameter).
   - Button: "Process Repayment".
2. "Disburse Loan" Modal (For approved loans):
   - Displays Loan Amount, Bank Details (from policy/partner).
   - Confirmation text: "Confirm disbursement of {amount} to {account}?"
   - Button: "Disburse Funds".
3. "Offset Loan" Modal (For claims/surrender):
   - Displays Outstanding Balance.
   - Input: Offset Amount (Default: Full Balance).
   - Warning: "This amount will be deducted from the policy payout."
   - Button: "Confirm Offset".
4. Integration:
   - Calls appropriate endpoints (`/repay/`, `/disburse/`, `/offset/`).
   - Shows success toast and refreshes detail data.

TESTS:
- repayment amount validation
- disburse confirmation flow
- offset warning display
- success data refresh

GIT:
- commit: "feat(web): loan repay disburse and offset action modals"
- push; tick checkbox

FINAL OUTPUT: modal behaviors, tests, commit hash, pushed branch.
```

---

## [ ] Prompt 8/10 — Partner Portal Loans View

```text
You are a senior frontend engineer. Continue the ZIC Loans UI. Execute ONLY Prompt 8.

MANDATORY RULES:
- Portal view is strictly read-only or restricted to "Request".
- Commit and push; tick checkbox.

SCOPE:
1. Partner Route `/portal/loans`:
   - Read-only list of loans associated with the partner's policies.
   - Read-only Detail view (Schedule, Repayments visible).
   - Action "Request Loan" available (if product allows).
   - Actions "Disburse", "Offset", "Reverse" strictly hidden.
2. UX Adjustments:
   - "View" button instead of "Manage".
   - Info Banner: "For changes to loan terms, contact ZIC Finance."
3. Scoping:
   - Ensure only linked policies' loans are fetched.
   - Sanitize sensitive financial data if required by partner permissions.

TESTS:
- partner sees only own loans
- restricted actions hidden
- request flow works for partner
- sensitive data sanitization

GIT:
- commit: "feat(web): loans partner portal view"
- push; tick checkbox

FINAL OUTPUT: portal behavior, tests, commit hash, pushed branch.
```

---

## [ ] Prompt 9/10 — Documents & Printouts UI

```text
You are a senior frontend engineer. Continue the ZIC Loans UI. Execute ONLY Prompt 9.

MANDATORY RULES:
- Use the authenticated print pipeline.
- Commit and push; tick checkbox.

SCOPE:
1. Documents Tab:
   - List generated documents: Loan Agreement, Repayment Schedule.
   - Actions: Preview, Download.
2. Print Actions:
   - Header buttons: "Print Agreement", "Print Schedule".
   - Preview Modal with PDF viewer.
   - Watermark logic: "DEFAULTED" or "SETTLED" stamps on documents.
3. Integration:
   - Connect to `POST /api/v1/ol/loans/{id}/print-agreement/`.
   - Handle `TEMPLATE_PENDING` errors via ErrorCoach.

TESTS:
- document list loads
- print agreement generates PDF
- watermark visibility by status
- error handling for missing templates

GIT:
- commit: "feat(web): loan documents and print integration"
- push; tick checkbox

FINAL OUTPUT: documents UI, print integration, tests, commit hash, pushed branch.
```

---

## [ ] Prompt 10/10 — E2E Verification, Audit, Docs & Release

```text
You are a senior QA and frontend release engineer. Complete the ZIC Loans UI. Execute ONLY Prompt 10.

MANDATORY RULES:
- Verify the UI against the REAL backend seeds.
- Commit and push; tick final checkbox; all 10 checkboxes ticked at the end.

SCOPE:
1. Playwright E2E:
   - Staff List View -> Detail View.
   - Staff Request Loan (Success path).
   - Staff Disburse Loan.
   - Staff Repay Loan (Partial and Full).
   - Staff Offset Loan.
   - Partner View (Restricted access).
   - Error flows: Request exceeding limit, Repay overbalance.
2. Audit Consistency:
   - Verify action buttons trigger audit logs.
   - Ensure no UUIDs in URL or payload where avoidable.
3. Documentation:
   - `frontend/docs/LOANS_UI_GUIDE.md` with action flows and error codes.
   - Update `docs/OL_LOANS_API.md`.
4. Run lint/typecheck/unit/E2E green.
5. Mark series complete in saved file.

GIT:
- commit: "feat(web): loans UI e2e verification docs and release"
- push; if blocked create feature/web-loans-complete and push
- tag v1.5.0-web-loans if tagging convention exists

FINAL OUTPUT:
Return the FULL loans UI summary: screens built, E2E results, portal behavior, docs added, all 10 checkboxes ticked, commit hash/tag, pushed branch, and next recommended module (Group Credit Backend).
```
