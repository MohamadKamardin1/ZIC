# ZIC Ordinary Life Loans API Guide

## API conventions

All endpoints are rooted at `/api/v1/ol/loans/` and require Bearer authentication unless explicitly documented otherwise. Financial actions require the matching `ol_loans.*` permission and an idempotency key or stable source reference. Dates use `YYYY-MM-DD`; monetary values are decimal strings; currency values are three-letter uppercase codes.

Successful responses use the platform envelope:

```json
{
  "data": {},
  "meta": {"correlation_id": "..."}
}
```

Errors use the Error Coach contract:

```json
{
  "error_code": "LOAN_EXCEEDS_LIMIT",
  "message": "Requested amount exceeds the configured policy loan limit.",
  "field_errors": {"requested_amount": ["Enter no more than 400000.00 TZS."]},
  "resolution_steps": [
    "Reduce the requested amount to the available configured loan limit.",
    "Review the policy cash-value snapshot and existing loan balance."
  ],
  "details": {"available_loan_limit": "400000.00"},
  "doc_ref": "docs/OL_LOANS_DESIGN.md"
}
```

Foreign keys are represented with human-readable display fields. Internal UUIDs are resource identifiers only and are not rendered as names in list, detail, portal, document, or export payloads.

## Read and reporting endpoints

| Method and path | Permission | Purpose |
| --- | --- | --- |
| `GET /api/v1/ol/loans/` | `ol_loans.view` | Paginated, searchable, filterable loan list |
| `GET /api/v1/ol/loans/{id}/` | `ol_loans.view` | Loan detail with schedules, repayments, accruals, offsets, actions, and audit timeline |
| `GET /api/v1/ol/loans/kpis/` | `ol_loans.view` | Current active/defaulted/settled counts and amount maps |
| `GET /api/v1/ol/loans/export/` | `ol_loans.view` | UTF-8 CSV using the same list filters and display columns |
| `GET /api/v1/ol/loans/dashboard/` | `ol_loans.view` | Outstanding balances grouped by branch and product plus default-rate KPI |
| `GET /api/v1/ol/loans/portal/` | partner visibility | Read-only partner-scoped portal list |
| `GET /api/v1/ol/loans/portal/{id}/` | partner visibility | Read-only partner-scoped detail |

List filters include `q`/`search`, `status`, `currency`, `product`, `agent`, `branch`, `disbursement_date_from`, `disbursement_date_to`, `maturity_date_from`, `maturity_date_to`, `overdue_only`, `balance_gt_zero`, `page`, `page_size`, and allow-listed `ordering`. Search covers loan number, policy number, and policyholder name/number.

A list item includes `loan_number`, `policy_number`, `policyholder_display`, `product_display`, `agent_display`, `branch_display`, `currency`, `principal_amount`, `outstanding_balance`, `disbursement_date`, `maturity_date`, `status`, and `allowed_actions`. It does not expose a raw policy or partner UUID as a display value.

The KPI response is shaped as follows:

```json
{
  "data": {
    "active_count": 3,
    "defaulted_count": 1,
    "settled_count": 1,
    "closed_count": 0,
    "disbursed_amounts_by_currency": {"TZS": "5000000.00"},
    "outstanding_amounts_by_currency": {"TZS": "3500000.00"},
    "currency": "TZS",
    "as_of": "2026-08-27",
    "timestamp": "2026-08-27T00:00:00Z"
  }
}
```

## Lifecycle endpoints

| Method and path | Permission | Required idempotency/source |
| --- | --- | --- |
| `POST /api/v1/ol/loans/request/` | `ol_loans.request` | `X-Idempotency-Key` |
| `POST /api/v1/ol/loans/{id}/approve/` | `ol_loans.approve` | Request lifecycle record |
| `POST /api/v1/ol/loans/{id}/reject/` | `ol_loans.approve` | Rejection reason |
| `POST /api/v1/ol/loans/{id}/disburse/` | `ol_loans.disburse` | `X-Idempotency-Key` |
| `POST /api/v1/ol/loans/{id}/repay/` | `ol_loans.repay` | `X-Idempotency-Key` or receipt reference |
| `POST /api/v1/ol/loans/{id}/reverse-repayment/` | `ol_loans.reverse` | Authorized correction key |
| `POST /api/v1/ol/loans/{id}/offset/` | `ol_loans.offset` | `(loan, source_type, source_id)` |
| `POST /api/v1/ol/loans/{id}/print-agreement/` | `ol_loans.print` | Document ticket/history |
| `POST /api/v1/ol/loans/{id}/print-schedule/` | `ol_loans.print` | Document ticket/history |

### Request example

```http
POST /api/v1/ol/loans/request/
Authorization: Bearer <access-token>
X-Idempotency-Key: OL-RELEASE-REQUEST-EXAMPLE-001
Content-Type: application/json

{
  "policy_id": "<policy-resource-id>",
  "requested_amount": "1000000.00",
  "term_months": 12,
  "repayment_mode": "EQUAL_INSTALLMENT",
  "reason": "Policyholder education expense"
}
```

The service checks policy status, product loan allowance, active effective-dated setup, configured repayment mode and term, cash value, minimum and maximum amounts, and existing active loans. A request requiring approval returns `REQUESTED` with `approval_required=true` and a linked shared approval record.

### Disbursement example

```http
POST /api/v1/ol/loans/<loan-id>/disburse/
Authorization: Bearer <access-token>
X-Idempotency-Key: OL-DISBURSE-EXAMPLE-001
Content-Type: application/json

{
  "payment_mode": "BANK_TRANSFER",
  "bank_account_code": "ZIC-OL-LOAN-RELEASE-TZS",
  "reason": "Release approved policy loan"
}
```

The operation creates one front-office requisition, one `OLLoanDisbursement`, one schedule per contractual installment, and the Active transition atomically. A replay returns the original disbursement and schedule.

### Repayment example

```http
POST /api/v1/ol/loans/<loan-id>/repay/
Authorization: Bearer <access-token>
X-Idempotency-Key: OL-REPAY-EXAMPLE-001
Content-Type: application/json

{
  "amount": "250000.00",
  "currency": "TZS",
  "exchange_rate": "1.00000000",
  "payment_date": "2026-08-27",
  "receipt_ref": "",
  "reason": "Scheduled policy-loan repayment"
}
```

For a different repayment currency, provide the approved positive exchange rate. The response retains the original amount/currency/rate and returns the converted applied amount and allocation breakdown.

### Offset example

```http
POST /api/v1/ol/loans/<loan-id>/offset/
Authorization: Bearer <access-token>
Content-Type: application/json

{
  "source_type": "CLAIM",
  "source_id": "CLM-2026-000123",
  "payout_amount": "600000.00",
  "reason": "Deduct outstanding loan from death claim proceeds"
}
```

The service returns `offset_amount`, `remaining_payout`, current status, and the immutable offset reference. Settlement integrations use `source_channel=SYSTEM` when converting policy events into loan ledger writes because `EVENT` is not a valid OL Loan source channel.

## Batch commands

```bash
python3 manage.py accrue_loan_interest --as-of 2026-08-27 --frequency daily --correlation-id ACCRUAL-2026-08-27
python3 manage.py detect_loan_defaults --as-of 2026-08-27 --correlation-id DEFAULT-2026-08-27
python3 manage.py verify_loan_audit --json
python3 manage.py seed_ol_loan_release --json
```

The release seed result contains ten scenario rows and five proof payloads. It is suitable for CI or operational evidence because all scenario numbers, states, balances, repayment/offset counts, audit counts, and error resolution steps are explicit.

## Authorization and source channels

The supported OL Loan source channels are `WEB`, `API`, `ADMIN`, `SYSTEM`, `IMPORT`, `PORTAL`, `BATCH`, and `MANUAL`. Policy settlement events are mapped to `SYSTEM` at the persistence seam. Every financial response includes a correlation ID when available; every audit record includes actor, reason, before/after state, and source channel.


## Final UI release contracts

The partner portal exposes sanitized, partner-scoped data only:

| Method and path | Permission/scope | Purpose |
| --- | --- | --- |
| `GET /api/v1/ol/loans/portal/` | Authenticated partner visibility | Paginated loans belonging to the current partner. |
| `GET /api/v1/ol/loans/portal/{loan_number}/` | Authenticated partner visibility | Read-only detail addressed by human-readable loan number. |
| `POST /api/v1/ol/loans/portal/request/` | Partner loan-request permission and ownership checks | Creates a request from a policy number using the canonical request validation service. |

Portal payloads include `loan_number`, `policy_number`, partner-safe display labels, balances, status, schedule rows where permitted, and `request_allowed`. They do not use a raw UUID as a visible label or navigation key. Portal users cannot disburse, repay, offset, reverse, or print through the staff action API.

Loan document generation uses the unified document pipeline:

| Method and path | Permission | Purpose |
| --- | --- | --- |
| `POST /api/v1/ol/loans/{id}/print-agreement/` | `ol_loans.print` | Generate and store a branded loan agreement instance. |
| `POST /api/v1/ol/loans/{id}/print-schedule/` | `ol_loans.print` | Generate and store a branded repayment schedule instance. |
| `GET /api/v1/documents/instances/?source_type=OL_LOAN&object_id={id}` | `ol_loans.print`/document visibility | List generated loan document instances with template version, page count, generated-by display, and timestamps. |
| `GET /api/v1/documents/instances/{instance_id}/download/?ticket={ticket}` | Bearer token or valid short-lived ticket | Stream the PDF for authenticated preview/download or signed new-tab access. |

A successful print response returns `instance`, `preview_url` or an authenticated preview source, and `signed_download_url`. The signed ticket is short-lived and single-purpose; the server rechecks expiry, document identity, permission, and ticket integrity. The browser must not open a raw unauthenticated `/api/` URL in a new tab.

Loan UI financial actions use the following authenticated endpoints and return the standard `data` envelope plus correlation metadata:

```http
POST /api/v1/ol/loans/<loan-id>/disburse/
POST /api/v1/ol/loans/<loan-id>/repay/
POST /api/v1/ol/loans/<loan-id>/offset/
```

Each request carries `X-Idempotency-Key`. Disbursement requires an approved loan and payment mode; repayment requires a positive amount no greater than the current balance, payment mode, and a receipt or approved manual reference; offset requires `source_type`, `source_id`, and a positive `payout_amount`. The backend remains authoritative for lifecycle, balance, ownership, and duplicate-operation checks.

The final UI release verification command is:

```bash
cd insurance-dashboard-ui
pnpm exec playwright test e2e/ol-loans-prompt10.spec.ts --reporter=line
```

The full frontend and affected backend verification commands remain documented in `insurance-dashboard-ui/docs/E2E.md` and `docs/OL_LOANS_ADMIN_GUIDE.md`.
