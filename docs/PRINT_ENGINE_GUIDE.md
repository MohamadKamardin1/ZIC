# ZIC Unified Print Engine Guide

## Purpose and design principles

The ZIC platform uses one authenticated document engine for every implemented PDF rather than separate renderers in quotation, proposal, or commitment modules. A generated document remains linked to its source transaction, the approved template version, the generating actor, the correlation identifier, and the stored checksum. Re-rendering is intentionally additive: it creates a new `DocumentInstance` and preserves prior history.

The engine is designed around four controls. The registry decides which document types are available and which source model, template, variables, and permission apply. The context builder converts domain data into display-safe printable labels. The shared print layout provides consistent branding, page numbering, repeating table headers, signatures, and legal notes. The authenticated transport protects preview and download operations with Bearer access or a short-lived, single-purpose signed ticket.

## Architecture

| Layer | Responsibility | Implementation |
|---|---|---|
| Registry | Maps document type to source model, template, permission, context builder, and variable schema. | `DocumentTypeRegistry` in `backend/apps/documents/services/engine.py` |
| Source access | Resolves the source transaction and checks permission plus partner scope. | `DocumentEngine.resolve_source()` and `ensure_access()` |
| Context | Builds display-safe values and collapses optional sections when no rows exist. | `_quotation_context()`, `_proposal_context()`, `_commitment_context()` |
| Branding | Resolves the active versioned configuration, legacy System Parameters fallback, default palette, and repository logo fallback. | `CompanyBranding.resolve()` |
| Layout | Supplies common header, title band, watermark, CSS tables, signatures, and page footer. | `documents/base_print.html` |
| Rendering | Produces HTML, converts it to PDF, counts pages, calculates SHA-256, and stores both HTML preview and PDF. | WeasyPrint plus Django default storage |
| Provenance | Stores source type/object, template version, actor, time, correlation ID, page count, checksum, and branding version. | `DocumentInstance` |
| Transport | Uses authenticated preview/download URLs and supplementary signed-ticket URLs. | `/api/v1/documents/` and `documentClient.ts` |
| Audit | Records generation, preview, bearer download, ticket issue, and ticket download events. | Central `AuditService` / `AuditLog` |

The PDF renderer is **WeasyPrint**. It is invoked server-side with the repository base directory so the shared ZIC logo and template assets can be resolved. `pypdf` verifies the resulting page count in the render pipeline and is used by regression tests for text and resource inspection.

## Implemented document types

| Document type | Source identifier | Template code | Required printable areas |
|---|---|---|---|
| `OL_QUOTATION` | `ol_quotations.olquotation` | `OL_QUOTATION_UNIFIED` | Header/meta, prospect, plans, members, riders and benefits, funds, financial summary, projections, installment payouts, disclaimer, signatures, footer, and DRAFT watermark when applicable. |
| `PROPOSAL_SUMMARY` | `ol_proposals.olproposal` | `PROPOSAL_SUMMARY_UNIFIED` | Proposal and quotation references, prospect, proposed plans, underwriting/approval block, financial summary, terms, disclaimer, signatures, and footer. |
| `COMMITMENT_STATEMENT` | `ol_commitments.olcommitment` | `COMMITMENT_STATEMENT_UNIFIED` | Commitment details, policyholder/product/plan snapshots, payment summary, allocations when present, statement notes, signatures, and footer. |

The following future registry entries are deliberately visible as `TEMPLATE_PENDING`: `RECEIPT`, `POLICY_CONTRACT`, `DISCHARGE_VOUCHER`, `COMMISSION_STATEMENT`, `DEBIT_NOTE`, and `PREMIUM_STATEMENT`. A render attempt returns HTTP 409 with `code: TEMPLATE_PENDING` and directs the operator to System Parameters instead of creating an incomplete PDF.

## Template variable dictionary

All templates receive common variables in addition to their document-specific context.

| Common variable | Type | Meaning |
|---|---|---|
| `branding` | object | Active company name, address, phone, email, registration number, legal footer, logo data URI, palette, and branding version. |
| `document_title` | string | Title shown in the blue title band. |
| `template_version` | integer | Approved `DocumentTemplate.version` used for the render. |
| `generated_at` | datetime | Server generation timestamp. |
| `generated_by_name` | string | Human-readable actor name. |
| `document_type` | string | Registered document type. |
| `source_type` | string | Canonical source identifier. |
| `source_object_id` | string | Source key retained for provenance; never used as a display label. |

### Quotation context

| Variable | Type | Meaning |
|---|---|---|
| `quote` | object | Quote number, name, date, expiry, status watermark, currency, location, branch, validity, and terms reference. |
| `meta` | object | Quote date, expiry date, currency, agent name/code, location, and branch. |
| `prospect` | object | Human name, identity type/number, date of birth, age, gender, smoker status, location, and address. |
| `plans` | array | Selected plan code/name/description, plan type and badges, terms, frequency, basis, sums, maturity, bonus, feature indicators, and premium amounts. |
| `members` | array | Policyholder/dependent names, relation, date of birth, age, gender, coverage basis, and sum assured. |
| `riders` | array | Rider code/name, category, term, sum assured, waiting period, underwriting flag, basis, values, loading, discount, and premium. |
| `benefits` | array | Benefit code/name/type, basis, value, cap, loading, discount, sum assured, and premium. |
| `funds` | array | Fund code/name, fund type, risk profile, currency, valuation frequency, plan, allocation percentage, and amount. |
| `financial` | object | Sum assured, base/rider/benefit premiums, loadings, discounts, tax, installment charge, total premium, premium words, frequency rows, and maturity value. |
| `projections` | array | Policy year, premiums paid, bonuses, surrender value, and paid-up value. |
| `installments` | array | Sequence, due date, description, rate percentage, amount, and paid-up rate. |
| `agent` | object | Agent/intermediary human name and code. |
| `validity` | object | Validity days, expiry date, and terms reference. |

### Proposal Summary context

Proposal rendering reuses the quotation context where a linked quotation is available and overlays immutable proposal snapshots where needed.

| Variable | Type | Meaning |
|---|---|---|
| `proposal` | object | Proposal number, status, quotation number/version, creation timestamp, and creator name. |
| `quote`, `meta`, `prospect`, `plans`, `agent`, `financial`, `branding` | inherited objects | Display-safe linked quotation data and proposal snapshot fallbacks. |
| `underwriting` | object | Underwriting status and review note. |

### Commitment Statement context

| Variable | Type | Meaning |
|---|---|---|
| `commitment` | object | Commitment number, source type/reference, partner/product/plan snapshots, currency, frequency, installment position, dates, status, approval flag, and reason. |
| `meta` | object | Commitment number, source reference, due date, and currency. |
| `financial` | object | Premium amount, amount paid, amount waived, and outstanding balance. |
| `allocations` | array | Receipt reference, amount, payment mode, currency, exchange rate, allocation timestamp, allocator name, and reason. |
| `branding` | object | The active branding context described above. |

Context builders apply `_safe_document_text()` to source values. UUID objects and UUID-shaped strings become a safe fallback rather than appearing in a customer-facing PDF. Names come from snapshots or related model display values.

## Branding configuration

The authoritative administration surface is **System Parameters → Document Branding**, route `/system-parameters/documents/branding`. It uses the authenticated documents branding API and creates a new immutable version for every successful update. The previous active version is retired atomically before the new version becomes active. The API supports `multipart/form-data` for the optional `logo_file` and accepts company identity, legal footer, and accent-color fields.

| Operation | Endpoint | Result |
|---|---|---|
| Read effective branding and recent versions | `GET /api/v1/documents/branding/` | Active version, display fields, palette, logo metadata, and safe history. |
| Create a new version | `POST /api/v1/documents/branding/` | HTTP 201 with the new active version. Requires the system-parameter manage permission or superuser access. |
| Review history | Same GET response | Recent immutable versions with active/retired status and timestamps. |

The API records `BRANDING_VERSION_RETIRED` for the former active row and `BRANDING_VERSION_CREATED` for the new row through the central audit service. Templates record the selected branding version in `DocumentInstance.metadata.branding_version`. If the active version has no uploaded logo, the repository ZIC logo is used. Missing individual colors are merged with the default primary, accent, and table-header palette. Legacy System Parameter keys remain a fallback for environments that have not yet created a versioned branding record.

## API and ticket contract

| Operation | Endpoint | Authentication |
|---|---|---|
| Render a document | `POST /api/v1/documents/render/<document_type>/<object_id>/` | Bearer token; permission and partner scope checked server-side. |
| List generated instances | `GET /api/v1/documents/instances/?source_type=<app.model>&object_id=<id>` | Bearer token; display-safe metadata only. |
| Preview HTML | `GET /api/v1/documents/instances/<id>/preview/` | Bearer token. Use only through the authenticated client. |
| Download PDF | `GET /api/v1/documents/instances/<id>/download/` | Bearer token or valid signed ticket. |

A successful render returns the instance payload with `template_name`, `template_version`, `generated_by_display`, `generated_at`, `page_count`, `preview_url`, `signed_download_url`, and `download_url_expires_at`. A signed URL is valid for five minutes, contains a single-purpose HMAC ticket, is bound to the instance/source/user, and is revalidated at download time. Tampering, expiry, source mismatch, inactive ticket owner, or permission loss returns HTTP 403. A ticket is supplementary: protected preview and authenticated download continue to use Bearer access.

The browser rule is strict. `preview_url` and protected download URLs are fetched through `fetchAuthenticatedDocument()` or `openAuthenticatedDocument()`, converted to a blob URL, and revoked after use. `window.open()` is permitted only for a server-issued `signed_download_url`; a raw `/api/` URL must never be passed to a new tab, iframe, anchor, or location navigation.

## Audit and troubleshooting

Generation writes `DOCUMENT_GENERATED` with actor, source, template version, checksum, and correlation ID. Authenticated HTML preview writes `DOCUMENT_PREVIEWED`; Bearer PDF access writes `DOCUMENT_DOWNLOADED`; signed access writes `DOCUMENT_TICKET_ISSUED` and `DOCUMENT_TICKET_DOWNLOADED`. All events use the central `AuditLog` with `source_channel=API` for the shared API path.

| Error/code | Meaning | Operator resolution |
|---|---|---|
| 401 / `Authentication credentials were not provided` | The request reached a protected document endpoint without valid Bearer authentication. | Stay in the application, retry through the document panel, or sign in again. Do not paste a protected API URL into a new tab. |
| `TEMPLATE_PENDING` | The document type is registered but no approved layout is available. | Open System Parameters → Document Branding/template administration, complete the approved setup, then retry. |
| `PARAMETER_MISSING` or `BRANDING_NOT_CONFIGURED` | The render lacks a required configuration or branding value. | Open `/system-parameters/documents/branding`, save a valid branding version, and retry. |
| Invalid or expired ticket | The five-minute signed URL is stale, changed, or bound to another user/source. | Return to the document instance panel and generate a fresh ticket. |
| Document no longer available | Stored HTML/PDF reference is missing from storage. | Re-render from the source transaction; preserve the failed instance for audit review. |
| Permission denied | The actor lacks the document action or partner scope. | Request the relevant module permission or access the source transaction within the permitted partner scope. |

## Verification standard

A document is considered release-ready only when the verification matrix proves an HTTP success response, `application/pdf`, a non-trivial byte size, the expected page count, company branding, a logo image resource, source number and human names, key tables, signatures, `Template vN`, and `Page X of Y` for every page. Multi-page quotation tests additionally verify repeated table headers and later plan rows. Security tests cover unauthenticated render/download, permission denial, ticket tampering, ticket expiry, and actor binding. Browser tests cover preview, blob iframe use, authenticated download, signed-ticket navigation, proposal/commitment parity, and transparent one-time token refresh.

## References

[1]: ./UNIFIED_DOCUMENT_ENGINE.md "Unified Document Engine architecture"
[2]: ./DOCUMENTS_PROMPT4_GUIDE.md "Prompt 4 documents and branding guide"
[3]: ../insurance-dashboard-ui/docs/E2E.md "Frontend end-to-end testing guide"
[4]: ./OL_COMMITMENTS_USER_GUIDE.md "Ordinary Life commitments user guide"
