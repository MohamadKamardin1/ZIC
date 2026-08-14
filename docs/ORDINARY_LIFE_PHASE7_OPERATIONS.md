# Ordinary Life Phase 7 — Operations, Work Management, and Audit Hooks

## Scope

Phase 7 adds the operational layer around the Ordinary Life lifecycle. It keeps documents, notes, approvals, dashboard work items, permission checks, workflow history, and compliance history service-owned and auditable. The implementation extends the locked lifecycle contract rather than creating a second policy state machine [1].

## Evidence and document workflow

`OrdinaryLifeOperationsService` manages the complete `OLDocumentRecord` lifecycle. A document must belong to exactly one proposal or policy. It can be created as `PENDING`, uploaded as `UPLOADED`, verified as `VERIFIED`, or rejected as `REJECTED`. Upload, verification, and rejection require authenticated actors and explicit permission actions. Rejection requires a reason, and a rejected document can be uploaded again without losing the rejection history.

| Operation | Guard | Durable records and hooks |
| --- | --- | --- |
| Create document | Exactly one parent, non-empty type, optional idempotency key | Document, workflow event, audit event, dashboard notification, upload task when pending |
| Upload document | Pending or rejected status and non-empty file reference | Updated document, workflow event, audit event, readiness notification |
| Submit verification | Uploaded status and no pending duplicate approval | Shared `ApprovalRequest`, workflow event, review task |
| Verify document | Uploaded status and review/approval permission | Verified actor/time, workflow event, audit event, notification |
| Reject document | Pending or uploaded status and required reason | Rejected actor/time/reason, workflow event, audit event, dashboard alert |

Document idempotency keys are persisted in the database. Repeated creation with the same key returns the original record; reuse of a key for another parent or document type is rejected. Proposal document types remain unique under the existing database constraint.

## Notes

Notes are append-only operational records. A note must belong to exactly one proposal or policy, requires non-empty content and an authenticated creator, and supports a persisted idempotency key. Notes are never edited or deleted by this service; corrections are represented by additional notes so the operational trail remains complete.

## Shared approvals

The service integrates with the central `ApprovalService` and `ApprovalRequest` model. Ordinary Life verification and policy-operation approvals use the shared module identifier `ORDINARY_LIFE`; duplicate pending submissions are returned instead of creating parallel approval requests. Completion is transactional: if the underlying Ordinary Life operation fails, approval completion and the domain transition roll back together.

The service also provides a generic bridge for endorsement, renewal, and reinstatement approvals. It delegates the final state transition to `OrdinaryLifePolicyService`, preserving the service-owned guards already implemented in Phase 6 rather than mutating status fields directly.

## Permissions

Ordinary Life operational methods enforce the existing user authorization API through `has_module_permission("ORDINARY_LIFE", action)`. The following actions are used:

| Capability | Permission action |
| --- | --- |
| Create documents and notes | `CREATE` |
| Upload documents | `UPDATE` |
| Submit evidence or policy approval | `REVIEW` |
| Verify evidence | `REVIEW` or `APPROVE` |
| Reject evidence | `REVIEW` or `REJECT` |
| Complete shared approvals | `APPROVE` |
| Read workflow history | `READ` |
| Read compliance audit history | `COMPLIANCE` |
| Assign dashboard work items | `ASSIGN` |

Superusers retain the platform’s existing bypass behavior. Authentication alone is not treated as authorization; a non-superuser must receive the relevant Ordinary Life permission through an active user group.

## Dashboard work management

Workflow hooks create clickable, idempotent dashboard records using the existing dashboard models. Pending uploads create `DashboardTask` records, verification approvals create review tasks, successful events create `DashboardNotification` records keyed by stable external keys, and document rejection creates an open `DashboardAlert`. Each record includes the Ordinary Life entity type, entity identifier, and route so the frontend can redirect to the exact workspace record.

## Audit and history

Every Phase 7 service transition writes an `OLWorkflowEvent` and a central `AuditLog` record with the actor, Ordinary Life app label, lowercase Django model name, object identifier, action, before/after status where applicable, changed fields, reason, request correlation identifier, and source channel from `AuditContext`. Read-only history access is exposed as service querysets and is restricted to the existing `READ` and `COMPLIANCE` permission boundaries.

## Schema additions

Migration `0007_oldocumentrecord_idempotency_key_and_more` adds document rejection metadata and persisted idempotency keys to `OLDocumentRecord` and `OLNote`. These fields support deterministic retries and preserve the identity and reason of compliance decisions without introducing a second audit store.

## Verification

The Phase 7 test module contains seven focused tests covering document creation and verification approval, rejection and re-upload, note/document idempotency, exactly-one-parent validation, shared approval idempotency, clickable task creation, compliance-history access, and permission enforcement. Django checks, migration consistency checks, and Ruff pass. The complete backend regression suite passes with **416 tests** and three pre-existing framework warnings.

## References

[1]: [Ordinary Life Phase 2 Domain Contract](./ORDINARY_LIFE_PHASE2_DOMAIN_CONTRACT.md)
[2]: [Central Audit Logging Framework](../backend/apps/governance/services/audit_service.py)
[3]: [Dashboard Workspace Models](../backend/apps/dashboard/models.py)
