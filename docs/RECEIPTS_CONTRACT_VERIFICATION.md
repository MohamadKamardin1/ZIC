# Front Office Receipts Contract Verification

**Verification date:** 25 August 2026  
**Frontend branch:** `feature/onboarding-backend-hardening` at `474b63f` (`origin/sultan`)  
**Backend under test:** `backend/`, development settings, SQLite database, Django server at `http://127.0.0.1:8000`  
**Verification mode:** live HTTP probes with `VITE_USE_MOCKS=false` semantics; no MSW service worker was used for the backend probes.

## Executive finding

The merged backend does **not** yet contain the Front Office Receipts contract implemented by the frontend Prompts 1–9. It contains only a legacy `FOReceipt` CRUD resource. The frontend now contains a compatibility normalizer for the live list response and uses the backend’s `per_page` pagination parameter, but the advanced lifecycle, allocation, import, documents, portal, options, KPI, exchange-rate, and notification routes remain unavailable. The full real-backend Prompt 10 flow therefore cannot honestly be marked green.

> The frontend receipt UI is contract-complete against the Prompt 1–9 MSW contract, but the merged backend is not implementation-complete against that contract.

## Evidence sources

| Evidence | Result |
|---|---|
| `backend/apps/front_office/models.py` | `FOReceipt` has only `receipt_number`, `amount`, `payment_method`, `payment_date`, `reference`, `status`, and timestamps. |
| `backend/apps/front_office/serializers.py` | `FOReceiptSerializer` exposes `fields = "__all__"`; no display fields or lifecycle payload serializers exist. |
| `backend/apps/front_office/views.py` | `FOReceiptViewSet` is a plain `ModelViewSet` with search on `receipt_number`, `reference`, and `payment_method`, and filters on `status` and `payment_method`. |
| `backend/apps/front_office/urls.py` | Only router-generated collection/detail CRUD routes are registered for receipts. |
| `backend/config/urls.py` | No `/api/v1/portal/receipts/` or `/api/v1/front-office/options/` route is registered. |
| `insurance-dashboard-ui/src/lib/receipts-api.ts` | The typed client declares the advanced receipts contract used by the UI. |
| `insurance-dashboard-ui/src/mocks/receiptsHandlers.ts` | MSW mirrors the intended advanced contract for deterministic frontend tests. |

## OpenAPI verification

The live schema URL `GET /api/schema/` returned HTTP 500 before a receipt schema could be consumed. The response was the platform’s structured `INTERNAL_SERVER_ERROR` shape and reported that a serializer `read_only_fields` option was a string rather than a list or tuple. A direct offline schema generation attempt also surfaced repository-wide introspection errors and operation-ID collisions. This is a release blocker for schema-first verification, independent of the receipt route gap.

The generated schema evidence obtained during diagnosis showed the following authoritative receipt paths before the live schema endpoint failed:

| Path | Methods exposed by merged backend | Security | Status |
|---|---|---|---|
| `/api/v1/front-office/receipts/` | `GET`, `POST` | JWT or session cookie | Matched only at basic CRUD level |
| `/api/v1/front-office/receipts/{id}/` | `GET`, `PUT`, `PATCH`, `DELETE` | JWT or session cookie | Matched only at basic CRUD level |

The backend response uses camel-case JSON rendering even though the OpenAPI serializer field names are snake_case. The live list response is an envelope with `success`, `statusCode`, `message`, `data`, `pagination.page`, `pagination.perPage`, `pagination.total`, and `pagination.pages`. The `data` item uses `receiptNumber`, `amount`, `paymentMethod`, `paymentDate`, `reference`, `status`, `createdAt`, and `updatedAt`.

## Live HTTP probe matrix

The following probes were run against the live Django process and the checked-in development database. A dedicated local superuser and one receipt numbered `RECEIPT-P10-001` were created only in the sandbox database for verification.

| Probe | Expected | Observed | Assessment |
|---|---:|---:|---|
| Anonymous `GET /api/v1/front-office/receipts/` | `401` with teachable auth error | `401`, `WWW-Authenticate: Bearer`, `UNAUTHORIZED`, resolution metadata, correlation request ID | Matched security baseline |
| Authenticated `GET /api/v1/front-office/receipts/` | Typed paginated receipt list | `200`, camel-case envelope, one seeded legacy receipt | Fixed in client normalizer |
| Authenticated `GET /api/v1/front-office/receipts/{id}/` | Typed receipt detail | Route is registered; legacy fields only | Partial match |
| Authenticated `GET /api/v1/front-office/receipts/kpis/` | KPI payload | `404` after authentication | Drift: unavailable |
| Authenticated `GET /api/v1/front-office/receipts/options/branches/` | Branch options | `404` HTML route response | Drift: unavailable |
| Authenticated `GET /api/v1/front-office/receipts/import/template/` | CSV template | `404` HTML route response | Drift: unavailable |
| Authenticated `GET /api/v1/front-office/receipts/{id}/post/` | Lifecycle action | `404` HTML route response | Drift: unavailable |
| Anonymous `GET /api/v1/portal/receipts/` | Sanitized portal response | `404` | Drift: unavailable |
| Anonymous `GET /api/schema/` | OpenAPI document | `500` structured internal error | Release blocker |

## Contract comparison and fixes

The comparison below is against the typed client and its MSW handlers, not against assumptions about an unmerged backend branch.

| Contract area | Frontend contract | Merged backend | Prompt 10 action/status |
|---|---|---|---|
| List and detail | Display-safe receipt fields, allocation totals, allowed actions | Seven legacy fields plus timestamps | Client normalizes legacy response; backend remains incomplete |
| Pagination | Client previously sent `page_size` | Backend schema and live payload use `per_page`/`perPage` | Fixed client list call to send `per_page`; tests added |
| Search/filter | Search and receipt filters | Search only on three legacy fields; two filters | Partial compatibility |
| Create/patch | Branch, payer, currency, payment mode, amount, idempotency | Receipt number, amount, payment method, date, reference, status | Drift remains; advanced create flow cannot run live |
| Post/cancel/reverse | Dedicated lifecycle actions with structured errors | No action routes or state machine | Drift remains |
| Allocate/auto-allocate | Commitment-aware allocation endpoints | No allocation models or routes | Drift remains |
| Print/documents | Authenticated PDF, ticket, document history | No receipt document routes in Front Office | Drift remains |
| Imports | Template, dry run, commit, history, reprocess | No import routes or models | Drift remains |
| KPIs/exchange rate | Server-driven KPI and exchange-rate payloads | No receipt routes | Drift remains |
| Options | Branch, payer, proposal, module, currency, payment mode, bank account, status | No Front Office options routes | Drift remains |
| Portal | Partner-scoped read-only list/detail | No portal receipt URLs | Drift remains |
| Notifications | Receipt notification feed | No notification route | Drift remains |
| Error shape | `ApiClientError` with code, field errors, resolution steps, deep link | Live auth errors are structured; missing routes may be HTML 404 | Client already handles structured errors; route availability remains backend work |

## Frontend changes delivered in Prompt 10

The receipts work queue now hydrates its initial filter state from `?today=true`, `?unallocated_only=true`, `?reversed_only=true`, status, branch, currency, payment mode, payer, source module, and date-range query parameters. This makes dashboard card deep links functional on first render. The change is covered by `FOReceipts.test.tsx`.

The typed client now normalizes both the advanced paginated contract and the live legacy camel-case array/envelope. It maps legacy `paymentMethod`, `paymentDate`, `amount`, and `reference` into the display-safe receipt shape and sends the backend-compatible `per_page` query parameter. The compatibility behavior is covered by `receipts-api.test.ts` and does not fabricate unavailable lifecycle data.

The Playwright suite adds receipt accessibility, keyboard quick-filter, dark-theme token, UUID-safety, structured `PARAMETER_MISSING` ErrorCoach, and opt-in real-backend coverage. The real-backend describe block never installs page-route mocks and is activated with `E2E_REAL_BACKEND=1` plus the seeded credentials.

## Release decision

Prompt 10 real-backend acceptance is **blocked**, not green. The frontend unit suite and deterministic mock E2E suite can verify the UI contract, but they cannot prove draft-to-post, allocation, reversal, import, portal scoping, or real PDF behavior until the advanced backend receipt implementation is merged and the OpenAPI endpoint is healthy.

The required backend completion is to merge the Front Office Receipts backend series, run migrations and receipt/commitment/proposal seeds, expose the exact routes from `receipts-api.ts`, return structured JSON errors for every action, and repair the repository-wide schema introspection errors. After that merge, rerun this matrix with `VITE_USE_MOCKS=false` and enable the real-backend Playwright describe block.

## References

[1]: ../insurance-dashboard-ui/src/lib/receipts-api.ts "Typed Front Office Receipts client contract"
[2]: ../insurance-dashboard-ui/src/mocks/receiptsHandlers.ts "MSW receipts contract handlers"
[3]: ../backend/apps/front_office/models.py "Merged backend Front Office receipt models"
[4]: ../backend/apps/front_office/views.py "Merged backend Front Office receipt views"
[5]: ../backend/apps/front_office/urls.py "Merged backend Front Office receipt URLs"
[6]: ../backend/config/urls.py "Merged backend API URL configuration"
