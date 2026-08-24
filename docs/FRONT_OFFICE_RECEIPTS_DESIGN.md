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
