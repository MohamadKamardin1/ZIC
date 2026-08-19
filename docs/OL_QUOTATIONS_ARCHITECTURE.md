# Ordinary Life Quotations Architecture

## Purpose and bounded-context boundary

The `ol_quotations` application is the transactional quotation foundation for Ordinary Life business. It owns quotation drafts, wizard child records, quotation lifecycle history, calculation snapshots, and the integration events needed by future proposal, policy, payment, and reporting bounded contexts.

The application deliberately consumes parameterized product, plan, rider, and fund configuration from `ol_parameters` and existing Ordinary Life product-version structures. It does not copy actuarial tables into quotation rows and does not create policy or claim records. Quotation data captures the customer-specific selection and underwriting inputs used to create a reproducible quotation snapshot.

## Seven-step wizard contract

A quotation is a draft aggregate completed through seven independently saveable wizard steps, followed by a partner-verification handoff step:

| Step | Resource | Completion rule |
|---|---|---|
| 1 | `OLQuotation` Personal Details | Quote identity, date of birth, age, gender, smoker status, location, agent, and address pass validation |
| 2 | `OLQuotationPlanConfiguration` | At least one selected product/plan configuration with valid term, payment period, frequency, quote basis, and positive maturity/base amounts |
| 3 | `OLQuotationMember` | At least one member and at least one `LIFE_ASSURED` |
| 4 | `OLQuotationInstallmentConfiguration` | At least one selected installment configuration |
| 5 | `OLQuotationFundAllocation` | Not applicable when no selected plan is investment-linked; otherwise every applicable plan must have allocations totaling 100% |
| 6 | `OLQuotationRiderSelection` | Optional rider selections driven by OL Rider Setup |
| 7 | `OLQuotationPaymentDetail` and `OLQuotationUnderwriting` | One payment detail record and one underwriting answer record |
| 8 | Partner verification and completion | A compliant partner is matched or an individual onboarding application is completed and converted to a partner. |

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

## Financial Details and premium calculation engine

Financial Details is the quotation’s reproducible rating boundary. The calculation service reads only the persisted quotation wizard state and effective-dated OL Product Rating / OL Parameters data; it never embeds actuarial rates or feature factors in quotation code. A successful calculation stores one current `OLQuotationFinancialSummary` for the quotation, increments the quotation version, marks `7_financial_details` complete, emits `QuotationPremiumCalculated`, and writes a central audit update describing the calculation.

The endpoint contract is:

| Method | Endpoint | Behavior |
|---|---|---|
| `POST` | `/api/v1/ol-quotations/quotations/{id}/calculate/` | Resolve all rating inputs, calculate and persist the latest summary, projections, and installment payouts. |
| `GET` | `/api/v1/ol-quotations/quotations/{id}/financial-details/` | Return the latest summary, component breakdowns, projections, payouts, and recalculation state. |

The engine applies the following calculation order. Every intermediate monetary value is rounded to two decimal places using `ROUND_HALF_UP`; rate and factor values retain their configured Decimal precision until applied.

| Sequence | Component | Parameter source and rule |
|---|---|---|
| 1 | Base premium | Effective `OLPremiumRateTable` / `OLPremiumRateRow`, matched by product version, plan, gender, smoker status, entry age, term, frequency, and optional sum-assured band. A `PER_MILLE` row uses `(sum assured / 1000) × rate`; a percentage row uses `sum assured × rate / 100`. |
| 2 | Joint-life factor | Effective `OLJointLifeSetup.premium_adjustment_factor` at plan or product scope when the selected plan has `joint_life=true`. |
| 3 | Mortgage factor | Effective `OLMortgageInterestFactor.factor` at product scope when the selected plan has `mortgage=true`. |
| 4 | Loadings and discounts | Effective `OLReserveLoading` rows at plan or product scope. Loading rows increase the premium and discount rows reduce it, with each rate applied to the current calculation base. |
| 5 | Rider premiums | Effective `OLRiderRateTable` / `OLRiderRateRow` rows matched by rider, product/plan, gender, smoker status, age, term, frequency, and optional sum-assured band. Rider benefit loadings and discounts are applied to the rider premium. |
| 6 | Installment charge | Effective `OLInstallmentChargeRate` matched by product/plan and payment frequency when the quotation contains an installment configuration. |
| 7 | Taxes | Effective `OLPlanTaxConfiguration` rows in ascending configured `sequence`. Percentage taxes apply to their configured base; fixed taxes add their configured fixed amount. |
| 8 | Total | Pre-tax subtotal plus sequenced taxes, rounded to two decimals. |

A missing base premium rate is a blocking validation error with the message `No premium rate found for the selected plan configuration. Please configure rating parameters.` Missing optional factor, loading, rider, installment, or tax rows do not introduce hardcoded fallback rates; the corresponding component is zero or one only when the parameter semantics define it as optional.

The persisted summary includes total sum assured, base premium, total loading, total discount, total tax, installment charge, total premium, estimated maturity value, quotation version number, calculation timestamp, and the SHA-256 `input_fingerprint`. The `calculation_snapshot` contains plan, rider, and tax component breakdowns, preserving the inputs used to explain the result.

Projections are generated for each policy year up to the longest selected term:

| Field | Meaning |
|---|---|
| `policy_year` | One-based policy year. |
| `premiums_paid` | Base calculated premium multiplied by the applicable years-paid count. |
| `estimated_bonus` | Estimated bonus rate per mille multiplied by sum assured and policy year, divided by 1000. |
| `surrender_value` | Sum assured multiplied by the effective `OLCashSurrenderValue.surrender_value_factor` for that policy year and scope. |
| `paid_up_value` | Sum assured multiplied by the effective `OLPaidUpRate.rate_factor` for that policy year and scope. |
| `estimated_maturity_value` | The plan’s configured maturity value, carried into the projection output. |

Installment payouts are derived from saved `OLQuotationInstallmentRateRow` records. Each row preserves its sequence, description, percentage, and paid-up rate. The payout amount is `rate_percent / 100 × maturity base`; the payout date starts at the saved first due date and advances by the configured payment-frequency interval for each subsequent sequence. No installment schedule is invented when no installment rows are configured.

Recalculation detection hashes sorted JSON containing the quotation’s product/plan configuration, sum assured, term, frequency, age, gender, smoker status, and rider selections. The GET endpoint returns `recalculation_required=true` when no summary exists or the current fingerprint differs from the stored fingerprint, allowing the frontend to require a new calculation after a rating input changes.

## Printable quotation documents

Printable quotations are generated through `QuotationDocumentService` and retain an explicit link to both the source quotation/version and the exact template version used for rendering. Templates are represented by `OLQuotationPrintTemplate` records with a stable `template_code`, monotonically managed `version`, layout variables, active status, and effective dates. Runtime generation selects the requested active template version or the seeded `OL_QUOTATION_DEFAULT` template; the service also keeps a safe built-in fallback so a deployment can still render after a seed has not yet been run, without embedding actuarial rates or customer-specific values in the template definition.

The endpoint contract is:

| Method | Endpoint | Behavior |
|---|---|---|
| `POST` | `/api/v1/ol-quotations/quotations/{id}/print/` | Render and persist a quotation printout as HTML and PDF. Accepts optional `template_code` and `preview` fields. |
| `GET` | `/api/v1/ol-quotations/quotations/{id}/documents/` | Return generated quotation documents, including source version, template version, generated actor/time, MIME type, and downloadable file references. |

A printout is allowed for effective `FINALIZED` or `CONVERTED` quotations. A `DRAFT` may be rendered only when the caller has the dedicated `ol_quotations.print` permission and explicitly requests `preview=true`; expired quotations are never printable. The endpoint requires the `PRINT` permission for generation, while document history is available through the quotation `VIEW` permission. Every generation is audited through the central audit service and emits `QuotationDocumentGenerated` with the quotation, source version, template code/version, actor, and generated file metadata.

The renderer builds a complete context from the persisted quotation aggregate and current immutable calculation/version data. The supported template variables are:

| Variable group | Included values |
|---|---|
| Header and identity | Company header, quote number, quote name, quote date, expiry date, quotation status, quotation version, currency, and generation date. |
| Prospect | Partner/prospect name, identity type and number, date of birth, age at quote, gender, smoker status, address, location, and agent. |
| Plans and terms | Product/plan code and name, section number, policy term, payment period, payment frequency, quote basis, sum assured, mortgage/joint-life/PA/WP flags, bonus rate, and maturity value. |
| Premiums and benefits | Base premium, loadings, discounts, taxes, installment charge, total premium, rider details, benefit basis/value/loading/discount/cap, and component breakdown. |
| Projections | Policy-year premiums paid, estimated bonus, surrender value, paid-up value, and estimated maturity value. |
| Installments | Sequence, description, rate percentage, paid-up rate, payout amount, and payout date. |

The generated record is stored as `OLQuotationDocument`. It references the quotation, the immutable `OLQuotationVersion` used as the source snapshot, the selected `OLQuotationPrintTemplate`, and the copied `template_version`. It records `generated_by`, `generated_at`, MIME type, and durable HTML/PDF file references. In the configured local storage backend, files are written below the media document directory using quotation and document identifiers; the model’s file references remain the source of truth and can be replaced by object-storage URLs without changing the API contract. The API exposes separate `html_url` and `pdf_url` values, allowing the quotation detail page to list prior generated documents and download the exact artifact that was produced.

Document generation is intentionally append-only: generating a new printout creates a new document record and never overwrites a prior artifact. This preserves the source transaction, source version, template version, and audit trail needed for reproducible customer-facing documents.

## Domain model and invariants

`OLQuotation` is the aggregate header. It stores the canonical quote number, partner, parameter-backed product, optional legacy product version, currency, expiry date, status, totals, calculation snapshot, and metadata. The quote number is generated by the existing numbering engine using `OL_QUOTATION`; currency defaults through the existing `DEFAULT_CURRENCY` system parameter and is normalized to an ISO-like three-letter code.

The aggregate supports the following lifecycle:

| Current status | Allowed next statuses |
|---|---|
| `DRAFT` | `FINALIZED`, `EXPIRED` |
| `FINALIZED` | `CONVERTED`, `EXPIRED` |
| `CONVERTED` | None |
| `EXPIRED` | None |

Finalization locks the quotation into a reproducible calculation state. It requires every applicable wizard prerequisite, including a current Financial Details summary whose input fingerprint still matches the quotation. It writes `total_sum_assured` and `total_premium`, stores the selected child identifiers and calculation currency in `calculation_snapshot`, sets `FINALIZED`, and emits `QuotationFinalized`. A missing, stale, or incomplete prerequisite returns a blocking validation response and leaves the quotation in `DRAFT`. Conversion creates only an `OLProposal` handoff skeleton; policy issuance remains outside this bounded context.

### BR-02 versioning and lifecycle operations

Quotation changes do not destroy prior business values. A finalized quotation can be revised through `POST /quotations/{id}/revise/`; the service records the finalized aggregate and child-state snapshot as an immutable `OLQuotationVersion`, marks that historical version `SUPERSEDED`, increments the active version number, and returns the same quotation aggregate as a new editable `DRAFT`. The editable revision invalidates the current financial summary for recalculation rather than presenting stale premium values as current. The prior version remains available for audit, comparison, and as-of retrieval.

Version history is available at `GET /quotations/{id}/versions/`, returning version number, status, creator, creation timestamp, and change reason. `GET /quotations/{id}/as-of-version/{version_number}/` returns the immutable snapshot for a selected version; this endpoint is read-only and does not restore or mutate the active quotation. Version creation and revision emit `QuotationVersionCreated`, and the corresponding audit records include the before-state, after-state, actor, reason, and correlation metadata.

Expiry is parameterized by `OL_QUOTATION_DEFAULT_EXPIRY_DAYS` and is applied when a draft is created unless an explicit expiry date is supplied. Read endpoints compute an effective `EXPIRED` status when a draft or finalized quotation has an expiry date before the evaluation date, while preserving the stored status until batch persistence is requested. The idempotent `python manage.py expire_ol_quotations [--as-of YYYY-MM-DD] [--dry-run]` command persists eligible expirations, increments the version, writes an immutable snapshot, and emits `QuotationExpired`. Expired quotations cannot be finalized, revised, printed, converted, or deleted.

Finalization evaluates the approval integration hook after the quotation is otherwise valid. When `OL_QUOTATION_APPROVAL_ENABLED` is active and the configured `OL_QUOTATION_APPROVAL_SUM_ASSURED_LIMIT` or `OL_QUOTATION_APPROVAL_LOAN_LIKE_LIMIT` is exceeded, the quotation is finalized with `approval_required=true`, the threshold reasons are retained in lifecycle metadata, and `QuotationApprovalRequested` is emitted. This is deliberately a clean hand-off to a future approval engine; the quotation module does not create or resolve approval tasks.

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
| Financial Details calculation | `POST /quotations/{id}/calculate/` |
| Financial Details summary | `GET /quotations/{id}/financial-details/` |
| Finalize quotation | `POST /quotations/{id}/finalize/` |
| Revise finalized quotation | `POST /quotations/{id}/revise/` |
| Quotation version history | `GET /quotations/{id}/versions/` |
| As-of version snapshot | `GET /quotations/{id}/as-of-version/{version_number}/` |
| Partner verification | `GET /quotations/{id}/partner-verification/` |
| Partner completion | `POST /quotations/{id}/partner-completion/` |
| Convert to proposal | `POST /quotations/{id}/convert-to-proposal/` (legacy alias: `/convert/`) |
| Expire quotation | `POST /quotations/{id}/expire/` |
| Add dependent member | `POST /quotations/{id}/members/` |
| Update dependent member | `PATCH /quotations/{id}/members/{member_id}/` |
| Remove dependent member | `DELETE /quotations/{id}/members/{member_id}/` |
| Personal Details options | `GET /quotations/personal-details-options/` |

Quotation list endpoints support filtering, search, ordering, pagination, partner row-level scoping, and effective expiry status. Lifecycle actions are exposed as `POST /quotations/{id}/finalize/`, `/revise/`, `/expire/`, and `/convert/`; version history and as-of snapshots are read-only; and the wizard state is available at `GET /quotations/{id}/wizard-summary/`.

`personal-details-options` returns identity types, genders, smoker statuses, active locations, and active partners assigned to the configured `OL_AGENT_PARTNER_TYPE_CODE`. It accepts an optional `search` parameter for location and agent lookup. `plans/search` searches active, effective product versions and plans. `plan-options` returns payment frequencies from the selected product version, quote-basis and premium-factor choice lists from system parameters, and feature availability derived from product/plan flags and effective OL Joint Life, Mortgage Interest Factor, and Rider Setup rows. Bonus-rate defaults are resolved from the effective OL Bonus Rate scope for the selected product/plan. `members` resolves the most specific effective Member Cover Configuration for each relation (plan scope, then product scope, then global scope), exposing relation, age, waiting-period, coverage-basis, and benefit-limit metadata. No select option is hardcoded in the quotation view; these catalogs remain editable through the platform configuration workflow.

Responses follow the platform API envelope and standard pagination contract. Validation failures are returned through the central error envelope with field-level details.

## Permission and row-level scope

The module uses the `ol_quotations` permission namespace with `VIEW`, `CREATE`, `UPDATE`, `DELETE`, `CONFIGURE`, `PRINT`, and `CONVERT` actions. Financial Details uses explicit `financial_view` (`VIEW`) and `financial_calculate` (`UPDATE`) mappings; revision uses `revise` (`UPDATE`); and version history/as-of retrieval uses `versions`/`as_of_version` (`VIEW`). Finalize and expiry use their lifecycle-specific permission mappings and are additionally constrained by effective status and wizard validation. The Personal Details mutation maps to `UPDATE`, its options endpoint maps to `VIEW`, plan search and plan options map to `VIEW`, plan selection and section configuration map to `UPDATE`, Member Coverage reads map to `VIEW`, dependent add/update/remove actions map to `UPDATE`, Installments state/template/configuration map to `VIEW`/`VIEW`/`UPDATE`, and Investment Funds state/options/configuration map to `VIEW`/`VIEW`/`UPDATE` respectively. The seed command creates the following groups:

| Group | Intended access |
|---|---|
| `OL_QUOTATION_VIEWER` | Read quotation data and summaries |
| `OL_QUOTATION_OFFICER` | Create and update quotations and wizard children |
| `OL_QUOTATION_SUPERVISOR` | Officer access plus finalize, expire, and print |
| `OL_QUOTATION_ADMINISTRATOR` | Full quotation configuration and conversion access |

Non-superusers are restricted to partners returned by `user.visible_partners()`. This preserves the platform’s existing partner-link authorization model and keeps quotation access independent from ordinary module visibility.

## Audit and outbox integration

Quotation creation, draft updates, and lifecycle transitions use `AuditService` with before-state, after-state, changed-field, actor, request, reason, and correlation context. Automatic audit receivers cover the quotation header and all wizard child tables. Lifecycle transitions additionally persist immutable `OLQuotationEvent` rows.

The service creates durable `DomainEvent` rows in the existing transactional outbox for `QuotationCreated`, `QuotationUpdated`, `QuotationFinalized`, `QuotationExpired`, `QuotationConverted`, `QuotationVersionCreated`, `QuotationApprovalRequested`, `QuotationPremiumCalculated`, `PartnerVerified`, `PartnerCompleted`, and `ProposalCreated`. Events carry the quotation identifier, quote number, actor identifier, status transition, proposal/version references, and metadata. Future proposal, policy, payment, notification, and reporting workers can consume these events without coupling to the quotation request transaction.

## Administration and operations

Django admin registrations present the aggregate and all child tables in table-first form with filters, search, ordering, and foreign-key selection. Quotation events are read-only in admin. Seed execution is idempotent:

```bash
python manage.py migrate
python manage.py seed_ol_quotations
```

The command creates module permissions, role groups, the `OL_QUOTATION` numbering configuration, the `SMOKER_STATUS_CHOICES`, `OL_QUOTE_BASIS_CHOICES`, and `OL_PREMIUM_FACTOR_CHOICES` choice lists, the Personal Details parameters `OL_MAX_QUOTATION_AGE`, `OL_MIN_QUOTATION_AGE`, `OL_AGENT_PARTNER_TYPE_CODE`, and `OL_IDENTITY_FORMAT_RULES`, and lifecycle defaults `OL_QUOTATION_DEFAULT_EXPIRY_DAYS`, `OL_QUOTATION_APPROVAL_ENABLED`, `OL_QUOTATION_APPROVAL_SUM_ASSURED_LIMIT`, and `OL_QUOTATION_APPROVAL_LOAN_LIKE_LIMIT` without duplicating existing rows. Production deployments should run the command after migrations and before enabling quotation menus. Batch expiry can then be run with `python manage.py expire_ol_quotations --dry-run` before the first persistence run.

## Partner verification and proposal conversion

Partner verification matches `identity_type`, `identity_number`, and `date_of_birth` against `partners.Partner`. A matching partner is compliant only when its status is `ACTIVE` and `is_active` is true. The response also reports quotation fields that are blank on the matched partner. A compliant match is linked to both quotation partner relationships and marks `partner_verified=true`.

When a matching partner is missing, `partner-completion` builds an individual `PartnerApplication` from Personal Details plus submitted KYC fields. It delegates draft creation, submission, review, compliance approval, duplicate checking, and conversion to `ApplicationService`, preserving the onboarding state machine and central audit behavior. Configured nested requirements remain authoritative; the bridge does not bypass required onboarding validation.

BR-01 is enforced by `convert-to-proposal`: the quotation must be effectively `FINALIZED`, unexpired, partner verified, and free of unresolved approval requirements. The operation locks the quotation, creates one `ol_proposals.OLProposal` record for the current finalized quotation version, copies prospect, plan, and financial-summary snapshots, assigns a parameter-backed proposal number, changes the quotation to `CONVERTED`, and emits `QuotationConverted` and `ProposalCreated`. The proposal starts in `DRAFT` status for the separate OL Proposals workflow. A unique quotation/version constraint prevents duplicate handoffs.

## Future integration points

The quotation aggregate is intentionally prepared for future policy conversion. A conversion worker can consume `QuotationConverted`, verify the calculation snapshot, and create proposal or policy records while retaining the quotation as the source transaction. Claims, commissions, payment collection, document generation, notifications, and reporting should consume the outbox events or read the stable quotation API rather than writing directly to quotation tables.

## Assumptions

The quotation partner is an existing `partners.Partner` record and quotation product configuration is an existing `ol_parameters.OLProduct` record. The optional `ordinary_life.OLProductVersion` and `OLPlan` references preserve compatibility with the earlier Ordinary Life product model while parameter migration remains in progress. Investment Fund allocation is conditional rather than globally optional: non-investment-linked plans are explicitly not applicable, whereas every selected investment-linked plan must have a complete 100% allocation across active, currency-compatible funds. Rider selections remain optional for the first quotation release, but any selected riders must reference active parameter configuration.
