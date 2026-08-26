# Prompt 4 Audit — Protected Print URL Contract

## Scope

This audit verifies the URL namespace used by Ordinary Life quotation print generation and protected document streaming after the signed-ticket implementation. It covers the canonical URL mount, the compatibility mount, named reverse routes, emitted document URLs, and duplicate-prefix regressions.

## Verified URL contract

| Purpose | Canonical path | Compatibility path |
|---|---|---|
| Generate quotation print | `/api/v1/ol-quotations/quotations/{quotation_id}/print/` | `/api/v1/ol/quotations/quotations/{quotation_id}/print/` |
| List quotation documents | `/api/v1/ol-quotations/quotations/{quotation_id}/documents/` | `/api/v1/ol/quotations/quotations/{quotation_id}/documents/` |
| Stream PDF | `/api/v1/ol-quotations/documents/{document_id}/download/` | `/api/v1/ol/quotations/documents/{document_id}/download/` |
| Stream HTML | `/api/v1/ol-quotations/documents/{document_id}/html/` | `/api/v1/ol/quotations/documents/{document_id}/html/` |

The backend keeps both quotation URL mounts for compatibility, but `PrintTicketService.protected_path()` emits only the canonical `/api/v1/ol-quotations/documents/{document_id}/...` path. The emitted document URL therefore contains exactly one `documents/{id}` segment and does not contain the historical incident-shaped duplicate `/quotations/quotations/` path.

## Evidence

The Django root URL configuration mounts `apps.ol_quotations.urls` under both `ol-quotations/` and `ol/quotations/`. The quotation URL configuration registers the document routes as `documents/<uuid:pk>/download/` and `documents/<uuid:pk>/html/`. The executable regression `OLPrintTicketAPITests.test_all_registered_print_routes_have_authentication_and_permission_classes` uses Django `reverse()` to assert the canonical named routes are exactly:

```text
/api/v1/ol-quotations/documents/11111111-1111-4111-8111-111111111111/download/
/api/v1/ol-quotations/documents/11111111-1111-4111-8111-111111111111/html/
```

The same test recursively audits registered routes whose path contains `print`, requiring a DRF view class with non-empty permission and authentication classes. The focused backend print/document suite passed with the signed ticket, format-binding, actor-binding, permission-recheck, and URL assertions enabled.

## Client contract

The authenticated frontend document client must treat `pdf_url`, `html_url`, `signed_download_url`, and `signed_preview_url` as fetch targets, not as raw browser navigation targets. It must fetch the content with the Bearer-aware client, retry one time after a 401 token refresh, validate the returned content type, and expose only a blob URL to an iframe or download action. A short-lived signed URL may be shared without an Authorization header, but a raw protected URL without a ticket remains Bearer-protected.

## Prompt 4 acceptance

Prompt 4 is green when the URL contract documentation is committed together with this audit note and the executable reverse-route regression remains green. Prompt 5 remains separate and is reserved for the complete repository regression and final delivery checkpoint.
