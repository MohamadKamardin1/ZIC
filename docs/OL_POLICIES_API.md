# ZIC Ordinary Life Policies — API Contract

All routes below are mounted under `/api/v1/ol/policies/` unless a full path is shown. Requests require the platform’s authenticated session or bearer token. The server is authoritative for permissions, lifecycle eligibility, calculation, and idempotency.

## Response conventions

Successful responses use the platform envelope:

```json
{
  "data": {
    "id": "…",
    "policy_number": "OL-…",
    "status": "ACTIVE"
  }
}
```

List responses are table-first and include display fields rather than exposing a bare foreign-key identifier as the user-facing value. Dates use ISO `YYYY-MM-DD`; monetary values are serialized as decimal strings; status values are stable uppercase codes. Structured failures contain an error code, human-readable message, details, field errors where applicable, resolution steps, and documentation reference.

## Read endpoints

| Method and route | Permission | Purpose |
| --- | --- | --- |
| `GET /api/v1/ol/policies/` | `ol_policies.view` | Search, filter, sort, paginate, and export-ready policy rows |
| `GET /api/v1/ol/policies/{id}/` | `ol_policies.view` | Policy header, snapshot children, commitments, proposal link, actions, and audit snippet |
| `GET /api/v1/ol/policies/kpis/` | `ol_policies.view` | Active, lapsed, new, maturing-soon, sum-assured, and value indicators |
| `GET /api/v1/ol/policies/{id}/endorsements/` | `ol_policies.view` | Immutable servicing history |
| `GET /api/v1/ol/policies/{id}/maturity/` | `ol_policies.view` | Maturity claim and payout state |
| `GET /api/v1/ol/policies/{id}/loans/` | `ol_policies.view` | Policy loan history and balances |
| `GET /api/v1/ol/policies/{id}/withdrawals/` | `ol_policies.view` | Withdrawal requests and payout requisitions |
| `GET /api/v1/ol/policies/{id}/documents/` | `ol_policies.print` | Generated contract and schedule instances |
| `GET /api/v1/ol/policies/{id}/audit/` | `ol_policies.view` | Policy-domain audit history |

Supported list query parameters include `q`, `status`, `product`, `agent`, `branch`, `currency`, `commencement_from`, `commencement_to`, `maturity_from`, `maturity_to`, `page`, `page_size`, `ordering`, and `format=csv` where the route supports export. Filtered responses preserve the same table column contract as the unfiltered list.

## Issuance

`POST /api/v1/ol/policies/issue/` requires `ol_policies.create` and accepts:

```json
{
  "proposal_id": "proposal-uuid"
}
```

The proposal must be in `AWAITING_FIRST_PREMIUM` or `PAYMENT_READY`, must have a selected plan, and must have a fully funded `COMPLETED` first-premium commitment. A successful first call returns HTTP `201`; an idempotent retry returns HTTP `200` with the same policy and `created=false`. The operation copies contract terms and child records, links the proposal through `policy_ref`, emits `PolicyIssued`, and audits the actor and source channel.

## Servicing

`POST /api/v1/ol/policies/{id}/endorsements/` requires `ol_policies.endorse` and accepts an endorsement type, changes, effective date, description, reason, and optional source channel. Supported types include `PREMIUM_CHANGE`, `TERM_CHANGE`, `MEMBER_ADD`, `MEMBER_REMOVE`, `BENEFICIARY_CHANGE`, and `ADDRESS_CHANGE`. The response includes the endorsement and any premium-adjustment commitment.

`POST /api/v1/ol/policies/{id}/reinstate/` requires `ol_policies.reinstate` and accepts `payment_amount`, `medical_clearance`, and optional `as_of`. The policy must be lapsed, within the active configured window, and compliant with payment and medical requirements.

`POST /api/v1/ol/policies/{id}/surrender/` requires `ol_policies.cancel` or the configured servicing entitlement and accepts optional `as_of`. The operation creates a surrender request and front-office payment requisition and changes status to `SURRENDER_PENDING`. A retry returns the existing pending request.

`POST /api/v1/ol/policies/{id}/paid-up/` requires servicing permission and converts an eligible lapsed policy using the active paid-up setup and rate. Future premium commitments are stopped and the resulting policy status is `PAID_UP`.

`POST /api/v1/ol/policies/{id}/cancel/` requires `ol_policies.cancel` and requires a non-empty cancellation `reason`. The service distinguishes free-look refund cancellation from standard cancellation and records the decision in the contract snapshot.

## Finance

`POST /api/v1/ol/policies/{id}/loans/` requests a loan. Approval and disbursement are separate actions:

```text
POST /api/v1/ol/policies/loans/{loan_id}/approve/
POST /api/v1/ol/policies/loans/{loan_id}/disburse/
POST /api/v1/ol/policies/loans/{loan_id}/repay/
```

Requests are checked against product flags, cash value, percentage and amount limits, currency, and approval configuration. Repayments accept a positive amount and optional payment date, apply interest before principal, and maintain same-day interest idempotency.

`POST /api/v1/ol/policies/{id}/withdrawals/` requests an allowed withdrawal, checks cash value after active loans and previous withdrawals, and creates the payment requisition.

## Maturity

`POST /api/v1/ol/policies/{id}/maturity/` creates or returns the policy’s maturity claim when the policy is eligible. Approval and payment are separate actions:

```text
POST /api/v1/ol/policies/maturity/{claim_id}/approve/
POST /api/v1/ol/policies/maturity/{claim_id}/pay/
```

Approval may require `documents_verified=true`. Payment requires a non-empty `payment_reference`. The final payment changes the policy from `MATURED_PENDING_PAYMENT` to `MATURED`, pays the linked requisition, emits `PolicyMaturityPaid`, and writes an audit row.

## Integration routes

The integration seam avoids hard dependencies on future claims and reinsurance applications:

| Method and route | Purpose |
| --- | --- |
| `GET /api/v1/ol/policies/{id}/claims-registration/` | Active coverage, members, benefits, and riders for claims registration |
| `GET /api/v1/ol/policies/{id}/reinsurance-risk/` | Reinsurance-ready risk payload without a reinsurance app dependency |
| `POST /api/v1/ol/policies/{id}/claim-settled/` | Idempotent claim-settlement ingress; exhausting claims close policy coverage |
| `GET /api/v1/ol/policies/portal/` | Partner-scoped portal list |
| `GET /api/v1/ol/policies/portal/{id}/` | Partner-scoped portal detail with sensitive values entitlement-gated |
| `GET /api/v1/ol/policies/dashboard-hooks/` | Active count, annualized premium, and lapsed ratio for dashboard consumers |

Notification and maturing-soon adapters queue `PolicyNotificationLog` and dashboard notifications. They are clean provider seams and do not hard-wire a particular email or SMS vendor.

## Errors and idempotency

Common error codes include `POLICY_NOT_FOUND`, `POLICY_ALREADY_ISSUED`, `POLICY_INVALID_STATUS`, `POLICY_FIRST_PREMIUM_NOT_POSTED`, `POLICY_SURRENDER_BLOCKED`, `POLICY_LOAN_BLOCKED`, `POLICY_LAPSED`, `POLICY_NOT_MATURED`, and `POLICY_ENDORSEMENT_INVALID`. A caller should display `message`, field errors, and resolution steps together.

The server treats issuance, lapse, maturity, surrender request, claim settlement, notification enqueue, and maturing-soon reminders as retry-safe operations. Clients may safely retry after a network timeout and should use the returned existing record when `created=false` or an idempotent marker is present.
