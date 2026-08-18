# OL Parameters Release Guide

## Scope

This release completes the **Ordinary Life Parameters** bounded context as a table-driven, effective-dated configuration foundation across nine groups: Default Setup, Policy Setup, Product Setup, Product Rating, Rider Setup, Agent Management, Loan Setup, Medical Underwriting, and Claim Setup.

The release owns configuration catalogs, rate tables, applicability rules, lifecycle metadata, API table contracts, permissions, audit integration, and administration. It does not execute quotation, policy, loan, underwriting, claim, payment, or servicing transactions. Those domains consume the active and approved parameter records through their own transactional services.

## Bootstrap sequence

Apply migrations before seeding:

```bash
cd backend
python manage.py migrate
python manage.py seed_ol_parameters_release
```

The unified command is idempotent and executes all group seeds, permission and role seeds, and the canonical registry seed. It performs no destructive deletion. Component-level registry rows remain available for detailed tables; nine stable `ol-*` registry rows provide top-level group discovery.

## Permissions and seeded roles

| Role code | Intended access |
|---|---|
| `OL_PARAMETER_VIEWER` | Read, list, retrieve, search, filter, and export active OL parameter tables. |
| `OL_PARAMETER_CONFIGURATOR` | Viewer access plus create and update. Deactivation is excluded intentionally. |
| `OL_PARAMETER_ADMINISTRATOR` | Full lifecycle access, including deactivation and registry configuration. |

Canonical permissions are:

- `ol_parameters.view`
- `ol_parameters.create`
- `ol_parameters.update`
- `ol_parameters.deactivate`
- `ol_parameters.configure`

Role assignment should be governed through IAM and organizational approval. Direct per-user grants should be reserved for controlled exceptions and remain auditable.

## Operational verification

After bootstrap, verify the readiness endpoint:

```text
GET /api/v1/ol-parameters/health/
```

The response reports active counts for all nine groups, Product Rating Parts 1 and 2, and the active canonical registry count. Verify that the response status is `ok`, the registry contains nine canonical top-level contracts, and the group counts reflect the expected environment data.

The release test suite can be run with:

```bash
pytest -q apps/ol_parameters/tests/test_release_hardening.py
pytest -q --disable-warnings
```

## Production approval assumptions

Seed values are development-safe examples. Before production activation, responsible owners must approve rates, factors, limits, effective dates, product and plan scope, medical and underwriting rules, claim transitions, discharge templates, correspondence channels, commission values, loan controls, and rider applicability. Production deployment must use PostgreSQL and the supported migration pipeline; SQLite is for local development only.

All material changes must use the authenticated API, approved admin workflow, or governed seed/release process so actor identity, timestamps, correlation IDs, before/after state, and source channel are preserved in the central audit log.

## Release acceptance checklist

- [ ] Migrations apply cleanly in the target environment.
- [ ] `seed_ol_parameters_release` completes successfully twice without duplicate records.
- [ ] All nine canonical registry contracts are active and expose valid table metadata.
- [ ] Viewer, configurator, and administrator roles have the expected permission sets.
- [ ] A seeded viewer can read representative endpoints from every group but cannot mutate records.
- [ ] The readiness endpoint reports all nine group sections.
- [ ] Focused group tests and the full backend regression suite pass.
- [ ] Database backup and rollback procedures are confirmed before production activation.
- [ ] Actuarial, underwriting, claims, product, legal, compliance, finance, and governance approvals are recorded for production starter values.
