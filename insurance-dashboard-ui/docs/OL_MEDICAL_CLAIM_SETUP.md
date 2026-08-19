# OL Medical U/W and Claim Setup

The OL Medical U/W and Claim Setup workspace is implemented in `src/pages/ordinary-life/OLMedicalClaimSetup.tsx`. Both routes use the shared table, filter, form-modal, confirmation-modal, access-control, toast, and backend-choice utilities.

## Routes and resources

| Frontend route | Screen group | API resource |
|---|---|---|
| `/ordinary-life/parameters/medical-uw` | OL Medical Underwriting | `/api/v1/ol-parameters/medical-codes/`, `/medical-limits/`, `/personal-habits/`, `/medical-history/`, `/medical-facilities/`, `/medical-practitioners/` |
| `/ordinary-life/parameters/claim-setup` | OL Claim Setup | `/api/v1/ol-parameters/claim-types/`, `/claim-reasons/`, `/claim-statuses/`, `/discharge-types/`, `/correspondent-types/` |

Every resource supports server-side table queries, search, sorting, pagination, effective-date presentation, CSV export, create/edit, permission-gated actions, and row-level deactivation through `/{id}/deactivate/`.

## Medical underwriting screens

| Screen | Main contract | Validation and behavior |
|---|---|---|
| **OL Medical Codes** | Code, name, medical category, description, effective dates | Code, name, category, and effective-from are required; effective dates must be ordered. |
| **OL Medical Limit** | Medical code, optional product/plan scope, age band, sum-assured band, limit type/amount, required frequency, mandatory flag | Age range is constrained to 0–150 and ordered; sum-assured bands cannot be negative or reversed; limit amount must be positive; code, limit type, frequency, and effective-from are required. |
| **OL Personal Habit** | Habit category, question text, underwriting impact, evidence flag | Category, question, and underwriting impact are required. |
| **OL Medical History** | Condition category, severity, waiting period, exclusion flag, loading flag, underwriting note | Category and severity are required; waiting period cannot be negative. |
| **OL Medical Facility** | Facility code/type, registration, location, contacts, approval status, optional partner ID | Facility code, facility type, approval status, and effective-from are required. Table rows show the related partner name/number where the backend supplies it. |
| **OL Medical Practitioners** | Practitioner identity, specialty, license, facility ID, contacts, approval status, optional partner ID | Practitioner code, names, specialty, license, approval status, and effective-from are required. Table rows show facility and partner linkage where supplied by the backend. |

Facility and practitioner partner linkage is display-only in the table and is submitted as an optional partner identifier in the editor. The frontend does not create partner master records from these parameter screens.

## Claim setup screens

| Screen | Main contract | Validation and behavior |
|---|---|---|
| **OL Claim Types** | Claim category, calculation basis, duplicate-check rule, waiting period, payable-to JSON, required-document JSON array, waiver and approval flags | Category, calculation basis, duplicate-check rule, and effective-from are required; waiting period cannot be negative; JSON fields are parsed before submission. |
| **OL Claim Reasons** | Optional claim-type scope, reason category, description | Reason category and effective-from are required. |
| **OL Claim Status** | Ordered status catalog, backend badge type, terminal/payable flags, effective dates, allowed transitions | Badge type and effective-from are required. Terminal statuses cannot have outgoing transitions; self-transitions are rejected. The transition editor presents active statuses loaded from the claim-status API, not a hardcoded list. |
| **OL Discharge Types** | Discharge category, template code, variables JSON object | Discharge category and effective-from are required; variables must be valid JSON object text before submission. |
| **OL Correspondent Types** | Correspondence category, communication channel, purpose, description | Category, channel, and effective-from are required. |

The claim-status transition editor persists `allowed_transitions` through the normal status detail `PATCH` endpoint. Active statuses are fetched from `/claim-statuses/?page_size=100` and rendered as checkbox options. This keeps the graph synchronized with the claim-status catalog and prevents hardcoded state values.

## Backend-driven options and permissions

Select options are loaded from DRF `OPTIONS` metadata through `useRemoteChoices`. When metadata does not contain a choice list, the utility supplements it with distinct values already returned in the active table response. The page therefore does not maintain business enum lists in React code. Status filters use the shared active/inactive table control because `is_active` is a common lifecycle field rather than a business catalog.

Create and edit actions require `ol_parameters` access and the corresponding create/update/write permission. Deactivation requires `ol_parameters.deactivate`. When permission metadata is absent, the existing platform convention treats module access as sufficient, preserving compatibility with installations that authorize at module level.

## Table and modal behavior

The workspace is table-first. Each screen exposes search, server-side pagination, sorting, filter controls, CSV export, empty/loading/error states, effective-date status rendering, and row actions. Create and edit use the shared `FormModal`; deactivation uses `ConfirmModal`. Backend errors are surfaced through the shared toast service while field-level client validation is displayed beside the affected control.

The implementation intentionally keeps product, plan, facility, practitioner, partner, and claim-type relations as backend identifiers unless the API supplies a master-data option list. This avoids inventing or duplicating master-data catalogs in the frontend.
