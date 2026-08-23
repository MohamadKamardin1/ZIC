# Unified Document Engine Series

This file records the unified platform print-engine continuation requested after the original print-flow series. The original `PRINT_ENGINE_FIX_PROMPTS.md` remains unchanged as historical prompt history; its Prompt 2 records the earlier authenticated frontend document-client work.

## [x] Prompt 2 — Rebuild unified print and PDF engine with branding

- [x] Create shared `DocumentTemplate`, `DocumentInstance`, and system-parameter-backed company branding support.
- [x] Register document-type context builders and render branded HTML through the shared CSS layout.
- [x] Convert HTML to PDF with WeasyPrint, persist page count/checksum, and store through Django storage.
- [x] Expose authenticated render/preview, signed-download, and source-filtered instance-history APIs.
- [x] Preserve source transaction and template-version provenance, audit generation/download events, and create a new instance on every render.
- [x] Add regression tests for PDF output, page count, branding, permission denial, Bearer 401 behavior, signed access, labels, and history preservation.
