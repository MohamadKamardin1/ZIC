# OL Proposals — Design Document

Status: **Foundation (Prompt 1 of 12)**
Module: Ordinary Life > OL Proposals
Canonical parameter source: `apps.ol_parameters` (OL Policy Setup / OL Proposal Status catalog)
Companion prompts: `docs/prompts/OL_PROPOSALS_BACKEND_PROMPTS.md`

---

## 1. Purpose and Scope

The Ordinary Life Proposals module owns the **proposal lifecycle** between an approved quotation and an issued policy:

1. **Quotation conversion** — a finalized, partner-verified quotation converts into a proposal (`BR-01`).
2. **Enrichment** — the operator confirms/carries policyholder, life assured, plans, installments, funds, riders, benefits, and required documents into the proposal.
3. **Payment-ready** — once enrichment and mandatory documents are complete, the proposal is marked `PAYMENT_READY`.
4. **First premium** — a first-premium commitment is generated; settlement posts against the proposal (commitments seam).
5. **Policy conversion** — after the first premium is posted and underwriting clears, the proposal converts into a policy (`BR-03`).

A proposal is not a policy, a ledger, or a commitment — it is the **ordered, audited handoff** that assembles everything the policy issuance step needs.

### 1.1 Traceability and assumptions

| Spec / rule | Where satisfied | Notes |
| --- | --- | --- |
| SRS §2.3.1 (proposals, commitments, policies flows) | Lifecycle states + integration seams below. | |
| BR-01 (partner-verified finalized quotation converts) | Enforced at conversion by `ol_quotations`; the proposal is created with partner snapshot copied and re-verified here. | Existing `quotation_service.convert_to_proposal` is the seam. |
| BR-03 (proposal → policy gate) | `PROPOSAL_NOT_PAYMENT_READY` / `PROPOSAL_FIRST_PREMIUM_NOT_POSTED` guards before conversion. | Documented assumption (A1). |
| Assumption A1 | A policy converts only when `payment_ready=True`, first premium posted to commitments, and underwriting completed. | `convert` action blocks otherwise. |
| Assumption A2 | Legacy handoff status `DRAFT` is retained in the OL Proposal Status catalog so quotation conversion keeps working; the domain primary states are the seeded workflow statuses. | Saved in `docs/OL_PROPOSALS_DESIGN.md` assumptions register. |
| Assumption A3 | `underwriting_status` mirrors the OL underwriting hook (`MEDICAL_REQUIRED`, `UNDER_REVIEW`, `CLEARED`, `DECLINED` subset) and is validated by the underwriting hook milestone. | Parameterized in the catalog when the U/W seat lands. |

---

## 2. Status State Machine (parameterized)

Statuses are **not hardcoded**: they are read from `ol_parameters.OLProposalStatus` (code, name, `display_order`, `is_terminal`, `applies_to="PROPOSAL"`, allowed-transition metadata, active/effective dates). Seeded catalog:

| Code | Meaning | Terminal | Typical next |
| --- | --- | --- | --- |
| `DRAFT` (legacy handoff) | Created from quotation | No | `ENRICHMENT` |
| `ENRICHMENT` | Operator confirmation of carried data + documents | No | `ENRICHMENT`, `PENDING_UNDERWRITING`, `CANCELLED` |
| `PENDING_UNDERWRITING` | Underwriting review (may raise `MedicalRequirementRaised`) | No | `PAYMENT_READY`, `CANCELLED` |
| `PAYMENT_READY` | Enrichment + mandatory documents complete | No | `AWAITING_FIRST_PREMIUM`, `ENRICHMENT`, `CANCELLED` |
| `AWAITING_FIRST_PREMIUM` | First-premium commitment created, awaiting settlement | No | `CONVERTED`, `EXPIRED`, `CANCELLED` |
| `CONVERTED` | Policy issued | Yes | — |
| `CANCELLED` | Closed by operator | Yes | — |
| `EXPIRED` | `expiry_date` passed un-converted | Yes | — |

**Rules applied by the module**:

1. Default/initial status = first active `PROPOSAL` status by `display_order`, `code` (seeded `DRAFT`).
2. Every persisted status is validated against the active catalog at `clean()` time; an unknown status is rejected.
3. Terminal statuses (from the catalog) cannot transition further — enforced by the shared transition guard.
4. Allowed transitions are read from the catalog's `allowed_transitions` JSON when present; otherwise the transition guard applies intrinsic rules (below) and returns `PROPOSAL_INVALID_TRANSITION` listing the allowed next states in `resolution_steps`.

Intrinsic transition guards (Prompt 3 will formalize):

- `enrich` — only from `DRAFT`/`ENRICHMENT`.
- `submit_underwriting` — only from `ENRICHMENT` (or `PENDING_UNDERWRITING` after a medical requirement is raised).
- `mark_payment_ready` — only from `ENRICHMENT`/`PENDING_UNDERWRITING` **and** mandatory documents complete; sets `payment_ready=True`.
- `await first premium` — on commitment generation the proposal moves to `AWAITING_FIRST_PREMIUM`.
- `convert` — only from `AWAITING_FIRST_PREMIUM` **and** first premium posted to commitments **and** underwriting cleared.
- `cancel` — from any non-terminal state.
- `expire` — automatic when `expiry_date < today` and non-terminal.

---

## 3. Event Map (outbox)

Every material change publishes a durable `DomainEvent` (`apps.common.models`) entry:

| Event | Emitted when |
| --- | --- |
| `ProposalCreated` | Proposal created from a quotation. |
| `ProposalEnriched` | Enrichment data saved / documents uploaded. |
| `ProposalPaymentReady` | `mark_payment_ready` action succeeds. |
| `ProposalConverted` | Policy conversion succeeds. |
| `ProposalCancelled` | Proposal cancelled with reason. |
| `ProposalExpired` | Expiry sweep marks the proposal expired. |
| `MedicalRequirementRaised` | Underwriting hook flags a required medical requirement. |

Payload convention: `proposal_number`, `proposal_id`, `actor_id`, `from_status`, `to_status`, `reason`, `source_channel`, `metadata`.

---

## 4. Integration Map

| Boundary | Seam |
| --- | --- |
| **Quotations** (`ol_quotations`) | `convert_to_proposal` creates the proposal (existing); proposal carries `OLProposalPlanConfig/Member/Installment/Fund/Rider/Benefit` rows from the quotation snapshot. |
| **Commitments** (`ol_commitments`) | First-premium generation consumes `PAYMENT_READY`/`AWAITING_FIRST_PREMIUM` proposals; `record_payment` posting clears the first-premium gate. Receipts post via `receipt_reference`. |
| **Receipts seam** (`apps.front_office`) | Allocations reference receipts; the proposal reads first-premium-settled state from commitments, not from FO directly. |
| **Policies** (stub) | `converted_policy` reference on `OLProposal`; prompt-series continues policy issuance. |
| **Underwriting hook** | `underwriting_status` + `medical_required` + `OLProposalHealthAnswer` feed the U/W seat; raises `MedicalRequirementRaised`. |
| **Documents** | `OLProposalDocument` (type, mandatory, status, uploaded_by). |
| **Portal** | Read-only scoped proposal views by linked partner (later prompt). |
| **Reports** | Proposal dataset + status funnel (later prompt). |
| **OL Parameters** | `OLProposalStatus` catalog + numbering (`OL_PROPOSAL`). |
| **Governance** | `AuditService` writers + outbox `DomainEvent`. |

---

## 5. Data Model (plants)

- **OLProposal** — extends the existing handoff aggregate: `proposal_number` (unique), `quotation` + `quotation_version`, `status` (catalog-validated), `partner` (policyholder) + snapshot, `agent_partner`, `employer_partner`, `currency`, `expiry_date`, `payment_ready` + `payment_ready_at`, `underwriting_status`, `medical_required`, `converted_policy`, `reason_code/text`, `source_channel`, audit fields; keeps legacy snapshots (`prospect_snapshot`, `plans_snapshot`, `financial_summary_snapshot`) for compatibility.
- **Carried-from-quotation parents**: `OLProposalPlanConfig`, `OLProposalMember`, `OLProposalInstallmentConfig` (+ `OLProposalInstallmentRateRow`), `OLProposalFundAllocation`, `OLProposalRider`, `OLProposalBenefit`.
- **OLProposalBeneficiary** — person name, identity type/number, `OLBeneficialType` parameter reference, `share_percent`, `is_primary`, minor + guardian fields.
- **OLProposalDocument** — document type, file reference, mandatory flag, status (`REQUESTED|UPLOADED|VERIFIED|REJECTED`), uploaded_by.
- **OLProposalHealthAnswer** — questionnaire item + health question references, answer snapshot, score, `triggers_medical`.

All models: UUID pk, `created_at/updated_at`, `created_by/updated_by`, `source_channel`, audit receivers.

---

## 6. Permissions

`ol_proposals.view | create | enrich | upload_documents | mark_payment_ready | convert | cancel | print`.
Registered as `users.UserPermission` rows (module `ol_proposals`), a `PermissionGroup`, and default role groups (Viewer / Handler / Administrator) via idempotent seed command. Action-to-code mapping + `HasOLProposalPermission` for DRF.

---

## 7. Structured Error Codes (Prompt 1 slice)

| Code | Meaning |
| --- | --- |
| `PROPOSAL_PARTNER_NOT_VERIFIED` | Partner (policyholder) not partner-verified. |
| `PROPOSAL_BENEFICIARY_SHARES_INVALID` | Beneficiary shares do not total 100% (or exceed). |
| `PROPOSAL_MANDATORY_DOCUMENTS_MISSING` | Required documents not uploaded. |
| `PROPOSAL_UNDERWRITING_PENDING` | Underwriting not cleared. |
| `PROPOSAL_NOT_PAYMENT_READY` | Proposal not flagged payment-ready. |
| `PROPOSAL_FIRST_PREMIUM_NOT_POSTED` | First premium not settled via commitments. |
| `PROPOSAL_EXPIRED` | Proposal past expiry. |
| `PROPOSAL_ALREADY_CONVERTED` | Already converted. |
| `PROPOSAL_INVALID_TRANSITION` | Action not allowed from current state (lists allowed next states). |
| `PARAMETER_MISSING` | Catalog/code not configured (reused from commitments registry). |

All rendered through the shared structured error handler (`apps.core.exceptions`) with `error_code`, `message`, `resolution_steps`, `field_errors`, `doc_ref`.

---

## 8. API Skeleton (Prompt 1)

- `GET /api/v1/ol-proposals/` — paginated proposal list (display names, never UUIDs).
- `GET /api/v1/ol-proposals/{id}/` — proposal detail with carried children.
Both gated by `ol_proposals.view`; the full action surface (Prompt 3+) extends this module.