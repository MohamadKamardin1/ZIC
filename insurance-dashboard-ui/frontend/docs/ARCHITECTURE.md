# ZIC Frontend Architecture

## Purpose

The ZIC frontend is a React 19 and TypeScript application that provides a secure operational shell over the Django APIs. The implementation deliberately extends the existing `insurance-dashboard-ui` workspace so completed dashboard, onboarding, partner, parameter, and Ordinary Life screens retain their current routes and backend integrations.

## Runtime composition

`src/main.tsx` composes the application in the following order:

| Layer | Responsibility |
|---|---|
| `QueryClientProvider` | Server-state caching, request lifecycle, and dashboard/module queries. |
| `BrowserRouter` | URL-based module navigation and deep-link support. |
| `ThemeProvider` | Light/dark theme state and CSS token application. |
| `LanguageProvider` | UI language labels and the existing language picker. |
| `AuthProvider` | Login, token/session state, 2FA, and sign-out. |
| `AccessProvider` | IAM access metadata, permission fallback, navigation visibility, and route access decisions. |
| `AIProvider` | Existing assistant panel and AI workspace controls. |

The root `App` keeps unauthenticated users on `/login`. Authenticated users render the `DashboardLayout`, which contains the collapsible navigation rail, topbar, breadcrumb context, route outlet, footer status bar, and assistant panel.

## API boundary

`src/lib/apiClient.ts` is the foundation client for new screens. It reads `VITE_API_BASE_URL` or `VITE_API_BASE`, otherwise using relative `/api` paths. Each request adds an `X-Correlation-ID`, attaches the session access token, unwraps the standard `{ data }` response envelope, and converts non-2xx responses into `ApiClientError` with status, code, message, field errors, details, and correlation ID.

Table pages should use `buildTableQuery({ page, pageSize, search, ordering, filters })`. The helper emits the backend’s `page`, `page_size`, `search`, and `ordering` contract while preserving arbitrary filter keys. Module APIs should remain parameter-driven and must not embed option lists or actuarial values in the frontend.

## Authentication and access

The existing `AuthProvider` remains the authority for credential login, token persistence, refresh, and 2FA. The login form uses React Hook Form and Zod for local validation but always submits through the existing auth context.

After authentication, `AccessProvider` queries `GET /api/v1/iam/me/access/`. It accepts direct access metadata or an `{ access }` envelope. Navigation items are filtered by module key, and `AccessGate` prevents direct URL access to modules that are not present in the access profile. The access layer supports broad parent-module aliases while the backend finalizes its normalized visible-module response.

## Routing

The existing route tree is retained and organized under the authenticated layout. It includes placeholders for the full platform menu: Partner On-boarding, Ordinary Life, Group Life, Group Credit, Front Office, Reports, System Parameters, User Management, Approvals, Help & Support, and dashboard workspaces. A module page can be implemented independently without changing shell contracts.

## Lit integration

Existing Lit custom elements remain registered from `src/lit/index.ts` and are consumed by React pages where the completed screens already use them. The shell does not duplicate Lit component behavior; it supplies the shared tokens, spacing, focus treatment, and theme variables that allow React and Lit surfaces to render consistently.

## Backend integration points

| Frontend capability | Backend contract |
|---|---|
| Login and 2FA | Existing IAM login and 2FA endpoints through `src/lib/api.ts`. |
| Navigation visibility | `GET /api/v1/iam/me/access/`. |
| Global search | Existing dashboard/global search API helper. |
| Notifications | Existing dashboard notification endpoints through `Topbar`. |
| Exchange-rate footer | `GET /api/v1/dashboard/currencies/current/`, with unavailable-state fallback. |
| OL Quotations | Existing `/api/v1/ol-quotations/` and `/api/v1/ol/quotations/` routes. |
| Parameter-driven forms | Existing System Parameters and OL Parameters APIs used by module pages. |

## Testing and quality gates

Vitest runs in jsdom with Testing Library and jest-dom. The foundation tests cover API error normalization, credential validation and login submission, and access-driven sidebar rendering. The release gate is `pnpm typecheck`, `pnpm lint`, `pnpm test`, and `pnpm build`.
