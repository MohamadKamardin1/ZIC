# Ordinary Life Quotations Architecture

## Purpose and bounded-context boundary

The `ol_quotations` application is the transactional quotation foundation for Ordinary Life business. It owns quotation drafts, wizard child records, quotation lifecycle history, calculation snapshots, and the integration events needed by future proposal, policy, payment, and reporting bounded contexts.

The application deliberately consumes parameterized product, plan, rider, and fund configuration from `ol_parameters` and existing Ordinary Life product-version structures. It does not copy actuarial tables into quotation rows and does not create policy or claim records. Quotation data captures the customer-specific selection and underwriting inputs used to create a reproducible quotation snapshot.

## Seven-step wizard contract

A quotation is a draft aggregate completed through seven independently saveable steps:

| Step | Resource | Completion rule |
|---|---|---|
| 1 | `OLQuotation` Personal Details | Quote identity, date of birth, age, gender, smoker status, location, agent, and address pass validation |
| 2 | `OLQuotationPlanConfiguration` | At least one selected product/plan configuration with valid term, payment period, frequency, quote basis, and positive maturity/base amounts |
| 3 | `OLQuotationMember` | At least one member and at least one `LIFE_ASSURED` |
| 4 | `OLQuotationInstallmentConfiguration` | At least one selected installment configuration |
| 5 | `OLQuotationFundAllocation` | Not applicable when no selected plan is investment-linked; otherwise every applicable plan must have allocations totaling 100% |
| 6 | `OLQuotationRiderSelection` | Optional rider selections driven by OL Rider Setup |
| 7 | `OLQuotationPaymentDetail` and `OLQuotationUnderwriting` | One payment detail record and one underwriting answer record |

The `wizard-summary` endpoint exposes the completion state without requiring the frontend to duplicate domain rules. Child resources are independently listable, filterable, paginated, and editable while the quotation remains in `DRAFT` status.

The Personal Details step is saved through `POST` or `PATCH /quotations/{id}/personal-details/`. It computes `age_at_quote` from `date_of_birth` and `quote_date`, rejects future or out-of-range dates, validates all select values against active system choice lists, validates active configured locations and agent partner assignments, and returns a warning when another active quotation uses the same identity and date-of-birth combination. A matching active partner with an active assignment and verified KYC is reported through `partner_exists`, `partner_id`, and `compliant`; the step links that partner but never creates a new partner record.

The Plan Selection step is driven by active `ordinary_life.OLProductVersion` and `OLPlan` records. The plan search endpoint returns product/plan cards with codes, descriptions, payment frequencies, entry-age and term limits, and capability badges derived from OL Product Setup and effective-dated OL Parameters. A selection request preserves the submitted order as `section_number` values, upserts selected plan configurations, deselects prior rows not in the new selection, and marks `2_plan_and_sub_products` complete. Each section can subsequently be patched for policy term, payment period, frequency, quote basis, maturity value, premium factor, optional feature toggles, bonus rate, and base sum assured. Every mutation is restricted to draft quotations and records an audit event plus a transactional outbox event.

The Member Coverage step is resolved from effective `OLMemberCoverConfiguration` rows for the selected product and plan scopes. `GET /quotations/{id}/members/` always synchronizes one immutable principal `LIFE_ASSURED` member from Personal Details and returns the principal card, configured additional relations, waiting periods, benefit limits, and the `requires_additional_coverage` flag. When no non-principal member-cover configuration applies, the endpoint returns the exact informational banner required by the screen and does not permit dependent creation. When additional coverage is configured, `POST` adds a dependent and `PATCH` or `DELETE` on the member detail route updates or removes only dependents. Relation eligibility, age, duplicate identity, coverage basis, and benefit limits are enforced against the selected configuration; principal changes must be made through Personal Details. Successful dependent mutations mark `3_member_coverage` complete, write central audit records, and emit `QuotationMemberCoverageUpdated` outbox events.

The Installments step is exposed through `GET /quotations/{id}/installments/`, `GET /quotations/{id}/installments/{plan_configuration_id}/template/`, and `POST /quotations/{id}/installments/{plan_configuration_id}/configure/`. The state endpoint returns one table row per selected plan configuration, including inherited policy term, payment mode, total installment count, `READY_TO_CONFIGURE` or `CONFIGURED` status, and whether configuration is still required. Template loading resolves effective `OLAnticipatedEndowmentInstallmentRate` rows for the selected legacy product/plan, term, age, frequency, and quote date; if no applicable rows exist, it returns `has_template=false` and the manual-configuration banner. Paid-up values are resolved from effective `OLPaidUpRate` rows using the same product/plan and term/age/policy-year scope, with plan-specific rows taking precedence over product-level fallback rows.

Configuration stores the annuity period, parameter-backed payment mode, maturity-benefit toggles, and ordered rate rows. The documented computation assumption is `total_number_of_installments = len(rate_rows)`; the persisted configuration therefore reports the number of saved allocation rows rather than deriving a payment count from frequency alone. Rate percentages must sum exactly to `100`, each sequence must be unique, the annuity period must be positive and no greater than the inherited policy term, and the selected payment mode must be present in the product-version payment frequencies. If the selected plan or product rules require installment benefits, at least one maturity toggle must be selected. The inherited policy term and installment amount are server-controlled; a positive estimated maturity value must exist before a new configuration can be saved. Successful saves mark wizard completion under the key `4_installments`, increment the quotation version, write an audit/outbox event, and transition the plan row from `READY_TO_CONFIGURE` to `CONFIGURED`.

The Investment Funds step is exposed through `GET /quotations/{id}/investment-funds/`, `GET /quotations/{id}/investment-funds/options/`, and `POST /quotations/{id}/investment-funds/`. Applicability is resolved from the selected plan/product capability configuration: non-investment-linked plans return `not_applicable=true` and do not require allocation rows, while every selected investment-linked plan must be configured independently. The options endpoint returns only active, effective `OLInvestmentFund` rows whose active `OLInvestmentFundType` includes the fund type, risk profile, currency, and valuation frequency metadata. No fund catalog is hardcoded in the quotation module.

Allocation requests carry `plan_config_id`, `fund_id`, `allocation_percent`, and an optional `allocated_amount`. Percentages are validated per plan configuration and must sum exactly to `100`; duplicate funds within a plan, inactive or expired funds, inactive fund types, and incompatible currencies are rejected. A fund with a different currency is selectable only when its parameter `allocation_rules` explicitly allows the quotation currency or enables currency conversion. Successful saves replace the selected allocation set transactionally, mark wizard completion under `5_investment_funds`, increment the quotation version, and emit central audit and `QuotationInvestmentFundAllocationsUpdated` outbox records. State responses expose one row per selected plan with `NOT_APPLICABLE`, `READY_TO_CONFIGURE`, or `CONFIGURED` status and the persisted allocation snapshot.

The Riders and Benefits step is exposed through `GET /quotations/{id}/riders/`, `GET /quotations/{id}/riders/options/`, and `POST /quotations/{id}/riders/`. Rider options are resolved from effective, active `OLRiderSetup` records and filtered by the selected product/plan scope, entry age, policy term, and base sum assured. The response includes rider code, name, category, benefit type, applicability ranges, waiting period, underwriting requirement, standalone support, and the active `OLBeneficialType` catalog; no rider or benefit option is hardcoded in the quotation module.

A rider selection stores plan ownership, rider sum assured, optional rider term, parameter benefit type, benefit basis, value, loading, discount, maximum cap, and optional nested benefit configurations. `FIXED` benefits require a non-negative value, `RATIO` values must be greater than zero and no greater than 100 percent, `CAPPED` benefits require a maximum cap that is not below the value, and loading/discount percentages are bounded from 0 to 100. Rider age, term, sum-assured, active/effective-date, duplicate, and standalone rules are enforced against the selected `OLRiderSetup`. The Plan & Sub-Products PA and WP toggles are synchronized to matching parameter riders (`PERSONAL_ACCIDENT` and `PREMIUM_WAIVER`) during save, while explicitly submitted rider selections remain parameter-validated. Successful saves replace the selected rider/benefit set transactionally, mark wizard completion under `6_riders_and_benefits`, increment the quotation version, and emit central audit and `QuotationRidersAndBenefitsUpdated` outbox records.

## Domain model and invariants

`OLQuotation` is the aggregate header. It stores the canonical quote number, partner, parameter-backed product, optional legacy product version, currency, expiry date, status, totals, calculation snapshot, and metadata. The quote number is generated by the existing numbering engine using `OL_QUOTATION`; currency defaults through the existing `DEFAULT_CURRENCY` system parameter and is normalized to an ISO-like three-letter code.

The aggregate supports the following lifecycle:

| Current status | Allowed next statuses |
|---|---|
| `DRAFT` | `FINALIZED`, `EXPIRED` |
| `FINALIZED` | `CONVERTED`, `EXPIRED` |
| `CONVERTED` | None |
| `EXPIRED` | None |

Finalization locks the quotation into a reproducible calculation state. It validates the wizard, calculates selected plan and rider totals, writes `total_sum_assured` and `total_premium`, and stores the selected child identifiers and calculation currency in `calculation_snapshot`. Conversion is intentionally a future integration hook and does not yet create a policy.

All financial values use `DecimalField`, date ranges reject an expiry date before the quote date, member ages are derived at the quote date, allocation percentages are bounded from 0 to 100, installment rate periods cannot overlap, and beneficiary percentages must total 100% when beneficiaries are supplied.

## API surface

The API is mounted under `/api/v1/ol-quotations/`.

| Resource | Endpoint |
|---|---|
| Quotations | `/quotations/` |
| Plan configurations | `/plan-configurations/` |
| Members | `/members/` |
| Installments | `/installments/` |
| Installment rate rows | `/installment-rate-rows/` |
| Fund allocations | `/fund-allocations/` |
| Rider selections | `/rider-selections/` |
| Payment details | `/payment-details/` |
| Underwriting | `/underwriting/` |
| Beneficiaries | `/beneficiaries/` |
| Immutable quotation events | `/events/` |
| Plan search | `GET /api/v1/ol/plans/search/` |
| Plan configurations | `POST /quotations/{id}/plans/` |
| Plan options | `GET /quotations/{id}/plan-options/` |
| Plan section configuration | `PATCH /quotations/{id}/plans/{configuration_id}/` |
| Member Coverage state | `GET /quotations/{id}/members/` |
| Installments state | `GET /quotations/{id}/installments/` |
| Installment template | `GET /quotations/{id}/installments/{plan_configuration_id}/template/` |
| Configure installments | `POST /quotations/{id}/installments/{plan_configuration_id}/configure/` |
| Investment Funds state | `GET /quotations/{id}/investment-funds/` |
| Investment Fund options | `GET /quotations/{id}/investment-funds/options/?plan_config_id={id}` |
| Configure Investment Funds | `POST /quotations/{id}/investment-funds/` |
| Riders and Benefits state | `GET /quotations/{id}/riders/` |
| Rider and benefit options | `GET /quotations/{id}/riders/options/?plan_config_id={id}` |
| Configure Riders and Benefits | `POST /quotations/{id}/riders/` |
| Add dependent member | `POST /quotations/{id}/members/` |
| Update dependent member | `PATCH /quotations/{id}/members/{member_id}/` |
| Remove dependent member | `DELETE /quotations/{id}/members/{member_id}/` |
| Personal Details options | `GET /quotations/personal-details-options/` |

Quotation list endpoints support filtering, search, ordering, pagination, and partner row-level scoping. Lifecycle actions are exposed as `POST /quotations/{id}/finalize/`, `/expire/`, and `/convert/`; the wizard state is available at `GET /quotations/{id}/wizard-summary/`.

`personal-details-options` returns identity types, genders, smoker statuses, active locations, and active partners assigned to the configured `OL_AGENT_PARTNER_TYPE_CODE`. It accepts an optional `search` parameter for location and agent lookup. `plans/search` searches active, effective product versions and plans. `plan-options` returns payment frequencies from the selected product version, quote-basis and premium-factor choice lists from system parameters, and feature availability derived from product/plan flags and effective OL Joint Life, Mortgage Interest Factor, and Rider Setup rows. Bonus-rate defaults are resolved from the effective OL Bonus Rate scope for the selected product/plan. `members` resolves the most specific effective Member Cover Configuration for each relation (plan scope, then product scope, then global scope), exposing relation, age, waiting-period, coverage-basis, and benefit-limit metadata. No select option is hardcoded in the quotation view; these catalogs remain editable through the platform configuration workflow.

Responses follow the platform API envelope and standard pagination contract. Validation failures are returned through the central error envelope with field-level details.

## Permission and row-level scope

The module uses the `ol_quotations` permission namespace with `VIEW`, `CREATE`, `UPDATE`, `DELETE`, `CONFIGURE`, `PRINT`, and `CONVERT` actions. The Personal Details mutation maps to `UPDATE`, its options endpoint maps to `VIEW`, plan search and plan options map to `VIEW`, plan selection and section configuration map to `UPDATE`, Member Coverage reads map to `VIEW`, dependent add/update/remove actions map to `UPDATE`, Installments state/template/configuration map to `VIEW`/`VIEW`/`UPDATE`, and Investment Funds state/options/configuration map to `VIEW`/`VIEW`/`UPDATE` respectively. The seed command creates the following groups:

| Group | Intended access |
|---|---|
| `OL_QUOTATION_VIEWER` | Read quotation data and summaries |
| `OL_QUOTATION_OFFICER` | Create and update quotations and wizard children |
| `OL_QUOTATION_SUPERVISOR` | Officer access plus finalize, expire, and print |
| `OL_QUOTATION_ADMINISTRATOR` | Full quotation configuration and conversion access |

Non-superusers are restricted to partners returned by `user.visible_partners()`. This preserves the platform’s existing partner-link authorization model and keeps quotation access independent from ordinary module visibility.

## Audit and outbox integration

Quotation creation, draft updates, and lifecycle transitions use `AuditService` with before-state, after-state, changed-field, actor, request, reason, and correlation context. Automatic audit receivers cover the quotation header and all wizard child tables. Lifecycle transitions additionally persist immutable `OLQuotationEvent` rows.

The service creates durable `DomainEvent` rows in the existing transactional outbox for `QuotationCreated`, `QuotationUpdated`, `QuotationFinalized`, `QuotationExpired`, and `QuotationConverted`. Events carry the quotation identifier, quote number, actor identifier, status transition, and metadata. Future proposal, policy, payment, notification, and reporting workers can consume these events without coupling to the quotation request transaction.

## Administration and operations

Django admin registrations present the aggregate and all child tables in table-first form with filters, search, ordering, and foreign-key selection. Quotation events are read-only in admin. Seed execution is idempotent:

```bash
python manage.py migrate
python manage.py seed_ol_quotations
```

The command creates module permissions, role groups, the `OL_QUOTATION` numbering configuration, the `SMOKER_STATUS_CHOICES`, `OL_QUOTE_BASIS_CHOICES`, and `OL_PREMIUM_FACTOR_CHOICES` choice lists, and the Personal Details parameters `OL_MAX_QUOTATION_AGE`, `OL_MIN_QUOTATION_AGE`, `OL_AGENT_PARTNER_TYPE_CODE`, and `OL_IDENTITY_FORMAT_RULES` without duplicating existing rows. Production deployments should run the command after migrations and before enabling quotation menus.

## Future integration points

The quotation aggregate is intentionally prepared for future policy conversion. A conversion worker can consume `QuotationConverted`, verify the calculation snapshot, and create proposal or policy records while retaining the quotation as the source transaction. Claims, commissions, payment collection, document generation, notifications, and reporting should consume the outbox events or read the stable quotation API rather than writing directly to quotation tables.

## Assumptions

The quotation partner is an existing `partners.Partner` record and quotation product configuration is an existing `ol_parameters.OLProduct` record. The optional `ordinary_life.OLProductVersion` and `OLPlan` references preserve compatibility with the earlier Ordinary Life product model while parameter migration remains in progress. Investment Fund allocation is conditional rather than globally optional: non-investment-linked plans are explicitly not applicable, whereas every selected investment-linked plan must have a complete 100% allocation across active, currency-compatible funds. Rider selections remain optional for the first quotation release, but any selected riders must reference active parameter configuration.
