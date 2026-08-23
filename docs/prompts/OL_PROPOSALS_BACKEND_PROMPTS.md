# OL PROPOSALS BACKEND — PROMPT SERIES (12 prompts)

- [x] Prompt 1 — Save Prompt Series + Discovery + Proposal Domain Foundation
- [x] Prompt 2 — Quotation to Proposal Conversion
- [x] Prompt 3 — Enrichment and Beneficiaries
- [x] Prompt 4 — Documents, Health Answers, and Underwriting Hook
- [x] Prompt 5 — Payment Readiness Evaluation Engine
- [x] Prompt 6 — First Premium Tracking and Receipt Seam
- [ ] Prompt 7 — [pending prompt text]
- [x] Prompt 8 — Lifecycle List and Detail APIs
- [x] Prompt 9 — Proposal Printout and Options Endpoints
- [x] Prompt 10 — Dashboard, Reports, Portal, and Notifications Integration
- [ ] Prompt 11 — Full Step and Error Matrix Test Suite
- [ ] Prompt 12 — [pending prompt text]

> **Note on fidelity:** prompts 2–12 were not included in the pasted series message for this session. They will be appended `EXACTLY as provided` when the user supplies them, then executed strictly one at a time. Prompt 1 below is saved verbatim.

---

## Prompt 1/12 — Save Prompt Series + Discovery + Proposal Domain Foundation

```text
You are a senior Django insurance platform engineer. Build the ZIC Ordinary Life Proposals backend. The user pasted the FULL 12-prompt series at once.

META-INSTRUCTION (HIGHEST PRIORITY):
1. Before coding, create docs/prompts/OL_PROPOSALS_BACKEND_PROMPTS.md and save ALL 12 prompts EXACTLY as provided, each with a checkbox "[ ] Prompt N — title".
2. Commit and push that file immediately.
3. Execute ONLY Prompt 1 now; when green, tick its checkbox, commit, then proceed to Prompt 2. Never merge or skip prompts.

MANDATORY RULES:
- No blocking questions; make senior insurance assumptions and document them.
- Everything parameterized; names never UUIDs; every material change audited with actor, before/after, reason, source channel.
- Reuse existing IAM, audit, OL Parameters, structured-error, and commitments seams.
- Commit and push at the end of each prompt.

SCOPE:
1. Produce docs/OL_PROPOSALS_DESIGN.md covering:
   - proposal concept per specification section 6.1 (quotation conversion, enrichment, payment-ready, first premium, policy conversion)
   - BR-01 and BR-03 enforcement points
   - status state machine parameterization
   - event map: ProposalCreated, ProposalEnriched, ProposalPaymentReady, ProposalConverted, ProposalCancelled, ProposalExpired, MedicalRequirementRaised
   - integration map: quotations, commitments, receipts seam, policies stub, underwriting hook, documents, portal, reports
2. Create/extend Django app ol_proposals with models:
   - OLProposal: proposal_number unique; quotation + quotation version reference; status; partner (policyholder); agent/intermediary partner; employer partner optional; currency; expiry_date; payment_ready flag + timestamp; underwriting_status; medical_required flag; converted_policy reference; reason fields; audit fields
   - OLProposalPlanConfig, OLProposalMember, OLProposalInstallmentConfig(+rows), OLProposalFundAllocation, OLProposalRider, OLProposalBenefit (carried from quotation)
   - OLProposalBeneficiary: person name, identity type/number, beneficial type parameter, share_percent, is_primary, minor + guardian fields
   - OLProposalDocument: document type, file reference, mandatory flag, status, uploaded_by
   - OLProposalHealthAnswer: questionnaire item, health question, answer, score, triggers_medical
3. Add OL Proposal Status catalog to OL Parameters (code, name, order, terminal, allowed transitions) seeded with: ENRICHMENT, PENDING_UNDERWRITING, PAYMENT_READY, AWAITING_FIRST_PREMIUM, CONVERTED, CANCELLED, EXPIRED.
4. Register permissions: ol_proposals.view, create, enrich, upload_documents, mark_payment_ready, convert, cancel, print.
5. Extend the structured error registry with proposal codes: PROPOSAL_PARTNER_NOT_VERIFIED, PROPOSAL_BENEFICIARY_SHARES_INVALID, PROPOSAL_MANDATORY_DOCUMENTS_MISSING, PROPOSAL_UNDERWRITING_PENDING, PROPOSAL_NOT_PAYMENT_READY, PROPOSAL_FIRST_PREMIUM_NOT_POSTED, PROPOSAL_EXPIRED, PROPOSAL_ALREADY_CONVERTED, PROPOSAL_INVALID_TRANSITION, PARAMETER_MISSING.
6. Admin tables, base list/detail API skeleton.

TESTS: models, status catalog validation, error shapes, permissions.

GIT:
- commit: "feat(ol-proposals): save prompt series and create proposal domain foundation"
- push; if blocked create feature/ol-proposals-foundation and push; tick checkbox

FINAL OUTPUT: design summary, models, events, permissions, error codes, tests, commit hash, pushed branch.
```

---

## Prompt 2/12 — Quotation to Proposal Conversion

```text
You are a senior Django insurance engineer. Continue the ZIC OL Proposals backend. Execute ONLY Prompt 2 from the saved series file.

MANDATORY RULES:
- Conversion must be idempotent and enforce BR-01.
- Commit and push; tick checkbox.

SCOPE:
1. Implement conversion service convert_quotation_to_proposal(quotation, version):
   - require quotation FINALIZED and partner_verified true; otherwise PROPOSAL_PARTNER_NOT_VERIFIED with resolution steps pointing to the quotation partner-verification flow
   - idempotency key = quotation + version; duplicate returns existing proposal with PROPOSAL_ALREADY_CONVERTED-style informational payload
   - carry over: prospect/personal details, plan configs, members, installment configs and rows, fund allocations, riders, benefits, financial summary snapshot, currency, agent
   - set initial status ENRICHMENT, expiry_date from OL default proposal validity days
   - emit ProposalCreated
2. Move ownership of conversion into ol_proposals; refactor the existing quotations convert endpoint to delegate to this service without breaking its contract.
3. Expose POST /api/v1/ol/proposals/from-quotation/{quotation_id}/ with optional version parameter.
4. Audit conversion with source channel and actor; log carried record counts.

TESTS:
- successful conversion carries every child dataset correctly
- unverified partner blocked with teachable error
- repeated conversion returns same proposal (idempotent)
- expiry date computed from parameter
- quotation endpoint delegation works unchanged

GIT:
- commit: "feat(ol-proposals): implement quotation to proposal conversion"
- push; tick checkbox

FINAL OUTPUT: service contract, endpoint, refactor notes, tests, commit hash, pushed branch.
```

---

## Prompt 3/12 — Enrichment and Beneficiaries

```text
You are a senior Django insurance engineer. Continue the ZIC OL Proposals backend. Execute ONLY Prompt 3.

MANDATORY RULES:
- Enrichment covers details not captured at quote stage per specification 6.1.
- Commit and push; tick checkbox.

SCOPE:
1. Enrichment endpoints (PATCH sections):
   - employer: corporate partner SmartSelect-compatible options; employment reference, payroll deduction flag
   - intermediary: agent/broker partner reference and commission-relevant channel
   - declarations: PEP flag, AML flag, existing policies count, occupation risk note, free-text declarations
   - policyholder bank details for maturity/claims payouts (bank, account name, number masked in responses)
2. Beneficiaries CRUD:
   - add/update/remove beneficiaries with beneficial type parameter options
   - validation: at least one primary; share percentages sum exactly 100; minor requires guardian; duplicate identity prevention
   - errors return PROPOSAL_BENEFICIARY_SHARES_INVALID with resolution steps
3. Enrichment completeness service computing missing required sections for payment-ready.
4. Emit ProposalEnriched events; audit every section change with before/after.

TESTS:
- employer/intermediary linkage validation
- declarations save and mask bank account
- beneficiary share math and guardian rule
- completeness service lists missing sections

GIT:
- commit: "feat(ol-proposals): implement enrichment and beneficiaries"
- push; tick checkbox

FINAL OUTPUT: endpoints, validation rules, tests, commit hash, pushed branch.
```

---

## Prompt 4/12 — Documents, Health Answers, and Underwriting Hook

```text
You are a senior Django insurance engineer. Continue the ZIC OL Proposals backend. Execute ONLY Prompt 4.

MANDATORY RULES:
- Mandatory documents block payment-ready, mirroring the BR-12 pattern.
- Commit and push; tick checkbox.

SCOPE:
1. Document requirement configuration: per product/plan document types with mandatory flag (parameterized; seed identity document, signature, KYC form defaults).
2. POST document upload endpoint storing file reference, type, uploaded_by; list endpoint with mandatory/optional badges and status.
3. Health answers endpoint:
   - serve applicable OL health questionnaire for product/plan and thresholds
   - accept answers; evaluate triggers using questionnaire item configuration
   - when triggered: set medical_required, status PENDING_UNDERWRITING, emit MedicalRequirementRaised for the future underwriting module
4. Underwriting clearance seam: POST underwriting-decision endpoint (clear / load / decline) permission-gated, setting underwriting_status and returning status to ENRICHMENT or terminal rejection with reasons.
5. Audit uploads and decisions; structured errors for missing mandatory documents.

TESTS:
- mandatory vs optional document behavior
- health trigger moves status to PENDING_UNDERWRITING and emits event
- clearance returns status correctly; decline blocks progression
- upload audit rows

GIT:
- commit: "feat(ol-proposals): implement documents and health answers underwriting hook"
- push; tick checkbox

FINAL OUTPUT: config model, endpoints, trigger logic, tests, commit hash, pushed branch.
```

---

## Prompt 5/12 — Payment Readiness Evaluation Engine

```text
You are a senior Django insurance engineer. Continue the ZIC OL Proposals backend. Execute ONLY Prompt 5.

MANDATORY RULES:
- The checklist must be teachable: every failed item returns code + resolution steps.
- Commit and push; tick checkbox.

SCOPE:
1. Implement evaluate_payment_ready service computing checklist items:
   - partner_verified
   - enrichment_complete
   - beneficiaries_valid
   - mandatory_documents_complete
   - underwriting_cleared_or_not_required
   - not_expired
   - quotation_version_current
2. POST /api/v1/ol-proposals/{id}/mark-payment-ready/:
   - all pass: status PAYMENT_READY then AWAITING_FIRST_PREMIUM, set payment_ready_at, emit ProposalPaymentReady (commitments listener creates first premium commitment)
   - any fail: 409 with structured error listing failed checklist items, each with error_code, message, resolution_steps, and deep_link to the fixing screen
3. GET checklist endpoint for UI rendering of current pass/fail state.
4. Re-evaluation allowed; status changes audited with full checklist snapshot.

TESTS:
- each failing item produces correct teachable error and deep link
- success path emits event exactly once per transition
- checklist endpoint matches service result
- audit snapshot stored

GIT:
- commit: "feat(ol-proposals): implement payment ready evaluation engine"
- push; tick checkbox

FINAL OUTPUT: checklist contract, endpoints, event flow, tests, commit hash, pushed branch.
```

---

## Prompt 6/12 — First Premium Tracking and Receipt Seam

```text
You are a senior Django insurance engineer. Continue the ZIC OL Proposals backend. Execute ONLY Prompt 6.

MANDATORY RULES:
- BR-03 guard must be airtight and reusable by the future receipts and policies modules.
- Commit and push; tick checkbox.

SCOPE:
1. Link first premium commitment (source_type PROPOSAL, installment 1) to proposal on ProposalPaymentReady; store reference.
2. GET first-premium status endpoint: commitment status, amount due, paid, balance, allocations, payment mode, last payment date.
3. Implement first_premium_posted guard service: true only when linked commitment status is Completed (fully allocated).
4. Receipts seam contract documented in docs/OL_PROPOSALS_RECEIPTS_SEAM.md:
   - future receipts module allocates to the commitment; proposals module only reads status
   - define PremiumReceived event contract for later integration
5. Expose payment status in proposal detail payload with next-action hints (e.g., "Record receipt in Front Office").

TESTS:
- guard false for partial payment, true for full payment
- detail payload shows commitment status and hints
- seam doc matches commitments allocation contract

GIT:
- commit: "feat(ol-proposals): implement first premium tracking and receipt seam"
- push; tick checkbox

FINAL OUTPUT: guard logic, endpoints, seam contract, tests, commit hash, pushed branch.
```

---

## Prompt 8/12 — Lifecycle List and Detail APIs

```text
You are a senior Django insurance engineer. Continue the ZIC OL Proposals backend. Execute ONLY Prompt 8.

MANDATORY RULES:
- Table-first; names never UUIDs; actions state+permission aware.
- Commit and push; tick checkbox.

SCOPE:
1. List endpoint columns: proposal_number, policyholder name, agent, employer if any, product/plan summary, total premium, currency, status badge, payment_ready, first_premium_posted, expiry_date, created_at, allowed actions.
2. Filters: status, product, agent, employer presence, expiry window, payment_ready, first_premium_posted; search by number/policyholder/identity.
3. KPI endpoint: total proposals, awaiting underwriting, payment ready, awaiting first premium, converted in period, expiring soon.
4. Detail endpoint: header data, enrichment sections, beneficiaries, documents, health/underwriting, checklist state, first premium status, versions of source quotation, allowed actions.
5. Lifecycle actions: cancel (reason mandatory), reactivate-from-expiry only via documented parameter-driven rule if allowed; transitions enforced from OL Proposal Status parameters; invalid transitions return PROPOSAL_INVALID_TRANSITION listing allowed transitions.
6. Expiry batch command marking expired proposals with system audit; idempotent.
7. CSV export respecting filters.

TESTS:
- list columns/filters/KPIs
- cancel requires reason and audits
- invalid transition teachable error
- expiry batch idempotent

GIT:
- commit: "feat(ol-proposals): implement lifecycle list and detail APIs"
- push; tick checkbox

FINAL OUTPUT: endpoint contract, KPI rules, lifecycle rules, tests, commit hash, pushed branch.
```

---

## Prompt 9/12 — Proposal Printout and Options Endpoints

```text
You are a senior Django insurance engineer. Continue the ZIC OL Proposals backend. Execute ONLY Prompt 9.

MANDATORY RULES:
- Generated documents retain source and template version.
- Commit and push; tick checkbox.

SCOPE:
1. Proposal summary print template (template code + version) with variables: proposal number, policyholder, beneficiaries, employer/intermediary, plans, terms, premiums, benefits, riders, first premium due, expiry, declarations, company header.
2. POST print endpoint generating HTML+PDF, storing OLProposalDocument-style generated document linked to proposal and template version; GET documents list.
3. Options endpoints for proposal UI:
   - proposal statuses
   - corporate partners (employers)
   - intermediary/agent partners
   - beneficial types
   - document types
   - banks for policyholder bank details
4. Admin tables for proposals, beneficiaries, documents.

TESTS:
- printout renders with all variable groups
- document stores template version and source link
- options endpoints labeled and active-only

GIT:
- commit: "feat(ol-proposals): implement proposal printout and options endpoints"
- push; tick checkbox

FINAL OUTPUT: template variables, endpoints, tests, commit hash, pushed branch.
```

---

## Prompt 10/12 — Dashboard, Reports, Portal, and Notifications Integration

```text
You are a senior Django insurance engineer. Continue the ZIC OL Proposals backend. Execute ONLY Prompt 10.

MANDATORY RULES:
- Integrate through events and clean seams.
- Commit and push; tick checkbox.

SCOPE:
1. Dashboard KPI hook: awaiting first premium count and amount, expiring-in-7-days count, pending underwriting count (role-filtered).
2. Register report category "Ordinary Life Proposals" and expose dataset fields (status, product, agent, premium, dates) for the reporting module.
3. Partner portal read-only endpoints scoped strictly to linked partner: own proposals list and detail without internal actions; sanitized errors.
4. Notification events: ProposalExpiringSoon (from expiry batch), ProposalPaymentReady, ProposalConverted into the notification center seam used by commitments.
5. Audit consistency utility covering proposal actions.

TESTS:
- portal scoping denies other partners
- dashboard KPI math
- notification events emitted once
- audit utility passes

GIT:
- commit: "feat(ol-proposals): integrate dashboard reports portal notifications"
- push; tick checkbox

FINAL OUTPUT: integration map, tests, commit hash, pushed branch.
```

---

## Prompt 11/12 — Full Step and Error Matrix Test Suite

```text
You are a senior QA engineer. Continue the ZIC OL Proposals backend. Execute ONLY Prompt 11.

MANDATORY RULES:
- Every step and error path tested; fix all failures before pushing.
- Commit and push; tick checkbox.

SCOPE:
1. Integration tests for the complete happy path:
   quotation finalize -> partner verify -> convert -> enrich -> beneficiaries -> documents -> health answers -> payment ready -> first premium commitment -> allocate full payment -> convert to policy.
2. Error matrix tests asserting structured teachable errors for every proposal error code, including deep links and resolution steps.
3. Permission matrix for all endpoints and actions.
4. Idempotency tests: conversion, payment-ready, policy conversion, expiry batch.
5. Audit assertions: every state change has audit row with actor, before/after, reason where required, source channel.
6. E2E API flow tests simulating staff and portal users.

GIT:
- commit: "test(ol-proposals): full step and error matrix test suite"
- push; tick checkbox

FINAL OUTPUT: coverage summary, audit evidence, test results, commit hash, pushed branch.
```

---