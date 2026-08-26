# Prompt 1 Audit — Frontend Print Navigation and Authentication

## Scope

This audit searched the complete frontend source tree at `insurance-dashboard-ui/src/**` for raw print/download navigation and API URL usage, including `window.open`, `window.location`, `location.href`, `location.assign`, `location.replace`, anchor targets, iframe sources, `/print/`, `/download`, `pdf_url`, `html_url`, `file_reference`, and `download` attributes.

## Findings

| Area | Finding |
|---|---|
| Raw `window.open` | No occurrences found in the frontend source tree. |
| Raw `window.location` navigation | No occurrences found for print/download flows. The only ordinary navigation anchor found is the access-gate link back to `/`. |
| Raw `/api/` anchor or iframe navigation | No literal `/api/` URL is embedded in an anchor or iframe, but the detail page directly assigns backend-returned `pdf_url` to an anchor `href` and `html_url` to an iframe `src`, bypassing the authenticated client. |
| Raw print/download endpoint URL | No hardcoded raw print URL was found. Backend-returned document URLs are navigated directly by the browser. |
| Quotation print generation | `OLQuotationDetail.tsx` calls `request()` with `POST` to the quotation print endpoint and stores the returned document in the preview state. |
| Document preview/download UI | The detail page directly renders `iframe src={printDocument.html_url}` and `a href={printDocument.pdf_url} target="_blank"`. These browser navigations do not carry the bearer header and are the confirmed authenticated-document-flow gap. |
| Onboarding document links | The onboarding document panel opens a returned `document.file` URL in a new tab. This backend-supplied file URL is another document navigation that should use the centralized authenticated utility. |

## Authentication evidence

The quotation print generation handler currently uses `request()` from `src/lib/apiClient.ts`. That helper injects `Authorization: Bearer <access token>` when a token exists and attaches `X-Correlation-ID`, but it does **not** refresh an expired access token or retry a 401 response.

After generation, the quotation detail page assigns backend-returned `pdf_url` and `html_url` directly to browser navigation elements. Browser-created iframe and anchor requests cannot reuse the bearer header injected by `request()`, which confirms the expected bypass at the document open/download boundary. The separate legacy `apiFetchAuth()` helper in `src/lib/api.ts` does refresh/retry once on HTTP 401, but the quotation print handler and direct document URLs do not use it.

The incident’s unauthenticated GET is therefore explained by a direct browser navigation to a protected print/document URL, whether from the deployed older path or a backend-returned URL. Prompt 2 must eliminate this class of failure by routing generation, preview, and download through one authenticated blob utility with a single token-refresh retry.

## URL naming observation

The current quotation endpoint prefix is `\`/api/v1/ol-quotations/quotations/{id}/print/\`` for print generation. The source audit found no duplicate-prefix raw navigation. Prompt 4 will verify the final signed-download route after implementation.

## Prompt 1 acceptance

Prompt 1 is green: the full frontend source tree was audited, current quotation print authentication behavior was confirmed, and token-expiry handling was identified as missing from the active print request path. No implementation from Prompts 2–5 has been started in this checkpoint.
