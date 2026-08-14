# ZIC API Conventions

## Base URL and representation

All public REST endpoints are versioned below `/api/v1/`. JSON request and response fields use camelCase at the transport boundary through the configured Django REST Framework camel-case parser and renderer. Domain and database code remains Pythonic and snake_case.

## Successful responses

Collection endpoints use the global `StandardPagination` class:

```json
{
  "success": true,
  "statusCode": 200,
  "message": "Data retrieved successfully",
  "data": [],
  "pagination": {
    "page": 1,
    "perPage": 100,
    "total": 0,
    "pages": 0
  },
  "meta": {
    "timestamp": "2026-08-14T00:00:00Z",
    "requestId": "req_abc123",
    "version": "v1"
  }
}
```

Single-resource endpoints may return the serializer representation directly where an existing module already establishes that behavior. New module endpoints should prefer the same success metadata when introducing new aggregate responses, and must not silently change established envelopes.

## Errors

The global exception handler returns a stable shape:

```json
{
  "success": false,
  "statusCode": 400,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed.",
    "details": {
      "fieldName": ["A human-readable validation message."]
    }
  },
  "meta": {
    "timestamp": "2026-08-14T00:00:00Z",
    "requestId": "req_abc123",
    "version": "v1"
  }
}
```

Clients should use `error.code` for programmatic branching and display `error.message` or field-level `error.details` for user feedback. Validation messages must identify the field or business rule that failed. Business services should raise Django or REST validation errors rather than returning ad hoc error dictionaries from views.

## Filtering, search, and ordering

List endpoints may expose `django-filter` fields through `?field=value`, full-text-like search through `?search=value`, and explicit ordering through `?ordering=field` or `?ordering=-field`. A module must declare allowed filter and ordering fields rather than accepting arbitrary database expressions.

## Request correlation

Clients may send `X-Request-ID`. The request middleware preserves a bounded correlation identifier or generates a `req_<random>` identifier. Responses include the same `X-Request-ID`; audit records and request logs use it to connect a state change to its transport request.

## Health and readiness

`GET /api/v1/live/` checks process liveness without dependencies. `GET /api/v1/ready/` checks required runtime dependencies and returns HTTP 503 when unavailable. `GET /api/v1/health/` remains an alias for readiness for existing monitoring clients.

## OpenAPI

The schema is generated at `/api/schema/`; Swagger UI is available at `/api/docs/` and ReDoc at `/api/redoc/`. New viewsets should use descriptive class and action names, serializer fields, and operation metadata so generated documentation remains useful. API tags should align with bounded contexts such as Authentication, Users, Partners, and Health.
