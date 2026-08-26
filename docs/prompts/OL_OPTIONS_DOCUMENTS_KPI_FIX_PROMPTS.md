# OL Options, Documents, and KPI Fix Prompt Series

> **Source note:** The current request included the complete text of Prompt 1 but did not include the text of Prompts 2–6. Prompt 1 is preserved verbatim below. The remaining entries are intentionally marked as not supplied so their requirements are not fabricated; they can be replaced with the exact source text when provided.

## [ ] Prompt 1 — Resolve 404 for banks/intermediaries/employers options endpoints

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

## [ ] Prompt 2 — Not supplied in the current request

The exact Prompt 2 text was not included in the current request. It is intentionally not reconstructed.

---

## [ ] Prompt 3 — Not supplied in the current request

The exact Prompt 3 text was not included in the current request. It is intentionally not reconstructed.

---

## [ ] Prompt 4 — Not supplied in the current request

The exact Prompt 4 text was not included in the current request. It is intentionally not reconstructed.

---

## [ ] Prompt 5 — Not supplied in the current request

The exact Prompt 5 text was not included in the current request. It is intentionally not reconstructed.

---

## [ ] Prompt 6 — Not supplied in the current request

The exact Prompt 6 text was not included in the current request. It is intentionally not reconstructed.
