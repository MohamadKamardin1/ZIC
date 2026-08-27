# OL WITHDRAWALS UI — FULL SERIES (10 Prompts)

## [x] Prompt 1 — Save Series File + Foundation + Contract-First API Layer

You are a senior frontend engineer for the ZIC Life Insurance Platform. The OL Withdrawals backend is complete. Build the Withdrawals UI. The user pasted the FULL 10-prompt series at once.

META-INSTRUCTION (HIGHEST PRIORITY):
1. Before coding, create docs/prompts/OL_WITHDRAWALS_UI_PROMPTS.md and save ALL 10 prompts EXACTLY as provided, each with a checkbox "[ ] Prompt N — title".
2. Commit and push that file immediately.
3. Execute ONLY Prompt 1 now; when green, tick its checkbox, commit, then proceed to Prompt 2. Never merge or skip prompts.

MANDATORY RULES:
- Use the established design system, DataTable, SmartSelect, ErrorCoach, and StatusBadge kits.
- Names never UUIDs; every failure teaches the user what happened and how to resolve it.
- Financial data must be displayed with high precision (MoneyCell).
- Commit and push at the end of each prompt.

SCOPE:
1. Register route Ordinary Life > Withdrawals gated by `ol_withdrawals.view`.
2. Implement API hooks (TanStack Query) for the full Withdrawals contract:
   - list, kpis, options
   - request_withdrawal, approve, reject, process_payout
   - cancel, reverse, offset
   - detail (with nested tabs: breakdown, payments, audit)
   - print_statement
3. Build Withdrawal-specific primitives:
   - WithdrawalStatusBadge (colors for Requested, Approved, Processing, Paid, Reversed).
   - MoneyCell (formats Gross Amount, Fee, Net Payout).
   - ImpactAlert (shows policy impact: "Cash Value will reduce by X").
4. Implement MSW mock handlers mirroring the backend contract.
5. Unit tests for primitives rendering.

GIT:
- commit: "feat(web): withdrawals UI foundation and contract-first API layer"
- push; if blocked create feature/web-withdrawals-foundation and push; tick checkbox

FINAL OUTPUT: hooks, primitives, tests, commit hash, pushed branch.

## [ ] Prompt 2 — Withdrawals List Page & Dashboard KPIs

You are a senior frontend engineer. Continue the ZIC Withdrawals UI. Execute ONLY Prompt 2 from the saved series file.

MANDATORY RULES:
- Table-first; actions gated by allowed actions + permissions.
- Commit and push; tick checkbox.

SCOPE:
1. Dashboard KPIs:
   - Total Withdrawn (Current Month).
   - Pending Approvals (Count & Amount).
   - Processing Payouts (Count).
   - Average Fee Amount.
2. Withdrawals DataTable:
   - Columns: Withdrawal Number, Policy Number (clickable), Policyholder Name, Product, Gross Amount, Fee Amount, Net Payout, Status Badge, Requested Date, Allowed Actions.
   - Filters: Status, Product, Branch, Agent, Date Range, Pending Approval Only.
   - Search: Withdrawal Number, Policy Number, Policyholder Name.
3. Row Actions: View, Approve/Reject (if Pending), Print.
4. Buttons: "Request Withdrawal" (opens policy search modal).
5. States: Skeleton, Empty, ErrorCoach.

TESTS:
- KPI display and math
- action visibility (e.g., no Approve button for Paid withdrawal)
- filters and search work
- no UUID leaks in table

GIT:
- commit: "feat(web): withdrawals list page and dashboard KPIs"
- push; tick checkbox

FINAL OUTPUT: page behavior, tests, commit hash, pushed branch.

## [ ] Prompt 3 — Withdrawal Request Wizard (Eligibility & Calculation)

You are a senior frontend engineer. Continue the ZIC Withdrawals UI. Execute ONLY Prompt 3.

MANDATORY RULES:
- The request flow must validate "Available for Withdrawal" (Cash Value - Loan Balance).
- Commit and push; tick checkbox.

SCOPE:
1. "Request Withdrawal" Wizard:
   - Step 1: Select Policy
     - Search active policies eligible for withdrawals.
     - On selection, fetch and display "Available Limit" (Cash Value less Active Loans).
     - Warning if Loan Balance > 0: "Active loan reduces available withdrawal limit."
   - Step 2: Amount & Fees
     - Input: Requested Amount (validates <= Available Limit).
     - Display: Estimated Fee (calculated from backend or parameter logic).
     - Display: Estimated Net Payout (Gross - Fee).
     - Input: Reason (Mandatory).
   - Step 3: Summary & Impact
     - Visual summary of the transaction.
     - ImpactAlert: "Policy Cash Value will be reduced by {Gross Amount}."
     - "Submit Request" button.
2. Validation Feedback:
   - If amount > Limit: Show ErrorCoach "Amount exceeds available cash value limit."
   - If policy lapsed: Show ErrorCoach "Policy is not eligible for withdrawals."
3. Success:
   - Toast "Withdrawal Request Submitted. Status: Pending Approval."
   - Navigate to Withdrawal Detail.

TESTS:
- policy search filters eligible policies
- available limit calculation display
- fee estimation display
- error coach on limit exceeded
- wizard flow completion

GIT:
- commit: "feat(web): withdrawal request wizard with limit validation"
- push; tick checkbox

FINAL OUTPUT: wizard behavior, validation logic, tests, commit hash, pushed branch.

## [ ] Prompt 4 — Withdrawal Detail Page: Header & Overview

You are a senior frontend engineer. Continue the ZIC Withdrawals UI. Execute ONLY Prompt 4.

MANDATORY RULES:
- Master-Detail pattern; clear visibility of financial breakdown.
- Commit and push; tick checkbox.

SCOPE:
1. Header:
   - Withdrawal Number (Copyable), Status Badge.
   - Policy Link.
   - Policyholder Name.
   - Financial Cards: Gross Amount, Fee Amount, Net Payout.
   - Dates: Requested, Approved, Processed, Paid.
   - Action Bar: Approve, Reject, Process Payout, Cancel, Reverse, Print (gated by status).
2. Tabs: Overview, Breakdown, Payments, Documents, Audit.
3. Overview Tab:
   - Details: Product, Currency, Reason for Withdrawal.
   - Policy Context: Cash Value Before/After, Sum Assured Before/After (if applicable).
   - Status Timeline.
4. Visual Indicators:
   - "Reversed" watermark if status is Reversed.

TESTS:
- header renders all financial fields
- action buttons visibility based on status
- policy link navigates correctly
- breakdown data renders correctly

GIT:
- commit: "feat(web): withdrawal detail header and overview"
- push; tick checkbox

FINAL OUTPUT: page structure, tests, commit hash, pushed branch.

## [ ] Prompt 5 — Breakdown Tab & Impact Analysis

You are a senior frontend engineer. Continue the ZIC Withdrawals UI. Execute ONLY Prompt 5.

MANDATORY RULES:
- Financial breakdown must be easy to audit.
- Commit and push; tick checkbox.

SCOPE:
1. Breakdown Tab:
   - Section: Withdrawal Calculation.
     - Cash Value Before: [Amount].
     - Gross Withdrawal: [Amount].
     - Withdrawal Fee: [Amount] (Show basis: e.g., "5% Fixed").
     - Net Payout: [Amount].
     - Cash Value After: [Amount].
   - Section: Policy Impact.
     - Sum Assured Before/After (if proportional reduction applies).
     - Adjustment Ratio used.
   - Audit Trail for this specific withdrawal.
2. Integration:
   - Data fetched from `/api/v1/ol/withdrawals/{id}/breakdown/`.

TESTS:
- breakdown table renders all values
- fee calculation explanation visible
- sum assured adjustment visible if applicable

GIT:
- commit: "feat(web): withdrawal breakdown and impact tab"
- push; tick checkbox

FINAL OUTPUT: tab behavior, tests, commit hash, pushed branch.

## [ ] Prompt 6 — Approval & Rejection Actions

You are a senior frontend engineer. Continue the ZIC Withdrawals UI. Execute ONLY Prompt 6.

MANDATORY RULES:
- Approval/Rejection requires reason and confirmation.
- Commit and push; tick checkbox.

SCOPE:
1. "Approve Withdrawal" Modal:
   - Displays Request Details.
   - Validation: Checks user has `approve` permission.
   - Button: "Confirm Approval".
   - Success: Status updates to "Approved", Audit entry added.
2. "Reject Withdrawal" Modal:
   - Mandatory "Reason for Rejection" input.
   - Button: "Reject".
   - Success: Status updates to "Rejected".
3. Error Handling:
   - If user lacks permission: Action button hidden.
   - If backend error: Show ErrorCoach with resolution.

TESTS:
- approval modal confirmation
- rejection reason validation
- status update on success
- permission gating

GIT:
- commit: "feat(web): withdrawal approval and rejection actions"
- push; tick checkbox

FINAL OUTPUT: modal behaviors, tests, commit hash, pushed branch.

## [ ] Prompt 7 — Financial Processing & Payout Actions

You are a senior frontend engineer. Continue the ZIC Withdrawals UI. Execute ONLY Prompt 7.

MANDATORY RULES:
- Payout processing is a final financial step; requires strict control.
- Commit and push; tick checkbox.

SCOPE:
1. "Process Payout" Modal (For Approved Withdrawals):
   - Displays Net Payout Amount.
   - Input: Payment Mode / Receipt Reference (from Front Office).
   - Button: "Confirm Payout Processed".
   - Success: Status updates to "Paid", Payout Date recorded.
2. "Cancel Request" Modal (For Pending Requests):
   - Reason mandatory.
   - Success: Status updates to "Cancelled".
3. "Reverse Withdrawal" Modal (For Paid Withdrawals):
   - Warning: "This will restore the policy cash value. Are you sure?"
   - Reason mandatory.
   - Success: Status updates to "Reversed".

TESTS:
- payout confirmation flow
- cancellation reason validation
- reversal warning and execution
- success data refresh

GIT:
- commit: "feat(web): withdrawal payout and lifecycle actions"
- push; tick checkbox

FINAL OUTPUT: modal behaviors, tests, commit hash, pushed branch.

## [ ] Prompt 8 — Partner Portal Withdrawals View

You are a senior frontend engineer. Continue the ZIC Withdrawals UI. Execute ONLY Prompt 8.

MANDATORY RULES:
- Portal view is strictly read-only or restricted to "Request".
- Commit and push; tick checkbox.

SCOPE:
1. Partner Route `/portal/withdrawals`:
   - Read-only list of withdrawals associated with the partner's policies.
   - Read-only Detail view (Breakdown, Status visible).
   - Action "Request Withdrawal" available (if product allows).
   - Actions "Approve", "Process Payout", "Reverse" strictly hidden.
2. UX Adjustments:
   - "View" button instead of "Manage".
   - Info Banner: "For changes to withdrawal terms, contact ZIC Finance."
3. Scoping:
   - Ensure only linked policies' withdrawals are fetched.
   - Sanitize sensitive fee data if required by partner permissions (depending on config).

TESTS:
- partner sees only own withdrawals
- restricted actions hidden
- request flow works for partner
- data sanitization

GIT:
- commit: "feat(web): withdrawals partner portal view"
- push; tick checkbox

FINAL OUTPUT: portal behavior, commit hash, pushed branch.

## [ ] Prompt 9 — Documents & Printouts UI

You are a senior frontend engineer. Continue the ZIC Withdrawals UI. Execute ONLY Prompt 9.

MANDATORY RULES:
- Use the authenticated print pipeline.
- Commit and push; tick checkbox.

SCOPE:
1. Documents Tab:
   - List generated documents: Withdrawal Statement, Payment Confirmation.
   - Actions: Preview, Download.
2. Print Actions:
   - Header buttons: "Print Statement".
   - Preview Modal with PDF viewer.
   - Watermark logic: "CANCELLED" or "REVERSED" stamps on documents.
3. Integration:
   - Connect to `POST /api/v1/ol/withdrawals/{id}/print-statement/`.
   - Handle `TEMPLATE_PENDING` errors via ErrorCoach.

TESTS:
- document list loads
- print statement generates PDF
- watermark visibility by status
- error handling for missing templates

GIT:
- commit: "feat(web): withdrawal documents and print integration"
- push; tick checkbox

FINAL OUTPUT: documents UI, print integration, tests, commit hash, pushed branch.

## [ ] Prompt 10 — E2E Verification, Audit, Docs & Release

You are a senior QA and frontend release engineer. Complete the ZIC Withdrawals UI. Execute ONLY Prompt 10.

MANDATORY RULES:
- Verify the UI against the REAL backend seeds.
- Commit and push; tick final checkbox; all 10 checkboxes ticked at the end.

SCOPE:
1. Playwright E2E:
   - Staff List View -> Detail View.
   - Staff Request Withdrawal (Success path with limit check).
   - Staff Approve Withdrawal.
   - Staff Process Payout.
   - Staff Reverse Withdrawal (and verify policy impact restoration).
   - Partner View (Restricted access).
   - Error flows: Request exceeding limit, Approval rejection.
2. Audit Consistency:
   - Verify action buttons trigger audit logs.
   - Ensure no UUIDs in URL or payload where avoidable.
3. Documentation:
   - `frontend/docs/WITHDRAWALS_UI_GUIDE.md` with action flows and error codes.
   - Update `docs/OL_WITHDRAWALS_API.md`.
4. Run lint/typecheck/unit/E2E green.
5. Mark series complete in saved file.

GIT:
- commit: "feat(web): withdrawals UI e2e verification docs and release"
- push; if blocked create feature/web-withdrawals-complete and push
- tag v1.7.0-web-withdrawals if tagging convention exists

FINAL OUTPUT:
Return the FULL withdrawals UI summary: screens built, E2E results, portal behavior, docs added, all 10 checkboxes ticked, commit hash/tag, pushed branch, and next recommended module (Group Credit Backend).
.
