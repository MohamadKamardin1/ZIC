# Central Audit Logging Framework

## Purpose and scope

The ZIC platform uses a central, append-only audit log to provide a consistent compliance record for material changes. The framework is intentionally generic so that policy, claims, finance, commission, reinsurance, approvals, reporting, and portal modules can record the same evidence without introducing separate audit tables or incompatible payloads.

An audit record identifies the actor and execution channel, the affected application/model/object, the action performed, the request correlation identifier, and the before/after state where a state transition is available. Audit records are operational evidence; they are not a replacement for domain transaction history, approval records, or reporting execution history. Future modules should keep their domain-specific history where it is needed and create a corresponding central audit record for traceability.

## Data model

`apps.governance.models.AuditLog` is stored in the `governance_audit_log` table. `AuditEvent` remains an alias for compatibility with earlier callers.

| Field | Meaning |
|---|---|
| `actor` | Authenticated user responsible for the event, when applicable. System events may leave this empty. |
| `actor_type` | Actor classification such as `USER`, `SYSTEM`, `IMPORT`, or another agreed value. |
| `action` | Normalized event verb, for example `CREATE`, `UPDATE`, `DELETE`, `LOGIN`, `ASSIGN`, or `REVOKE`. |
| `app_label`, `model_name` | Django application and model identifying the affected resource. |
| `object_id`, `object_repr` | Stable object identifier and human-readable representation. |
| `before_state`, `after_state` | JSON snapshots captured immediately before and after a material transition. |
| `changed_fields` | JSON object containing only changed fields and their old/new values for updates. |
| `reason` | Business reason, comment, or operator-provided explanation when available. |
| `source_channel` | Origin such as `WEB`, `API`, `ADMIN`, `SYSTEM`, `IMPORT`, `PORTAL`, or `BATCH`. |
| `ip_address`, `user_agent` | Request metadata captured by the request context middleware. |
| `correlation_id` | Request or job identifier used to connect related events. |
| `created_at` | Event creation timestamp. |

Indexes support the principal investigation paths: actor, action, source channel, application/model/object, correlation ID, and creation time. The object identifier is represented as text so the framework can audit integer, UUID, string, and externally generated identifiers uniformly.

## Service API

Use `apps.governance.services.audit_service.AuditService` rather than creating `AuditLog` rows directly. The service centralizes normalization, snapshots, diffs, request metadata, and compatibility behavior.

```python
from apps.governance.services.audit_service import AuditService

AuditService.log_create(instance, reason="Created during onboarding")
AuditService.log_update(instance, before_state=before, reason="Approved by underwriting")
AuditService.log_delete(instance, before_state=before, reason="Removed by administrator")
AuditService.log_action(
    action="APPROVE",
    instance=policy,
    reason="Underwriting approval",
    after_state={"status": "approved"},
)
AuditService.log_model_action(
    app_label="claims",
    model_name="Claim",
    object_id=claim.pk,
    action="SETTLE",
    object_repr=str(claim),
    reason="Settlement completed",
)
```

`log_update` computes a field-level diff when both snapshots are supplied. Snapshot and diff helpers are available for callers that need to capture state before a mutation. Service methods accept explicit context values for asynchronous jobs or integrations; otherwise they use the current `AuditContext`.

The framework is designed to be failure-aware: audit creation should occur in the same transaction as the material mutation whenever possible. Domain services should not silently claim success after a required audit write fails. For non-transactional integrations, callers should include a stable correlation ID and retain the external event reference in the reason or action metadata supported by the domain module.

## Request context and middleware

`AuditContextMiddleware` establishes and clears request-local metadata for each request. It captures the authenticated user, request ID, source channel, client IP, user agent, and correlation ID. The existing request-ID middleware provides identifiers in the `req_<hex>` format; an inbound correlation header may be preserved according to the middleware implementation.

The context is thread-local and must not be treated as global mutable state. Long-running workers and scheduled jobs must set an explicit system context for the duration of the job and clear it in a `finally` block. Portal, import, and batch modules should set their corresponding source channel rather than relying on the default API channel.

## Automatic receivers

`apps.governance.audit_receivers` registers signal receivers from `GovernanceConfig.ready()`. Current coverage includes the critical IAM and authorization objects below.

| Resource | Events covered |
|---|---|
| `User` | Creation and material updates with before/after state. |
| `UserGroup` | Creation and material updates. |
| Group permission assignments | Assignment and removal actions. |
| Group report-category assignments | Assignment and removal actions. |
| `UserPartnerLink` | Creation, updates, and removal actions. |

Receivers use recursion-safe snapshots and migration-safe table checks so that schema setup and test database creation do not fail because the audit table is not yet available. New modules should prefer explicit service calls for business actions with reasons and approval context; signals are best reserved for broad safety-net coverage of critical model mutations.

## Read-only API

The governance API exposes audit records at `/api/v1/governance/audit-logs/`. The endpoint is read-only and restricted to staff or superusers under the governance permission policy. A single event can be retrieved by its identifier.

Supported investigation filters include actor, model/application, action, source channel, object identifier, correlation ID, and date bounds. Results are ordered newest first and are serialized in the standard ZIC response envelope. The API exposes state snapshots and changed fields for authorized investigators but does not permit mutation or deletion.

The endpoint is intended for compliance investigation and operational support. It should not be used as an unrestricted end-user activity feed. Future row-level authorization can be added without changing the event schema by narrowing the queryset in the governance permission layer.

## Django admin

AuditLog is registered as read-only administration data. Add, change, and delete operations are disabled. Central fields, request metadata, state JSON, and correlation information are displayed and searchable where useful. Administrative users should use the API or database-backed investigation tooling for large result sets rather than editing records in place.

## Immutability contract

Audit records are append-only. `AuditLog.save()` rejects updates to an existing row and `AuditLog.delete()` rejects deletion. This protects the application-level contract even when an administrator has normal model access. Database-level controls, restricted database roles, backups, and retention policies should be added in production to protect against direct SQL changes and to meet Zanzibar regulatory retention requirements.

If a correction is needed, do not edit an existing event. Create a new compensating audit action with a reason that references the original event or business transaction. Any future archival process must preserve event integrity and correlation identifiers.

## Future integration hooks

Future domain modules should use the following conventions:

1. Record a central audit event for every material create, update, delete, approval, rejection, assignment, payment, settlement, endorsement, import, and report execution transition.
2. Use stable domain object identifiers and include a useful object representation that does not expose secrets or sensitive credentials.
3. Capture before and after state selectively. Exclude passwords, tokens, raw identity documents, payment credentials, and other secret or unnecessarily sensitive values.
4. Supply a business reason or comment for operator-driven actions, and preserve approval or external transaction references in domain-specific fields or structured action metadata when those fields are introduced.
5. Reuse the request correlation ID across related events. For asynchronous work, create a job correlation ID and propagate the originating request ID as a domain reference.
6. Choose `source_channel` accurately: interactive staff work should use `WEB`, API integrations use `API`, administration uses `ADMIN`, customer/partner interactions use `PORTAL`, and automated imports or scheduled jobs use `IMPORT` or `BATCH`.
7. Keep report-category entitlement separate from action permissions. A reporting endpoint should first apply the existing report visibility checker, then record report execution history and a central audit event.

The existing `AuditEvent` alias and service helpers provide a compatibility surface for modules that were designed against the earlier event terminology. New code should use `AuditLog` and `AuditService` directly.

## Testing expectations

The audit acceptance suite covers user creation, user state updates and diffs, group assignment, partner-link auditing, correlation-ID capture, read-only API authorization, and immutability. Every new module should add tests that assert both the domain transition and the corresponding audit evidence. Tests should also prove that unauthorized users cannot infer protected objects through audit filters.

## Assumptions

The initial implementation treats audit events as application-level append-only records and assumes production database roles and backup controls will provide defense in depth. System-generated events may have no user actor but must identify their actor type and source channel. State snapshots are JSON-safe, bounded representations; large documents and file contents should be referenced by stable IDs rather than embedded in an audit row. Retention, legal hold, export, and redaction policies remain deployment-specific governance configuration and should be finalized before production go-live.

## Related documentation

The framework integrates with the IAM and authorization foundations described in [`IAM_RBAC.md`](IAM_RBAC.md), [`IAM_REPORT_CATEGORIES.md`](IAM_REPORT_CATEGORIES.md), and [`IAM_PARTNER_LINKAGE.md`](IAM_PARTNER_LINKAGE.md). The common response and API conventions are defined in [`API_CONVENTIONS.md`](API_CONVENTIONS.md).

## References

[1]: https://docs.djangoproject.com/en/5.0/topics/signals/ "Django Signals Documentation"
[2]: https://www.django-rest-framework.org/api-guide/permissions/ "Django REST framework Permissions"
[3]: https://docs.djangoproject.com/en/5.0/ref/models/instances/ "Django Model Instance Reference"

The references above describe the framework primitives used by this implementation; ZIC-specific behavior is defined by the source code and tests in this repository.

## Author

**Manus AI**
