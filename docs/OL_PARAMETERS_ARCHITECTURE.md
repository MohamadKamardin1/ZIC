# Ordinary Life Parameters Architecture

## Purpose and bounded-context boundary

The **Ordinary Life Parameters** bounded context is the configuration foundation for the Ordinary Life insurance domain. It owns reusable parameter lifecycle rules, effective dating, rate-table dimensions, and declarative table metadata. It does not own transactional quotations, proposals, policies, claims, payments, or servicing records. Those transactional contexts consume published parameter contracts and remain responsible for their own state machines and business invariants.

This boundary keeps configuration changes auditable and independently permissioned while allowing the frontend to discover parameter tables without hardcoding every future entity. The foundation is implemented as the isolated Django app `apps.ol_parameters` and is exposed through `/api/v1/ol-parameters/`.

## Application structure

| Layer | Responsibility | Primary location |
|---|---|---|
| App configuration | Django registration and signal initialization | `backend/apps/ol_parameters/apps.py` |
| Domain base models | Shared identity, lifecycle, effective dating, versions, and rate dimensions | `backend/apps/ol_parameters/models.py` |
| Metadata registry | Declarative table contracts for future parameter entities | `OLParameterTableRegistry` |
| Serialization | Stable API representation and JSON metadata validation | `backend/apps/ol_parameters/serializers.py` |
| Application services | Permission-aware mutations and audit emission | `backend/apps/ol_parameters/services/parameter_service.py` |
| API layer | Registry list/retrieve, create/update, deactivation, and health | `backend/apps/ol_parameters/views.py` |
| Admin | Searchable table-first registry maintenance | `backend/apps/ol_parameters/admin.py` |
| Seed utility | Idempotent nine-group table registry bootstrap | `seed_ol_parameter_registry` |
| Tests | Model, registry, permission, API, admin, and audit coverage | `backend/apps/ol_parameters/tests/` |

## Model contracts

`OLParameterBaseModel` is abstract and provides a UUID identity, business code, name, description, active flag, optional effective date range, actor references, and timestamps. It validates non-empty code and name values and rejects an effective-to date earlier than effective-from. Concrete parameter entities should add domain-specific fields and define their own uniqueness constraints where a code must be unique within a particular scope.

`OLEffectiveDateModel` extends the base contract and makes `effective_from` mandatory. `OLRateTableVersionModel` adds a version identifier, supersession link, current-version flag, and publication timestamp. It supports multiple versions under one business code and protects against self-supersession. `OLRateRowBaseModel` is an abstract dimension contract for rate rows and includes product, plan, age, gender, term, effective dates, active state, and display order. It validates age and effective-date ranges.

The base models deliberately do not publish concrete parameter tables in this foundation phase. Each of the nine parameter groups will introduce concrete models in later bounded-context increments, with table registry records describing how those models are rendered and queried.

## Table-metadata registry

`OLParameterTableRegistry` is the frontend-facing table contract. Each row identifies a stable `slug`, a human label, a parameter group, and a `model_label` resource identifier. The JSON metadata fields are intentionally declarative so a Lit-enhanced or React host can render a standard table without embedding model-specific assumptions.

| Registry field | Meaning |
|---|---|
| `visible_columns` | Ordered columns allowed in the standard table, including lifecycle and audit fields where appropriate. |
| `searchable_fields` | Logical fields accepted by table search. |
| `filter_fields` | Logical fields exposed as filters. |
| `default_ordering` | Ordered list of default sort expressions. |
| `allowed_actions` | UI and API actions supported by the resource. |
| `export_support` | Whether the future resource may expose an export operation. |
| `permission_code` | Default permission required to view the resource. |
| `permission_requirements` | Optional per-action permission map, such as create, update, deactivate, and configure. |

Registry records are active by default and can be deactivated rather than physically deleted. The API hides inactive records from ordinary viewers while configuration-authorized users can inspect the full registry.

## Permission contract

The generic module permissions are normalized codes and are also compatible with the existing `User.has_module_permission()` implementation:

| Code | Intended use |
|---|---|
| `ol_parameters.view` | Read active table metadata and future parameter tables. |
| `ol_parameters.create` | Create a parameter or registry record. |
| `ol_parameters.update` | Change parameter metadata or values. |
| `ol_parameters.deactivate` | Deactivate a parameter without destructive deletion. |
| `ol_parameters.configure` | Manage table contracts and inspect inactive registry records. |

Superusers bypass these checks according to the repository IAM convention. Configuration access implies read access so an administrator can inspect the contract being configured. Future submodules may add narrower codes such as `ol_parameters.product_setup.update` while retaining the generic fallback.

## Audit and mutation flow

All service mutations capture a before snapshot where applicable, assign the actor to `created_by` or `updated_by`, persist inside an atomic transaction, and call the central `AuditService`. The audit payload records the model label, object identity, changed fields, reason, source channel, and request correlation data supplied by the existing governance middleware. Signal receivers provide a safety net for registry saves originating from admin or other code paths; service-controlled saves suppress the receiver to prevent duplicate events.

Physical deletion is intentionally not exposed by the registry API or admin. Deactivation is the default lifecycle operation, preserving the metadata contract and its audit history for downstream consumers.

## API contract

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/v1/ol-parameters/health/` | Low-sensitivity readiness response for this bounded context. |
| `GET` | `/api/v1/ol-parameters/tables/` | List active registry records for ordinary viewers; configuration users may see all records. |
| `GET` | `/api/v1/ol-parameters/tables/{id}/` | Retrieve one registry record. |
| `POST` | `/api/v1/ol-parameters/tables/` | Create a registry record with create permission. |
| `PATCH` / `PUT` | `/api/v1/ol-parameters/tables/{id}/` | Update a registry record with update permission. |
| `POST` | `/api/v1/ol-parameters/tables/{id}/deactivate/` | Deactivate a registry record with deactivate permission. |
| `DELETE` | `/api/v1/ol-parameters/tables/{id}/` | Compatibility alias for deactivation; no physical delete is performed. |

The registry endpoint uses the project-wide Django Filter, Search, Ordering, pagination, authentication, and JSON rendering conventions.

## Future submodule integration

A future concrete parameter entity should inherit the appropriate abstract base, add a migration, register a serializer and table endpoint, and add a registry seed record. The entity should retain the standard table fields (`code`, `name`, `description`, `is_active`, effective dates, and audit fields) and publish only active, effective records to transactional consumers. A later publication service may add approval or version activation, but this foundation already supports version headers, supersession, and auditable lifecycle changes.

## Operational assumptions

The repository's existing user and governance applications are the source of truth for authentication, permission storage, actor identity, and audit persistence. The foundation uses UUID identifiers for new configuration records and stores model/resource identifiers as strings in the registry so future parameter tables can be introduced without changing the registry schema. Parameter values themselves are not seeded in this phase; only the table contracts for the nine groups are bootstrapped.
