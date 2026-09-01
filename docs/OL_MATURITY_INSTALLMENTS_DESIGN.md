# OL Maturity Installments — Design

Bounded context for converting a matured Ordinary Life policy benefit into a
lump sum or an installment (annuity) schedule. The module guarantees the total
payouts match the Maturity Value and integrates with the Front Office for
disbursement.

## Bounded context

- App: `apps.ol_maturity_installments`
- API prefix: `/api/v1/ol/maturity-installments/`
- Series: `docs/prompts/OL_MATURITY_INSTALLMENTS_BACKEND_PROMPTS.md`

## Lifecycles

Installment Plan: `CREATED -> ACTIVE -> COMPLETED | TERMINATED | CANCELLED`

Installment Item: `SCHEDULED -> PAYMENT_PENDING -> PAID | MISSED | WAIVED`, with
`PAID` reversible back to `SCHEDULED | MISSED` within the configured window.

## Integration map

| System | Role |
| --- | --- |
| OL Policies (`Policy`) | Trigger: a matured policy is the subject of the plan |
| Maturity Claims (`MaturityClaim`) | Source of value: `maturity_value` feeds the schedule |
| Front Office (`FORequisition`) | Disbursement channel for each paid installment |
| Notifications | Domain events via the durable `DomainEvent` outbox |

## Parameterization

Every calculation is driven by OL Policy Setup / Product Rating parameters:

- Installment Rates — `OLAnticipatedEndowmentInstallmentRate` (effective-dated
  rows keyed by product, optional plan, frequency, term, age and policy year).
- Paid-Up Rates — `OLPaidUpRate` (reserved for future conversion calculations).
- Charges — `OLInstallmentChargeRate` (reserved for future charge application).

The plan's `parameter_snapshot` and the one-to-one `OLMaturityInstallmentConfig`
preserve the exact basis used so later changes to rating parameters cannot
silently alter an issued schedule.

## Calculation engine (Prompt 2)

Public contract in `apps/ol_maturity_installments/services/calculation.py`:

```python
generate_schedule(policy, maturity_value, frequency, term_years) -> [{date, amount}, ...]
```

`calculate_schedule(...)` returns the richer result dict (totals, dates, exact
rate row, audit) and is the audit-writing entry point; `generate_schedule` is
the thin Prompt-2 contract wrapper.

### Resolution order

1. **Maturity validation** — `policy.maturity_date <= today`, else
   `PLAN_POLICY_NOT_MATURED`.
2. **Frequency validation** — must be a valid maturity option
   (`SINGLE | MONTHLY | QUARTERLY | HALF_YEARLY | ANNUAL`); aliases such as
   `ANNUALLY` are normalised. Else `INSTALLMENT_INVALID_FREQUENCY`.
3. **Term validation** — positive whole years (cap 60). Else
   `INSTALLMENT_INVALID_TERM`.
4. **Rate resolution** — the policy's product/plan is resolved by
   `product_plan_ref` (with `contract_snapshot` fallback codes) against the
   `OLProduct`/`OLPlan` catalogues, then the most specific active, effective
   `OLAnticipatedEndowmentInstallmentRate` row is chosen:
   - exact product + plan + term coverage scores highest;
   - a product-only row with term coverage is the default fallback;
   - an unconstrained (no term bounds) product row is the least-preferred
     fallback.
   If the product cannot be resolved, or no active row covers the
   product/frequency/term on the calculation date, the run fails with the
   teachable `PLAN_PARAMETER_MISSING`.
5. **Amount** — `Amount = Maturity Value * (Rate / 100)` per installment, where
   the rate is the table's `rate_factor` expressed as a percentage.
6. **Rounding** — each amount is quantised to the penny and the residual is
   distributed by largest remainder so `sum(items) == maturity_value`. If the
   table rate cannot reconcile (residual larger than one penny per item) the
   run fails with `PLAN_CALCULATION_MISMATCH`.
7. **Audit** — every run writes an `AuditService` record
   (`action=CALCULATE`, actor, before/after, reason, source channel) so
   calculation runs are fully traceable for compliance.

### Schedule geometry

- Installment count = `1` for `SINGLE`; otherwise `term_years * 12 / months`
  per frequency (monthly=1, quarterly=3, half-yearly=6, annual=12).
- Due dates start on `start_date` (defaults to the calculation date, never
  before `maturity_date`) and advance by the frequency's month step, clamping
  to month end for short months (e.g. 31 Jan -> 28 Feb).

## Plan generation and creation (Prompt 3)

`POST /api/v1/ol/maturity-installments/create/` generates a schedule and
persists a plan.

Payload: `policy_id` (UUID), `maturity_claim_id` (optional UUID), `frequency`,
`term_years`. Idempotency is enforced via the `X-Idempotency-Key` header.

Processing:

1. **Idempotency** — the key is required (`INSTALLMENT_IDEMPOTENCY_REQUIRED`);
   a replay of the identical request returns the original plan (200) instead of
   creating a duplicate, and reusing the key with a different payload raises
   `INSTALLMENT_IDEMPOTENCY_CONFLICT`. The fingerprint is the SHA-256 of the
   normalised payload (`policy_id`, `maturity_claim_id`, `frequency`,
   `term_years`).
2. **Policy and claim validation** — the policy must exist
   (`INSTALLMENT_POLICY_NOT_FOUND`); when a claim is supplied it must belong to
   the policy (`INSTALLMENT_CLAIM_MISMATCH`) and be settled — `APPROVED` or
   `PAID` (`INSTALLMENT_CLAIM_NOT_SETTLED`). A standalone plan (no claim) is
   allowed only for a `MATURED` or `MATURED_PENDING_PAYMENT` policy
   (`PLAN_POLICY_NOT_MATURED`).
3. **Value source** — the maturity value is the claim `net_payout` when a claim
   is linked, otherwise the policy `sum_assured`. This is the senior decision:
   a settled claim's approved net payout governs the schedule; a standalone
   maturity uses the sum assured as the default maturity benefit.
4. **Calculation** — the Prompt 2 engine produces the schedule and audits the
   run.
5. **Persistence** — `OLMaturityInstallmentPlan` is created in `CREATED`, the
   schedule rows become `OLInstallmentItem` records in `SCHEDULED`, and a
   one-to-one `OLMaturityInstallmentConfig` snapshots the calculation basis
   (`calculation_basis`, rate row, parameters, assumptions).
6. **Event** — `InstallmentPlanCreated` is emitted to the durable event outbox.
7. **Audit** — the creation is audited with actor, inputs, and totals via
   `AuditService`.

Integration seam: a request triggered by a Maturity Claim links the claim to
the plan (`maturity_claim_ref`); a standalone maturity links only the policy.

## Payment processing and integration (Prompt 4)

`POST /api/v1/ol/maturity-installments/items/{id}/process-payment/` raises a
Front Office disbursement requisition; the callback
`POST /api/v1/ol/maturity-installments/items/{id}/confirm-payment/` records the
payment. Both require the `process_payment` entitlement.

Processing:

1. **Validation** — the item must exist (`INSTALLMENT_ITEM_NOT_FOUND`), be
   `SCHEDULED` or `PAYMENT_PENDING`, and be due (its `due_date` is not in the
   future; `INSTALLMENT_PAYMENT_NOT_DUE` otherwise).
2. **Bank details** — the policyholder's primary verified bank account
   (`PartnerBankAccount`, falling back to primary → verified → first on file)
   is resolved; a policyholder with no bank account is blocked with
   `INSTALLMENT_BANK_DETAILS_MISSING`. The account snapshot is stored on the
   item in `payment_bank_details` (the legacy `FORequisition` has no bank
   field, so the domain record carries the disbursement instructions, matching
   the OL Claims pattern).
3. **Requisition** — a `FORequisition` (`department=MATURITY_INSTALLMENTS`,
   `status=PENDING`) is created and linked on the item. Processing is
   idempotent: replaying returns the existing requisition (200) instead of
   duplicating it.
4. **Status** — the item moves `SCHEDULED -> PAYMENT_PENDING`, the
   `InstallmentPaymentDue` event is emitted, and the transition is audited with
   actor, before/after, requisition ref, and source channel.

Confirmation:

1. **Paid** — the item moves `PAYMENT_PENDING -> PAID` with `paid_date` set
   (the callback date by default) and its requisition is marked `COMPLETED`.
   Reconfirmation of an already-paid item is a safe no-op.
2. **Plan completion** — when the last remaining item is paid, the plan moves
   to `COMPLETED` (`completed_at`/`completed_by` set) and the
   `InstallmentPlanCompleted` event is emitted.
3. **Audit** — confirmation is audited with actor, requisition ref, paid date,
   and before/after state.

## Missed detection, reversal, and cancellation (Prompt 5)

### Missed detection

`detect_missed_installments` is a daily management command
(`python manage.py detect_missed_installments [--as-of YYYY-MM-DD] [--plan-id]
[--correlation-id]`) that walks every `SCHEDULED`/`PAYMENT_PENDING` item whose
`due_date` is before the as-of date, moves it to `MISSED` (`missed_date` set),
emits `InstallmentPaymentMissed`, and audits the transition. It is idempotent —
only the two pre-missed statuses are candidates, so re-runs touch nothing — and
writes a batch-level audit row plus one per-item audit. A `MISSED` item remains
recoverable through `process-payment`.

### Reversal

`POST /api/v1/ol/maturity-installments/items/{id}/reverse-payment/` undoes a
paid installment (requires the `process_payment` entitlement and a `reason`).

1. **Validation** — the item must be `PAID` (`INSTALLMENT_REVERSAL_NOT_ALLOWED`
   otherwise, which also blocks reversing an already-reversed item because a
   reversed item is no longer paid), and the paid date must fall inside the
   configured window (`INSTALLMENT_REVERSAL_WINDOW_DAYS`, default 7; outside it
   raises `INSTALLMENT_REVERSAL_WINDOW_EXPIRED`).
2. **Front Office seam** — the linked requisition is marked `REVERSED`, and the
   item's requisition reference, paid date, payer, and payment reference are
   cleared so the installment can be disbursed again (a fresh requisition is
   raised on the next `process-payment`).
3. **Status** — the item returns to `SCHEDULED`, or `MISSED` when its due date
   has already passed.
4. **Audit** — the reversal is audited with actor, reason, requisition ref, and
   before/after state.

### Cancellation

`POST /api/v1/ol/maturity-installments/plans/{id}/cancel/` cancels an entire
plan. It requires the `cancel` entitlement — the module's admin-level
permission (superusers short-circuit) — and a `reason`.

1. **Eligibility** — only `CREATED`/`ACTIVE` plans can be cancelled
   (`INSTALLMENT_PLAN_CANNOT_CANCEL` for completed, terminated, or cancelled
   plans and for fully paid plans).
2. **Irrevocability** — a plan with paid installments is blocked when the
   `INSTALLMENT_PAYMENT_IRREVOCABLE` parameter (default false) is on
   (`INSTALLMENT_PLAN_IRREVOCABLE`).
3. **Effect** — the plan moves to `CANCELLED` (`cancelled_at`/`cancelled_by`
   set), every remaining payable item is waived (`WAIVED` + `waived_date`), and
   any still-pending disbursement requisitions are cancelled so nothing
   disburses after cancellation. Paid installments are left untouched.
4. **Audit** — the cancellation is audited with actor, reason, the waived
   installment numbers, and before/after state.

## Reconciliation and financial audit (Prompt 6)

### Reconciliation service

`validate_plan_reconciliation(plan_id, tolerance=0.01)` in
`services/reconciliation.py` verifies that the paid installments on a plan
reconcile to its maturity value. It sums every `PAID` item amount and compares
the result with the plan's `total_payable_amount` (which the schedule
guarantees equals the maturity value), then reports a pass/fail
`ReconciliationReport`:

- `PLAN_TOTAL_MISMATCH` — `total_payable_amount` differs from
  `total_maturity_value` beyond tolerance.
- `MISSING_PAYMENTS` — paid installments fall short, listing the unpaid
  installment numbers.
- `OVER_PAYMENT` — paid installments exceed the plan total.
- The report carries `status` (`PASS`/`FAIL`), totals, paid/missing amounts,
  paid vs total item counts, and every discrepancy.
- Each run is itself audited (`INSTALLMENT_RECONCILIATION_RUN`) so the check is
  traceable end-to-end. The tolerance can be overridden per call
  (`?tolerance=...`) and defaults to 0.01 currency units.

Endpoint: `GET /api/v1/ol/maturity-installments/{id}/reconciliation/`
(`InstallmentPlanReconciliationView`, `view` entitlement) returns the report.

### Audit consistency utility

`validate_audit_consistency(plan_id=None)` verifies the audit trail is
end-to-end verifiable. For each plan it requires at least one audit row
(`PLAN_MISSING_AUDIT`) and that a non-`CREATED` current status is reflected in
some row's `after_state.status` (`PLAN_STATUS_NOT_AUDITED`); for each item it
requires that any non-initial status (beyond `SCHEDULED`) is backed by an
item-level audit row (`ITEM_STATUS_NOT_AUDITED`). Orphan items — an item with a
missing or dangling `plan_ref` — are flagged (`ORPHAN_ITEM`). The report is
pass/fail with per-finding detail.

To keep this check honest, plan cancellation now audits each waived installment
individually (`INSTALLMENT_ITEM_WAIVED`); previously only the plan-level
cancellation was audited, so a `WAIVED` item had no matching audit row.

## List, detail, KPI and export APIs (Prompt 7)

The register, dashboard, and export are served at the canonical prefix:

- `GET /api/v1/ol/maturity-installments/` — paginated list. Table columns:
  `plan_number`, `policy_number`, `policyholder_name`, `total_amount`,
  `paid_amount`, `balance`, `status`, `start_date`, `allowed_actions` (plus the
  richer legacy fields). Filters: `status`, `product`
  (`policy_ref__product_plan_ref`), `branch` (the policy quotation's
  location/location-master/branch chain), `date_from`/`date_to` (on
  `start_date`), and `missed_only` (plans carrying at least one `MISSED`
  installment). Search (`q`/`search`) matches `plan_number`, `policy_number`,
  and `policyholder_name`. Sorting via `sort` over the whitelisted columns;
  pagination via `page`/`page_size` (max 100).
- `GET /api/v1/ol/maturity-installments/{id}/` — detail: header fields, nested
  `items`, `payment_history` (paid installments with requisition number,
  payment reference, paid date, payer), `audit_timeline`, and
  `allowed_actions` derived from status and the caller's entitlement.
- `GET /api/v1/ol/maturity-installments/kpis/` — real-time dashboard computed
  live from the filtered register (never stale/cached): `total_plans_active`
  (plans in `ACTIVE`), `total_upcoming_payouts` (payable installments —
  `SCHEDULED`/`PAYMENT_PENDING` — due today or later), `missed_payments_count`
  (`MISSED` installments), `completed_plans_count` (plans in `COMPLETED`).
  Returns `filters_applied` and a `timestamp` for auditability.
- `GET /api/v1/ol/maturity-installments/export/` — CSV download applying the
  same filters as the list (`Content-Disposition` attachment). Columns mirror
  the register: plan number, policy number, policyholder name, total amount,
  paid amount, balance, status, start/end date.
- Admin tables mirror the register columns: the plan admin now also shows
  `paid_amount` and `balance` alongside the existing plan, policy, policyholder,
  total, schedule, and status columns.

The legacy `installment-plans/` routes remain wired for backward compatibility.

## Documents and print engine (Prompt 8)

Maturity installment documents are generated through the shared print engine
(`apps/documents/`), so every render reuses the authenticated print pipeline,
signed download ticket, and immutable `DocumentInstance` storage with the
source/template version retained. Two document types are registered:

- `OL_MATURITY_SCHEDULE` — the plan schedule. Template variables: `plan`
  (number, status, frequency, dates, installment count), `policyholder`,
  `policy`, `financial` (maturity value, total payable, paid, balance),
  `schedule` (a table of installments: number, due date, amount, status, paid
  date, payment reference), `schedule_summary`, and `signatures` (policyholder,
  agent, company representative).
- `OL_MATURITY_PAYMENT_ADVICE` — advises on the individual installment payments
  of a plan, reusing the same header and schedule blocks and adding
  advice-specific notes.

Print endpoints (both require the module `print` entitlement):

- `POST /api/v1/ol/maturity-installments/{id}/print-schedule/`
- `POST /api/v1/ol/maturity-installments/{id}/print-advice/`

Each call renders the active, approved template version, stores a
`DocumentInstance` with `template_version` and the source/template reference,
issues a short-lived signed download ticket, and returns the standard document
payload (`id`, `template_version`, `signed_download_url`, `preview_url`,
`page_count`, `checksum`, ...). A status watermark is applied when the plan is
`CANCELLED` (`CANCELLED`) or when any installment is `MISSED`
(`MISSED PAYMENT`), so an altered or lapsed plan is visibly flagged.

Generation (`DOCUMENT_GENERATED`), ticket issue (`DOCUMENT_TICKET_ISSUED`), and
download (`DOCUMENT_TICKET_DOWNLOADED`) are all audited with actor,
before/after state, reason, and source channel through the shared engine.

### Print assumptions (senior document decisions)

- A `CANCELLED` plan and a plan carrying a `MISSED` installment are both
  watermarked; `CANCELLED` takes precedence over `MISSED PAYMENT`.
- The Maturity Schedule lists every installment with its live status and
  payment reference; the Payment Advice reuses the same schedule block and adds
  advice-specific notes. Both carry signature blocks and never render a UUID —
  plan, policy, and policyholder reference numbers are human-readable labels.

## Policy, claims, portal and notification integrations (Prompt 9)

### Integration map

- **Policies → Maturity Installments (guard):** a policy carrying a
  non-terminal installment plan (`CREATED` or `ACTIVE`) cannot be surrendered
  or cancelled, unless the System Parameter
  `INSTALLMENT_ALLOW_POLICY_ACTION_WITH_ACTIVE_PLAN` (default `false`)
  explicitly permits it. The guard lives in
  `apps/ol_maturity_installments/services/integration_service.py`
  (`installment_plan_policy_action_guard`) and is invoked from the OL Policies
  termination service through a deferred import, so neither context carries a
  hard import-time dependency on the other. Surrender raises
  `POLICY_SURRENDER_BLOCKED`; cancellation raises `POLICY_CANCELLATION_BLOCKED`;
  both return the blocking plan numbers and the parameter state in `details`.
- **Policies → Maturity Installments (payload):** the policy detail payload
  exposes `maturity_installment_plan_summary` (count by status, active
  outstanding amount, and one row per plan with number, status, totals, paid,
  balance, dates, next due date, and linked claim number), mirroring the
  existing `ol_loan_summary` block.
- **Maturity Claims → Maturity Installments:** a plan created against a settled
  maturity claim links the claim (`maturity_claim_ref`). When the plan starts —
  the first installment is confirmed as paid and the plan moves
  `CREATED -> ACTIVE` — the linked claim is advanced to
  `PAID_VIA_INSTALLMENTS` ("Paid via Installments") and both transitions are
  audited (`INSTALLMENT_PLAN_ACTIVATED`, `MATURITY_CLAIM_PAID_VIA_INSTALLMENTS`).
- **Partner Portal → Maturity Installments:** read-only portal endpoints scoped
  to the caller's `visible_partners()`:
  - `GET /api/v1/ol/maturity-installments/portal/` — the partner's own plans.
  - `GET /api/v1/ol/maturity-installments/portal/{id}/` — one plan by number or
    UUID, including the installment schedule.
  Cross-partner lookups return a sanitized `PORTAL_RESOURCE_NOT_FOUND` with no
  internal detail; no internal actions are exposed.
- **Notifications:** the durable domain-event outbox drives policyholder
  alerts. A `post_save` receiver on `DomainEvent`
  (`apps/ol_maturity_installments/integration_receivers.py`) dispatches
  `InstallmentPaymentDue`, `InstallmentPaymentMissed`, and
  `InstallmentPlanCompleted` into the notification center: a
  `PolicyNotificationLog` row per SMS/email channel and a
  `DashboardNotification` per linked user. The shared external key
  (`installment:<plan>:<event>`) collapses duplicate dispatches, so an event is
  surfaced exactly once.

### Plan activation ("plan starts")

The plan lifecycle `CREATED -> ACTIVE -> COMPLETED | TERMINATED` is made real by
activating a plan when its first installment is confirmed as paid (the moment
the annuity begins disbursing). The first confirmation moves the plan to
`ACTIVE`, sets `activated_at`/`activated_by`, and — for a claim-backed plan —
marks the linked maturity claim `PAID_VIA_INSTALLMENTS`. A plan that reaches
`COMPLETED` on the same confirmation passes through `ACTIVE` first.

### Integration assumptions (senior decisions)

- "Active maturity plan" for the policy guard means any non-terminal plan
  (`CREATED` or `ACTIVE`): even a not-yet-started schedule is an arrangement to
  pay the maturity value over time, so a policy action that would orphan it is
  blocked unless an operator explicitly allows it via the parameter.
- The allowance parameter is boolean and defaults to `false`; when enabled the
  policy action proceeds and the plan is left to be resolved independently.
- A claim is only advanced to `PAID_VIA_INSTALLMENTS` from `APPROVED`/`PAID`;
  a claim already marked paid-via-installments is never re-touched, and a plan
  without a linked claim changes no claim state.
- Notifications are delivered through the existing OL notification center
  (`PolicyNotificationLog` + `DashboardNotification`) and deduplicated by
  external key, so retries and idempotent replays never double-notify.

## Options endpoints

- `GET /api/v1/ol/maturity-installments/options/frequencies/` — the five
  maturity payout frequencies with `months_between` and `payout_per_year`.
- `GET /api/v1/ol/maturity-installments/options/terms/` — term years found in
  the active installment rate table (falls back to 1–30 when no table is
  seeded), optionally scoped with `?product=<code>`. Search via `?q=...`,
  pagination via `page`/`page_size`.

## Assumptions (senior finance decisions, documented)

- A missed installment is recoverable: a `MISSED` item is still processable, so
  the daily detection batch flags the lapse without foreclosing collection.
- The reversal window is a System Parameter (`INSTALLMENT_REVERSAL_WINDOW_DAYS`,
  default 7); once the window closes a reversal must go through Finance
  Operations rather than the API.
- Reversal clears the item's requisition reference and payment markers so a
  corrected disbursement raises a fresh Front Office requisition; the history
  of the reversed requisition is preserved in the audit trail and on the
  requisition itself.
- "Admin permission" for cancellation maps to the module's `cancel` entitlement
  (superusers short-circuit), matching the OL Policies cancellation gate.
- Cancellation waives the remaining payable installments and cancels still
  pending requisitions, so no part of a cancelled plan can still disburse;
  already-paid installments are never reversed by cancellation.
- Irrevocability is an operator-controlled System Parameter
  (`INSTALLMENT_PAYMENT_IRREVOCABLE`, default false): when enabled, a plan with
  any paid installment cannot be cancelled through the API.
- Reconciliation compares the sum of PAID installments with the plan's total
  payable amount (the schedule's guarantee that items sum to the maturity
  value) within a 0.01 currency-unit tolerance; the plan-level
  `total_payable_amount` vs `total_maturity_value` check catches schedule-data
  drift. A shortfall is reported, not silently zeroed.
- Audit consistency treats `SCHEDULED` items and `CREATED` plans as initial
  states requiring no transition audit; any later status must have a matching
  audit row. Waiving an installment during cancellation is audited per item so
  the trail remains complete end-to-end.

- A matured policyholder may choose any maturity payout frequency; the premium
  payment frequency is advisory, and the schedule reports
  `frequency_matches_policy` for visibility rather than restricting choice.
- The rate table is the single source of truth; no hard-coded percentages exist
  in the engine. A missing table is an operator error surfaced as
  `PLAN_PARAMETER_MISSING`, never silently zero.
- Rounding follows largest-remainder (the last item absorbs any residual penny)
  so the item total equals the maturity value to the cent.
- The maturity value for a plan is the linked claim's `net_payout` when a
  settled claim is provided, otherwise the policy `sum_assured`. A standalone
  plan is restricted to matured policies so a benefit is never scheduled before
  it is due.
- Generation is idempotent: callers must send `X-Idempotency-Key`, and a replay
  returns the original plan untouched rather than creating a second schedule.
- Payment processing is idempotent at the item level: replaying
  `process-payment` returns the already-raised requisition instead of creating a
  second one, and reconfirming a paid installment is a safe no-op.
- An installment cannot be processed before its due date; the Front Office
  requisition is the single source of truth for the disbursement, and the
  policyholder's primary verified bank account on file drives the payment
  instructions.

## Error codes

`PLAN_POLICY_NOT_MATURED`, `PLAN_CALCULATION_MISMATCH`,
`INSTALLMENT_ALREADY_PAID`, `INSTALLMENT_PAYOUT_FAILED`,
`PLAN_PARAMETER_MISSING` (Prompt 1), plus supporting codes
`INSTALLMENT_PLAN_NOT_FOUND`, `INSTALLMENT_ITEM_NOT_FOUND`,
`INSTALLMENT_PLAN_INVALID_STATUS`, `INSTALLMENT_ITEM_INVALID_STATUS`,
`INSTALLMENT_INVALID_FILTER`, `INSTALLMENT_INVALID_FREQUENCY`,
`INSTALLMENT_INVALID_TERM`, `INSTALLMENT_INVALID_AMOUNT`, plus Prompt 3 codes
`INSTALLMENT_IDEMPOTENCY_REQUIRED`, `INSTALLMENT_IDEMPOTENCY_CONFLICT`,
`INSTALLMENT_POLICY_NOT_FOUND`, `INSTALLMENT_CLAIM_NOT_FOUND`,
`INSTALLMENT_CLAIM_MISMATCH`, `INSTALLMENT_CLAIM_NOT_SETTLED`,
`INSTALLMENT_INVALID_CREATION`, plus Prompt 4 codes
`INSTALLMENT_PAYMENT_NOT_DUE`, `INSTALLMENT_BANK_DETAILS_MISSING`, plus Prompt 5
codes `INSTALLMENT_REVERSAL_REASON_REQUIRED`,
`INSTALLMENT_REVERSAL_NOT_ALLOWED`, `INSTALLMENT_REVERSAL_WINDOW_EXPIRED`,
`INSTALLMENT_CANCELLATION_REASON_REQUIRED`, `INSTALLMENT_PLAN_CANNOT_CANCEL`,
`INSTALLMENT_PLAN_IRREVOCABLE`. All render through the global structured Error
Coach handler with resolution steps and `doc_ref` pointing here.
