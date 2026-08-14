# IAM Report-Category Visibility

## Purpose

Report-category visibility is an independent entitlement layer in the ZIC Identity and Access Management module. A user group may grant access to an application module or process through `UserPermission`, while report visibility is granted separately through `ReportCategory` assignments. Possessing a process permission does not imply visibility of the corresponding reports, and report visibility does not grant process permissions.

## Data model

`ReportCategory` is a system or tenant-defined report classification with a stable lowercase `code`, display name, description, business area, active flag, and system flag. The required system catalog currently includes `ordinary_life`, `group_credit`, `group_life`, `claims`, `commission`, `finance`, `underwriting`, `reinsurance`, `audit`, and `ifrs17`.

`UserGroupReportCategory` is the auditable through model linking a `UserGroup` to a `ReportCategory`. It records the assigning user and assignment timestamp and enforces one assignment per group/category pair. Removing an assignment does not remove either the group or the category.

## Visibility contract

The user model exposes two integration methods:

```python
user.visible_report_categories()
user.can_view_report_category("claims")
```

Only active users, active groups, and active categories participate in visibility. Superusers can view all active categories. Ordinary users receive the distinct union of categories assigned to their active groups.

The future reporting engine should use `ReportVisibilityChecker.visible_categories(user)` for category-filtered listings and `ReportVisibilityChecker.require(user, code)` immediately before report execution or export. The checker is intentionally separate from `HasPermission` and `User.has_permission()`.

## API surface

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/v1/users/report-categories/` | List active and inactive categories according to administrative filters. |
| `GET` | `/api/v1/users/report-categories/{id}/` | Retrieve one category. |
| `POST` | `/api/v1/users/report-categories/` | Create a non-system category. |
| `PATCH` | `/api/v1/users/report-categories/{id}/` | Update category metadata. System identity fields are protected. |
| `DELETE` | `/api/v1/users/report-categories/{id}/` | Soft-deactivate a non-system category. |
| `GET` | `/api/v1/users/users/visible-report-categories/` | List categories visible to the authenticated user. |
| `POST` | `/api/v1/users/groups/{id}/assign_report_categories/` | Assign categories to a group. |
| `POST` | `/api/v1/users/groups/{id}/remove_report_categories/` | Remove categories from a group. |
| `GET` | `/api/v1/auth/me/` | Includes `visible_report_categories` in the nested current-user payload. |

Administrative mutations require the existing user-management administration capability or the legacy users-management permission. The current-user visibility endpoint requires authentication only.

## Audit and integration hooks

Report-category assignment and removal emit `PERMISSION_CHANGE` activity records for affected group members and `iam.group.report_categories_assigned` or `iam.group.report_categories_removed` domain events. The domain event payload includes affected category IDs and stable category codes, allowing future reporting services to consume entitlement changes without coupling to the reporting implementation.

## Assumptions

The first implementation uses group-level assignment only. User-level overrides are intentionally deferred until the reporting requirements demonstrate a need for exceptions that cannot be represented by groups. No seeded category is assigned to a group automatically; administrators must make visibility grants explicitly. Category deletion is represented by deactivation, and system category codes are immutable. Report execution history is not implemented here, but the visibility checker and domain-event payload provide the integration boundary for that future module.
