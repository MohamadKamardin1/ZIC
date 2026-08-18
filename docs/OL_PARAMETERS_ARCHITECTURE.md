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

The base models provide the shared contract for the nine concrete parameter groups now delivered in this bounded context. Each group adds domain-specific models while retaining the common lifecycle, audit, effective-date, permission, and table-registry conventions.

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


## OL Product Setup subcontext

OL Product Setup is now **Implemented** as the first concrete product-configuration group in the canonical OL Parameters bounded context. It owns reusable product and plan configuration contracts consumed by future quotation, proposal, policy, rating, underwriting, investment, and servicing workflows. It does not own transactional products, policy records, investment transactions, or rating execution; those remain in their respective operational contexts.

| Entity | Purpose | Main scope or behavior |
|---|---|---|
| `OLPlanType` | Plan-category catalog. | Effective-dated plan categories such as endowment, whole life, term life, education, pension-linked, and credit-linked. |
| `OLProduct` | Product contract and eligibility configuration. | Plan type, insurance class, currency, age and term limits, sum-assured limits, premium frequencies, product capabilities, and effective dates. |
| `OLPlanTaxConfiguration` | Product/plan tax component configuration. | Tax type and basis, percentage or fixed rate, application event, sequence, country/branch scope, and effective dates. |
| `OLPlanTargetMarket` | Target-market eligibility configuration. | Product/plan scope, market type, age limits, occupation categories, residency requirement, and effective dates. |
| `OLPlanRiskCategory` | Underwriting risk-class configuration. | Product/plan scope, underwriting class, loading basis, and effective dates. |
| `OLPlanOccupationRiskLimit` | Occupation-risk limit and loading configuration. | Product/plan scope, occupation-risk category, maximum sum assured, loading rate, exclusion flag, and effective dates. |
| `OLInvestmentFundType` | Investment fund risk-profile catalog. | Conservative, moderate, aggressive, or other configured fund risk profiles. |
| `OLInvestmentFund` | Investment fund catalog and valuation metadata. | Fund type, currency, valuation frequency, unit price, allocation rules, and effective dates. |

All eight entities use UUID identity, standard OL lifecycle fields, actor attribution, effective dates, generic permission checks, and central audit events. Model validation rejects invalid age, term, sum-assured, tax-rate, loading-rate, unit-price, and scope combinations. Product and plan references are validated for consistency with the operational Ordinary Life domain. Effective-dated scoped configuration rows use overlap protection so two active rows cannot ambiguously govern the same product/plan or global scope.

The table-first API exposes the following resources under `/api/v1/ol-parameters/`:

| Resource | Endpoint |
|---|---|
| Plan types | `/plan-types/` |
| Products | `/products/` |
| Plan tax configurations | `/plan-tax-configurations/` |
| Plan target markets | `/plan-target-markets/` |
| Plan risk categories | `/plan-risk-categories/` |
| Plan occupation-risk limits | `/plan-occupation-risk-limits/` |
| Investment fund types | `/investment-fund-types/` |
| Investment funds | `/investment-funds/` |

Each endpoint supports authenticated list/retrieve/create/update, configured search and filters, ordering, pagination, CSV export, and soft deactivation through the shared OL Parameters viewset contract. Writes use the common parameter service for actor attribution, transactional persistence, model validation, and audit logging. The eight models are explicitly registered with signal-based audit receivers so direct administrative saves are covered alongside API mutations.

The idempotent `python manage.py seed_ol_product_setup` command seeds six plan types, one safe standard endowment product, starter tax/target-market/risk/occupation rows, three investment fund types, one balanced fund, and eight Product Setup registry contracts. Re-running the command updates the declared baseline without duplicating rows. Starter financial values are deliberately conservative configuration placeholders and must be reviewed before production underwriting or investment execution.

Product Setup is delivered through additive migration `0008_olinvestmentfundtype_olinvestmentfund_olplantype_and_more.py`. It remains isolated from the existing `apps.ordinary_life.OLProduct` transactional model: canonical new configuration consumers should resolve Product Setup rows through `apps.ol_parameters`, while legacy operational tables and routes remain available for compatibility and controlled reconciliation.

## OL Product Rating Part 1 subcontext

OL Product Rating Part 1 is now **Implemented** as an isolated, table-first rating configuration surface for Ordinary Life premium rates, mortality rates, and joint-life setup. These records are actuarial inputs for future quotation, proposal, underwriting, and policy calculation services; they do not execute pricing, mortality projection, underwriting decisions, or policy transactions themselves.

| Entity | Purpose | Main scope or behavior |
|---|---|---|
| `OLPremiumRateTable` | Versioned premium-rate table header. | Product and optional plan scope, rating basis, optional currency, version, effective dates, and active lifecycle. |
| `OLPremiumRateRow` | Premium-rate dimension row. | Gender, smoker status, age band, term band, frequency, optional sum-assured band, Decimal rate, and rate unit. |
| `OLMortalityRateTable` | Versioned mortality basis header. | Table code, name, description, version, effective dates, and active lifecycle. |
| `OLMortalityRateRow` | Mortality basis row. | Age, gender, optional smoker status, optional policy year, Decimal mortality rate, and effective dates. |
| `OLJointLifeSetup` | Joint-life product configuration. | Product or optional plan scope, joint-life type, age basis, survivor-benefit rule, premium adjustment factor, underwriting rule, and effective dates. |

All five resources inherit the standard OL parameter identity, actor, timestamp, active-status, and effective-date contract. Premium and mortality rate values use `DecimalField`; percentage and factor validation occurs in model and serializer validation. Age and term bands are inclusive and require lower bounds no greater than upper bounds. A rate row must belong to an active, effective table whose product/plan scope and effective interval contain the row interval. A row cannot overlap another active row in the same table and complete rating dimensions; this prevents ambiguous runtime resolution while allowing adjacent bands and distinct frequencies, genders, smoker statuses, policy years, or sum-assured bands.

The table-first API surface is exposed under `/api/v1/ol-parameters/`:

| Resource | Endpoint | Table behavior |
|---|---|---|
| Premium rate tables | `/premium-rate-tables/` | Header list/detail/create/update/deactivate, product/plan/version/effective-date filters, and CSV export. |
| Premium rate rows | `/premium-rate-rows/` | Dimension list/detail/create/update/deactivate, product/plan delegation filters, age/term/gender/smoker/frequency filters, and CSV export. |
| Mortality rate tables | `/mortality-rate-tables/` | Header list/detail/create/update/deactivate, version/effective-date filters, and CSV export. |
| Mortality rate rows | `/mortality-rate-rows/` | Age/gender/smoker/policy-year filters, list/detail/create/update/deactivate, CSV export, and atomic JSON bulk import. |
| Joint-life setups | `/joint-life-setups/` | Product/plan/type/age-basis filters, list/detail/create/update/deactivate, and CSV export. |

The mortality bulk-import action is `POST /api/v1/ol-parameters/mortality-rate-rows/bulk-import/` with a JSON body containing a `rows` array. Each row is fully validated using the same serializer and model contract as ordinary CRUD; if any row fails validation, the transaction is rolled back and no partial import is retained. CSV export remains available on every Product Rating resource through the shared table viewset behavior.

The idempotent command `python manage.py seed_ol_product_rating` ensures the Product Setup starter product exists, seeds one safe premium table and row, one mortality table and row, one joint-life setup, and five `PRODUCT_RATING` registry contracts. The starter actuarial values are development placeholders and require formal actuarial review and approval before production use. Re-running the command updates the declared baseline without duplicating records.

All five Product Rating models are registered with the central signal-based audit receiver. API and admin mutations use the shared permission-aware OL mutation service, stamp the actor, capture request correlation data, and emit central audit events. Physical deletion is not exposed; deactivation preserves the rating history required for actuarial governance and reproducibility.

Product Rating Part 1 is delivered through additive migrations `0009_olmortalityratetable_olmortalityraterow_and_more.py` and `0010_oljointlifesetup_ol_joint_life_dates_valid_and_more.py`. The implementation remains separate from operational rating execution and can later be consumed by a publication or pricing-resolution service that selects one active table and one unambiguous row for a requested product, plan, age, term, gender, smoker status, frequency, sum assured, and policy year.


## OL Product Rating Part 1 subcontext

OL Product Rating Part 1 is now **Implemented** as the first isolated, table-first actuarial rating configuration surface for Ordinary Life. It covers premium rates, mortality rates, and joint-life configuration. These records are actuarial inputs for future quotation, proposal, underwriting, and policy calculation services; they do not execute pricing, mortality projection, underwriting decisions, or policy transactions themselves.

| Entity | Purpose | Main scope or behavior |
|---|---|---|
| `OLPremiumRateTable` | Versioned premium-rate table header. | Product and optional plan scope, rating basis, optional currency, version, effective dates, and active lifecycle. |
| `OLPremiumRateRow` | Premium-rate dimension row. | Gender, smoker status, age band, term band, frequency, optional sum-assured band, Decimal rate, and rate unit. |
| `OLMortalityRateTable` | Versioned mortality basis header. | Table code, name, description, version, effective dates, and active lifecycle. |
| `OLMortalityRateRow` | Mortality basis row. | Age, gender, optional smoker status, optional policy year, Decimal mortality rate, and effective dates. |
| `OLJointLifeSetup` | Joint-life product configuration. | Product or optional plan scope, joint-life type, age basis, survivor-benefit rule, premium adjustment factor, underwriting rule, and effective dates. |

All five resources use the standard OL parameter identity, actor, timestamp, active-status, and effective-date contract. Premium and mortality values use `DecimalField`; rate, percentage, factor, age, term, policy-year, and scope validation occurs in the model and serializer layers. Age and term bands are inclusive and require lower bounds no greater than upper bounds. A rate row must belong to an active, effective table whose effective interval contains the row interval. Active rows cannot overlap another row with the same table and complete rating dimensions, preventing ambiguous runtime resolution while allowing adjacent bands and distinct frequencies, genders, smoker statuses, policy years, or sum-assured bands.

The table-first API surface is exposed under `/api/v1/ol-parameters/`:

| Resource | Endpoint | Table behavior |
|---|---|---|
| Premium rate tables | `/premium-rate-tables/` | Header list/detail/create/update/deactivate, product/plan/version/effective-date filters, and CSV export. |
| Premium rate rows | `/premium-rate-rows/` | Dimension list/detail/create/update/deactivate, product/plan delegation filters, age/term/gender/smoker/frequency filters, and CSV export. |
| Mortality rate tables | `/mortality-rate-tables/` | Header list/detail/create/update/deactivate, version/effective-date filters, and CSV export. |
| Mortality rate rows | `/mortality-rate-rows/` | Age/gender/smoker/policy-year filters, list/detail/create/update/deactivate, CSV export, and atomic JSON bulk import. |
| Joint-life setups | `/joint-life-setups/` | Product/plan/type/age-basis filters, list/detail/create/update/deactivate, and CSV export. |

The mortality bulk-import action is `POST /api/v1/ol-parameters/mortality-rate-rows/bulk-import/` with a JSON body containing a `rows` array. Each row is validated through the same serializer and model contract as ordinary CRUD. The import is atomic: if any row fails validation, no partial rows are retained. All resources inherit the shared search, filtering, ordering, pagination, authentication, permission, CSV, and soft-deactivation conventions.

The idempotent command `python manage.py seed_ol_product_rating` ensures the Product Setup starter product exists, seeds one development premium table and row, one mortality table and row, one joint-life setup, and five `PRODUCT_RATING` registry contracts. The starter actuarial values are placeholders and require actuarial review and approval before production use. Re-running the command updates the declared baseline without duplicating rows.

All five Product Rating models are registered with the central signal-based audit receiver. API and admin mutations use the shared permission-aware OL mutation service, stamp the actor, capture request correlation data, and emit central audit events. Physical deletion is not exposed; deactivation preserves the rate history required for actuarial governance and reproducibility.

Product Rating Part 1 is delivered through additive migrations `0009_olmortalityratetable_olmortalityraterow_and_more.py` and `0010_oljointlifesetup_ol_joint_life_dates_valid_and_more.py`. The implementation remains separate from operational rating execution and can later be consumed by a publication or pricing-resolution service that selects one active table and one unambiguous row for a requested product, plan, age, term, gender, smoker status, frequency, sum assured, and policy year.


## OL Product Rating Part 2 subcontext

OL Product Rating Part 2 is now **Implemented** as the second isolated actuarial configuration increment for Ordinary Life. It provides effective-dated table-first parameters for reinstatement interest, bonuses, mortgage interest factors, installment charges, cash surrender values, and reserve loadings. These records are configuration inputs for future policy, loan, surrender, reserve, and actuarial calculation services; they do not execute those transactions themselves.

| Entity | Purpose | Main scope or behavior |
|---|---|---|
| `OLReinstatementInterestRate` | Reinstatement interest assumption. | Product or plan scope, calculation basis, Decimal rate, and effective-dated active lifecycle. |
| `OLBonusRate` | Bonus declaration assumption. | Product and plan scope, bonus type, Decimal rate, optional valuation year, declaration frequency, and effective-dated lifecycle. |
| `OLMortgageInterestFactor` | Mortgage or policy-loan interest factor. | Product with optional plan scope, calculation basis, positive Decimal factor, and effective-dated lifecycle. |
| `OLInstallmentChargeRate` | Installment or premium charge configuration. | Optional product/plan scope, frequency, charge type, Decimal value, application event, and effective-dated lifecycle. |
| `OLCashSurrenderValue` | Cash surrender value factor/rate row. | Product and optional plan scope, policy-year, age, term, gender, smoker-status dimensions, and Decimal factor or rate. |
| `OLReserveLoading` | Reserve loading assumption. | Product and optional plan scope, loading type, loading basis, non-negative Decimal value, and effective-dated lifecycle. |

All six entities use the standard OL parameter identity, actor, timestamp, active-status, and effective-date contract. Rates, factors, and loading values are stored as `DecimalField` values. Model and database validation reject negative or out-of-range values, unsupported enum dimensions, invalid effective intervals, missing required product/plan scopes, and invalid age, term, policy-year, or rate bands. Active records cannot overlap another active record with the same scope and actuarial dimensions; adjacent effective periods and distinct dimensions remain valid.

The table-first API surface is exposed under `/api/v1/ol-parameters/`:

| Resource | Endpoint | Table behavior |
|---|---|---|
| Reinstatement interest rates | `/reinstatement-interest-rates/` | Product/plan/basis/effective-date filters, CRUD, pagination, CSV export, and soft deactivation. |
| Bonus rates | `/bonus-rates/` | Product/plan/bonus-type/valuation-year/declaration-frequency filters, CRUD, pagination, CSV export, and soft deactivation. |
| Mortgage interest factors | `/mortgage-interest-factors/` | Product/plan/calculation-basis filters, CRUD, pagination, CSV export, and soft deactivation. |
| Installment charge rates | `/installment-charge-rates/` | Product/plan/frequency/charge-type/application filters, CRUD, pagination, CSV export, and soft deactivation. |
| Cash surrender values | `/cash-surrender-values/` | Product/plan/policy-year/age/term/gender/smoker-status filters, CRUD, pagination, CSV export, and soft deactivation. |
| Reserve loadings | `/reserve-loadings/` | Product/plan/loading-type/loading-basis filters, CRUD, pagination, CSV export, and soft deactivation. |

The idempotent command `python manage.py seed_ol_product_rating_part2` creates six `PRODUCT_RATING` registry contracts and safe development starter rows for each Part 2 resource. It also ensures the Product Setup starter scope exists through the existing seed command. Starter actuarial values are placeholders requiring formal actuarial review and approval before production use; repeated execution updates the declared baseline without duplicating rows.

All six Part 2 models are registered with the central signal-based audit receiver. API and admin mutations use the shared permission-aware OL mutation service, capture actor and correlation metadata, and emit central audit events. Physical deletion is not exposed through the table-first APIs; deactivation preserves the actuarial configuration history needed for reproducibility and governance.

Product Rating Part 2 is delivered through additive migrations following Product Rating Part 1. The implementation remains separate from transactional rating execution and can later be consumed by controlled publication and calculation-resolution services that select one active, unambiguous assumption for a product, plan, event, policy year, demographic profile, and effective date.


## OL Rider Setup subcontext

OL Rider Setup is now **Implemented** as the canonical, table-first rider configuration surface for Ordinary Life. It provides reusable rider definitions and versioned rider rate tables for future quotation, proposal, underwriting, policy, and servicing consumers. The subcontext defines configuration contracts only; it does not attach riders to transactional policies or execute rider pricing.

| Entity | Purpose | Main scope or behavior |
|---|---|---|
| `OLRiderSetup` | Parameterized rider catalog and applicability contract. | Rider category, benefit type, calculation basis, age/term/sum-assured limits, waiting period, standalone and underwriting flags, exclusion JSON, optional product/plan applicability, and effective-dated lifecycle. |
| `OLRiderRateTable` | Versioned rider rate-table header. | Required rider scope, optional product/plan scope, rating basis, version, effective dates, active lifecycle, and referential consistency with rider applicability. |
| `OLRiderRateRow` | Multi-dimensional rider rate row. | Gender, smoker status, age band, term band, frequency, optional sum-assured band, Decimal rate, rate unit, effective dates, and active lifecycle. |

Rider definitions enforce ordered age and term bands, age limits from 0 through 150 years, nonnegative and ordered sum-assured limits, effective-date consistency, supported enum values, active product/plan references, and product-plan consistency. Rate tables require an active rider and remain aligned with any product or plan applicability declared by that rider. Rate rows require an active, effective parent table, inclusive ordered age and term bands, nonnegative Decimal rates, supported rate units, and ordered sum-assured bands. Active rows cannot overlap another row in the same table, gender, smoker status, frequency, rate unit, effective-date interval, and age/term/sum-assured dimensions; adjacent bands and distinct dimensions remain valid.

The table-first API surface is exposed under `/api/v1/ol-parameters/`:

| Resource | Endpoint | Table behavior |
|---|---|---|
| Rider setups | `/rider-setups/` | Rider catalog CRUD, category/benefit/product/plan/eligibility filters, search, ordering, pagination, CSV export, and soft deactivation. |
| Rider rate tables | `/rider-rate-tables/` | Versioned table-header CRUD, rider/product/plan/rating-basis/version filters, search, ordering, pagination, CSV export, and soft deactivation. |
| Rider rate rows | `/rider-rate-rows/` | Dimension-row CRUD, table/rider/gender/smoker/frequency/rate-unit/age/term filters, search, ordering, pagination, CSV export, and soft deactivation. |

All three resources use `ol_parameters.view`, `.create`, `.update`, `.deactivate`, and `.configure` through the shared permission-aware mutation service. API and admin mutations stamp actor references and emit central audit events; the three models are explicitly registered with the signal-based audit receiver so direct administrative saves are also covered. Physical deletion is not exposed and deactivation preserves actuarial configuration history.

The idempotent command `python manage.py seed_ol_rider_setup` ensures the Product Setup starter product exists, seeds one development accidental-death rider, one versioned rider rate table, one rider rate row, and three `RIDER_SETUP` registry contracts. Starter actuarial values and exclusion rules are placeholders requiring actuarial and underwriting approval before production use; repeated execution updates the declared baseline without duplicating rows.

Rider Setup is delivered through additive migration `0013_olridersetup_olriderratetable_olriderraterow_and_more.py`. Future quotation and policy consumers should resolve the active rider definition first, then select one unambiguous rate table and rate row for the requested rider, product, plan, demographic profile, frequency, age, term, sum assured, and effective date.

## OL Agent Management implementation status
OL Agent Management is now **Implemented** as the sixth concrete OL Parameters group. It provides a table-driven commission configuration foundation for first-premium, renewal, administrative, hierarchical, override, and future commission types without coupling configuration to commission settlement transactions.

| Requirement | Delivered artifact | Status |
|---|---|---|
| Agent commission setup | `OLAgentCommissionSetup` with optional partner, intermediary type, distribution channel, product, plan, rider, currency, branch, commission type, premium/policy-year bands, rate type, rate value, commission caps, priority, reason, and effective dates | Implemented |
| Commission scope | Product/plan/rider/channel/intermediary/currency/branch dimensions are persisted as data and exposed for future commission calculation services | Implemented |
| Validation and invariants | Required product and channel scope, normalized choice values, three-letter currency validation, percentage upper bound, nonnegative Decimal values, minimum/maximum ordering, year-band ordering, effective-date consistency, product/plan and rider/product alignment, and active scoped overlap prevention | Implemented |
| APIs | `/api/v1/ol-parameters/agent-commission-setups/` with CRUD, search, filters, ordering, pagination, CSV export, and soft deactivation | Implemented |
| Permissions | Existing `ol_parameters.view`, `.create`, `.update`, `.deactivate`, and `.configure` enforcement through the shared OL parameter permission class | Implemented |
| Admin | Permission-aware, table-first admin registration showing partner, product/plan, commission type, rate, priority, channel, effective dates, and active status | Implemented |
| Audit | Central audit receiver registration for `OLAgentCommissionSetup` plus shared mutation-service and request-correlation audit behavior | Implemented |
| Seed data | `seed_ol_agent_management` idempotently seeds a development starter commission rule and one `AGENT_MANAGEMENT` registry contract; it ensures the standard product and starter rider prerequisites exist | Implemented |
| Tests | CRUD, filtering, CSV export, deactivation, rate/currency/year/date validation, overlap prevention, non-overlapping periods, permissions, audit correlation, seed idempotency, and admin registration | Implemented |
| Migrations | Additive migration `0014_olagentcommissionsetup_and_more.py` with uniqueness, nonnegative-rate, year-order, cap-order, scope, priority, and product/type indexes | Implemented |

The Agent Management increment is intentionally configuration-only. Starter commission values are development placeholders and require commercial, actuarial, compliance, and governance approval before production calculation or settlement services consume them.

## Updated nine-group status after OL Agent Management
| Required group | Concrete implementation status after this delivery |
|---|---|
| OL Default Setup | **Implemented** |
| OL Policy Setup | **Parts 1, 2, and 3 implemented**; later policy setup parts remain planned |
| OL Product Setup | **Implemented** |
| OL Product Rating | **Parts 1 and 2 implemented**: premium, mortality, joint life, reinstatement, bonus, mortgage, installment, surrender, and reserve parameters |
| OL Rider Setup | **Implemented**: rider catalog, applicability rules, rider rate tables, and rider rate rows |
| OL Agent Management | **Implemented**: effective-dated agent commission setup with scoped rates, priorities, caps, and overlap protection |
| OL Loan Setup | **Implemented**: effective-dated loan system setup and interest control |
| OL Medical / Underwriting | **Implemented**: medical codes, limits, personal habits, medical history, facilities, and practitioners |
| OL Claim Setup | Foundation registry only; planned |


## OL Loan Setup — implemented

OL Loan Setup provides the table-driven policy-loan configuration foundation required by future Ordinary Life loan transactions. It is split into two independently versioned, effective-dated resources so eligibility and loan limits can evolve separately from interest and capitalization behavior.

| Resource | Model and configuration contract |
|---|---|
| Loan system setup | `OLLoanSystemSetup` stores optional product/plan scope, `allow_policy_loans`, loan basis (`CASH_VALUE`, `PAID_UP_VALUE`, `PREMIUM_BASED`, `OTHER`), maximum percentage of cash value, minimum and maximum loan amounts, optional three-letter loan currency, repayment-options JSON, benefit deduction behavior, claim/surrender/maturity effect rules, approval requirement, lifecycle state, and effective dates. |
| Loan interest control | `OLLoanInterestControl` stores optional product/plan scope, Decimal interest rate, compounding frequency, interest calculation basis, grace-period days, optional penalty interest rate, suspension rule text, capitalization behavior, lifecycle state, and effective dates. |

Both models inherit the common OL effective-date/audit base. Product-level, plan-level, and global configurations are represented by nullable scope foreign keys. An active record with the same product/plan scope cannot overlap another active record of the same resource in effective dates. This keeps precedence deterministic for downstream loan transaction services while allowing different scopes to coexist.

### APIs and table contracts

The API resources are available under `/api/v1/ol-parameters/`:

| Endpoint | Supported behavior |
|---|---|
| `loan-system-setups/` | CRUD, soft deactivation, CSV export, search, filters by product/plan/status/loan basis/currency/behavior, pagination, and ordering. |
| `loan-interest-controls/` | CRUD, soft deactivation, CSV export, search, filters by product/plan/status/compounding/calculation basis/capitalization, pagination, and ordering. |

The table registry seed creates `loan-system-setups` and `loan-interest-controls` under parameter group `LOAN_SETUP`, with visible columns, searchable fields, filter fields, default ordering, permission requirements, and export support.

### Validation and audit

Validation enforces Decimal rate fields, a 0–100 percentage range for cash-value loan limits and interest rates, positive loan amounts when supplied, minimum/maximum amount ordering, three-letter currency codes, supported behavior choices, supported compounding and calculation bases, JSON object/array repayment options, required effective-from dates, effective-date ordering, and active scope overlap prevention. Database check constraints and indexes reinforce the most important range and query invariants.

All create and update mutations are registered with the central OL Parameters signal audit receiver and therefore capture actor, before/after state, changed fields, source context, and correlation identifiers through the existing governance audit service. The viewsets use the established OL parameter permission contract: `ol_parameters.view`, `ol_parameters.create`, `ol_parameters.update`, `ol_parameters.deactivate`, and `ol_parameters.configure`.

### Seed, migration, and tests

The idempotent command `python manage.py seed_ol_loan_setup` ensures the `STANDARD_ENDOWMENT` product prerequisite, creates development starter rows for policy-loan behavior and annual compound interest, and upserts both registry contracts. Starter values are placeholders and require actuarial, product, legal, compliance, and governance approval before production loan calculations or settlement use them.

The additive migration `0015_olloansystemsetup_olloaninterestcontrol_and_more.py` creates both models, constraints, and indexes. Focused tests in `backend/apps/ol_parameters/tests/test_loan_setup.py` cover both CRUD surfaces, filtering, CSV export, deactivation, invalid percentages and amounts, unsupported choices, effective-date consistency, scope overlap prevention, permission enforcement, audit correlation, seed idempotency, and admin table registration.

### Design assumptions

The implementation treats `ol_parameters.OLProduct` as the canonical product relation used by the newer parameter groups and retains the established optional `ordinary_life.OLPlan` relation for plan-level overrides. A null product and null plan represent a global default. Repayment options and interest suspension behavior are intentionally data-driven JSON/text fields at this foundation stage; a future loan transaction module can promote these into normalized workflow tables without changing the effective-dated setup API contract.


## OL Medical Underwriting — implemented

OL Medical Underwriting provides the table-driven configuration foundation required by future quotation, proposal, policy, medical-evidence, and underwriting-decision workflows. The group separates reusable medical catalogs from effective-dated product and plan limits and from approved medical service-provider catalogs.

| Resource | Model and configuration contract |
|---|---|
| Medical codes | `OLMedicalCode` stores reusable medical examination, evidence, and underwriting codes with category, description, active status, and effective dates. |
| Medical limits | `OLMedicalLimit` stores medical or financial evidence limits by medical code, optional product/plan, age band, sum-assured band, limit type, limit amount, required frequency, mandatory flag, and effective dates. |
| Personal habits | `OLPersonalHabit` stores configurable habit questions with category, question text, underwriting impact, evidence requirement, active status, and effective dates. |
| Medical history | `OLMedicalHistory` stores condition catalogs with category, severity, waiting period, exclusion/loading flags, underwriting notes, active status, and effective dates. |
| Medical facilities | `OLMedicalFacility` stores approved facility catalogs with optional Partner master linkage, facility code/type, registration, location, contact details, approval status, active status, and effective dates. |
| Medical practitioners | `OLMedicalPractitioner` stores approved practitioner catalogs with optional Partner and facility linkages, practitioner code, names, specialty, license, contact details, approval status, active status, and effective dates. |

### APIs and table contracts

The six table-first API resources are available under `/api/v1/ol-parameters/`:

| Endpoint | Supported behavior |
|---|---|
| `medical-codes/` | CRUD, soft deactivation, CSV export, search, category/status/date filters, pagination, and ordering. |
| `medical-limits/` | CRUD, soft deactivation, CSV export, search, code/product/plan/type/frequency/dimension/status filters, pagination, and ordering. |
| `personal-habits/` | CRUD, soft deactivation, CSV export, search, habit category/impact/evidence/status filters, pagination, and ordering. |
| `medical-history/` | CRUD, soft deactivation, CSV export, search, condition/severity/waiting-period/exclusion/loading/status filters, pagination, and ordering. |
| `medical-facilities/` | CRUD, soft deactivation, CSV export, search, Partner/facility type/approval/location/status filters, pagination, and ordering. |
| `medical-practitioners/` | CRUD, soft deactivation, CSV export, search, Partner/facility/specialty/approval/status filters, pagination, and ordering. |

All resources use `ol_parameters.view`, `.create`, `.update`, `.deactivate`, and `.configure` through the shared permission-aware OL parameter viewset. Physical deletion is not exposed; deactivation preserves configuration history.

### Validation and audit

Validation normalizes catalog codes and choice values, requires medical categories, habit questions, history categories and severities, practitioner identity and license fields, and facility codes and types. Medical limits enforce age bounds from 0 to 150, ordered age and sum-assured ranges, positive limit amounts, supported limit types and evidence frequencies, active medical-code/product/plan references, product-plan ownership, effective-date consistency, and active overlap prevention for the same medical code, product/plan scope, limit type, required frequency, age band, sum-assured band, and effective period.

Facility and practitioner Partner references are optional but, when supplied, must be active and use the repository’s medical-service classifications (`SERVICE_PROVIDER`, `MEDICAL_FACILITY`, or `MEDICAL_PROVIDER` for facilities; `SERVICE_PROVIDER` or `MEDICAL_PRACTITIONER` for practitioners). Practitioner facility references must be active. Database constraints and query indexes reinforce code uniqueness, range ordering, positive amounts, and common table filters.

All six models are registered with the central signal-based audit receiver. Create, update, deactivation, and administrative mutations therefore capture actor, before/after state, changed fields, source context, and correlation identifiers through the existing governance audit framework.

### Seed, migration, and tests

The idempotent command `python manage.py seed_ol_medical_underwriting` ensures the `STANDARD_ENDOWMENT` product prerequisite, creates one development starter row for each medical resource, and upserts six `MEDICAL_UNDERWRITING` registry contracts. Starter medical codes, limits, questions, conditions, facilities, and practitioners are placeholders requiring underwriting, medical, actuarial, legal, compliance, and governance approval before production use.

The additive migration `0016_olmedicalcode_olmedicalfacility_olmedicalhistory_and_more.py` creates the six models, foreign keys, constraints, and query indexes. Focused tests in `backend/apps/ol_parameters/tests/test_medical_underwriting.py` cover CRUD, filtering, CSV export, deactivation, range and amount validation, overlap prevention, active Partner linkage, permission enforcement, audit correlation, seed idempotency, and admin table registration.

### Design assumptions

The implementation treats `ol_parameters.OLProduct` as the canonical product relation and retains the optional `ordinary_life.OLPlan` relation for plan-level medical limits. A null product and null plan represent a global medical rule. Medical facilities and practitioners link to the existing Partner master without duplicating partner identity data; the medical catalog stores only underwriting-specific facility and practitioner attributes. Medical history and personal-habit outcomes remain configuration inputs at this stage, while future underwriting decision services may add normalized outcomes, referral rules, and case-level evidence transactions.


## OL Claim Setup — implemented

OL Claim Setup provides the table-driven claim configuration foundation for future Ordinary Life claims intake, assessment, approval, settlement, discharge, and correspondence workflows. The increment is configuration-only and does not introduce claim transaction processing.

### Claim Type Configuration

`OLClaimType` defines claim categories for death, critical illness, disability, surrender, maturity, medical, and other events. Each row supports calculation basis, duplicate-check rule, optional waiting period, payable-to rules, required document codes, waiver-of-premium behavior, approval requirement, effective dates, active status, and inherited audit attribution.

### Claim Reason Catalog

`OLClaimReason` provides reusable reason codes and descriptions, optionally scoped to an active `OLClaimType`. Reason categories include event, medical, administrative, financial, documentary, and other reasons.

### Claim Status Catalog

`OLClaimStatus` defines the claim workflow status catalog with display order, badge type, terminal/payable flags, and a JSON directed transition graph. Transition targets must exist and be active; duplicate/self transitions are rejected, and terminal statuses cannot have outgoing transitions. Runtime helpers `can_transition_to()` and `validate_transition_to()` provide the future claims engine with a stable transition contract.

The seeded status sequence includes Registered, Documents Pending, Under Assessment, Pending Approval, Approved, Rejected, Payment Pending, Settled, and Closed.

### Discharge Type Catalog

`OLDischargeType` defines settlement discharge/release document types with discharge category, template code, JSON template variables, effective dates, active status, and audit fields. Template variables are validated as JSON objects for future document rendering.

### Correspondence Type Catalog

`OLCorrespondentType` models correspondence templates and purposes. It supports correspondence category, communication channel (Letter, Email, SMS, Portal, WhatsApp, System, or Other), purpose, lifecycle, and audit data for future notification and claim communication services.

### APIs and Administration

The following resources are registered under `/api/v1/ol-parameters/`:

- `claim-types/`
- `claim-reasons/`
- `claim-statuses/`
- `discharge-types/`
- `correspondent-types/`

Each resource uses the shared OL parameter viewset contract for list, retrieve, create, update, soft deactivation, search, filters, ordering, pagination, and CSV export. Supported filters are aligned to each table’s principal category, lifecycle, relationship, and workflow fields. Django admin provides permission-aware, table-first screens with list columns, filters, search, fieldsets, and audit fields.

### Validation, Audit, and Seed Evidence

All five models use unique code constraints, active/effective lifecycle fields, normalized choice values, database indexes, and model-level `full_clean()` validation. Claim type JSON fields distinguish payable-to objects from required-document arrays. Discharge variables must be JSON objects. Claim status transitions are validated against the active status catalog and cannot create an invalid directed graph.

All five models are registered in `backend/apps/ol_parameters/audit_receivers.py` for central create, update, delete, and lifecycle audit coverage. The idempotent `seed_ol_claim_setup.py` command registers five `CLAIM_SETUP` table contracts and seeds representative claim types, reasons, statuses, discharge templates, and correspondence types.

Focused coverage is provided by `backend/apps/ol_parameters/tests/test_claim_setup.py`, including CRUD for every catalog, filtering/export, deactivation, JSON/category/date validation, status transition consistency, unique-code enforcement, permissions, audit correlation, seed idempotency, and admin table configuration. Migration `0017_olclaimtype_olclaimreason_olcorrespondenttype_and_more.py` provides the additive database schema, uniqueness constraints, waiting-period constraint, indexes, and foreign-key relationship.

The starter records are development configuration placeholders. Claim calculation rules, legal discharge language, approval authorities, transition governance, and correspondence templates require claims, actuarial, legal, compliance, product, and governance approval before production claims workflows consume them.

## Updated nine-group status after OL Claim Setup

| Required group | Status | Evidence |
|---|---|---|
| OL Default Setup | Implemented | Models, APIs, admin, seed, tests, and documentation |
| OL Policy Setup | Parts 1, 2, and 3 implemented | Policy setup models, APIs, seed, tests, and documentation |
| OL Product Setup | Implemented | Product and supporting table-driven configuration resources |
| OL Product Rating | Parts 1 and 2 implemented | Premium, mortality, joint-life, reinstatement, bonus, mortgage, installment, surrender, and reserve resources |
| OL Rider Setup | Implemented | Rider catalog, applicability controls, rate tables, rows, seed, tests, and migration 0013 |
| OL Agent Management | Implemented | Agent commission setup, seed, tests, audit registration, and migration 0014 |
| OL Loan Setup | Implemented | Loan system setup and loan interest control, seed, tests, audit registration, and migration 0015 |
| OL Medical / Underwriting | Implemented | Six medical underwriting resources, seed, tests, audit registration, and migration 0016 |
| OL Claim Setup | Implemented | Five claim catalogs, status transition graph, seed, tests, audit registration, and migration 0017 |


## OL Parameters release-hardening contract

The nine-group OL Parameters foundation is released through one idempotent bootstrap command:

```text
python manage.py seed_ol_parameters_release
```

The command executes the group seed commands in dependency order, then provisions canonical permissions and role groups, and finally upserts the nine top-level table registry contracts. Component-level registry records remain available for detailed tables inside groups; the nine canonical records use the stable `ol-*` slugs and are the release-level discovery surface.

| Release concern | Canonical contract |
|---|---|
| Group bootstrap | Default Setup, Policy Setup, Product Setup, Product Rating, Rider Setup, Agent Management, Loan Setup, Medical Underwriting, and Claim Setup are all executed by the release orchestrator. |
| Permission bootstrap | `ol_parameters.view`, `ol_parameters.create`, `ol_parameters.update`, `ol_parameters.deactivate`, and `ol_parameters.configure` are seeded idempotently. |
| Role bootstrap | `OL_PARAMETER_VIEWER`, `OL_PARAMETER_CONFIGURATOR`, and `OL_PARAMETER_ADMINISTRATOR` are system groups with deterministic permission sets. |
| Registry bootstrap | Nine canonical top-level records expose valid `model_label`, visible columns, searchable fields, filter fields, ordering, export support, allowed actions, and per-action permissions. |
| Readiness | `/api/v1/ol-parameters/health/` reports operational counts for all nine groups and the active registry contract count. |
| Auditability | All concrete group models are connected to the central audit receiver; lifecycle mutations use the shared actor, correlation, and source-channel context. |
| API consistency | Each concrete resource uses the common authenticated OL viewset contract for search, filtering, ordering, pagination, CSV export, create/update, and soft deactivation. |

The seeded viewer role is intentionally read-only. The configurator role can create and update configuration but cannot deactivate it. The administrator role has full lifecycle and registry configuration access. Production deployments should map these system roles to approved organizational groups through the existing IAM governance process rather than granting permissions directly to individual users.

Release seeds contain development-safe starter values only. Product, actuarial, underwriting, claims, legal, compliance, finance, reinsurance, and governance owners must approve production values, effective dates, rates, limits, workflow transitions, templates, and partner references before transactional consumers use them.

The release hardening suite validates canonical registry completeness, idempotent bootstrap, seeded role resolution, read-only viewer behavior, representative endpoint access across all nine groups, readiness observability, permission uniqueness, and metadata field contracts. These tests are cross-cutting safeguards in addition to each group’s focused CRUD and validation suite.

## OL Parameters release operating checklist

Before promoting a release, apply migrations, execute `seed_ol_parameters_release`, verify the health endpoint, review active effective-dated configuration, confirm role assignments, and inspect the audit stream for seed and administrative changes. SQLite is a development database only; production deployments must use the supported PostgreSQL schema and deployment migration process. No seed command performs destructive deletion.
