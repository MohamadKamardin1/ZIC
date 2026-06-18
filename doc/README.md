# ZIC Core Life Requirements Package

This workspace contains the revised full requirements and technical foundation package based on the expanded module attachment.

## Deliverables

- `docs/SRS.md` - full System Requirements Specification.
- `docs/django_app_structure.md` - recommended Django project, apps, module ownership, services, and API structure.
- `database/postgresql_schema.sql` - PostgreSQL schema organized by domain, including tables, relationships, indexes, triggers, and operational views.

## Module Coverage

- Dashboard
- Partner Onboarding
- Partners
- Ordinary Life
- Group Life
- Group Credit
- Front Office
- Reports
- General Parameters
- Partner Parameters
- User Parameters
- Reinsurance Parameters
- User Management
- Approval

## Database Domains

The SQL script uses PostgreSQL schemas for clear module separation:

- `core`
- `security`
- `approval`
- `partner`
- `onboarding`
- `dashboard`
- `ol`
- `gl`
- `gc`
- `front_office`
- `reinsurance`
- `reporting`
