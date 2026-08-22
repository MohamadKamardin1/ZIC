# OL COMMITMENTS UI — PROMPT SERIES (10 prompts)

- [ ] Prompt 1 — Commitments UI Foundation and Error Coach Kit
- [ ] Prompt 2 — [pending prompt text]
- [ ] Prompt 3 — [pending prompt text]
- [ ] Prompt 4 — [pending prompt text]
- [ ] Prompt 5 — [pending prompt text]
- [ ] Prompt 6 — [pending prompt text]
- [ ] Prompt 7 — [pending prompt text]
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