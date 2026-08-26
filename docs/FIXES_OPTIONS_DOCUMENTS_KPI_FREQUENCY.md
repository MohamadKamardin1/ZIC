# ZIC OL Fixes Verification Summary

## Purpose

This document records the final verification of the OL options, document, KPI, product-frequency, and quotation-wizard Manage-link fixes. The changes are intentionally narrow: they repair the contracts used by the existing OL quotation workflow without replacing the unified document engine or introducing a second options registry.

The verification approach combines real Django API tests for persistence, authorization, aggregation, document rendering, signed tickets, and audit records with Playwright contract tests for the browser flows. Playwright uses deterministic API route fixtures so that browser assertions remain repeatable; the backend API suite exercises the corresponding real service and database behavior.

## Fixed contract matrix

| Area | Canonical contract | Verified behavior |
|---|---|---|
| Partner options | `GET /api/v1/ol/options/banks/`, `/intermediaries/`, and `/employers/` | Returns active, labeled `{value, label, meta}` options with search, pagination, permission enforcement, and structured unknown-entity errors. |
| General OL options | `GET /api/v1/ol/options/<entity>/?q=&page=&page_size=` | Uses the registry providers, excludes inactive/effectively unavailable records, and exposes human-readable labels rather than UUID text. |
| Legacy options | `/api/v1/ol-proposals/options/<entity>/` | Retained as compatibility redirects to the canonical OL options namespace. |
| Quotation KPIs | `GET /api/v1/ol/quotations/kpis/` | Returns real-time counts, premium totals, finalization latency, currency, per-currency breakdown, and an ISO timestamp. Status, date, agent, branch/location, and currency filters are honored. |
| Product frequency | `OLProduct.premium_frequencies` | Stores only canonical uppercase codes: `ANNUALLY`, `SEMI_ANNUALLY`, `QUARTERLY`, `MONTHLY`, and `SINGLE`. Legacy aliases are normalized during save. |
| Frequency validation | Quotation plan selection and plan-configuration CRUD | Accepts a case-insensitive value only when it is present in the selected product configuration, persists the canonical uppercase value, and returns `PLAN_CONFIG_INVALID_FREQUENCY` with allowed values and correction guidance on mismatch. |
| Unified documents | `/api/v1/documents/render/<document_type>/<object_id>/` | Generates and stores branded PDF instances with template provenance, preview/blob access, and a short-lived signed ticket. |
| Signed document ticket | `GET /api/v1/documents/instances/<id>/download/?ticket=<ticket>` | Valid for five minutes, bound to the document and PDF purpose, permission-rechecked, and rejected when expired, tampered, cross-format, or out of scope. |
| Manage links | Frontend SmartSelect `manageRoute` and registry | Visible only to superusers or authorized configure-equivalent roles. Wizard links preserve `return_to` and active draft context and open the exact parameter tab where supported. |

## KPI behavior and data safety

The KPI service uses the same quotation scope and effective-status semantics as the quotation work queue. A quotation whose effective state has become expired is counted in `total_expired`, even when its stored status is still a non-terminal state. `avg_days_to_finalize` is calculated from the quotation creation timestamp to the first durable finalized lifecycle event; quotations without that event do not contribute to the average.

Premium values are not added across currencies. A requested currency produces `total_premium_sum` for that currency. An unqualified result containing more than one currency returns `total_premium_sum: null` together with `premium_by_currency`, preventing a misleading mixed-currency total. The frontend renders the selected currency through `Intl.NumberFormat` and exposes a clear multi-currency state when no single total is mathematically safe.

## Wizard and parameter-screen behavior

The quotation wizard uses product-scoped payment-frequency choices, fixed enum controls for non-reference values, and registry-backed SmartSelect controls for foreign-key fields. The Manage registry covers identity types, locations, branches, agents, intermediaries, employers, banks, products, plan types, payment frequencies, quote bases, premium factors, member relations, cover types, payment modes, investment funds, fund types, riders, benefit types, and currencies.

The Manage link is deliberately separate from quick-create permission. A user may be permitted to create a minimal option without being permitted to administer the full parameter screen; in that case the plus control may be present but the Manage link is omitted. Internal target paths are not rendered for users who lack a configured permission. Fixed enums such as gender, smoker status, Yes/No feature switches, and benefit basis do not receive Manage or quick-create controls.

When a link is opened from the quotation wizard, the target carries the current wizard return path and active draft identifier. The wizard already persists a local browser snapshot, so parameter changes can be completed in a second authenticated tab without losing the quotation draft. Product Setup and Policy Setup consume their `screen` query parameter so links open the intended tab rather than a generic parent page.

## Document and audit evidence

The unified document tests verify that seeded quotation, proposal, commitment, and receipt scenarios generate PDF responses with the correct content type, page count, source linkage, template version, and branded context. The tests also verify preview and authenticated download behavior, signed-ticket tamper/expiry rejection, permission denial, and the teachable unauthenticated Bearer challenge.

Generation and ticket-download audit rows are checked for actor, document instance, source channel, and template provenance. Option access remains permission-gated and is covered by the backend option-provider tests and request correlation logging. Quick-create mutations use the existing audit framework with source channel `QUICK_CREATE` and reason `Created from OL quotation wizard`. Option and KPI payload assertions use labels and display fields and fail if a bare foreign-key UUID is used as user-facing option text.

## Verification results

| Verification layer | Result |
|---|---:|
| Backend options, quotation, KPI/frequency, unified-document, and audit matrix | **153 passed**, 47 subtests passed |
| SmartSelect route/permission/draft-context suite | **25 passed** |
| Quotation wizard suite | **27 passed** |
| Complete frontend Vitest suite | **59 files / 374 tests passed** |
| Full Chromium Playwright suite | **23 passed, 1 skipped** |
| Frontend strict typecheck | Passed |
| Frontend lint with zero warnings allowed | Passed |
| Frontend production build | Passed |
| Django system validation | Passed |
| Git whitespace validation | Passed |

The single skipped Playwright test is the repository’s explicitly marked legacy receipt-contract test that requires `VITE_USE_MOCKS=false` and a separate live backend contract. The full unified quotation/proposal/commitment print paths passed, including PDF preview, authenticated download, signed-ticket opening, and token-refresh retry. A stale proposal E2E selector was corrected to assert the current unified modal buttons and iframe preview. A pre-existing asynchronous dropdown-configuration assertion was made deterministic by awaiting its option-load call.

## Commands used

```bash
# Backend verification matrix
cd backend
pytest apps/ol_quotations/tests/test_option_registry.py \
       apps/ol_quotations/tests/test_quotations.py \
       apps/documents/tests/test_engine.py \
       apps/governance/test_audit_framework.py

# Frontend unit/integration verification
cd insurance-dashboard-ui
pnpm test -- --run
pnpm typecheck
pnpm lint
pnpm build

# Browser verification
pnpm exec playwright test
```

## Operational guidance

After applying migrations in a fresh environment, run the idempotent OL seed commands so the options registry, product configurations, active document templates, and demonstration data are present. Product payment frequencies are managed in **Ordinary Life Parameters → Product Setup → OL Product**. Choice-backed values such as payment modes, quote bases, premium factors, identity types, and currencies are managed in **Ordinary Life Parameters → Drop Down Configuration**. Riders, beneficial types, funds, locations, branches, and partners remain managed in their authoritative parameter screens.

The final release changes do not flush or reset application data. Existing quotations remain compatible with the legacy summary and option paths, while new frontend code uses canonical KPI, option, document, and product-frequency contracts.
