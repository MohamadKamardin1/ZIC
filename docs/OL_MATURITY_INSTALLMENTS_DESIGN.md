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
