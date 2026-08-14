# ZIC Foundation Assumptions

This document records assumptions made while establishing the backend foundation from the provided test specification. They are explicit so later module work can challenge or refine them without silently changing behavior.

| Area | Assumption | Rationale |
|---|---|---|
| Database | SQLite remains the default local/test database; PostgreSQL is the deployment target through `DATABASE_URL`. | The repository already uses SQLite locally and already includes PostgreSQL URL support. |
| Identity | The existing `users.User` model remains the authoritative user model. | Replacing the custom user implementation would risk breaking existing authentication and permissions. |
| Shared identifiers | New reusable foundation entities use UUID primary keys; existing bounded-context models retain their current identifiers. | UUIDs are safer for externally visible domain events, while preserving existing schema compatibility is mandatory. |
| Audit ownership | `created_by` and `updated_by` are optional foreign keys because automated jobs and historical imports may not have a human actor. | The requirement asks for attribution where practical, but system work must remain representable. |
| Soft deletion | Soft deletion is opt-in through `SoftDeleteModel`; existing models are not migrated automatically. | Hard-changing every existing model would be a broad, risky schema rewrite unrelated to the foundation’s immediate acceptance criteria. |
| Domain events | `DomainEvent` is persisted transactionally as an outbox record; publication workers are a follow-on integration concern. | Durable storage establishes the correct consistency boundary without inventing an unavailable message broker contract. |
| Health probes | `/live/` checks process responsiveness; `/ready/` and `/health/` check the database and configured cache. Redis is not required for readiness unless the application explicitly uses it as a cache dependency. | This avoids declaring a development environment unhealthy solely because optional Celery infrastructure is not running. |
| Production secrets | Production settings reject the known local fallback secret. | A deployment must provide a real `DJANGO_SECRET_KEY`. |
| API compatibility | Existing response envelopes and routes are preserved; new foundation endpoints are additive. | Current frontend and module integrations already depend on the established API contract. |
| Static analysis | Ruff and mypy configuration is scoped conservatively at first, with shared core packages as the initial type-check target. | Legacy modules contain heterogeneous patterns; expanding strict coverage should happen incrementally with each module hardening pass. |
| Git delivery | The active feature branch and remote are preserved; pushing is attempted only after all required checks pass. | This repository is being developed incrementally and must not have its branch topology rewritten implicitly. |
