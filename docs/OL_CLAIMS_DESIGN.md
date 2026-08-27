# Ordinary Life Claims Design

## Purpose and scope

The Ordinary Life Claims bounded context manages the controlled journey from a claim notification through documentation, assessment, payment requisition, approval, and settlement. It owns claim workflow state, claimant identity captured for the event, benefit assessment items, claim evidence, file notes, and the payment requisition record. It does not duplicate policy, loan, reinsurance, or payment ledgers; instead, it records stable references and emits durable domain events for those bounded contexts to consume.

The design is intentionally table-first and audit-first. Every material workflow transition must be attributable to an actor, a before and after state, a reason where applicable, a source channel, and a correlation identifier when the request pipeline provides one. User-facing failures use the platform Error Coach contract with a code, clear message, resolution steps, and optional field-level guidance.

## Claim lifecycle

The canonical business flow is:

```text
REGISTERED -> ASSESSMENT -> ASSESSED -> REQUISITIONED -> APPROVED -> SETTLED
```

The model also supports controlled side states required by underwriting and servicing: `PENDING_MEDICAL`, `REJECTED`, and `CANCELLED`. `REQUISITION` is retained as a compatibility/preparation state for workflows that separate requisition drafting from final submission. A claim must not skip a required preceding state through a client-side status update; later prompts will add the service-layer transition guards.

| State | Meaning | Typical owner | Exit conditions |
|---|---|---|---|
| `REGISTERED` | Initial claim record and claimant details have been captured. | Claims intake | Basic eligibility passes and documentation is available for assessment. |
| `PENDING_MEDICAL` | Medical or underwriting evidence is required before assessment. | Medical / underwriting | Medical result is cleared or the claim is rejected. |
| `ASSESSMENT` | Claim evidence and covered benefits are being reviewed. | Claims assessor | Assessment is completed and benefit items have approved values. |
| `ASSESSED` | Assessment is complete and amounts are ready for payment requisition. | Claims supervisor | Net payable amount is confirmed and requisition can be raised. |
| `REQUISITIONED` | A payment requisition is linked to the claim. | Finance / Front Office | Approval workflow completes or rejects the requisition. |
| `APPROVED` | Payment has been approved for the claim. | Approver | Front Office confirms payment. |
| `SETTLED` | Payment has been confirmed and the claim is closed financially. | Finance / Claims | Terminal state; corrections use an explicitly governed reversal process. |
| `REJECTED` | Claim or requested benefit was declined with a documented reason. | Claims supervisor | Terminal for the current claim attempt. |
| `CANCELLED` | Claim was withdrawn or administratively cancelled with a reason. | Claims supervisor | Terminal for the current claim attempt. |

State labels are stored as stable uppercase codes and displayed using human-readable labels. The UI must derive available actions from the server action matrix and the user’s claims permissions.

## Claimants and claim items

A claim can identify a `POLICYHOLDER`, `INSURED`, or `DEPENDENT` claimant. The `OLClaimant` record snapshots the name, identity number, relationship, age, and gender at registration so the claim remains intelligible even if a policy party record changes later. `claimant_ref` on `OLClaim` points to the selected claimant; the one-to-many claimant relation allows future claims with multiple claimant records while preserving a clear primary reference.

Each `OLClaimItem` represents one covered benefit or rider assessment. It stores the captured sum assured, the backend-calculated maximum, the approved amount, and any adjustment reason. Later assessment services must enforce that the approved amount does not exceed the calculated amount unless an explicitly approved exception workflow is introduced.

## Documents, notes, and requisitions

`OLClaimDocument` records evidence linked to the claim, including the document type, storage reference, mandatory flag, uploader, and upload time. It is a metadata record; binary storage remains behind the platform storage abstraction. `OLClaimFileNote` is an internal operational note and is not a partner-portal disclosure by default.

`OLClaimRequisition` is the claims-side payment request. It retains the requisition number, amount, sanitized bank-details payload, and requisition status. The Front Office payment seam will consume a stable claim/requisition reference rather than reaching into claims tables directly.

## Integration map

| Bounded context | Direction | Contract | Claims responsibility |
|---|---|---|---|
| OL Policies | Claims reads; policy lifecycle may consume events | Policy reference, status, risk commencement, benefits, members | Verify the policy is eligible and later apply claim-settlement status changes through a service seam. |
| OL Policy Members | Claims reads | Policy member reference and benefit relationship | Resolve eligible insured/dependent claimants without exposing internal identifiers to users. |
| OL Parameters | Claims reads | Claim types, reasons, benefit coverage, waiting periods, mandatory documents, medical triggers | Drive validation and document requirements; no hardcoded business rules in the UI. |
| OL Loans | Claims reads/writes through service seam | Active loan balance and offset transaction | Deduct outstanding loan balance from claim payout and record a controlled offset. |
| Reinsurance | Claims publishes | `ClaimSettled` payload with claim, benefit, retention, and ceded-amount inputs | Emit settlement data; reinsurance calculations remain owned by the reinsurance context. |
| Front Office Payments | Claims publishes/consumes | Requisition reference, payment confirmation, payment failure | Create or link a payment requisition and settle only after payment confirmation. |
| Approvals | Claims publishes/consumes | Approval request and approved/rejected events | Route threshold payments and update claim status from approval outcomes. |
| Notifications | Claims publishes | Registered, assessed, and settled events | Provide notification payloads without coupling claims to a delivery provider. |
| Documents | Claims requests | Unified document type and source reference | Later prompts will generate discharge vouchers through the shared print engine. |

## Events

The claims outbox uses the shared `DomainEvent` model with aggregate type `OLClaim`. Prompt 1 registers the following stable event names:

| Event | Emitted when | Minimum payload |
|---|---|---|
| `ClaimRegistered` | A valid claim is created. | Claim number, claim ID, policy number, claim type, actor, source channel, and target status. |
| `ClaimAssessed` | Assessment is completed. | Claim number, assessed values, actor, reason, and target status. |
| `ClaimDocumentUploaded` | Claim evidence is linked. | Claim number, document type, actor, source channel, and target status. |
| `ClaimRequisitioned` | A payment requisition is submitted. | Claim number, requisition number, amount, actor, and target status. |
| `ClaimApproved` | The payment request is approved. | Claim number, approved amount, actor, reason, and target status. |
| `ClaimSettled` | Front Office confirms payment. | Claim number, settlement amount, policy number, actor, source channel, and reinsurance inputs. |
| `ClaimCancelled` | A claim is cancelled. | Claim number, reason, actor, source channel, and target status. |

All event payloads include `from_status`, `to_status`, `reason`, `source_channel`, and a metadata object. IDs are retained for machine correlation; user-facing serializers and documents must use claim numbers, policy numbers, and names.

## Permissions

The claims module uses the following permission codes:

| Permission | Intended capability |
|---|---|
| `ol_claims.view` | View the claims register and claim detail. |
| `ol_claims.register` | Register a claim and attach intake evidence. |
| `ol_claims.assess` | Perform assessment and manage internal assessment notes. |
| `ol_claims.requisition` | Raise and manage payment requisitions. |
| `ol_claims.approve` | Approve or reject a claim payment decision. |
| `ol_claims.settle` | Confirm final settlement after payment confirmation. |
| `ol_claims.cancel` | Cancel a claim with an auditable reason. |
| `ol_claims.print` | Generate or preview controlled claim documents. |

A repeatable `seed_ol_claim_permissions` management command creates the permissions, a permission bundle, and viewer/handler/administrator system groups. Superusers retain the platform’s existing unrestricted behavior; all other users are evaluated against the normalized claims permission code or claims module entitlement.

## Prompt 1 assumptions

The existing `ol_policies.Policy` model is the source of policy truth, so `OLClaim.policy_ref` is a protected foreign key rather than a duplicated policy number. Claim types, benefit types, reasons, waiting periods, and mandatory documents are represented as strings in the foundation because the parameter app owns their evolving catalogs; later prompts will resolve and validate those codes through the OL Claim Setup configuration APIs.

Claim amount is not stored directly on `OLClaim` in the foundation. The authoritative claim amount is the sum of claim items, where calculated and approved amounts are held at benefit level. This prevents a second total from drifting and gives assessment and loan-offset services a precise audit surface. Requisitions are one-to-one with a claim for the first release; a later payment or retry design can add a controlled requisition history without changing the initial claim identity.

## Validation engine and option contract

Prompt 2 introduces the `validate_eligibility(policy, member, claim_type, claim_date)` service as the single registration gate. It resolves an active, effective-dated `OLClaimType`, checks policy status, applies a configured lapsed grace period, enforces the claim-type waiting period from risk commencement, evaluates explicit product or benefit compatibility rules, and applies the configured duplicate rule against settled claims. Each check writes a central audit record with the policy number, check name, pass/fail result, actor, source channel, and resolution details before the service returns or raises a structured error.

The benefit base service, `calculate_max_claimable(policy, benefit_type)`, uses the configured claim type calculation basis. `SUM_ASSURED` reads the issued policy sum assured, `CASH_VALUE` reads the policy contract snapshot, `BENEFIT_AMOUNT` resolves the matching issued policy benefit, `FIXED_AMOUNT` and `PERCENTAGE` use configured `payable_to_rules`, and a configured maximum cap is always applied. Amounts are returned to two decimal places and never computed or trusted in the frontend.

Claim option APIs return the same standardized shape used by the platform SmartSelect components:

```json
{
  "value": "DEATH_CLAIM",
  "label": "DEATH_CLAIM — Death Claim",
  "meta": {
    "claim_category": "DEATH",
    "calculation_basis": "SUM_ASSURED",
    "waiting_period_days": 0,
    "require_documents": ["DEATH_CERTIFICATE"]
  }
}
```

| Endpoint | Scope | Notes |
|---|---|---|
| `GET /api/v1/ol/claims/options/types/` | Active current claim types | Supports `q`, `page`, and `page_size`; returns calculation and document metadata. |
| `GET /api/v1/ol/claims/options/reasons/` | Active current claim reasons | Supports `q` and optional `claim_type` code or UUID filter. |
| `GET /api/v1/ol/claims/options/benefits/?policy_id=` | Issued policy benefits and riders | Policy-specific; requires `policy_id` and returns policy number in metadata, never in the label as an internal UUID. |
| `GET /api/v1/ol/claims/options/members/?policy_id=` | Active issued policy members | Policy-specific; labels use member name and relationship while metadata carries DOB, gender, and benefit amount. |

The option envelope includes `data.items`, `data.results`, `data.count`, and a `data.pagination` object with page, page size, total, and navigation flags. Malformed pagination, missing policy references, inactive policies, missing claim types, waiting periods, duplicates, and incompatible benefits all return Error Coach responses with a stable code and resolution steps.

## Mandatory documents and progression

Prompt 4 uses the active claim type’s `require_documents` configuration as the sole source of mandatory evidence. `get_required_documents(claim_type)` resolves the current effective-dated parameter and returns normalized document type codes. `document_requirement_status(claim)` compares those requirements with uploaded document types and returns `required_document_types`, `uploaded_document_types`, `missing_document_types`, and `all_mandatory_uploaded`.

Claim evidence is managed through `GET/POST /api/v1/ol/claims/{claim_id}/documents/`. Multipart uploads are stored through Django’s configured `default_storage` under a claim-number path; controlled `file_reference` values remain supported for managed storage integrations. Uploads are upserted by claim and document type, marked mandatory from the parameter configuration, and audited with actor, source channel, claim number, and document type. The response includes completeness and missing-document data so clients can teach the operator what remains.

`POST /api/v1/ol/claims/{claim_id}/assessment-readiness/` is the progression guard. It returns success only when every configured mandatory document is present. Otherwise it raises `CLAIM_MANDATORY_DOC_MISSING` with the missing and required document types in `error.details` and resolution steps directing the operator to the Documents section. The same requirement summary is available through the readiness `GET` endpoint for non-mutating UI checks.

## Medical and underwriting integration

Prompt 5 persists medical workflow state on each claim using `medical_status` values `NONE`, `PENDING`, `CLEARED`, `REJECTED`, and `LOADING`, together with the medical result, reason, reviewer, timestamps, and applied loading factor. `evaluate_medical_requirements(claim)` reads current claim-type rules, medical evidence requirements, claimant age, claim amount, and effective-dated `OLMedicalLimit` records. A configured medical requirement moves the claim to `PENDING_MEDICAL`; otherwise the claim remains available for assessment.

The API exposes `POST /api/v1/ol/claims/{claim_id}/medical/evaluate/`, `/medical/require/`, and `/medical/result/`. A reviewer may record `CLEARED`, `REJECTED`, or `LOADING`. Rejection moves the claim to `REJECTED` and requires a reason. Loading requires a positive factor no greater than 10, or a percentage that is converted to a factor; each claim item is updated transactionally and records the applied factor in its adjustment reason. Cleared and loaded claims return to `REGISTERED` for the next workflow stage.

Assessment readiness now checks both document completeness and medical state. Pending medical review raises `CLAIM_MEDICAL_REVIEW_REQUIRED`; a rejected medical outcome raises `CLAIM_MEDICAL_REJECTED`. Medical requirement evaluation, manual requests, and results are recorded in the central audit log and durable claims outbox with actor, before/after status, reason, source channel, amount, age, and loading metadata.
