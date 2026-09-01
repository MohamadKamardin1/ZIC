# OL MATURITY INSTALLMENTS BACKEND — PROMPT SERIES (12 prompts)

- [x] Prompt 1 — Save Prompt Series + OL Maturity Installments Domain Foundation
- [x] Prompt 2 — Implement Parameter Validation & Calculation Engine
- [x] Prompt 3 — Implement Plan Generation and Creation
- [x] Prompt 4 — Implement Payment Processing and Integration
- [ ] Prompt 5 — Implement Missed Detection and Reversal Lifecycle

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

---

## Prompt 2/12 — Implement Parameter Validation & Calculation Engine

```text
You are a senior Django finance configuration engineer. Continue the ZIC OL Maturity Installments backend. Execute ONLY Prompt 2 from the saved series file.

MANDATORY RULES:
- Calculation must be driven by OL Parameters (Installment Rate Tables).
- Commit and push; tick checkbox.

OBJECTIVE:
Implement parameter consumption and the calculation engine for installment schedules.

SCOPE:
1. Implement Installment Calculation Service:
   - generate_schedule(policy, maturity_value, frequency, term_years):
     - Validates policy maturity (Maturity Date <= Today).
     - Fetches relevant Installment Rate Table from OL Product Rating parameters based on Product/Plan/Frequency/Term.
     - If no table found, falls back to default parameters or returns PLAN_PARAMETER_MISSING.
     - Calculates each installment amount: Amount = Maturity Value * (Rate / 100).
     - Handles rounding differences (distribute penny rounding across installments to ensure Total Payable = Maturity Value).
     - Returns list of dicts (date, amount).
2. Implement Options Endpoints:
   - GET /api/v1/ol/maturity-installments/options/frequencies/
   - GET /api/v1/ol/maturity-installments/options/terms/
3. Seed validation rules:
   - Total calculated installments must equal maturity value.
   - Frequency must match policy payment frequency or be a valid maturity option.
4. Audit all calculation runs for compliance.

TESTS:
- calculation service returns correct schedule
- rounding error handling (total matches)
- missing parameter returns teachable error
- options endpoints return labeled data

GIT:
- commit: "feat(ol-maturity-installments): implement parameter validation and calculation engine"
- push; tick checkbox

FINAL OUTPUT: calculation logic, options endpoints, tests, commit hash, pushed branch.
```

---

## Prompt 3/12 — Implement Plan Generation and Creation

```text
You are a senior Django insurance engineer. Continue the ZIC OL Maturity Installments backend. Execute ONLY Prompt 3.

MANDATORY RULES:
- Generation must be idempotent.
- Must integrate with Policy Maturity status and Maturity Claims.
- Commit and push; tick checkbox.

OBJECTIVE:
Implement the creation of Installment Plans triggered by Policy Maturity or Maturity Claim Settlement.

SCOPE:
1. POST /api/v1/ol/maturity-installments/create/
   - Payload: policy_id, maturity_claim_id (optional), frequency, term_years.
   - Idempotency Key: X-Idempotency-Key.
2. Processing Steps:
   - Validate Policy is Matured or Maturity Claim is Settled.
   - Run Calculation Service to get schedule.
   - Create OLMaturityInstallmentPlan in status CREATED.
   - Create OLInstallmentItem records for each schedule row with status SCHEDULED.
   - Emit InstallmentPlanCreated event.
   - Audit creation with actor, inputs, totals.
3. Return structured error on failure (e.g., policy not matured).
4. Integration Seam:
   - If triggered by Maturity Claim, link the claim to the plan.
   - If standalone maturity, link only policy.

TESTS:
- successful creation generates plan and items
- policy not matured blocked with error
- idempotent duplicate returns same plan
- claim linkage works
- audit row created

GIT:
- commit: "feat(ol-maturity-installments): implement plan generation and creation"
- push; tick checkbox

FINAL OUTPUT: endpoint, validation logic, tests, commit hash, pushed branch.
```

---

## Prompt 4/12 — Implement Payment Processing and Integration

```text
You are a senior Django finance transaction engineer. Continue the ZIC OL Maturity Installments backend. Execute ONLY Prompt 4.

MANDATORY RULES:
- Payment must integrate with Front Office seam for disbursement.
- Status transitions must be audited.
- Commit and push; tick checkbox.

OBJECTIVE:
Implement installment payment processing and status updates.

SCOPE:
1. POST /api/v1/ol/maturity-installments/items/{id}/process-payment/
   - Permission: ol_maturity_installments.process_payment
   - Validation: Item status is SCHEDULED or PAYMENT_PENDING. Due date check.
   - Action:
     - Create Payment Requisition via Front Office seam (partner bank details).
     - Status -> PAYMENT_PENDING.
     - Emit InstallmentPaymentDue event.
   - Idempotent: repeated call returns existing requisition.
2. Callback/Confirmation Endpoint:
   - POST /api/v1/ol/maturity-installments/items/{id}/confirm-payment/
   - Updates status -> PAID, sets paid_date.
   - Checks if Plan is completed (all items paid). If so, Plan status -> COMPLETED.
   - Emits InstallmentPlanCompleted if applicable.
3. Audit payment processing with actor, requisition ref, paid date.

TESTS:
- process payment creates requisition and updates status
- confirmation completes item and potentially plan
- idempotent processing safe
- audit row complete

GIT:
- commit: "feat(ol-maturity-installments): implement payment processing and integration"
- push; tick checkbox

FINAL OUTPUT: processing endpoints, integration seam, tests, commit hash, pushed branch.
```

---

## Prompt 5/12 — Implement Missed Detection and Reversal Lifecycle

```text
You are a senior Django insurance lifecycle engineer. Continue the ZIC OL Maturity Installments backend. Execute ONLY Prompt 5.

MANDATORY RULES:
- Missed payments must be detected and flagged.
- Reversal must be atomic.
- Commit and push; tick checkbox.

OBJECTIVE:
Implement lifecycle management for missed payments and reversals.

SCOPE:
1. Management Command: detect_missed_installments
   - Runs daily.
   - Checks items where due_date < today and status is SCHEDULED/PAYMENT_PENDING.
   - Updates status -> MISSED.
   - Emits InstallmentPaymentMissed.
   - Idempotent.
2. Reversal Endpoint:
   - POST /api/v1/ol/maturity-installments/items/{id}/reverse-payment/
   - Allowed only for PAID items within configured window.
   - Action:
     - Reverse payment requisition via Front Office seam.
     - Status -> SCHEDULED (or MISSED if due date passed).
     - Audit reversal with actor, reason.
3. Cancellation:
   - Cancel entire plan (if not fully paid). Requires Admin permission.
   - Status -> CANCELLED.
4. Validation:
   - Cannot reverse if already reversed.
   - Cannot cancel if payments are irrevocable per parameters.

TESTS:
- missed detection command updates status
- reversal restores status and reverses payment
- cancellation works for active plans
- audit records created

GIT:
- commit: "feat(ol-maturity-installments): implement missed detection and reversal lifecycle"
- push; tick checkbox

FINAL OUTPUT: missed command, reversal endpoint, tests, commit hash, pushed branch.
```
