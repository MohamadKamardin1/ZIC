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

## Assessment, fraud, and waiver controls

Prompt 6 exposes `POST /api/v1/ol/claims/{claim_id}/assess/` and requires an assessed amount, assessment findings, and completed document and medical checks. The service calculates the maximum from persisted claim items and rejects any assessed amount above that authoritative total with `CLAIM_ASSESSMENT_AMOUNT_INVALID`. Approved item amounts are allocated proportionally for multi-benefit claims and always sum to the assessed amount without exceeding an item maximum.

Fraud review is explicit: setting `fraud_flag` requires a human-readable `fraud_flag_reason`, which is retained on the claim and in the audit/outbox metadata. Assessment moves the claim to `ASSESSED`, sets the admitting actor/date, emits `ClaimAssessed`, and records the before/after state. Internal staff notes are created through `POST /api/v1/ol/claims/{claim_id}/notes/`, listed through `GET` on the same route, and audited separately.

When the active claim type permits waiver of premium, `waiver_of_premium_days` records the approved period, calculates an end date, and writes a traceable `premium_waiver` object into the policy contract snapshot. Claim types that do not allow waiver reject the request with `CLAIM_WAIVER_INPUT_INVALID`. This is an integration seam for the commitments module and does not silently alter premium schedules outside the policy snapshot.

## Loan offsets and financial interaction

Prompt 7 treats the sum of persisted `OLClaimItem.approved_amount` values as the claim gross amount. `calculate_net_payout(claim_id)` is a read-only calculation: it resolves the policy currency, sums active `DISBURSED` and `PARTIALLY_REPAID` policy-loan balances as outstanding principal plus outstanding interest, and returns gross amount, active loan balance, loan offset, and net payout. It never mutates a loan or creates a ledger row when the financial summary is viewed.

Settlement code calls `apply_loan_offset(claim_id, actor, source_channel, reason)` inside a database transaction. The claim and every active policy loan are locked before balances are read. Allocations are deterministic in loan request order and apply interest before principal, matching the existing OL Loans repayment convention. Each affected loan is updated with the new principal, interest, status, and `updated_by` actor; a `PolicyLoanRepayment` row is created as the OL Loans ledger evidence with the claim number in its reason. A repeated call returns the existing applied offset and does not reduce any balance a second time.

The claims-side `OLClaimLoanOffset` row is the one-per-claim financial summary and references the primary affected loan for relational navigation. Its human-readable JSON breakdown contains every touched loan number, before and after balances, interest/principal allocation, repayment number, status, and any residual closure amount. The linked `PolicyLoanRepayment` rows remain the authoritative per-loan transaction evidence in OL Policies/Loans. This deliberately avoids a denormalized claims loan ledger while preserving a durable claims settlement snapshot and a durable loan-module ledger entry for each loan.

The documented business assumption for a loan balance greater than the approved claim amount is that the claim consumes the full approved amount, produces a zero net payout, and closes all active policy loans as required by the Prompt 7 settlement rule. The breakdown explicitly records the residual closure amount so the exceptional treatment is visible to finance reviewers. A future product or finance policy can replace this closure rule with an approval-controlled residual balance without changing the API shape.

`GET /api/v1/ol/claims/{claim_id}/financial-summary/` requires `ol_claims.view` and returns a `data` object with `claim_number`, `policy_number`, `currency`, `gross_amount`, `loan_offset`, `net_payout`, `loan_offset_applied`, and `loan_breakdown`. Decimal values are kept at two places and serialized by the API renderer; labels use claim, policy, and loan numbers rather than UUIDs. Claim detail also includes a read-only `loan_offset` object after application, and the offset is recorded in the shared audit log and `ClaimLoanOffsetApplied` outbox event with readable before/after balances, actor, reason, source channel, and allocation metadata.

## Requisitions and payment approval

Prompt 8 exposes `POST /api/v1/ol/claims/{claim_id}/raise-requisition/` for assessed claims. The request requires a human-readable narration and sanitized claimant or partner bank details. The service calculates the net payout from approved claim items and active policy-loan balances; it rejects non-assessed claims and zero-net payouts with Error Coach guidance. A claim can have only one requisition, so retries are blocked rather than creating duplicate payment instructions.

A successful request creates the claim-owned `OLClaimRequisition` and a linked `front_office.FORequisition` in the Front Office payment seam. The Front Office row carries a readable `FO-CLM-...` requisition number, Claims department, payable amount, narration, and `PENDING` status. The claim requisition stores the sanitized bank-details payload, narration, amount, `payment_requisition_number`, and approval metadata; the API does not expose the relational payment UUID as a user-facing value.

Payment approval is parameter-driven through the optional `OL_CLAIM_PAYMENT_APPROVAL_THRESHOLD` system parameter. The default is zero when the parameter is not configured, which conservatively routes every positive claim payment through governance approval. When the net payout exceeds the configured threshold, an `ApprovalRequest` is created for module `OL_CLAIMS`, entity `OLClaimRequisition`, action `PAYMENT`, with claim number, policy number, requisition number, amount, currency, gross amount, and loan offset in the request data. The governance approval service emits the shared `approval_status_changed` signal after an approval or rejection is persisted.

The claims receiver consumes only `OL_CLAIMS` payment requests. An approved request moves the claim to `APPROVED`, the claim requisition to `APPROVED`, and the Front Office requisition to `APPROVED`, then emits `ClaimApproved` and writes a central before/after audit row. A rejected request applies the equivalent `REJECTED` statuses, emits `ClaimRejected`, and retains the governance comments as the rejection reason. Repeated delivery of the same outcome is idempotent. Settlement remains a later Prompt 9 action and must not be inferred from requisition approval alone.

## Settlement, discharge, and policy updates

Prompt 9 exposes `POST /api/v1/ol/claims/{claim_id}/settle/` as the final claims transition. Settlement accepts a Front Office `payment_reference` and a confirmed payment status (`CONFIRMED`, `PAID`, or `COMPLETED`); it rejects pending or unreferenced payments and requires an approved requisition when the configured payment approval threshold applies. The operation is transactional and idempotent: an already settled claim is returned with `changed: false` and no duplicate settlement event.

Settlement applies any pending policy-loan offset first, uses the resulting net payout as the settlement amount, marks the claims requisition and linked Front Office requisition `PAID`, stores the payment reference and settlement date, and emits `ClaimSettled`. Death or total-benefit claim categories update the policy to `CLAIM_SETTLED`. Maturity categories update the policy to `MATURITY_SETTLED`, a dedicated lifecycle status. Partial or critical-illness categories keep the policy in force and exhaust matching active policy riders; a product contract snapshot may explicitly enable a reduction of policy sum assured, which is separately audited.

The settlement record stores a reinsurance snapshot for treaty processing: currency, settlement amount, retention amount, ceded amount, and the retention basis. A contract snapshot retention amount takes precedence, then a configured retention percentage, and otherwise the conservative default retains the full amount and emits zero ceded amount. The claims outbox metadata therefore provides readable claim and policy numbers plus payment, loan-offset, policy-update, retention, and ceded-amount inputs without coupling claims to a reinsurance calculation engine.
