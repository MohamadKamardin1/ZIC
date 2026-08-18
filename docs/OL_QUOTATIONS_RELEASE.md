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
