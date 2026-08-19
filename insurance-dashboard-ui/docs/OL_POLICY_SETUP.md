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


## Policy Setup part 2

The second Policy Setup set extends the same workspace with five additional API-backed tabs:

| Screen | Collection endpoint | Primary configuration |
|---|---|---|
| OL Surrender Setup | `/api/v1/ol-parameters/surrender-setups/` | Minimum premiums, paid-premium ratio, charge type/value, partial surrender, and approval requirement |
| OL Paid-Up Setup | `/api/v1/ol-parameters/paid-up-setups/` | Eligibility years, minimum premium ratio, conversion basis, and approval requirement |
| OL Surrender Value Rate | `/api/v1/ol-parameters/surrender-value-rates/` | Version scope plus product/plan, gender, smoker, age, term, policy-year, and rate-factor dimensions |
| OL Paid-Up Rate | `/api/v1/ol-parameters/paid-up-rates/` | Version scope plus product/plan, gender, smoker, age, term, policy-year, and rate-factor dimensions |
| OL Commitment Status | `/api/v1/ol-parameters/commitment-statuses/` | Display order, configured badge type, terminal flag, and applicability scope |

Surrender-value and paid-up rate screens use `EditableGrid` for multi-dimensional rate rows. Version metadata is shown in the table with version number, effective dates, active/scheduled/expired state, and configured status badge. Dimension values are entered as decimal-safe fields where appropriate, and row-level validation reports invalid ranges, negative factors, and incomplete dimensions inline. The grid provides add, edit, remove, and total-row behavior without introducing a second table implementation.

The rate tables expose the shared `DataTable` CSV export action. CSV import is available for versioned rate screens through the table import control. The client maps supported CSV columns to the backend payload, normalizes blank numeric dimensions to null, submits each row independently, and retains errors by source row number. Malformed files and backend overlap/validation responses are displayed in an inline error banner so accepted rows remain visible while rejected rows can be corrected and retried.

Effective-date overlap and duplicate-scope checks remain server-authoritative. When the backend rejects a version or rate row because its effective scope overlaps an existing configuration, the shared toast and import error surfaces preserve the backend message rather than replacing it with a generic client-side error. All create, update, import, export, and deactivate actions remain governed by the existing `ol_parameters` permissions.

## Part 2 assumptions

The frontend treats rate-version records and rate rows as one backend collection because the current API exposes the same collection and row-level actions. When the backend represents one version as multiple rows, editing the first row updates the version metadata and additional grid rows are posted as new rows carrying the same serialized version scope. Product, plan, gender, smoker, frequency, charge, basis, and status choices are supplied by API payloads or existing table metadata; no new business catalogs are hardcoded in the page.

The commitment-status screen is implemented as a catalog editor using the same lifecycle and badge rendering rules as Policy Status. The route remains `/ordinary-life/parameters/policy-setup`, so the existing navigation and access mapping continue to cover both Policy Setup parts without adding a second permission surface.

## Policy Setup part 3: health and lifecycle parameters

The remaining workspace includes four additional API-backed experiences:

| Screen | Collection endpoint | Primary configuration |
|---|---|---|
| OL Health Questions | `/api/v1/ol-parameters/health-questions/` | Catalog code, question text, category, answer type, underwriting impact, and medical follow-up |
| OL Health Questionnaires | `/api/v1/ol-parameters/health-questionnaires/` | Version, scope, product/plan/scheme applicability, sum-assured and age thresholds, and effective dates |
| Grace Period Notification Schedule | `/api/v1/ol-parameters/grace-period-notification-schedules/` | Event type, signed day offset, channel, recipient, template, and effective dates |
| Reinstallment / Reinstatement Window | `/api/v1/ol-parameters/reinstatement-windows/` | Lapse window, maximum reinstatements, medical underwriting, outstanding premium requirement, interest, and penalty rates |

The questionnaire builder loads active catalog questions from `/api/v1/ol-parameters/health-questions/`, then persists the questionnaire header and ordered item rows through `/api/v1/ol-parameters/health-questionnaires/` and `/api/v1/ol-parameters/health-questionnaire-items/`. The builder supports add, remove, up/down reorder, sequence renumbering, mandatory and trigger-medical flags, score, threshold fields, effective dates, and a live preview. Existing questionnaires can be copied into a new version; current and superseded badges are derived from active state and effective dates.

Builder changes are held locally until save, shown with an **Unsaved changes** badge, and protected by browser unload handling and an in-workspace confirmation before leaving the builder. Lifecycle forms use the existing inline validation and backend-authoritative error flow. No answer type, scope, channel, recipient, event, or reinstatement option catalog is hardcoded in the frontend.
