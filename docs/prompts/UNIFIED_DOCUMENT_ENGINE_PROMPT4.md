# Unified Document Engine Prompt 4 — Branded Proposal and Commitment Documents

- [x] Prompt 4 — Branded Proposal Summary, Commitment Statement, future registry, authenticated preview UI, and audited branding administration

## Delivered

The unified registry now renders `PROPOSAL_SUMMARY` and `COMMITMENT_STATEMENT` through the shared WeasyPrint engine and branded print CSS. Proposal access derives partner scope through its source quotation and uses the quotation print permission. Commitment access uses the existing commitment view permission helper. Proposal and commitment contexts use human-readable snapshots and templates do not expose UUIDs.

Receipt, Policy Contract, Discharge Voucher, Commission Statement, Debit Note, and Premium Statement are registered as inactive `TEMPLATE_PENDING` types. Their render response is HTTP 409 with a stable `code: TEMPLATE_PENDING` and a teachable configuration message.

`BrandingConfiguration` is an immutable, versioned model with logo upload, company identity fields, legal footer, accent colors, active-version switching, admin read-only history, authenticated GET/POST API, atomic retirement, and central `BRANDING_VERSION_CREATED` / `BRANDING_VERSION_RETIRED` audit actions. The resolver falls back to the repository ZIC logo and default colors when individual values are absent. Each new document records the branding version in instance metadata.

A reusable `DocumentInstancesPanel` lists template/version/actor/time/page-count metadata. It renders PDFs in an authenticated blob-backed preview modal, downloads through the authenticated document client, opens new tabs only with server-issued signed ticket URLs, and revokes preview object URLs. Quotation detail, proposal selected-record drawers, and commitment detail now expose document surfaces. Legacy quotation HTML preview code was removed from the active flow. The branding screen is available at `/system-parameters/documents/branding`.

## Verification

Backend: `pytest -q` — **700 passed**, 12 warnings. Focused document tests: **15 passed**. Django `check` passed. `makemigrations --check --dry-run` reported no changes. `git diff --check` passed.

Frontend: `pnpm test` — **40 files, 207 tests passed**. `pnpm typecheck` passed. `pnpm lint` passed. `pnpm build` passed. Focused Prompt 4 document-panel and branding tests passed. The build emits an existing large-main-chunk advisory but completes successfully.
