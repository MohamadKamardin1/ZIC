# FRONT OFFICE RECEIPTS UI — FULL SERIES

## [x] Prompt 1 — Save Series File + Foundation + Contract-First API Layer

```text
You are a senior frontend engineer for the ZIC Life Insurance Platform. The Front Office Receipts backend is being built in parallel by another agent from docs/prompts/FRONT_OFFICE_RECEIPTS_BACKEND_PROMPTS.md. Build the receipts frontend contract-first. The user pasted the FULL 10-prompt series at once.

META-INSTRUCTION (HIGHEST PRIORITY):
1. Before coding, create docs/prompts/FRONT_OFFICE_RECEIPTS_UI_PROMPTS.md and save ALL 10 prompts EXACTLY as provided, each with a checkbox "[ ] Prompt N — title".
2. Commit and push that file immediately.
3. Execute ONLY Prompt 1 now; when green, tick its checkbox, commit, then proceed to Prompt 2. Never merge or skip prompts.

MANDATORY RULES:
- Use the established design system, DataTable, SmartSelect, ErrorCoach, ReasonField, ConfirmDialog kits.
- Names never UUIDs; every failure teaches the user what happened and how to resolve it.
- Do not hardcode business data; options come from options endpoints (or mocks mirroring them).
- Commit and push at the end of each prompt.

SCOPE:
1. Read docs/FRONT_OFFICE_RECEIPTS_API.md (or the backend prompt series if the doc is not merged yet) and implement a typed receipts API client covering exactly these endpoints:
   - list, create, patch draft, post
   - allocation-options, allocate, auto-allocate
   - reverse, allocation reverse, cancel
   - print, documents
   - import dry-run/commit, imports list/detail, CSV template
   - KPIs, exchange-rate
   - options: branches, currencies, payment-modes, bank-accounts, statuses
   - portal receipts list/detail
2. Implement MSW mock handlers mirroring the contract, including structured errors (RECEIPT_OVERALLOCATION, RECEIPT_CURRENCY_MISMATCH, RECEIPT_PARAMETER_MISSING with deepLink, etc.); enable via VITE_USE_MOCKS.
3. Register route Front Office > Receipts gated by front_office.receipts.view.
4. Build receipts primitives:
   - ReceiptStatusBadge
   - AmountCell with currency formatting and amount-in-words tooltip
   - AllocationProgressBar (allocated vs receipt amount)
   - MaskedAccount with permission-gated show/hide
   - PaymentModeBadge
   - FirstPremiumBadge for proposal installment-1 commitments
5. Unit tests: mock contract parity for payloads, primitives rendering, route gating.

GIT:
- commit: "feat(web): receipts UI foundation and contract-first API layer"
- push; if blocked create feature/web-receipts-foundation and push; tick checkbox

FINAL OUTPUT: client surface, mock coverage, primitives, tests, commit hash, pushed branch.
```

---

## [ ] Prompt 2 — Receipts List Page and Work Queue

```text
You are a senior frontend engineer. Continue the ZIC Receipts UI. Execute ONLY Prompt 2 from the saved series file.

MANDATORY RULES:
- Table-first; actions gated by allowed actions + permissions.
- Commit and push; tick checkbox.

SCOPE:
1. KPI cards: Received Today, Allocated in Period, Unallocated Amount, Receipt Count, Reversed Amount.
2. Receipts DataTable with contract columns: receipt_number, receipt_date, payer_display, branch_display, payment_mode_display, currency_display, receipt_amount, allocated_amount, unallocated_amount with AllocationProgressBar, status badge, source_module, created_by_display, posted_by_display, actions.
3. Filters: status, branch, currency, payment_mode, payer, source_module, date range; quick chips: Unallocated Only, Reversed Only, Today.
4. Search: receipt number, payer name, payment reference, source reference.
5. Row actions from allowed actions: View, Edit (draft), Post, Allocate, Reverse, Cancel, Print.
6. Buttons: New Receipt (primary), Import CSV, Export CSV.
7. States: skeleton, empty state with guidance, ErrorCoach on fetch failure.

TESTS:
- KPI display
- chips and filters
- action visibility by status/permission
- export respects filters

GIT:
- commit: "feat(web): receipts list page with KPIs and work queue"
- push; tick checkbox

FINAL OUTPUT: page behavior, tests, commit hash, pushed branch.
```

---

## [ ] Prompt 3 — Receipt Creation and Posting

```text
You are a senior frontend engineer. Continue the ZIC Receipts UI. Execute ONLY Prompt 3.

MANDATORY RULES:
- Payment-mode rules must drive field requirements live.
- Commit and push; tick checkbox.

SCOPE:
1. New Receipt form:
   - receipt date default today
   - branch SmartSelect with "+"
   - payer/partner SmartSelect with search and "+"
   - source module select; when OL_PROPOSAL, source reference SmartSelect searching proposals with first-premium status hint
   - currency SmartSelect
   - payment mode SmartSelect; on change apply rule: requires_reference shows mandatory payment reference, requires_bank_account shows bank account SmartSelect (masked options)
   - amount with live amount-in-words preview
   - narration
2. Actions: Save Draft, Save & Post.
3. Save & Post opens ConfirmDialog summarizing branch/payer/mode/amount; on success toast with receipt number and next-step hint "Allocate to commitments".
4. Idempotency: generate X-Idempotency-Key per submit; duplicate response shows informational banner with link to existing receipt.
5. Posted receipts open read-only with immutability notice; drafts editable.
6. Inline validation from fieldErrors; structured errors via ErrorCoach.

TESTS:
- payment mode rule toggling
- amount-in-words preview
- draft vs post flows
- duplicate idempotent banner
- posted read-only behavior

GIT:
- commit: "feat(web): receipt creation and posting forms"
- push; tick checkbox

FINAL OUTPUT: form behavior, rule mapping, tests, commit hash, pushed branch.
```

---

## [ ] Prompt 4 — Receipt Detail Page with Tabs and Audit Timeline

```text
You are a senior frontend engineer. Continue the ZIC Receipts UI. Execute ONLY Prompt 4.

MANDATORY RULES:
- Master-detail pattern; money visibility with controls.
- Commit and push; tick checkbox.

SCOPE:
1. Header: receipt number, date, payer, branch, payment mode badge, currency, amount, AllocationProgressBar, status badge, posted_by/at, reversed/cancelled banner with reason when present.
2. Account details card: bank account masked with permission-gated show/hide, payment reference.
3. Tabs:
   - Allocations: table with target display (commitment number + source display), amount, currency, exchange rate when cross-currency, allocation status, reversal link
   - Reversals: reversal history with reversal number, reason, created_by/at
   - Documents: generated receipt printouts with template version and preview/download
   - Audit Timeline: create/post/allocate/reverse/cancel/print events with actor, timestamp, before/after summary, reason, source channel
4. Action bar from allowed actions: Edit, Post, Allocate, Auto-Allocate, Reverse, Cancel, Print.

TESTS:
- tabs render from detail payload
- masked account toggle permission
- audit timeline completeness
- no UUIDs rendered

GIT:
- commit: "feat(web): receipt detail page with allocations reversals audit tabs"
- push; tick checkbox

FINAL OUTPUT: page structure, tests, commit hash, pushed branch.
```

---

## [ ] Prompt 5 — Allocation and Auto-Allocation UI (First Premium Aware)

```text
You are a senior frontend engineer. Continue the ZIC Receipts UI. Execute ONLY Prompt 5.

MANDATORY RULES:
- Over-allocation and currency mismatches must be teachable.
- First premium allocation must visibly explain its effect.
- Commit and push; tick checkbox.

SCOPE:
1. Allocate modal:
   - open commitments table for the payer: commitment number, source display, product/plan, due date, balance, status, FirstPremiumBadge when source PROPOSAL installment 1
   - per-row amount input with running total; total cannot exceed unallocated amount or row balance (inline blocking)
   - cross-currency: exchange rate input appears per row; converted amount preview; missing rate returns ErrorCoach with deep link to exchange rate parameters
2. Auto-Allocate button: confirms oldest-first rule in the dialog; result summary panel listing created allocations and remaining unallocated amount.
3. Success behaviors:
   - toast "Allocation recorded"
   - when a first premium commitment completes: additional success banner "First premium posted. Proposal <number> can now convert to policy." with link to the proposal
4. Errors: RECEIPT_OVERALLOCATION, RECEIPT_ALLOCATION_INVALID, RECEIPT_INVALID_STATUS via ErrorCoach with resolution steps.

TESTS:
- running total blocking over-allocation
- auto-allocate summary rendering
- first premium banner and link
- cross-currency preview and missing-rate coach

GIT:
- commit: "feat(web): receipt allocation and auto allocation UI"
- push; tick checkbox

FINAL OUTPUT: modal behavior, first-premium UX, tests, commit hash, pushed branch.
```

---

## [ ] Prompt 6 — Reversal, Allocation Reversal, and Cancellation UI

```text
You are a senior frontend engineer. Continue the ZIC Receipts UI. Execute ONLY Prompt 6.

MANDATORY RULES:
- Reversals are dangerous actions: impact preview + reason + confirm.
- Commit and push; tick checkbox.

SCOPE:
1. Reverse Receipt modal:
   - impact preview listing every allocation that will be reversed with commitment displays and restored balances
   - warning banner when a first premium allocation will be reversed: "Proposal conversion guard will return to false unless the policy is already issued."
   - ReasonField mandatory + danger ConfirmDialog
2. Reverse single allocation from Allocations tab row action with reason and confirm.
3. Cancel Draft modal with ReasonField.
4. Errors: RECEIPT_ALREADY_REVERSED, RECEIPT_REVERSAL_LOCKED (lock period) via ErrorCoach with resolution steps.
5. After success: status badge updates, watermark note appears on print preview, audit timeline entry visible.

TESTS:
- impact preview lists allocations
- first premium warning shown
- reason enforcement
- lock-period coach rendering

GIT:
- commit: "feat(web): receipt reversal cancellation and multi currency coach"
- push; tick checkbox

FINAL OUTPUT: modal behaviors, tests, commit hash, pushed branch.
```

---

## [ ] Prompt 7 — Bulk Receipt Import UI

```text
You are a senior frontend engineer. Continue the ZIC Receipts UI. Execute ONLY Prompt 7.

MANDATORY RULES:
- Imports must explain every row error and allow safe reprocessing.
- Commit and push; tick checkbox.

SCOPE:
1. Import modal: CSV template download, file upload, dry-run default.
2. Dry-run results table: row #, status OK/ERROR, field-level messages with resolution hints; summary counts.
3. Commit step: import mode select (create drafts / post / post-and-allocate when target commitment provided); enabled only when no blocking errors or explicit partial confirmation.
4. Import history page section: batch list with file name, uploaded by, date, counts, status badge; drill-down to row errors; reprocess action.
5. Errors rendered through ErrorCoach taxonomy (RECEIPT_IMPORT_ROW_INVALID, RECEIPT_IMPORT_DUPLICATE, RECEIPT_IMPORT_PARTIAL_FAILURE).

TESTS:
- template download
- dry-run error table
- commit gating
- history drill-down and reprocess

GIT:
- commit: "feat(web): receipt bulk import UI"
- push; tick checkbox

FINAL OUTPUT: import UX, tests, commit hash, pushed branch.
```

---

## [ ] Prompt 8 — Receipt Print Preview and Documents UI

```text
You are a senior frontend engineer. Continue the ZIC Receipts UI. Execute ONLY Prompt 8.

MANDATORY RULES:
- Use the authenticated print pipeline; never raw window.open to /api/.
- Commit and push; tick checkbox.

SCOPE:
1. Print action opens preview modal rendering the receipt PDF (logo, company header, receipt number, amount in figures and words, allocations table, signatures, footer template version).
2. Buttons: Download, Open in New Tab (signed ticket), Close.
3. Watermarks: REVERSED and CANCELLED receipts show the watermark in preview and on the PDF.
4. Documents tab lists instances with template name/version, generated by/at, page count, actions.
5. Failures via ErrorCoach (e.g., TEMPLATE_PENDING, PARAMETER_MISSING branding with deep link to System Parameters).

TESTS:
- preview renders from authenticated blob
- watermark visibility by status
- documents list names not UUIDs
- coach on failure

GIT:
- commit: "feat(web): receipt print preview and documents UI"
- push; tick checkbox

FINAL OUTPUT: preview behavior, tests, commit hash, pushed branch.
```

---

## [ ] Prompt 9 — Portal Receipts, Dashboard KPIs, Notifications

```text
You are a senior frontend engineer. Continue the ZIC Receipts UI. Execute ONLY Prompt 9.

MANDATORY RULES:
- Portal strictly read-only and partner-scoped; sanitized errors.
- Commit and push; tick checkbox.

SCOPE:
1. Partner portal route /portal/receipts:
   - read-only list of own receipts (number, date, amount, mode, status)
   - read-only detail with own allocations only
   - info banner: "For disputes or corrections, contact your ZIC representative or raise a ticket." with Raise Ticket shortcut
2. Staff dashboard cards: Receipts Today, Amount Received Today, Unallocated Receipts, Reversed Amount; deep links applying list filters.
3. Notification center entries for ReceiptPosted, ReceiptReversed, FirstPremiumReceived with deep links.

TESTS:
- portal scoping shows own data only and no actions
- dashboard deep links
- notification deep links

GIT:
- commit: "feat(web): receipts portal dashboard and notifications"
- push; tick checkbox

FINAL OUTPUT: portal and dashboard behavior, tests, commit hash, pushed branch.
```

---

## [ ] Prompt 10 — E2E, Contract Verification, Merge Readiness, Release

```text
You are a senior QA and frontend release engineer. Complete the ZIC Receipts UI. Execute ONLY Prompt 10.

MANDATORY RULES:
- Verify the frontend against the REAL merged backend before release; fix all drift.
- Commit and push; tick final checkbox; all 10 checkboxes ticked at the end.

SCOPE:
1. Contract verification:
   - fetch backend OpenAPI schema from the merged branch
   - compare every receipts endpoint, payload field, and error shape against the typed client and mocks
   - produce docs/RECEIPTS_CONTRACT_VERIFICATION.md listing matched/drifted items; fix drift in the frontend client
   - set VITE_USE_MOCKS=false for real runs and remove mock-only shortcuts
2. Playwright E2E against real backend seeds:
   - create draft -> post -> partial allocate -> full first-premium allocate -> proposal unlock banner -> convert proposal visible as unblocked
   - reverse receipt with reason; proposal guard warning; watermark on print
   - import dry-run with row errors then commit
   - portal read-only scoping
   - ErrorCoach deep links for PARAMETER_MISSING and over-allocation
3. Accessibility pass (focus, aria-live for coaches/toasts, keyboard modals) and dark theme parity.
4. Documentation:
   - frontend/docs/RECEIPTS_UI_GUIDE.md with screen map and error-code resolution table
   - merge checklist: env flags, mock removal, seed dependencies, permission seeds required from backend
5. Run lint/typecheck/unit/E2E green; mark series complete in the saved prompt file.

GIT:
- commit: "feat(web): receipts UI e2e contract verification docs and release"
- push; if blocked create feature/web-receipts-complete and push
- tag v1.1.0-web-receipts if tagging convention exists

FINAL OUTPUT:
Return the FULL receipts UI summary: screens built, contract verification results (matched/drifted/fixed), E2E results, accessibility notes, docs added, merge checklist, all 10 checkboxes ticked, commit hash/tag, pushed branch, and next recommended module (OL Policies backend + Policy Servicing, then Group Credit).
```
