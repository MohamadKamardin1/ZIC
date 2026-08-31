# OL MATURITY INSTALLMENTS BACKEND — PROMPT SERIES (12 prompts)

- [x] Prompt 1 — Save Prompt Series + OL Maturity Installments Domain Foundation

> **Note on fidelity:** only Prompt 1 was included in the pasted series message for
> this session. Prompts 2–12 will be appended `EXACTLY as provided` when the user
> supplies them, then executed strictly one at a time, ticking each checkbox after
> its commit and push. Prompt 1 below is saved verbatim.

---

## Prompt 1/12 — Save Prompt Series + OL Maturity Installments Domain Foundation

```text
You are a senior Django insurance platform engineer. Build the ZIC Ordinary Life Maturity Installments backend. The user pasted the FULL 12-prompt series at once.

META-INSTRUCTION (HIGHEST PRIORITY):
1. Before coding, create docs/prompts/OL_MATURITY_INSTALLMENTS_BACKEND_PROMPTS.md and save ALL 12 prompts EXACTLY as provided, each with a checkbox "[ ] Prompt N — title".
2. Commit and push that file immediately.
3. Execute ONLY Prompt 1 now; when green, tick its checkbox, commit, then proceed to Prompt 2. Never merge or skip prompts.

MANDATORY RULES:
- No blocking questions; make senior insurance/finance assumptions and document them.
- Everything must be parameterized via existing OL Policy Setup and Product Rating parameters (specifically Installment Rates and Paid-Up Rates).
- Every financial state change must be audited with actor, before/after, reason, source channel.
- All user-facing errors must use the structured Error Coach shape with resolution steps.
- Commit and push at the end of each prompt.

OBJECTIVE:
Create the OL Maturity Installments bounded context and core domain foundation.

BUSINESS CONTEXT:
When a policy matures, the policyholder may choose to receive the maturity benefit as a lump sum or as installments (annuity). This module manages the Installment Plan (the schedule) and the individual Installment Items (payments). It ensures the total payouts match the Maturity Value and integrates with the Front Office for disbursement.

SCOPE:
1. Produce docs/OL_MATURITY_INSTALLMENTS_DESIGN.md defining:
   - Installment Plan lifecycle: CREATED -> ACTIVE -> COMPLETED | TERMINATED
   - Installment Item lifecycle: SCHEDULED -> PAYMENT_PENDING -> PAID | MISSED | WAIVED
   - Integration map: Policies (trigger), Maturity Claims (source of value), Front Office (disbursement), Notifications.
2. Create Django app `ol_maturity_installments`.
3. Implement core models:
   - OLMaturityInstallmentPlan: plan_number unique, policy_ref, maturity_claim_ref optional, partner, currency, total_maturity_value, total_payable_amount, installment_count, frequency, start_date, end_date, status, audit fields.
   - OLInstallmentItem: plan_ref, installment_number, due_date, amount, status, payment_requisition_ref optional, paid_date, narration, audit fields.
   - OLMaturityInstallmentConfig: (optional) to store snapshot of the calculation basis used.
4. Register permissions: ol_maturity_installments.view, create, process_payment, cancel, print, configure.
5. Register domain events: InstallmentPlanCreated, InstallmentPaymentDue, InstallmentPaymentMissed, InstallmentPlanCompleted.
6. Add structured error registry: PLAN_POLICY_NOT_MATURED, PLAN_CALCULATION_MISMATCH, INSTALLMENT_ALREADY_PAID, INSTALLMENT_PAYOUT_FAILED, PLAN_PARAMETER_MISSING.
7. Add base API skeleton: list, retrieve.
8. Add admin table-first registration.

TESTS:
- model creation and relationships
- status enum validation
- error shape contract
- permissions registered

GIT:
- commit: "feat(ol-maturity-installments): save prompt series and create domain foundation"
- push; if blocked create feature/ol-maturity-installments-foundation and push; tick checkbox

FINAL OUTPUT: design summary, models, permissions, events, error codes, tests, commit hash, pushed branch.
```
