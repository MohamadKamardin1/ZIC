# OL PROPOSALS UI — PROMPT SERIES (10 prompts)

Backend reference: `docs/prompts/OL_PROPOSALS_BACKEND_PROMPTS.md` (complete), `docs/OL_PROPOSALS_API.md`.
Kits in use: design system, DataTable, SmartSelect, ErrorCoach, ReasonField, ConfirmDialog.

- [x] Prompt 1 — Proposals UI Foundation and Readiness Primitives
- [x] Prompt 2 — Proposals List Page with KPIs and Filters
- [x] Prompt 3 — Convert Quotation Modal: Search, Versions, and Partner Verification
- [x] Prompt 4 — Proposal Detail Page Shell and Overview
- [x] Prompt 5 — Enrichment Workspace and Documents Tab
- [x] Prompt 6 — Beneficiaries Management Tab
- [ ] Prompt 7 — [pending prompt text]
- [ ] Prompt 8 — [pending prompt text]
- [ ] Prompt 9 — [pending prompt text]
- [ ] Prompt 10 — [pending prompt text]

---

## Prompt 1/10 — Proposals UI Foundation and Readiness Primitives

You are a senior frontend engineer for the ZIC Life Insurance Platform. The proposals backend is complete. Build the full Proposals UI.

MANDATORY RULES:
- Use the established design system, DataTable, SmartSelect, ErrorCoach, ReasonField, ConfirmDialog kits.
- Names never UUIDs; every failure teaches the user what happened and how to resolve it.
- Commit and push at the end of each prompt.

SCOPE:
1. Register route Ordinary Life > Ordinary Life Proposals gated by ol_proposals.view; hidden without permission.
2. API hooks (TanStack Query) for: list+KPIs, detail with allowed actions, from-quotation conversion, enrichment sections, beneficiaries CRUD, documents, health answers, underwriting decision, mark-payment-ready, first-premium status, convert-to-policy, cancel, print, generated documents, and all proposal options endpoints.
3. Build proposal-specific primitives:
   - ProposalStatusBadge (parameter-driven colors)
   - ExpiryWarning (amber <7 days, red expired)
   - ReadinessChecklist panel component: pass/fail icons per checklist item, resolution text, deep_link buttons
   - FirstPremiumCard component: commitment number link, status badge, due/paid/balance, allocations mini-table, next-action hint
   - ShareTotalIndicator for beneficiary percentages
4. Unit tests for primitives including ErrorCoach deep-link rendering for proposal error codes.

GIT:
- commit: "feat(web): proposals UI foundation and readiness primitives"
- push; if blocked create feature/web-proposals-foundation and push; tick checkbox

FINAL OUTPUT: hooks, primitives, tests, commit hash, pushed branch.

## Prompt 2/10 — Proposals List Page with KPIs and Filters

You are a senior frontend engineer. Continue the ZIC Proposals UI. Execute ONLY Prompt 2 from the saved series file.

MANDATORY RULES:
- Table-first; actions gated by allowed actions + permissions.
- Commit and push; tick checkbox.

SCOPE:
1. KPI cards: Total Proposals, Pending Underwriting, Payment Ready, Awaiting First Premium, Converted in Period, Expiring Soon.
2. Proposals DataTable with backend columns: proposal_number, policyholder name, agent, employer (badge when present), product/plan summary, total premium, currency, status badge, payment_ready tick, first_premium_posted tick, expiry date with ExpiryWarning, created_at, actions.
3. Filters: status, product, agent, employer presence, expiry window, payment_ready, first_premium_posted; search by number/policyholder/identity; quick chips: Awaiting First Premium, Expiring 7 Days, Pending Underwriting.
4. Row actions from allowed actions: View, Enrich, Mark Payment Ready, Convert to Policy, Cancel, Print.
5. Buttons: Convert Quotation (primary), Export CSV.
6. States: loading skeleton, empty state with guidance linking to quotations, ErrorCoach on fetch failure.

TESTS:
- KPI display and deep links applying filters
- chip filters work
- action visibility by status/permission
- export respects filters

GIT:
- commit: "feat(web): proposals list page with KPIs and filters"
- push; tick checkbox

FINAL OUTPUT: page behavior, tests, commit hash, pushed branch.

## Prompt 3/10 — Convert Quotation Modal: Search, Versions, and Partner Verification

You are a senior frontend engineer. Continue the ZIC Proposals UI. Execute ONLY Prompt 3 from the saved series file.

MANDATORY RULES:
- BR-01 failures must be teachable with deep links to the quotation partner-verification flow.
- Commit and push; tick checkbox.

SCOPE (upgrade the Convert Quotation modal):
1. Replace the raw reference input with a searchable SmartSelect over finalized quotations: quote number, quotation name, policyholder, partner-verified badge, and version.
2. When a quotation has multiple versions, offer a version selector defaulting to the current version.
3. Show a compact summary preview card of the selected quotation: plans, premium, currency.
4. Submitting creates the proposal from the selected quotation + version. On success show "Proposal created" toast and navigate to the proposal detail page.
5. If the backend rejects with PROPOSAL_PARTNER_NOT_VERIFIED, render an ErrorCoach with a deep link into that quotation's partner verification flow (quotation detail).
6. If the backend responds duplicate/already_converted, show an informational banner with a link to view the existing proposal instead of treating it as an error.

TESTS:
- Quotation options show verified badges
- Unverified partner error renders deep link and navigates
- Duplicate shows existing link
- Success navigation works

GIT:
- commit: "feat(web): quotation to proposal conversion modal"
- push; tick checkbox

FINAL OUTPUT: modal behavior, tests, commit hash, pushed branch.

## Prompt 4/10 — Proposal Detail Page Shell and Overview

You are a senior frontend engineer. Continue the ZIC Proposals UI. Execute ONLY Prompt 4.

MANDATORY RULES:
- Master-detail pattern; right-side readiness panel always visible.
- Commit and push; tick checkbox.

SCOPE:
1. Header: proposal number, policyholder name, product/plan, status badge, currency, expiry with ExpiryWarning, payment_ready and first_premium_posted ticks, agent and employer names.
2. Right-side ReadinessChecklist panel rendering live checklist state with pass/fail icons, resolution text, and deep links; Mark Payment Ready button below it (permission-gated).
3. Tabs:
   - Overview: personal details, quotation reference with version switcher (read-only snapshot view), financial summary snapshot, declarations summary, reasons for cancel when present
   - Quotation Source: read-only carried data (plans, members, installments, funds, riders, benefits)
   - History: status timeline with actor, timestamp, previous/new state, reason, source channel
4. Action bar from allowed actions: Enrich, Beneficiaries, Documents, Underwriting, Mark Payment Ready, Convert to Policy, Cancel, Print.
5. Fetch failures render ErrorCoach.

TESTS:
- tabs render from detail payload
- version switcher shows prior quotation snapshot
- checklist panel matches backend state
- no UUIDs rendered

GIT:
- commit: "feat(web): proposal detail page shell and overview"
- push; tick checkbox

FINAL OUTPUT: page structure, tests, commit hash, pushed branch.

## Prompt 5/10 — Enrichment Workspace and Documents Tab

You are a senior frontend engineer. Continue the ZIC Proposals UI. Execute ONLY Prompt 5.

MANDATORY RULES:
- All selects use SmartSelect with '+' quick-create where permitted.
- Bank account numbers stay masked end to end; never render or resend raw values.
- Commit and push; tick checkbox.

SCOPE:
1. Enrichment modal over PATCH /enrich/ with independent sections: employer (corporate partner SmartSelect, employment reference, payroll deduction), intermediary (agent SmartSelect with quick-create; channel display-only from quotation), declarations (PEP/AML tri-state, existing policies count, occupation note, free-text JSON), bank details (bank name SmartSelect, account name, masked account number).
2. Each section has Save and Clear actions; saving one section must not affect the others.
3. Masked account number is placeholder-only — it is included in a payload only when a replacement value is typed.
4. Documents tab: mandatory/uploaded counts, document list (type, status, mandatory badge), upload form using the proposal options document-types endpoint plus file reference.
5. Action bar: Enrich opens the modal; Documents jumps to the tab. Both gated by allowed actions + permissions.
6. Validation and API failures teach: inline validation for declarations JSON, ErrorCoach with retry for rejected saves.

TESTS:
- Employer section save sends selected partner + edited fields
- Masked account number omitted unless replaced
- Invalid declarations JSON blocked with message
- Documents tab lists rows and uploads via mutation

GIT:
- commit: "feat(web): proposal enrichment workspace and documents tab"
- push; tick checkbox

FINAL OUTPUT: modal behavior, documents tab behavior, tests, commit hash, pushed branch.

## Prompt 6/10 — Beneficiaries Management Tab

You are a senior frontend engineer. Continue the ZIC Proposals UI. Execute ONLY Prompt 6.

MANDATORY RULES:
- Share math must be visible and teachable.
- Commit and push; tick checkbox.

SCOPE:
1. Beneficiaries tab: table with name, identity type/number, beneficial type badge, share %, primary star, minor badge with guardian, actions edit/remove.
2. Add/Edit modal: full name, identity type SmartSelect, identity number, beneficial type SmartSelect with '+', share percent, primary toggle, minor toggle revealing guardian fields; live ShareTotalIndicator over the projected set — green at 100, red otherwise.
3. Errors: PROPOSAL_BENEFICIARY_SHARES_INVALID via ErrorCoach listing exact fix steps; duplicate identity inline error; minor without guardian inline error.
4. Remove via confirm dialog; at least one primary enforced with a teachable error.

TESTS:
- Share indicator behavior (under/over/valid live)
- 100-sum validation success and failure
- Minor guardian rule
- Primary enforcement
- Duplicate identity inline
- Remove through confirm dialog

GIT:
- commit: "feat(web): proposal beneficiaries management UI"
- push; tick checkbox

FINAL OUTPUT: table/modal behavior, tests, commit hash, pushed branch.
