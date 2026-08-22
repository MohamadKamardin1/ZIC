# OL COMMITMENTS UI — PROMPT SERIES (10 prompts)

- [x] Prompt 1 — Commitments UI Foundation and Error Coach Kit
- [x] Prompt 2 — Commitments List Page
- [x] Prompt 3 — Commitment Generation Wizard and Manual Creation
- [x] Prompt 4 — Commitment Bulk Import with Row Error Handling
- [x] Prompt 5 — Commitment Detail Page with Tabs and Actions
- [x] Prompt 6 — Commitment Payment and Reversal Modals
- [ ] Prompt 7 — Commitment Lifecycle Action Modals
- [ ] Prompt 8 — [pending prompt text]
- [ ] Prompt 9 — [pending prompt text]
- [ ] Prompt 10 — [pending prompt text]

> **Note on fidelity:** prompts 2–10 were not included in the pasted series message for this session. They will be appended `EXACTLY as provided` when the user supplies them, then executed strictly one at a time. Prompt 1 below is saved verbatim.

---

## Prompt 1/10 — Commitments UI Foundation and Error Coach Kit

```text
You are a senior frontend engineer for the ZIC Life Insurance Platform. The commitments backend is complete. Build the full Commitments UI. The user pasted the FULL 10-prompt series at once.

META-INSTRUCTION (HIGHEST PRIORITY):
1. Before coding, create docs/prompts/OL_COMMITMENTS_UI_PROMPTS.md and save ALL 10 prompts EXACTLY as provided, each with a checkbox "[ ] Prompt N — title".
2. Commit and push that file immediately.
3. Execute ONLY Prompt 1 now; when green, tick its checkbox, commit, then proceed to Prompt 2. Never merge or skip prompts.

MANDATORY RULES:
- Use the established design system, DataTable, SmartSelect, and wizard kits.
- No UUIDs visible anywhere; names only.
- Every failure must teach the user what happened and how to resolve it.
- Commit and push at the end of each prompt.

SCOPE:
1. Register route Ordinary Life > Ordinary Life Commitments, gated by access metadata; hidden without ol_commitments.view.
2. Create API hooks (TanStack Query) for:
   - list + KPIs + filters
   - detail with allowed actions
   - options endpoints (payment modes, currencies, statuses)
   - generation preview/execute, import, process-overdue, action endpoints
3. Build the ErrorCoach component rendering the backend structured error shape:
   - error code chip + plain-language message
   - numbered resolution_steps
   - deep_link button "Open configuration" for PARAMETER_MISSING
   - "View existing" link for duplicates
   - retry button where safe
   - aria-live, dark-theme parity
4. Build shared Commitment UI primitives:
   - StatusBadge (parameter-driven colors)
   - DueDateWarning (amber in grace, red overdue/lapse)
   - ReasonField (mandatory reason textarea with minimum length + inline error)
   - ConfirmDialog with danger variants
   - success toast with next-step hint
5. Unit tests for ErrorCoach, ReasonField, badges, and route gating.

GIT:
- commit: "feat(web): commitments UI foundation and error coach kit"
- push; if blocked create feature/web-commitments-foundation and push; tick checkbox

FINAL OUTPUT: components, hooks, tests, commit hash, pushed branch.
```

---

## Prompt 2/10 — Commitments List Page

```text
You are a senior frontend engineer. Continue the ZIC Commitments UI. Execute ONLY Prompt 2 from the saved series file.

MANDATORY RULES:
- Table-first, names never UUIDs, actions gated by allowed-actions + permissions.
- Commit and push; tick checkbox.

SCOPE:
1. KPI cards: Total Due, Outstanding, Overdue Count, Collected in Period (currency-aware formatting).
2. Commitments DataTable with backend columns: commitment_number, source display, policyholder/partner name, product/plan, installment #, due_date, amount_due, amount_paid, balance, currency, status badge, grace_date, actions.
3. Filters: status, product, source_type, currency, due date range, balance>0; search by commitment number/partner/policy; quick chips: Overdue, In Grace, Outstanding.
4. Row actions from allowed actions: View, Record Payment, Suspend, Waive, Cancel, Reschedule, Reverse — hidden when absent.
5. Buttons: Create New Commitment, Generate Commitments, Import CSV, Export CSV.
6. States: loading skeleton, empty state with guidance, error state via ErrorCoach.
7. DueDateWarning rendering on grace/lapse dates.

TESTS:
- KPI math display
- action visibility by status/permission
- filters, chips, search, export
- error state renders ErrorCoach

GIT:
- commit: "feat(web): commitments list page with KPIs and filters"
- push; tick checkbox

FINAL OUTPUT: page behavior, tests, commit hash, pushed branch.
```

---

## Prompt 4/10 — Commitment Bulk Import with Row Error Handling

```text
You are a senior frontend engineer. Continue the ZIC Commitments UI. Execute ONLY Prompt 4.

MANDATORY RULES:
- Imports must be safe, explainable, and reprocessable.
- Commit and push; tick checkbox.

SCOPE:
1. Import modal: CSV template download, file upload, dry-run mode default.
2. Dry-run results table: row #, status (OK/ERROR), field-level error messages with resolution hints.
3. "Fix and reprocess" guidance panel; commit mode enabled only when zero blocking errors or when explicitly confirming partial import if supported.
4. Import history list: file name, uploaded by, date, counts (ok/error/created), status badge; view errors per import.
5. All import failures rendered through ErrorCoach taxonomy (IMPORT_ROW_INVALID with row/field detail).

TESTS:
- template download link
- dry-run error table rendering
- commit disabled with blocking errors
- history list displays counts

GIT:
- commit: "feat(web): commitment bulk import with row error handling"
- push; tick checkbox

FINAL OUTPUT: import UX, tests, commit hash, pushed branch.
```

---

## Prompt 5/10 — Commitment Detail Page with Tabs and Actions

```text
You are a senior frontend engineer. Continue the ZIC Commitments UI. Execute ONLY Prompt 5.

MANDATORY RULES:
- Master-detail pattern consistent with the platform.
- Commit and push; tick checkbox.

SCOPE:
1. Header: commitment number, partner name, product/plan, status badge, currency, due/grace/lapse dates with DueDateWarning, balance highlight.
2. Status card showing payment progress bar (paid vs due) and allowed actions button bar.
3. Tabs:
   - Overview: source info, amounts, parameters applied (grace days, frequency), reasons for suspend/waive/cancel when present
   - Allocations: table of payments with payment mode, amount, currency, exchange rate, receipt reference, reversal links
   - History: status change timeline with actor, timestamp, previous/new state, reason, source channel
   - Notifications: grace/overdue notification log with channel and recipient badges
4. Action buttons render only from allowed actions payload.
5. Fetch failures render ErrorCoach.

TESTS:
- tabs render from detail payload
- progress bar math
- history shows reasons and actors
- no UUIDs rendered

GIT:
- commit: "feat(web): commitment detail page with tabs and actions"
- push; tick checkbox

FINAL OUTPUT: page structure, tests, commit hash, pushed branch.
```

---

## Prompt 6/10 — Commitment Payment and Reversal Modals

```text
You are a senior frontend engineer. Continue the ZIC Commitments UI. Execute ONLY Prompt 6.

MANDATORY RULES:
- Money actions must be explicit, confirmed, and teachable on failure.
- Commit and push; tick checkbox.

SCOPE:
1. Record Payment modal:
   - amount with live balance preview and remaining-after payment
   - payment mode SmartSelect with "+" quick-create
   - currency SmartSelect; exchange rate field appears on cross-currency with validation
   - receipt reference input with source channel display
   - overpayment attempt returns COMMITMENT_OVERPAYMENT via ErrorCoach with resolution steps
2. Reverse Allocation modal:
   - allocation summary, mandatory ReasonField, danger ConfirmDialog
   - success toast: "Payment reversed. Balance restored."
3. After success: refetch detail, allocations and history tabs update, audit-visible entries appear.

TESTS:
- live balance preview math
- cross-currency exchange rate validation
- overpayment ErrorCoach rendering
- reversal requires reason and updates tabs

GIT:
- commit: "feat(web): commitment payment and reversal modals"
- push; tick checkbox

FINAL OUTPUT: modal behaviors, tests, commit hash, pushed branch.
```

---

## Prompt 7/10 — Commitment Lifecycle Action Modals

```text
You are a senior frontend engineer. Continue the ZIC Commitments UI. Execute ONLY Prompt 7.

MANDATORY RULES:
- Reasons mandatory; invalid transitions must teach.
- Commit and push; tick checkbox.

SCOPE:
1. Modals for Suspend, Reactivate, Waive, Cancel, Reschedule:
   - Suspend/Cancel: ReasonField + danger confirm
   - Waive: ReasonField + approval-required banner explaining the approval hook
   - Reschedule: new due date with hint text showing parameter limits (grace/lapse rules), reason
2. Invalid transition responses render ErrorCoach listing allowed transitions from resolution_steps.
3. Buttons appear only when allowed; after success, status badge and history update with toast hint.

TESTS:
- each modal validation
- invalid transition ErrorCoach shows allowed transitions
- waive approval banner visible
- reschedule limit hint from parameters

GIT:
- commit: "feat(web): commitment lifecycle action modals"
- push; tick checkbox

FINAL OUTPUT: modal behaviors, tests, commit hash, pushed branch.
```

---

## Prompt 3/10 — Commitment Generation Wizard and Manual Creation

```text
You are a senior frontend engineer. Continue the ZIC Commitments UI. Execute ONLY Prompt 3.

MANDATORY RULES:
- Generation must preview before creating; duplicates must be teachable.
- Commit and push; tick checkbox.

SCOPE:
1. "Generate Commitments" modal wizard:
   - source type select: Proposal (payment-ready), Policy, Manual
   - SmartSelect with search for the source (proposals/policies), "+" quick-create where permitted
   - Preview (dry-run) table: installment #, due date, amount, grace date, lapse date, initial status
   - parameter warnings banner when grace period or status parameters missing, with ErrorCoach deep links
   - Execute button creating commitments idempotently; duplicate result shows "View existing" link
2. Manual creation form modal: partner, product/plan, currency, installment #, due date, amount, payment mode SmartSelect, reason.
3. Success toast with next-step hint and navigation to the new commitment detail.

TESTS:
- dry-run preview renders schedule
- missing parameter error shows deep link to OL Parameters screen
- duplicate flow shows existing link
- manual form validation inline

GIT:
- commit: "feat(web): commitment generation wizard and manual creation"
- push; tick checkbox

FINAL OUTPUT: wizard behavior, tests, commit hash, pushed branch.
```

---