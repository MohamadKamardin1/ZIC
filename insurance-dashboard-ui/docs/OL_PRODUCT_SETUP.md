# OL Product Setup

## Scope

The OL Product Setup workspace provides table-first configuration for plan types, OL products, plan taxes, target markets, risk categories, occupation risk limits, investment fund types, and investment funds. It is available from the Ordinary Life Parameters navigation group at `/ordinary-life/parameters/product-setup`.

## Screen contracts

| Screen | Backend collection | Main configuration |
|---|---|---|
| OL Plan Types | `/api/v1/ol-parameters/plan-types/` | Code, name, plan category, description, active state |
| OL Product | `/api/v1/ol-parameters/products/` | Plan type, class, currency, eligibility ages, terms, sum assured limits, premium frequencies, capabilities, effective dates |
| Plan Tax Configurations | `/api/v1/ol-parameters/plan-tax-configurations/` | Product/plan scope, tax type, basis, rate type/value, application sequence |
| Plan Target Market | `/api/v1/ol-parameters/plan-target-markets/` | Product/plan scope, market type, age range, occupation categories, residency |
| Plan Risk Categories | `/api/v1/ol-parameters/plan-risk-categories/` | Product/plan scope, underwriting class, loading basis |
| Plan Occupation Risk Limit | `/api/v1/ol-parameters/plan-occupation-risk-limits/` | Product/plan scope, occupation risk, maximum sum assured, loading, exclusion |
| Investment Fund Type | `/api/v1/ol-parameters/investment-fund-types/` | Code, name, risk profile, description |
| Investment Fund | `/api/v1/ol-parameters/investment-funds/` | Fund type, currency, valuation frequency, unit price, allocation rules |

Each collection uses the shared server-side table contract for search, filters, pagination, sorting, metadata, and CSV export. Row mutations use the corresponding standard create, update, and deactivate actions.

## Product editor

The OL Product editor is grouped into the following sections:

1. **Identity:** code, name, plan type, insurance class, currency, and description.
2. **Eligibility and limits:** minimum and maximum entry ages, minimum and maximum policy terms, and optional sum assured limits.
3. **Premium frequencies:** a controlled tag editor whose suggestions are populated from Product Setup option data. Values are not hardcoded in the page.
4. **Product capabilities:** a reusable toggle grid for riders, loans, withdrawals, surrender, paid-up, bonus, and investment-linked behavior.
5. **Effective dates and status:** effective-from, effective-to, and active state.

Product and plan selectors are loaded from the corresponding OL Product Setup APIs. Investment fund selectors are loaded from the active investment fund type collection. The frontend only presents values received from the backend; server validation remains authoritative.

## Validation

The editor blocks invalid submissions before sending a mutation. Required identity and scope fields must be populated. Effective-to cannot precede effective-from. Minimum values cannot exceed their corresponding maximum values for ages, terms, or sum assured. Premium frequency lists must contain at least one configured value for products. Numeric fields use decimal-safe controls and preserve backend-compatible values.

The server remains responsible for effective-date overlap detection, duplicate scope rules, permission checks, and all final model constraints. API errors are normalized through the shared client and displayed through the UI kit’s inline field errors, banners, or toast notifications.

## Access and actions

The page requires the `ol_parameters` module to be visible. View permission is required for table access. Create, update, and deactivate permissions independently gate the New setup button, edit actions, and deactivate actions. No mutation control is shown to users without its corresponding permission.

## Implementation assumptions

The existing backend route names and serializer fields are treated as the source of truth. The product capabilities use the established backend boolean field names, including `allow_paidup` and `investment_linked`. Product Setup reference data is intentionally not duplicated in frontend constants so future parameter changes become visible without a frontend deployment.
