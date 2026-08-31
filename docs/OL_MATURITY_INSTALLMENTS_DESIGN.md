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

Installment Plan: `CREATED -> ACTIVE -> COMPLETED | TERMINATED`

Installment Item: `SCHEDULED -> PAYMENT_PENDING -> PAID | MISSED | WAIVED`

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

## Options endpoints

- `GET /api/v1/ol/maturity-installments/options/frequencies/` — the five
  maturity payout frequencies with `months_between` and `payout_per_year`.
- `GET /api/v1/ol/maturity-installments/options/terms/` — term years found in
  the active installment rate table (falls back to 1–30 when no table is
  seeded), optionally scoped with `?product=<code>`. Search via `?q=...`,
  pagination via `page`/`page_size`.

## Assumptions (senior finance decisions, documented)

- A matured policyholder may choose any maturity payout frequency; the premium
  payment frequency is advisory, and the schedule reports
  `frequency_matches_policy` for visibility rather than restricting choice.
- The rate table is the single source of truth; no hard-coded percentages exist
  in the engine. A missing table is an operator error surfaced as
  `PLAN_PARAMETER_MISSING`, never silently zero.
- Rounding follows largest-remainder (the last item absorbs any residual penny)
  so the item total equals the maturity value to the cent.

## Error codes

`PLAN_POLICY_NOT_MATURED`, `PLAN_CALCULATION_MISMATCH`,
`INSTALLMENT_ALREADY_PAID`, `INSTALLMENT_PAYOUT_FAILED`,
`PLAN_PARAMETER_MISSING` (Prompt 1), plus supporting codes
`INSTALLMENT_PLAN_NOT_FOUND`, `INSTALLMENT_ITEM_NOT_FOUND`,
`INSTALLMENT_PLAN_INVALID_STATUS`, `INSTALLMENT_ITEM_INVALID_STATUS`,
`INSTALLMENT_INVALID_FILTER`, `INSTALLMENT_INVALID_FREQUENCY`,
`INSTALLMENT_INVALID_TERM`, `INSTALLMENT_INVALID_AMOUNT`. All render through
the global structured Error Coach handler with resolution steps and `doc_ref`
pointing here.
