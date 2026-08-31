# OL MATURITY INSTALLMENTS — DESIGN

Domain design for the ZIC Ordinary Life Maturity Installments bounded context.
Prompt 1 of the OL Maturity Installments backend series.

## 1. Business context

When a policy reaches its maturity date, the policyholder may elect to receive the
maturity benefit either as a single lump-sum payment or spread over a series of
installments (a form of annuity). This module owns the **Installment Plan** — the
approved schedule — and the individual **Installment Items** — the individual
payments that make it up.

The module guarantees a core financial invariant: **the total of all installment
payouts equals the Maturity Value made payable by the policy** (net of any agreed
loan deduction). Any divergence raises a structured `PLAN_CALCULATION_MISMATCH`
and blocks the plan from being activated.

## 2. Lifecycles

### 2.1 Installment Plan

```
CREATED -> ACTIVE -> COMPLETED
                \-> TERMINATED
```

| State       | Meaning |
|-------------|---------|
| `CREATED`   | The plan and its items have been generated from the maturity value. Not yet payable. |
| `ACTIVE`    | The schedule is live; items become payable on their due dates. |
| `COMPLETED` | Every installment has been settled; the plan is finished. |
| `TERMINATED`| The plan was stopped before completion (e.g. commuted to lump sum, policy correction, or repayment default) with the balance handled by the terminating action. |

### 2.2 Installment Item

```
SCHEDULED -> PAYMENT_PENDING -> PAID
                            \-> MISSED
                            \-> WAIVED
```

| State              | Meaning |
|--------------------|---------|
| `SCHEDULED`        | Item is on the calendar; not yet due. |
| `PAYMENT_PENDING`  | Item has reached its due date (or a grace period has lapsed) and awaits disbursement via Front Office. |
| `PAID`             | Front Office confirmed the disbursement for this item. Terminal. |
| `MISSED`           | The disbursement could not be completed at the expected window; it remains payable and is flagged for follow-up. |
| `WAIVED`           | The item was forgiven under an approved policy/product rule. Terminal. |

## 3. Integration map

| System                 | Role                                                          | Direction / seam |
|------------------------|---------------------------------------------------------------|------------------|
| **OL Policies**        | Trigger: a policy reaching `MATURED` (or `MATURED_PENDING_PAYMENT`) is eligible to carry an installment plan. Policy provides partner, currency, product/plan reference, and maturity date. | Read; the plan references `ol_policies.Policy` via `policy_ref`. |
| **Maturity Claims**    | Source of value: the approved maturity claim supplies `maturity_value`, `loan_deduction`, and `net_payout`. | Read; optional `maturity_claim_ref` to `ol_policies.MaturityClaim`. |
| **Front Office**       | Disbursement: each payable item raises/links a `FORequisition`; Front Office confirmation transitions the item to `PAID`. | Write seam via `payment_requisition_ref` to `front_office.FORequisition`. |
| **Notifications**      | Consumers listen for domain events (`InstallmentPlanCreated`, `InstallmentPaymentDue`, `InstallmentPaymentMissed`, `InstallmentPlanCompleted`) to drive SMS/e-mail and dashboard alerts. | Events published to the shared `DomainEvent` outbox. |
| **OL Parameters (Policy Setup / Product Rating)** | Calculation basis: installment schedule and charges are parameterized from Product Rating rate tables. | Read-only parameter consumption (see §4). |

## 4. Parameterization

All installment behavior is parameterized through the existing OL Policy Setup and
Product Rating parameter catalog in `apps.ol_parameters`:

| Parameter model             | Use in this module |
|-----------------------------|--------------------|
| `OLAnticipatedEndowmentInstallmentRate` | Supplies the **Installment Rate** (`rate_factor`) by product/plan/frequency/age/term/policy-year/currency used to derive the annuity schedule. |
| `OLPaidUpRate`              | Supplies the **Paid-Up Rate** (`rate_factor`) by table/version/product/plan/gender/smoker/age/term/policy-year used when a paid-up policy's maturity value is converted to installments. |
| `OLInstallmentChargeRate`   | Supplies per-frequency installment charges (`FIXED` / `PERCENTAGE` / `FACTOR`) applied on the chosen `apply_on` dimension. |

The calculation basis used at plan-creation time is snapshotted onto
`OLMaturityInstallmentConfig` so later reconciliation is possible even if the
rate tables are superseded. When a required rate row is missing for the policy's
product/plan scope, plan creation raises `PLAN_PARAMETER_MISSING` with a deep
link into the parameter catalog.

### 4.1 Documented senior-assumption notes

- **Currency**: an installment plan is denominated in the policy's currency.
  No cross-currency conversion is performed in this module; Front Office owns any
  exchange behaviour at disbursement time.
- **Frequency mapping**: plan `frequency` maps onto `OLInstallmentFrequency`
  (`SINGLE`, `MONTHLY`, `QUARTERLY`, `HALF_YEARLY`, `ANNUAL`). A single-frequency
  plan has exactly one item.
- **Rounding**: each item `amount` is rounded to the policy currency's smallest
  unit (2 dp). The last item absorbs the rounding remainder so the item total
  exactly equals `total_maturity_value`.
- **Eligibility**: a plan may only be created against a policy whose status is
  `MATURED` or `MATURED_PENDING_PAYMENT`. Anything else raises
  `PLAN_POLICY_NOT_MATURED`.
- **Audit**: every financial state transition is written to the central audit
  log with actor, before/after state, reason, and source channel, and mirrored to
  a durable `DomainEvent` in the shared outbox.

## 5. Core models

### OLMaturityInstallmentPlan

| Field                | Notes |
|----------------------|-------|
| `plan_number`        | Unique, auto-generated (`MIP-YYYYMMDD-<hex>`). |
| `policy_ref`         | FK → `ol_policies.Policy` (PROTECT). |
| `maturity_claim_ref` | FK → `ol_policies.MaturityClaim` (SET_NULL, optional). |
| `partner`            | FK → `partners.Partner` (PROTECT). |
| `currency`           | Default `TZS`. |
| `total_maturity_value` | Maturity value payable by the policy. |
| `total_payable_amount` | Sum of item amounts; must reconcile to `total_maturity_value`. |
| `installment_count`  | Positive integer. |
| `frequency`          | `OLInstallmentFrequency`-aligned choices. |
| `start_date` / `end_date` | Schedule window. |
| `status`             | Plan lifecycle state. |
| audit fields         | `created_by` / `updated_by` + timestamps, plus lifecycle actor/datetime fields. |

### OLInstallmentItem

| Field                  | Notes |
|------------------------|-------|
| `plan_ref`             | FK → plan (CASCADE). |
| `installment_number`   | 1-based sequence; unique per plan. |
| `due_date`             | Scheduled payment date. |
| `amount`               | Item payout, currency-denominated. |
| `status`               | Item lifecycle state. |
| `payment_requisition_ref` | FK → `front_office.FORequisition` (SET_NULL, optional). |
| `paid_date`            | Set when confirmed `PAID`. |
| `narration`            | Free-text note. |
| audit fields           | `created_by` / `updated_by` + timestamps. |

### OLMaturityInstallmentConfig

One-to-one snapshot of the calculation basis used for a plan: the resolved
installment-rate row, paid-up-rate row, installment-charge row, the
`calculation_basis` label, and the documented assumptions that were applied.

## 6. Permissions

`ol_maturity_installments.view`, `.create`, `.process_payment`, `.cancel`,
`.print`, `.configure`. Seeded idempotently into the IAM `UserPermission`
catalog with supporting role groups.

## 7. Domain events

`InstallmentPlanCreated`, `InstallmentPaymentDue`, `InstallmentPaymentMissed`,
`InstallmentPlanCompleted` — published to the shared `DomainEvent` outbox keyed to
the `OLMaturityInstallmentPlan` aggregate.

## 8. Structured error registry

`PLAN_POLICY_NOT_MATURED`, `PLAN_CALCULATION_MISMATCH`,
`INSTALLMENT_ALREADY_PAID`, `INSTALLMENT_PAYOUT_FAILED`,
`PLAN_PARAMETER_MISSING` — all rendered in the global Error Coach shape with
`message`, `status_code`, `resolution_steps`, `field_errors`, and `doc_ref`.
