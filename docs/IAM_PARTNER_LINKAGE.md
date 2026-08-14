# IAM Partner Linkage and Row-Level Scope

## Purpose

The partner linkage foundation establishes the relationship between authenticated users and the existing `Partner` master. It provides reusable row-level visibility for partner-facing workflows without duplicating the partner entity or coupling partner access to report-category entitlements or module permissions.

## Data model

`apps.partners.models.Partner` remains the authoritative partner master. The implementation adds normalized identity, registration, lifecycle, contact, activation, and audit fields while preserving legacy fields used by completed onboarding and partner workflows.

`UserPartnerLink` is a time-bounded through model between `users.User` and `partners.Partner`. It records `link_status`, `valid_from`, optional `valid_to`, `is_primary`, assignment actor, and timestamps. Database constraints prevent duplicate active user/partner links and more than one primary active link for a user.

## Scope rules

Partner accounts (`user_type=PARTNER`) are restricted to active links whose validity window includes the current time and whose partner is active with status `ACTIVE`. The legacy `User.partner_id` UUID remains supported as a compatibility fallback.

Staff, superusers, and internal operational user types bypass partner row filtering. Legacy unscoped portal accounts also retain their historical unrestricted partner-read behavior until they receive an explicit partner link or `partner_id`; once explicitly linked, their visibility is scoped.

The reusable `PartnerScopePermission` checks object access through `user.can_access_partner(partner)`, while `PartnerScopedQuerySetMixin` filters querysets using `user.visible_partners()`. Future policy, claims, commission, and reporting endpoints should use these primitives rather than duplicating partner predicates.

## API surface

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/v1/partners/context/` | Return the authenticated user’s current partner context. |
| `GET` | `/api/v1/partners/users/{user_id}/links/` | List links for a user. |
| `POST` | `/api/v1/partners/users/{user_id}/links/` | Create or activate a user-partner link. |
| `POST` | `/api/v1/partners/users/{user_id}/links/remove/` | Deactivate a user-partner link. |
| `GET` | `/api/v1/partners/` | List only partners visible to the authenticated user. |
| `GET` | `/api/v1/partners/{id}/` | Retrieve a partner only when visible to the authenticated user. |

Link mutations require administrative authorization and publish activity/audit events through the existing activity-log and domain-event mechanisms.

## Assumptions

The existing `Partner` model remains authoritative; no parallel partner master is introduced. A user may have multiple active partner links, but only one may be primary. Link validity is evaluated against the server timezone at request time. Deactivation is preferred to deletion so historical assignments remain auditable. Internal users may bypass row-level partner filtering, while explicitly linked partner accounts cannot.

The current context endpoint is intentionally read-only. Partner switching, delegated administration, and workflow-specific object scoping are future capabilities and should build on `current_partner()`, `visible_partners()`, and `PartnerScopePermission`.
