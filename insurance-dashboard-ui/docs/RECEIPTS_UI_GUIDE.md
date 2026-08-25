# Front Office Receipts UI Guide

The Receipts UI is a contract-first Front Office workspace for registering incoming payments, posting drafts, allocating money to commitments, reversing or cancelling transactions, importing CSV batches, and exposing a partner-scoped read-only portal. It follows the ZIC AIMS patterns: server-driven options, permission plus backend `allowed_actions` gating, structured ErrorCoach resolution, accessible focus states, and authenticated document handling.

## Screen map

| Screen | Route | Purpose | Primary API surface |
|---|---|---|---|
| Receipts work queue | `/front-office/receipts` | KPIs, quick views, server-side search/filtering, row actions, CSV export | `/api/v1/front-office/receipts/`, `/kpis/`, `/options/*` |
| New receipt | `/front-office/receipts/new` | Capture a draft or save-and-post payment details | receipt create and options endpoints |
| Edit receipt | `/front-office/receipts/:id/edit` | Update a draft; posted receipts are immutable | receipt detail and patch/post endpoints |
| Receipt detail | `/front-office/receipts/:id` | Master-detail summary, allocations, reversals, documents, audit timeline | detail, allocation, lifecycle, documents endpoints |
| Receipt imports | `/front-office/receipts/imports` | Download template, dry-run, row errors, commit mode, history, reprocess | import template, dry-run, commit, history endpoints |
| Partner portal list | `/portal/receipts` | Read-only own receipts list with dispute guidance | `/api/v1/portal/receipts/` |
| Partner portal detail | `/portal/receipts/:id` | Read-only receipt detail and own allocations | `/api/v1/portal/receipts/:id/` |

Dashboard cards link into the work queue with query parameters such as `?today=true`, `?unallocated_only=true`, and `?reversed_only=true`. The work queue hydrates these parameters on first render, and the active quick-view button exposes its state through `aria-pressed`.

## Action and permission rules

The UI first checks the operator’s IAM permission and then checks the row’s backend-provided `allowed_actions`. Superusers bypass the frontend permission check, but the backend remains authoritative. A missing or empty `allowed_actions` list never grants dangerous actions; the only legacy fallback is draft edit visibility for a row whose status is `DRAFT`.

| Action | Permission | State rule |
|---|---|---|
| View | `front_office.receipts.view` | Any visible receipt |
| Create | `front_office.receipts.create` | New Receipt button |
| Edit | `front_office.receipts.edit` | Draft only and allowed by backend |
| Post | `front_office.receipts.post` | Draft only and allowed by backend |
| Allocate/auto-allocate | `front_office.receipts.allocate` | Posted/unallocated state as determined by backend |
| Reverse | `front_office.receipts.reverse` | Backend allowed action and reversal rules |
| Cancel | `front_office.receipts.cancel` | Draft and backend allowed action |
| Print | `front_office.receipts.print` | Backend permission and document readiness |
| Import | `front_office.receipts.import` | Import CSV entry point |

## Error-code resolution table

Error messages must explain what happened and what the operator should do next. Deep links should land on a real configuration screen; do not expose UUIDs as user guidance.

| Code | Meaning | Operator resolution |
|---|---|---|
| `RECEIPT_PARAMETER_MISSING` | A required receipt parameter or option is not configured | Open the linked parameter screen, add/activate the missing option, then retry. |
| `RECEIPT_OVERALLOCATION` | Allocation total exceeds the receipt’s unallocated balance or a commitment balance | Reduce one or more allocation amounts until both totals are within balance; confirm currency before saving. |
| `RECEIPT_CURRENCY_MISMATCH` | Receipt and target commitment currencies differ without an effective rate | Configure or request the effective exchange rate, then retry the allocation. |
| `RECEIPT_ALLOCATION_INVALID` | An allocation row is incomplete or targets an ineligible commitment | Select a valid commitment, enter a positive amount, and keep the row amount within its balance. |
| `RECEIPT_INVALID_STATUS` | The requested action is not valid for the current receipt state | Refresh the receipt, review its status and allowed actions, and choose the next permitted action. |
| `RECEIPT_ALREADY_REVERSED` | The receipt or allocation has already been reversed | Review the Reversals and Audit tabs; do not submit a second reversal. |
| `RECEIPT_REVERSAL_LOCKED` | The reversal lock period or downstream policy state blocks reversal | Contact an authorized supervisor or follow the linked exception workflow. |
| `RECEIPT_IMPORT_ROW_INVALID` | One CSV row has invalid field data | Use the row and field message, correct the CSV value, and rerun dry-run. |
| `RECEIPT_IMPORT_DUPLICATE` | The row matches an existing receipt or duplicate row | Compare receipt number/reference and remove the duplicate or choose the approved reprocess path. |
| `RECEIPT_IMPORT_PARTIAL_FAILURE` | Some rows succeeded while others failed | Review every failed row, keep the successful batch evidence, and reprocess only corrected failures. |
| `TEMPLATE_PENDING` | No active print template is available | Ask a document administrator to activate the receipt template, then retry print. |
| `PARAMETER_MISSING` | Branding, currency, or another required parameter is absent | Open the deep-linked configuration page, complete the required setup, and retry. |
| `AUTHENTICATION_REQUIRED` | The session expired or the token was rejected | Select the sign-in link. The client refreshes once automatically before showing this coach. |

## Accessibility and theme readiness

All action buttons are keyboard reachable and retain visible focus rings. Quick filters use `aria-pressed`; data refresh counts are announced in an `aria-live="polite"` region; ErrorCoach uses `role="alert"`; dialogs are opened through the shared modal primitive with labelled title/description and keyboard close behavior. Destructive actions require a reason and confirmation rather than relying on color alone.

Receipt surfaces use design-token variables for backgrounds, borders, text, focus rings, badges, and modal surfaces. Dark-mode verification should be performed with the theme toggle and with `prefers-color-scheme: dark`; no receipt component should introduce a fixed white surface except the intentionally white PDF frame.

## Secure document handling

Receipt preview and download must use the authenticated document client. A protected `/api/` URL must never be passed directly to `window.open`, an iframe `src`, or an anchor `href`. The client fetches a PDF blob with the bearer token, retries once after a 401 refresh, creates a short-lived object URL for preview/download, and revokes it on cleanup. Opening a new tab is allowed only with a backend-issued short-lived signed ticket URL.

## Environment and merge checklist

| Check | Required action before production merge |
|---|---|
| `VITE_USE_MOCKS` | Use `true` only for deterministic frontend contract tests. Set `VITE_USE_MOCKS=false` for backend verification and production builds. |
| API base/proxy | Set `VITE_API_BASE` or `VITE_API_BASE_URL` as appropriate, and set the Vite `/api` proxy to the merged Django backend. |
| MSW removal | Do not ship mock-only fallback behavior. Keep MSW handlers for unit/E2E contract tests, but prove live calls with mocks disabled. |
| Backend migrations | Apply Front Office Receipts migrations, document migrations, allocation/import migrations, and any commitment/proposal integration migrations. |
| Seed dependencies | Seed branches, currencies, payment modes, payers/partners, proposals, commitments, receipt parameters, document branding, active receipt template, and test scenarios for partial/full first-premium allocation. |
| OpenAPI | `GET /api/schema/` must return a valid OpenAPI document without serializer introspection errors or receipt path omissions. |
| Permissions | Seed and verify view/create/edit/post/allocate/reverse/cancel/print/import permissions and partner portal scoping. |
| Structured errors | Every receipt action must return JSON error code, human message, field errors where applicable, resolution steps, correlation ID, and deep link where configuration is needed. |
| Real E2E | Run `E2E_REAL_BACKEND=1` with seeded credentials and no route mocks. Cover lifecycle, allocation, reversal, import, portal scoping, and ErrorCoach paths. |
| Release gates | Run frontend unit tests, typecheck, lint, build, Playwright, backend receipt tests, `git diff --check`, and verify the pushed SHA. |

## Current merged-backend status

At the time of Prompt 10 verification, the merged backend exposed only legacy receipt CRUD and did not expose the advanced routes listed in the screen map. The live evidence and exact drift list are maintained in [`docs/RECEIPTS_CONTRACT_VERIFICATION.md`](../../docs/RECEIPTS_CONTRACT_VERIFICATION.md). This guide must not be read as evidence that the missing backend endpoints are already available.

## References

[1]: ../../docs/RECEIPTS_CONTRACT_VERIFICATION.md "Receipts contract verification"
[2]: ../src/lib/receipts-api.ts "Typed receipt API client"
[3]: ../src/lib/documentClient.ts "Authenticated document client"
[4]: ../src/components/ErrorCoach.tsx "Accessible ErrorCoach component"
