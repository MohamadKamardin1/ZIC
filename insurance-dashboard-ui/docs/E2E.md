# ZIC Frontend End-to-End Testing Guide

**Scope:** Ordinary Life parameters and quotation lifecycle coverage  
**Runner:** Playwright Test  
**Browser target:** Chromium  
**Application:** Vite development server on `http://127.0.0.1:4173`

## 1. Test commands

Install frontend dependencies from the project root before running tests:

```bash
cd insurance-dashboard-ui
pnpm install
pnpm exec playwright install chromium
```

The unit and component suite is run with:

```bash
pnpm test -- --run
```

The browser suite is run with:

```bash
pnpm test:e2e
```

The Playwright configuration starts Vite automatically through `webServer`, reuses an existing server when one is already available, and stores artifacts under Playwright’s standard `test-results` directory. A headed run is useful while diagnosing selectors or focus behavior:

```bash
pnpm exec playwright test --headed
```

A single scenario can be isolated by file or test title:

```bash
pnpm exec playwright test e2e/ol-quotation-lifecycle.spec.ts
pnpm exec playwright test -g "partner verification"
```

## 2. Test architecture

The E2E suite uses a deterministic browser fixture rather than depending on a developer’s personal account or a running Django database. The shared fixture seeds the frontend’s session storage with a superuser profile, mocks IAM access metadata, and supplies the minimum API responses needed to exercise the actual UI paths.

This approach keeps the suite repeatable while retaining production-like behavior at the browser boundary: React Router resolves real routes, lazy-loaded chunks are fetched, form controls are interacted with through accessible locators, and success/error states are driven by mocked HTTP responses.

| Shared fixture | Purpose |
|---|---|
| `seedSuperuserSession(page)` | Seeds the same access-token and session keys consumed by the auth context |
| `mockAccessApi(page)` | Returns IAM metadata with superuser status and Ordinary Life permissions |
| `mockParameterApi(page)` | Mocks the default parameter list/create response for CRUD coverage |
| `mockQuotationApi(page, overrides)` | Mocks quotation detail, wizard step, financial, lifecycle, and proposal endpoints |
| `mockPlans(page)` | Supplies the standalone plan-search response required by plan selection |

The Playwright suite is intentionally excluded from Vitest via `vitest.config.ts`. This prevents Vitest from importing `test()` declarations from Playwright files while keeping both runners available through separate package scripts.

## 3. Scenario inventory

| File | Scenario | Coverage |
|---|---|---|
| `e2e/auth.spec.ts` | Login and role-aware navigation | Login request, session persistence, access metadata, Ordinary Life navigation visibility |
| `e2e/ol-parameters.spec.ts` | Default parameter CRUD | Open Default Setup, create a typed parameter, save it, and verify the refreshed table request |
| `e2e/ol-quotation-wizard.spec.ts` | Full quotation wizard progression | Personal details, plan selection, member coverage, installment modal, funds step, riders, financial details, and Review & Finalize |
| `e2e/ol-quotation-lifecycle.spec.ts` | Lifecycle controls | Generated document print preview, blocked conversion when partner verification is incomplete, completion, and eligible conversion handoff |

The browser tests intentionally cover both allowed and blocked paths. A green result therefore confirms not only that buttons work, but also that the UI communicates business-rule blocks without sending an invalid conversion request.

## 4. Authentication scenario

The authentication test starts from `/login`, intercepts the login endpoint, fills the existing username and password fields, submits the real form, and waits for the application to resolve the authenticated root route. The access metadata response marks the user as a superuser and includes Ordinary Life permission metadata. The test then confirms that the Ordinary Life navigation branch is visible and that the quotations entry can be opened.

No real credentials are stored in the repository. When a connected backend is used instead of route mocks, credentials must be provided through the execution environment or an interactive local setup and must never be committed to `e2e/` files.

## 5. Parameter CRUD scenario

The parameter scenario navigates directly to `/ordinary-life/parameters/default-setup`, verifies the screen heading, opens the create modal, chooses a typed value, enters a key and value, submits the form, and observes the mocked POST response followed by a refreshed list request. It uses accessible labels and role-based button names rather than CSS implementation details.

The scenario represents the CRUD contract used by the other parameter screens: table-first collection rendering, typed form controls, modal validation, server save, and refresh. Additional parameter pages can reuse the shared fixture and add screen-specific validation cases without changing the runner configuration.

## 6. Quotation wizard scenario

The wizard test starts at `/ordinary-life/quotations/new`. It exercises required-field validation on Personal Details, enters a valid personal profile, selects a plan from the backend plan-search result, and proceeds through the wizard tabs. The Installments step opens the Configure Installments modal and enters a valid 100% allocation before saving.

After the installment modal closes, the test explicitly visits Investment Funds, Riders & Benefits, and Financial Details. It then confirms the Financial Details heading and the Review & Finalize section. The test does not assert a client-side premium calculation; financial values remain mocked backend output and the frontend only renders them.

## 7. Lifecycle scenarios

The lifecycle suite opens a finalized quotation detail route and confirms the generated document appears in the Documents tab. It opens Print Preview and verifies the source quotation and template-version metadata. A separate draft or non-compliant partner response confirms that the conversion modal lists the partner-verification block and does not submit the conversion request.

The eligible path returns a finalized, non-expired, partner-verified quotation with a compliant partner. The test opens Convert to Proposal, submits the modal, and waits for the real application navigation to `/ordinary-life/proposals?quotation=quote-1`. This matches the detail page handler, which closes the modal after a successful API response and routes the user to the proposal work queue.

## 8. Locator and accessibility conventions

Tests prefer `getByRole`, `getByLabel`, and `getByText` with exact names where duplicated navigation labels exist. The test suite avoids selectors tied to Tailwind classes, DOM nesting, or generated React identifiers. Dialog actions are scoped through `getByRole("dialog", { name: ... })` so that a page-level action and a modal submit button cannot be confused.

Every new modal or drawer should preserve the shared overlay behavior: focus moves into the surface, Tab remains inside it, Escape closes it, and focus returns to the initiating control. Any new icon-only button must include an explicit `aria-label`.

## 9. Debugging failed runs

When a test fails in CI or locally, first rerun the single spec with the same browser project. Use `--headed` to observe navigation and `--trace on` when request ordering or lazy loading is suspected:

```bash
pnpm exec playwright test e2e/ol-quotation-wizard.spec.ts --headed --trace on
```

Playwright retains screenshots, videos, and traces for failed tests in `test-results`. The most useful debugging sequence is to confirm the route, inspect the request URL captured by the fixture, then verify the accessible name of the target control. Avoid fixing a failure by weakening a business assertion; update the fixture to match the actual backend contract or correct the UI behavior.

## 10. Extending the suite

New Ordinary Life modules should add a focused spec under `e2e/`, reuse `seedSuperuserSession` and `mockAccessApi`, and keep module-specific API handlers in a dedicated fixture helper. A test should cover at least one successful path, one validation or permission block, and one refresh or navigation outcome. The final acceptance command remains:

```bash
pnpm typecheck && pnpm test -- --run && pnpm lint && pnpm build && pnpm test:e2e
```

## 11. Unified print-engine scenarios

`e2e/print-engine.spec.ts` verifies the shared document experience for all currently implemented document types. The quotation scenario opens the list, selects a finalized row, chooses **Print**, previews the returned PDF in the authenticated panel, captures the downloaded file, and confirms that **Open in new tab** receives only the server-issued signed ticket. The proposal and commitment scenarios exercise their respective document tabs with the same Preview, Download, and signed-ticket actions.

The refresh scenario deliberately returns one 401 for the first PDF request. The browser intercepts `/api/v1/auth/refresh/`, returns refreshed tokens, and verifies that the original PDF operation succeeds without a session ErrorCoach. The spec also checks that the preview iframe uses a `blob:` URL rather than a protected API URL.

Run the focused suite with:

```bash
pnpm exec playwright test e2e/print-engine.spec.ts --project=chromium
```

The full browser acceptance suite should include this focused print spec together with the quotation lifecycle, quotation wizard, commitment, parameter, and authentication specs. These tests use deterministic API mocks; backend PDF bytes, pypdf content, ticket tamper/expiry, permission, and audit evidence are covered by `backend/apps/documents/tests/test_engine.py`.
