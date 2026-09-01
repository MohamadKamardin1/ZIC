# OL MATURITY INSTALLMENTS UI — PROMPT SERIES (10 prompts)

- [x] Prompt 1 — Save Prompt Series + Maturity Installments UI Foundation and Contract-First API Layer
- [x] Prompt 2 — Maturity Installments List Page and Dashboard KPIs
- [ ] Prompt 3 — Maturity Installments Detail Header and Overview

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

---

## Prompt 2/10 — Maturity Installments List Page and Dashboard KPIs

```text
You are a senior frontend engineer. Continue the Z maturity Installments UI. Execute ONLY Prompt 2 from the saved series file.

MANDATORY RULES:
- Table-first; actions gated by allowed actions + permissions.
- Commit and push; tick checkbox.

SCOPE:
1. Dashboard KPIs:
   - Total Active Plans.
   - Total Value of Active Plans.
   - Upcoming Payments (Next 30 Days).
   - Missed Payments Count.
2. Installment Plans DataTable:
   - Columns: Plan Number, Policy Number (clickable), Policyholder Name, Total Maturity Value, Total Paid, Remaining Balance, Frequency, Status Badge, Start Date, Allowed Actions.
   - Filters: Status, Product, Branch, Frequency, Date Range.
   - Search: Plan Number, Policy Number, Policyholder Name.
3. Row Actions: View, Process Payment (bulk), Print Schedule, Cancel.
4. Buttons: "Generate Plan" (if manual trigger allowed), Export CSV.
5. States: Skeleton, Empty, ErrorCoach.

TESTS:
- KPI display and math
- action visibility (e.g., no "Process Payment" button for COMPLETED plan)
- filters and search work
- no UUID leaks in table

GIT:
- commit: "feat(web): maturity-installments list page and dashboard KPIs"
- push; tick checkbox

FINAL OUTPUT: page behavior, tests, commit hash, pushed branch.
```

---

## Prompt 3/10 — Maturity Installments Detail Header and Overview

```text
You are a senior frontend engineer. Continue the Z maturity Installments UI. Execute ONLY Prompt 3.

MANDATORY RULES:
- Master-Detail pattern; clear visibility of the financial schedule.
- Commit and push; tick checkbox.

SCOPE:
1. Header:
   - Plan Number (Copyable), Status Badge.
   - Policy Link (Policy Number + Product).
   - Policyholder Name.
   - Financial Cards: Total Maturity Value, Amount Paid, Balance Remaining.
   - Dates: Start Date, End Date.
   - Action Bar: Process Payment, Print, Cancel (gated by status).
2. Tabs: Overview, Schedule, Payments, Audit, Documents.
3. Overview Tab:
   - Plan Context: Frequency (e.g., Monthly), Number of Installments, Calculation Source (Rate Table/Claim).
   - Policy Details Snippet.
   - Status Timeline.
4. Visual Indicators:
   - If "TERMINATED": Red banner with reason.
   - If "COMPLETED": Green success banner.

TESTS:
- header renders all key financial fields
- action buttons visibility based on status
- policy link navigates correctly
- no UUIDs

GIT:
- commit: "feat(web): maturity-installments detail header and overview"
- push; tick checkbox

FINAL OUTPUT: page structure, tests, commit hash, pushed branch.
```
