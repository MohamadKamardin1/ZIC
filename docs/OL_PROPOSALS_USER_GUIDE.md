# OL Proposals — User Guide

Audience: operations staff (underwriting, policy issuance, partner support) working Ordinary
Life proposals in the ZIC platform. Companion references: `OL_PROPOSALS_API.md` (endpoint
contract) and `OL_PROPOSALS_DESIGN.md` (architecture and as-built notes).

---

## 1. What an OL Proposal Is

An **OL Proposal** is the application record created when a finalized OL quotation is handed
over to the proposals module. It carries copies of the quoted plan configuration, tracks
enrichment (declarations, bank details, beneficiaries), mandatory documents, health
questionnaires and underwriting decisions, and ends in exactly one terminal state:
**CONVERTED** (policy issued), **CANCELLED**, or **EXPIRED**.

Proposals are never created by hand — they are converted from a quotation.

## 2. Lifecycle at a Glance

```
DRAFT ──► ENRICHMENT ──► PENDING_UNDERWRITING ──► PAYMENT_READY ──► AWAITING_FIRST_PREMIUM ──► CONVERTED
             │  ▲               │                        │                        │
             │  └───────────────┘ (back to enrichment)  │                        ├──► EXPIRED   (batch, past expiry)
             └──────────────────────────────────────────┴────────────────────────┴──► CANCELLED (reason required)
```

| Status | Meaning | Allowed next states |
| --- | --- | --- |
| `ENRICHMENT` | Operator confirms carried data; sections and documents completed here. | ENRICHMENT, PENDING_UNDERWRITING, PAYMENT_READY, CANCELLED |
| `PENDING_UNDERWRITING` | Health questionnaire triggered a medical requirement; underwriting reviews. | PAYMENT_READY, ENRICHMENT, CANCELLED |
| `PAYMENT_READY` | Enrichment + documents complete; first premium can be generated. | AWAITING_FIRST_PREMIUM, ENRICHMENT, CANCELLED |
| `AWAITING_FIRST_PREMIUM` | Live first-premium commitment exists; awaiting settlement. | CONVERTED, EXPIRED, CANCELLED |
| `CONVERTED` | Policy issued (stub row in legacy ordinary_life). Terminal. | — |
| `CANCELLED` | Closed by an operator with a mandatory reason. Terminal. | — |
| `EXPIRED` | Passed expiry date without conversion; set by nightly batch or manual action. Terminal. |

Rules enforced by the system:

- Every transition is audited (`PROPOSAL_TRANSITION`) and validated against the status
  catalog seeded by `seed_ol_proposal_statuses`. Illegal moves raise
  `PROPOSAL_INVALID_TRANSITION` with the allowed states listed.
- Cancelling requires a reason.
- Expiry can be applied manually or by `python manage.py expire_proposals` (idempotent,
  system-audited, source channel `BATCH`).
- A declined underwriting decision is final for that proposal path (terminal via decline →
  the proposal stays in enrichment with a `DECLINED` underwriting status and cannot proceed).

## 3. The Payment Readiness Checklist

Before a proposal can generate its first premium it must pass **all seven** checklist items.
The checklist is exposed read-only on `GET …/payment-readiness/` (each failed item includes
a deep link) and enforced on `POST …/mark-payment-ready/`.

| # | Checklist key | Passes when… | Where to fix it |
| --- | --- | --- | --- |
| 1 | `partner_verified` | The policyholder partner exists and the quotation was partner-verified. | Partners module → verify partner |
| 2 | `enrichment_complete` | Declarations and bank details sections are saved. | Proposal → Enrich screen (declarations, bank details) |
| 3 | `beneficiaries_valid` | At least one beneficiary and all shares total exactly 100%. | Proposal → Beneficiaries |
| 4 | `mandatory_documents_complete` | No document requirement from the seeded catalog is missing. | Proposal → Documents (deep link lists each missing type) |
| 5 | `underwriting_cleared_or_not_required` | Underwriting cleared, or no medical requirement was raised. | Proposal → Underwriting decision |
| 6 | `not_expired` | Proposal is not past its expiry date. | Re-quote / new proposal if expired |
| 7 | `quotation_version_current` | The proposal still matches the quotation's current version. | Re-convert if the quotation changed |

When `mark-payment-ready` succeeds the proposal lands in `AWAITING_FIRST_PREMIUM`, a live
first-premium commitment is linked automatically (source type `PROPOSAL`), and payment-ready /
commitment-generated notifications are queued. This whole step is idempotent — calling it
twice will not duplicate commitments or notifications.

## 4. Working a Proposal End to End

1. **Convert**: From the quotation workspace choose *Create Proposal*. The proposal opens in
   `ENRICHMENT` with the quoted plan snapshot attached.
2. **Enrich**: Save declarations (PEP/AML flags), bank details, and beneficiaries
   (shares must total 100%). Each section save is audited.
3. **Documents**: Upload each mandatory document (identity, signature, KYC form — catalog is
   parameter-driven per product/plan). Uploads are versioned and audited.
4. **Health questionnaire**: Answer the questions served by
   `GET …/health-questions/`. Any answer flagged as triggering sets *medical required* and
   moves the proposal to `PENDING_UNDERWRITING`.
5. **Underwriting decision** (if raised): *Clear*, *Load* (reason recorded, e.g. premium
   loading), or *Decline* (reason mandatory). Clear/load returns the proposal to `ENRICHMENT`.
6. **Payment readiness**: Review the checklist, resolve failures, then *Mark payment ready*.
   The first-premium commitment appears immediately.
7. **Collect first premium**: Receipts post allocations against the commitment. Once paid in
   full the commitment completes.
8. **Convert to policy**: With the premium settled, *Convert to policy*. The system creates
   the policy stub, links it back on the proposal (`converted_policy`), emits
   `ProposalConverted`, and closes the proposal as `CONVERTED`.
9. **Print**: Any time after conversion the proposal pack can be printed/downloaded as PDF
   (`…/print/`).

Portal users (partner-linked) get read-only views of their own proposals through
`/proposals/portal/` endpoints and can never convert, cancel, or enrich.

## 5. Notifications

The notification log (`OLProposalNotificationLog`) de-duplicates per
(proposal, event type, dispatch date, channel, recipient). Queued events include payment
ready, commitment generated, medical required, and expiring-soon (7-day window, sent by the
nightly batch). Outbox events land in `DomainEvent` for downstream consumers.

## 6. Error Resolution Table

All errors share one structured shape: `error_code`, `message`, `resolution_steps`,
`field_errors`, optional `details` (e.g. the failing checklist), and `doc_ref`.

| Code | HTTP | When you see it | How to resolve |
| --- | --- | --- | --- |
| `PROPOSAL_PARTNER_NOT_VERIFIED` | 422 | Converting a quotation whose partner is not verified. | Verify the partner in the Partners module, then convert again. |
| `PROPOSAL_BENEFICIARY_SHARES_INVALID` | 422 | Saving beneficiaries whose shares do not total exactly 100%. | Adjust shares so they total 100% (the error shows the current total). |
| `PROPOSAL_DUPLICATE_BENEFICIARY` | 409 | Two beneficiaries share the same identity number on one proposal. | Use different identity numbers or update the existing beneficiary. |
| `PROPOSAL_BENEFICIARY_GUARDIAN_REQUIRED` | 422 | A minor beneficiary has no guardian details. | Provide guardian name/identity/relationship for every minor. |
| `PROPOSAL_BENEFICIARY_NOT_FOUND` | 404 | Updating/deleting a beneficiary that does not exist on this proposal. | Refresh the beneficiary list; use an existing ID. |
| `PROPOSAL_MANDATORY_DOCUMENTS_MISSING` | 422 | Finalizing readiness while required documents are missing. | Upload each listed document type under Documents. |
| `PROPOSAL_DOCUMENT_NOT_FOUND` | 404 | Referencing a document not attached to this proposal. | Check the document ID belongs to this proposal. |
| `PROPOSAL_ENRICHMENT_INCOMPLETE` | 422 | Checklist item: declarations or bank details missing. | Complete both sections on the Enrich screen. |
| `PROPOSAL_UNDERWRITING_PENDING` | 409 | Converting while a medical requirement is unresolved. | Obtain the underwriting decision first. |
| `PROPOSAL_NOT_PAYMENT_READY` | 409 | Marking payment ready with failed checklist items (`details.checklist` lists them). | Resolve each failed item via its deep link, then retry. |
| `PROPOSAL_FIRST_PREMIUM_NOT_POSTED` | 422 | Converting before the first premium commitment is fully settled. | Collect the outstanding premium, then convert. |
| `PROPOSAL_EXPIRED` | 422 | Acting on a proposal past its expiry date. | Create a fresh proposal from a new quotation. |
| `PROPOSAL_ALREADY_CONVERTED` | 409 | Converting twice. | Nothing to do — return the existing policy reference. |
| `PROPOSAL_INVALID_TRANSITION` | 422 | Any state change not allowed from the current status (`details.allowed` lists valid targets). | Follow the allowed transitions for the current status. |
| `PROPOSAL_AUDIT_INCONSISTENT` | 500 | Terminal-state audit check found a state change without evidence. | Contact system administration; export the consistency report. |
| `PARAMETER_MISSING` | 422 | Required catalog data absent (e.g. no active health questionnaire for the product/plan). | Configure the referenced parameters module entry, then retry. |
| `VALIDATION_ERROR` | 422 | Payload problems (unknown section, empty cancel reason, bad decision value, unknown health question). | Fix the fields named in `field_errors`. |
| `PERMISSION_DENIED` | 403 | Your roles lack the action's permission code. | Request the matching role (see table below). |

## 7. Who Can Do What

Permissions follow the shared RBAC model (`module.action` codes, checked against user
groups). Codes: `view`, `create`, `enrich`, `upload_documents`, `mark_payment_ready`,
`convert`, `cancel`, `print`. Reactivate reuses `enrich`; list/detail/export reuse `view`.
Superusers bypass checks. Portal users are restricted to their own partner's proposals,
read-only.

Seeded demo roles are created by `python manage.py seed_ol_proposal_permissions`.

## 8. Demo Data

`python manage.py seed_ol_proposal_scenarios` seeds nine proposals covering every lifecycle
path (simple conversion, corporate employer-linked, medically triggered, loaded/cleared,
payment-ready with live commitment, partial payment, fully converted with policy stub,
cancelled, batch-expired) and writes structured failure-proof evidence to
`docs/evidence/ol_proposals_error_proofs.json`. It is idempotent and safe to re-run.
