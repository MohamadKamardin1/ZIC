# OL Maturity Installments — API Reference

The Ordinary Life (OL) Maturity Installments module converts a matured OL policy
(or a settled maturity claim) into a schedule of installment payouts. Every
endpoint below lives under the canonical base prefix `/api/v1/ol/` and returns
the platform's standard envelope. Responses are serialized with the global
CamelCase renderer, so JSON keys are camelCase in HTTP bodies even though the
underlying model fields are snake_case.

## Conventions

- **Base path:** `/api/v1/ol/maturity-installments/`
- **Auth:** Bearer token (DRF). Superusers pass all permission checks.
- **Permissions:** each endpoint is gated by an `ol_maturity_installments.<action>`
  permission (see *Permissions* below).
- **Idempotency:** plan creation requires an `X-Idempotency-Key` header.
  Replaying the same key with the same payload returns the original plan (`200`)
  instead of creating a duplicate (`201`). The same key with a different payload
  returns `409 INSTALLMENT_IDEMPOTENCY_CONFLICT`.
- **Source channel:** the optional `X-Source-Channel` header (`API`, `WEB`,
  `PORTAL`, `ADMIN`, `SYSTEM`, `BATCH`) records where the change originated and
  defaults to `API`. It is stored on the plan and written to the audit trail.
- **Error shape:** all failures use the structured Error Coach envelope with an
  `error_code`, `message`, `status_code`, optional `fieldErrors` and
  `details`, and a list of `resolutionSteps`. See
  [`OL_MATURITY_INSTALLMENTS_ERROR_CODES.md`](./OL_MATURITY_INSTALLMENTS_ERROR_CODES.md).

Response envelope for success:

```json
{
  "success": true,
  "status_code": 200,
  "message": "...",
  "data": { "...": "..." }
}
```

## Endpoints

### List plans

`GET /api/v1/ol/maturity-installments/`

Paginated register of installment plans. Supported query parameters:

| Parameter      | Meaning                                                            |
|----------------|--------------------------------------------------------------------|
| `q` / `search` | Search plan number, policy number, claim number, policyholder name |
| `status`       | `CREATED`, `ACTIVE`, `COMPLETED`, `CANCELLED`, `TERMINATED`        |
| `frequency`    | `SINGLE`, `MONTHLY`, `QUARTERLY`, `HALF_YEARLY`, `ANNUAL`          |
| `policy_number`| Exact policy number                                                |
| `product`      | Product/plan code on the policy                                    |
| `branch`       | Branch name, location, or location-master code of the policy       |
| `missed_only`  | `true`/`false` — plans carrying at least one missed installment    |
| `date_from` / `date_to` | Plan start-date range (ISO `YYYY-MM-DD`)              |
| `sort`         | One of `plan_number`, `policy_number`, `start_date`, `end_date`, `status`, `created_at`; prefix `-` for descending |
| `page`, `page_size` | Pagination (default page 1, page_size 20; max 100)          |

Response `data` contains `count`, `results`, `page`, `page_size`, `next`, `previous`.
Each row exposes the plan summary including `planNumber`, `policyNumber`,
`status`, `currency`, `frequency`, `totalAmount` (alias of total payable),
`balance` (unpaid remainder), `startDate`, `endDate`, and `paidAmount`.

### Plan detail

`GET /api/v1/ol/maturity-installments/{plan_id}/`

Full plan with `paymentHistory` (paid installments with requisition number,
payment reference, paid date, payer), the schedule items, and the
`parameterSnapshot` recording the calculation basis.

### KPIs

`GET /api/v1/ol/maturity-installments/kpis/`

Respects the same filters as the list. Returns `totalPlansActive`,
`totalUpcomingPayouts`, `missedPaymentsCount`, `completedPlansCount`, the
applied `filtersApplied`, and a `timestamp`.

### CSV export

`GET /api/v1/ol/maturity-installments/export/`

`text/csv` download applying the same filters, with `X-Content-Type-Options:
nosniff` and spreadsheet-formula-injection neutralization on free-text cells.
Columns: Plan Number, Policy Number, Policyholder Name, Total Amount,
Paid Amount, Balance, Status, Start Date, End Date.

### Create plan

`POST /api/v1/ol/maturity-installments/create/`

**Required header:** `X-Idempotency-Key` (max 64 chars).

```json
{
  "policyId": "<uuid>",
  "maturityClaimId": "<uuid or null>",
  "frequency": "ANNUAL",
  "termYears": 10
}
```

- `policyId` — a policy in `MATURED` or `MATURED_PENDING_PAYMENT` status when no
  claim is supplied. `PLAN_POLICY_NOT_MATURED` otherwise.
- `maturityClaimId` — optional; must belong to the policy and be
  `APPROVED`/`PAID`. When present, the maturity value is the claim's net payout;
  otherwise the policy sum assured is used.
- Returns `201` with the full plan on first creation, `200` with the same plan on
  an idempotent replay.

### Frequency options

`GET /api/v1/ol/maturity-installments/options/frequencies/`

Catalog of payout frequencies (`SINGLE`, `MONTHLY`, `QUARTERLY`,
`HALF_YEARLY`, `ANNUAL`) with `monthsBetween` and `payoutPerYear`. Query
parameter `q` filters by label/value; `page`/`page_size` paginate.

### Term options

`GET /api/v1/ol/maturity-installments/options/terms/`

Whole-year terms available from the installment rate table for the product
(`product`/`product_code` query filter). When no rate table covers the product,
a 1–30 year default is returned with `source: "DEFAULT"`.

### Process payment

`POST /api/v1/ol/maturity-installments/items/{item_id}/process-payment/`

Raises a Front Office disbursement requisition (`MATURITY_INSTALLMENTS`
department) against the policyholder's verified primary bank account and moves
the item to `PAYMENT_PENDING`. Requires the item to be `SCHEDULED`,
`PAYMENT_PENDING`, or `MISSED`, and its due date not to be in the future
(`INSTALLMENT_PAYMENT_NOT_DUE` otherwise). Idempotent: replaying returns the
existing requisition (`200`).

```json
{
  "data": {
    "item": { "...": "..." },
    "requisition": { "requisitionNumber": "FO-MIP-...", "status": "PENDING", "amount": "6250000.00", "department": "MATURITY_INSTALLMENTS" }
  }
}
```

### Confirm payment

`POST /api/v1/ol/maturity-installments/items/{item_id}/confirm-payment/`

Marks the disbursed item `PAID` with `paidDate`, completes the linked Front
Office requisition, activates a `CREATED` plan on its first payment, and
completes the plan (`COMPLETED` + completion audit) when every installment is
paid. Confirming an already-paid item is a safe no-op (`confirmed: false`).

### Reverse payment

`POST /api/v1/ol/maturity-installments/items/{item_id}/reverse-payment/`

```json
{ "reason": "Payment raised against a stale bank account." }
```

Reverses a paid installment within the configured window
(`INSTALLMENT_REVERSAL_WINDOW_DAYS`, default 7). The requisition is marked
`REVERSED`, the item returns to `SCHEDULED` (or `MISSED` when past due), and the
payment reference is cleared. Requires a reason
(`INSTALLMENT_REVERSAL_REASON_REQUIRED`) and a `PAID` item within the window.

### Cancel plan

`POST /api/v1/ol/maturity-installments/plans/{plan_id}/cancel/`

```json
{ "reason": "Policyholder changed payout preference." }
```

Cancels a `CREATED`/`ACTIVE` plan that is not fully paid. Remaining payable
installments are waived and pending requisitions cancelled. Blocked for
terminal/fully-paid plans (`INSTALLMENT_PLAN_CANNOT_CANCEL`) and — when the
`INSTALLMENT_PAYMENT_IRREVOCABLE` parameter is set — for any plan with a paid
installment (`INSTALLMENT_PLAN_IRREVOCABLE`).

### Reconciliation report

`GET /api/v1/ol/maturity-installments/{plan_id}/reconciliation/`

Financial reconciliation and audit-consistency verification for one plan.
Returns `status` (`PASS`/`FAIL`), maturity value, total payable, paid amount,
missing amount, paid/total item counts, and a `discrepancies` list with codes
such as `PLAN_TOTAL_MISMATCH`, `MISSING_PAYMENTS`, and `OVER_PAYMENT`.

### Print schedule / payment advice

`POST /api/v1/ol/maturity-installments/{plan_id}/print-schedule/`
`POST /api/v1/ol/maturity-installments/{plan_id}/print-advice/`

Render the maturity schedule or a payment-advice document through the shared
document engine and issue a signed download ticket (returns `201`). Watermark
rules: `CANCELLED` plans show "CANCELLED"; otherwise any missed installment
shows "MISSED PAYMENT".

### Partner portal (read-only)

`GET /api/v1/ol/maturity-installments/portal/`
`GET /api/v1/ol/maturity-installments/portal/{plan_id}/` (UUID **or** plan number)

Partner-scoped, read-only view of the policyholder's own plans with a sanitized
schedule. Any other partner's plan returns `404 PORTAL_RESOURCE_NOT_FOUND`.
POST is not allowed (`405`).

### Legacy aliases

`GET /api/v1/ol/installment-plans/` and `GET /api/v1/ol/installment-plans/{plan_id}/`
are kept for backward compatibility and map to the same list/detail views.

## Permissions

| Action             | Endpoints                                                    |
|--------------------|--------------------------------------------------------------|
| `view`             | list, detail, kpis, export, options, reconciliation, portal  |
| `create`           | create                                                       |
| `process_payment`  | process, confirm, reverse                                    |
| `cancel`           | cancel                                                       |
| `print`            | print-schedule, print-advice                                 |
| `configure`        | parameter/config management (no public endpoint)             |

The seeded role groups are `OL_MATURITY_INSTALLMENTS_VIEWER` (view only),
`OL_MATURITY_INSTALLMENTS_HANDLER` (view, create, process_payment, print), and
`OL_MATURITY_INSTALLMENTS_ADMINISTRATOR` (all six actions).
