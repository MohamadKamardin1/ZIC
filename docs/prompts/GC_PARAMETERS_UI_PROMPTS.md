# GC PARAMETERS UI — PROMPT SERIES (10 prompts)

- [ ] Prompt 1 — Save Series File + GC Parameters UI Foundation & Contract-First API Layer

> **Note on fidelity:** only Prompt 1 was included in the pasted series message for
> this session. Prompts 2–10 will be appended `EXACTLY as provided` when the user
> supplies them, then executed strictly one at a time, ticking each checkbox after
> its commit and push. Prompt 1 below is saved verbatim.

---

## Prompt 1/10 — Save Series File + GC Parameters UI Foundation & Contract-First API Layer

```text
You are a senior frontend engineer for the ZIC Life Insurance Platform. The GC Parameters backend is complete. Build the GC Parameters UI. The user pasted the FULL 10-prompt series at once.

META-INSTRUCTION (HIGHEST PRIORITY):
1. Before coding, create docs/prompts/GC_PARAMETERS_UI_PROMPTS.md and save ALL 10 prompts EXACTLY as provided, each with a checkbox "[ ] Prompt N — title".
2. Commit and push that file immediately.
3. Execute ONLY Prompt 1 now; when green, tick its checkbox, commit, then proceed to Prompt 2. Never merge or skip prompts.

MANDATORY RULES:
- Use the established design system, DataTable, SmartSelect, ErrorCoach, StatusBadge, and ConfirmDialog kits.
- Names never UUIDs; every failure teaches the user what happened and how to resolve it.
- Commit and push at the end of each prompt.

SCOPE:
1. Register route Group Credit > Parameters gated by `gc_parameters.configure` or `gc_parameters.view`.
2. Implement API hooks (TanStack Query) for all GC Parameter entities:
   - scheme-types, scheme-rates, member-statuses, scheme-statuses, renewal-statuses
   - health-questions, health-questionnaires
   - sub-products, products
   - riders, rider-rates
   - medical-codes, medical-limits, underwriting-decisions, personal-habits, medical-history
   - medical-facilities, medical-practitioners
   - claim-types, claim-reasons, claim-statuses, discharge-types, correspondent-types
   - options endpoints for all SmartSelects
3. Build GC Parameter primitives:
   - ParameterSectionCard (groups related parameters visually)
   - EffectiveDateBadge (shows active/expired status)
   - RateTypeBadge (UNIT, FLAT, PERCENTAGE, FIXED)
   - MedicalCategoryBadge, ClaimCategoryBadge
4. Implement MSW mock handlers mirroring the backend contract.
5. Unit tests for primitives rendering.

GIT:
- commit: "feat(web): gc-parameters UI foundation and API layer"
- push; if blocked create feature/web-gc-parameters-foundation and push; tick checkbox

FINAL OUTPUT: hooks, primitives, tests, commit hash, pushed branch.
```
