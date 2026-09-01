# OL Maturity Installments — Administrator Guide

This guide is for ZIC operators and administrators who create, process, and
maintain Ordinary Life maturity installment plans. It covers the lifecycle,
the daily batch, permissions, seeded scenarios, and operational guardrails.

## 1. Overview

A maturity installment plan spreads a policy's maturity payout over a chosen
term (for example ten annual installments). The plan is generated from the
product's installment rate table, so the total of all installments always equals
the maturity value. A plan may be created either against the matured policy
directly or against an approved maturity claim (in which case the claim's net
payout is the maturity value).

## 2. Lifecycle

```
CREATED → (first confirmed payment) → ACTIVE → (all installments paid) → COMPLETED
   │                                     │
   └── (cancelled before full payment) ──┴→ CANCELLED  (remaining items WAIVED)
```

| Status | Meaning |
|--------|---------|
| `CREATED` | Plan generated; all installments scheduled. |
| `ACTIVE` | At least one installment confirmed paid; plan is running. |
| `COMPLETED` | Every installment paid; nothing left to disburse. |
| `CANCELLED` | Closed by an administrator; remaining payable installments waived. |
| `TERMINATED` | Reserved for future termination flows. |

Each installment item moves through `SCHEDULED → PAYMENT_PENDING → PAID`, with
`MISSED` (flagged by the daily batch) and `WAIVED` (on cancellation) as the
exception states.

## 3. Daily operations

### Create a plan

1. Open a policy in `MATURED` (or `MATURED_PENDING_PAYMENT`) status.
2. Optionally select an approved maturity claim to back the plan.
3. Choose a frequency and term from the options endpoints — they reflect what
   the product's rate table actually supports.
4. Submit. A plan number is generated and every installment is scheduled.

Creation is idempotent: the caller's `X-Idempotency-Key` guarantees a duplicate
submission returns the original plan.

### Process and confirm a payment

1. **Process** an installment to raise a Front Office disbursement requisition
   against the policyholder's verified primary bank account. The item moves to
   `PAYMENT_PENDING`. Processing is only allowed once the installment is due.
2. **Confirm** the disbursement to mark the item `PAID` with a paid date and
   complete the requisition.

The first confirmation activates the plan. When the last installment is
confirmed, the plan completes automatically and a completion event fires.

### Detect missed installments (daily batch)

Run the missed-detection command to flag overdue installments and notify
policyholders:

```
python manage.py detect_missed_installments --as-of 2026-09-01 --correlation-id ops-2026-09-01
```

The batch moves `SCHEDULED`/`PAYMENT_PENDING` items past their due date to
`MISSED`, emits a notification, and is safe to re-run (it only touches items
that are still payable).

### Reverse a payment

A paid installment can be reversed within the configured window
(`INSTALLMENT_REVERSAL_WINDOW_DAYS`, default 7). The Front Office requisition is
marked `REVERSED`, the payment reference is cleared, and the item returns to
`SCHEDULED` (or `MISSED` once past due). Reversal requires a reason and cannot
apply to an item that is not currently `PAID`.

### Cancel a plan

Cancellation requires a reason and is only allowed for `CREATED`/`ACTIVE` plans
that are not fully paid. On cancellation the plan is `CANCELLED` and remaining
payable installments are `WAIVED`; still-pending requisitions are cancelled.
If the `INSTALLMENT_PAYMENT_IRREVOCABLE` parameter is enabled, any plan with a
paid installment is protected from cancellation.

## 4. Reconciliation and audit

Every financial state change is audited with actor, before/after values, reason,
and source channel. Two verification tools support the finance function:

- **Plan reconciliation** (`GET .../{plan_id}/reconciliation/`) checks that the
  total paid equals the total payable; it reports `PASS`/`FAIL` with structured
  discrepancies (`PLAN_TOTAL_MISMATCH`, `MISSING_PAYMENTS`, `OVER_PAYMENT`).
- **Audit consistency** verifies that each plan status reached and each
  non-scheduled item status has a matching audit row, so the trail can be
  trusted end to end.

## 5. Permissions

| Role | Capabilities |
|------|--------------|
| `OL_MATURITY_INSTALLMENTS_VIEWER` | Read-only: list, detail, KPIs, export, reconciliation, portal. |
| `OL_MATURITY_INSTALLMENTS_HANDLER` | Viewer capabilities plus create, process/confirm/reverse payments, and print. |
| `OL_MATURITY_INSTALLMENTS_ADMINISTRATOR` | All capabilities including plan cancellation. |

Assign users to these groups via the user-management module. Superusers bypass
the checks.

## 6. Seeded scenarios

The command below populates realistic data across every lifecycle state, plus
captured failure proofs:

```
python manage.py seed_ol_maturity_installment_scenarios
```

It seeds exactly eight plans:

1. **Standard active plan** — one installment paid, one missed, the rest
   scheduled.
2. **Fully completed plan** — all ten annual installments paid.
3. **All payments missed** — every installment flagged missed by the batch.
4. **Cancelled by admin** — plan cancelled; installments waived.
5. **Reversed payment** — an installment paid and then reversed.
6. **Multi-currency plan** — a USD-denominated plan.
7. **Claim-linked plan** — backed by an approved maturity claim (claim moved to
   `PAID_VIA_INSTALLMENTS` on activation).
8. **Policy-only plan** — created from a matured policy with no claim; still
   `CREATED`.

The same command then attempts four failure scenarios and prints proof payloads:
creating for an immature policy, processing an already-paid item, reversing
outside the reversal window, and a duplicate idempotent creation. It is safe to
re-run — stable keys and numbers make it idempotent.

## 7. Documents

Print a maturity schedule or a payment advice through the document engine. Plans
that are cancelled print with a `CANCELLED` watermark; plans with a missed
installment print with a `MISSED PAYMENT` watermark (cancellation wins).

## 8. Operational guardrails

- Verify a policyholder's bank account (primary + verified) before processing a
  disbursement, or processing fails with `INSTALLMENT_BANK_DETAILS_MISSING`.
- Never cancel a fully paid plan; the system blocks it.
- Confirm the product's installment rate table covers the requested term before
  creating a plan, or creation fails with `PLAN_PARAMETER_MISSING`.
