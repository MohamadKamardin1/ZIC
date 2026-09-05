# GC Parameters — REST API

The GC Parameters bounded context is exposed as two REST namespaces under
`/api/v1/gc/` (permission namespace `gc_parameters.*`):

- `/api/v1/gc/parameters/…` — List/Detail APIs for every parameter entity.
- `/api/v1/gc/options/…` — SmartSelects option endpoints for frontend dropdowns.

All parameter rows are served through serializers that emit **display names**
(`CODE — Name`) alongside raw FK ids, so names never render as bare UUIDs.
Every list endpoint is paginated, filterable, searchable, and CSV-exportable.

## Conventions

- **Envelope** — paginated list responses use the standard ZIC envelope:
  `{success, status_code, message, data, pagination, meta}` where `data` holds
  the rows and `pagination` carries `{page, per_page, total, pages}`.
- **Pagination** — `StandardPagination`; default `page_size=100`, override with
  `?per_page=` (max `1000`).
- **Filtering** — each resource lists its `filterset_fields`; filter with
  `?field=value`. `django-filter` is active.
- **Search** — every resource supports `?search=` across its listed
  `search_fields` (icontains across the searchable columns).
- **CSV export** — every list endpoint exposes `GET <resource>/export/`; the
  filters/search are honoured and the response is `text/csv` with a
  `Content-Disposition: attachment` header.
- **Display fields** — each row adds `display_name` plus one `<fk>_display`
  name field per many-to-one foreign key (e.g. a product row carries
  `scheme_type_ref_display`). Format is `CODE — Name`.
- **Authentication** — all endpoints require an authenticated user
  (`IsAuthenticated`). Fine-grained `gc_parameters.*` authorisation is layered
  on top via `HasGCParameterPermission`.
- **Errors** — structured errors come from the GC error registry as
  `GCParameterError` (codes such as `SCHEME_RATE_OVERLAP`,
  `PRODUCT_INVALID_LIMITS`, `CLAIM_TYPE_DUPLICATE`) with `message`,
  `resolution_steps` and `doc_ref`.

## 1. Parameter List/Detail APIs

Base path: `/api/v1/gc/parameters/`

| Resource | Router basename | `filterset_fields` (subset shown) | `search_fields` |
|----------|-----------------|-----------------------------------|-----------------|
| `scheme-types/` | `gc-param-scheme-type` | — | code, name |
| `scheme-rates/` | `gc-param-scheme-rate` | rate_type, gender, is_active | name |
| `scheme-statuses/` | `gc-param-scheme-status` | — | code, name |
| `member-statuses/` | `gc-param-member-status` | — | code, name |
| `renewal-statuses/` | `gc-param-renewal-status` | — | code, name |
| `health-questions/` | `gc-param-health-question` | question_type, category, is_active | code, question_text |
| `health-questionnaires/` | `gc-param-health-questionnaire` | is_active | code, name |
| `lookup-values/` | `gc-param-lookup-value` | category, is_active | value, label, category |
| `sub-products/` | `gc-param-sub-product` | — | code, name |
| `products/` | `gc-param-product` | scheme_type_ref, sub_product, is_active, currency, premium_basis, requires_medical | code, name |
| `riders/` | `gc-param-rider` | rider_type, rider_category, benefit_type, requires_underwriting, is_mandatory, is_active | code, name |
| `rider-rates/` | `gc-param-rider-rate` | rider, product_ref, is_active | rider__name |
| `medical/codes/` | `gc-param-medical-code` | category, is_active | code, name, icd10_code |
| `medical/limits/` | `gc-param-medical-limit` | scheme_type_ref, medical_code_ref, product, is_active | scheme_type_ref__code, scheme_type_ref__name, medical_code_ref__code, description |
| `medical/decisions/` | `gc-param-uw-decision` | requires_review, is_active | code, name |
| `medical/habits/` | `gc-param-personal-habit` | habit_category, underwriting_impact, is_active | code, name |
| `medical/histories/` | `gc-param-medical-history` | condition_category, severity, exclusion_flag, is_active | code, name |
| `medical/facilities/` | `gc-param-medical-facility` | facility_type, approval_status, partner_ref, is_active, region | code, name, city |
| `medical/practitioners/` | `gc-param-medical-practitioner` | approval_status, facility, partner_ref, is_active | code, name, first_name, last_name, specialization |
| `claims/types/` | `gc-param-claim-type` | category, calculation_basis, requires_document_check, is_active | code, name |
| `claims/reasons/` | `gc-param-claim-reason` | claim_type, category, is_active | code, name |
| `claims/statuses/` | `gc-param-claim-status` | is_terminal, is_active | code, name |
| `claims/discharge-types/` | `gc-param-discharge-type` | is_active | code, name, template_code |
| `claims/correspondent-types/` | `gc-param-correspondent-type` | category, communication_channel, purpose, is_active | code, name |

Each `ModelViewSet` supplies `GET` (list/detail), `POST`, `PUT/PATCH`,
`DELETE`-style deactivation via the standard router, plus the `export` action.
List responses are paginated; **detail responses are the plain serialized row**
(no envelope).

### Example — list scheme types

```
GET /api/v1/gc/parameters/scheme-types/?search=bank&per_page=50
```

```json
{
  "success": true,
  "status_code": 200,
  "message": "Data retrieved successfully",
  "data": [
    {
      "id": "<uuid>",
      "code": "BANK_LOAN",
      "name": "Bank Loan",
      "description": "Credit life cover on personal and asset loans issued by banks.",
      "is_active": true,
      "display_name": "BANK_LOAN — Bank Loan",
      "created_at": "…",
      "updated_at": "…"
    }
  ],
  "pagination": {"page": 1, "per_page": 50, "total": 1, "pages": 1},
  "meta": {"timestamp": "…", "request_id": null, "version": "v1"}
}
```

> **Wire format note:** the JSON renderer camelizes keys on the wire
> (`display_name` → `displayName`, `is_active` → `isActive`). Client code should
> read camelCase.

## 2. Options Endpoints (SmartSelects)

Base path: `/api/v1/gc/options/`

These feed frontend SmartSelects. Each returns a JSON **array** of
`{value, label, meta}`:

| Endpoint | `meta` extras | Behaviour |
|----------|---------------|-----------|
| `scheme-types/` | `code`, `partner_type_restriction`, `is_active` | active scheme types |
| `products/` | `code`, `scheme_type_code`, `currency`, `is_active` | active products; `?scheme_type=` accepts a scheme-type **UUID or code** to scope the list |
| `questionnaires/` | `code`, `version`, `is_active` | active questionnaires |
| `claim-types/` | `code`, `category`, `is_active` | active claim types |

All option endpoints honour `?search=` (code/name icontains) and return only
`is_active=True` rows. `value` is the row UUID; `label` is the display name
(names, never UUIDs).

### Example — products for a scheme type

```
GET /api/v1/gc/options/products/?scheme_type=BANK_LOAN
```

```json
[
  {
    "value": "<product-uuid>",
    "label": "CREDIT_LIFE_A — Credit Life Plan A",
    "meta": {
      "code": "CREDIT_LIFE_A",
      "scheme_type_code": "BANK_LOAN",
      "currency": "TZS",
      "is_active": true
    }
  }
]
```

## 3. CSV export

Every parameter list endpoint exposes its filters/search as a downloadable CSV:

```
GET /api/v1/gc/parameters/products/export/?scheme_type_ref=<uuid>
```

Columns mirror the serializer row keys (snake_case, including `display_name`).
The response is `text/csv; charset=utf-8` with
`Content-Disposition: attachment; filename="<model_table>.csv"`.
