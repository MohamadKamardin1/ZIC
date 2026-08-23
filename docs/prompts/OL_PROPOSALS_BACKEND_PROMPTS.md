# OL PROPOSALS BACKEND — PROMPT SERIES (12 prompts)

- [x] Prompt 1 — Save Prompt Series + Discovery + Proposal Domain Foundation
- [ ] Prompt 2 — Quotation to Proposal Conversion
- [ ] Prompt 3 — [pending prompt text]
- [ ] Prompt 4 — [pending prompt text]
- [ ] Prompt 5 — [pending prompt text]
- [ ] Prompt 6 — [pending prompt text]
- [ ] Prompt 7 — [pending prompt text]
- [ ] Prompt 8 — [pending prompt text]
- [ ] Prompt 9 — [pending prompt text]
- [ ] Prompt 10 — [pending prompt text]
- [ ] Prompt 11 — [pending prompt text]
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