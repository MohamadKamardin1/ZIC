# ZIC Front Office Receipts — Design

Authoritative design for the Front Office Receipts bounded context (Django app
`front_office` → module `apps.front_office.receipts`). This document is the
`doc_ref` cited by every structured error raised from the module.

## 1. The receipt concept

A receipt is the front-office write path for premium collections. It records
*who paid, when, how much, in what currency, by what instrument, against which
source record*, and it carries the full lifecycle of that collection until the
money is allocated and the record is closed.

```
DRAFT -> POSTED -> PARTIALLY_ALLOCATED -> FULLY_ALLOCATED
   |         |                                  |
   +-- CANCELLED   +----------------------------+-- REVERSED
```

Status machine rules:

- **DRAFT** — created from a quotation/proposal or manually. Fully editable.
  A draft has never touched the money trail.
- **POSTED** — the collection is confirmed (cash counted, bank credited).
  Amount fields are locked; allocations may begin.
- **PARTIALLY_ALLOCATED** — at least one allocation exists but money remains.
- **FULLY_ALLOCATED** — every shilling is allocated; the record is closed.
- **CANCELLED** — only from DRAFT, before any money is confirmed.
- **REVERSED** — from any posted state, via a first-class reversal record.

Amount invariants are enforced in the model and again at the database level:
`receipt_amount > 0`, `exchange_rate > 0`, `allocated_amount >= 0`,
`unallocated_amount >= 0`, and `unallocated = receipt - allocated` is recomputed
on every save.

## 2. Identities and naming

- `receipt_number` (e.g. `RCT-2026-000123`) is the unique human identifier
  shown in every API response, list, and notification — **never** the UUID.
- `idempotency_key` guards duplicate submission of the same financial event;
  a repeated key returns the existing receipt instead of creating a duplicate.
- `partner_name_snapshot`, `branch_name_snapshot`, and `bank_account_snapshot`
  freeze the name at capture time so history survives later renames.

## 3. First premium flow

The primary business driver is the first premium of an OL proposal.

1. The OL Proposals module signals that a first premium is due (via the
   proposals-receipts seam — see section 10).
2. Front Office creates a **DRAFT** receipt with
   `source_module = OL_PROPOSAL`, `source_reference_type = PROPOSAL_NUMBER`,
   and `source_reference_id = <proposal_number>`. The model validates that the
   referenced proposal exists.
3. Money is confirmed; the receipt is **POSTED** (prompt 3 in the series).
4. An allocation is created against the matching OL Commitment
   (`target_type = OL_COMMITMENT`). The allocation write path owns the
   OL Commitment accounting (the proposals module only reads).
5. When the first premium allocation lands, the module emits
   `FirstPremiumReceived` into the durable outbox so proposals, policies,
   reports, and the portal can reconcile asynchronously.

## 4. Allocation flow

- An allocation applies a portion of a receipt to a target
  (commitment, proposal, policy, or manual).
- `ReceiptAllocation.allocation_status` is `ACTIVE` by default; `allocated_amount`
  is the sum of active non-reversal allocations.
- Allocating more than the `unallocated_amount` raises `RECEIPT_OVERALLOCATION`.
- A currency mismatch between payment and target raises `RECEIPT_CURRENCY_MISMATCH`.
- Each allocation records `allocated_by`, `allocated_at`, and `source_channel`,
  and the receipt emits `ReceiptAllocated` (and `ReceiptFullyAllocated` when the
  balance reaches zero).

## 5. Reversal flow

- Reversals are first-class, auditable records (`ReceiptReversal`), not a status
  flag on the receipt.
- A reversal carries `reason`, `reversal_number`, a frozen
  `reversed_allocations` snapshot, and the acting user.
- Each reversed allocation is voided and linked via `reversal_of` to its original
  row, keeping the money trail fully reconstructible.
- Only a posted/allocated receipt can be reversed; an already-reversed receipt
  raises `RECEIPT_ALREADY_REVERSED`. The receipt emits `ReceiptReversed`.

## 6. Multi-currency assumptions

- The functional currency is **TZS** (parameter `RECEIPT_DEFAULT_CURRENCY`).
- Receipts may be captured in foreign currency with an `exchange_rate` to the
  functional currency (default `1.000000`).
- Amounts are stored in the receipt currency; conversion happens at allocation
  and reporting time using the stored rate.
- A payment in a currency different from the target raises
  `RECEIPT_CURRENCY_MISMATCH` unless a valid exchange rate is supplied.

## 7. Payment mode assumptions

- Payment modes are parameterized (`RECEIPT_PAYMENT_MODES`); the resolvers
  return the configured list with a documented fallback:
  `CASH, BANK_TRANSFER, CHEQUE, M-PESA, MOBILE_MONEY, OTHER`.
- Every API response renders `payment_mode_label` (a name), never a bare code.
- The payment instrument references (`payment_reference`, `bank_account`) are
  snapshotted at capture time.

## 8. Future seams (designed now, wired later)

### 8.1 Government control number (e.g. TRA)

`ReceiptDocument.document_number` is reserved for the government control
number. When the TRA integration is active, posting (prompt 3) will mint a
control number, persist it as a `ReceiptDocument` of type `RECEIPT`, and make
the receipt printable only when the control number exists.

### 8.2 Bank / payment gateway

`bank_account` and `payment_reference` already model the instrument. A gateway
integration will bind a `POSTED` receipt to a settlement reference and reconcile
against the bank statement; no schema change is expected.

### 8.3 ERP / GL

Receipts are posted to the general ledger asynchronously through the outbox
(`ReceiptPosted`, `FirstPremiumReceived`). A GL adapter will consume these
events and map to ledger journals; receipts never write to the ledger directly.

## 9. Integration with OL Commitments

- The receipts module **owns** the allocation writes against an OL Commitment
  (the `target_id` on an `OL_COMMITMENT` allocation is the commitment number).
- Allocating money updates the commitment's paid balance and status through the
  allocation service (prompt 5 in the series).
- The commitment is read-only from the OL Proposals side of this seam.

## 10. Integration with OL Proposals (the receipts seam)

Full contract lives in `docs/OL_PROPOSALS_RECEIPTS_SEAM.md`. Summary:

- Front Office Receipts owns the receipt lifecycle and the allocation writes.
- OL Proposals consumes receipt state read-only through `first_premium_posted`
  and `first_premium_status`.
- Material transitions emit durable outbox events; `FirstPremiumReceived`
  carries the `PremiumReceived` payload shape so proposals/policies/reports can
  reconcile without coupling to receipt internals.

## 11. Domain events (durable outbox)

| Event | Emitted when |
| --- | --- |
| `ReceiptCreated` | A draft receipt is created |
| `ReceiptPosted` | Money confirmed; receipt posted |
| `ReceiptAllocated` | An allocation is applied |
| `ReceiptFullyAllocated` | Unallocated balance reaches zero |
| `ReceiptReversed` | A posted receipt is reversed |
| `ReceiptCancelled` | A draft receipt is cancelled |
| `FirstPremiumReceived` | First premium of an OL proposal is allocated |

## 12. Permissions

Module `front_office.receipts`, actions
`view, create, post, allocate, reverse, cancel, print, import, configure`.
Seeded by `seed_receipt_permissions` together with role groups
`RECEIPT_VIEWER`, `RECEIPT_HANDLER`, `RECEIPT_ADMINISTRATOR`.

## 13. Structured errors (Error Coach shape)

All module faults render the platform structured shape with a registry code and
resolution steps. Registry (10 codes):

`RECEIPT_NOT_FOUND`, `RECEIPT_INVALID_STATUS`, `RECEIPT_AMOUNT_INVALID`,
`RECEIPT_ALLOCATION_INVALID`, `RECEIPT_OVERALLOCATION`, `RECEIPT_ALREADY_POSTED`,
`RECEIPT_ALREADY_REVERSED`, `RECEIPT_CURRENCY_MISMATCH`,
`RECEIPT_PERMISSION_DENIED`, `RECEIPT_PARAMETER_MISSING`.

## 14. Prompt 1 scope

Implemented and tested in this prompt:

- Domain models: `Receipt`, `ReceiptAllocation`, `ReceiptReversal`,
  `ReceiptDocument`, `ReceiptStatusHistory`.
- Permissions registration (9 codes + role groups).
- Durable outbox events (7 types).
- Central audit via signal receivers for all five models.
- Parameterized resolvers (currency, payment modes, source modules, numbering).
- API skeleton: list, create draft, retrieve, update draft, options.
- Structured error registry with the 10 codes above.
- Tests: model creation, amount computations, status enum behavior, permissions
  registered, structured error shape, audit on create/update.

## 15. Prompt 5 — multi-currency receipt and allocation behavior

The following assumptions govern cross-currency receipt and allocation
behavior. Multi-currency handling is explicit and auditable; nothing is
silently assumed.

- **`ExchangeRate` reference table.** A minimal `ExchangeRate` model
  (`apps/front_office/receipts/models.py`) holds `from_currency`, `to_currency`,
  `rate`, `effective_date`, `source`, `is_active`, plus `created_at`/`updated_at`.
  A rate is uniquely identified by `(from_currency, to_currency, effective_date)`;
  the resolver picks the most recent active rate with `effective_date` at or
  before the reference date (default today). This is a receipts-context reference
  table — the dashboard's `CurrencyPair`/`CurrencyRate` remain per-owner
  watchlist data and are not used for allocation conversion.
- **Same currency needs no rate.** When the receipt currency equals the target
  commitment currency the applied rate is `1.000000`, source `SAME_CURRENCY`;
  `converted_amount` equals the allocation `amount` and `converted_currency`
  equals the commitment currency.
- **Cross-currency requires an explicit rate.** A cross-currency allocation
  (receipt currency != commitment currency) must carry a positive exchange rate
  quoted receipt-currency → target/commitment-currency. Resolution order:
  1. an explicit `exchange_rate` on the allocation request wins (source
     `EXPLICIT`, or the caller-supplied `exchange_rate_source`);
  2. otherwise the most recent active table rate for the pair is applied (source
     `EXCHANGE_RATE_TABLE:<row.source>`);
  3. otherwise the allocation is rejected with `RECEIPT_CURRENCY_MISMATCH` (422)
     and resolution steps.
  Converted amount: `converted = (amount * rate)` quantized to 2dp in the
  commitment currency.
- **Both amounts are stored and surfaced.** `ReceiptAllocation.amount` holds the
  receipt-currency original; `converted_amount`/`converted_currency` hold the
  commitment-side values. The allocation response carries
  `allocation_amount_in_receipt_currency` and
  `allocation_amount_in_target_currency`. `recompute_allocated()` keeps summing
  `amount` in the receipt currency.
- **Audit fields.** Each allocation persists `exchange_rate_used` (the applied
  rate, quantized to the column scale so the audit trail exactly matches the
  stored value), `exchange_rate_source` (provenance), `converted_amount`, and
  `converted_currency`. `AuditService` snapshots all concrete fields, so these
  appear in the `ReceiptAllocation` audit row's `after_state`.
- **Rate validation.** Zero and negative rates are rejected: the allocation
  serializer enforces a minimum positive rate (structured 400 with
  `field_errors.exchange_rate`), and the service re-validates on the write path.
  A missing rate for a cross-currency allocation is `RECEIPT_CURRENCY_MISMATCH`
  with resolution steps and `field_errors.exchange_rate`.
- **Staleness is a warning, never a block.** The optional system parameter
  `RECEIPT_EXCHANGE_RATE_STALE_DAYS` (integer) configures a staleness window.
  When set and a table-resolved rate is older than the window, the allocation
  response and the exchange-rate endpoint carry a `warning`; the write is not
  blocked. Explicit rates and same-currency allocations never produce a stale
  warning.
- **Auto-allocation stays same-currency.** `auto_allocate` skips cross-currency
  commitments — a cross-currency allocation must be explicit, so auto-allocation
  never applies rate `1.0` silently. Cross-currency is handled by a manual
  allocation (explicit rate or table-resolved rate).
- **Endpoint contract.** `GET /api/v1/front-office/exchange-rate/?from=&to=&date=`
  validates three-letter alpha codes and an ISO date, then returns the resolved
  rate as `{from_currency, to_currency, rate, effective_date, source, is_active,
  stale, warning}`. A missing rate raises `RECEIPT_CURRENCY_MISMATCH` with
  resolution steps.
- **Events.** `PremiumReceived` (published in the same transaction as the
  `OLCommitmentAllocation` insert) reports the commitment-side converted amount
  and currency for cross-currency allocations, with the applied `exchange_rate`
  carried explicitly.

## 16. Prompt 6 — receipt reversal, allocation reversal & draft cancellation

Reversal is a first-class, auditable, *never-deleting* operation. Assumptions
governing the reversal/cancellation behavior:

- **Reversal never deletes history.** The original `ReceiptAllocation` row is
  kept and marked `allocation_status = REVERSED`; a linked reversal row
  (`reversal_of` set, status `REVERSED`) is created. `recompute_allocated()`
  sums only `reversal_of__isnull=True AND allocation_status = ACTIVE`, so the
  reversal row and the status-`REVERSED` original are both excluded and the
  allocated amount decreases by the reversed amount. The same pattern is
  mirrored on the OL Commitments side: the original `OLCommitmentAllocation` is
  kept and a reversal `OLCommitmentAllocation` (with `reversal_of`) is created
  by `ol_commitments.services.reversal_service.reverse_allocation_to_commitment`.
- **Reasons are mandatory.** A reversal (full or single allocation) and a
  cancellation without a `reason` are rejected (structured
  `RECEIPT_REASON_REQUIRED`, or a DRF 400 with `field_errors.reason` from the
  endpoint serializer). The reason is persisted on the `ReceiptReversal`
  record, the status history row, and the audit trail.
- **Full receipt reversal** (`POST /receipts/{id}/reverse/`): reverses every
  active allocation (OL commitment side included), records a `ReceiptReversal`
  with a `RVR-` reversal number and a frozen `reversed_allocations` snapshot
  (each entry carries the original allocation, its reversal row, and the linked
  OL commitment allocation reversal reference), marks the receipt `REVERSED`
  with `reversed_at`/`reversed_by`, restores each commitment's
  `amount_paid`/`balance`/status, and emits `ReceiptReversed`. After a first
  premium reversal the commitment returns to `PENDING`, so the proposal
  `first_premium_posted` guard (which reads commitment `COMPLETED` +
  fully-paid) naturally becomes `False`.
- **Single allocation reversal** (`POST /receipts/{id}/allocations/{id}/reverse/`):
  reverses one active allocation, recomputes the receipt allocated/unallocated
  amounts, and recalculates the receipt status from the amount split (e.g.
  `FULLY_ALLOCATED` -> `PARTIALLY_ALLOCATED`, or back to `POSTED` when it was
  the only allocation). The commitment balance/status restore to match.
- **Status rules.** `DRAFT` receipts cancel (`CANCELLED` + `cancellation_reason`);
  `POSTED`/`PARTIALLY_ALLOCATED`/`FULLY_ALLOCATED` receipts reverse (`REVERSED`).
  No hard delete exists for any status. `POSTED`/`PARTIALLY_ALLOCATED`/`FULLY_ALLOCATED`
  are shown with the `reverse` action in `allowed_actions`.
- **Reversal constraints.**
  - An already-reversed receipt (or an already-reversed allocation) is blocked
    with `RECEIPT_ALREADY_REVERSED` (409).
  - A configured lock period blocks reversal outside the window with
    `RECEIPT_REVERSAL_LOCKED` (422). The optional integer system parameter
    `RECEIPT_REVERSAL_LOCK_DAYS` sets how many days after `receipt_date` a
    reversal is still allowed; a value of `0`/unset disables the lock. Reversal
    of an old receipt beyond the window is refused with resolution steps.
  - Permissions: `front_office.receipts.reverse` gates full and single
    allocation reversal; `front_office.receipts.cancel` gates cancellation
    (`MustActionPermission`).
- **Reversal numbering.** Reversal numbers use a dedicated, parameterized
  `ReceiptNumberingRule` (`RVR_DEFAULT`, prefix `RVR`, seeded by
  `seed_receipt_parameters`). `ReceiptNumberingService.next_number` accepts an
  optional `rule_code`; without one it resolves the canonical receipt rule by
  code (stable `RCT_DEFAULT` selection regardless of rule creation order).
- **Audit.** Reversal writes CREATE audit rows for the `ReceiptReversal` record
  and each reversal `ReceiptAllocation`/`OLCommitmentAllocation` row, and UPDATE
  rows for the original allocations, the receipt, and each commitment — with
  before/after state, actor (`reversed_by`/`created_by`), reason, and the linked
  commitment allocation reversal references. `CommitmentPaymentReversed` is
  emitted on the commitments side for every reversed commitment allocation.

## 17. Prompt 7 — list, detail, work queue & export APIs

The read-side contract is table-first: every row is a flat object of the list
columns below, display names are surfaced (never UUIDs), and `allowed_actions`
is both state-aware and permission-aware.

- **List endpoint** `GET /api/v1/front-office/receipts/` returns paginated rows
  (`data.results`, `data.count/page/page_size/next/previous`) with columns:
  `receipt_number`, `receipt_date`, `payer_display`, `branch_display`,
  `payment_mode_display`, `currency_display`, `receipt_amount`,
  `allocated_amount`, `unallocated_amount`, `status` (code) + `status_display`
  (badge label), `source_module` + `source_module_display`,
  `created_by_display`, `posted_by_display`, `created_at`, and
  `allowed_actions`. `payer_display`, `branch_display`,
  `payment_mode_display`, `currency_display`, and the actor displays are names,
  never UUIDs.
- **Filters.** The list, KPI, and export endpoints share one filter pipeline
  (`filter_receipts`): `status`, `branch`, `currency`, `payment_mode`, `payer`
  (payer/partner name substring), `partner` (FK), `source_module`,
  `receipt_date_from`/`receipt_date_to` (aliases `date_from`/`date_to`),
  `unallocated_only`, `allocated_only`, `reversed_only`, and `search`
  (receipt number, payer name, payment reference, source reference).
  `apply_ordering` resolves the allow-listed `ordering` parameter
  (`-receipt_date` default).
- **Allowed actions are state- and permission-aware.** `allowed_actions(receipt,
  user)` derives the candidate set from status (DRAFT → update/post/cancel;
  POSTED/PARTIALLY_ALLOCATED → allocate/reverse; FULLY_ALLOCATED → reverse;
  REVERSED/CANCELLED → none) and prunes it by the actor's entitlements
  (`update`→create, `post`→post, `cancel`→cancel, `allocate`→allocate,
  `reverse`→reverse). A view-only operator therefore sees `allowed_actions: []`
  even on a DRAFT. The list/detail serializers receive the request context so
  the pruning is per-user.
- **KPI endpoint** `GET /api/v1/front-office/receipts/kpis/` returns work-queue
  aggregates over the *same* filters as the list: `total_received_period`
  (sum of `receipt_amount`), `total_allocated_period` (sum of `allocated_amount`),
  `total_unallocated` (sum of `unallocated_amount` restricted to open statuses —
  DRAFT/POSTED/PARTIALLY_ALLOCATED/FULLY_ALLOCATED — so reversed/cancelled
  receipts never inflate it), `receipt_count`, and `reversed_amount` (sum of
  `receipt_amount` over REVERSED receipts). Amounts are quantized to two decimal
  places; the applied date period is echoed as `data.period`.
- **CSV export** `GET /api/v1/front-office/receipts/export/` streams
  `text/csv` (attachment `receipts_YYYY-MM-DD.csv`) with the same list columns
  in the same order, and respects the same filters/ordering as the list.
  `allowed_actions` is serialized as a pipe-joined string; dates use ISO format.
- **Detail endpoint** `GET /api/v1/front-office/receipts/{id}/` returns the
  receipt header plus `allocations`, `reversals` (reversal history),
  `documents`, `status_history`, `allowed_actions`, and `audit_timeline` — the
  central audit entries for the receipt *and* its related records (allocations,
  reversals, documents, status-history rows), newest first, each with action,
  entity, actor name, changed fields, reason, and source channel.
- **Admin list** mirrors the API columns (receipt number, branch, payer,
  source, currency, amounts, payment, status, posted_by, timestamps) and adds
  `branch` to `list_filter`, so the admin and the work queue tell the same
  story.
- **Permissions.** List, detail, KPI, and export all require
  `front_office.receipts.view` (`MustViewReceiptsPermission`).

## 18. Prompt 8 — receipt printout & document integration

- **Unified print/PDF engine.** Receipt printouts reuse the same engine that
  OL proposals use: a versioned HTML template (`ReceiptPrintTemplate`, code
  `RECEIPT`, v1 seeded on first use) is rendered with a Django context, turned
  into a PDF by WeasyPrint, persisted via `default_storage` under
  `front_office_receipts/{receipt_number}/{timestamp}.html|pdf`, and recorded
  as a `ReceiptDocument` row (status `GENERATED`, `mime_type
  application/pdf`). Each generated document retains its source transaction
  (FK `ReceiptDocument.receipt`) and the template version that produced it
  (`template_version`, cross-checked against `template.version` on save), then
  the pipeline writes a `PRINT` audit entry and emits the durable
  `ReceiptPrintGenerated` domain event. `html_reference` keeps the raw markup
  for re-printing / inspection.
- **Template variables** (`ReceiptPrintService.VARIABLES`):
  - `company` — logo + company details (name, address, phone, email, tax id).
  - `receipt` — receipt number, date, branch, source module/reference,
    payment mode, payment reference, currency, status.
  - `payer` — payer name, identity, and partner/identity number.
  - `money` — amount in figures (`TZS 100,000.00`) and amount in words
    (whole + fractional subunit, rounded half-up to two decimals).
  - `allocations` — allocated commitments table (commitment number,
    narration, amount, converted amount/currency when multi-currency,
    allocation status) plus the unallocated-amount row.
  - `generated` — print-generation trace (`by` actor, `at` timestamp).
  - `cashier` — created-by display; `posted_by` — posting actor display.
  - `watermark` — `REVERSED` / `CANCELLED` overlay for non-clean printouts.
  - `preview` — true for DRAFT preview printouts.
  - `template_version` — footer `Template v{version}`.
- **Print rules.** `DRAFT` → preview only (requires `preview: true`, else
  `RECEIPT_INVALID_STATUS` 422; the permission gate still applies).
  `POSTED` / `PARTIALLY_ALLOCATED` / `FULLY_ALLOCATED` → official receipt
  (no watermark). `REVERSED` → official receipt with a reversal watermark.
  `CANCELLED` → official receipt with a cancelled watermark. Any other status
  is rejected with `RECEIPT_INVALID_STATUS`.
- **API.** `POST /api/v1/front-office/receipts/{id}/print/` generates and
  returns the document payload (incl. signed `pdf_url`/`html_url`), gated by
  `front_office.receipts.print` (`MustActionPermission("print")`);
  `GET /api/v1/front-office/receipts/{id}/documents/` returns the document
  register for a receipt (view permission); `GET
  /api/v1/front-office/receipts/documents/{id}/download/?ticket=...` streams
  the generated PDF.
- **Signed-ticket download.** The media backend is public in DEBUG, so
  generated files are never served from `/media/`. `document_urls` issues an
  HMAC-SHA256 ticket over a base64url JSON payload
  `{purpose, document_id, user_id, expires}` (15-minute TTL) bound to the
  requesting user; the download view validates it with constant-time
  comparison and streams the file (`Content-Disposition: inline`), auditing a
  `DOWNLOAD` entry on the source receipt. Tickets cannot be replayed across
  users or documents.
- **Audit.** `PRINT` is logged at generation (document id, template code and
  version, watermark, preview flag) and `DOWNLOAD` is logged per streamed
  file, both on the receipt entity via `AuditService`. The receipt document
  serializer exposes template, template version, generated-by, generated-at,
  and the signed download URLs so the front end can deep-link prints.

## 19. Prompt 9 — bulk receipt import

Bulk receipt import is a two-phase, safe, idempotent pipeline: **dry-run**
validates every CSV row and explains every error without touching `Receipt`;
**commit** replays the validated rows into receipts and records per-row
outcomes so failed rows stay reprocessable.

- **Models.** `ReceiptImportBatch` (batch_number unique, `import_mode`
  `DRAFT`/`POST`/`ALLOCATE`, status `PENDING`/`VALIDATED`/`COMMITTED`/
  `PARTIAL`/`FAILED`, row counters, `file_name`, `summary`) owns
  `ReceiptImportRow` rows (row_number, `row_hash` sha256 content hash, `data`
  JSON, per-row status `PENDING`/`VALID`/`INVALID`/`COMMITTED`/`FAILED`/
  `DUPLICATE`, `validation_errors` JSON, `error_code`, `error_message`,
  optional `receipt` FK, `committed_at`). Both are `AuditedModel`s; batch
  actions are audited via `AuditService`.
- **CSV contract** (downloadable template; six required columns, four
  optional): `receipt_date`, `branch_code`, `payer_partner_number`,
  `currency_code`, `payment_mode_code`, `amount` (required) plus
  `payment_reference`, `source_module`, `target_commitment_number`,
  `narration` (optional). The file must be UTF-8; missing required headers
  fail the whole upload with a clear field error.
- **Dry-run.** `POST /import/dry-run/` (multipart `file` + `import_mode`,
  permission `import`): normalizes each row (dates, currency defaults to the
  configured default, amount to 2dp), validates branch/partner/currency/
  payment-mode/amount against active reference data, rejects any
  `source_module` other than `MANUAL` (receipts are allocated manually
  afterwards), validates an optional target commitment (exists, not terminal,
  partner match, and in `ALLOCATE` mode amount ≤ balance and same currency),
  enforces the payment-mode rule for `POST`/`ALLOCATE` modes (reference /
  bank-account / min-max), and marks intra-file duplicates `DUPLICATE` via
  content hash. No receipts are created; every row is persisted with its
  field-level errors.
- **Commit.** `POST /import/commit/` (`batch_id`, permission `import`):
  replays `VALID`/`FAILED`/`PENDING` rows inside a per-row `atomic` block via
  `create_draft` (idempotency key `IMP:{batch}:{row_hash[:20]}`), then posts
  when `import_mode` is `POST`/`ALLOCATE` and allocates to the target
  commitment when `ALLOCATE` + target. A row failure rolls its draft back and
  marks the row `FAILED` with a structured error code and field errors; the
  batch ends `COMMITTED`, `PARTIAL` (some failed), or `FAILED` (all failed).
- **Idempotent reprocessing.** Re-committing a batch skips `COMMITTED` rows
  and retries only `FAILED` rows, so fixing the underlying cause (e.g.
  re-activating a branch) and re-committing completes the import without
  duplicating receipts.
- **Register.** `GET /imports/` lists batches (view permission, paginated)
  and `GET /imports/{batch_id}/` returns the batch header plus every row's
  status/errors/receipt link.
- **Error codes.** `RECEIPT_IMPORT_ROW_INVALID` (422, row-level field errors),
  `RECEIPT_IMPORT_DUPLICATE` (409, duplicate content within the file),
  `RECEIPT_IMPORT_PARTIAL_FAILURE` (422, commit ended with failed rows),
  `RECEIPT_IMPORT_BATCH_NOT_FOUND` (404).
- **Audit.** `IMPORT_DRY_RUN` is logged at dry-run (totals + import mode) and
  `IMPORT_COMMIT` at commit (status, committed/failed counts) on the batch.

## 20. Prompt 10 — integrations around receipts

Prompt 10 wires the receipts module into its neighbours through clean,
event-driven seams (no tight coupling — the receipts module keeps owning its
write path; every other module consumes it read-only or via the durable
outbox).

- **OL Proposals (Scope 1).** `first_premium_status` already reads the linked
  commitment's allocations; the proposal **detail** payload now also exposes a
  `receipts` array (`proposal_receipt_references` in
  `ol_proposals/services/first_premium_service.py`) listing the latest receipts
  that reference the proposal directly (`source_module=OL_PROPOSAL`) or that
  allocated against its first-premium commitment — newest first, capped at 5.
  `first_premium_posted` remains the single BR-03 truth: it flips to `True` the
  moment a posted receipt is fully allocated against the commitment (status
  `COMPLETED` + `amount_paid + amount_waived >= premium_amount`).
- **OL Commitments (Scope 2).** Commitment detail already serialises its
  allocations, each carrying `receipt_reference`; `CommitmentPaymentAllocated`
  already embeds `receipt_reference` when the source is a receipt. No change was
  needed on the commitments side — the seam contract
  (`docs/OL_PROPOSALS_RECEIPTS_SEAM.md`) already guarantees receipts write
  `OLCommitmentAllocation` rows in the same DB transaction.
- **Dashboard (Scope 3).** `receipt_kpis` (front-office KPI hook) now returns
  four additional aggregates scoped to the same filters as the list: receipts
  today (`receipts_today`), amount received today (`amount_received_today`),
  count of open receipts still carrying unallocated balance
  (`unallocated_receipts`), and count of reversed receipts
  (`reversed_receipts`). Amounts stay quantized to two decimal places.
- **Reporting (Scope 4).** New `reporting_service.py` idempotently registers
  the `FRONT_OFFICE_RECEIPTS` report category and the
  `front-office-receipts-report` dataset registry (slug, `parameter_group`
  `REPORT`, permission `front_office.receipts.view`), and `GET
  /front-office/receipts/reporting/dataset/` exposes the field contract:
  `receipt_number`, `date`, `branch`, `payer`, `payment_mode`, `currency`,
  `amount`, `allocated`, `unallocated`, `status`, `cashier`, `source_module`.
- **Portal (Scope 5).** `GET /front-office/receipts/portal/` and
  `/portal/{receipt_id}/` are partner-scoped, read-only endpoints: the actor's
  `current_partner()` gates the queryset, so a partner only ever sees their own
  receipts and their own allocations, and a foreign/nonexistent receipt returns
  the same 404. The portal serializers deliberately exclude internal audit
  state (`allowed_actions`, `audit_timeline`, `created_by_display`, status
  history, reversals, documents) so no internal leakage is possible.
- **Notifications (Scope 6).** New `ReceiptNotificationLog` model mirrors the
  commitments/proposals notification contract. `notification_service.py`
  emits `ReceiptPosted` (on post), `ReceiptReversed` (on reversal, with the
  reason), and `FirstPremiumReceived` (when a PROPOSAL first-premium commitment
  is discharged by a receipt allocation), each idempotent via the
  `(receipt, event_type, dispatch_on, channel, recipient)` unique constraint.
- **ERP/GL seam (Scope 7).** New `gl_seam.py` writes durable `DomainEvent`
  outbox payloads — `GLReceiptPosting` on post and `GLReceiptReversal` on
  reversal — for a future GL consumer to post. The documented DR/CR mapping
  assumption (posting: DR `BANK_OR_CASH`, CR `PREMIUM_SUSPENSE`; reversal:
  mirrored) is carried in each payload's `mapping` key for the accounting team
  to review. Allocation's suspense-clearing transition stays owned by the
  commitments module (`PremiumReceived`), so the GL seam deliberately stops at
  posting/reversal.
- **Tests.** `apps/front_office/receipts/tests/test_integrations.py` covers:
  proposal first-premium status reflects a receipt allocation (service + API),
  proposal detail exposes latest receipt references, commitment detail includes
  the receipt reference (model + API + `CommitmentPaymentAllocated` event),
  portal scoping denies other partners and leaks no audit state, dashboard KPI
  math, report category/dataset registration, GL outbox events on post and
  reversal, and the three notification log rows.
