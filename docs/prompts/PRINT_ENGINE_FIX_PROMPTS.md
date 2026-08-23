# ZIC Print Engine Fix Prompts

This file preserves the five sequential workstreams from the supplied print-flow incident instructions. They must be executed in order; no later prompt may be merged or skipped before the preceding prompt is green.

## [x] Prompt 1 — Audit frontend print and download navigation

1. Search the entire frontend for direct navigation to API URLs used for printing/downloading: window.open, anchor href, location.href, iframe src pointing at /api/.
2. Confirm the print button bypasses the authenticated API client (this is the expected root cause). Also check token expiry handling on that call.

## [x] Prompt 2 — Implement the authenticated document client flow

3. Fix by implementing an authenticated document flow:
   - frontend utility openAuthenticatedDocument(url): fetch via API client with Bearer token, expect blob, validate content-type, create object URL, open preview modal or trigger download
   - replace ALL print/download call sites (quotations, proposals, commitments, documents lists) with this utility
   - on 401: auto token-refresh retry once; if still failing show ErrorCoach "Session expired — sign in again" with login deep link

## [ ] Prompt 3 — Harden backend print access with signed tickets

4. Backend hardening:
   - add signed print ticket support: POST print returns document instance plus a short-lived (5 min) single-purpose signed download URL (HMAC ticket) that re-checks permission and expiry server-side, enabling safe "open in new tab" and mobile sharing without exposing long-lived tokens
   - keep Bearer auth as primary; ticket is supplementary and audited
   - ensure every print endpoint across all modules uses the same permission + auth pattern; add a test that fails if any future print route is registered without authentication classes

## [ ] Prompt 4 — Verify URL naming and document the contract

5. Verify URL naming consistency (no accidental duplicate prefixes) and document the final print URL contract.

## [ ] Prompt 5 — Execute the complete regression, delivery, and reporting gate

TESTS:

- reproduce the 401 with a raw unauthenticated request and prove the new flow returns 200 with PDF via authenticated client
- ticket expiry and tamper rejection tests
- frontend unit test that print button never calls window.open with a raw /api/ URL
- token-refresh retry test

GIT:

- commit: "fix(documents): repair authenticated print flow and 401 on print endpoints"
- push; if blocked create feature/print-auth-fix and push; tick checkbox

FINAL OUTPUT: root cause evidence, fixed call sites, ticket contract, tests, commit hash, pushed branch.

## Incident source

INCIDENT:
GET /api/v1/ol/quotations/quotations/{id}/print/ returns 401 "Authentication credentials were not provided" with WWW-Authenticate: Bearer. The request carried no Authorization header.

META-INSTRUCTION (HIGHEST PRIORITY):

1. Before coding, create docs/prompts/PRINT_ENGINE_FIX_PROMPTS.md and save ALL 5 prompts EXACTLY as provided, each with a checkbox "[ ] Prompt N — title".
2. Commit and push that file immediately.
3. Execute ONLY Prompt 1 now; when green, tick its checkbox, commit, then proceed to Prompt 2. Never merge or skip.
