# OL Quotations Release Guide

## Release scope

This release introduces the Django `ol_quotations` bounded context for Ordinary Life quotation preparation. It provides the quotation header, all seven wizard child structures, lifecycle transitions, immutable event history, standard APIs, admin tables, central audit integration, transactional outbox events, permissions, row-level partner scoping, and idempotent bootstrap.

## Bootstrap

Run the following after deploying the migration:

```bash
cd backend
python manage.py migrate
python manage.py seed_ol_quotations
```

The seed command is safe to run repeatedly. It creates or updates the `ol_quotations` module permissions, role groups, and the `OL_QUOTATION` numbering configuration. Quote numbers are generated through the existing numbering engine and use the configured prefix rather than application-level hardcoding.

## Permission roles

| Role | Permissions |
|---|---|
| `OL_QUOTATION_VIEWER` | View quotations and child records |
| `OL_QUOTATION_OFFICER` | View, create, and update quotations and wizard records |
| `OL_QUOTATION_SUPERVISOR` | Officer access plus finalize, expire, and print |
| `OL_QUOTATION_ADMINISTRATOR` | Full quotation CRUD, configuration, print, and conversion |

The permission namespace is `ol_quotations`. API access also applies the existing partner-link scope for non-superusers.

## Wizard and lifecycle validation

A quotation can be saved as a draft before all wizard steps are complete. Finalization requires a selected plan configuration, a life-assured member, a selected installment configuration, payment details, and underwriting answers. Selected fund allocation percentages must total 100%; beneficiary percentages must total 100% if beneficiaries are entered. Finalization writes the calculation snapshot and totals before changing the status to `FINALIZED`.

Allowed lifecycle transitions are `DRAFT -> FINALIZED`, `DRAFT -> EXPIRED`, and `FINALIZED -> CONVERTED` or `EXPIRED`. Terminal statuses cannot be changed. A quotation cannot be expired before its configured expiry date.

## Validation gates

The release should be accepted only when the following gates pass:

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
pytest -q apps/ol_quotations/tests/
pytest -q
python manage.py seed_ol_quotations
python manage.py seed_ol_quotations
git diff --check
```

The quotation tests cover draft creation, numbering, audit and outbox records, wizard summaries, incomplete-wizard rejection, finalization totals and snapshot, viewer-versus-officer permission separation, structured member validation errors, and model invariants.

## API entry points

The API is available under `/api/v1/ol-quotations/`. The primary frontend flow creates a draft at `/quotations/`, saves each wizard resource independently, reads `/quotations/{id}/wizard-summary/`, and invokes `/quotations/{id}/finalize/` only after all required steps report complete.

## Audit and event operations

Every quotation mutation is recorded by the central audit framework. Lifecycle changes also create immutable quotation event history rows and durable `DomainEvent` outbox records. Consumers should subscribe to the event types `QuotationCreated`, `QuotationUpdated`, `QuotationFinalized`, `QuotationExpired`, and `QuotationConverted` rather than depending on request timing.

## Production assumptions

The release assumes the existing partner authorization and audit middleware are enabled, `DEFAULT_CURRENCY` is configured through system parameters when a non-TZS default is required, and the outbox dispatcher is responsible for publishing pending domain events. The current release does not create policy, claim, payment settlement, or commission transactions; those bounded contexts should consume the quotation snapshot and events through explicit integration contracts.

## Work queue and list contract

The table page reads `GET /api/v1/ol/quotations/quotations/` or the compatibility-equivalent `/api/v1/ol-quotations/quotations/`. The paginated response preserves the standard envelope and returns rows under `data`, with pagination metadata under `pagination`.

Each row exposes `quote_number`, `quote_name`, `prospect_name`, `plans_summary`, `plan_count`, `total_premium`, `currency`, `status`, `status_badge`, `version`, `quote_date`, `agent`, `created_by`, and `row_actions`. The `status_badge` object contains the stable status code, display label, and monochrome-friendly tone key. Each row action includes its HTTP method, URL, permission code, state eligibility, visibility, enabled state, and a reason when unavailable.

| Query capability | Parameters |
|---|---|
| Search | `search` across quote number, quote name, quotation identity number, member identity number, location, partner identity, and agent identity |
| Status | `status`, including comma-separated status codes; expired rows are excluded by default unless `include_expired=true` |
| Plan | `plan` by plan UUID, code, or name |
| Agent | `agent` by agent UUID, username, first name, or last name |
| Location | `location` using case-insensitive partial matching |
| Quote date | `quote_date_from` and `quote_date_to` in `YYYY-MM-DD` format |
| Sorting | `ordering`, including quote number, quote name, quote date, expiry date, status, total premium, version, and timestamps |
| Pagination | `page` and `per_page`, using the shared standard pagination contract |

The KPI endpoint is `GET /api/v1/ol/quotations/quotations/summary/`. It returns `total`, `drafts`, `finalized`, `converted`, and `expired`, scoped to the current user’s authorized partner visibility.

Row actions are state- and permission-aware. `edit` and `delete` are available only for `DRAFT`; `finalize` is available only for `DRAFT`; `revise` is available only for `FINALIZED`; `print` is available for `FINALIZED` and `CONVERTED`; and `convert_to_proposal` is available only for `FINALIZED` quotations with `partner_verified=true`. The API service layer enforces the same rules, so hiding an action in the table is not the security boundary. Revise, print, conversion, finalization, and draft deletion are audited through the central audit framework.

The Django admin quotation table mirrors the work queue with quote number, quote name, prospect, plan summary and count, premium, currency, status, version, quote date, agent, and creator columns. It supports status, currency, quote date, expiry date, product, agent, and location filters plus identity, partner, agent, quote-name, and quote-number search.

The work-queue tests cover table columns, status badges, action visibility by state and permission, identity/plan/agent/location/date search and filtering, invalid date handling, KPI counts, and audit enforcement for print, revise, and deletion actions.
