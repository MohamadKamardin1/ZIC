# OL Proposals — API Reference

Base URL: `/api/v1`. Authentication: OAuth2 bearer token (session auth in development).
All responses use the shared envelope `{ "data": …, "meta" }`; errors use the structured
shape below. Display fields are human-readable names — raw UUIDs appear only as `id`s.

```
error: {
  "error_code": "PROPOSAL_NOT_PAYMENT_READY",
  "message": "…",
  "resolution_steps": ["…"],
  "field_errors": { … } | {},
  "details": { … } | omitted,
  "doc_ref": "docs/OL_PROPOSALS_USER_GUIDE.md"
}
```

Permissions: every endpoint requires the listed `ol_proposals.*` code via group RBAC
(superusers bypass). Portal endpoints scope to the caller's linked partner and are read-only.

---

## Creation

### POST `/api/v1/ol/proposals/from-quotation/{quotation_id}/`
Convert a finalized quotation into a proposal. Idempotent: converting twice returns the
existing proposal with `"created": false`.

- Permission: `ol_proposals.create` (and the view's `MustCreateProposalPermission`)
- Body: none (quotation must be `FINALIZED` and partner-verified)
- Errors: `PROPOSAL_PARTNER_NOT_VERIFIED`, `PROPOSAL_ERROR` (quotation not finalized)
- Response: proposal detail payload + `"created"` boolean; audits `CONVERT_QUOTATION_TO_PROPOSAL`

## Listing, Detail, Dashboard

| Endpoint | Method | Permission | Notes |
| --- | --- | --- | --- |
| `/api/v1/ol-proposals/proposals/` | GET | `view` | Paginated list; filters: `status`, `search`, `partner`; ordering |
| `/api/v1/ol-proposals/proposals/{id}/` | GET | `view` | Detail incl. carried children, beneficiaries, documents, commitments |
| `/api/v1/ol-proposals/proposals/kpis/` | GET | `view` | Operations KPI counts by status |
| `/api/v1/ol-proposals/proposals/dashboard-kpis/` | GET | `view` | Dashboard tile dataset |
| `/api/v1/ol-proposals/proposals/reporting/dataset/` | GET | `export` | Reporting rows |
| `/api/v1/ol-proposals/proposals/export/` | GET | `export` | CSV export of the list |

## Actions

| Endpoint | Method | Permission | Body | Success effect / errors |
| --- | --- | --- | --- | --- |
| `…/proposals/{id}/enrich/` | PATCH | `enrich` | `{"section": "declarations"\|"bank_details", …fields}` | Saves section, audited. Unknown section → `VALIDATION_ERROR` |
| `…/proposals/{id}/beneficiaries/` | GET, POST | `view` / `enrich` | beneficiary fields | POST adds one; shares must keep 100% total |
| `…/proposals/{id}/beneficiaries/{bid}/` | PATCH, DELETE | `enrich` | partial fields | Update/remove one beneficiary |
| `…/proposals/{id}/documents/` | POST | `upload_documents` | `document_type`, `file_reference` | Uploads + audits; catalog-driven requirements |
| `…/proposals/{id}/health-questions/` | GET | `enrich` | — | Applicable questionnaire items for the plan |
| `…/proposals/{id}/health-answers/` | POST | `enrich` | `[{"health_question": id, "answer": {"value": …}}]` | Records answers; triggering items move to `PENDING_UNDERWRITING`. No questionnaire → `PARAMETER_MISSING`; unknown ids → `VALIDATION_ERROR` |
| `…/proposals/{id}/underwriting-decision/` | POST | `enrich` | `{"decision": "clear"\|"load"\|"decline", "reason": "…"}` | Clear/load → back to `ENRICHMENT` (`CLEARED`, loading recorded); decline sets `DECLINED`. Decline without reason → `VALIDATION_ERROR` |
| `…/proposals/{id}/payment-readiness/` | GET | `view` | — | Read-only checklist: per-item pass/fail, error code, deep link |
| `…/proposals/{id}/mark-payment-ready/` | POST | `mark_payment_ready` | — | Runs checklist; on success → `AWAITING_FIRST_PREMIUM` + live first-premium commitment. Failures → 409 with `details.checklist` |
| `…/proposals/{id}/first-premium/` | GET | `view` | — | Commitment status, paid/outstanding amounts |
| `…/proposals/{id}/convert/` | POST | `convert` | — | Issues policy stub (BR-03: first premium must be settled) → `CONVERTED`. Idempotent |
| `…/proposals/{id}/cancel/` | POST | `cancel` | `{"reason": "…"}` | Terminal `CANCELLED`; empty reason → `VALIDATION_ERROR` |
| `…/proposals/{id}/reactivate/` | POST | `enrich` (reactivate maps to enrich) | — | Reopens non-terminal stalled proposals to `ENRICHMENT` |
| `…/proposals/{id}/print/` | GET | `print` | `?format=pdf` | Proposal pack PDF |
| `…/proposals/{id}/completeness/` | GET | `view` | — | Section/document completeness summary |
| `…/proposals/options/{kind}/` | GET | `view` | — | Dropdown options (`bank`, `identity_type`, …) |

## Portal (partner-scoped, read-only)

| Endpoint | Method | Notes |
| --- | --- | --- |
| `/api/v1/ol-proposals/proposals/portal/` | GET | Own proposals only; cross-partner IDs return generic 404 `PROPOSAL_NOT_FOUND` |
| `/api/v1/ol-proposals/proposals/portal/{id}/` | GET | Detail without staff-only fields (no `allowed_actions`) |

## Lifecycle transitions

Direct transition endpoint is service-backed; allowed targets come from the status catalog:

| From \ To | ENRICHMENT | PENDING_UNDERWRITING | PAYMENT_READY | AWAITING_FIRST_PREMIUM | CONVERTED | CANCELLED | EXPIRED |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ENRICHMENT | ✓ | ✓ | ✓ | — | — | ✓ | — |
| PENDING_UNDERWRITING | ✓ | — | ✓ | — | — | ✓ | — |
| PAYMENT_READY | ✓ | — | — | ✓ | — | ✓ | — |
| AWAITING_FIRST_PREMIUM | — | — | — | — | ✓ | ✓ | ✓ |

Illegal moves return `PROPOSAL_INVALID_TRANSITION` (422) with `resolution_steps` listing
allowed states.

## Batch operations

- `python manage.py expire_proposals` — expires past-expiry proposals and queues
  expiring-soon notifications (7-day window). System-audited, source channel `BATCH`.
  Exposed to operators through the lifecycle API as well.

## Webhook-style events (DomainEvent outbox)

Emitted for downstream consumers: `ProposalConverted`, payment-ready, commitment-generated,
medical-required, expiring-soon, and print events, all keyed on aggregate
`OLProposal:{id}`.
