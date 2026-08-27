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
