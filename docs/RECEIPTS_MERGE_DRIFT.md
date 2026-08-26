# Front Office Receipts — Merge Drift Report

**Prepared:** 26 August 2026
**Branch:** `feature/front-office-receipts-foundation`
**Frontend source:** manus.im parallel build, contract-first against `docs/FRONT_OFFICE_RECEIPTS_API.md` and the MSW mock handlers.
**Backend under test:** `backend/` (Django 5.0.14, `config.settings.development`).

This report compares the frontend typed client (`insurance-dashboard-ui/src/lib/receipts-api.ts`)
and the authoritative MSW mock handlers (`insurance-dashboard-ui/src/mocks/receiptsHandlers.ts`)
against the actual backend. Every drift found below was resolved in the backend (preferred) —
no frontend change was required. See `docs/RECEIPTS_MERGE_CHECKLIST.md` for the merge gate.

## 1. Contract sources

| Source | Role |
|---|---|
| `insurance-dashboard-ui/src/lib/receipts-api.ts` | Typed API client — the consumed shape. |
| `insurance-dashboard-ui/src/mocks/receiptsHandlers.ts` | MSW handlers — authoritative response shapes. |
| `docs/FRONT_OFFICE_RECEIPTS_API.md` | Written API contract. |
| `backend/apps/front_office/receipts/*` | Actual backend implementation. |

The backend client (`request()` in `src/lib/apiClient.ts`) unwraps the `{data: ...}` envelope, so
all backend responses wrap their payload in `{"data": ...}`.

## 2. Missing endpoints — added

The frontend contract declared these routes that the backend did not expose. All were implemented
in the backend.

| Endpoint | View |
|---|---|
| `GET /front-office/receipts/{id}/allocations/` | `ReceiptAllocationsView` |
| `GET /front-office/receipts/{id}/reversals/` | `ReceiptReversalsView` |
| `GET /front-office/receipts/{id}/audit-timeline/` | `ReceiptAuditTimelineView` |
| `GET /front-office/receipts/{id}/bank-account/` | `ReceiptBankAccountView` |
| `POST /front-office/receipts/imports/{batch_id}/reprocess/` | `ReceiptImportReprocessView` |
| `GET /front-office/receipts/options/{resource}/` | `ReceiptOptionsResourceView` — branches, payers, proposals, source-modules, currencies, payment-modes, bank-accounts, statuses |
| `GET /front-office/receipts/options/{resource}/quick-create-schema/` | `ReceiptOptionsResourceView` (GET) |
| `POST /front-office/receipts/options/{resource}/quick-create/` | `ReceiptOptionsResourceView` (POST) — branch / payer quick-create |
| `GET /api/v1/portal/receipts/` | `PartnerPortalReceiptListView` (portal alias module) |
| `GET /api/v1/portal/receipts/{id}/` | `PartnerPortalReceiptDetailView` (portal alias module) |

`ReceiptOptionsResourceView` returns paginated `{results, count, page, page_size, next, previous}`
of `{value, label, meta}` options with `?q=` filtering; proposals are filtered to open,
first-premium commitments and carry a `status_hint` meta.

## 3. Field drift — aliases and `*_display` labels added

All FK/reference fields now ship a human-readable display label and the web-facing aliases the
frontend consumes.

| Serializer / service | Fields added |
|---|---|
| `ReceiptAllocationSerializer` | `status`, `source_display`, `reversed_at`, `is_first_premium`, `proposal_number`, `restored_balance` |
| `ReceiptReversalSerializer` | `created_by_display`, `created_at`, `source_channel` |
| `ReceiptDocumentSerializer` | `template_name`, `generated_by_display`, `page_count` (guarded pypdf), `preview_url`, `download_url`, `signed_download_url` |
| `ReceiptImportBatchSerializer` | `uploaded_by_display`, `uploaded_at`, `ok_count`, `error_count` |
| Work-queue KPIs | `received_today`, `allocated_in_period`, `unallocated_amount`, `unallocated_receipt_count`, `currency` (dominant-currency default TZS) |
| Audit timeline | `actor_display`, `occurred_at`, `before_summary`, `after_summary` (kept `action` = `entry.action_type`) |
| Import row payload | `row`, `field_errors`, `resolution_steps` (from `RECEIPT_ERROR_REGISTRY`) |
| Allocation options (`commitment_option`) | `is_first_premium`, `proposal_number` (first-premium proposal resolution) |
| Auto-allocate result | `is_first_premium`, `proposal_number`, `remaining_unallocated_amount`, `first_premium_completed`, `first_premium_proposal_number` |

## 4. Response shape changes

- **`POST /print/`** now returns `{data: {receipt, document}}` where `document.urls.pdf_url` and
  `document.urls.html_url` carry signed, short-life download tickets
  (`/front-office/receipts/documents/{id}/download/?ticket=...`). For backward compatibility the
  legacy document fields are flattened onto the envelope (including `watermark` from metadata) as
  a superset — no caller of either shape breaks.
- **`POST /allocate/`** accepts the web plural contract
  `{allocations: [{commitment, amount, exchange_rate}]}` (commitment = commitment pk) **or** the
  legacy `{target_type, target_id, amount}`. The response is a superset: the receipt detail at the
  top level plus `receipt`, `allocations`, `remaining_unallocated_amount`,
  `first_premium_completed`, `first_premium_proposal_number`. Allocation rows include the legacy
  FX keys `allocation_amount_in_receipt_currency`, `allocation_amount_in_target_currency`,
  `exchange_rate_used`, `converted_amount`, `converted_currency`.
- **`POST /import/commit/`** accepts either the web flow (`file` + `mode` via FormData,
  re-validated then committed) or the batch flow (`batch_id`). Dry-run and commit share the
  flattened `ReceiptImportResult` shape: `{dry_run, imported, created, total_rows, ok_count,
  error_count, batch_id, status, rows, errors, summary}` — plus the legacy `batch` envelope,
  `partial_failure`, and `error_code` keys.

## 5. Error shape alignment

The backend error envelope already carries `success`, `status_code`, `error_code`, `message`,
`resolution_steps`, `field_errors`, `doc_ref`, plus the camelCase aliases `resolutionSteps` and
`deepLink` added earlier for the frontend coach UI. `RECEIPT_ERROR_REGISTRY`
(`apps/front_office/receipts/errors.py`) maps every receipt error code to a teachable
`(message, status_code, resolution_steps)` triple. Unauthenticated access returns HTTP 401 in the
structured envelope with `resolution_steps` that explain how to authenticate.

## 6. Fixes applied during merge verification

Running the merged backend suite surfaced four regressions from the drift work — all fixed:

1. **`ReceiptImportRowStatus.ERROR` AttributeError** — `_import_errors` referenced an enum member
   that does not exist. Fixed to filter `INVALID`, `FAILED`, `DUPLICATE`.
2. **Allocation-options legacy shape** — the paginated rewrite dropped `data.commitments`. Added the
   full option list under `commitments` (superset; the items already carry both the web and legacy
   field names).
3. **Allocation row FX keys** — `_allocation_item` lacked the legacy FX fields; added
   `allocation_amount_in_*`, `exchange_rate_used`, `converted_amount`, `converted_currency`.
4. **Import result / batch detail / print envelopes** — added the `batch` envelope,
   `partial_failure`, `error_code`, `rows` to import responses, and flattened the print document
   fields (incl. `watermark`) so both the web contract and the legacy suite pass.

One backend test (`test_row_level_error_payload_shape`) asserted the *exact* pre-merge row key set;
it was updated to include the frontend-required `row`, `field_errors`, `resolution_steps` keys.
This is the only test change; no frontend files were modified.

Two earlier schema blockers were also fixed so `openapi-generator`-style verification works at all:
a serializer `read_only_fields` set as a bare string (→ list) and a redundant `source="documents"`
declaration removed (ordinary_life / partners serializers).

## 7. Verification summary

| Check | Result |
|---|---|
| Backend receipt suite | 216 passed |
| Front-office + OL-proposals suite (incl. first-premium E2E, portal read-only) | 320 passed |
| Full backend suite | see merge checklist |
| OpenAPI schema (`manage.py spectacular`) | generates (drf-spectacular `unable to guess serializer` fallbacks for hand-built APIViews are informational, not blockers) |
| Ruff (edited files, line-length 120) | clean |
| URL resolution for all new routes | all resolve |

## 8. Open notes

- The drf-spectacular "unable to guess serializer" messages for the hand-built `APIView`s are
  pre-existing and non-fatal. If strict schema-first generation is ever required, annotate the
  views with `@extend_schema`/`serializer_class`; out of scope for this merge.
- `VITE_USE_MOCKS=false` must be set in staging/prod so the UI calls the real backend (see the
  merge checklist).
