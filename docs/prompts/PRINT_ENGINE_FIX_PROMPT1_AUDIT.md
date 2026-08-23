# Prompt 1 Audit — Frontend Print Navigation and Authentication

## Scope

This audit searched the complete frontend source tree at `insurance-dashboard-ui/src/**` for raw print/download navigation and API URL usage, including `window.open`, `window.location`, `location.href`, `location.assign`, `location.replace`, anchor targets, iframe sources, `/print/`, `/download`, `pdf_url`, `html_url`, `file_reference`, and `download` attributes.

## Findings

| Area | Finding |
|---|---|
| Raw `window.open` | No occurrences found in the frontend source tree. |
| Raw `window.location` navigation | No occurrences found for print/download flows. The only ordinary navigation anchor found is the access-gate link back to `/`. |
| Raw `/api/` anchor or iframe navigation | No occurrences found for print/download flows. |
| Raw print/download endpoint URL | No occurrences found in the current frontend source tree. |
| Quotation print generation | `OLQuotationDetail.tsx` calls `request()` with `POST` to the quotation print endpoint and stores the returned document in the preview state. |
| Document preview/download UI | The current detail page renders the preview from the returned document state; there is no raw API URL navigation in the audited source. |
| Onboarding document links | The onboarding document panel opens a returned `document.file` URL in a new tab. This is a document/file URL supplied by the backend, not a raw `/api/` URL; it must still be reviewed by the authenticated document-flow workstream. |

## Authentication evidence

The quotation print handler currently uses `request()` from `src/lib/apiClient.ts`. That helper injects `Authorization: Bearer <access token>` when a token exists and attaches `X-Correlation-ID`, but it does **not** refresh an expired access token or retry a 401 response.

The separate legacy `apiFetchAuth()` helper in `src/lib/api.ts` injects a bearer token and does refresh/retry once on HTTP 401. The current quotation print handler does not use that helper. Therefore, the verified Prompt 1 issue is not a currently visible raw `window.open('/api/...')` call in this branch; it is that quotation print uses an authenticated request helper with no token-expiry retry. The incident’s raw unauthenticated GET is consistent with an older/deployed print navigation path or a browser-opened API URL outside the current source tree, and the final fix must eliminate both possibilities by routing every document operation through one authenticated document utility.

## URL naming observation

The current quotation endpoint prefix is `\`/api/v1/ol-quotations/quotations/{id}/print/\`` for print generation. The source audit found no duplicate-prefix raw navigation. Prompt 4 will verify the final signed-download route after implementation.

## Prompt 1 acceptance

Prompt 1 is green: the full frontend source tree was audited, current quotation print authentication behavior was confirmed, and token-expiry handling was identified as missing from the active print request path. No implementation from Prompts 2–5 has been started in this checkpoint.
