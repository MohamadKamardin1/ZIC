# OL Option and Quick-Create Registry Contract

## Scope

The Ordinary Life option registry provides a stable, labeled reference-data API for quotation and parameter screens. It centralizes option lookup, active/effective filtering, search, pagination, schema discovery, permission enforcement, creation, and audit logging.

The registry is extensible: adding an entity requires a canonical provider entry and, when inline creation is supported, a `QuickCreateSpec` containing its permission, field schema, and creator function.

## Option list endpoint

```text
GET /api/v1/ol/options/<entity>/?q=<search>&page=1&page_size=50
```

The endpoint returns a paginated payload with the standard option shape:

```json
{
  "items": [
    {
      "value": "6d4c…",
      "label": "008 — Boresha Elimu",
      "meta": {
        "code": "008",
        "name": "Boresha Elimu",
        "plan_type_id": "…"
      }
    }
  ],
  "count": 1,
  "page": 1,
  "page_size": 50,
  "has_next": false
}
```

`value` is the identifier submitted by the client. `label` is the only field intended for direct user display. `meta` contains non-authoritative context such as codes, related IDs, categories, and display labels. Clients must not substitute an identifier for a label.

Providers exclude inactive records and records outside their effective date window. Search is case-insensitive across the provider’s code, name, and configured display fields. Pagination is mandatory for large entities such as products, agents, and riders.

## Registered wizard entities

| Entity | Purpose | Inline-create permission |
| --- | --- | --- |
| `identity-types` | Personal identity document types | `system_parameters.manage` |
| `locations` | Partner branches and quotation locations | `ol_parameters.create` |
| `agents` | Agent/intermediary partners | `partners.create` |
| `products` | Ordinary Life products/plans | `ol_parameters.create` |
| `plan-types` | Product plan type catalog | `ol_parameters.create` |
| `payment-frequencies` | Premium payment frequencies | `system_parameters.manage` |
| `quote-bases` | Quotation basis catalog | `system_parameters.manage` |
| `premium-factors` | Premium factor catalog | `system_parameters.manage` |
| `member-relations` | Additional member relationship catalog | `system_parameters.manage` |
| `cover-types` | Member cover catalog | `system_parameters.manage` |
| `payment-modes` | Installment payment modes | `system_parameters.manage` |
| `investment-funds` | Investment fund catalog | `ol_parameters.create` |
| `investment-fund-types` | Investment fund type catalog | `ol_parameters.create` |
| `riders` | Rider setup catalog | `ol_parameters.create` |
| `benefit-types` | Wizard benefit choice catalog | `system_parameters.manage` |
| `benefit-types-catalog` | Full OL benefit setup records | `ol_parameters.create` |
| `currencies` | Currency catalog | `system_parameters.manage` |

## Quick-create schema endpoint

```text
GET /api/v1/ol/options/<entity>/quick-create-schema/
```

The response describes the minimum valid record form:

```json
{
  "entity": "products",
  "permission": "ol_parameters.create",
  "fields": [
    {
      "name": "code",
      "type": "string",
      "required": true,
      "choices": [],
      "default": null
    },
    {
      "name": "plan_type",
      "type": "select",
      "required": true,
      "choices": [
        {"value": "…", "label": "IND — Individual"}
      ],
      "default": null,
      "nested_entity": "plan-types"
    }
  ],
  "defaults": {}
}
```

Each field declares `name`, `type`, `required`, `choices`, and `default`. Supported types include `string`, `email`, `decimal`, `boolean`, and `select`. A select may declare `nested_entity` when its parent can create a missing related record inline. Dynamic choices are resolved from active registry data at schema-request time.

The minimal schemas are:

| Entity | Required/minimal fields |
| --- | --- |
| Choice-backed catalogs | `code`, `name` |
| `locations` | `code`, `name`, `branch` |
| `agents` | `partner_type`, `legal_name`, `phone`, `email`; `national_id` optional |
| `plan-types` | `code`, `name`; `plan_category` defaults to `INDIVIDUAL` |
| `investment-fund-types` | `code`, `name`; `risk_profile` defaults to `MODERATE` |
| `investment-funds` | `code`, `name`, `fund_type`; currency and valuation frequency have defaults |
| `products` | `code`, `name`, `plan_type`; insurance class and capability flags have defaults |
| `riders` | `code`, `name`, `rider_category`, `benefit_type`; calculation basis defaults to sum assured |
| `benefit-types-catalog` | `code`, `name`; category, basis, and ratio have defaults |

## Quick-create mutation endpoint

```text
POST /api/v1/ol/options/<entity>/quick-create/
Content-Type: application/json
```

A successful response returns a selectable option:

```json
{
  "id": "6d4c…",
  "code": "OL-E2E",
  "name": "E2E Product",
  "value": "6d4c…",
  "label": "OL-E2E — E2E Product",
  "meta": {
    "code": "OL-E2E",
    "name": "E2E Product",
    "plan_type_id": "…",
    "investment_linked": false
  }
}
```

The client should immediately select `value` and use `label` for display. The server performs the operation atomically and marks newly created records active. Related IDs may be supplied as primary keys or canonical codes where the creator supports both; the creator resolves them to active records before saving.

## Enforcement and audit

Before creation, the registry resolves the canonical entity and checks its declared permission. Superusers are allowed through Django’s server-side superuser check. Other users must have the mapped module/action permission; a missing permission returns HTTP 403.

Creators apply required-field validation, enum validation, active foreign-key resolution, and case-insensitive duplicate checks for code and name. Integrity errors are converted into field-level validation messages. Location duplicates are scoped to the selected branch. Agent creation also prevents duplicate email, phone, or national identification values and records whether KYC completion is still required.

Every successful quick-create operation writes an audit record using:

```text
source_channel = QUICK_CREATE
reason         = Created from OL quotation wizard
```

The same shared setup and audit services used by full parameter creation are used wherever the underlying model supports them. Choice-backed records invalidate configuration caches after creation. Nested records are audited independently, and the parent record is audited after its related reference has been resolved.

## Frontend integration requirements

The React `SmartSelect` component consumes the list endpoint and normalizes `value`, `label`, and `meta`. It reads the permission metadata supplied by `/api/v1/iam/me/access`; it must hide both `+` and `Manage…` when the required create permission is absent. The quick-create modal consumes the schema endpoint, posts to the mutation endpoint, invalidates the entity query, and selects the returned option.

Fixed enums such as gender, smoker, joint life, mortgage, personal accident, and premium waiver remain ordinary enum controls. They are not option-registry entities and must not expose a quick-create button.

## Compatibility and testing contract

New providers must include tests for labeled results, active/effective filtering, search, pagination where applicable, and human-readable related-object metadata. New quick-create specs must include success, permission denial, duplicate detection, schema shape, and `QUICK_CREATE` audit assertions. Quotation serializers must expose `*_display` fields alongside foreign-key IDs so list and detail views never need to render bare UUIDs.
