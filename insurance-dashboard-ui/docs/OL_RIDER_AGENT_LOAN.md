# OL Rider, Agent, and Loan Setup

This module uses the shared table-first UI kit. All select values are loaded from the backend `OPTIONS` metadata for the relevant DRF resource and, where applicable, augmented from active records returned by the collection endpoint. No business enum is duplicated in the page implementation.

## OL Riders

The **OL Riders** screen consumes `/api/v1/ol-parameters/rider-setups/`. The table presents rider code, name, category and benefit badges, age and term ranges, waiting period, standalone/underwriting rules, effective dates, and status. The editor supports rider category, benefit type, calculation basis, minimum and maximum age, term, sum assured limits, waiting period, effective dates, standalone attachment, underwriting requirement, product/plan scope, and description. The UI blocks missing code/name/catalog values, invalid age or term ranges, negative sum assured limits, and an effective-to date earlier than effective-from.

The **OL Rider Rate Tables** screen consumes `/api/v1/ol-parameters/rider-rate-tables/`. It supports versioned table records scoped by rider, product, plan, rating basis, and effective period. The **OL Rider Rate Rows** screen consumes `/api/v1/ol-parameters/rider-rate-rows/` and provides row CRUD, dimension filters, CSV import, and CSV export. Rate rows validate gender, smoker status, rate unit, age band, term band, sum-assured band ordering, and non-negative decimal rate values. Imported rows are validated independently and only accepted rows are posted to the collection endpoint; rejected rows are surfaced through the shared toast system.

## Agent Commission Setup

The **Agent Commission Setup** screen consumes `/api/v1/ol-parameters/agent-commission-setups/`. Its table supports filters for agent/partner, product, commission type, and active status, and displays intermediary scope, product/plan scope, channel, commission type, rate, priority, effective dates, and status. The editor loads intermediary type, distribution channel, commission type, rate type, and related master-data choices from backend metadata. It validates required scope fields, non-negative commission values, effective-date ordering, and percentage limits when the backend identifies a percentage rate type. Backend overlap responses are shown as inline warning banners/toast messages rather than silently replacing an existing rule.

## OL Loan System Setup

The **OL Loan System Setup** screen consumes `/api/v1/ol-parameters/loan-system-setups/`. It supports loan basis, maximum percentage of cash value, minimum and maximum loan amounts, repayment options, effects on claim/surrender/maturity, policy-loan availability, automatic benefit deduction, approval requirement, product/plan scope, effective dates, and description. Percentage validation is inclusive from `0` to `100`; amounts must be positive and the maximum amount cannot be below the minimum amount. The repayment-options field is persisted as backend-compatible JSON.

## OL Loan Interest Control

The **OL Loan Interest Control** screen consumes `/api/v1/ol-parameters/loan-interest-controls/`. It supports decimal interest rate, compounding frequency, interest calculation basis, grace period days, optional penalty interest rate, interest suspension rule, capitalization toggle, product/plan scope, effective dates, and description. Interest and penalty rates are validated as non-negative decimals with percentage bounds where the backend identifies percentage semantics; grace periods cannot be negative. Nullable penalty-rate values remain nullable when sent to the API.

## Shared behavior and permissions

All three page groups use shared DataTable pagination, server-side sorting, search, filter controls, CSV export, modal forms, status badges, and confirmation-gated deactivation. Create, update, import, and deactivate actions are hidden unless the authenticated access payload exposes the corresponding `ol_parameters` permission. Effective-date status is rendered as Active, Scheduled, Expired, or Inactive. Successful mutations refresh the active table without leaving the current parameter group.

## API and metadata contract

Each page requests `OPTIONS` on its active collection endpoint and reads DRF `actions.POST.<field>.choices`. If a backend does not expose choices for a field, the page derives only distinct values from active collection records; it does not introduce a local business catalog. Collection responses are normalized through the shared table envelope helper and support the existing pagination, filtering, search, ordering, and CSV-export contracts.
