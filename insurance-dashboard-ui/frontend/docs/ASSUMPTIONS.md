# Frontend Assumptions

This frontend foundation extends the existing `insurance-dashboard-ui` workspace rather than creating a second application. Existing pages, Lit custom elements, TanStack Query usage, authentication context, and dashboard integrations remain the source of truth for already-implemented modules.

The backend is consumed through the `/api/v1/` namespace. The development server proxies `/api` to `http://127.0.0.1:8000` by default; set `VITE_BACKEND_PROXY_TARGET` to point to another Django host. In deployed environments, `VITE_API_BASE_URL` may be set to an absolute API origin. When it is empty, requests remain relative so the reverse proxy can serve both application and API from one origin.

The IAM access endpoint is expected at `GET /api/v1/iam/me/access/`. The client accepts either direct access metadata or an `{ access: ... }` envelope. Until the endpoint is available for a particular account, the frontend falls back to permissions returned by the login response. A user with no permissions in the fallback response is treated as an authenticated administrator; this avoids hiding the entire application while the backend access endpoint is unavailable.

Module keys are mapped to the existing platform naming conventions. `ol_quotations`, `ol_parameters`, and related Ordinary Life keys also accept the broad `ordinary_life` permission. Group Life and Group Credit child modules similarly accept their broad parent keys. This aliasing is intentionally isolated in `src/lib/access.tsx` and can be removed once the IAM access payload exposes normalized visible-module keys for every module.

The current backend does not expose a single universal exchange-rate contract in every environment. The footer requests `GET /api/v1/dashboard/currencies/current/` and displays a transparent unavailable state if that endpoint is missing, unauthorized, or temporarily unavailable; no business rate is hardcoded in the frontend.

The existing backend login contract and two-factor flow remain authoritative. Credential validation is now performed client-side with Zod for immediate feedback, while server-side validation and authorization continue to govern the final outcome.
