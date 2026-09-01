# OL Maturity Installments — Calculation Logic

The maturity installments engine converts a matured OL policy's maturity value
into a schedule of installment payouts, driven entirely by OL Product Rating
parameters. No amount is hard-coded: every factor comes from the
Anticipated Endowment installment rate table
(`OLAnticipatedEndowmentInstallmentRate`), and the schedule is guaranteed to
reconcile to the maturity value to the penny.

## 1. Inputs

| Input          | Source                                                     |
|----------------|------------------------------------------------------------|
| Maturity value | Claim `netPayout` when a settled claim is linked, else the policy `sumAssured` |
| Frequency      | `SINGLE`, `MONTHLY`, `QUARTERLY`, `HALF_YEARLY`, `ANNUAL`   |
| Term           | Whole number of years (1–60)                               |
| Rate row       | Most specific active/effective `OLAnticipatedEndowmentInstallmentRate` for the policy |

## 2. Rate resolution

The engine scores every active rate row for the policy's product and plan:

- **+4** for an exact product **and** plan match (product-only rows score lower).
- **+2** for explicit term coverage (`termFrom`–`termTo`) that contains the
  requested term; unconstrained rows score **+1**.
- The row with the highest score is used; ties break toward the latest
  `effectiveFrom`.

A row must be active and effective on the plan date (`effectiveFrom <= date`
and, if set, `effectiveTo >= date`), must match the requested frequency, and — when
the policy has a currency — must have either a blank currency or the policy's
currency. If no row applies, creation fails with `PLAN_PARAMETER_MISSING`.

## 3. Installment count and amount

```
installments = term_years * 12 / months_per_frequency   (min 1)
base_amount  = maturity_value * (rate_factor / 100)
```

`rateFactor` is a decimal rate such that the installment equals
`Maturity Value * (Rate / 100)` — e.g. a `10.00000000` annual rate on a
25,000,000.00 maturity value yields ten installments of 2,500,000.00.

## 4. Penny rounding (largest remainder)

Each installment is first quantized to two decimals. Any remainder between the
sum of the rounded installments and the exact maturity value is then spread one
penny at a time across the installments ordered by largest fractional remainder.
This guarantees:

```
sum(installment amounts) == total payable amount == maturity value
```

If rounding cannot make the schedule reconcile (impossible for well-formed
rates but guarded regardless), the engine raises
`PLAN_CALCULATION_MISMATCH`.

## 5. Due dates

Installments are due every `months_between(frequency)` starting from the plan
start date:

```
due_date(n) = start_date + (n - 1) * frequency months
```

The start date defaults to the creation date and is never earlier than the
policy maturity date. Month arithmetic clamps to the last day of the target
month (31 Jan + 1 month → 28/29 Feb).

## 6. Reconciliation invariant

A plan's `totalPayableAmount` always equals its `totalMaturityValue`. At any
point the paid total can be checked against `totalPayableAmount` via
`validate_plan_reconciliation`:

- **PASS** when `paid_amount == total_payable_amount` (within 0.01 tolerance)
  and no discrepancies exist.
- **FAIL** with structured codes when the total does not match
  (`PLAN_TOTAL_MISMATCH`), installments are unpaid (`MISSING_PAYMENTS`), or the
  paid total exceeds the payable (`OVER_PAYMENT`).

## 7. Lifecycle and financial state changes

Every financial state change is audited with actor, before/after, reason, and
source channel.

```
CREATED ──first confirmed payment──▶ ACTIVE ──all installments paid──▶ COMPLETED
   │                                      │
   │ cancel (unpaid)                      │ cancel (not fully paid)
   ▼                                      ▼
CANCELLED (remaining items WAIVED)   CANCELLED (remaining items WAIVED)
```

- **Create** — plan `CREATED`, items `SCHEDULED`; emits `InstallmentPlanCreated`;
  audit `CREATE`.
- **Process** — item `SCHEDULED/MISSED` → `PAYMENT_PENDING`; Front Office
  requisition raised; emits `InstallmentPaymentDue`; audit
  `INSTALLMENT_PAYMENT_PROCESSED`.
- **Confirm** — item → `PAID`; first payment activates the plan
  (`INSTALLMENT_PLAN_ACTIVATED`) and marks a linked claim
  `PAID_VIA_INSTALLMENTS`; final payment completes the plan
  (`INSTALLMENT_PLAN_COMPLETED`); audits `INSTALLMENT_PAYMENT_CONFIRMED`.
- **Missed** — daily batch moves past-due `SCHEDULED`/`PAYMENT_PENDING` items to
  `MISSED`; emits `InstallmentPaymentMissed`.
- **Reverse** — `PAID` → `SCHEDULED` (or `MISSED` when past due) within the
  reversal window; audit `INSTALLMENT_PAYMENT_REVERSED`.
- **Cancel** — plan → `CANCELLED`, payable items `WAIVED`; audits
  `INSTALLMENT_PLAN_CANCELLED` plus `INSTALLMENT_ITEM_WAIVED` per item.

## 8. Audit consistency

`validate_audit_consistency` verifies that every plan status reached and every
non-`SCHEDULED` item status is backed by a matching audit row. A completed plan
therefore carries a plan-level `INSTALLMENT_PLAN_COMPLETED` row with
`afterState.status == "COMPLETED"`, mirroring how activation writes
`INSTALLMENT_PLAN_ACTIVATED` with `afterState.status == "ACTIVE"`.

## 9. Parameters

| Parameter                            | Purpose                                        | Default |
|--------------------------------------|------------------------------------------------|---------|
| `INSTALLMENT_REVERSAL_WINDOW_DAYS`   | Days a paid installment may be reversed        | 7       |
| `INSTALLMENT_PAYMENT_IRREVOCABLE`    | Block cancellation once any installment is paid | false  |
| `INSTALLMENT_ALLOW_POLICY_ACTION_WITH_ACTIVE_PLAN` | Permit policy surrender/cancel with an active plan | false |
