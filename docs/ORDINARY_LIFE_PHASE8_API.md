# Ordinary Life Phase 8 — Hardened API Boundary

## Scope

Phase 8 exposes the completed Ordinary Life domain through a versioned, authenticated, permission-aware API without allowing serializers or endpoints to bypass service-owned lifecycle transitions. The hardened API is mounted below `/api/v1/ordinary-life/` and preserves the existing setup namespace while replacing the core namespace with the Phase 5–7 workflow surface.

## API surface

The `setup/` namespace retains the existing reference-data viewsets for lookup values, system parameters, computation approaches, grace periods, policy statuses, beneficiary types, health questionnaires, surrender and paid-up configuration, and related setup records.

The `core/` namespace now exposes read representations and service-backed actions for products, clients, applications, quotations, quotation versions, proposals, underwriting cases and decision events, medical requirements, health declarations and responses, payment obligations and allocations, policies, endorsements, renewals, reinstatement requests, premium schedules and installments, policy parties, beneficiaries, documents, notes, workflow events, policy transactions, policy status history, approvals, audit history, commitments, loans, withdrawals, claims, and maturity installments.

| Workflow area | Representative routes | Write behavior |
|---|---|---|
| Intake and quotation | `applications/`, `quotations/`, `proposals/` | Creation and transitions call `OrdinaryLifeApplicationService`; quotation versions remain immutable. |
| Underwriting | `underwriting-cases/`, `medical-requirements/`, `health-declarations/` | Decisions and evidence actions call the Phase 5 service and enforce evidence gates. |
| Policy servicing | `policies/`, `endorsements/`, `renewals/`, `reinstatements/` | Issuance, status transitions, payment allocation, endorsements, renewals, and reinstatement call `OrdinaryLifePolicyService`. |
| Operational evidence | `documents/`, `notes/`, `approvals/` | Evidence, notes, and approval completion call `OrdinaryLifeOperationsService`; no direct status mutation is accepted. |
| History | `workflow-events/`, `policy-transactions/`, `policy-status-history/`, `audit-history/` | Read-only representations with normalized entity and audit filters. |

## Response contract

All endpoints use the platform response envelope:

```json
{
  "success": true,
  "status_code": 200,
  "message": "...",
  "data": {},
  "meta": {
    "timestamp": "...",
    "version": "v1"
  }
}
```

List endpoints support the shared `search` query parameter where configured. Ordinary Life audit history additionally supports `model_name`, `object_id`, and `action`; model names and actions are normalized to the canonical lowercase/uppercase audit conventions before filtering. Workflow history supports `entity_type` and `entity_id` filters.

## Authorization and data scope

Every hardened core viewset requires an authenticated caller and an active Ordinary Life module permission appropriate to the requested action. Read endpoints use the `READ` action, while service-backed transitions map to their corresponding `CREATE`, `UPDATE`, or `APPROVE` capability. Staff and superusers retain the platform’s administrative bypass behavior.

Partner-scoped querysets apply the existing `User.visible_partners()` boundary to applications, proposals, policies, documents, notes, servicing requests, payments, history, and other related aggregates. A partner user therefore cannot retrieve another partner’s policy or workflow records merely by guessing an object identifier.

## Serializer boundaries

Read serializers expose durable database representations and derived labels such as policy numbers, proposal numbers, actor names, and unresolved medical requirements. Write serializers accept only operation inputs. Lifecycle status, actor, timestamps, approval fields, snapshots, transaction links, and audit metadata remain read-only and are populated by domain services.

Monetary input fields use `Decimal("0.01")` minimums. Renewal and reinstatement creation no longer accept client-provided premium or arrears amounts because those values are derived deterministically from the policy’s persisted financial state by the policy service.

Document and note creation enforce an exactly-one-parent rule: each record must belong to either a proposal or a policy, never both and never neither. Policy issuance requires at least one beneficiary allocation payload.

## Verification

The Phase 8 endpoint test module covers authenticated envelope responses, entity search, unauthenticated rejection, independent module-permission rejection, partner-scope filtering, application creation and submission through service-owned actions, and normalized read-only audit-history filters.

Quality gates completed for this phase:

- `python manage.py check`
- `python manage.py makemigrations --check --dry-run`
- Ruff on the Phase 8 serializer, API views, URL registrations, and tests
- `pytest -q apps/ordinary_life/test_phase8_api.py` — 5 passed
- Full backend regression suite — 421 passed, with only the repository’s existing Django/dependency/pagination warnings
