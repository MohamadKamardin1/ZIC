# ZIC IAM User Groups and Permission Engine

## Purpose

The ZIC permission engine provides explicit module and action authorization for internal staff, partner users, administrators, and auditors. A user inherits permissions from active `UserGroup` memberships; there are no user-level permission overrides in this iteration because group inheritance is sufficient for the current operating model and is easier to audit.

A permission is addressed through a stable machine-readable code:

> `module.action`

For example, `ordinary_life.view`, `claims.approve`, and `user_management.administer` are valid permission codes.

## Domain model

`UserGroup` is a first-class entity with a unique display name and machine-readable code. It records its group type, active state, system protection state, creator, updater, assigned permissions, and assigned users. Group types are `INTERNAL`, `PARTNER`, `ADMINISTRATIVE`, and `AUDIT`.

`UserPermission` is the permission catalog entity. It stores the module/domain, action, resource type, stable code (`codename`), description, and active state. Legacy action values remain supported for backward compatibility while the catalog adds view, configure, reject, print, reverse, settle, assign, and administer actions.

System groups remain protected from code/type edits and deactivation. User-created groups are deactivated rather than physically deleted so historical assignments and audit records remain explainable.

## Permission inheritance and enforcement

The preferred application-level check is:

```python
request.user.has_permission("claims.approve")
```

The following authorization primitives are available:

| Primitive | Use |
|---|---|
| `User.has_permission(code)` | Direct inherited permission check for service and domain logic. |
| `HasPermission(code)` | DRF permission instance for endpoint authorization. |
| `permission_required(code)` | Decorator for function-based Django views. |
| `HasModulePermission(module, action)` | Backward-compatible helper for existing endpoints and legacy permission rows. |

Superusers bypass permission checks. All other users require an active group and an active permission. Partner users may only be assigned to partner groups, while internal users cannot be assigned to partner groups.

## Group API

The existing users API prefix is `/api/v1/users/`.

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/groups/` | List groups. Requires `user_management.view` or the legacy users read permission. |
| `POST` | `/groups/` | Create a non-system group. Requires `user_management.administer` or legacy users manage permission. |
| `GET` | `/groups/{id}/` | Retrieve a group with permissions and assigned-user summaries. |
| `PUT/PATCH` | `/groups/{id}/` | Update a group subject to system-group protections. |
| `DELETE` | `/groups/{id}/` | Deactivate a non-system group; no database deletion occurs. |
| `POST` | `/groups/{id}/activate/` | Reactivate a group. |
| `POST` | `/groups/{id}/deactivate/` | Deactivate a group explicitly. |
| `POST` | `/groups/{id}/assign_permissions/` | Assign active permissions using `permission_ids`. |
| `POST` | `/groups/{id}/remove_permissions/` | Remove permissions using `permission_ids`. |
| `POST` | `/groups/{id}/assign_users/` | Assign active users using `user_ids`, with group-type validation. |
| `POST` | `/groups/{id}/remove_users/` | Remove users using `user_ids`. |
| `GET` | `/permissions/` | List active permission definitions. |
| `GET` | `/permissions/modules/` | List active catalog modules. |

Mutation responses preserve the project success envelope and include a serialized resource or assignment identifier list in `data`.

## Audit and outbox behavior

Group creation, updates, activation/deactivation, permission assignments/removals, and user assignments/removals create `UserActivityLog` records with action type `PERMISSION_CHANGE`. Each mutation also creates a pending `DomainEvent` with an `iam.*` event type, aggregate type, aggregate identifier, actor identifier, and affected identifiers. The outbox event is intended for future audit, notification, and integration consumers.

## Seed catalog

Migration `0009_seed_zic_permission_catalog` seeds the major ZIC domains defined by the IAM requirements, including dashboard, user management, system parameters, onboarding, ordinary life, group credit, group life, medical underwriting, front office, claims, commission, approvals, reporting, reinsurance, partner portal, tickets, and audit. The common catalog actions include view, read, create, update, delete, approve, reject, configure, export, print, reverse, settle, assign, and administer.

## Operational assumptions

The existing `users` and legacy module/action permission rows remain supported to avoid breaking completed modules. The new catalog is additive and normalizes newly seeded codenames to `module.action`. The current partner boundary treats `PARTNER` and `PORTAL_USER` as partner identities. Administrative users are expected to receive `user_management.administer` through an administrative group or retain superuser status.
