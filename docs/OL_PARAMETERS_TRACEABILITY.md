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
