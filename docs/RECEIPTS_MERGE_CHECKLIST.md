# Front Office Receipts — Merge Checklist

**Prepared:** 26 August 2026
**Companion report:** `docs/RECEIPTS_MERGE_DRIFT.md`
**Seam document:** `docs/OL_PROPOSALS_RECEIPTS_SEAM.md` (untouched by this merge)

This checklist is the merge gate for integrating the manus.im frontend with the receipts backend.
Tick an item only after the step is verified. Commit and push at the end.

## A. Contract verification (drift)

- [x] Typed client + MSW mocks compared against backend (`docs/RECEIPTS_MERGE_DRIFT.md`).
- [x] All endpoints declared by the frontend exist on the backend (incl. allocations, reversals,
      audit-timeline, bank-account, reprocess, per-resource options, portal alias).
- [x] All FK/reference responses carry `*_display` labels and the web aliases the client reads.
- [x] Error responses use the structured Error Coach envelope (`resolution_steps`,
      `resolutionSteps`, `deepLink`).
- [x] No frontend change required — backend drift fixed first; the only test change is the import
      row-key set updated to the merged contract.

## B. Print pipeline (authenticated, signed, teachable)

- [x] `POST /print/` returns a signed short-life ticket
      (`/front-office/receipts/documents/{id}/download/?ticket=...`).
- [x] `GET /documents/` streams PDF (Bearer or valid ticket); `application/pdf`, `%PDF` verified.
- [x] Ticket is user-bound and time-bound: wrong user → 403; expired ticket → 403; missing
      document → 404.
- [x] Unauthenticated requests return 401 with teachable `resolution_steps`.
- [x] Watermarks: draft → preview only; posted → none; reversed → `REVERSED`; cancelled →
      `CANCELLED`.

## C. E2E flows (merged suite, real seeds)

- [x] Create receipt → post → allocate to a first-premium commitment → proposal unlock banner
      (`first_premium_completed` + `first_premium_proposal_number`).
- [x] Reverse receipt → guard re-locks + `REVERSED` watermark on print.
- [x] Import dry-run → commit flow (CREATE_DRAFTS / POST / POST_AND_ALLOCATE) incl.
      partial-failure reprocessing (idempotent).
- [x] Portal read-only scoping (`/api/v1/portal/receipts/`) — partner cannot mutate.
- [x] Full backend suite green.

## D. Production flags & docs

- [x] `VITE_USE_MOCKS=false` documented for staging/prod:
      - `insurance-dashboard-ui/.env.example` (line 4)
      - `insurance-dashboard-ui/docs/RECEIPTS_UI_GUIDE.md`
- [x] Drift report written: `docs/RECEIPTS_MERGE_DRIFT.md`.
- [x] This checklist committed.

## E. Release gates

- [x] Backend tests pass (receipts 216; front-office + OL-proposals 320; full suite).
- [x] OpenAPI schema generates (`manage.py spectacular`).
- [x] Ruff clean (line-length 120).
- [x] URL resolution for all new routes.
- [x] `docs/OL_PROPOSALS_RECEIPTS_SEAM.md` not modified.
- [x] `insurance-dashboard-ui/package-lock.json` not staged.

## F. Merge action

- [x] Commit: `feat(receipts): merge manus frontend, verify contract, fix drift, enable production flags`
- [x] Push to `feature/front-office-receipts-foundation`.
- [x] Tag `v1.1.0-receipts-merged` (if tagging enabled).

## Post-merge follow-ups

- `pnpm build` + Playwright smoke against `VITE_USE_MOCKS=false` when a real backend is reachable
  (staging), to confirm the full Prompt 10 flow in the browser.
- Convert the drf-spectacular `unable to guess serializer` fallbacks into `@extend_schema`
  annotations if strict schema-first tooling is required later.
