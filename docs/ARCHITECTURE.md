# ZIC Backend Architecture

## Purpose

The ZIC backend is a Django and Django REST Framework service for Zanzibar Insurance Company. It is organized around bounded contexts so that insurance workflows can evolve independently while sharing authentication, governance, configuration, and API infrastructure.

## Application boundaries

| Context | Responsibility | Primary integration points |
|---|---|---|
| `apps.core` | API infrastructure, request correlation, pagination, exception normalization, health probes | Django middleware and REST Framework settings |
| `apps.common` | Reusable abstract models and the durable domain-event outbox | Domain services and asynchronous publishers |
| `apps.users` / `apps.authentication` | Identity, authentication, tokens, and user profile data | JWT, OAuth2, permissions |
| `apps.partners` | Partner master data, assignments, setup, and partner lifecycle | Onboarding conversion and insurance operations |
| `apps.partner_onboarding` | Partner application, documents, review, compliance, approval, and conversion | Partners and governance |
| `apps.governance` | Audit logs, approval controls, and request audit context | All state-changing services |
| `apps.system_parameters` | Numbering, configuration, and workflow parameters | Domain services and administration |
| `apps.ordinary_life` | Individual life products, quotations, proposals, policies, servicing, and claims | Partners, governance, payments, and reporting |
| `apps.group_life` | Group-life setup, underwriting, member and claim workflows | Partners, governance, payments, and reporting |
| `apps.group_credit` | Credit-life products, schedules, certificates, and claims | Partners, lenders, governance, and payments |
| `apps.front_office` | Operational intake and front-office workflows | Users, partners, quotations, and dashboard |

## Dependency rules

Feature apps may depend on shared infrastructure and other bounded contexts through explicit services, serializers, and stable API contracts. Business state transitions belong in transaction-safe application services rather than view methods or signal handlers. Views validate transport input, authorize the request, invoke a service, and serialize the resulting state.

All state-changing workflows should record an immutable audit entry through `apps.governance` and should publish a durable `apps.common.models.DomainEvent` inside the same database transaction when an integration event is required. The outbox model is intentionally persistence-only at foundation stage; publisher workers can be added without changing domain transaction boundaries.

## Settings discipline

Settings are split into `base.py`, `development.py`, `staging.py`, and `production.py`. Base settings contain shared application wiring and safe defaults for local execution. Environment-specific modules control debug mode, allowed hosts, cookies, TLS, email, token lifetimes, and observability. Production refuses the development fallback signing key.

The default database configuration uses `DATABASE_URL`, which supports SQLite for local development and PostgreSQL-compatible URLs in deployed environments. Secrets, hosts, CORS, CSRF origins, email credentials, JWT signing keys, broker URLs, and release metadata are environment-driven.

## API layers

The versioned API is rooted at `/api/v1/`. REST Framework applies authentication, pagination, filtering, throttling, camel-case JSON, OpenAPI schema generation, and the centralized exception handler globally. Infrastructure exposes `/api/v1/live/`, `/api/v1/ready/`, and the backward-compatible `/api/v1/health/` endpoint.

## Delivery topology

The backend can run under Gunicorn or Uvicorn, with Celery and Redis available for asynchronous work. Static assets are served through WhiteNoise in deployments where an external static server is not used. PostgreSQL is the production database target. CI runs Django checks, migration drift detection, focused tests, linting, and best-effort type checking.
