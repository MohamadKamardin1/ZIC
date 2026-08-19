# OL Policy Setup — Frontend

The Policy Setup workspace is available at `/ordinary-life/parameters/policy-setup` and uses the shared table, filter, modal, form-control, status-badge, and editable-grid components.

## Screens

The workspace contains six API-backed tabs:

| Screen | Collection endpoint | Primary configuration |
|---|---|---|
| Anticipated Endowment Installment Rate | `/api/v1/ol-parameters/anticipated-endowment-rates/` | Product/plan scope, frequency, age/term/policy-year ranges, rate factor, currency |
| OL Grace Period | `/api/v1/ol-parameters/grace-periods/` | Product/plan scope, premium frequency, grace, warning, pre-lapse, lapse days, minimum due amount |
| OL Policy Status | `/api/v1/ol-parameters/policy-statuses/` | Display order, configured badge type, terminal flag, allowed transitions |
| OL Policy Renewal Status | `/api/v1/ol-parameters/policy-renewal-statuses/` | Display order and renewal action |
| OL Beneficial Type | `/api/v1/ol-parameters/beneficial-types/` | Category, calculation basis, default ratio, multiplicity |
| OL Member Cover Configuration | `/api/v1/ol-parameters/member-cover-configurations/` | Product/plan scope, cover type, relation, age limits, waiting period, benefit limit, premium/coverage basis |

Each table supports backend search, filtering, pagination, sorting, CSV export, configured status badges, effective-date state display, and permission-gated row actions. Active, scheduled, expired, and inactive records are visually distinguished without introducing hardcoded business-state data into the page.

## Editing and validation

Create and edit operations use the shared `FormModal`. Effective dates, required identifiers, and basic numeric/range validation are checked before requests are sent. The backend remains authoritative for overlap detection, product-plan linkage, decimal precision, catalog consistency, and lifecycle constraints.

The anticipated installment screen uses `EditableGrid` for one or more rate rows. A create operation posts each grid row to the collection endpoint; an edit updates the existing row and posts any additional rows. The row editor validates non-negative rate factors and ordering of age, term, and policy-year ranges.

The policy-status transition editor loads active statuses from the policy-status collection itself. It presents checkbox targets dynamically, excludes self-transitions, persists the selected status codes as `allowed_transitions`, and blocks terminal statuses from having outgoing transitions. No status, category, frequency, action, or basis catalog is duplicated in frontend source code.

## Permissions and deactivation

The page uses the existing `ol_parameters` access metadata. View permission controls table visibility and row-action availability. Create and update permissions control the New setup and Edit actions. Deactivate permission controls the confirmation-gated Deactivate action. Deactivation calls `POST {collection}/{id}/deactivate/` and preserves the server-side audit history.

## Routing and navigation

`App.tsx` maps `/ordinary-life/parameters/policy-setup` to `OLPolicySetup`. The existing access-aware Ordinary Life Parameters submenu already exposes Policy Setup alongside the remaining parameter groups, and the existing `/ordinary-life/parameters` route prefix maps to `ol_parameters` access metadata.
