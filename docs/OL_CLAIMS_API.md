# ZIC Ordinary Life Claims API

All endpoints are mounted below `/api/v1/ol/` unless the path is explicitly under `/api/v1/portal/claims/`. Requests require the platform’s authenticated session/token and the relevant `ol_claims.*` permission. Responses use the platform structured-error contract: `error_code`, `message`, `resolution_steps`, `field_errors`, and `details`.

## Resource conventions

Claim responses expose `claim_number`, `status`, `status_display`, `policy_number`, `claimant_display`, and readable child values. UUIDs may be present in machine-only identifiers or URLs but are never used as user-facing labels. Money is returned as decimal values by the DRF response and is serialized to two decimal places by JSON clients.

| Resource | Canonical user-facing key |
|---|---|
| Claim | `claim_number` |
| Policy | `policy_number` |
| Claimant | `claimant_display` / name |
| Requisition | `requisition_number` |
| Payment | Front Office payment reference |
| Loan | `loan_number` |
| Document | document type, template code/version, generated timestamp |

## Claims and options

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/v1/ol/claims/` | Paginated staff worklist with search and filters. |
| GET | `/api/v1/ol/claims/{claim_id}/` | Claim detail, child records, financial evidence, actions, and audit timeline. |
| GET | `/api/v1/ol/claims/kpis/` | Aggregated counts and monetary KPIs using the same filters as the list. |
| GET | `/api/v1/ol/claims/export.csv` | Filtered CSV export of authorized claim rows. |
| GET | `/api/v1/ol/claims/options/types/` | Effective claim type options. |
| GET | `/api/v1/ol/claims/options/reasons/` | Effective reason options. |
| GET | `/api/v1/ol/claims/options/benefits/` | Policy-compatible benefit options. |
| GET | `/api/v1/ol/claims/options/members/` | Policy member options. |

List filters include `q`, `status`, `claim_type`, `medical_status`, `fraud_flag`, `policy_number`, `claim_date_from`, `claim_date_to`, `agent`, and `branch` where the issued-policy lineage provides the value. Pagination uses the platform list envelope with `count`, `next`, `previous`, and `results`.

## Registration and evidence

```http
POST /api/v1/ol/policies/{policy_id}/claims/
X-Idempotency-Key: claim-registration-001
X-Source-Channel: WEB
Content-Type: application/json
```

The request includes `claim_type`, `claim_date`, `cause_of_claim`, `description`, `member_id`, `claimant_details`, and `benefit_type`. The server validates policy status, lapsed grace, effective claim setup, waiting periods, duplicate rules, benefit compatibility, and calculated maximum. A new claim returns `201`; a same-fingerprint retry returns `200`; a changed payload with the same idempotency key returns a structured `409`.

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/v1/ol/claims/{claim_id}/documents/` | List requirements, missing types, and uploaded evidence. |
| POST | `/api/v1/ol/claims/{claim_id}/documents/` | Upload one evidence document. |
| GET/POST | `/api/v1/ol/claims/{claim_id}/assessment-readiness/` | Inspect or enforce document and medical readiness. |

## Medical and assessment

| Method | Endpoint | Purpose |
|---|---|---|
| GET/POST | `/api/v1/ol/claims/{claim_id}/medical/require/` | Inspect or require a medical review. |
| POST | `/api/v1/ol/claims/{claim_id}/medical/evaluate/` | Evaluate applicable medical limits and review status. |
| POST | `/api/v1/ol/claims/{claim_id}/medical/result/` | Record Cleared, Loading, or Rejected outcome. |
| POST | `/api/v1/ol/claims/{claim_id}/assess/` | Save approved amount, notes, fraud decision, and waiver period. |
| POST | `/api/v1/ol/claims/{claim_id}/notes/` | Add an internal file note. |

Assessment requires mandatory documents and a compatible medical outcome. Approved item amounts cannot exceed calculated amounts. Fraud flags require a reason. Waiver periods are validated against the effective claim type and are snapshotted on the claim and policy.

## Financials, requisitions, approvals, and settlement

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/v1/ol/claims/{claim_id}/financial-summary/` | Side-effect-free gross, active loans, offset, net payout, currency, and readable loan allocations. |
| POST | `/api/v1/ol/claims/{claim_id}/raise-requisition/` | Create the claim payment requisition and link the Front Office request. |
| POST | `/api/v1/ol/claims/{claim_id}/settle/` | Confirm Front Office payment and settle the claim. |
| POST | `/api/v1/ol/claims/{claim_id}/print-discharge-voucher/` | Render a branded discharge voucher through the unified Documents engine. |

Requisition requests include `bank_details` and optional `narration`. The server calculates the positive net payout, applies any configured approval threshold, and returns a readable `requisition_number`, status, amount, Front Office payment reference, and approval status. Settlement requires an approved requisition, confirmed payment status, and a payment reference. The settlement transaction records the amount, policy status update, rider/benefit effects, and reinsurance snapshot.

The financial summary never changes balances. At settlement, the loan-offset transaction locks the claim, policy, and active loans, allocates interest before principal, writes OL Policies repayment ledger records, and records `ClaimLoanOffsetApplied` evidence. A repeated settlement or offset request is idempotent.

## Portal endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/v1/portal/claims/` | List only claims for the authenticated user’s linked partner. |
| GET | `/api/v1/portal/claims/{claim_number}/` | Open a scoped claim by human-readable claim number. |
| POST | `/api/v1/portal/claims/register/` | Register a claim through the restricted portal contract. |

Portal registration requires `X-Idempotency-Key` and accepts policy number, claim type, claim date, narrative, benefit type, member reference, and claimant details. Staff-only amounts, statuses, approvals, payment confirmation, and policy updates are rejected.

## Documents response

The discharge-voucher response follows the unified Documents contract:

```json
{
  "success": true,
  "data": {
    "instance": {"id": "machine identifier", "document_type": "DISCHARGE_VOUCHER", "template_version": 1, "page_count": 1},
    "preview_blob_base64_or_url": "/api/v1/documents/instances/.../preview/",
    "signed_download_url": "/api/v1/documents/download/.../?ticket=..."
  }
}
```

The document instance retains the claim source link and template version. The signed URL is short-lived and permission-checked; Bearer-authenticated preview/download remains the primary path. `TEMPLATE_PENDING` means an approved active template is not configured.

## Durable events and audit

Claim lifecycle events are stored in the shared DomainEvent outbox. All material changes create central AuditLog rows with actor, before/after state, reason, source channel, correlation ID, and readable object representation. Supported event names include `ClaimRegistered`, `ClaimDocumentUploaded`, `ClaimMedicalRequired`, `ClaimMedicalResultRecorded`, `ClaimAssessed`, `ClaimLoanOffsetApplied`, `ClaimRequisitioned`, `ClaimApproved`, `ClaimRejected`, `ClaimSettled`, and `ClaimCancelled`.

## Example structured error

```json
{
  "success": false,
  "error_code": "CLAIM_MANDATORY_DOC_MISSING",
  "message": "One or more mandatory claim documents are missing.",
  "resolution_steps": [
    "Upload every document listed in the claim requirements.",
    "Refresh the readiness check and retry assessment."
  ],
  "field_errors": {}
}
```
