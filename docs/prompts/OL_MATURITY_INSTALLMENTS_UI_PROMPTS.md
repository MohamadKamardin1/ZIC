# OL MATURITY INSTALLMENTS UI — PROMPT SERIES (10 prompts)

- [x] Prompt 1 — Save Prompt Series + Maturity Installments UI Foundation and Contract-First API Layer

> **Note on fidelity:** only Prompt 1 was included in the pasted series message for
> this session. Prompts 2–10 will be appended `EXACTLY as provided` when the user
> supplies them, then executed strictly one at a time, ticking each checkbox after
> its commit and push. Prompt 1 below is saved verbatim.

---

## Prompt 1/10 — Save Prompt Series + Maturity Installments UI Foundation and Contract-First API Layer

```text
You are a senior frontend engineer for the ZIC Life Insurance Platform. The OL Maturity Installments backend is complete. Build the Maturity Installments UI. The user pasted the FULL 10-prompt series at once.

META-INSTRUCTION (HIGHEST PRIORITY):
1. Before coding, create docs/prompts/OL_MATURITY_INSTALLMENTS_UI_PROMPTS.md and save ALL 10 prompts EXACTLY as provided, each with a checkbox "[ ] Prompt N — title".
2. Commit and push that file immediately.
3. Execute ONLY Prompt 1 now; when green, tick its checkbox, commit, then proceed to Prompt 2. Never merge or skip prompts.

MANDATORY RULES:
- Use the established design system, DataTable, SmartSelect, ErrorCoach, StatusBadge, and MoneyCell kits.
- Names never UUIDs; every failure teaches the user what happened and how to resolve it.
- Financial data must be displayed with high precision (2 decimal places, currency formatted).
- Commit and push at the end of each prompt.

SCOPE:
1. Register route Ordinary Life > Maturity Installments gated by `ol_maturity_installments.view`.
2. Implement API hooks (TanStack Query) for the full Installment contract:
   - list, kpis, options
   - create_plan, detail (with schedule items)
   - process_payment, confirm_payment, reverse_payment
   - print_schedule, print_statement
   - portal_views (read-only)
3. Build Installment-specific primitives:
   - PlanStatusBadge (colors for CREATED, ACTIVE, COMPLETED, TERMINATED).
   - ItemStatusBadge (SCHEDULED, PAYMENT_PENDING, PAID, MISSED).
   - MoneyCell (formats amounts with currency and locale).
   - ProgressCell (visual bar showing Total Paid vs Total Maturity Value).
4. Implement MSW mock handlers mirroring the backend contract.
5. Unit tests for primitives rendering.

GIT:
- commit: "feat(web): maturity-installments UI foundation and contract-first API layer"
- push; if blocked create feature/web-maturity-installments-foundation and push; tick checkbox

FINAL OUTPUT: hooks, primitives, tests, commit hash, pushed branch.
```
