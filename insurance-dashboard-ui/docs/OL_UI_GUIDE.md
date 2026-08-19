# Ordinary Life Frontend UI Guide

**Status:** v0.4.0-web-ol milestone guide  
**Scope:** Ordinary Life parameter configuration, quotation creation, quotation lifecycle, and proposal handoff  
**Frontend:** React 19, TypeScript, Vite, React Router, TanStack Query-compatible API conventions, React Hook Form, Zod, Tailwind CSS 4

## 1. Purpose and design principles

The Ordinary Life frontend provides a parameter-driven administration surface and a guided quotation work queue. The UI deliberately avoids embedding insurance business values in component code. Product, plan, frequency, fund, rider, benefit, location, agent, and underwriting options are obtained from the corresponding backend endpoints and are rendered with the reusable table, form, modal, drawer, and wizard primitives.

The visual system uses the established ZIC monochrome foundation: white and charcoal surfaces, restrained indigo and blue hierarchy tokens, consistent control heights, compact radii, visible focus states, and clear status badges. The layout is table-first for catalog data and master-detail for transactional records.

> **Core rule:** The frontend validates shape and presents server results; the backend remains the authority for effective dating, applicability, rating, approval, finalization, versioning, expiry, and conversion eligibility.

## 2. Ordinary Life navigation and routes

All routes below are nested under the authenticated `DashboardLayout`. Access metadata is loaded through `/api/v1/iam/me/access`; unauthorized module branches are hidden by the sidebar, while route guards still require an authenticated access token.

| Area | Route | Screen | Primary purpose |
|---|---|---|---|
| OL home | `/ordinary-life/setup` | Ordinary Life workspace | Module landing and navigation |
| Default setup | `/ordinary-life/parameters/default-setup` | Default System Parameters | Effective-dated default values |
| Policy setup | `/ordinary-life/parameters/policy-setup` | Policy Setup | Policy status, renewal, surrender, paid-up, questionnaire, and lifecycle setup |
| Product setup | `/ordinary-life/parameters/product-setup` | Product Setup | Plans, products, tax, market, risk, and investment fund catalogs |
| Product rating | `/ordinary-life/parameters/product-rating` | Product Rating | Premium, mortality, joint-life, bonus, surrender, and loading rate setup |
| Rider setup | `/ordinary-life/parameters/rider-setup` | Rider Setup | Rider definitions and rider rate tables |
| Agent management | `/ordinary-life/parameters/agent-management` | Agent Commission Setup | Agent and intermediary commission configuration |
| Loan setup | `/ordinary-life/parameters/loan-setup` | Loan Setup | Loan system and interest control |
| Medical U/W | `/ordinary-life/parameters/medical-uw` | Medical U/W | Medical catalogs, limits, facilities, practitioners, and history |
| Claim setup | `/ordinary-life/parameters/claim-setup` | Claim Setup | Claim types, reasons, statuses, discharge, and correspondent catalogs |
| Quotation list | `/ordinary-life/quotations` | Quotations work queue | KPI summary, filters, pagination, and state-aware actions |
| New quotation | `/ordinary-life/quotations/new` | Create New Quote | Seven-step quotation wizard |
| Quotation detail | `/ordinary-life/quotations/:id` | Quotation detail | Lifecycle master-detail view |
| Quotation edit | `/ordinary-life/quotations/:id/edit` | Quotation detail/edit | Editable quotation version view |
| Proposal handoff | `/ordinary-life/proposals?quotation=:id` | Proposals | Destination after successful conversion |

Quotation routes are loaded lazily. The application renders an accessible loading status while the quotation list, wizard, or detail chunk is fetched, reducing the initial authenticated workspace bundle.

## 3. Access control

The sidebar and page actions use the IAM metadata contract exposed by `useAccess()`. The access provider recognizes the Django superuser flag before evaluating individual permission entries, so superusers receive unrestricted access to the Ordinary Life parameter and quotation areas.

| Permission key | UI behavior |
|---|---|
| `ol_parameters.view` / `ol_parameters.read` | Show and open OL parameter screens |
| `ol_parameters.create` | Show create actions and save new parameter rows |
| `ol_parameters.update` | Show edit actions and save changes |
| `ol_parameters.deactivate` | Show deactivate actions |
| `ol_quotations.view` | Show the quotations list and detail pages |
| `ol_quotations.update` | Show draft edit and wizard update actions |
| `ol_quotations.destroy` | Show draft deletion actions |
| `ol_quotations.finalize` | Show finalization actions |
| `ol_quotations.print` | Show printout and preview actions |
| `ol_quotations.convert` | Show proposal conversion actions |

The UI also checks quotation state before exposing an action. Drafts can be edited or deleted; finalized quotations can be revised; print is available according to permission and backend state; conversion is only submitted after frontend eligibility checks and is always revalidated by the backend.

## 4. Parameter screens

The parameter groups are implemented as collection-oriented screens. Each screen supports server-backed search or filtering where the endpoint provides it, pagination, status and effective-date presentation, create/edit modals, inline validation, and deactivation where supported. Rate tables additionally use the reusable `EditableGrid` pattern with decimal-safe inputs, dimension filters, totals, CSV import feedback, and CSV export.

| Group | Representative entities |
|---|---|
| Default Setup | Default system parameters, override commission, computation approach, maturity claim setup |
| Policy Setup | Anticipated endowment rates, grace periods, policy statuses, renewal statuses, beneficial types, member cover, surrender, paid-up, surrender-value rates, paid-up rates, commitment statuses, health questions, questionnaire builder, notification schedules, reinstatement windows |
| Product Setup | Plan types, products, plan tax configurations, target market, risk categories, occupation limits, investment fund types, investment funds |
| Product Rating | Premium rates, mortality rates, joint-life setup, reinstatement interest, bonus rates, mortgage factors, installment charges, cash surrender values, reserve loadings |
| Rider Setup | Riders and rider rate tables |
| Agent Management | Agent commission setup |
| Loan Setup | Loan system setup and loan interest control |
| Medical U/W | Medical codes, medical limits, personal habits, medical history, facilities, practitioners |
| Claim Setup | Claim types, reasons, statuses and transitions, discharge types, correspondent types |

Options in forms are sourced from master-data responses, product configuration, or the relevant parameter collection. A form should display a clear empty state rather than inventing a fallback business option when the backend has returned no active values.

## 5. Quotation list and work queue

The quotation work queue displays KPI counts for drafts, finalized, converted, and expired quotations. The main table contains quote number, quote name, prospect, plan summary, total premium, currency, status, version, quote date, agent, and creator. Search supports quote number, name, and identity number; filters include status, plan, agent, location, and date range.

Row actions are state-aware. The list delegates view navigation to the detail route, opens the wizard for new drafts, and does not duplicate business calculations in the browser. Any API error is normalized by the shared client and presented through the ZIC toast pattern or an inline table state.

## 6. Seven-step quotation wizard

The wizard creates a draft quotation and progressively persists each step. The step navigation displays completed and invalid states, and the footer prevents moving forward when the current step cannot be saved. Draft snapshots are also stored locally for resume behavior; the server remains the source of truth.

| Step | UI responsibility | Main API contract |
|---|---|---|
| Personal Details | Quote identity, dates, prospect identity, gender, smoker status, location, agent, and address | `POST /api/v1/ol-quotations/quotations/`; `GET .../{id}/personal-details-options/`; `POST .../{id}/personal-details/` |
| Plan & Sub-Products | Search and select plans, then configure term, payment period, frequency, basis, maturity estimate, joint life, mortgage, PA, WP, and bonus inputs | `GET .../{id}/plan-options/`; `POST .../{id}/plans/`; `PATCH .../{id}/plans/{configuration_id}/` |
| Member Coverage | Principal member card and conditional additional coverage grid | `GET .../{id}/members/`; `POST/PATCH .../{id}/members/`; `DELETE .../{id}/members/{member_id}/` |
| Installments | Configure annuity period, payment mode, inherited policy term, computed installment count, benefit timing, and rate rows | `GET .../{id}/installments/`; `GET .../{id}/installments/{plan_configuration_id}/template/`; `POST .../{id}/installments/{plan_configuration_id}/configure/` |
| Investment Funds | Show not-applicable state for non-investment plans; otherwise allocate active funds and validate totals | `GET .../{id}/investment-funds/`; `GET .../{id}/investment-funds/options/`; `POST .../{id}/investment-funds/` |
| Riders & Benefits | Attach applicable riders, configure benefit basis and caps, and synchronize PA/WP mapping | `GET .../{id}/riders/`; `GET .../{id}/riders/options/`; `POST .../{id}/riders/` |
| Financial Details | Request backend rating output, display premium breakdown, projections, and payout schedule, then review and finalize | `GET .../{id}/financial-details/`; `POST .../{id}/calculate/`; `POST .../{id}/finalize/` |

The browser only formats backend financial output. It does not calculate premiums, taxes, rider rates, surrender values, bonuses, or payout amounts.

## 7. Quotation detail lifecycle

The detail page is a master-detail shell with a summary header and nine tabs: Overview, Plans, Members, Installments, Funds, Riders & Benefits, Financials, Versions, and Documents. The header exposes quote number, quote name, status, version, currency, quote date, expiry date, and key prospect information.

| Detail feature | Endpoint | UI behavior |
|---|---|---|
| Detail summary | `GET .../{id}/` | Load header and overview values |
| Versions | `GET .../{id}/versions/` | Render historical list and status badges |
| As-of view | `GET .../{id}/as-of-version/{version_number}/` | Load a retained snapshot without mutating the current record |
| Revise | `POST .../{id}/revise/` | Request a new editable version from a finalized quotation |
| Partner verification | `GET .../{id}/partner-verification/` | Show partner existence, compliance, and missing fields |
| Partner completion | `POST .../{id}/partner-completion/` | Submit required KYC fields and link the partner |
| Financial details | `GET .../{id}/financial-details/` | Render server-produced breakdown and projections |
| Recalculation | `POST .../{id}/calculate/` | Refresh financial output and clear recalculation-required state |
| Print | `POST .../{id}/print/` | Generate a source-linked quotation document, with preview mode supported |
| Documents | `GET .../{id}/documents/` | List generated printouts and template versions |
| Finalize | `POST .../{id}/finalize/` | Lock the current version after backend validation |
| Convert | `POST .../{id}/convert-to-proposal/` | Handoff to proposal creation after BR-01 eligibility checks |

The versions drawer exposes current and superseded versions, supports switching to an as-of snapshot, and provides a revise action where allowed. Generated document rows preserve the quotation version, template code, and template version returned by the backend.

## 8. Business-rule presentation

The frontend surfaces the following lifecycle rules before submission and displays backend validation errors when the server provides a more authoritative result.

| Rule | Presentation |
|---|---|
| Partner verification before conversion | Verification banner, missing-field list, and partner-completion modal |
| Finalized status before conversion | Conversion modal eligibility error |
| Expiry check | Expiry status and conversion eligibility error |
| Approval-required flag | Persistent approval banner and conversion block |
| Recalculation after input changes | Financial-details warning and disabled finalization until recalculation |
| Complete wizard steps before finalization | Review checklist with jump-to-step controls |
| BR-02 version preservation | Versions tab and revise flow; prior versions are never silently overwritten |

## 9. Shared accessibility behavior

All modal and drawer surfaces use `role="dialog"`, `aria-modal="true"`, a labelled heading, labelled close controls, Escape-to-close behavior, body scroll locking, focus-on-open, focus trapping with Tab and Shift+Tab, and focus restoration to the previously active element. The route-level Suspense fallback uses a live status region so users of assistive technology receive feedback during lazy chunk loading.

Interactive controls use visible text wherever possible. Icon-only controls, including close buttons and drawer dismissal controls, have explicit accessible labels. Tables expose captions through the reusable table shell, and status indicators include text rather than relying on color alone.

## 10. Source references inside the repository

The primary implementation references are the [quotation detail page](../src/pages/ordinary-life/OLQuotationDetail.tsx), [quotation wizard](../src/pages/ordinary-life/OLQuotationWizard.tsx), [quotation list](../src/pages/ordinary-life/OLQuotations.tsx), [application routes](../src/App.tsx), [access provider](../src/lib/access.tsx), and [overlay primitives](../src/components/ui/Overlays.tsx). These files are the authoritative examples when extending the module.
