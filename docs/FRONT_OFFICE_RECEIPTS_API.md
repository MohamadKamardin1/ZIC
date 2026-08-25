# Front Office Receipts — API Reference

**Base path:** `/api/v1/front-office/receipts/`
**Auth:** bearer token · **Permissions:** `front_office.receipts.<action>`
**Errors:** structured Error Coach shape — see [FRONT_OFFICE_RECEIPTS_ERROR_CODES.md](FRONT_OFFICE_RECEIPTS_ERROR_CODES.md).

All responses use **names, never UUIDs**, for user-facing reference fields
(branch, partner, payment mode, currency, bank account, actors). Financial
actions are idempotent, permission-controlled, and audited.

---

## Receipts

### List receipts

`GET /receipts/`

Filters: `status`, `branch`, `currency`, `payment_mode`, `payer`, `source_module`,
`date_from`, `date_to`, `unallocated_only`, `reversed_only`.
Search: `q` matches receipt number, payer name, payment reference, source reference.
Ordering: `ordering` (default `-receipt_date`). Paginated.

Each row: `receipt_number`, `receipt_date`, `payer_display`, `branch_display`,
`payment_mode_display`, `currency_display`, `receipt_amount`, `allocated_amount`,
`unallocated_amount`, `status`, `source_module`, `created_by_display`,
`posted_by_display`, `created_at`, `allowed_actions`.

### Create a draft

`POST /receipts/`

Idempotency: send header `X-Idempotency-Key`; a duplicate POST returns the same
receipt rather than creating a second one.

Body:

```json
{
  "receipt_date": "2026-08-25",
  "branch_id": "<uuid>",
  "partner_id": "<uuid>",
  "payer_name": "Asha Mollel",
  "source_module": "MANUAL",
  "currency": "TZS",
  "receipt_amount": "250000.00",
  "payment_mode": "CASH",
  "payment_reference": "",
  "narration": "Draft manual receipt."
}
```

The receipt is created as `DRAFT`. `source_module` of `OL_PROPOSAL`, `OL_POLICY`,
or `GROUP_CREDIT` requires `source_reference_type` + `source_reference_id`
(proposal / policy number).

### Retrieve / update draft

- `GET /receipts/{receipt_id}/` — header, allocations, reversal history,
  documents, audit timeline, `allowed_actions`.
- `PATCH /receipts/{receipt_id}/` — edit a `DRAFT`. Posted receipts reject
  changes to payer, amount, currency, payment mode, receipt date, and branch.

### Post a receipt

`POST /receipts/{receipt_id}/post/`

Assigns the receipt number, validates the payment-mode rule / reference data /
amount, sets `POSTED`, records `posted_by`/`posted_at`, emits `ReceiptPosted`,
and audits. Requires `front_office.receipts.post`.

### KPIs

`GET /receipts/kpis/`

`total_received_period`, `total_allocated_period`, `total_unallocated`,
`receipt_count`, `reversed_amount` — computed over the same filters as the list.

### Export

`GET /receipts/export/` — CSV export respecting the list filters.

### Options

`GET /receipts/options/` — reference-data options (`value` / `label` / `meta`)
for branches, currencies, payment modes, company bank accounts, receipt
statuses, source modules.

---

## Allocation

### Allocation options

`GET /receipts/{receipt_id}/allocation-options/`

Open commitments for the receipt's payer/partner:
`commitment_number`, `source_type`, `source_display`, `proposal_number`,
`policy_number`, `product`/`plan` display, `due_date`, `amount_due`,
`amount_paid`, `balance`, `currency`, `status`.

### Manual allocation

`POST /receipts/{receipt_id}/allocate/`

```json
{
  "target_type": "OL_COMMITMENT",
  "target_id": "OLC-2026-00001",
  "amount": "50000.00",
  "exchange_rate": "2500.000000",
  "exchange_rate_source": "EXCHANGE_RATE_TABLE:SEED",
  "narration": "Partial first instalment."
}
```

- Same-currency: no rate needed. Cross-currency: explicit `exchange_rate`, or an
  active configured rate; otherwise `RECEIPT_CURRENCY_MISMATCH`.
- Cannot exceed the receipt's unallocated balance (`RECEIPT_OVERALLOCATION`).
- Cannot exceed the commitment's outstanding balance (`RECEIPT_OVERALLOCATION`).
- Receipt must be `POSTED` or `PARTIALLY_ALLOCATED`.
- Emits `ReceiptAllocated` / `ReceiptFullyAllocated` and `PremiumReceived` (or
  `FirstPremiumReceived` when a first-premium commitment completes).

### Auto-allocate

`POST /receipts/{receipt_id}/auto-allocate/`

Allocates oldest-due commitments first (same currency first) until the receipt's
unallocated balance is exhausted. Returns a detailed allocation result.

### Exchange rate lookup

`GET /receipts/exchange-rate/?from=USD&to=TZS&date=2026-08-25`

Returns the active configured rate or `RECEIPT_CURRENCY_MISMATCH` if none.

---

## Reversal & cancellation

### Reverse a receipt

`POST /receipts/{receipt_id}/reverse/`

Body: `{ "reason": "Duplicate deposit — reversed in full." }`

Reverses all allocations, restores commitment balances/status, marks the receipt
`REVERSED`, emits `ReceiptReversed`, audits. Requires `front_office.receipts.reverse`.
Rejected by `RECEIPT_REVERSAL_LOCKED` when the receipt is older than
`RECEIPT_REVERSAL_LOCK_DAYS`. Reason is mandatory.

### Reverse a single allocation

`POST /receipts/{receipt_id}/allocations/{allocation_id}/reverse/`

Body: `{ "reason": "Wrong commitment selected." }`

Creates a reversal allocation linked via `reversal_of`, recalculates receipt
amounts/status, restores the commitment balance, audits.

### Cancel a draft

`POST /receipts/{receipt_id}/cancel/`

Body: `{ "reason": "Payer declined the deposit." }`

Only `DRAFT` receipts. Status becomes `CANCELLED`. Requires
`front_office.receipts.cancel`.

---

## Print & documents

### Generate a printout

`POST /receipts/{receipt_id}/print/`

Generates the official PDF (unified print engine) and creates a
`ReceiptDocument` with a signed, expiring download ticket. Requires
`front_office.receipts.print`.

### List documents

`GET /receipts/{receipt_id}/documents/`

### Download

`GET /receipts/documents/{document_id}/download/`

Invalid/expired ticket → `RECEIPT_TICKET_INVALID`; missing file →
`RECEIPT_FILE_MISSING`.

---

## Import

### Template

`GET /receipts/import/template/` — CSV template.

### Dry-run

`POST /receipts/import/dry-run/` (multipart `file`, `import_mode`)

Validates every row and returns row-level and field-level errors without
creating anything. Requires `front_office.receipts.import`.

### Commit

`POST /receipts/import/commit/` (body: `{ "batch_id": "<uuid>" }`)

Creates receipts and (depending on import mode) posts/allocates. Rows are
idempotent per `batch_number + row hash`. `RECEIPT_IMPORT_PARTIAL_FAILURE` when
some rows fail; failed rows remain reprocessable.

### Batches

- `GET /receipts/imports/` — batch list.
- `GET /receipts/imports/{batch_id}/` — batch detail with row statuses and
  per-row errors.

---

## Reporting & portal

### Reporting dataset

`GET /receipts/reporting/dataset/`

Fields: `receipt_number`, `date`, `branch`, `payer`, `payment_mode`, `currency`,
`amount`, `allocated`, `unallocated`, `status`, `cashier`, `source_module`.
Registered under report category `FRONT_OFFICE_RECEIPTS`.

### Partner portal (read-only)

- `GET /receipts/portal/` — the authenticated partner's own receipts (partner
  scoped, no internal audit leakage).
- `GET /receipts/portal/{receipt_id}/` — own-receipt detail.

---

## Lifecycle → event mapping

| Action | Domain event | Audit entity |
| --- | --- | --- |
| Create draft | `ReceiptCreated` | receipt |
| Update draft | — | receipt |
| Post | `ReceiptPosted` | receipt |
| Allocate | `ReceiptAllocated` / `ReceiptFullyAllocated` / `PremiumReceived` / `FirstPremiumReceived` | receipt + commitment + allocation |
| Reverse | `ReceiptReversed` / `PremiumReceived` (reverse_of) | receipt + reversal + commitment |
| Cancel | `ReceiptCancelled` | receipt |
| Print | `ReceiptPrintGenerated` | document + receipt |
