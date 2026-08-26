 OL POLICIES UI — FULL SERIES (10 Prompts)

## [x] Prompt 1/10 — Save Series File + Foundation + Contract-First API Layer

```text
You are a senior frontend engineer for the ZIC Life Insurance Platform. The OL Policies backend is complete. Build the Policies UI. The user pasted the FULL 10-prompt series at once.

META-INSTRUCTION (HIGHEST PRIORITY):
1. Before coding, create docs/prompts/OL_POLICIES_UI_PROMPTS.md and save ALL 10 prompts EXACTLY as provided, each with a checkbox "[ ] Prompt N — title".
2. Commit and push that file immediately.
3. Execute ONLY Prompt 1 now; when green, tick its checkbox, commit, then proceed to Prompt 2. Never merge or skip prompts.

MANDATORY RULES:
- Use the established design system, DataTable, SmartSelect, ErrorCoach, and StatusBadge kits.
- Names never UUIDs; every failure teaches the user what happened and how to resolve it.
- Commit and push at the end of each prompt.

SCOPE:
1. Register route Ordinary Life > Ordinary Life Policies gated by `ol_policies.view`.
2. API hooks (TanStack Query) for:
   - list, detail, kpis
   - issue_policy (from proposal)
   - create_endorsement, list_endorsements
   - request_loan, repay_loan, list_loans
   - request_withdrawal, request_surrender
   - process_maturity
   - print_contract, print_schedule
   - options (products, statuses, endorsement_types, etc.)
3. Build Policy-specific primitives:
   - PolicyStatusBadge (color-coded based on parameters: Active, Lapsed, Matured, Surrendered).
   - PolicyHeader: Displays Policy Number, Policy Holder, Product, Sum Assured, Premium, Status, and "Issue Date/Maturity Date".
   - LifeStageBadge: Indicates if policy is in "Grace", "Lapse", or "Paid-Up".
   - MoneyCell: Formats currency and amount with locale.
4. Implement MSW mock handlers mirroring the backend contract.
5. Unit tests for primitives.

GIT:
- commit: "feat(web): policies UI foundation and contract-first API layer"
- push; if blocked create feature/web-policies-foundation and push; tick checkbox

FINAL OUTPUT: hooks, primitives, tests, commit hash, pushed branch.
```

---

## [x] Prompt 2/10 — Policy List Page & Dashboard KPIs

```text
You are a senior frontend engineer. Continue the ZIC Policies UI. Execute ONLY Prompt 2 from the saved series file.

MANDATORY RULES:
- Table-first; actions gated by allowed actions + permissions.
- Commit and push; tick checkbox.

SCOPE:
1. KPI Cards:
   - Total Active Policies
   - Sum Assured (Total Risk Exposure)
   - New Policies (Current Month)
   - Lapsed Policies
   - Maturing Soon (Next 30 Days)
2. Policies DataTable:
   - Columns: policy_number, policyholder_name, product_plan, sum_assured, premium, status badge, commencement_date, maturity_date, agent_name, allowed_actions.
   - Filters: status, product, branch, agent, date range (commencement/maturity).
   - Search: policy_number, policyholder_name, national_id.
3. Row Actions: View, Endorse, Print, Cancel (if permitted).
4. Buttons: New Policy (Issuance), Export CSV.
5. States: Skeleton, Empty, ErrorCoach.

TESTS:
- KPI display and math
- action visibility by status (e.g., no Endorse button for Cancelled)
- filters and search
- no UUID leaks

GIT:
- commit: "feat(web): policies list page and dashboard KPIs"
- push; tick checkbox

FINAL OUTPUT: page behavior, tests, commit hash, pushed branch.
```

---

## [x] Prompt 3/10 — Policy Issuance UI (Proposal to Policy)

```text
You are a senior frontend engineer. Continue the ZIC Policies UI. Execute ONLY Prompt 3.

MANDATORY RULES:
- Issuance is a one-way action from a "Ready" Proposal.
- Commit and push; tick checkbox.

SCOPE:
1. "New Policy" Wizard Flow:
   - Step 1: Select Proposal
     - Searchable list of Proposals with status `AWAITING_FIRST_PREMIUM` or `PAYMENT_READY`.
     - Show Proposal Number, Applicant, Product, Premium.
     - Warning badge if First Premium is NOT fully paid (should not appear due to filter, but good for safety).
   - Step 2: Confirm & Issue
     - Review Proposal snapshot data.
     - "Issue Policy" button.
     - Loading state "Issuing Policy...".
2. On Success:
   - Toast: "Policy {number} Issued Successfully."
   - Redirect to Policy Detail Page.
3. On Error:
   - Show ErrorCoach (e.g., "Proposal not eligible for issuance").

TESTS:
- wizard flow from proposal selection
- issuance success redirection
- error handling for invalid proposal
- button disabled until proposal selected

GIT:
- commit: "feat(web): policy issuance wizard from proposal"
- push; tick checkbox

FINAL OUTPUT: wizard behavior, tests, commit hash, pushed branch.
```

---

## [x] Prompt 4/10 — Policy Detail Page: Header & Overview Tab

```text
You are a senior frontend engineer. Continue the ZIC Policies UI. Execute ONLY Prompt 4.

MANDATORY RULES:
- Master-Detail pattern; clear visibility of policy facts.
- Commit and push; tick checkbox.

SCOPE:
1. Header:
   - Policy Number (Copyable), Status Badge.
   - Policy Holder Name & Identity.
   - Product & Plan.
   - Sum Assured, Premium Amount & Frequency.
   - Commencement Date, Maturity Date.
   - Action Buttons: Endorse, Loan, Withdraw, Surrender, Print (gated by status and permissions).
2. Tabs: Overview, Members & Riders, Endorsements, Financials (Loans/Withdrawals), Documents, Audit.
3. Overview Tab:
   - Snapshot Data: Terms, Benefits, Premium Factors.
   - Linked Proposal Reference.
   - Status History Timeline (Issued -> Active, etc.).
   - Agent Details.
4. Visual Indicators:
   - If Lapsed: Show "Lapsed Since [Date]" and "Reinstate" button.
   - If Matured: Show "Matured" badge.

TESTS:
- header renders all key fields
- action buttons visibility based on status (e.g., Loan button hidden if policy Lapsed)
- timeline displays correctly
- no UUIDs

GIT:
- commit: "feat(web): policy detail header and overview tab"
- push; tick checkbox

FINAL OUTPUT: page structure, tests, commit hash, pushed branch.
```

---

## [x] Prompt 5/10 — Members, Riders, & Benefits Tabs

```text
You are a senior frontend engineer. Continue the ZIC Policies UI. Execute ONLY Prompt 5.

MANDATORY RULES:
- Read-only display of policy composition.
- Commit and push; tick checkbox.

SCOPE:
1. Members Tab:
   - Table of covered lives (Policyholder, Spouse, Children, etc.).
   - Columns: Name, Relation, DOB, Gender, Sum Assured/Cover.
   - "Add Member" action (if allowed by product parameters and endorsement type).
2. Riders & Benefits Tab:
   - Table of attached Riders (e.g., Waiver of Premium, Accidental Death).
   - Columns: Rider Name, Benefit Amount, Premium Load.
   - "Add Rider" action (via Endorsement).
3. Data Source:
   - Fetch from `GET /api/v1/ol/policies/{id}/members/` and `riders/`.

TESTS:
- members list renders correctly
- riders list renders correctly
- "Add" buttons visible only if endorsement allowed

GIT:
- commit: "feat(web): policy members and riders tabs"
- push; tick checkbox

FINAL OUTPUT: tables, tests, commit hash, pushed branch.
```

---

## [x] Prompt 6/10 — Endorsements Tab & Workflow

```text
You are a senior frontend engineer. Continue the ZIC Policies UI. Execute ONLY Prompt 6.

MANDATORY RULES:
- Endorsements must not overwrite history; they append.
- Commit and push; tick checkbox.

SCOPE:
1. Endorsements Tab:
   - Table of past endorsements.
   - Columns: Endorsement Number, Type (Premium Change, Address, etc.), Date, Status, Description.
   - "View Detail" action to see Before/After values.
2. Create Endorsement Modal:
   - Triggered by "Endorse" button on header.
   - Step 1: Select Endorsement Type (Dropdown from parameters).
   - Step 2: Form based on type.
     - Example: Premium Change -> New Amount input.
     - Example: Member Add -> Member details form.
   - Validation: Check against Product parameters (e.g., Max Premium Change %).
   - Submit: Creates pending endorsement.
3. Status Badges: Pending, Approved, Rejected, Applied.

TESTS:
- history table loads
- modal type selection
- form validation
- successful endorsement creation

GIT:
- commit: "feat(web): endorsements history and creation workflow"
- push; tick checkbox

FINAL OUTPUT: tab behavior, modal logic, tests, commit hash, pushed branch.
```

---

## [x] Prompt 7/10 — Loans & Withdrawals Tab (Financial Actions)

```text
You are a senior frontend engineer. Continue the ZIC Policies UI. Execute ONLY Prompt 7.

MANDATORY RULES:
- Financial actions must be validated against policy eligibility (Loans enabled flag, Cash Value).
- Commit and push; tick checkbox.

SCOPE:
1. Financials Tab (Sub-tabs: Loans, Withdrawals).
2. Loans Section:
   - List of active/past loans: Loan Number, Amount, Interest Rate, Balance, Status.
   - "Request Loan" Modal:
     - Input: Loan Amount.
     - Validation: Amount <= Max Loan % of Surrender Value (fetched from backend).
     - Show "Available Loan Limit".
     - If Policy Lapsed: Block loan request with ErrorCoach.
   - Repayment View: Link to commitment/payment history for the loan.
3. Withdrawals Section:
   - List of withdrawals.
   - "Request Withdrawal" Modal:
     - Input: Amount.
     - Validation: Amount <= Available Cash Value.
     - Warning: "Withdrawals may reduce your Sum Assured."

TESTS:
- loan request validation (max limit)
- withdrawal validation
- blocking logic for lapsed policies
- history list display

GIT:
- commit: "feat(web): policy loans and withdrawals actions"
- push; tick checkbox

FINAL OUTPUT: financial actions, validation, tests, commit hash, pushed branch.
```

---

## [x] Prompt 8/10 — Surrender, Paid-Up, & Cancellation Flows

```text
You are a senior frontend engineer. Continue the ZIC Policies UI. Execute ONLY Prompt 8.

MANDATORY RULES:
- These are destructive/terminal actions; require strong confirmation and reason.
- Commit and push; tick checkbox.

SCOPE:
1. Surrender Workflow:
   - Button "Surrender Policy" (visible if eligible).
   - Modal:
     - Show "Estimated Surrender Value" (fetched from backend calculation).
     - Input: Reason for Surrender (Mandatory).
     - Warning: "This will terminate the policy."
     - Confirm.
2. Paid-Up Conversion:
   - If policy is Lapsed and eligible, show "Convert to Paid-Up" action.
   - Modal: Explain reduction in Sum Assured.
3. Cancellation:
   - "Cancel Policy" action (for free-look period).
   - Modal: Reason input.
4. Post-Action:
   - Policy status updates to Surrendered/Paid-Up/Cancelled.
   - Header reflects new state.

TESTS:
- surrender eligibility check
- paid-up conversion flow
- cancellation reason validation
- status update UI

GIT:
- commit: "feat(web): surrender paid-up and cancellation flows"
- push; tick checkbox

FINAL OUTPUT: terminal actions, tests, commit hash, pushed branch.
```

---

## [x] Prompt 9/10 — Policy Documents & Printouts

```text
You are a senior frontend engineer. Continue the ZIC Policies UI. Execute ONLY Prompt 9.

MANDATORY RULES:
- Use the authenticated print pipeline.
- Commit and push; tick checkbox.

SCOPE:
1. Documents Tab:
   - List of generated documents: Policy Contract, Schedule of Benefits, Premium Statement.
   - Actions: Preview, Download.
2. Print Actions:
   - Header "Print Contract" button -> Generates PDF.
   - Preview Modal with PDF viewer.
   - Watermark logic: "CANCELLED" if status is cancelled.
3. Integration:
   - Connect to `POST /api/v1/ol/policies/{id}/print-contract/`.
   - Handle `TEMPLATE_PENDING` errors via ErrorCoach.

TESTS:
- document list
- print contract generation
- watermark visibility
- error handling

GIT:
- commit: "feat(web): policy documents and print integration"
- push; tick checkbox

FINAL OUTPUT: documents UI, print integration, tests, commit hash, pushed branch.
```

---

## [ ] Prompt 10/10 — Partner Portal View, Dashboard, & E2E Release

```text
You are a senior QA and frontend release engineer. Complete the ZIC Policies UI. Execute ONLY Prompt 10.

MANDATORY RULES:
- Portal strictly read-only.
- E2E coverage mandatory.
- Commit and push; tick final checkbox; all 10 checkboxes ticked at the end.

SCOPE:
1. Partner Portal Route `/portal/policies`:
   - Read-only list of own policies.
   - Read-only detail view (Overview, Members, Documents).
   - No Endorse/Loan/Surrender buttons.
   - Info banner: "Contact agent for changes."
2. Staff Dashboard Integration:
   - Ensure "Active Policies" KPI card on main dashboard links to filtered list.
3. E2E Playwright Tests:
   - Staff Issue Policy from Proposal.
   - Staff view Policy Detail.
   - Staff create Endorsement.
   - Staff request Loan (success and validation failure).
   - Staff Surrender Policy.
   - Partner view read-only policy.
4. Documentation:
   - `frontend/docs/POLICIES_UI_GUIDE.md`.
   - Update `docs/OL_POLICIES_API.md`.
5. Run lint/typecheck/unit/E2E green.
6. Mark series complete in saved file.

GIT:
- commit: "feat(web): policies UI portal e2e and release"
- push; if blocked create feature/web-policies-complete and push
- tag v1.3.0-web-policies if tagging convention exists

FINAL OUTPUT:
Return the FULL policies UI summary: screens built, portal behavior, E2E results, docs added, all 10 checkboxes ticked, commit hash/tag, pushed branch, and next recommended module (Group Life Backend).
``