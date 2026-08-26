# Unified Document Engine Prompt 4 Guide

## Scope

Prompt 4 extends the shared document engine with the currently implemented **Proposal Summary** and **Commitment Statement** templates. The quotation template remains owned by the same engine and is not duplicated. Receipt, Policy Contract, Discharge Voucher, Commission Statement, Debit Note, and Premium Statement are registered as `TEMPLATE_PENDING`; they return HTTP 409 with `code: TEMPLATE_PENDING` until an approved template is activated.

## Backend contract

The render endpoint is `POST /api/v1/documents/render/<document_type>/<object_id>/`. It requires Bearer authentication and the document-specific permission. It returns a `DocumentInstance` payload with source type/object, template name/version, generated actor/date, page count, protected preview URL, and a five-minute signed download URL.

The instance history endpoint is `GET /api/v1/documents/instances/?source_type=<app_label.model>&object_id=<id>`. Canonical Prompt 4 source identifiers are `ol_quotations.olquotation`, `ol_proposals.olproposal`, and `ol_commitments.olcommitment`. The payload uses display-safe actor and source values; UUIDs are retained only as machine identifiers.

The protected download route is `GET /api/v1/documents/instances/<id>/download/`. Bearer authentication is the primary path. A valid `ticket` query parameter is supplementary, single-purpose, HMAC-signed, expires after five minutes, re-checks source access, and is audited. The frontend fetches PDF content through `fetchAuthenticatedDocument`; it navigates directly only to a server-issued signed ticket.

## Branding administration

The authoritative branding surface is `GET/POST /api/v1/documents/branding/`, linked in the frontend at `/system-parameters/documents/branding`. POST accepts multipart form data, including `logo_file`, company name, address, phone, email, registration number, legal footer text, and JSON `accent_colors`. Each successful update creates an immutable `BrandingConfiguration` version, retires the previous active version inside an atomic locked transaction, and writes `BRANDING_VERSION_RETIRED` and `BRANDING_VERSION_CREATED` audit actions.

Templates resolve the latest active version and record `branding_version` in `DocumentInstance.metadata`. If no versioned record exists, legacy System Parameter branding values remain supported. If an active version has no uploaded logo, the repository ZIC logo is used. Missing accent keys are merged with the default ZIC palette.

## Frontend behavior

Quotation detail, proposal selected-record drawers, and commitment detail expose a Documents surface backed by `DocumentInstancesPanel`. The panel lists template name/version, generated-by, generated-at, page count, and Preview, Download, and signed-ticket Open in new tab actions. Preview uses a blob URL in an in-app PDF modal and revokes the URL on replacement/unmount. Download uses the same authenticated transport. Render failures are routed through ErrorCoach; pending-template and branding errors link to the branding administration screen.

## Permission behavior

Quotation rendering uses the existing `ol_quotations.print` entitlement. Proposal rendering explicitly inherits the quotation print entitlement until the proposal module defines a dedicated print permission. Commitment rendering uses `has_ol_commitment_permission(actor, "view")`. Branding administration accepts `system_parameters.manage` or `documents.manage`; superusers bypass both checks.
