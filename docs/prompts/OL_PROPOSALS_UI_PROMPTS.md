# OL PROPOSALS UI — PROMPT SERIES (10 prompts)

Backend reference: `docs/prompts/OL_PROPOSALS_BACKEND_PROMPTS.md` (complete), `docs/OL_PROPOSALS_API.md`.
Kits in use: design system, DataTable, SmartSelect, ErrorCoach, ReasonField, ConfirmDialog.

- [x] Prompt 1 — Proposals UI Foundation and Readiness Primitives
- [ ] Prompt 2 — [pending prompt text]
- [ ] Prompt 3 — [pending prompt text]
- [ ] Prompt 4 — [pending prompt text]
- [ ] Prompt 5 — [pending prompt text]
- [ ] Prompt 6 — [pending prompt text]
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
