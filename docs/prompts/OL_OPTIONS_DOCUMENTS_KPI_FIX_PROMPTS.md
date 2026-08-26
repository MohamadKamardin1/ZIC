# OL Options, Documents, and KPI Fix Prompt Series

> **Source note:** The current request included the complete text of Prompt 1 but did not include the text of Prompts 2–6. Prompt 1 is preserved verbatim below. The remaining entries are intentionally marked as not supplied so their requirements are not fabricated; they can be replaced with the exact source text when provided.

## [x] Prompt 1 — Resolve 404 for banks/intermediaries/employers options endpoints

```text
You are a senior Django API engineer. Fix missing options endpoints in the ZIC platform. The user pasted the FULL 6-prompt series at once.

META-INSTRUCTION (HIGHEST PRIORITY):

1. Before coding, create docs/prompts/OL_OPTIONS_DOCUMENTS_KPI_FIX_PROMPTS.md and save ALL 6 prompts EXACTLY as provided, each with a checkbox "[ ] Prompt N — title".
2. Commit and push that file immediately.
3. Execute ONLY Prompt 1 now; when green, tick its checkbox, commit, then proceed to Prompt 2. Never merge or skip prompts.

MANDATORY RULES:

- Do not ask blocking questions; document assumptions.
- All option endpoints must return standardized { value, label, meta } payloads, support ?q= search, pagination, and active filtering.
- Commit and push at the end of each prompt.

OBJECTIVE:
Resolve 404 errors for `/api/v1/ol-proposals/options/banks/`, `/intermediaries/`, `/employers/` and align them with the existing Partner model.

SCOPE:

1. Implement or fix URL routing to expose:
   - GET /api/v1/ol/options/banks/
   - GET /api/v1/ol/options/intermediaries/
   - GET /api/v1/ol/options/employers/
     (Keep legacy `/ol-proposals/options/...` as redirects for backward compatibility)
2. Backing query logic:
   - banks: Partner.objects.filter(partner_type__in=['BANK'], is_active=True)
   - intermediaries: Partner.objects.filter(partner_type__in=['INTERMEDIARY', 'AGENT'], is_active=True)
   - employers: Partner.objects.filter(partner_type__in=['EMPLOYER', 'CORPORATE'], is_active=True)
3. Response serialization:
   - value = partner.id (or partner_number if configured)
   - label = "{partner_number} — {legal_name}"
   - meta = { partner_type, location, active_status }
4. Add ?q= search on legal_name, partner_number, registration_number.
5. Enforce permission: `ol_parameters.view` or `partners.view`.
6. Add structured error OPTIONS_ENTITY_NOT_FOUND if entity not registered.
7. Frontend: update option hooks to call canonical `/api/v1/ol/options/{entity}/` paths.

TESTS:

- each endpoint returns 200 with labeled payload
- search filters correctly
- inactive partners excluded
- 404 replaced with teachable structured error for unknown entities
- backward-compat redirect works

GIT:

- commit: "fix(options): resolve 404 for banks/intermediaries/employers options endpoints"
- push; if blocked create feature/options-endpoints-fix and push; tick checkbox

FINAL OUTPUT: routes, serializers, query logic, frontend hook updates, tests, commit hash, pushed branch.
```

---

## [x] Prompt 2 — Repair PDF generation flow and secure download URL

```text
You are a senior Django document engineer. Continue the ZIC fix series. Execute ONLY Prompt 2 from the saved series file.

MANDATORY RULES:

- No blocking questions; document assumptions.
- Every print action must return a working preview blob or signed short-life download URL.
- Commit and push; tick checkbox.

OBJECTIVE:
Resolve "This document has no secure PDF download URL" and ensure PDF generation, storage, and preview work end-to-end.

SCOPE:

1. Fix document render view:
   - validate template exists and is active
   - build context from entity data
   - render HTML → PDF using WeasyPrint (or repo's configured engine)
   - save PDF to storage, create/update DocumentInstance with file_path, template_version, page_count, checksum
   - generate HMAC-signed short-life download URL (expiry 5 min, single-purpose, audited)
   - return { instance, preview_blob_base64_or_url, signed_download_url }
2. Handle engine/storage failures gracefully:
   - return structured error DOCUMENT_RENDER_FAILED with resolution steps
   - log correlation ID and stack trace internally
3. Frontend preview modal:
   - consume signed_download_url or fetch blob via authenticated client
   - render PDF in iframe/object
   - show ErrorCoach if URL missing or fetch fails
   - "Open in New Tab" uses signed URL; "Download" triggers authenticated fetch
4. Audit: log generation and download events with actor, source channel, template version.
5. Ensure all modules (quotation, proposal, commitment, receipt) use the same unified pipeline.

TESTS:

- PDF generates for seeded entities
- signed URL validates and expires correctly
- preview modal renders PDF
- missing template/storage error returns teachable shape
- audit rows created for generate/download

GIT:

- commit: "fix(documents): repair pdf generation flow and secure download url"
- push; tick checkbox

FINAL OUTPUT: engine pipeline, signed URL contract, frontend preview fix, tests, commit hash, pushed branch.
```

---

## [x] Prompt 3 — Resolve empty KPI cards on quotation list/detail pages

```text
You are a senior Django + frontend engineer. Continue the ZIC fix series. Execute ONLY Prompt 3.

MANDATORY RULES:

- KPIs must reflect real-time aggregated data with correct filters and currency formatting.
- Commit and push; tick checkbox.

OBJECTIVE:
Resolve empty KPI cards on quotation list/detail pages.

SCOPE:

1. Backend KPI endpoint `/api/v1/ol/quotations/kpis/`:
   - compute: total_drafts, total_finalized, total_converted, total_expired, total_premium_sum, avg_days_to_finalize
   - respect date range, status, agent, branch filters
   - return structured payload with currency and timestamp
2. Frontend KPI component:
   - bind to KPI hook
   - map fields correctly to cards
   - handle loading/empty/error states
   - format currency and numbers per locale
3. Ensure KPI auto-refreshes on list filter change.
4. Add unit tests for aggregation math and frontend rendering.

TESTS:

- KPI payload matches expected schema
- frontend cards display correct numbers and formatting
- filter changes update KPIs
- empty state handles zero counts gracefully

GIT:

- commit: "fix(quotations): repair kpi cards aggregation and frontend binding"
- push; tick checkbox

FINAL OUTPUT: backend aggregation, frontend binding, tests, commit hash, pushed branch.
```

---

## [x] Prompt 4 — Align payment frequency validation with product configuration

```text
You are a senior Django product configuration engineer. Continue the ZIC fix series. Execute ONLY Prompt 4.

MANDATORY RULES:

- Validation must accept exact product-configured frequencies; no hardcoded fallbacks.
- Commit and push; tick checkbox.

OBJECTIVE:
Resolve `premiumFrequency` validation error: "value you entered is 'QUARTERLY'. Choose one of the listed frequencies."

SCOPE:

1. Ensure `OLProduct.premium_frequencies` stores standardized uppercase codes: `ANNUALLY`, `SEMI_ANNUALLY`, `QUARTERLY`, `MONTHLY`, `SINGLE`.
2. Fix product setup serializer to validate and normalize frequencies on save.
3. Fix quotation plan config serializer validation:
   - accept only frequencies present in product's `premium_frequencies`
   - case-insensitive match but store normalized uppercase
   - return structured error PLAN_CONFIG_INVALID_FREQUENCY listing allowed values
4. Frontend wizard:
   - dropdown options sourced directly from product's `premium_frequencies` array
   - disable selection if product has no frequencies configured
   - show inline validation matching backend error shape
5. Seed at least one product with multiple frequencies configured.

TESTS:

- product save normalizes frequencies
- quotation plan config rejects invalid frequency with teachable error
- dropdown shows only configured frequencies
- seeded product validates successfully

GIT:

- commit: "fix(products): align payment frequency validation with product configuration"
- push; tick checkbox

FINAL OUTPUT: model/serializer fixes, frontend dropdown binding, validation rules, tests, commit hash, pushed branch.
```

---

## [ ] Prompt 5 — Not supplied in the current request

The exact Prompt 5 text was not included in the current request. It is intentionally not reconstructed.

---

## [ ] Prompt 6 — Not supplied in the current request

The exact Prompt 6 text was not included in the current request. It is intentionally not reconstructed.
