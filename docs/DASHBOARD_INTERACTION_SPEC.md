# ZIC Dashboard Interaction Specification

## Product direction

The dashboard becomes an operational workspace rather than a read-only KPI page. The visual language remains the existing ZIC system: an airy light canvas, white elevated cards, restrained blue brand accents, semantic success/warning/destructive colors, compact Inter typography, and a persistent navigation rail. Interactions use short ease-out transitions, visible focus rings, keyboard-friendly controls, and responsive drawers on smaller screens.

## Interaction map

| Surface | Interaction | Destination or outcome |
|---|---|---|
| Sidebar module item | Click | Navigates to the exact module route already registered in `App.tsx`. |
| Sidebar parent | Click | Expands/collapses its children; if a parent has no children yet, it navigates to a real workspace page rather than remaining inert. |
| KPI card | Click | Deep-links to the corresponding policy, claims, partners, or front-office page. |
| Quotation chart series/legend | Click | Deep-links to the corresponding quotation workspace with the selected product context. |
| Notification item | Click | Marks the notification read and opens its related application/entity route. |
| Todo item | Click | Toggles completion through the dashboard API and keeps the current list responsive. |
| Global search | Type | Searches users, partners, onboarding applications, and available policy/scheme/claim/quotation entities in the database. Selecting a result navigates to its canonical detail or list route. |
| Language picker | Select | Persists the preference, updates translated shell labels, and keeps the chosen language after reload. Unsupported translations fall back to English. |
| Notification bell | Click | Opens a live popover with unread count, filters, read-all action, and a full notifications route. |
| Tasks/alerts hub | Click | Opens a dashboard workspace with task status filters, alert severity filters, acknowledge/dismiss actions, and links to source entities. |
| Currency tracker | Click | Opens the currency workspace with tracked pairs, latest rates, refresh state, and a rate-history view when the provider supplies it. |
| AI button | Click | Opens the assistant drawer. The drawer can expand into an inside-the-dashboard workspace width while preserving route context and conversation state. |
| Help & Support | Click | Opens the support workspace with documentation links, shortcuts, and an issue-report action. |

## Backend data contracts

The dashboard app owns durable user tasks, alert records, notification read state, tracked currency pairs, and a global search endpoint. Dashboard overview remains backward-compatible but now returns persisted tasks and live notification data where available. All mutation endpoints require authentication, enforce ownership/permission boundaries, and return the standard ZIC response envelope.

The first currency implementation uses a provider-backed latest-rate synchronization with a bounded timeout and a last-known-good cache in the database. The UI never blocks the dashboard on a third-party currency provider. A failed refresh exposes the last successful timestamp and a clear stale-state indicator. The default provider is ExchangeRate-API’s public endpoint, verified on 14 August 2026 at `https://open.er-api.com/v6/latest/USD`; it includes TZS and returns a `rates` map plus the provider update timestamp. Provider terms and availability must be reviewed before production SLA commitments.

## Route additions

The shell adds real destinations for `/search`, `/notifications`, `/tasks`, `/alerts`, `/currencies`, `/reports`, `/approvals`, and `/help`. Existing module routes remain the canonical target for entity search and KPI drill-downs. Search results include a `route` field generated server-side from entity type and identifier to prevent the frontend from guessing URLs.

## State and persistence

Language is stored in the authenticated user preference when the backend supports it and mirrored in local storage for immediate shell startup. Notification read state, task completion, alert acknowledgement, and tracked currency pairs are persisted through authenticated API calls. Optimistic UI updates are rolled back on failed mutations and report the error without losing the current filter/search state.

## Accessibility and responsive behavior

Every icon-only control has an accessible label. Popovers close on Escape and outside click. Search supports keyboard navigation, Enter selection, and a visible loading/empty/error state. The sidebar becomes an overlay on small screens. The AI drawer uses a full-height sheet on mobile and an expandable right workspace on desktop with `aria-expanded` and focus-visible controls.

## Assumptions

The existing Django authentication and standard response envelope remain authoritative. Module endpoints that are not yet implemented still receive a real route and clear empty-state copy, but the dashboard does not fabricate successful backend mutations. Currency rates are operational reference data and are labelled with provider and freshness metadata. Entity search is permission-scoped on the server before results are returned.
