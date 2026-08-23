# Ordinary Life Quotations API Reference

## Base URL and response envelope

The primary API base is `/api/v1/ol-quotations/`. A compatibility plan-search route is also mounted under `/api/v1/ol/plans/search/`.

Successful responses use the platform envelope:

```json
{
  "success": true,
  "message": "Human-readable result message.",
  "data": {}
}
```

Paginated list responses retain the standard pagination fields inside `data`. Validation and domain failures use the platform error envelope with field-level details. UUID values are serialized as strings and timestamps use ISO-8601 format.

## Authentication and permissions

All endpoints require authenticated users. Superusers bypass the module permission check. Other users need the action-specific permission shown below and remain subject to visible-partner row-level authorization.

| Permission | Scope |
|---|---|
| `ol_quotations.view` | Read quotations, wizard state, options, documents, versions, and partner verification. |
| `ol_quotations.create` | Create quotation drafts. |
| `ol_quotations.update` | Update draft wizard data, calculate, and complete a partner. |
| `ol_quotations.delete` | Delete a non-expired draft. |
| `ol_quotations.print` | Generate printable documents and explicitly requested draft previews. |
| `ol_quotations.finalize` | Finalize a valid calculated quotation. |
| `ol_quotations.revise` | Revise a finalized quotation into a new editable version. |
| `ol_quotations.expire` | Persist expiry transitions. |
| `ol_quotations.convert` | Convert a verified finalized quotation into an `OLProposal`. |

## Quotation resource and work queue

| Method | Endpoint | Permission | Behavior |
|---|---|---|---|
| `GET` | `/quotations/` | View | Paginated searchable/filterable quotation work queue. |
| `POST` | `/quotations/` | Create | Create a draft quotation. |
| `GET` | `/quotations/{id}/` | View | Retrieve quotation detail and current aggregate state. |
| `PATCH` | `/quotations/{id}/` | Update | Update permitted draft header fields. |
| `DELETE` | `/quotations/{id}/` | Delete | Delete only a non-expired draft quotation. |
| `GET` | `/quotations/summary/` | View | Return draft, finalized, converted, and expired KPI counts. |
| `GET` | `/quotations/{id}/wizard-summary/` | View | Return authoritative completion state for every wizard/handoff step. |

The list endpoint supports `search`, `status`, `plan`, `agent`, `location`, `quote_date_from`, `quote_date_to`, `ordering`, and standard pagination parameters. Row actions are state- and permission-aware: edit is draft-only, revise is finalized-only, print is finalized or converted, convert requires finalized plus verified partner, and delete is draft-only.

## Personal Details

| Method | Endpoint | Permission | Behavior |
|---|---|---|---|
| `POST`, `PATCH` | `/quotations/{id}/personal-details/` | Update | Save identity, quote date, date of birth, computed age, gender, smoker status, location, agent, and address. |
| `GET` | `/quotations/personal-details-options/` | View | Return parameter-backed identity/gender/smoker choices, active locations, and active agent partners. |

The server computes `age_at_quote` from date of birth and quote date. Date of birth cannot be in the future or outside configured age limits. Matching partner information is returned as a hook in the personal-details response, but this step never creates a partner.

Example request:

```json
{
  "quote_name": "Asha Life Protection",
  "quote_date": "2026-08-19",
  "identity_type": "NIN",
  "identity_number": "NIN-000123",
  "date_of_birth": "1990-04-15",
  "gender": "FEMALE",
  "smoker_status": "NON_SMOKER",
  "location_id": "uuid",
  "agent_id": "uuid",
  "address": "Zanzibar Town"
}
```

## Plans and plan configuration

| Method | Endpoint | Permission | Behavior |
|---|---|---|---|
| `GET` | `/api/v1/ol/plans/search/` | View | Search active effective Ordinary Life plans with product/plan metadata and capability badges. |
| `GET` | `/quotations/{id}/plan-options/` | View | Return parameter-backed frequencies, quote bases, premium factors, and feature availability. |
| `POST` | `/quotations/{id}/plans/` | Update | Select one or more plans in submitted order and create/update section configurations. |
| `PATCH` | `/quotations/{id}/plans/{configuration_id}/` | Update | Configure term, payment period, frequency, basis, maturity, factor, and feature toggles. |

Selection order determines section numbering. Product setup validates policy term, payment period, entry age, frequency, and required positive amounts. Joint life, mortgage, PA, WP, and bonus defaults are resolved from active OL parameters and plan applicability.

## Member Coverage

| Method | Endpoint | Permission | Behavior |
|---|---|---|---|
| `GET` | `/quotations/{id}/members/` | View | Return the immutable principal card, applicable configuration, and dependent rows. |
| `POST` | `/quotations/{id}/members/` | Update | Add a dependent when selected plans require additional coverage. |
| `PATCH` | `/quotations/{id}/members/{member_id}/` | Update | Update a dependent; principal member is immutable here. |
| `DELETE` | `/quotations/{id}/members/{member_id}/` | Update | Remove a dependent. |

Member age, relation, duplicate identity, coverage basis, waiting period, and benefit limits are resolved from OL Member Cover Configuration. If no selected plan requires extra coverage, the state response returns `requires_additional_coverage=false` and the configured informational banner.

## Installments

| Method | Endpoint | Permission | Behavior |
|---|---|---|---|
| `GET` | `/quotations/{id}/installments/` | View | Return one status row per selected plan configuration. |
| `GET` | `/quotations/{id}/installments/{plan_config_id}/template/` | View | Load effective anticipated-endowment installment rows or return `has_template=false`. |
| `POST` | `/quotations/{id}/installments/{plan_config_id}/configure/` | Update | Persist annuity period, payment mode, maturity toggles, and ordered rate rows. |

The inherited policy term is server-controlled. Rate percentages must sum exactly to `100`. Paid-up values default from OL Paid-Up Rate when available, and the persisted total installment count is the number of saved rate rows. **Premium frequency and payment mode are separate values:** premium frequency is resolved from the selected product version for rating and template lookup; payment mode is resolved from the active `OL_PAYMENT_MODE_CHOICES` catalog and stored on the installment configuration. Product versions may restrict active methods through `servicing_rules.installment_payment_modes`. The template response returns the effective `available_payment_modes` list, and the frontend filters the Payment Mode selector to that list. Configure premium frequencies under `Ordinary Life Parameters → Product Setup → OL Product`; configure payment methods under `Ordinary Life Parameters → Drop Down Configuration → Payment Modes`; configure the selected quotation’s annuity period, maturity toggles, and payout rows under `Ordinary Life Quotations → Installments → Configure`.

## Investment Funds

| Method | Endpoint | Permission | Behavior |
|---|---|---|---|
| `GET` | `/quotations/{id}/investment-funds/` | View | Return applicability and saved allocations per selected plan. |
| `GET` | `/quotations/{id}/investment-funds/options/` | View | Return active effective funds with fund type, risk profile, currency, and valuation frequency. |
| `POST` | `/quotations/{id}/investment-funds/` | Update | Replace allocations for applicable plans. |

Each applicable plan’s allocations must total exactly `100%`. Inactive funds and incompatible currencies are rejected unless effective fund allocation rules explicitly allow conversion.

## Riders and Benefits

| Method | Endpoint | Permission | Behavior |
|---|---|---|---|
| `GET` | `/quotations/{id}/riders/` | View | Return saved rider selections and benefits. |
| `GET` | `/quotations/{id}/riders/options/` | View | Return active riders applicable to the selected plan, age, term, and sum assured. |
| `POST` | `/quotations/{id}/riders/` | Update | Replace rider and benefit selections for the quotation. |

Supported benefit bases are parameter-backed and validated as `FIXED`, `RATIO`, `LOADED`, `DISCOUNTED`, or `CAPPED`. PA and WP plan toggles synchronize to matching configured riders where applicable. Duplicate riders and out-of-range age, term, or sum assured selections are rejected.

## Financial Details and rating

| Method | Endpoint | Permission | Behavior |
|---|---|---|---|
| `POST` | `/quotations/{id}/calculate/` | Update | Resolve effective rates/factors and persist the current financial summary. |
| `GET` | `/quotations/{id}/financial-details/` | View | Return premium components, taxes, projections, installments, and recalculation state. |

The rating engine uses Decimal values and parameter-backed effective rows. A missing mandatory base rate is a blocking error. The summary includes `input_fingerprint`; the GET response returns `recalculation_required=true` when the persisted fingerprint is absent or no longer matches current quotation inputs.

## Lifecycle and versioning

| Method | Endpoint | Permission | Behavior |
|---|---|---|---|
| `POST` | `/quotations/{id}/finalize/` | Finalize | Validate wizard completion and current calculation, then set `FINALIZED`. |
| `POST` | `/quotations/{id}/revise/` | Revise | Snapshot the finalized version and return the active quotation to editable `DRAFT`. |
| `POST` | `/quotations/{id}/expire/` | Expire | Persist an eligible expired transition. |
| `GET` | `/quotations/{id}/versions/` | View | List immutable quotation versions. |
| `GET` | `/quotations/{id}/as-of-version/{version_number}/` | View | Retrieve an immutable version snapshot. |

Finalization can set `approval_required=true` when configured thresholds are exceeded. An unresolved approval requirement blocks proposal conversion.

## Printable documents

| Method | Endpoint | Permission | Behavior |
|---|---|---|---|
| `POST` | `/quotations/{id}/print/` | Print | Generate and persist HTML/PDF quotation output. |
| `GET` | `/quotations/{id}/documents/` | View | List generated documents with source quotation/version and template provenance. |

Print generation stores `OLQuotationDocument` with the source quotation, immutable source version, print template/version, actor, timestamp, MIME type, and file references. Draft preview requires explicit `preview=true`; expired quotations are never printable.

## Partner verification and completion

### Verify an existing partner

```http
GET /api/v1/ol-quotations/quotations/{id}/partner-verification/
```

Example response data:

```json
{
  "partner_exists": true,
  "partner_id": "uuid",
  "partner_number": "PT-2026-000001",
  "partner_display_name": "Asha Ali",
  "compliant": true,
  "missing_fields": []
}
```

Matching uses quotation `identity_type`, `identity_number`, and `date_of_birth`. Compliance is true only for an active partner whose `status` is `ACTIVE` and `is_active` is true. The endpoint links the matching record to the quotation; it does not create a missing partner.

### Complete a missing individual partner

```http
POST /api/v1/ol-quotations/quotations/{id}/partner-completion/
Content-Type: application/json
```

Request fields are optional at the transport layer because quotation Personal Details prefill the values; onboarding validation determines the final required set:

```json
{
  "first_name": "Asha",
  "other_name": "Salim",
  "surname": "Ali",
  "email": "asha@example.com",
  "mobile_number": "+255777000000",
  "gender": "FEMALE",
  "date_of_birth": "1990-04-15",
  "identification_type": "NIN",
  "identification_number": "NIN-000123",
  "nationality": "Tanzanian",
  "occupation": "Business owner"
}
```

Successful response data:

```json
{
  "quotation_id": "uuid",
  "partner_id": "uuid",
  "partner_number": "PT-2026-000001",
  "partner_verified": true,
  "application_id": "uuid"
}
```

The operation delegates application creation, submission, review, compliance approval, duplicate checks, and partner conversion to onboarding services. Configured missing nested KYC/document/contact/bank requirements are returned as validation errors rather than bypassed.

## Proposal conversion and BR-01 errors

Primary endpoint:

```http
POST /api/v1/ol-quotations/quotations/{id}/convert-to-proposal/
Content-Type: application/json
```

The request body is optional and may include workflow notes:

```json
{
  "notes": "Ready for proposal underwriting."
}
```

The legacy-compatible alias `/quotations/{id}/convert/` returns the same contract. Successful response data is an `OLProposal` representation:

```json
{
  "id": "uuid",
  "proposal_number": "OLP-2026-000001",
  "status": "DRAFT",
  "quotation_id": "uuid",
  "quotation_version_id": "uuid",
  "created_at": "2026-08-19T14:10:00Z"
}
```

Conversion is blocked with a validation response when the quotation is draft, expired, already converted, partner verification has not succeeded, or `approval_required=true`. The quotation changes to `CONVERTED` only after the proposal skeleton is created. A unique quotation/version constraint prevents duplicate conversion of the same finalized version.

## Events and audit

The module writes central audit records for wizard mutations, verification, partner completion, printing, lifecycle changes, and conversion. The transactional outbox event types relevant to this API include:

| Event | Emitted when |
|---|---|
| `QuotationCreated` | Draft is created. |
| `QuotationUpdated` | Quotation or wizard child data changes. |
| `QuotationPremiumCalculated` | Financial summary is recalculated. |
| `QuotationFinalized` | Finalization succeeds. |
| `QuotationVersionCreated` | Revision creates an immutable version. |
| `QuotationExpired` | Expiry is persisted. |
| `QuotationDocumentGenerated` | Print output is generated. |
| `PartnerVerified` | Matching compliant partner is linked. |
| `PartnerCompleted` | Onboarding completion creates and links a partner. |
| `QuotationConverted` | Quotation status changes to `CONVERTED`. |
| `ProposalCreated` | `OLProposal` handoff skeleton is persisted. |

Each event carries the quotation aggregate identifier and actor metadata; proposal conversion also carries proposal and quotation-version references.

## Administration and seeding

Quotation and proposal records are registered in table-first admin views with filters, search, ordering, and read-only provenance fields. Run the idempotent seed command after migrations:

```bash
python manage.py migrate
python manage.py seed_ol_quotations
python manage.py seed_ol_quotations
```

The seed command configures quotation permissions, role groups, quotation/proposal numbering prefixes, lifecycle defaults, and the configured quotation partner-type code without duplicating existing rows.

## Standardized OL option registry

The quotation wizard uses the authenticated registry endpoint:

```http
GET /api/v1/ol/options/<entity>/?q=<search>&page=1&page_size=50
```

The supported entities are `identity-types`, `locations`, `agents`, `products`, `plan-types`, `payment-frequencies`, `quote-bases`, `premium-factors`, `member-relations`, `cover-types`, `payment-modes`, `investment-funds`, `investment-fund-types`, `riders`, `benefit-types`, and `currencies`. A compatibility route is also available below `/api/v1/ol-quotations/options/<entity>/`.

Each option is returned in the stable shape `{value, label, meta}`. `value` is the canonical UUID or code used for writes, while `label` is always human-readable, for example `008 — Boresha Elimu`, `National ID (NIDA)`, or `TZS — Tanzanian Shilling`. `meta` carries entity-specific details such as branch, product, plan, fund type, risk profile, currency, and status.

Catalog providers exclude inactive records and records outside their effective date window. Product, agent, and rider providers support case-insensitive `q` search and all providers support bounded pagination through `page` and `page_size` (maximum 200). Unknown entities return HTTP 404 with the available entity list.

All model-backed OL quotation and parameter serializers retain UUID foreign-key fields for write compatibility but also expose a matching `<field>_display` field. The display field is the authoritative presentation value for UI tables, detail pages, and select controls; clients must never render a foreign-key UUID directly. Quotation headers additionally expose `agent_display`, `location_display`, and `currency_display` aliases for the wizard’s personal-details and summary views.

The baseline `seed_ol_quotations` command is idempotent and seeds identity types, payment modes, premium frequencies, quote bases, premium factors, member relations, cover types, benefit types, and currencies. The unified Zanzibar demo seeder adds the canonical location and demo-agent prerequisites. No seed operation flushes or destructively resets existing data.


## OL option quick-create

The quotation wizard can discover and create missing reference data through the registry-driven endpoints:

```text
GET  /api/v1/ol/options/<entity>/quick-create-schema/
POST /api/v1/ol/options/<entity>/quick-create/
```

The schema response is wrapped in the standard API envelope and returns `entity`, `permission`, `fields`, and `defaults`. Each field contains `name`, `type`, `required`, `choices`, and `default`. Relational fields such as `branch`, `plan_type`, and `fund_type` expose current active choices as human-readable labels.

Successful creation returns a selectable option under `data.option` together with top-level `value` and `label` fields. The created option includes its persisted `id`, canonical `code`, human-readable `name`, and `meta` information. Validation failures return HTTP 400 with field-level `errors`; users missing the entity permission receive HTTP 403.

The current quick-create permission map is:

| Entity family | Required permission |
|---|---|
| Choice-backed catalogs | `system_parameters.manage` |
| Locations, products, plans, funds, fund types, riders, benefit catalog | `ol_parameters.create` |
| Agents/intermediaries | `partners.create` |

Every successful quick-create operation uses the existing model validation and creation service where applicable and writes an audit record with source channel `QUICK_CREATE` and reason `Created from OL quotation wizard`. Agent creation also marks incomplete KYC through `meta.completion_required` in the returned option.
