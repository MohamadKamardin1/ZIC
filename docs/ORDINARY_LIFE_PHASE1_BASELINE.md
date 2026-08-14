# Ordinary Life Phase 1 Baseline

**Status:** Phase 1 complete — specification and implementation baseline validated

**Repository:** `ZIC`

**Delivery branch:** `sultan`

**Scope:** Ordinary Life Insurance module

## 1. Purpose and authoritative sources

This document locks the Phase 1 baseline before further Ordinary Life implementation begins. It reconciles the authoritative ZIC system specification, the full walkthrough context retained for this project, the existing partial Django implementation, the existing Ordinary Life API client, and the repository’s established IAM, partner, audit, dashboard, and response-envelope conventions.

The authoritative functional baseline is the Ordinary Life flow described in the system specification: product and plan configuration; quotation; partner/customer verification; quotation versioning; proposal conversion; underwriting and medical requirements; approval; first-premium receipt; policy issuance; policy servicing; endorsements; premium statements; loans; withdrawals; surrender and paid-up behavior; maturity; renewals; lapses and reinstatement; claims; commissions; documents; notes; notifications; reporting hooks; partner scope; and complete audit history.

> The existing partial implementation is a useful compatibility starting point, not the final domain contract. Existing tables and APIs must be evolved deliberately rather than treated as production-complete.

## 2. Verified current implementation

The current backend contains configuration/reference models, a small operational core, basic CRUD viewsets, and one transactional lifecycle service. The latest uncommitted Ordinary Life work is intentionally isolated from prior delivered commits and currently consists of modified models, serializers, and views, the `0003` migration, and a new lifecycle service directory.

| Area | Current implementation | Phase 1 assessment |
|---|---|---|
| Configuration | Lookup values, system parameters, computation approaches, grace periods, policy statuses, renewal statuses, beneficiary types, surrender/paid-up setup, rates, health questions/questionnaires, notification schedules, and reinstatement windows. | Good configuration intent, but relationships, effective dating, validation, auditability, and seed data are incomplete. |
| Product | `OLProduct` with code, name, description, minimum/maximum age, term, and active flag. | Too thin for configured benefits, riders, rates, loadings, discounts, currencies, payment frequencies, funds, surrender, loan, withdrawal, and medical rules. |
| Customer | `OLClient` with personal identity, date of birth, gender, ID number, phone, and email. | Duplicates the canonical Partner domain and lacks partner compliance linkage, roles, address, nationality, employer, and insured-party modeling. |
| Quotation | One quotation per record with client, product, sum assured, premium amount, status, and number. | Missing quotation versions, payment frequency, currency, benefit/rider selections, financial inputs, projections, installments, calculation inputs, expiry, printable snapshot, and conversion controls. |
| Proposal | One-to-one quotation conversion with underwriting status, medical-required flag, status, and number. | Missing proposal-party details, employer/intermediary, declarations, versioned source snapshot, approval request linkage, payment-ready state, and complete underwriting case. |
| Commitment | Proposal-linked amount-paid and payment method with a simple status. | Not a receipt/deposit/allocation model and lacks branch, currency, payment mode, receipt number, reversals, allocations, and ledger/payment boundary. |
| Policy | Proposal-linked policy with policyholder/life-assured client links, agent, currency, sum assured, premium, dates, and status. | Missing product-version snapshot, policy parties, riders, benefits, schedule, premium plan, installments, grace/lapse/reinstatement state, endorsement history, servicing rules, and financial statement. |
| Servicing | Basic loan and withdrawal records exist. | Missing policy eligibility rules, cash value/build-up, schedules, approval, payment/requisition boundary, reversal, surrender/paid-up/reinstatement workflows, and endorsement history. |
| Claims | Basic policy claim with event date, cause, amount, and status. | Claims are a separate module in the overall sequence; Ordinary Life must expose claim linkage and configured benefit context without duplicating the future Claims domain. |
| Beneficiaries | Basic policy beneficiary model with type, name, relationship, identity, and percentage. | Needs total-allocation invariant, effective dating, verification state, change history, and policy-party integration. |
| History/audit | `OLWorkflowEvent` plus calls to the central `AuditService` from the lifecycle service. | Valuable starting point, but all material changes must use central audit context and immutable event semantics consistently. |
| APIs | Setup and core routers expose basic CRUD and several actions. | Missing beneficiary and workflow-event routes, partner scope, module permissions, serializer hardening, approval integration, pagination consistency, and complete lifecycle endpoints. |
| Frontend | Dedicated Ordinary Life screens are not yet implemented. A typed `src/lib/ol-api.ts` exists with setup/core helper scaffolding. | Frontend must be designed from the locked domain and workflow rather than mirroring the current thin CRUD surface. |
| Admin/tests | Ordinary Life admin is effectively empty and the app test module is a placeholder. | Admin, service tests, API tests, and end-to-end journeys are mandatory before module completion. |

## 3. Specification-derived workflow baseline

The implementation will follow this primary journey:

1. Configure an active product version, plan, benefits, riders, rates, underwriting rules, payment frequencies, grace/lapse rules, and servicing eligibility.
2. Select or create a compliant Partner/customer and identify the policyholder and life assured.
3. Produce a quotation from explicit inputs. Persist every material recalculation as a quotation version, retaining the input snapshot and calculated outputs.
4. Submit the quotation and verify partner compliance before conversion.
5. Convert the eligible quotation into a proposal, carrying the approved quote version and allowing proposal-only details such as employer, intermediary, declarations, and attachments.
6. Run underwriting and medical requirements. Apply configurable referral/approval limits and record decisions, reasons, medical outcomes, and timestamps.
7. Approve or decline the proposal through the generic approval boundary where a rule requires it.
8. Mark the approved proposal payment-ready and record the first premium through the future finance/payment boundary. A receipt or settled allocation covering the required first premium is mandatory before issuance.
9. Issue the policy from immutable approved proposal/product snapshots, then generate benefits, riders, premium schedule, installment schedule, policy parties, beneficiary allocation, and initial policy history.
10. Service the policy through endorsements, premium statements, payments, loans, withdrawals, surrender, paid-up conversion, claims linkage, maturity, renewals, lapse, and reinstatement, with each material change recorded as a new history event or transaction rather than an overwrite.

## 4. Locked bounded-context model

The following model families are locked for Phase 2 design. Names may receive normal Django implementation refinements, but the responsibilities and ownership boundaries should not be changed without a documented architecture decision.

### 4.1 Product and configuration family

| Model family | Responsibility |
|---|---|
| `OLProduct` | Stable product identity, code, business name, class, active lifecycle, and ownership metadata. |
| `OLProductVersion` | Effective-dated, immutable-at-use configuration snapshot for rates, terms, ages, currency, payment frequencies, underwriting, servicing, and calculation rules. |
| `OLPlan` | Optional product plan variant used where one product has distinct benefit/rate configurations. |
| `OLBenefit` and `OLProductBenefit` | Configured benefit definitions and product-version applicability, including fixed/ratio amount rules, limits, waiting periods, and claim type mapping. |
| `OLRider` and `OLProductRider` | Optional supplementary cover with eligibility, pricing, and effective-dated configuration. |
| `OLRateTable` / `OLRateBand` | Explicit premium or benefit rate inputs with effective dates and calculation approach. |
| Existing setup entities | Retained where useful, but normalized around product version and effective dates rather than being isolated global dropdown tables. |

### 4.2 Customer and application-party family

| Model family | Responsibility |
|---|---|
| `Partner` | Canonical external party. New Ordinary Life flows must use a compliant partner or explicitly record a completion requirement before conversion. |
| `OLPartyRole` or equivalent | Role-specific relationship for policyholder, life assured, payer, beneficiary, employer, and intermediary without duplicating identity records. |
| Compatibility `OLClient` | Retained temporarily for migration compatibility. It must gain an explicit partner linkage and must not become a second canonical customer master. |
| `OLApplication` / proposal party details | Proposal-level captured information that is not part of the canonical partner master, with source and verification state. |

### 4.3 Quotation and proposal family

| Model family | Responsibility |
|---|---|
| `OLQuotation` | Stable quote identity, owner/partner context, current status, expiry, and current version pointer. |
| `OLQuotationVersion` | Immutable input and calculation snapshot for each material quote revision, including product version, currency, frequency, term, sum assured, premium, loadings, discounts, benefits, riders, projections, and installment outputs. |
| `OLQuotationBenefit` / `OLQuotationRider` | Selected cover and calculated values per quote version. |
| `OLProposal` | Conversion record tied to a specific eligible quote version, proposal status, payment-ready state, and underwriting/approval references. |
| `OLProposalDocument`, `OLProposalNote`, and declarations | Proposal evidence, communication, and declared risk context. |

### 4.4 Underwriting and approval family

| Model family | Responsibility |
|---|---|
| `OLUnderwritingCase` | One coordinated underwriting case per proposal/version, including decision, risk class, referral reason, limits, reviewer, and timestamps. |
| `OLHealthDeclaration` / `OLHealthResponse` | Versioned responses to configured health questions. |
| `OLMedicalRequirement` / `OLMedicalResult` | Required medical evidence, assignment, due state, result, documents, and decision impact. |
| Approval integration | Use the generic approval engine once available. Ordinary Life supplies approval type, object reference, triggered values, and required limit context; it must not implement a second unrelated approval engine. |

### 4.5 Policy and servicing family

| Model family | Responsibility |
|---|---|
| `OLPolicy` | Issued contract identity, status, dates, currency, product-version snapshot, and current servicing state. |
| `OLPolicyParty` | Policyholder, life assured, payer, beneficiary, employer, and intermediary relationships. |
| `OLPolicyBenefit` / `OLPolicyRider` | Issued benefit and rider snapshots; later changes occur through endorsement. |
| `OLPremiumSchedule` / `OLPremiumInstallment` | Contractual premium due dates, amounts, paid/allocated state, grace state, and receipt links. |
| `OLPolicyTransaction` | Endorsement, payment, allocation, loan, withdrawal, surrender, paid-up, reinstatement, cancellation, maturity, and other material contract events. |
| `OLEndorsement` | Requested, approved, effective, and applied policy changes with before/after snapshots. |
| `OLPolicyRenewal` | Renewal notice, offer, decision, effective dates, and resulting policy state. |
| `OLPolicyStatusHistory` | Explicit status history for active, grace, lapsed, reinstatement-pending, surrendered, paid-up, matured, cancelled, and other configured states. |
| `OLLoan`, `OLWithdrawal`, surrender, paid-up, reinstatement records | Retained or evolved into policy transactions with eligibility, approvals, calculated values, and payment boundary references. |

### 4.6 Documents, history, and integration family

| Model family | Responsibility |
|---|---|
| `OLDocument` / document attachment boundary | Metadata, type, required/optional state, checksum, storage reference, uploader, verification, and lifecycle. Actual shared file storage should use the platform storage boundary once available. |
| `OLNote` | Internal and partner-visible notes with author, visibility, reason, and timestamps. |
| `OLWorkflowEvent` | Compatibility timeline record for Ordinary Life-readable history. It must remain consistent with the central immutable `AuditLog`; material state changes must not rely only on local events. |
| Payment/finance boundary | Ordinary Life creates payable/receivable intents and consumes receipt/allocation confirmations; it must not invent a second ledger. |
| Commission boundary | Ordinary Life emits commission-eligible transaction events with product, partner/intermediary, policy/proposal, amount, currency, and period context. |
| Claims boundary | Claims owns claim processing. Ordinary Life provides policy, insured-life, benefit, waiting-period, premium, and coverage context through stable service/API contracts. |
| Reporting boundary | Ordinary Life exposes report-category, policy, premium, underwriting, and transaction facts plus report execution hooks; it does not embed report rendering in the domain models. |

## 5. Locked state-machine boundaries

### Quotation

`DRAFT → SUBMITTED → EXPIRED` or `CONVERTED`. A draft may be revised by creating a new quotation version. A submitted quote cannot be silently overwritten. Conversion requires an active product version, positive valid calculation, partner compliance, and no expiry.

### Proposal

`PENDING → UNDERWRITING → REFERRED → APPROVED` or `DECLINED`, followed by `PAYMENT_PENDING → READY_FOR_ISSUANCE → CONVERTED_TO_POLICY` or `EXPIRED/CANCELLED` according to configured rules. Underwriting and approval decisions must be distinct facts even when the same user performs both actions.

### Policy

`ACTIVE → GRACE → LAPSED → REINSTATEMENT_PENDING → ACTIVE` plus terminal or contract states `SURRENDERED`, `PAID_UP`, `MATURED`, and `CANCELLED`. Exact transitions are rule-driven and must be enforced by services, not by direct serializer updates.

### Servicing requests

Endorsements, loans, withdrawals, surrender, paid-up conversion, reinstatement, and cancellations each have an explicit request/approval/application state and an applied policy transaction. A request must never mutate the policy before its eligibility and approval conditions are satisfied.

### Payment and claim boundaries

Ordinary Life may expose proposal/policy payment obligations and claim context, but payment posting, financial reversal, claim adjudication, and settlement remain integration boundaries until those modules are implemented. No direct cross-module table duplication should be introduced.

## 6. Current gap register

| Priority | Gap | Required resolution |
|---|---|---|
| P0 | `OLClient` duplicates the canonical Partner master. | Add explicit partner linkage and require compliant Partner verification for quote conversion; migrate progressively. |
| P0 | Quotation has no version history or calculation snapshot. | Add immutable quote versions and benefit/rider/input/output snapshots. |
| P0 | Direct CRUD permits bypassing lifecycle rules. | Make lifecycle-critical fields read-only in serializers and route transitions through services/actions. |
| P0 | Proposal underwriting and approval are collapsed into simple strings. | Add underwriting case/decision and generic approval integration boundaries. |
| P0 | Commitment is not a real receipt/allocation. | Replace or bridge with a finance/payment contract that can prove settled first premium. |
| P0 | Policy has no premium schedule, party snapshot, or transaction history. | Add issued snapshots, installments, policy transactions, and status history. |
| P1 | Product configuration is too thin. | Add effective-dated versions, benefits, riders, rates, payment frequencies, and rules. |
| P1 | Policy servicing is incomplete. | Implement endorsements, renewals, cancellations, surrender, paid-up, reinstatement, loans, withdrawals, and eligibility rules. |
| P1 | Documents, notes, and notifications are absent. | Add shared-boundary-compatible Ordinary Life records and event hooks. |
| P1 | Beneficiary allocation is not constrained. | Enforce total active percentage and effective-dated changes. |
| P1 | Audit is incomplete for direct model/API edits. | Integrate central audit receivers/service hooks and make workflow events immutable/read-only. |
| P1 | Partner scope and permissions are absent from Ordinary Life viewsets. | Apply existing permission catalog and partner-scope queryset rules. |
| P1 | Routes omit beneficiary and workflow-event viewsets. | Register only after permission/serializer hardening; expose read-only history. |
| P2 | Admin and tests are placeholders. | Add read-only audit/history admin, controlled setup admin, and layered tests. |
| P2 | Frontend has only API scaffolding. | Build list/detail/form/approval/servicing workspaces after API contracts are locked. |

## 7. Implementation assumptions locked for the next phases

1. The canonical customer and external-party identity is `partners.Partner`; Ordinary Life will not create a competing customer master as the long-term design.
2. Existing `OLClient` rows are preserved for compatibility and migrated through an explicit partner-link strategy rather than deleted or silently re-keyed.
3. All monetary amounts use `Decimal`, explicit currency, fixed quantization rules, and server-side calculations. The browser may preview calculations but cannot become the authoritative calculator.
4. Product and quotation configuration is effective-dated. Issued policies and converted proposals keep immutable snapshots of the configuration used at the time.
5. State changes are service-owned. Generic `ModelViewSet` CRUD may remain for safe reference data, but lifecycle-critical status fields are not directly writable.
6. The generic approval engine, future finance/payment module, future claims module, future commission module, shared documents/storage, and reporting engine are integration boundaries. Ordinary Life will expose stable contracts and hooks rather than duplicate them.
7. Existing response-envelope and authentication conventions remain mandatory. All Ordinary Life APIs must honor current IAM permissions, partner visibility, audit context, and API envelope behavior.
8. The initial implementation may use the existing local SQLite environment for development, but schema and constraints must remain production-safe for PostgreSQL migration.
9. The first implementation slice will prioritize individual ordinary-life quotation-to-policy and policy servicing foundations. Group-life and group-credit workflows remain separate modules and will consume shared abstractions only where appropriate.
10. The required delivery style is incremental: each coherent backend slice receives migrations, tests, documentation, a focused commit, and a push to `sultan`; Ordinary Life work must not be mixed with unrelated generated artifacts.

## 8. Phase 2 entry criteria

Phase 2 may begin when these facts are accepted as the design baseline:

- The bounded-context model families above are the target architecture.
- The quotation, proposal, underwriting, payment-ready, issuance, and policy servicing states are explicit and service-owned.
- `Partner` is the canonical external-party identity, with a compatibility migration path for `OLClient`.
- Payment, commissions, claims, documents, approvals, and reporting are integration boundaries rather than duplicated domain implementations.
- The P0 gap register is the first implementation priority.

Phase 2 will convert this baseline into a detailed data dictionary, transition matrix, invariant catalog, migration strategy, and concrete model changes before adding new services.
