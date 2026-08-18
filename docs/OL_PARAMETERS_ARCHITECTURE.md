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


## OL Default Setup subcontext

The first concrete parameter group is implemented in `apps.ol_parameters` as the canonical OL Default Setup resource. It contains four table-backed entities and intentionally leaves the legacy `apps.ordinary_life` setup routes unchanged for compatibility. New configuration consumers should use `/api/v1/ol-parameters/`.

| Entity | Purpose | Main scope or behavior |
|---|---|---|
| `OLDefaultSystemParameter` | Typed global defaults for lifecycle, rating, claims, maturity, identification, and commission behavior. | One unique `parameter_key`/`code`, with typed storage and effective dates. |
| `OLOverrideCommissionSetup` | Priority-ordered commission overrides. | Optional partner, intermediary type, product, plan, rider, channel, branch, currency, and year-range dimensions. Same-scope active rows cannot overlap in effective date and premium/policy year ranges. |
| `OLComputationApproach` | Named calculation strategy selected by future product and transaction engines. | Calculation area, basis, formula key, sequence, and JSON configuration. |
| `OLMaturityClaimSetup` | Maturity claim initiation and payout behavior. | Optional product/plan scope, initiation lead time, notification period, documents, approval, payout method, and claim status. |

`OLDefaultSystemParameter` follows the established typed-configuration approach used by the system-parameters app, but uses an OL-specific value catalog: `STRING`, `TEXT`, `INTEGER`, `DECIMAL`, `BOOLEAN`, `DATE`, and `JSON`. The write API accepts one logical `typed_value`, normalizes it into exactly one concrete storage column, and clears stale columns when the value type changes. Reads expose the normalized `value` while retaining the underlying storage columns for diagnostics and controlled administration.

The Default Setup API is table-first and supports list, retrieve, create, update, soft deactivation, search, filters, ordering, pagination, and CSV export:

| Resource | Endpoint |
|---|---|
| Typed OL defaults | `/api/v1/ol-parameters/default-system-parameters/` |
| Commission overrides | `/api/v1/ol-parameters/override-commission-setups/` |
| Computation approaches | `/api/v1/ol-parameters/computation-approaches/` |
| Maturity claim setup | `/api/v1/ol-parameters/maturity-claim-setups/` |

All mutations use the existing `ol_parameters.create`, `ol_parameters.update`, and `ol_parameters.deactivate` permissions, stamp the actor, execute transactionally, and emit central audit events. Admin mutations are also protected by the same permission helper. Physical deletion is not exposed.

The seed command `python manage.py seed_ol_default_setup` is idempotent and provides an operational baseline for currency, premium mode, quotation and proposal validity, first-premium requirement, duplicate-claim behavior, grace and warning periods, maturity claim creation, commission basis, and policy numbering. Seed values are configuration defaults rather than hard-coded business logic; downstream lifecycle and calculation services must resolve active, effective records before execution.

## OL Policy Setup Part 1 subcontext

OL Policy Setup Part 1 is the second concrete parameter group delivered on the foundation. It provides canonical, effective-dated configuration for policy lifecycle and member-cover behavior while leaving transactional policy state and workflow execution in `apps.ordinary_life`.

| Entity | Purpose | Main scope or behavior |
|---|---|---|
| `OLAnticipatedEndowmentInstallmentRate` | Anticipated endowment installment rate/factor rows. | Product/plan, frequency, age, term, policy-year, currency, and effective-date dimensions; nonnegative rates and ordered ranges. |
| `OLGracePeriod` | Premium grace, warning, pre-lapse, and lapse timing. | Optional product/plan and premium-frequency scope, minimum due amount, effective dates, and ordered lifecycle intervals. |
| `OLPolicyStatus` | Policy lifecycle status catalog. | Display order, badge type, terminal flag, and an explicit allowed-transition code list. |
| `OLPolicyRenewalStatus` | Renewal lifecycle status catalog. | Display order, renewal action, and effective dates for renewal processing consumers. |
| `OLBeneficialType` | Beneficiary/benefit/coverage classification. | Category, calculation basis, default ratio, and multiple-allocation behavior. |
| `OLMemberCoverConfiguration` | Member cover eligibility and calculation defaults. | Optional product/plan scope, cover type, member relation, age range, waiting period, limits, premium basis, and coverage basis. |

All six tables use the standard OL parameter lifecycle contract: UUID identity, business code, name, description, active flag, effective dates, actor attribution, timestamps, permission-aware service mutations, and central audit events. The APIs support table list/detail/create/update/deactivate, search, exact filters, ordering, pagination, and CSV export. Policy statuses additionally expose `GET /api/v1/ol-parameters/policy-statuses/validate-transitions/`, which validates that active transition targets exist and are not terminal-transition violations.

The model layer validates product-plan consistency, ordered age/term/year and lifecycle ranges, nonnegative numeric values, active transition targets, and terminal status rules. Effective-dated scoped records use model-level overlap protection where a duplicate active configuration would create ambiguous runtime resolution. The service and serializers execute the same validation contract for API/admin writes.

The idempotent command `python manage.py seed_ol_policy_setup` seeds operational policy and renewal status catalogs, beneficiary types, grace-period and member-cover defaults, six table-registry contracts, and safe starter rows where no product scope is required. The legacy `apps.ordinary_life` setup models and `/api/v1/ordinary-life/setup/` routes remain available unchanged for compatibility; new configuration screens and future consumers should use the canonical `apps.ol_parameters` tables.

## OL Policy Setup Part 2 subcontext

OL Policy Setup Part 2 extends the canonical policy-configuration surface with surrender, paid-up, value-rate, and commitment configuration. It remains configuration-only: policy transactions, servicing actions, surrender processing, paid-up conversion, and commitment execution remain owned by the Ordinary Life transactional domain.

| Entity | Purpose | Main scope or behavior |
|---|---|---|
| `OLSurrenderSetup` | Surrender eligibility, charges, payout timing, and approval behavior. | Optional product/plan scope, minimum premiums/months, minimum premium ratio, charge type/value, partial-surrender flag, payout days, and approval requirement. |
| `OLPaidUpSetup` | Paid-up conversion eligibility and effective timing. | Optional product/plan scope, minimum premiums/months, proportional or fixed conversion basis, eligibility flag, and effective-rule selection. |
| `OLSurrenderValueRate` | Surrender-value factor/rate rows. | Product/optional plan scope, table code/version, gender, smoker status, age/term/policy-year dimensions, row order, effective dates, and nonnegative Decimal rate factor. |
| `OLPaidUpRate` | Paid-up value factor/rate rows. | Product/optional plan scope, table code/version, gender, smoker status, age/term/policy-year dimensions, row order, effective dates, and nonnegative Decimal rate factor. |
| `OLCommitmentStatus` | Commitment lifecycle status catalog. | Status code, display order, applicability, terminal flag, effective dates, and standard active/audit lifecycle fields. |

The setup entities enforce product-plan consistency and prevent ambiguous active effective-dated rows within the same scope. Surrender setup rejects nonzero charges when the charge type is `NONE`; paid-up setup requires at least one eligibility threshold when conversion is allowed; rate rows require a table code or version, validate age/term/policy-year ranges, reject negative factors, and protect against overlapping rows with the same table/version, product/plan, demographic dimensions, and effective date interval.

The Part 2 resources use the shared table-first contract and expose list, retrieve, create, update, soft deactivation, search, filtering, ordering, pagination, and CSV export:

| Resource | Endpoint |
|---|---|
| Surrender setup | `/api/v1/ol-parameters/surrender-setups/` |
| Paid-up setup | `/api/v1/ol-parameters/paid-up-setups/` |
| Surrender-value rates | `/api/v1/ol-parameters/surrender-value-rates/` |
| Paid-up rates | `/api/v1/ol-parameters/paid-up-rates/` |
| Commitment statuses | `/api/v1/ol-parameters/commitment-statuses/` |

All mutations reuse the generic OL Parameters permission contract, actor stamping, atomic persistence, and central audit events. The idempotent `python manage.py seed_ol_policy_setup` command now seeds the Part 1 and Part 2 registry contracts, commitment statuses, global surrender and paid-up defaults, and product-scoped starter rate rows only when an active product is available. Existing `apps.ordinary_life` Policy Setup models and routes remain unchanged for compatibility.

The Part 2 schema is delivered by additive migration `0006_olpaiduprate_olpaidupsetup_olsurrendersetup_and_more.py`. Future Policy Setup parts can reuse the same scoped effective-date and rate-row conventions without changing the registry or API foundation.


## OL Policy Setup Part 3 subcontext

OL Policy Setup Part 3 adds reusable health-questionnaire, grace-notification, and lapse-reinstatement configuration to the canonical OL Parameters bounded context. These records are configuration inputs for future underwriting, policy servicing, notification, and reinstatement workflows; they do not execute medical decisions, send notifications, reinstate policies, or change transactional policy state themselves.

| Entity | Purpose | Main scope or behavior |
|---|---|---|
| `OLHealthQuestion` | Reusable typed health-question catalog. | Question text, category, answer type (`BOOLEAN`, `TEXT`, `NUMBER`, `DATE`, or `CHOICE`), underwriting impact, and medical-follow-up flag. |
| `OLHealthQuestionnaire` | Effective-dated and versioned questionnaire header. | Global, product, plan, or scheme scope; optional sum-assured and age thresholds; unique code/version contract. |
| `OLHealthQuestionnaireItem` | Ordered membership of questions in a questionnaire version. | Positive sequence, mandatory flag, medical-requirement trigger, optional nonnegative score, and unique question/sequence membership per questionnaire. |
| `OLGracePeriodNotificationSchedule` | Notification schedule relative to premium and lapse lifecycle events. | Event type, signed day offset from -3650 to 3650, channel, recipient type, and template code. |
| `OLReinstatementWindow` | Effective-dated lapse-reinstatement eligibility configuration. | Optional product/plan scope, days after lapse, maximum reinstatements, medical underwriting and outstanding-premium requirements, interest rate, and penalty rate. |

The Part 3 model layer rejects blank or unsupported health-question values, invalid questionnaire scopes, inactive referenced products/plans/questions, product-plan mismatches, nonpositive questionnaire sequences, duplicate questionnaire membership, invalid notification offsets, nonpositive reinstatement windows, rates outside 0–100 percent, and overlapping active reinstatement windows in the same scope and effective-date interval. All five entities use UUID identity, standard OL lifecycle fields, actor attribution, effective dating, shared permission checks, and central audit events.

The table-first API exposes the following resources under `/api/v1/ol-parameters/`:

| Resource | Endpoint |
|---|---|
| Health questions | `/health-questions/` |
| Health questionnaires | `/health-questionnaires/` |
| Health questionnaire items | `/health-questionnaire-items/` |
| Grace-period notification schedules | `/grace-period-notification-schedules/` |
| Reinstatement windows | `/reinstatement-windows/` |

Each endpoint supports authenticated list/retrieve/create/update, search, configured filters, ordering, pagination, CSV export, and soft deactivation through the shared OL Parameters viewset contract. Writes invoke model validation, permission-aware service behavior, actor stamping, and audit logging. The five models are explicitly registered with signal-based audit receivers so direct saves from administrative or future application paths are covered as well as API writes.

The idempotent `python manage.py seed_ol_policy_setup` command now seeds five additional registry contracts and safe starter data: one smoking-history question, one global standard underwriting questionnaire, one mandatory questionnaire item, three lifecycle notification schedules, and one global reinstatement window. Registry coverage for Policy Setup is therefore sixteen table contracts across Parts 1–3. Running the command repeatedly uses upsert semantics and does not duplicate configuration rows.

Part 3 is delivered through additive migration `0007_olhealthquestion_olhealthquestionnaire_and_more.py`. The migration preserves all prior OL Parameters and legacy Ordinary Life tables. Future Medical Underwriting, Claim Setup, and policy-servicing modules should resolve active effective-dated Part 3 records through these canonical resources rather than duplicating questionnaire, notification, or reinstatement rules in transactional models.
