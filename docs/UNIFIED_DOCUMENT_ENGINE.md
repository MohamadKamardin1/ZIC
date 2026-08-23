# Unified Documents and PDF Engine

## Architecture

The `apps.documents` Django application is the platform-level owner of generated document output. A `DocumentTypeRegistry` maps each document type to its source app/model, permission code, context builder, template code, layout path, title, and variables schema. Adding a proposal, commitment, policy, or claims document requires registering a context builder and template definition; it does not require another PDF renderer or another storage/download implementation.

`DocumentEngine.render()` resolves the registered source transaction, enforces source-module permission and partner scope, resolves the active versioned `DocumentTemplate`, resolves company branding, builds the document context, renders the shared branded HTML, converts it to PDF with WeasyPrint, counts pages with pypdf, stores HTML and PDF through Django's `default_storage`, calculates a SHA-256 checksum, and creates a new `DocumentInstance`. Re-rendering never overwrites an instance, so generated-document history is retained.

The existing Ordinary Life quotation service is now an adapter. It retains its legacy `OLQuotationDocument` metadata and URLs for compatibility, while delegating HTML/PDF generation and storage to `DocumentEngine`. The unified instance identifier is retained in the legacy record metadata as `unified_document_instance_id`.

## Models and provenance

`DocumentTemplate` stores the template code, human name, document type, version, Django layout path, variables schema, branding configuration reference, active flag, and approval attribution. Template code plus version is unique.

`DocumentInstance` stores the document type, source app label, source model, source object identifier, selected template and template version, private PDF and HTML storage references, generating user and timestamp, correlation identifier, page count, checksum, MIME type, status, and render metadata. The source transaction and exact template version can therefore be reconstructed for every generated artifact.

## Branding

`CompanyBranding.resolve()` reads typed values through `ConfigurationService` using the template's `branding_config_reference`. The default reference is `COMPANY_BRANDING`. Supported values are `COMPANY_NAME`, `ADDRESS`, `PHONE`, `EMAIL`, `REGISTRATION_NUMBER`, `FOOTER_LEGAL_TEXT`, `ACCENT_COLORS`, and the FILE-typed `LOGO_FILE`. Missing values use Zanzibar Insurance Corporation defaults; no module owns a second branding configuration.

## Rendering design

The shared `documents/base_print.html` provides the single print CSS system: logo-left/company-right header, branded title band, metadata grid, branded table headers, totals rows, signature block, legal footer, generation timestamp, template version, and `Page X of Y` counters. Registered layouts extend the base template and provide only document-specific business sections.

WeasyPrint is the HTML-to-PDF renderer because the repository already uses it and it preserves CSS print layout. pypdf reads the generated PDF to persist a page count. Django's configured storage abstraction stores both artifacts; API responses never expose storage paths.

## APIs

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/v1/documents/render/{document_type}/{object_id}/` | Render a registered source transaction and return document metadata, authenticated preview URL, and short-lived signed PDF URL. |
| `GET` | `/api/v1/documents/instances/?source_type=&object_id=` | List source-filtered generated history with template and display names. |
| `GET` | `/api/v1/documents/instances/{id}/preview/` | Authenticated HTML preview stream. |
| `GET` | `/api/v1/documents/instances/{id}/download/` | Bearer-protected PDF stream or valid signed-ticket stream. |

`OL_QUOTATION` is the first registered type and resolves to `ol_quotations.OLQuotation` with the `ol_quotations.print` permission. The registry is intentionally extensible for future modules.

## Access and audit

Render and authenticated preview/download requests use DRF authentication. Signed PDF tickets are supplementary: they are HMAC-backed timestamp signatures valid for five minutes, bound to the document instance, source type/object, issuing user, purpose, and PDF format. Every ticket use rechecks owner activity, source permission, and source scope. Requests without Bearer credentials or a valid ticket receive a teachable 401; permission or scope failures receive 403.

Generation, ticket issuance, bearer download, ticket download, and HTML preview are recorded through the central audit service with `source_channel=API`. The instance and source identifiers are retained in audit state without exposing storage URLs to clients.
