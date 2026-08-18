# Ordinary Life Parameters Traceability

## Traceability purpose

This document maps the nine Ordinary Life parameter groups required by the ZIC system context to the foundation delivered in the current phase. The current change intentionally implements the reusable framework only. It does not introduce transactional OL tables or claim, policy, quotation, or servicing workflows.

The table registry gives each group a stable discovery contract now. Concrete group entities will be added incrementally, each in an isolated change with its own models, migrations, serializers, services, permissions, admin configuration, tests, and frontend table workspace.

## Nine-group map

| Required group | Registry slug | Foundation status | Concrete entity status | Demonstrated or expected responsibility |
|---|---|---|---|---|
| OL Default Setup | `ol-default-setup` | **Ready**: seeded table contract, standard metadata, generic permissions, audit path | Planned next group implementation | Global lookups, defaults, computation approaches, currency and operating rules. |
| OL Policy Setup | `ol-policy-setup` | **Ready**: seeded table contract and lifecycle metadata | Planned | Policy status, grace periods, renewal, lapse, reinstatement, surrender, paid-up, maturity, and payment rules. |
| OL Product Setup | `ol-product-setup` | **Ready**: seeded table contract and product/plan table shape | Planned | Products, plans, benefits, eligibility, coverage, terms, and product-level underwriting configuration. |
| OL Product Rating | `ol-product-rating` | **Ready**: seeded table contract and rate version/row base models | Planned | Versioned rates, product/plan dimensions, age/gender/term factors, loadings, discounts, and pricing rules. |
| OL Rider Setup | `ol-rider-setup` | **Ready**: seeded table contract and standard lifecycle contract | Planned | Riders, rider benefits, limits, eligibility, effective dates, and rider pricing. |
| OL Agent Management | `ol-agent-management` | **Ready**: seeded table contract and actor/audit contract | Planned | Intermediary setup, distribution relationships, hierarchy, commissions, and agency rules. |
| OL Loan Setup | `ol-loan-setup` | **Ready**: seeded table contract and effective-dated table contract | Planned | Ordinary Life loan eligibility, limits, terms, interest, repayment, and servicing rules. |
| OL Medical / Underwriting | `ol-medical-underwriting` | **Ready**: seeded table contract and effective-date contract | Planned | Health questions, medical requirements, thresholds, underwriting outcomes, and escalation rules. |
| OL Claim Setup | `ol-claim-setup` | **Ready**: seeded table contract and audit/lifecycle contract | Planned | Claim types, waiting periods, required documents, benefit calculation, waiver, and settlement rules. |

## Requirement-to-artifact mapping

| Requirement | Implemented artifact | Verification path |
|---|---|---|
| New `ol_parameters` app | `apps.ol_parameters.apps.OLParametersConfig` | Django app registry and migrations |
| Reusable base models | `OLParameterBaseModel`, `OLEffectiveDateModel`, `OLRateTableVersionModel`, `OLRateRowBaseModel` | Model tests and `full_clean()` invariants |
| Table metadata | `OLParameterTableRegistry` | Registry API tests and seed command |
| Generic permissions | `apps/ol_parameters/permissions.py` and seeded `UserPermission` records | Permission matrix tests |
| Audit integration | Service calls plus registry signal receivers | Audit event tests |
| Versioned API base | `apps/ol_parameters/urls.py` and project URL registration | API health and endpoint tests |
| Table-first admin | `OLParameterTableRegistryAdmin` | Admin accessibility and lifecycle tests |
| Seed utility | `seed_ol_parameter_registry` | Idempotency test and command execution |
| Documentation | Architecture and traceability documents | Repository review |

## Business-context traceability notes

The full-system context describes Ordinary Life product and policy setup as configurable, including policy status, grace periods, lapse, reinstatement, surrender eligibility, and minimum premium or payment conditions. It also describes product and rate configuration, riders and benefits, medical and underwriting thresholds, and claim types, waiting periods, documents, and benefit calculations. Those capabilities are represented here as group boundaries and registry contracts rather than prematurely implemented transactional behavior.

The product-rating foundation is intentionally more specialized than the other groups. Rate-table headers need explicit version and supersession semantics, while rate rows need product, plan, age, gender, term, and effective-date dimensions. The corresponding abstract models are available now so future rating tables do not invent incompatible shapes.

## Delivery status policy

A group is marked **Ready** when its table contract can be discovered, permissioned, audited, and rendered by a standard table client. It becomes **Implemented** only after its concrete parameter entities, migrations, APIs, admin, seed data, tests, and frontend workspace are delivered in a dedicated change. This distinction prevents the registry foundation from being mistaken for a complete business configuration module.


## OL Default Setup implementation status

The OL Default Setup group is now **Implemented** as the first concrete group beyond the foundation. Its canonical artifacts are isolated under `backend/apps/ol_parameters/` and are exposed under `/api/v1/ol-parameters/`:

| Requirement | Delivered artifact | Status |
|---|---|---|
| Typed OL defaults | `OLDefaultSystemParameter` with `STRING`, `TEXT`, `INTEGER`, `DECIMAL`, `BOOLEAN`, `DATE`, and `JSON` storage | Implemented |
| Commission overrides | `OLOverrideCommissionSetup` with partner/intermediary/product/plan/rider/channel/branch/currency/year-range scope, priority, rate type, and effective dating | Implemented |
| Calculation strategies | `OLComputationApproach` with calculation area, basis, formula key, sequence, and JSON configuration | Implemented |
| Maturity claim behavior | `OLMaturityClaimSetup` with product/plan scope, initiation lead time, notifications, payout, documents, approval, and creation status | Implemented |
| APIs | List/detail/create/update/deactivate, search, filters, ordering, pagination, and CSV export for all four tables | Implemented |
| Admin | Table-first, permission-aware Django admin for all four entities | Implemented |
| Audit | Central audit events for service and direct-save paths, with actor and request correlation support | Implemented |
| Seed data | `seed_ol_default_setup` idempotently seeds 11 operational defaults | Implemented |
| Tests | Typed validation, stale-column clearing, overlap rules, API behavior, export, deactivation, and audit tests | Implemented |

The legacy `apps.ordinary_life` Default Setup models and `/api/v1/ordinary-life/setup/` routes remain unchanged in this delivery to preserve backward compatibility. The new `apps.ol_parameters` entities are canonical for new configuration screens and future consumers. A later compatibility migration may map legacy records into the new tables after a controlled data-reconciliation decision.

## Updated nine-group status

| Required group | Concrete implementation status after this delivery |
|---|---|
| OL Default Setup | **Implemented** |
| OL Policy Setup | Foundation registry only; planned |
| OL Product Setup | Foundation registry only; planned |
| OL Product Rating | Foundation registry and abstract rate contracts; planned |
| OL Rider Setup | Foundation registry only; planned |
| OL Agent Management | Foundation registry only; planned |
| OL Loan Setup | Foundation registry only; planned |
| OL Medical / Underwriting | Foundation registry only; planned |
| OL Claim Setup | Foundation registry only; planned |

## OL Policy Setup Part 1 implementation status

OL Policy Setup Part 1 is now **Implemented** as the second concrete group beyond the OL Parameters foundation. The canonical artifacts are isolated under `backend/apps/ol_parameters/`, with legacy Ordinary Life setup routes preserved.

| Requirement | Delivered artifact | Status |
|---|---|---|
| Anticipated endowment rates | `OLAnticipatedEndowmentInstallmentRate` with product/plan, frequency, age, term, policy-year, currency, rate, and effective-date dimensions | Implemented |
| Grace periods | `OLGracePeriod` with frequency, grace, warning, pre-lapse, lapse, minimum due amount, and optional product/plan scope | Implemented |
| Policy status catalog | `OLPolicyStatus` with display ordering, terminal status flag, and allowed transition codes | Implemented |
| Renewal status catalog | `OLPolicyRenewalStatus` with display ordering and renewal action | Implemented |
| Beneficial types | `OLBeneficialType` with category, calculation basis, default ratio, and multiple-allocation behavior | Implemented |
| Member cover configuration | `OLMemberCoverConfiguration` with product/plan scope, relation, age limits, waiting period, limits, and calculation bases | Implemented |
| Validation and invariants | Effective-date ordering, range checks, product-plan consistency, nonnegative values, active transition targets, and terminal transition rules | Implemented |
| APIs | Six table-first resources under `/api/v1/ol-parameters/`, including search, filters, ordering, pagination, CSV export, deactivation, and transition validation | Implemented |
| Admin | Permission-aware table-first registrations for all six entities | Implemented |
| Audit | Central audit events for service and direct-save paths, including actor and request correlation | Implemented |
| Seed data | `seed_ol_policy_setup` idempotently seeds catalogs, defaults, registry contracts, and safe starter rows | Implemented |
| Tests | Model invariants, transition graph validation, CRUD, filtering, export, soft deactivation, audit, registry, and seed idempotency coverage | Implemented |

## Updated nine-group status after Policy Setup Part 1

| Required group | Concrete implementation status after this delivery |
|---|---|
| OL Default Setup | **Implemented** |
| OL Policy Setup | **Part 1 implemented**; later policy setup parts remain planned |
| OL Product Setup | Foundation registry only; planned |
| OL Product Rating | Foundation registry and abstract rate contracts; planned |
| OL Rider Setup | Foundation registry only; planned |
| OL Agent Management | Foundation registry only; planned |
| OL Loan Setup | Foundation registry only; planned |
| OL Medical / Underwriting | Foundation registry only; planned |
| OL Claim Setup | Foundation registry only; planned |

The canonical Policy Setup records are intended for new configuration consumers. The existing legacy `apps.ordinary_life` setup tables and endpoints remain unchanged, so migration or reconciliation of preexisting configuration data is a separate controlled decision rather than an implicit destructive replacement.

## OL Policy Setup Part 2 implementation status

OL Policy Setup Part 2 is now **Implemented** as the next isolated increment of the canonical Policy Setup group. It adds surrender, paid-up, value-rate, and commitment configuration while preserving the legacy Ordinary Life setup surface.

| Requirement | Delivered artifact | Status |
|---|---|---|
| Surrender setup | `OLSurrenderSetup` with product/plan scope, eligibility thresholds, charge type/value, partial surrender, payout timing, and approval | Implemented |
| Paid-up setup | `OLPaidUpSetup` with conversion basis, eligibility thresholds, effective rule, and product/plan scope | Implemented |
| Surrender-value rates | `OLSurrenderValueRate` with table/version, product/plan, demographic, age/term/policy-year, Decimal factor, and effective-date dimensions | Implemented |
| Paid-up rates | `OLPaidUpRate` with table/version, product/plan, demographic, age/term/policy-year, Decimal factor, and effective-date dimensions | Implemented |
| Commitment statuses | `OLCommitmentStatus` with display order, applicability, terminal flag, and effective dates | Implemented |
| Validation and invariants | Product-plan consistency, ordered ranges, nonnegative rates, required table/version, surrender-charge rule, paid-up eligibility threshold, and active scoped overlap protection | Implemented |
| APIs | Five table-first resources under `/api/v1/ol-parameters/` with CRUD, search, filters, ordering, pagination, CSV export, and deactivation | Implemented |
| Admin | Permission-aware table-first admin screens for all five entities | Implemented |
| Audit | Central audit events for service and direct-save paths across all Part 2 models | Implemented |
| Seed data | `seed_ol_policy_setup` now seeds Part 1 and Part 2 catalogs, registry metadata, global setup defaults, and safe product-scoped starter rates | Implemented |
| Tests | Part 2 model invariants, overlap protection, CRUD for all five tables, permissions, audit coverage, seed idempotency, and admin access | Implemented |

## Updated nine-group status after Policy Setup Part 2

| Required group | Concrete implementation status after this delivery |
|---|---|
| OL Default Setup | **Implemented** |
| OL Policy Setup | **Parts 1 and 2 implemented**; later policy setup parts remain planned |
| OL Product Setup | Foundation registry only; planned |
| OL Product Rating | Foundation registry and abstract rate contracts; planned |
| OL Rider Setup | Foundation registry only; planned |
| OL Agent Management | Foundation registry only; planned |
| OL Loan Setup | Foundation registry only; planned |
| OL Medical / Underwriting | Foundation registry only; planned |
| OL Claim Setup | Foundation registry only; planned |

The Part 2 implementation is additive. Existing legacy `apps.ordinary_life` tables and endpoints remain available; reconciliation of existing legacy configuration into canonical OL Parameters tables is a separate controlled migration decision.


## OL Policy Setup Part 3 implementation status

OL Policy Setup Part 3 is now **Implemented** as the third isolated increment of the canonical Policy Setup group. It adds the reusable configuration foundation needed by future medical underwriting, policy notification, and lapse-reinstatement workflows while preserving the legacy Ordinary Life setup surface.

| Requirement | Delivered artifact | Status |
|---|---|---|
| Health-question catalog | `OLHealthQuestion` with typed answers, categories, underwriting impact, and medical-follow-up flag | Implemented |
| Questionnaire headers | `OLHealthQuestionnaire` with global, product, plan, and scheme scope, versioning, thresholds, and effective dates | Implemented |
| Questionnaire membership | `OLHealthQuestionnaireItem` with ordered sequence, mandatory/medical-trigger flags, scores, and uniqueness constraints | Implemented |
| Notification schedules | `OLGracePeriodNotificationSchedule` with lifecycle event, signed offset, channel, recipient, and template configuration | Implemented |
| Reinstatement windows | `OLReinstatementWindow` with product/plan scope, lapse window, repeat limit, underwriting, premium, interest, and penalty controls | Implemented |
| Validation and invariants | Scope rules, active-reference checks, product-plan consistency, positive ordering, range checks, and effective-date overlap protection | Implemented |
| APIs | Five table-first resources under `/api/v1/ol-parameters/` with CRUD, search, filters, ordering, pagination, CSV export, and deactivation | Implemented |
| Admin | Permission-aware Django admin changelists and forms for all five entities | Implemented |
| Audit | Explicit signal registration for all five Part 3 models, covering direct creates and updates through the central audit service | Implemented |
| Seed data | `seed_ol_policy_setup` idempotently seeds five registry contracts and starter questionnaire, notification, and reinstatement records | Implemented |
| Migration | Additive `0007_olhealthquestion_olhealthquestionnaire_and_more.py` | Implemented |
| Tests | Model invariants, all-five-resource CRUD, permission enforcement, audit coverage, seed idempotency, registry count, and admin access | Implemented |

The Policy Setup registry now contains **16 contracts across Parts 1–3**. The Part 3 implementation is configuration-only: future underwriting and policy modules remain responsible for collecting answers, applying underwriting decisions, scheduling messages, and executing reinstatements using these active, effective-dated records.

## Updated nine-group status after Policy Setup Part 3

| Required group | Concrete implementation status after this delivery |
|---|---|
| OL Default Setup | **Implemented** |
| OL Policy Setup | **Parts 1, 2, and 3 implemented**; later policy setup parts remain planned |
| OL Product Setup | Foundation registry only; planned |
| OL Product Rating | Foundation registry and abstract rate contracts; planned |
| OL Rider Setup | Foundation registry only; planned |
| OL Agent Management | Foundation registry only; planned |
| OL Loan Setup | Foundation registry only; planned |
| OL Medical / Underwriting | Foundation registry only; planned; consumes Part 3 health-question configuration |
| OL Claim Setup | Foundation registry only; planned |


## OL Product Setup implementation status

OL Product Setup is now **Implemented** as the next isolated concrete OL Parameters group. The implementation is configuration-only and remains separate from the transactional `apps.ordinary_life` product model and operational product workflows.

| Requirement | Delivered artifact | Status |
|---|---|---|
| Plan-type catalog | `OLPlanType` with effective-dated plan categories | Implemented |
| Product contract | `OLProduct` with plan type, class, currency, eligibility, limits, frequencies, and product capabilities | Implemented |
| Tax configuration | `OLPlanTaxConfiguration` with product/plan scope, tax basis, rate, application event, sequence, and country/branch scope | Implemented |
| Target-market configuration | `OLPlanTargetMarket` with market type, age range, occupation categories, residency, and product/plan scope | Implemented |
| Risk categories | `OLPlanRiskCategory` with underwriting class, loading basis, and product/plan scope | Implemented |
| Occupation-risk limits | `OLPlanOccupationRiskLimit` with category, maximum sum assured, loading rate, and exclusion flag | Implemented |
| Investment fund catalogs | `OLInvestmentFundType` and `OLInvestmentFund` with risk profile, valuation, unit price, currency, and allocation metadata | Implemented |
| Validation and invariants | Product eligibility ranges, scoped references, nonnegative and percentage bounds, positive fund pricing, and active effective-date overlap protection | Implemented |
| APIs | Eight table-first resources with CRUD, search, filters, ordering, pagination, CSV export, and soft deactivation | Implemented |
| Admin | Permission-aware registrations for all eight Product Setup entities | Implemented |
| Audit | Central audit events through service mutations and explicit signal registration for all eight entities | Implemented |
| Seed data | `seed_ol_product_setup` idempotently seeds six plan types, one product, starter scoped configuration, three fund types, one fund, and eight registry contracts | Implemented |
| Tests | Model invariants, all endpoint CRUD paths, filtering/export, permissions, audit, seed idempotency, and admin registration coverage | Implemented |
| Migration | Additive `0008_olinvestmentfundtype_olinvestmentfund_olplantype_and_more.py` | Implemented |

## Updated nine-group status after OL Product Setup

| Required group | Concrete implementation status after this delivery |
|---|---|
| OL Default Setup | **Implemented** |
| OL Policy Setup | **Parts 1, 2, and 3 implemented**; later policy setup parts remain planned |
| OL Product Setup | **Implemented** |
| OL Product Rating | Foundation registry and abstract rate contracts; planned |
| OL Rider Setup | Foundation registry only; planned |
| OL Agent Management | Foundation registry only; planned |
| OL Loan Setup | Foundation registry only; planned |
| OL Medical / Underwriting | Foundation registry only; planned |
| OL Claim Setup | Foundation registry only; planned |

The Product Setup increment is additive and does not alter legacy Ordinary Life product tables or routes. A future controlled reconciliation process may map approved legacy product data into canonical parameter rows, but no implicit data migration or destructive replacement is performed by this delivery.
