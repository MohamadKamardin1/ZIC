---
name: drf-jwt-frontend-integration
description: Integrate a React/Vite frontend with a Django DRF backend using JWT auth with response envelopes, automatic token refresh on 401, and two-step 2FA login
source: auto-skill
extracted_at: '2026-06-21T08:43:27.066Z'
---

# DRF JWT Frontend Integration Pattern

## When to Use
When connecting a React (or any SPA) frontend to a Django REST Framework backend that uses:
- `djangorestframework-simplejwt` for JWT authentication
- Standard response envelope: `{ success, status_code, message, data, meta }`
- Optional 2FA flow (TOTP) where login can require a second OTP step
- Token refresh with rotation and blacklist

## Authentication Flow

### Step 1: Credentials → check for 2FA
```
POST /api/v1/auth/login/  { username, password }
```
Two possible responses:
- **2FA required**: `{ data: { requires_2fa: true, user_id } }` → show OTP screen
- **Login success**: `{ data: { access_token, refresh_token, user } }` → store tokens, navigate

### Step 2 (if 2FA): OTP → tokens
```
POST /api/v1/auth/login/  { username, password, otp_code }
```
Returns tokens directly.

## API Layer Pattern

### Token helpers in `lib/api.ts`
```typescript
// sessionStorage — cleared on tab close
const TK_ACCESS = "aims_access_token"
const TK_REFRESH = "aims_refresh_token"

function getAccessToken(): string | null { return sessionStorage.getItem(TK_ACCESS) }
function setTokens(tokens: { access_token: string; refresh_token: string; ... }) {
  sessionStorage.setItem(TK_ACCESS, tokens.access_token)
  sessionStorage.setItem(TK_REFRESH, tokens.refresh_token)
}
function clearTokens() { ... }
```

### Low-level fetch with auth header injection
```typescript
async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers)
  headers.set("Content-Type", "application/json")
  const token = getAccessToken()
  if (token) headers.set("Authorization", `Bearer ${token}`)
  return fetch(`${API_BASE}${path}`, { ...init, headers })
}
```

### Automatic 401 retry with token refresh
```typescript
let _refreshing: Promise<Tokens | null> | null = null

async function doRefresh(): Promise<Tokens | null> {
  const refresh = getRefreshToken()
  if (!refresh) return null
  const res = await fetch(`${API_BASE}/api/v1/auth/refresh/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh }),
  })
  if (!res.ok) return null
  const json = await res.json()
  const data = json?.data ?? json
  const tokens = {
    access_token: data.access_token ?? data.access ?? "",
    refresh_token: data.refresh_token ?? data.refresh ?? refresh,
    ...
  }
  setTokens(tokens)
  return tokens
}

async function apiFetchAuth(path: string, init: RequestInit = {}): Promise<Response> {
  const res = await apiFetch(path, init)
  if (res.status !== 401) return res
  // Deduplicate concurrent refresh calls
  if (!_refreshing) {
    _refreshing = doRefresh().finally(() => { _refreshing = null })
  }
  const refreshed = await _refreshing
  if (!refreshed) throw { status: 401, message: "Session expired." }
  return apiFetch(path, init)  // retry with new token
}
```

### Error extraction from DRF responses
```typescript
function extractError(res: Response, body: unknown): string {
  if (typeof body === "object" && body !== null) {
    const b = body as Record<string, unknown>
    if (Array.isArray(b.non_field_errors)) return b.non_field_errors[0] as string
    for (const key in b) {
      const val = b[key]
      if (Array.isArray(val) && val.length > 0) return `${key}: ${val[0] as string}`
    }
    if (typeof b.detail === "string") return b.detail
  }
  return `Request failed (${res.status}).`
}
```

## Auth Context Pattern (React)

### Two-step login — return boolean from signIn
```typescript
// signIn returns true if 2FA is required, false otherwise
const signIn = useCallback(async (email, password): Promise<boolean> => {
  const result = await apiLogin({ email, password })
  const data = result.data
  if (data.requires_2fa) {
    setRequires2FA(true)
    setPendingCreds({ email, password })
    return true  // caller shows OTP step
  }
  if (data.user) {
    setTokens({ ... })
    setUser(data.user)
    sessionStorage.setItem("aims_user", JSON.stringify(data.user))
  }
  return false  // no 2FA, navigate directly
}, [])
```

### Login page uses the return value
```typescript
async function onCredentialsSubmit(e: FormEvent) {
  const needs2FA = await signIn(email, password)
  if (!needs2FA) navigate("/", { replace: true })
}
```

### 2FA completion reuses stored credentials
```typescript
const complete2FA = useCallback(async (otpCode: string) => {
  if (!pendingCreds) return
  const result = await apiLogin(pendingCreds, otpCode)
  // ... store tokens, set user ...
  setRequires2FA(false)
  setPendingCreds(null)
}, [pendingCreds])
```

## Dashboard API Response Mapping

Backend returns camelCase nested objects. Map to frontend types:

```typescript
function mapDashboard(raw: BackendDashboard): DashboardData {
  // Hero stats
  const hero = [
    { label: "Monthly Growth", value: `+${raw.kpis.monthlyGrowth}%`, icon: "growth" },
    ...
  ]
  // Policies — map object entries to arrays
  const breakdown = Object.entries(raw.policies.breakdown).map(([key, v]) => ({
    label: LABEL_MAP[key] ?? key,
    count: v.count,
    delta: v.growth,
    up: v.growth >= 0,
  }))
  // ... map each section ...
  return { hero, policies, claims, partners, ... }
}
```

## Session Persistence

- **sessionStorage** — tokens + user survive page reloads but clear on tab close
- On app mount, check `hasValidSession()` or `loadStoredTokens()` to determine if user is already logged in
- On `signOut()`: call backend logout (best-effort), then clear all local state + sessionStorage

## Auth-Protected Routes

```typescript
function RequireAuth({ children }) {
  const { accessToken } = useAuth()
  return accessToken ? <>{children}</> : <Navigate to="/login" replace />
}
```

## Error Handling in Protected Pages

```typescript
useEffect(() => {
  getDashboard()
    .then(setData)
    .catch((e) => {
      const msg = e.message
      if (msg.includes("Session expired") || msg.includes("401")) {
        signOut()
        navigate("/login", { replace: true })
      } else {
        setError(msg)
      }
    })
}, [])
```

## .env Configuration

```
VITE_API_BASE=http://localhost:8000
```

Used as: `export const API_BASE = import.meta.env.VITE_API_BASE ?? ""`

## Common Pitfalls

- **Backend login field name**: DRF `LoginSerializer` uses `username` but accepts email as value. Frontend must send `{ username: emailValue, password }`.
- **Response envelope**: Backend wraps everything in `{ success, data, meta }`. The `data` field contains the actual payload. Always extract `json.data` (with fallback to `json`).
- **Token field names**: SimpleJWT refresh returns `{ access, refresh }` but login returns `{ access_token, refresh_token }`. Handle both.
- **Concurrent 401s**: Deduplicate refresh calls with a shared Promise (`_refreshing`) so multiple parallel requests don't hit the refresh endpoint multiple times.
- **User type mismatch**: Backend `UserListSerializer` returns `full_name`, `user_type`, `department` — not the simplified `{ name, org, avatar }` from mocks. Update all references.
- **Logout best-effort**: If the refresh token is invalid or expired, the backend logout will fail. Always clear local tokens in a `finally` block regardless.

## djangorestframework-camel-case — Critical

If the backend has `djangorestframework_camel_case` in its renderer/parser pipeline, **all snake_case keys in JSON responses are converted to camelCase**. This means:

| Python/DRF key | JSON key (with renderer) |
|---|---|
| `access_token` | `accessToken` |
| `refresh_token` | `refreshToken` |
| `requires_2fa` | `requires2FA` |
| `user_id` | `userId` |
| `access_expires_in` | `accessExpiresIn` |
| `first_name` | `firstName` |
| `full_name` | `fullName` |

**Defensive pattern** — always check both key variants:
```typescript
const data = result.data as Record<string, unknown>
const accessToken = (data.accessToken as string) ?? (data.access_token as string) ?? ""
const requires2FA = (data.requires2FA ?? data.requires_2fa) === true
```

**The refresh endpoint is special**: SimpleJWT's `TokenRefreshView` returns `{ access, refresh }` (no underscores at all), so it is **NOT** affected by the camelCase renderer. The login endpoint **IS** affected.

**TypeScript types must match camelCase** (the renderer's output):
```typescript
interface LoginTokens {
  accessToken: string
  refreshToken: string
  accessExpiresIn: number
  refreshExpiresIn: number
}
interface AuthUser {
  fullName: string
  firstName: string
  userType: string
  is2faEnabled: boolean
  // ... etc
}
```
