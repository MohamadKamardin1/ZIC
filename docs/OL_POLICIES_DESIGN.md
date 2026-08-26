# Ordinary Life Policies Design

## Status and purpose

This document defines the first bounded-context contract for **Ordinary Life Policies**. The policy is the definitive servicing record created from an agreed proposal after the first premium is posted. Upstream quotation and proposal records remain valuable for traceability, but the issued policy owns the contract snapshot used by servicing, claims, loans, surrender, maturity, and reporting workflows.

## Domain boundary

The `apps.ol_policies` Django application owns the issued policy aggregate and its immutable-at-issuance children. It deliberately does not yet implement issuance, lifecycle commands, financial transactions, or document rendering; those capabilities are delivered in subsequent prompts against this foundation.

| Aggregate or record | Responsibility | Relationship |
| --- | --- | --- |
| `Policy` | Definitive contract header and issuance snapshot | References the canonical OL proposal and policyholder; stores product/plan reference, financial terms, dates, and current lifecycle status |
| `PolicyMember` | Covered principal or dependent snapshot | Owned by one policy; relation is stored as the parameter code used at issuance |
| `PolicyRider` | Attached rider snapshot | Owned by one policy; rider code and monetary values are copied at issuance |
| `PolicyBenefit` | Benefit snapshot | Owned by one policy; benefit type, basis, and amount are copied at issuance |
| `PolicyEndorsement` | Versioned material servicing change | Owned by one policy; before and after JSON snapshots preserve history |
| `PolicyAuditLog` | Immutable policy event and state-change trail | Owned by one policy and records actor, state diff, reason, channel, and correlation ID |

## Contract snapshot rule

The policy header and child tables are contract snapshots. Issuance must copy the agreed terms from the proposal rather than relying on mutable product, quotation, or parameter records for historical servicing. `contract_snapshot` provides an extensible JSON preservation area for additional agreed terms that do not yet have first-class columns. Later endorsements must create a new version or a new snapshot row and must not silently overwrite historical values.

The current foundation uses explicit scalar fields for the primary servicing values: policy number, proposal reference, policyholder, agent, product/plan reference, currency, sum assured, premium, premium frequency, term, risk commencement date, maturity date, status, and first-premium receipt reference. Product and plan references are intentionally stored as an immutable display-safe reference string at this stage; future issuance work can add structured snapshot metadata without changing the meaning of the existing field.

## Lifecycle state machine

Policy status is stored on the policy as a controlled catalog value. The `PolicyStatus` choices provide a safe baseline for the foundation and are intended to be aligned with the configurable OL Policy Status parameter catalog in later lifecycle prompts.

| Current status | Allowed next state in the foundation contract | Business meaning |
| --- | --- | --- |
| `ACTIVE` | `LAPSED`, `PAID_UP`, `SURRENDER_PENDING`, `MATURED_PENDING_PAYMENT`, `CANCELLED`, `CLAIM_SETTLED`, `TERMINATED` | Contract is in force and may receive servicing actions subject to parameters |
| `LAPSED` | `ACTIVE`, `PAID_UP`, `SURRENDER_PENDING`, `CANCELLED`, `EXPIRED` | Premium obligations are overdue beyond the configured grace process |
| `PAID_UP` | `SURRENDER_PENDING`, `MATURED_PENDING_PAYMENT`, `CANCELLED`, `TERMINATED` | Future premiums are stopped while reduced benefits remain in force |
| `SURRENDER_PENDING` | `SURRENDERED`, `CANCELLED` | Surrender request is awaiting payment processing |
| `SURRENDERED` | none | Contract has been surrendered and is terminal |
| `MATURED_PENDING_PAYMENT` | `MATURED`, `CANCELLED` | Maturity value is due and payment is outstanding |
| `MATURED` | none | Contract has completed its term and maturity has been paid |
| `EXPIRED` | none | Contract reached a terminal expiry condition without an active payout path |
| `CANCELLED` | none | Contract was cancelled and is terminal |
| `CLAIM_SETTLED` | `TERMINATED` | An exhausting claim was settled; termination may be recorded separately |
| `TERMINATED` | none | Contract is closed for servicing |

The table is a domain contract rather than an authorization bypass. Every transition must be checked against the effective OL parameter configuration, the current policy status, financial conditions, and the caller’s action permission. All state changes must generate a `PolicyAuditLog` row with the prior status, new status, actor, reason, and source channel.

## Relationship with proposals

`Policy.proposal_ref` points to `apps.ol_proposals.OLProposal` with `PROTECT` deletion behavior. A proposal may therefore be traced to its issued policy, while deleting or removing a proposal cannot destroy an issued contract. The existing proposal model currently carries a compatibility `converted_policy` relation to the legacy `ordinary_life.OLPolicy`; the issuance prompt will add the deliberate bridge to the new policy aggregate without breaking existing proposal and quotation integrations.

The policy reference is not a replacement for the proposal’s commercial history. It is the servicing-side contract link. Issuance must preserve the proposal number, quotation version, first-premium commitment, and receipt reference in the policy snapshot or audit payload so an operator can follow the full origin chain.

## Relationship with commitments

Renewal commitments are owned conceptually by the policy after issuance. The current OL Commitments module already supports a `POLICY` source type and stores source references and snapshot fields. Prompt 2 will connect policy issuance to that seam, creating or triggering the first renewal commitment only after the policy has been created atomically and the first premium guard has passed. Commitment generation, lapse processing, and reinstatement remain separate services so the policy aggregate does not import operational payment logic prematurely.

## Endorsements

An endorsement is the controlled representation of a material post-issuance change. It records the type, effective date, description, status, reason, source channel, and before/after snapshots. The presence of a separate endorsement table is intentional: policy servicing must not erase the prior contract position. The endorsement prompt will apply approved changes through a transaction and create a corresponding policy audit event.

## Integration map

| Integration | Foundation seam | Later responsibility |
| --- | --- | --- |
| OL Proposals | Protected `proposal_ref` foreign key | Atomic first-premium issuance and idempotency |
| Receipts | `first_premium_receipt_ref` traceability field | First-premium validation and payment evidence |
| OL Commitments | Policy-owned renewal concept and source reference | Renewal schedule generation, overdue processing, lapse, and reinstatement |
| Claims | Policy status values include claim-settlement outcomes | Coverage lookup, maturity claim, and exhausting-claim termination |
| Loans | Policy status and audit seams are ready | Loan balance, repayment, and withdrawal controls |
| Unified Documents | Policy number, status, dates, and snapshot are stable inputs | Policy contract and benefit schedule rendering |
| IAM and Audit | `ol_policies.*` permission codes and `PolicyAuditLog` | Action-level authorization and consistent audit reporting |

## Permissions

The policy module registers the following permission codes. Superusers are allowed by the common policy gate, while normal users must receive the specific code or an equivalent module entitlement through the IAM system.

| Permission code | Intended use |
| --- | --- |
| `ol_policies.view` | List and retrieve policies |
| `ol_policies.create` | Create or import a policy where an authorized workflow permits it |
| `ol_policies.service` | Service policy records and apply non-endorsement maintenance actions |
| `ol_policies.endorse` | Create and apply endorsements |
| `ol_policies.cancel` | Cancel a policy |
| `ol_policies.reinstate` | Reinstate a lapsed policy |
| `ol_policies.print` | Generate and download policy documents |
| `ol_policies.configure` | Configure policy behavior and parameter mappings |

## Audit requirements

`PolicyAuditLog` is append-only by application convention and read-only in Django admin. A row contains the policy, event type, before and after status, before and after snapshots, actor, reason, source channel, correlation ID, and timestamps. The model is intentionally separate from generic request logging so policy history remains queryable even when request logs are rotated. Later prompts will add service-layer helpers and event/outbox integration so every material state transition produces the same audit shape.

## Assumptions recorded for implementation continuity

The canonical proposal model is `apps.ol_proposals.OLProposal`, while the repository still contains a legacy `ordinary_life.OLPolicy` model. The new app therefore uses a distinct database table and model label rather than replacing the legacy model in the foundation prompt. Future issuance work must preserve compatibility for existing proposal fields and can introduce an explicit bridge or migration after the new aggregate is proven.

Policyholder and proposal references are required for a new policy because an issued contract without an origin or insured party cannot be serviced safely. Agent is optional because direct business and legacy records may not have an intermediary. Currency is stored as an uppercase three-letter code, and the first-premium receipt is represented as a traceable external reference until the receipts domain exposes a stable cross-app foreign-key contract.

The foundation API is read-only. Creation, issuance, cancellation, reinstatement, financial transactions, and document generation are intentionally deferred to their numbered prompts. This prevents a partially implemented action endpoint from bypassing BR-03 or the parameterized lifecycle rules.
