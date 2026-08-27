# Ordinary Life Withdrawals API

## Contract principles

The OL Withdrawals APIs are backend-authoritative. The Django service validates policy status, cash value, loan balances, withdrawal limits, fee configuration, duplicate requests, lifecycle transitions, permissions, and audit requirements. Frontends must render the supplied display fields and must not expose raw foreign-key UUIDs as human-facing labels.

All JSON responses use the project response envelope. Successful responses are returned as `{ "data": ... }`; paginated endpoints return `count`, `results`, `next`, and `previous` inside `data`. Error responses use the platform’s canonical snake_case keys (`error_code`, `field_errors`, `resolution_steps`) and camelCase aliases (`errorCode`, `fieldErrors`, `resolutionSteps`) so existing clients remain compatible. All errors include a teachable code, message, and resolution steps.

## Staff endpoints

| Method | Endpoint | Permission | Purpose |
|---|---|---|---|
| `GET` | `/api/v1/ol/withdrawals/` | `ol_withdrawals.view` | Paginated staff register. Supports `q`, `search`, `status`, `product`, `branch`, `agent`, `date_from`, `date_to`, `pending_approval_only`, `page`, `page_size`, and `ordering`. |
| `GET` | `/api/v1/ol/withdrawals/kpis/` | `ol_withdrawals.view` | Current-month withdrawn amount/count, pending approvals, processing payouts, average fee, currency, optional amounts by currency, and timestamp. Accepts the same scope filters as the list. |
| `GET` | `/api/v1/ol/withdrawals/options/policies/` | `ol_withdrawals.request` | Searchable eligible-policy options. Each option has `value`, `label`, and `meta` including policy number, policyholder, product, status, currency, cash value, loan balance, and available limit. |
| `GET` | `/api/v1/ol/withdrawals/options/products/` | `ol_withdrawals.view` | Active product options for list filtering. |
| `GET` | `/api/v1/ol/withdrawals/options/branches/` | `ol_withdrawals.view` | Active branch options for list filtering. |
| `GET` | `/api/v1/ol/withdrawals/options/agents/` | `ol_withdrawals.view` | Active agent options for list filtering. |
| `GET` | `/api/v1/ol/withdrawals/options/payment-modes/` | `ol_withdrawals.process_payout` | Active payout payment modes. |
| `GET` | `/api/v1/ol/withdrawals/{id}/` | `ol_withdrawals.view` | Withdrawal detail with policy-safe display labels, financial fields, allowed actions, policy context, and embedded related information where available. |
| `GET` | `/api/v1/ol/withdrawals/{id}/breakdown/` | `ol_withdrawals.view` | Auditable withdrawal calculation and policy-impact values. |
| `GET` | `/api/v1/ol/withdrawals/{id}/payments/` | `ol_withdrawals.view` | Read-only payout payment records. |
| `GET` | `/api/v1/ol/withdrawals/{id}/audit/` | `ol_withdrawals.view` | Paginated actor/source/reason/timestamp audit timeline. |
| `POST` | `/api/v1/ol/withdrawals/estimate/` | `ol_withdrawals.request` | Backend fee and net-payout estimate. Body: `{ "policy_id": "…", "amount": "250000.00" }`. |
| `GET` | `/api/v1/ol/policies/{policy_id}/withdrawals/eligibility/` | `ol_withdrawals.request` | Rechecks policy eligibility and returns cash value, loan balance, available limit, fee rate, and fee basis. |
| `POST` | `/api/v1/ol/policies/{policy_id}/withdrawals/request/` | `ol_withdrawals.request` | Canonical idempotent staff request endpoint. Body: `{ "amount": "250000.00", "reason": "Education expenses", "as_of": "YYYY-MM-DD" }`. Send an `X-Idempotency-Key`. |
| `POST` | `/api/v1/ol/policies/{policy_id}/withdrawals/` | `ol_withdrawals.request` | Backward-compatible creation route using the same finance service, fee rules, audit events, and idempotency behavior. |

## Lifecycle endpoints

| Method | Endpoint | Permission | Required body |
|---|---|---|---|
| `POST` | `/api/v1/ol/withdrawals/{id}/approve/` | `ol_withdrawals.approve` | `{ "reason": "Eligibility and documents verified" }` |
| `POST` | `/api/v1/ol/withdrawals/{id}/reject/` | `ol_withdrawals.approve` | `{ "reason": "Reason for rejection" }` |
| `POST` | `/api/v1/ol/withdrawals/{id}/process-payout/` | `ol_withdrawals.process_payout` | `{ "payment_mode": "BANK_TRANSFER", "receipt_reference": "RCT-0001" }` |
| `POST` | `/api/v1/ol/withdrawals/{id}/cancel/` | `ol_withdrawals.cancel` | `{ "reason": "Customer cancelled request" }` |
| `POST` | `/api/v1/ol/withdrawals/{id}/reverse/` | `ol_withdrawals.reverse` | `{ "reason": "Payment reversed after reconciliation" }` |

The server validates the current status and permission on every action. Approval, rejection, cancellation, and reversal require a non-empty reason. Payout requires a configured payment mode and receipt reference. Reversal restores the policy cash-value state according to the finance service and records the policy impact in the audit trail.

The normalized withdrawal response contains `withdrawalNumber`, `policyNumber`, `policyDisplay`, `policyholderDisplay`, `productDisplay`, `agentDisplay`, `branchDisplay`, `currency`, `grossAmount`, `feeAmount`, `netPayout`, `cashValueBefore`, `loanBalanceBefore`, `cashValueAfter`, `status`, `statusDisplay`, lifecycle timestamps, `reason`, and `allowedActions`. `allowedActions` is the backend action matrix and must be intersected with the authenticated user’s permissions in the UI.

## Partner portal API

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/v1/portal/withdrawals/` | Returns only withdrawals within the authenticated partner’s visible scope. Supports `q`, `status`, `page`, and `page_size`. |
| `GET` | `/api/v1/portal/withdrawals/{id}/` | Returns one portal-safe scoped withdrawal or `404` when it is outside the partner scope. |
| `POST` | `/api/v1/portal/withdrawals/` | Limited partner request flow. Body: `{ "policy_id": "…", "amount": "…", "reason": "…", "as_of": "YYYY-MM-DD" }`. Reuses the same eligibility, amount, idempotency, permission, and audit service as staff requests. |

Portal responses use `requestNumber`, `policyNumber`, `policyholderDisplay`, `productDisplay`, `currency`, `grossAmount`, `netPayout`, `statusDisplay`, `requestedAt`, `reason`, and `requestAllowed`. Sensitive fee and loan fields are omitted by default unless the backend explicitly authorizes their disclosure. Partner users cannot approve, reject, process payouts, cancel staff requests, reverse withdrawals, or access staff audit controls.

## Documents and authenticated print

`POST /api/v1/ol/withdrawals/{id}/print-statement/` requires `ol_withdrawals.print` and returns a unified document response containing `instance`, `preview_url` or an equivalent preview value, and `signed_download_url`. The document type is `OL_WITHDRAWAL_STATEMENT`. The instance preserves the source app/model/object ID, template code/version, generated actor/time, correlation ID, page count, checksum, and file references.

The statement is rendered through the shared `DocumentEngine` with the `OL_WITHDRAWAL_STATEMENT_UNIFIED` template. It includes the withdrawal number, policy and policyholder labels, financial calculation, fee basis, net payout, policy impact, status watermark for cancelled/reversed requests, signatures, and the standard branded footer.

The document instance download contract is:

```text
GET /api/v1/documents/instances/{instance_id}/download/?ticket={short_lived_ticket}
```

A valid authenticated Bearer request or valid short-lived single-purpose ticket is required. Frontends should prefer `fetchAuthenticatedDocument`/`openAuthenticatedDocument` for preview and download. They must not open a protected raw `/api/` URL directly. Ticket expiry, tampering, missing templates, branding failures, storage failures, and permission failures return structured teachable errors and are audited.

## Error contract

| Code | HTTP status | Meaning |
|---|---:|---|
| `WITHDRAWAL_LIMIT_EXCEEDED` | `422` | Requested amount exceeds the backend-computed Available Limit. `fieldErrors.amount` may include the maximum. |
| `WITHDRAWAL_POLICY_INELIGIBLE` | `422` | Policy lifecycle, product configuration, cash-value, loan, or parameter rules block the request. |
| `WITHDRAWAL_REASON_REQUIRED` | `422` | Controlled action requires a reason. |
| `WITHDRAWAL_PAYMENT_REQUIRED` | `422` | Payout requires payment mode and receipt reference. |
| `WITHDRAWAL_ACTION_INVALID` | `422` | Current status does not allow the requested lifecycle action. |
| `DOCUMENT_RENDER_FAILED` | `500` | Unified HTML/PDF rendering or storage failed. Resolution steps include checking active template/branding and retrying with the correlation ID. |
| `TEMPLATE_PENDING` | `409` | No active approved withdrawal statement template is available. |
| `401` | `401` | Authentication is missing or expired. The frontend should refresh once where supported, then show a sign-in ErrorCoach. |

## Audit requirements

Every request and lifecycle action records the authenticated actor, action, source channel, reason where applicable, correlation ID, and affected withdrawal. The request service emits the durable `POLICY_WITHDRAWAL_REQUESTED` domain event and updates policy withdrawal totals transactionally. Document generation and download events include the document instance, document type, template version, actor, and source channel. The audit trail is append-only and is exposed through the staff detail audit endpoint with human-readable actor labels.
