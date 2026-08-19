# OL Product Rating frontend

The Product Rating workspace is available at `/ordinary-life/parameters/product-rating` and uses the shared `DataTable`, `EditableGrid`, `FilterBar`, modal, form-control, status-badge, and toast components.

## Screens and API contracts

| Screen | Collection endpoint | Editor behavior |
|---|---|---|
| OL Premium Rates | `/api/v1/ol-parameters/premium-rate-tables/` | Version list with product/plan, currency, effective dates, status, and multi-dimensional premium rows |
| OL Mortality Rate | `/api/v1/ol-parameters/mortality-rate-tables/` | Version list with age/gender/smoker/policy-year mortality rows |
| OL Joint Life Setup | `/api/v1/ol-parameters/joint-life-setups/` | Catalog modal for joint-life type, age basis, survivor rule, adjustment factor, and underwriting rule |

Premium and mortality row collections are loaded from the table context exposed by the backend. The rate editor uses `EditableGrid` for add, edit, remove, and save operations. Premium dimensions are gender, smoker status, age band, term band, frequency, sum-assured band, and rate. Mortality dimensions are age, gender, smoker status, policy year, and mortality rate. Numeric fields remain decimal-safe and are validated before mutation.

## Versioning and CSV

The version list provides a `New version` action that copies the selected table scope and increments the serialized version number. The copied version retains effective-date and rating-basis context while remaining a separate backend record. Existing quotation calculations continue to reference their original source version.

The shared table export action is enabled for premium and mortality tables. The row editor also provides CSV import for the selected table. Supported CSV fields are normalized to backend payload names; blank optional dimensions become null. Rows with invalid age, term, policy-year, or rate values are rejected locally with their source row number. Backend errors, including overlap and duplicate-scope responses, are surfaced in the inline `CSV rows rejected` banner without hiding accepted rows.

## Validation and permissions

The frontend checks required table code/name/effective-date fields, decimal precision-compatible values, non-negative rates, ordered age/term/year ranges, and the required joint-life fields. The backend remains authoritative for product/plan linkage, effective-date overlaps, duplicate dimensions, actuarial constraints, and audit behavior. Backend overlap messages are retained in the `Validation or overlap warning` banner.

The workspace uses `ol_parameters` access metadata. View permission controls visibility. Create and update permissions control table creation, version creation, row save, and joint-life mutation. Deactivate permission controls the confirmation-gated deactivate action. No product, plan, gender, smoker, frequency, or rating catalog is hardcoded in the page; values arrive from backend records or table metadata.

## Assumptions

The current API exposes rate tables and row collections independently. The frontend treats the selected table as the parent context and posts new rows with that table identifier. Existing rows are patched by identifier. Version creation uses the standard table POST contract because no separate custom version action is exposed by the backend. Product and plan scope remains represented by the backend table fields and metadata, allowing later product-selector integration without changing the grid contract.

## Part 2 rating parameter screens

The continuation screens are available as tabs in the same Product Rating workspace. They use the collection endpoints below and preserve the shared table-first interaction model: server-backed pagination, search and filters, CSV export, permission-aware row actions, effective-date status, and confirmation-gated deactivation.

| Screen | Collection endpoint | Core fields and editor behavior |
|---|---|---|
| Reinstatement Interest Rate | `/api/v1/ol-parameters/reinstatement-interest-rates/` | Code, optional product/plan scope, calculation basis, rate percentage, effective dates, active status, and description. Basis values are `OUTSTANDING_PREMIUM`, `POLICY_VALUE`, and `LOAN_BALANCE`. |
| OL Bonus Rate | `/api/v1/ol-parameters/bonus-rates/` | Code, optional product/plan scope, bonus type, rate, valuation year, declaration frequency, effective dates, active status, and description. The frontend sends the backend-authoritative `REVERSIONARY` value for reversionary bonus setups. |
| OL Mortgage Interest Factor | `/api/v1/ol-parameters/mortgage-interest-factors/` | Code, optional product/plan scope, calculation basis, factor, effective dates, active status, and description. Basis values are `CASH_VALUE`, `PREMIUM`, and `LOAN_BALANCE`. |
| Installment Charge Rate | `/api/v1/ol-parameters/installment-charge-rates/` | Code, optional product/plan scope, payment frequency, charge type, application basis, charge value, effective dates, active status, and description. |
| OL Cash Surrender Value | `/api/v1/ol-parameters/cash-surrender-values/` | Effective-dated dimensions for policy year, age, term, gender, and smoker status, plus exactly one value representation: surrender-value factor or percentage rate. The row editor and CSV importer support both representations. |
| OL Reserve Loadings | `/api/v1/ol-parameters/reserve-loadings/` | Code, optional product/plan scope, loading type, loading basis, rate value, effective dates, active status, and description. The frontend preserves backend loading and basis values when posting records. |

Every Part 2 collection supports the detail action `/{id}/deactivate/` with `POST`. Deactivation is available only when the current access metadata includes the `ol_parameters.deactivate` permission. Create and update controls are similarly gated by `ol_parameters.create` and `ol_parameters.update`; view access controls the table workspace.

### Validation rules

The frontend validates the following rules before sending mutations, while the Django API remains authoritative for overlap detection, duplicate scope/dimension detection, effective dating, audit fields, and database constraints.

| Resource | Client-side validation |
|---|---|
| Reinstatement Interest Rate | Code and product-or-plan scope are required; rate must be between 0 and 100; effective-to cannot precede effective-from. |
| OL Bonus Rate | Code and product-or-plan scope are required; bonus type must be present; valuation year must be positive; rate cannot be negative; effective dates must be ordered. |
| OL Mortgage Interest Factor | Code and product-or-plan scope are required; factor must be greater than zero; effective dates must be ordered. |
| Installment Charge Rate | Code and product-or-plan scope are required; charge value must be between 0 and 100; effective dates must be ordered. |
| OL Cash Surrender Value | Policy-year, age, and term upper bounds cannot be below their lower bounds; age and term dimensions are range-checked; exactly one of `surrender_value_factor` or `rate` must be provided; factor is restricted to 0–1 and rate to 0–100. Gender values are `M` and `F`; smoker values are `NS` and `S`. |
| OL Reserve Loadings | Code and product-or-plan scope are required; loading value must be between 0 and 100; effective dates must be ordered. |

### Cash surrender CSV contract

Cash surrender import is intentionally handled as a row-level workflow because the backend exposes collection CRUD rather than a dedicated bulk-import action. The CSV header uses the backend field names: `code`, `product`, `plan`, `policy_year_from`, `policy_year_to`, `age_from`, `age_to`, `term_from`, `term_to`, `gender`, `smoker_status`, `surrender_value_factor`, and `rate`. Each accepted row is posted to `/api/v1/ol-parameters/cash-surrender-values/`; rejected rows remain visible in the `CSV rows rejected` banner with their source row number and validation message. A row must provide exactly one value representation, and the factor range is deliberately decimal-based rather than percentage-based.

The six Part 2 screens do not hardcode product or plan catalog values. Scope identifiers are entered as backend references in the current modal contract, while all enumerated values sent by the page match the model choices and acceptance fixtures. This leaves the screens compatible with later searchable master-data selectors without changing the collection or mutation contracts.

## Part 2 test coverage

`OLProductRating.test.tsx` covers rendering all six Part 2 collections from mocked API responses, editing and persisting a reinstatement setup with the correct scope and enum payload, blocking a bonus setup with missing required scope, rejecting an out-of-range cash surrender factor during CSV import, and requiring confirmation before deactivation. The existing Part 1 tests remain in the same file and continue to cover premium and mortality row workflows, version creation, and joint-life validation.

## Part 2 assumptions

The page treats each Part 2 endpoint as a standard table collection returning either a paginated `{ results, count, page, page_size }` payload or an equivalent normalized response. It uses `POST` for create, `PATCH` for update, and `POST` for deactivation. Backend audit behavior and effective-date conflict policy remain server-side responsibilities; the frontend surfaces returned messages in the shared inline warning banner and toast system.
