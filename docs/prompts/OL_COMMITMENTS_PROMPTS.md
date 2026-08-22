# OL COMMITMENTS MODULE — PROMPT SERIES (12 prompts)

- [x] Prompt 1 — Save Prompt Series File + Discovery + Domain Foundation
- [ ] Prompt 2 — Commitment Generation Engine
- [ ] Prompt 3 — Lifecycle Actions and Payment Allocation
- [ ] Prompt 4 — Grace, Overdue, and Notification Processing
- [ ] Prompt 5 — Commitment List and Detail APIs
- [ ] Prompt 6 — Structured Error Coach Taxonomy (Backend)
- [ ] Prompt 7 — Frontend: Commitments List Page
- [ ] Prompt 8 — Frontend: Commitment Detail and Action Modals
- [ ] Prompt 9 — Frontend: Error Coach UX
- [ ] Prompt 10 — Integrations: Proposals, Policies, Receipts, Reports, Portal
- [ ] Prompt 11 — Full Phase and Step Test Suite
- [ ] Prompt 12 — Seed 10 Scenarios, Docs, Release Verification

---

## Prompt 1/12 — Save Prompt Series File + Discovery + Domain Foundation

```text
You are a senior Django insurance platform engineer. Build the ZIC Ordinary Life Commitments module. The user pasted the FULL 12-prompt series at once.

META-INSTRUCTION (HIGHEST PRIORITY):
1. Before writing any code, create docs/prompts/OL_COMMITMENTS_PROMPTS.md and save ALL 12 prompts of this series EXACTLY as provided, each with a checkbox "[ ] Prompt N — title".
2. Commit and push that file immediately.
3. Execute ONLY Prompt 1 now. When its deliverables are complete, tested, committed, and pushed, tick its checkbox in the file, commit the tick, then proceed to Prompt 2. Never execute two prompts at once. Never skip.

MANDATORY RULES:
- No blocking questions; make senior insurance assumptions and document them.
- Search the repository, the ZIC specification, and any video transcript for every commitment detail; fill missing details with documented assumptions.
- Everything parameterized; nothing hardcoded.
- Every material change audited with actor, before/after, reason, source channel.
- Commit and push at the end of this prompt.

SCOPE:
1. Produce docs/OL_COMMITMENTS_DESIGN.md defining:
   - commitment concept (proposal first premium + policy renewal schedule)
   - status state machine read from OL Commitment Status parameters
   - generation rules from payment frequency, payment period, policy term
   - grace/overdue/lapse behavior from OL Grace Period parameters
   - notification behavior from Grace Period Notification Schedule
   - integration map: proposals, policies, front office receipts, reports, partner portal
   - traceability to specification (BR-03, BR-05, premium transaction/receipt entity)
2. Create Django app ol_commitments with models:
   - OLCommitment: commitment_number, source_type (PROPOSAL|POLICY|MANUAL), source reference, partner display, product/plan, currency, installment_number, due_date, premium_amount, amount_paid, balance, status (validated against OL commitment status parameters), grace_date, lapse_date, reason fields, approval_required, audit fields
   - OLCommitmentAllocation: commitment, receipt reference, amount, payment_mode, currency, exchange_rate, reason, reversal_of, audit fields
   - OLCommitmentNotificationLog
3. Register permission codes: view, create, generate, record_payment, reverse, suspend, waive, cancel, reschedule.
4. Wire audit and domain events: CommitmentGenerated, CommitmentPaymentAllocated, CommitmentOverdue, CommitmentSuspended, CommitmentWaived, CommitmentCancelled, CommitmentCompleted.
5. Implement global structured error shape: { error_code, message, resolution_steps[], field_errors, doc_ref } via a shared exception handler.
6. Admin registration with table-first views.

TESTS:
- model creation and balance computation
- status validated against parameter catalog
- error shape contract

GIT:
- commit: "feat(ol-commitments): save prompt series and create commitment domain foundation"
- push; if blocked create feature/ol-commitments-foundation and push
- tick Prompt 1 checkbox in the saved file and commit

FINAL OUTPUT: design doc summary, models, events, permissions, tests, commit hashes, pushed branch.
```

---

## Prompt 2/12 — Commitment Generation Engine

```text
You are a senior Django insurance engineer. Continue the ZIC OL Commitments module. Read docs/prompts/OL_COMMITMENTS_PROMPTS.md and execute ONLY Prompt 2.

MANDATORY RULES:
- Generation must be idempotent and parameter-driven.
- Commit and push; tick Prompt 2 checkbox when green.

SCOPE:
1. Implement generation services:
   - generate_from_proposal: creates the first premium commitment when a proposal reaches payment-ready state
   - generate_from_policy: creates the full renewal schedule using payment frequency, payment period, policy term, start date, and premium per frequency
   - create_manual: authorized manual commitment
   - bulk import CSV with row- and field-level errors and safe reprocessing
2. Idempotency key = source_type + source_id + installment_number; duplicate attempts return structured error COMMITMENT_DUPLICATE with resolution steps and a reference to the existing commitment.
3. Compute due_date, grace_date, lapse_date from OL Grace Period parameters; initial status from OL Commitment Status parameters (e.g., Pending).
4. Regeneration on premium change: pending commitments are superseded (never deleted) with audit reason; paid commitments untouched.
5. Emit CommitmentGenerated events; audit all generation paths with source channel (SYSTEM, API, IMPORT, MANUAL).

TESTS:
- annual and monthly schedule math against fixtures
- first premium commitment from proposal
- duplicate generation returns COMMITMENT_DUPLICATE
- CSV import error reporting and reprocessing
- supersede behavior preserves history

GIT:
- commit: "feat(ol-commitments): implement commitment generation engine"
- push; tick checkbox

FINAL OUTPUT: services, formulas, error codes added, tests, commit hash, pushed branch.
```

---

## Prompt 3/12 — Lifecycle Actions and Payment Allocation

```text
You are a senior Django insurance engineer. Continue the ZIC OL Commitments module. Execute ONLY Prompt 3 from the saved series file.

MANDATORY RULES:
- State transitions must be read from OL Commitment Status parameter allowed transitions.
- Reasons mandatory for reverse/suspend/waive/cancel/reschedule.
- Commit and push; tick checkbox.

SCOPE:
1. POST endpoints on a commitment:
   - record_payment (allocation): partial and full; full payment moves status to Completed per parameters; overpayment returns structured error COMMITMENT_OVERPAYMENT with resolution (adjust amount or raise credit handling per documented assumption)
   - reverse_allocation: permission-gated, reason mandatory, creates reversal row, restores balance, audit before/after
   - suspend / reactivate
   - waive: sets approval_required hook and emits event; blocked without permission
   - cancel
   - reschedule due_date with parameter limits and reason
2. Invalid transitions return COMMITMENT_INVALID_TRANSITION listing allowed transitions in resolution_steps.
3. Cross-currency allocation uses exchange rate field; currency mismatch without rate returns CURRENCY_MISMATCH error with resolution.
4. Every action writes audit with actor, previous/new state, reason, source channel.

TESTS:
- full transition matrix valid and invalid
- partial then full payment completes commitment
- reversal restores balance and audit
- waive requires permission and flags approval
- overpayment and currency mismatch structured errors

GIT:
- commit: "feat(ol-commitments): implement lifecycle actions and payment allocation"
- push; tick checkbox

FINAL OUTPUT: endpoints, transition enforcement, error codes, tests, commit hash, pushed branch.
```

---

## Prompt 4/12 — Grace, Overdue, and Notification Processing

```text
You are a senior Django insurance engineer. Continue the ZIC OL Commitments module. Execute ONLY Prompt 4.

MANDATORY RULES:
- Batch processing must be idempotent and re-runnable.
- Commit and push; tick checkbox.

SCOPE:
1. Management command process_commitment_overdue:
   - marks unpaid commitments Overdue after due date using grace days from OL Grace Period parameters
   - computes lapse recommendation after lapse days and flags policy-level lapse review event
   - creates OLCommitmentNotificationLog entries per Grace Period Notification Schedule parameters (event type, days offset, channel, recipient)
   - emits CommitmentOverdue events
2. System actor audit entries for batch changes.
3. Notification dispatch is a clean integration point (email/SMS/portal stubs) without external calls.
4. Summary output counts processed/overdue/notified for operations.

TESTS:
- time-frozen scenarios: before due, in grace, overdue, lapse window
- idempotent rerun produces no duplicate logs
- notification schedule respected per channel/recipient

GIT:
- commit: "feat(ol-commitments): implement grace overdue and notification processing"
- push; tick checkbox

FINAL OUTPUT: command behavior, schedule logic, tests, commit hash, pushed branch.
```

---

## Prompt 5/12 — Commitment List and Detail APIs

```text
You are a senior Django engineer. Continue the ZIC OL Commitments module. Execute ONLY Prompt 5.

MANDATORY RULES:
- Table-first, names never UUIDs.
- Commit and push; tick checkbox.

SCOPE:
1. GET list endpoint with columns: commitment_number, source display (proposal/policy), policyholder/partner name, product/plan, installment #, due_date, amount_due, amount_paid, balance, currency, status badge, grace_date, allowed actions.
2. Filters: status, product, source_type, currency, due date range, overdue_only, balance>0; search by commitment number, partner, policy.
3. KPI endpoint: total_due, total_outstanding, overdue_count, collected_in_period.
4. Detail endpoint includes allocations, status history, notification logs, and state+permission-aware allowed actions.
5. CSV export respecting filters.
6. Admin tables mirror the same columns.

TESTS:
- list columns and filters
- KPI math
- allowed actions differ by status and permission
- export respects filters

GIT:
- commit: "feat(ol-commitments): implement commitment list and detail APIs"
- push; tick checkbox

FINAL OUTPUT: endpoint contract, KPI rules, tests, commit hash, pushed branch.
```

---

## Prompt 6/12 — Structured Error Coach Taxonomy (Backend)

```text
You are a senior Django engineer. Continue the ZIC OL Commitments module. Execute ONLY Prompt 6.

MANDATORY RULES:
- Every user-facing failure must teach the user what happened and how to resolve it.
- Commit and push; tick checkbox.

SCOPE:
1. Implement a commitment error registry with codes, messages, and resolution_steps, including at least:
   COMMITMENT_DUPLICATE, COMMITMENT_INVALID_TRANSITION, COMMITMENT_OVERPAYMENT, COMMITMENT_ALREADY_COMPLETED, COMMITMENT_NOT_FOUND, PARAMETER_MISSING, CURRENCY_MISMATCH, RECEIPT_REFERENCE_INVALID, PERMISSION_DENIED, POLICY_NOT_ACTIVE, GRACE_EXPIRED_REVERSAL_BLOCKED, IMPORT_ROW_INVALID
2. PARAMETER_MISSING resolution_steps must include the exact navigation path to the OL Parameters screen that fixes it (e.g., Ordinary Life Parameters > Policy Setup > OL Grace Period) plus a deep_link field.
3. Map Django/DRF validation, permission, and state errors into the global structured shape automatically.
4. Every structured error is logged with correlation id for audit consistency.

TESTS:
- each registry code returns correct shape
- missing grace period parameter produces PARAMETER_MISSING with deep link
- permission denial shape includes resolution

GIT:
- commit: "feat(ol-commitments): implement structured error coach taxonomy"
- push; tick checkbox

FINAL OUTPUT: error registry table, mapping behavior, tests, commit hash, pushed branch.
```

---

## Prompt 7/12 — Frontend: Commitments List Page

```text
You are a senior frontend engineer. Continue the ZIC frontend. Execute ONLY Prompt 7.

MANDATORY RULES:
- Use the established design system, DataTable, and SmartSelect kit.
- Commit and push; tick checkbox.

SCOPE:
1. Route Ordinary Life > Ordinary Life Commitments.
2. KPI cards: total due, outstanding, overdue count, collected in period.
3. Commitments DataTable with the backend columns, status badges, grace/lapse date warnings (amber/red), row actions gated by allowed actions: View, Record Payment, Suspend, Waive, Cancel, Reschedule, Reverse.
4. Filters and search per backend contract; overdue quick filter chip.
5. CSV export button.
6. Empty and loading states; error state rendered through Error Coach when list fetch fails.

TESTS:
- table renders names not UUIDs
- actions hidden by status/permission
- filters and KPI display

GIT:
- commit: "feat(web): implement commitments list page"
- push; tick checkbox

FINAL OUTPUT: page behavior, tests, commit hash, pushed branch.
```

---

## Prompt 8/12 — Frontend: Commitment Detail and Action Modals

```text
You are a senior frontend engineer. Continue the ZIC frontend. Execute ONLY Prompt 8.

MANDATORY RULES:
- Reasons mandatory where backend requires them.
- Commit and push; tick checkbox.

SCOPE:
1. Master-detail page: summary header (commitment number, partner, product, status badge, currency, due/grace/lapse dates), status card, tabs: Overview, Allocations, History, Notifications.
2. Action modals:
   - Record Payment: amount, payment mode SmartSelect, receipt reference, currency + exchange rate when cross-currency; live balance preview
   - Reverse Allocation: reason textarea + confirmation
   - Suspend / Reactivate: reason
   - Waive: reason + approval banner
   - Cancel: reason + confirmation
   - Reschedule: new due date with parameter limit hint
3. Buttons visible only from allowed actions payload.
4. After each success: toast, refetch detail, history tab shows the change.

TESTS:
- modal validation inline
- success flows update tabs
- hidden actions for unauthorized user

GIT:
- commit: "feat(web): implement commitment detail and action modals"
- push; tick checkbox

FINAL OUTPUT: page and modal behaviors, tests, commit hash, pushed branch.
```

---

## Prompt 9/12 — Frontend: Error Coach UX

```text
You are a senior frontend engineer. Continue the ZIC frontend. Execute ONLY Prompt 9.

MANDATORY RULES:
- Errors must teach, not just alarm.
- Commit and push; tick checkbox.

SCOPE:
1. ErrorCoach component rendering the structured error shape:
   - error code chip, plain-language message
   - numbered resolution_steps
   - deep_link button "Open configuration" for PARAMETER_MISSING
   - "View existing" link for COMMITMENT_DUPLICATE
   - retry button where safe
2. Integrate ErrorCoach into: list fetch failures, all action modals, import errors, and payment failures.
3. Inline field errors mapped from field_errors.
4. Success toasts with next-step hint (e.g., "Payment recorded. Commitment completed.").
5. Accessible (aria-live), dark-theme parity.

TESTS:
- ErrorCoach renders each code family correctly
- deep link navigates to OL Parameters screen
- duplicate error shows existing commitment link

GIT:
- commit: "feat(web): implement error coach UX for commitments"
- push; tick checkbox

FINAL OUTPUT: component contract, integration points, tests, commit hash, pushed branch.
```

---

## Prompt 10/12 — Integrations: Proposals, Policies, Receipts, Reports, Portal

```text
You are a senior Django engineer. Continue the ZIC OL Commitments module. Execute ONLY Prompt 10.

MANDATORY RULES:
- Integrate through events and clean seams; no tight coupling.
- Commit and push; tick checkbox.

SCOPE:
1. Event listeners:
   - proposal payment-ready -> generate first premium commitment (idempotent)
   - PolicyIssued -> generate renewal schedule (idempotent)
2. Receipts seam: allocation accepts receipt reference from front office when available; until then accepts manual reference with source channel; document the contract for the future receipts module.
3. Register report category "Ordinary Life Commitments" and expose commitment dataset fields for the reporting module.
4. Dashboard KPI hook for overdue commitments and approvals pending.
5. Partner portal read-only endpoints scoped strictly to linked partner: list and detail of own commitments.
6. Audit consistency check utility verifying every commitment action has an audit row.

TESTS:
- listeners idempotent on repeated events
- portal scoping denies other partners
- audit consistency utility passes on seeded data

GIT:
- commit: "feat(ol-commitments): integrate proposals policies receipts reports and portal hooks"
- push; tick checkbox

FINAL OUTPUT: integration map, contracts, tests, commit hash, pushed branch.
```

---

## Prompt 11/12 — Full Phase and Step Test Suite

```text
You are a senior QA engineer. Continue the ZIC OL Commitments module. Execute ONLY Prompt 11.

MANDATORY RULES:
- Every phase and step must be tested; fix all failures before pushing.
- Commit and push; tick checkbox.

SCOPE:
1. Unit and integration coverage for:
   - generation (annual, monthly, first premium, manual, import)
   - payments (partial, full, overpay, reverse, cross-currency)
   - transitions (every valid and invalid transition from parameters)
   - grace/overdue/lapse batch and notifications
   - permissions matrix for all actions
   - structured errors for the full registry
2. E2E Playwright:
   - list page KPIs and filters
   - detail page record payment success
   - invalid transition shows Error Coach with resolution steps
   - PARAMETER_MISSING deep link opens the OL Parameters screen
   - unauthorized user sees no restricted actions
3. Audit assertions: every action in tests has audit row with actor, before/after, reason, channel.
4. Fix any gaps discovered; no skipped tests.

GIT:
- commit: "test(ol-commitments): full phase and step test suite"
- push; tick checkbox

FINAL OUTPUT: coverage summary, E2E results, audit evidence, commit hash, pushed branch.
```

---

## Prompt 12/12 — Seed 10 Scenarios, Docs, Release Verification

```text
You are a senior Django release engineer. Complete the ZIC OL Commitments module. Execute ONLY Prompt 12.

MANDATORY RULES:
- Seed through DIFFERENT approaches and prove every error path is caught and teachable.
- Commit and push; tick final checkbox; all 12 checkboxes must be ticked at the end.

SCOPE:
1. Seed exactly 10 commitments via different approaches:
   1 manual API creation
   2 proposal event first premium
   3 policy annual generation
   4 policy monthly generation with partial payment
   5 overdue produced by batch processing
   6 suspended with reason
   7 waived with approval flag
   8 cancelled with reason
   9 CSV import row
   10 multi-currency USD fully paid
2. Additionally attempt and CATCH three failure scenarios, storing proof payloads:
   duplicate generation, invalid transition, missing parameter (temporarily unset then restored)
3. Verify UI-ready structured errors for all three and that Error Coach renders them (E2E assertion).
4. Run audit consistency report; zero orphan actions allowed.
5. Documentation:
   - docs/OL_COMMITMENTS_USER_GUIDE.md with error code + resolution table
   - docs/OL_COMMITMENTS_ADMIN_GUIDE.md
   - docs/OL_COMMITMENTS_API.md
6. Final verification: backend and frontend lint/typecheck/tests/E2E green; mark module complete in docs/prompts/OL_COMMITMENTS_PROMPTS.md.

GIT:
- commit: "feat(ol-commitments): seed ten commitment scenarios docs and release"
- push; if blocked create feature/ol-commitments-complete and push
- tag v0.6.0-ol-commitments if tagging convention exists

FINAL OUTPUT:
Return the FULL commitment module summary: models, endpoints, parameters consumed, integrations, error registry, seed scenario results, error-catch proofs, audit consistency result, test/E2E results, docs added, all 12 checkboxes ticked, commit hash/tag, pushed branch, and next recommended module.
```

---