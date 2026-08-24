import type {
  AuthUser,
  LoginResult,
  LoginSuccessData,
  LoginTokens,
  Setup2FAResult,
  DashboardData,
  DashboardTaskRecord,
  DashboardAlertRecord,
  DashboardNotificationRecord,
  GlobalSearchResult,
  CurrencyPairRecord,
  PartnerTypeRecord,
  BranchRecord,
  LocationRecord,
  ParameterGroup,
  SystemParameter,
  ChoiceList,
  ChoiceOption,
  PartnerTypeDocumentRequirement,
  PartnerTypeFieldConfiguration,
  PartnerTypeContactRequirement,
  PartnerTypeBankRequirement,
  PartnerDocument,
  PartnerDynamicFieldValue,
  PartnerAssignmentContact,
  PartnerAssignmentBankAccount,
  PartnerKYCProfile,
  ApplicationContact,
  ApplicationBankAccount,
  ApplicationFieldValue,
  UnifiedOnboardingRecord,
  PartnerTypeAssignment,
  PartnerTypeAssignmentHistory,
} from "./types"

export const API_BASE = import.meta.env.VITE_API_BASE ?? ""

// ---------------------------------------------------------------------------
// Token helpers. localStorage keeps authenticated same-origin Manage tabs in the
// same session, while the sessionStorage fallback preserves existing sessions.
// ---------------------------------------------------------------------------

const TK_ACCESS = "aims_access_token"
const TK_REFRESH = "aims_refresh_token"

function readStoredValue(key: string): string | null {
  return localStorage.getItem(key) ?? sessionStorage.getItem(key)
}

function getAccessToken(): string | null {
  return readStoredValue(TK_ACCESS)
}

function getRefreshToken(): string | null {
  return readStoredValue(TK_REFRESH)
}

function setTokens(tokens: LoginTokens) {
  localStorage.setItem(TK_ACCESS, tokens.accessToken)
  localStorage.setItem(TK_REFRESH, tokens.refreshToken)
  sessionStorage.setItem(TK_ACCESS, tokens.accessToken)
  sessionStorage.setItem(TK_REFRESH, tokens.refreshToken)
}

function clearTokens() {
  localStorage.removeItem(TK_ACCESS)
  localStorage.removeItem(TK_REFRESH)
  sessionStorage.removeItem(TK_ACCESS)
  sessionStorage.removeItem(TK_REFRESH)
}

export function hasValidSession(): boolean {
  return !!getAccessToken()
}

export function loadStoredTokens(): LoginTokens | null {
  const access = getAccessToken()
  const refresh = getRefreshToken()
  if (access && refresh) return { accessToken: access, refreshToken: refresh, accessExpiresIn: 0, refreshExpiresIn: 0 }
  return null
}

export function dropTokens() {
  clearTokens()
}

// ---------------------------------------------------------------------------
// Low-level fetch wrapper with auth header injection
// ---------------------------------------------------------------------------

interface ApiError {
  status: number
  body: Record<string, unknown> | null
  message: string
}

async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers)
  headers.set("Content-Type", "application/json")
  headers.set("Accept", "application/json")

  const token = getAccessToken()
  if (token) {
    headers.set("Authorization", `Bearer ${token}`)
    console.log(`[apiFetch] ${init.method ?? "GET"} ${path} — sending token: ${token.substring(0, 30)}...`)
  } else {
    console.warn(`[apiFetch] ${init.method ?? "GET"} ${path} — NO token in sessionStorage`)
  }

  const res = await fetch(`${API_BASE}${path}`, { ...init, headers })
  if (!res.ok) console.warn(`[apiFetch] ${path} → ${res.status}`)
  return res
}

function extractError(res: Response, body: unknown): string {
  if (typeof body === "object" && body !== null) {
    const b = body as Record<string, unknown>
    // DRF non-field errors
    if (Array.isArray(b.non_field_errors)) return (b.non_field_errors[0] as string) ?? "Request failed."
    // DRF field errors — return first
    for (const key in b) {
      const val = b[key]
      if (Array.isArray(val) && val.length > 0) return `${key}: ${val[0] as string}`
      if (typeof val === "string") return `${key}: ${val}`
    }
    if (typeof b.detail === "string") return b.detail
    if (typeof b.message === "string") return b.message
  }
  return `Request failed (${res.status}).`
}

// ---------------------------------------------------------------------------
// Token refresh — called when an API call returns 401
// ---------------------------------------------------------------------------

let _refreshing: Promise<LoginTokens | null> | null = null

async function doRefresh(): Promise<LoginTokens | null> {
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
  // Refresh endpoint returns { access, refresh } inside data (no underscores, so unchanged by camelCase renderer)
  const tokens: LoginTokens = {
    accessToken: data.accessToken ?? data.access ?? "",
    refreshToken: data.refreshToken ?? data.refresh ?? getRefreshToken() ?? "",
    accessExpiresIn: data.accessExpiresIn ?? 0,
    refreshExpiresIn: data.refreshExpiresIn ?? 0,
  }
  setTokens(tokens)
  return tokens
}

/**
 * Performs a fetch with automatic token refresh on 401.
 * Retries the original request exactly once after a successful refresh.
 */
export async function apiFetchAuth(path: string, init: RequestInit = {}): Promise<Response> {
  const res = await apiFetch(path, init)

  if (res.status !== 401) return res

  // Deduplicate concurrent refresh calls
  if (!_refreshing) {
    _refreshing = doRefresh().finally(() => { _refreshing = null })
  }
  const refreshed = await _refreshing
  if (!refreshed) throw { status: 401, body: null, message: "Session expired. Please sign in again." } as ApiError

  // Retry original request with new token
  return apiFetch(path, init)
}

// ---------------------------------------------------------------------------
// Auth API calls
// ---------------------------------------------------------------------------

export interface LoginCredentials {
  email: string
  password: string
}

/**
 * POST /api/v1/auth/login/
 * If the user has 2FA enabled and no otp_code is provided, the response
 * contains `requires_2fa: true`.  Call login again with the same credentials
 * plus the OTP code to obtain tokens.
 */
export async function login(credentials: LoginCredentials, otpCode?: string): Promise<LoginResult> {
  const res = await fetch(`${API_BASE}/api/v1/auth/login/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      username: credentials.email, // backend accepts email as username
      password: credentials.password,
      ...(otpCode ? { otp_code: otpCode } : {}),
    }),
  })

  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(extractError(res, body))
  }

  const json: LoginResult = await res.json()

  // DEBUG: log what we got back
  const raw = json as unknown as Record<string, unknown>
  const d = raw.data as Record<string, unknown> | undefined
  console.log("[api.login] response keys:", Object.keys(raw))
  console.log("[api.login] data keys:", d ? Object.keys(d) : "undefined")
  console.log("[api.login] accessToken present:", "accessToken" in (d || {}))
  console.log("[api.login] access_token present:", "access_token" in (d || {}))

  // If login succeeded with tokens, persist them
  const data = json.data as LoginSuccessData
  const dataRecord = data as unknown as Record<string, unknown>
  const token = dataRecord.accessToken as string | undefined
    ?? dataRecord.access_token as string | undefined
  if (token) {
    console.log("[api.login] storing token:", token.substring(0, 30) + "...")
    setTokens({
      accessToken: dataRecord.accessToken as string ?? dataRecord.access_token as string,
      refreshToken: dataRecord.refreshToken as string ?? dataRecord.refresh_token as string,
      accessExpiresIn: Number(dataRecord.accessExpiresIn ?? dataRecord.access_expires_in ?? 0),
      refreshExpiresIn: Number(dataRecord.refreshExpiresIn ?? dataRecord.refresh_expires_in ?? 0),
    })
  } else {
    console.warn("[api.login] NO token found in response data!")
  }

  return json
}

/**
 * POST /api/v1/auth/logout/
 */
export async function logout(): Promise<void> {
  const refreshToken = getRefreshToken()
  try {
    await apiFetchAuth("/api/v1/auth/logout/", {
      method: "POST",
      body: JSON.stringify({ refresh_token: refreshToken }),
    })
  } catch {
    // Best-effort — always clear local tokens
  } finally {
    clearTokens()
  }
}

/**
 * POST /api/v1/auth/setup-2fa/
 * Returns QR code URL, secret, and backup codes.
 */
export async function setup2FA(): Promise<Setup2FAResult> {
  const res = await apiFetchAuth("/api/v1/auth/setup-2fa/", { method: "POST" })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(extractError(res, body))
  }
  const json = await res.json()
  return json.data as Setup2FAResult
}

/**
 * POST /api/v1/auth/verify-2fa/
 * Verifies a TOTP code and enables 2FA.
 */
export async function verify2FA(otpCode: string): Promise<void> {
  const res = await apiFetchAuth("/api/v1/auth/verify-2fa/", {
    method: "POST",
    body: JSON.stringify({ otp_code: otpCode }),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(extractError(res, body))
  }
}

/**
 * POST /api/v1/auth/disable-2fa/
 * Requires current password confirmation.
 */
export async function disable2FA(password: string): Promise<void> {
  const res = await apiFetchAuth("/api/v1/auth/disable-2fa/", {
    method: "POST",
    body: JSON.stringify({ password }),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(extractError(res, body))
  }
}

/**
 * GET /api/v1/users/users/me/
 */
export async function getMe(): Promise<AuthUser> {
  const res = await apiFetchAuth("/api/v1/users/users/me/")
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(extractError(res, body))
  }
  return (await res.json()).data ?? (await res.json())
}

// ---------------------------------------------------------------------------
// Dashboard API call — maps backend camelCase shape → frontend types
// ---------------------------------------------------------------------------

interface BackendDashboard {
  date: { day: string; weekday: string; month: string }
  kpis: { monthlyGrowth: number; activeUsers: number; revenue: string }
  policies: {
    total: number
    growth: number
    breakdown: Record<string, { count: number; growth: number }>
  }
  claims: Record<string, { percentage: number; count: number }>
  partners: { total: number; breakdown: Record<string, { percentage: number; remaining: number }> }
  debited: { total: string; breakdown: Record<string, { amount: string; color: string }> }
  quotations: {
    total: number
    period: string
    data: { month: string; ol: number; gl: number; gc: number; pen: number }[]
    legend: Record<string, { percentage: number; color: string }>
  }
  notifications: {
    request: number; approved: number; rejected: number; cancelled: number
    unreadCount: number
    notifications: { id: string; type: string; status: string; date: string; amount?: string; unread: boolean }[]
  }
  todos: { id: string; text: string; date: string; completed: boolean }[]
  leads: { rank: number; name: string; amount: string }[]
}

const LABEL_MAP: Record<string, string> = {
  groupCredit: "Group Credit",
  groupLife: "Group Life",
  ordinaryLife: "Ordinary Life",
  pension: "Pension",
}

const CHART_COLORS: Record<string, string> = {
  gc: "var(--chart-1)",
  gl: "var(--chart-3)",
  ol: "var(--chart-4)",
  pen: "var(--chart-5)",
}

function mapDashboard(raw: BackendDashboard): DashboardData {
  // Hero stats
  const hero = [
    { label: "Monthly Growth", value: `+${raw.kpis.monthlyGrowth}%`, icon: "growth" as const },
    { label: "Active Users", value: String(raw.kpis.activeUsers), icon: "users" as const },
    { label: "Revenue", value: raw.kpis.revenue, icon: "revenue" as const },
  ]

  // Policies
  const bdEntries = Object.entries(raw.policies.breakdown)
  const policies = {
    total: raw.policies.total,
    delta: raw.policies.growth,
    up: true,
    breakdown: bdEntries.map(([key, v]) => ({
      label: LABEL_MAP[key] ?? key,
      count: v.count,
      delta: v.growth,
      up: v.growth >= 0,
    })),
  }

  // Claims
  const claims = Object.entries(raw.claims).map(([key, v]) => ({
    label: LABEL_MAP[key] ?? key,
    percent: v.percentage,
    claims: v.count,
    color: "var(--chart-2)",
  }))

  // Partners
  const partnerLabels: Record<string, string> = {
    client: "Client",
    intermediary: "Intermediary",
    serviceProvider: "Service Provider",
    coInsurer: "Co-Insurer",
  }
  const partners = {
    total: raw.partners.total,
    bars: Object.entries(raw.partners.breakdown).map(([key, v]) => ({
      label: partnerLabels[key] ?? key,
      left: v.percentage,
      right: v.remaining,
    })),
  }

  // Debited
  const debitedLabels: Record<string, string> = { gc: "GC", gl: "GL", ol: "OL", pen: "PEN" }
  const debited = {
    total: raw.debited.total,
    gaugePercent: 68,
    segments: Object.entries(raw.debited.breakdown).map(([key, v]) => ({
      label: debitedLabels[key] ?? key,
      value: v.amount,
      color: v.color,
    })),
  }

  // Quotations
  const months = raw.quotations.data.map((d) => d.month)
  const seriesNames: { name: string; key: "ol" | "gl" | "gc" | "pen" }[] = [
    { name: "OL", key: "ol" },
    { name: "GL", key: "gl" },
    { name: "GC", key: "gc" },
    { name: "PEN", key: "pen" },
  ]
  const series = seriesNames.map((s) => ({
    name: s.name,
    color: CHART_COLORS[s.key] ?? "var(--chart-1)",
    points: raw.quotations.data.map((d) => d[s.key]),
  }))
  const legend = seriesNames.map((s) => {
    const leg = raw.quotations.legend[s.key]
    return { label: s.name, color: leg?.color ?? "var(--chart-1)", percent: leg?.percentage ?? 0, count: 0 }
  })
  const quotations = { total: raw.quotations.total, labels: months, series, legend }

  // Notifications
  const toneMap: Record<string, "warning" | "success" | "destructive" | "muted"> = {
    SUBMITTED: "warning",
    APPROVED: "success",
    REJECTED: "destructive",
    CANCELLED: "muted",
    PENDING: "warning",
    Under_Review: "warning",
    Pending_Documents: "warning",
    Compliance_Check: "warning",
    Suspended: "muted",
    Converted: "success",
  }
  const statuses = [
    { label: "Request", count: raw.notifications.request, tone: "warning" as const },
    { label: "Approved", count: raw.notifications.approved, tone: "success" as const },
    { label: "Rejected", count: raw.notifications.rejected, tone: "destructive" as const },
    { label: "Cancelled", count: raw.notifications.cancelled, tone: "muted" as const },
  ]
  const items = raw.notifications.notifications.map((n) => ({
    id: n.id,
    title: n.type,
    status: n.status,
    time: n.date,
    ...(n.amount ? { amount: n.amount } : {}),
  }))
  const notifications = { unread: raw.notifications.unreadCount, statuses, items }

  // Todos
  const todos = raw.todos.map((t) => ({ id: t.id, title: t.text, date: t.date }))

  // Leads
  const placeMap = ["st", "nd", "rd"]
  const leads = raw.leads.map((l) => ({
    rank: l.rank,
    place: `${l.rank}${placeMap[l.rank - 1] ?? "th"}`,
    name: l.name,
    amount: l.amount,
  }))

  return { hero, policies, claims, partners, debited, quotations, notifications, todos, leads }
}

export async function getDashboard(): Promise<DashboardData> {
  const res = await apiFetchAuth("/api/v1/dashboard/overview/")
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(extractError(res, body))
  }
  const raw = await res.json()
  return mapDashboard(raw)
}

// ============================================================================
// Interactive Dashboard Workspace API
// ============================================================================

async function dashboardRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await apiFetchAuth(path, init)
  const json = await res.json().catch(() => null)
  if (!res.ok) throw new Error(extractError(res, json))
  return ((json as Record<string, unknown>)?.data ?? json) as T
}

export async function searchDashboard(query: string, signal?: AbortSignal): Promise<GlobalSearchResult[]> {
  const params = new URLSearchParams({ q: query })
  const payload = await dashboardRequest<{ results: GlobalSearchResult[] }>(`/api/v1/dashboard/search/?${params}`, { signal })
  return payload.results ?? []
}

export async function listDashboardTasks(status?: string): Promise<DashboardTaskRecord[]> {
  const query = status ? `?status=${encodeURIComponent(status)}` : ""
  return dashboardRequest<DashboardTaskRecord[]>(`/api/v1/dashboard/tasks/${query}`)
}

export async function createDashboardTask(input: Partial<DashboardTaskRecord>): Promise<DashboardTaskRecord> {
  return dashboardRequest<DashboardTaskRecord>("/api/v1/dashboard/tasks/", {
    method: "POST",
    body: JSON.stringify(input),
  })
}

export async function updateDashboardTask(id: number, input: Partial<DashboardTaskRecord>): Promise<DashboardTaskRecord> {
  return dashboardRequest<DashboardTaskRecord>(`/api/v1/dashboard/tasks/${id}/`, {
    method: "PATCH",
    body: JSON.stringify(input),
  })
}

export async function deleteDashboardTask(id: number): Promise<void> {
  await dashboardRequest<null>(`/api/v1/dashboard/tasks/${id}/`, { method: "DELETE" })
}

export async function listDashboardAlerts(params: { severity?: string; status?: string } = {}): Promise<DashboardAlertRecord[]> {
  const search = new URLSearchParams()
  if (params.severity) search.set("severity", params.severity)
  if (params.status) search.set("status", params.status)
  const query = search.toString() ? `?${search}` : ""
  return dashboardRequest<DashboardAlertRecord[]>(`/api/v1/dashboard/alerts/${query}`)
}

export async function actOnDashboardAlert(id: number, action: "acknowledge" | "dismiss"): Promise<DashboardAlertRecord> {
  return dashboardRequest<DashboardAlertRecord>(`/api/v1/dashboard/alerts/${id}/${action}/`, { method: "POST" })
}

export async function listDashboardNotifications(unreadOnly = false): Promise<DashboardNotificationRecord[]> {
  return dashboardRequest<DashboardNotificationRecord[]>(`/api/v1/dashboard/notifications/${unreadOnly ? "?unread=true" : ""}`)
}

/**
 * Module feed for the top-bar bell: recent CommitmentOverdue outbox events with
 * deep links into the Commitments UI. Backed by the OL Commitments module.
 */
export async function listCommitmentOverdueNotifications(): Promise<DashboardNotificationRecord[]> {
  const res = await apiFetchAuth("/api/v1/ol-commitments/notifications/overdue/")
  const json = await res.json().catch(() => null)
  if (!res.ok) throw new Error(extractError(res, json))
  const record = json && typeof json === "object" ? (json as Record<string, unknown>) : {}
  const results = Array.isArray(record.results)
    ? record.results
    : record.data && typeof record.data === "object" && Array.isArray((record.data as { results?: unknown }).results)
      ? (record.data as { results: unknown[] }).results
      : []
  return results.map((raw) => {
    const item = raw && typeof raw === "object" ? (raw as Record<string, unknown>) : {}
    return {
      id: String(item.id ?? ""),
      kind: "ol-commitments",
      title: String(item.title ?? "Commitment overdue"),
      message: String(item.message ?? ""),
      status: "UNREAD",
      route: typeof item.deep_link === "string" ? item.deep_link : "/ordinary-life/commitments",
      entityType: "OLCommitment",
      entityId: String(item.id ?? ""),
      isRead: false,
      createdAt: String(item.created_at ?? item.createdAt ?? ""),
      deepLink: typeof item.deep_link === "string" ? item.deep_link : "/ordinary-life/commitments",
    }
  })
}

/**
 * Module feed for the top-bar bell: recent proposal lifecycle events
 * (payment ready, converted, expiring soon) with deep links into the
 * proposals UI. Backed by the OL Proposals module.
 */
export async function listProposalNotifications(): Promise<DashboardNotificationRecord[]> {
  const res = await apiFetchAuth("/api/v1/ol-proposals/proposals/notifications/")
  const json = await res.json().catch(() => null)
  if (!res.ok) throw new Error(extractError(res, json))
  const record = json && typeof json === "object" ? (json as Record<string, unknown>) : {}
  const results = Array.isArray(record.results)
    ? record.results
    : record.data && typeof record.data === "object" && Array.isArray((record.data as { results?: unknown }).results)
      ? (record.data as { results: unknown[] }).results
      : []
  return results.map((raw) => {
    const item = raw && typeof raw === "object" ? (raw as Record<string, unknown>) : {}
    return {
      id: String(item.id ?? ""),
      kind: "ol-proposals",
      title: String(item.title ?? "Proposal update"),
      message: String(item.message ?? ""),
      status: "UNREAD",
      route: typeof item.deep_link === "string" ? item.deep_link : "/ordinary-life/proposals",
      entityType: "OLProposal",
      entityId: String(item.id ?? ""),
      isRead: false,
      createdAt: String(item.created_at ?? item.createdAt ?? ""),
      deepLink: typeof item.deep_link === "string" ? item.deep_link : "/ordinary-life/proposals",
    }
  })
}

export async function markDashboardNotificationRead(id: number): Promise<DashboardNotificationRecord> {
  return dashboardRequest<DashboardNotificationRecord>(`/api/v1/dashboard/notifications/${id}/read/`, { method: "POST" })
}

export async function markAllDashboardNotificationsRead(): Promise<void> {
  await dashboardRequest<null>("/api/v1/dashboard/notifications/read-all/", { method: "POST" })
}

export async function listCurrencyPairs(): Promise<CurrencyPairRecord[]> {
  return dashboardRequest<CurrencyPairRecord[]>("/api/v1/dashboard/currencies/")
}

export async function addCurrencyPair(baseCurrency: string, quoteCurrency: string, targetRate?: string): Promise<CurrencyPairRecord> {
  return dashboardRequest<CurrencyPairRecord>("/api/v1/dashboard/currencies/", {
    method: "POST",
    body: JSON.stringify({ baseCurrency, quoteCurrency, targetRate }),
  })
}

export async function removeCurrencyPair(id: number): Promise<void> {
  await dashboardRequest<null>(`/api/v1/dashboard/currencies/${id}/`, { method: "DELETE" })
}

export async function refreshCurrencyPairs(): Promise<{ refreshed: string[]; errors: { pair: string; error: string }[] }> {
  return dashboardRequest<{ refreshed: string[]; errors: { pair: string; error: string }[] }>("/api/v1/dashboard/currencies/refresh/", { method: "POST" })
}

// ============================================================================
// Partner Onboarding API
// ============================================================================

import type {
  PartnerApplicationList,
  PartnerApplicationDetail,
  ApplicationDocument,
  ApplicationTask,
  ChoicesResponse,
  PaginatedResponse,
  ApplicationStatus,
  PartnerListItem,
  PartnerDetail,
  SetupSummary,
  ApplicationPartnerType,
  BulkUploadResult,
} from "./types"

const ONBOARDING = "/api/v1/onboarding"

// --- Helpers ---

async function apiPost(
  path: string,
  body?: Record<string, unknown>,
  signal?: AbortSignal,
): Promise<unknown> {
  const res = await apiFetchAuth(path, {
    method: "POST",
    body: body ? JSON.stringify(body) : undefined,
    signal,
  })
  const json = await res.json().catch(() => null)
  if (!res.ok) throw new Error(extractError(res, json))
  return (json as Record<string, unknown>)?.data ?? json
}

function qs(params: Record<string, string | number | undefined>): string {
  const entries = Object.entries(params).filter(([, v]) => v !== undefined && v !== "")
  if (!entries.length) return ""
  return "?" + new URLSearchParams(entries.map(([k, v]) => [k, String(v)])).toString()
}

// --- Applications ---

export async function listUnifiedRecords(
  params: {
    page?: number
    pageSize?: number
    search?: string
    application_status?: string
    kyc_status?: string
    partner_type?: string
    ordering?: string
  } = {}
): Promise<PaginatedResponse<UnifiedOnboardingRecord>> {
  const backendParams: Record<string, string | number | undefined> = {
    page: params.page,
    per_page: params.pageSize,
    search: params.search,
    application_status: params.application_status,
    kyc_status: params.kyc_status,
    partner_type: params.partner_type,
    ordering: params.ordering,
  }
  const res = await apiFetchAuth(`${ONBOARDING}/unified-records/${qs(backendParams)}`)
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(extractError(res, body))
  }
  const body = await res.json()
  return {
    results: body.data ?? body,
    count: body.pagination?.total ?? body.count ?? (body.data || body).length,
    next: body.pagination?.next ?? body.next ?? null,
    previous: body.pagination?.previous ?? body.previous ?? null,
  }
}

export interface ListApplicationsParams {
  page?: number
  pageSize?: number
  search?: string
  status?: ApplicationStatus
  partnerType?: string
  ordering?: string
}

export async function listApplications(
  params: ListApplicationsParams = {},
): Promise<PaginatedResponse<PartnerApplicationList>> {
  // Map frontend camelCase params → backend snake_case
  const backendParams: Record<string, string | number | undefined> = {
    page: params.page,
    per_page: params.pageSize,
    search: params.search,
    status: params.status,
    partner_type: params.partnerType,
    ordering: params.ordering,
  }
  const res = await apiFetchAuth(`${ONBOARDING}/applications/${qs(backendParams)}`)
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(extractError(res, body))
  }
  const body = await res.json()
  // Backend returns { data: [...], pagination: { total, ... } }
  // Frontend expects { results: [...], count: N }
  return {
    results: body.data ?? body,
    count: body.pagination?.total ?? (Array.isArray(body.data) ? body.data.length : 0),
    next: null,
    previous: null,
  }
}

export async function getPartner(id: string): Promise<PartnerDetail> {
  const res = await apiFetchAuth(`${PARTNERS_API}/${id}/`)
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(extractError(res, body))
  }
  const json = await res.json()
  return json.data ?? json
}

export async function activatePartner(id: string): Promise<PartnerDetail> {
  const res = await apiFetchAuth(`${PARTNERS_API}/${id}/activate/`, { method: "POST", body: JSON.stringify({}) })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(extractError(res, body))
  }
  const json = await res.json()
  return json.data ?? json
}

export async function deactivatePartner(id: string, reason = ""): Promise<PartnerDetail> {
  const res = await apiFetchAuth(`${PARTNERS_API}/${id}/deactivate/`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(extractError(res, body))
  }
  const json = await res.json()
  return json.data ?? json
}

export async function getAssignmentHistory(assignmentId: string): Promise<PartnerTypeAssignmentHistory[]> {
  const res = await apiFetchAuth(`${PARTNERS_API}/assignments/${assignmentId}/history/`)
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(extractError(res, body))
  }
  const json = await res.json()
  const rows = Array.isArray(json.data) ? json.data : (Array.isArray(json) ? json : [])
  return rows.map((row: Record<string, unknown>) => ({
    id: String(row.id ?? ""),
    assignment: String(row.assignment ?? assignmentId),
    previousStatus: String(row.previous_status ?? row.previousStatus ?? ""),
    newStatus: String(row.new_status ?? row.newStatus ?? row.action ?? ""),
    reason: String(row.reason ?? ""),
    changedBy: row.changed_by ? String(row.changed_by) : null,
    changedByEmail: row.changed_by_email ? String(row.changed_by_email) : null,
    changedByName: row.changed_by_name ? String(row.changed_by_name) : (row.actor_name ? String(row.actor_name) : null),
    changedAt: String(row.changed_at ?? row.created_at ?? ""),
    eventType: row.event_type === "AUDIT" ? "AUDIT" : "STATUS",
    action: row.action ? String(row.action) : undefined,
    description: row.description ? String(row.description) : undefined,
    actorName: row.actor_name ? String(row.actor_name) : null,
    createdAt: row.created_at ? String(row.created_at) : undefined,
    entityType: row.entity_type ? String(row.entity_type) : undefined,
    objectId: row.object_id ? String(row.object_id) : undefined,
    changedFields: Array.isArray(row.changed_fields) ? row.changed_fields.map(String) : undefined,
    beforeState: (row.before_state as Record<string, unknown> | null | undefined) ?? null,
    afterState: (row.after_state as Record<string, unknown> | null | undefined) ?? null,
    sourceChannel: row.source_channel ? String(row.source_channel) : undefined,
  }))
}

export async function activateAssignment(assignmentId: string, reason = ""): Promise<PartnerTypeAssignment> {
  const res = await apiFetchAuth(`${PARTNERS_API}/assignments/${assignmentId}/activate/`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(extractError(res, body))
  }
  const json = await res.json()
  return json.data ?? json
}

export async function deactivateAssignment(assignmentId: string, reason = ""): Promise<PartnerTypeAssignment> {
  const res = await apiFetchAuth(`${PARTNERS_API}/assignments/${assignmentId}/deactivate/`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(extractError(res, body))
  }
  const json = await res.json()
  return json.data ?? json
}

export async function getAssignmentSetupSummary(assignmentId: string): Promise<SetupSummary> {
  const res = await apiFetchAuth(`${PARTNERS_API}/assignments/${assignmentId}/setup/summary/`)
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(extractError(res, body))
  }
  const json = await res.json()
  return json.data ?? json
}

export async function updatePartner(id: string, data: Record<string, unknown>): Promise<PartnerDetail> {
  const res = await apiFetchAuth(`${PARTNERS_API}/${id}/`, {
    method: "PATCH",
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(extractError(res, body))
  }
  const json = await res.json()
  return json.data ?? json
}

export async function updateIndividualProfile(id: string, data: Record<string, unknown>): Promise<Record<string, unknown>> {
  const res = await apiFetchAuth(`${PARTNERS_API}/${id}/individual-profile/`, {
    method: "PATCH",
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(extractError(res, body))
  }
  const json = await res.json()
  return json.data ?? json
}

export async function updateCorporateProfile(id: string, data: Record<string, unknown>): Promise<Record<string, unknown>> {
  const res = await apiFetchAuth(`${PARTNERS_API}/${id}/corporate-profile/`, {
    method: "PATCH",
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(extractError(res, body))
  }
  const json = await res.json()
  return json.data ?? json
}

export async function assignPartnerType(id: string, data: {
  partner_type: string
  branches?: string[]
  location?: string | null
  share_data_externally?: boolean
  effective_date?: string | null
}): Promise<Record<string, unknown>> {
  const res = await apiFetchAuth(`${PARTNERS_API}/${id}/assign-type/`, {
    method: "POST",
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(extractError(res, body))
  }
  const json = await res.json()
  return json.data ?? json
}

export async function updatePartnerTypeAssignment(
  partnerId: string,
  assignmentId: string,
  data: {
    partner_type: string
    branches?: string[]
    location?: string | null
    share_data_externally?: boolean
    effective_date?: string | null
  },
): Promise<PartnerTypeAssignment> {
  const res = await apiFetchAuth(`${PARTNERS_API}/${partnerId}/assignments/${assignmentId}/`, {
    method: "PATCH",
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(extractError(res, body))
  }
  const json = await res.json()
  return json.data ?? json
}

export async function listPartners(
  params: { page?: number; per_page?: number; search?: string } = {},
): Promise<PaginatedResponse<PartnerListItem>> {
  const q = new URLSearchParams()
  if (params.page) q.set("page", String(params.page))
  if (params.per_page) q.set("per_page", String(params.per_page))
  if (params.search) q.set("search", params.search)
  const res = await apiFetchAuth(`${PARTNERS_API}/?${q}`)
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(extractError(res, body))
  }
  const body = await res.json()
  return {
    results: body.data ?? body,
    count: body.pagination?.total ?? (Array.isArray(body.data) ? body.data.length : 0),
    next: null,
    previous: null,
  }
}

export async function getApplication(id: string): Promise<PartnerApplicationDetail> {
  const res = await apiFetchAuth(`${ONBOARDING}/applications/${id}/`)
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(extractError(res, body))
  }
  return (await res.json()).data
}

export async function createApplication(
  data: Record<string, unknown>,
): Promise<PartnerApplicationDetail> {
  return (await apiPost(`${ONBOARDING}/applications/`, data)) as PartnerApplicationDetail
}

export async function updateApplication(
  id: string,
  data: Record<string, unknown>,
): Promise<PartnerApplicationDetail> {
  const res = await apiFetchAuth(`${ONBOARDING}/applications/${id}/`, {
    method: "PATCH",
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(extractError(res, body))
  }
  return (await res.json()).data
}

export async function listApplicationPartnerTypes(applicationId: string): Promise<ApplicationPartnerType[]> {
  const res = await apiFetchAuth(`${ONBOARDING}/applications/${applicationId}/partner-types/`)
  if (!res.ok) throw new Error("Failed to load application partner types")
  const json = await res.json()
  return Array.isArray(json.data) ? json.data : (Array.isArray(json) ? json : [])
}

export async function createApplicationPartnerType(applicationId: string, data: {
  partner_type: string
  branches?: string[]
  region?: string
  share_data_externally?: boolean
}): Promise<ApplicationPartnerType[]> {
  const res = await apiFetchAuth(`${ONBOARDING}/applications/${applicationId}/partner-types/`, {
    method: "POST",
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(extractError(res, body))
  }
  const json = await res.json()
  return Array.isArray(json.data) ? json.data : [json.data]
}

export async function deleteApplicationPartnerType(applicationId: string, ptId: string): Promise<void> {
  const res = await apiFetchAuth(`${ONBOARDING}/applications/${applicationId}/partner-types/${ptId}/`, {
    method: "DELETE",
  })
  if (!res.ok) throw new Error("Failed to delete application partner type")
}

export async function downloadTemplate(partnerType: string): Promise<Blob> {
  const token = getAccessToken()
  const headers: Record<string, string> = {}
  if (token) headers["Authorization"] = `Bearer ${token}`
  const res = await fetch(
    `${API_BASE}${ONBOARDING}/applications/bulk-upload/template/?partner_type=${partnerType}`,
    { headers },
  )
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(extractError(res, body))
  }
  return res.blob()
}

export async function bulkUploadPartners(file: File): Promise<BulkUploadResult> {
  const formData = new FormData()
  formData.append("file", file)

  const headers = new Headers()
  const token = getAccessToken()
  if (token) headers.set("Authorization", `Bearer ${token}`)

  const res = await fetch(
    `${API_BASE}${ONBOARDING}/applications/bulk-upload/`,
    { method: "POST", headers, body: formData },
  )
  const json = await res.json().catch(() => null)
  if (!res.ok) throw new Error(extractError(res, json))
  return ((json as Record<string, unknown>)?.data ?? json) as BulkUploadResult
}

export async function deleteApplication(id: string): Promise<void> {
  const res = await apiFetchAuth(`${ONBOARDING}/applications/${id}/`, { method: "DELETE" })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(extractError(res, body))
  }
}

// --- State transitions ---

export async function submitApplication(id: string): Promise<PartnerApplicationDetail> {
  return (await apiPost(`${ONBOARDING}/applications/${id}/submit/`)) as PartnerApplicationDetail
}

export async function startReview(id: string): Promise<PartnerApplicationDetail> {
  return (await apiPost(`${ONBOARDING}/applications/${id}/start-review/`)) as PartnerApplicationDetail
}

export async function requestDocuments(
  id: string,
  requestedDocuments: string[],
): Promise<PartnerApplicationDetail> {
  return (await apiPost(`${ONBOARDING}/applications/${id}/request-documents/`, {
    requested_documents: requestedDocuments,
  })) as PartnerApplicationDetail
}

export async function sendToCompliance(
  id: string,
  notes?: string,
): Promise<PartnerApplicationDetail> {
  return (await apiPost(`${ONBOARDING}/applications/${id}/send-to-compliance/`, {
    ...(notes ? { notes } : {}),
  })) as PartnerApplicationDetail
}

export async function approveApplication(
  id: string,
  notes?: string,
): Promise<PartnerApplicationDetail> {
  return (await apiPost(`${ONBOARDING}/applications/${id}/approve/`, {
    ...(notes ? { notes } : {}),
  })) as PartnerApplicationDetail
}

export async function rejectApplication(
  id: string,
  reason: string,
  notes?: string,
): Promise<PartnerApplicationDetail> {
  return (await apiPost(`${ONBOARDING}/applications/${id}/reject/`, {
    rejection_reason: reason,
    ...(notes ? { notes } : {}),
  })) as PartnerApplicationDetail
}

export async function suspendApplication(
  id: string,
  notes?: string,
): Promise<PartnerApplicationDetail> {
  return (await apiPost(`${ONBOARDING}/applications/${id}/suspend/`, {
    ...(notes ? { notes } : {}),
  })) as PartnerApplicationDetail
}

export async function resumeApplication(id: string): Promise<PartnerApplicationDetail> {
  return (await apiPost(`${ONBOARDING}/applications/${id}/resume/`)) as PartnerApplicationDetail
}

export async function convertApplication(id: string): Promise<PartnerApplicationDetail> {
  return (await apiPost(`${ONBOARDING}/applications/${id}/convert/`)) as PartnerApplicationDetail
}

export async function runCompliance(id: string): Promise<{
  riskScore: number
  threshold: number
  isHighRisk: boolean
}> {
  return (await apiPost(`${ONBOARDING}/applications/${id}/run-compliance/`)) as {
    riskScore: number
    threshold: number
    isHighRisk: boolean
  }
}

// --- Documents ---

export async function listDocuments(
  applicationId: string,
): Promise<ApplicationDocument[]> {
  const res = await apiFetchAuth(`${ONBOARDING}/applications/${applicationId}/documents/`)
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(extractError(res, body))
  }
  const json = await res.json()
  // paginated or plain array
  return json.results ?? json.data ?? json
}

export async function uploadDocument(
  applicationId: string,
  file: File,
  documentType: string,
  documentName?: string,
  applicationPartnerTypeId?: string,
): Promise<ApplicationDocument> {
  const formData = new FormData()
  formData.append("file", file)
  formData.append("document_type", documentType)
  formData.append("document_name", documentName || file.name)
  if (applicationPartnerTypeId) formData.append("application_partner_type", applicationPartnerTypeId)

  const headers = new Headers()
  const token = getAccessToken()
  if (token) headers.set("Authorization", `Bearer ${token}`)

  const res = await fetch(
    `${API_BASE}${ONBOARDING}/applications/${applicationId}/documents/`,
    { method: "POST", headers, body: formData },
  )
  const json = await res.json().catch(() => null)
  if (!res.ok) throw new Error(extractError(res, json))
  return (json as Record<string, unknown>)?.data ?? json
}

export async function deleteDocument(
  applicationId: string,
  documentId: string,
): Promise<void> {
  const res = await apiFetchAuth(
    `${ONBOARDING}/applications/${applicationId}/documents/${documentId}/`,
    { method: "DELETE" },
  )
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(extractError(res, body))
  }
}

export async function verifyDocument(
  applicationId: string,
  documentId: string,
  notes?: string,
): Promise<ApplicationDocument> {
  return (await apiPost(
    `${ONBOARDING}/applications/${applicationId}/documents/${documentId}/verify/`,
    notes ? { verification_notes: notes } : undefined,
  )) as ApplicationDocument
}

// --- Tasks ---

export async function listTasks(applicationId: string): Promise<ApplicationTask[]> {
  const res = await apiFetchAuth(`${ONBOARDING}/applications/${applicationId}/tasks/`)
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(extractError(res, body))
  }
  const json = await res.json()
  return json.results ?? json.data ?? json
}

export async function createTask(
  applicationId: string,
  data: {
    taskType: string
    title: string
    description?: string
    assignedTo?: string
    priority?: string
    dueDate?: string
  },
): Promise<ApplicationTask> {
  return (await apiPost(`${ONBOARDING}/applications/${applicationId}/tasks/`, {
    task_type: data.taskType,
    title: data.title,
    ...(data.description ? { description: data.description } : {}),
    ...(data.assignedTo ? { assigned_to: data.assignedTo } : {}),
    ...(data.priority ? { priority: data.priority } : {}),
    ...(data.dueDate ? { due_date: data.dueDate } : {}),
  })) as ApplicationTask
}

export async function updateTask(
  applicationId: string,
  taskId: string,
  data: Partial<{
    taskType: string
    title: string
    description: string
    assignedTo: string
    status: string
    priority: string
    dueDate: string
    notes: string
  }>,
): Promise<ApplicationTask> {
  const body: Record<string, unknown> = {}
  if (data.taskType) body.task_type = data.taskType
  if (data.title) body.title = data.title
  if (data.description !== undefined) body.description = data.description
  if (data.assignedTo !== undefined) body.assigned_to = data.assignedTo
  if (data.status) body.status = data.status
  if (data.priority) body.priority = data.priority
  if (data.dueDate !== undefined) body.due_date = data.dueDate
  if (data.notes !== undefined) body.notes = data.notes

  const res = await apiFetchAuth(
    `${ONBOARDING}/applications/${applicationId}/tasks/${taskId}/`,
    { method: "PATCH", body: JSON.stringify(body) },
  )
  if (!res.ok) {
    const json = await res.json().catch(() => null)
    throw new Error(extractError(res, json))
  }
  return (await res.json()).data
}

export async function completeTask(
  applicationId: string,
  taskId: string,
  notes?: string,
): Promise<ApplicationTask> {
  return (await apiPost(
    `${ONBOARDING}/applications/${applicationId}/tasks/${taskId}/complete/`,
    notes ? { notes } : undefined,
  )) as ApplicationTask
}

export async function deleteTask(
  applicationId: string,
  taskId: string,
): Promise<void> {
  const res = await apiFetchAuth(
    `${ONBOARDING}/applications/${applicationId}/tasks/${taskId}/`,
    { method: "DELETE" },
  )
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(extractError(res, body))
  }
}

// --- Choices ---

export async function getChoices(): Promise<ChoicesResponse> {
  const res = await apiFetchAuth(`${ONBOARDING}/choices/`)
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(extractError(res, body))
  }
  return (await res.json()).data
}

// --- Application Partner Types ---

export async function listPartnerTypes(applicationId: string): Promise<ApplicationPartnerType[]> {
  const res = await apiFetchAuth(`${ONBOARDING}/applications/${applicationId}/partner-types/`)
  if (!res.ok) throw new Error("Failed to load partner types")
  return (await res.json()).data
}

export async function createPartnerType(
  applicationId: string,
  data: { partner_type: string; branches?: string[]; region?: string; location?: string | null; share_data_externally?: boolean }
): Promise<ApplicationPartnerType[]> {
  const res = await apiFetchAuth(`${ONBOARDING}/applications/${applicationId}/partner-types/`, {
    method: "POST",
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error("Failed to add partner type")
  return (await res.json()).data
}

export async function updatePartnerType(
  applicationId: string,
  id: string,
  data: Partial<{
    branch: string | null
    location: string | null
    region: string
    share_data_externally: boolean
  }>,
): Promise<ApplicationPartnerType> {
  const res = await apiFetchAuth(`${ONBOARDING}/applications/${applicationId}/partner-types/${id}/`, {
    method: "PATCH",
    body: JSON.stringify(data),
  })
  const json = await res.json().catch(() => null)
  if (!res.ok) throw new Error(extractError(res, json))
  return ((json as Record<string, unknown>)?.data ?? json) as ApplicationPartnerType
}

export async function deletePartnerType(applicationId: string, id: string): Promise<void> {
  const res = await apiFetchAuth(`${ONBOARDING}/applications/${applicationId}/partner-types/${id}/`, {
    method: "DELETE",
  })
  if (!res.ok) throw new Error("Failed to delete partner type")
}

// --- Application Contacts ---

export async function listContacts(applicationId: string): Promise<ApplicationContact[]> {
  const res = await apiFetchAuth(`${ONBOARDING}/applications/${applicationId}/contacts/`)
  if (!res.ok) throw new Error("Failed to load contacts")
  const json = await res.json()
  return json.data ?? json
}

export async function createContact(
  applicationId: string,
  data: Partial<ApplicationContact> | Record<string, unknown>
): Promise<ApplicationContact> {
  const res = await apiFetchAuth(`${ONBOARDING}/applications/${applicationId}/contacts/`, {
    method: "POST",
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error("Failed to create contact")
  const json = await res.json()
  return json.data ?? json
}

export async function deleteContact(applicationId: string, id: string): Promise<void> {
  const res = await apiFetchAuth(`${ONBOARDING}/applications/${applicationId}/contacts/${id}/`, {
    method: "DELETE",
  })
  if (!res.ok) throw new Error("Failed to delete contact")
}

// --- Application Bank Accounts ---

export async function listBankAccounts(applicationId: string): Promise<ApplicationBankAccount[]> {
  const res = await apiFetchAuth(`${ONBOARDING}/applications/${applicationId}/bank-accounts/`)
  if (!res.ok) throw new Error("Failed to load bank accounts")
  const json = await res.json()
  return json.data ?? json
}

export async function createBankAccount(
  applicationId: string,
  data: Partial<ApplicationBankAccount> | Record<string, unknown>
): Promise<ApplicationBankAccount> {
  const res = await apiFetchAuth(`${ONBOARDING}/applications/${applicationId}/bank-accounts/`, {
    method: "POST",
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error("Failed to create bank account")
  const json = await res.json()
  return json.data ?? json
}

export async function deleteBankAccount(applicationId: string, id: string): Promise<void> {
  const res = await apiFetchAuth(`${ONBOARDING}/applications/${applicationId}/bank-accounts/${id}/`, {
    method: "DELETE",
  })
  if (!res.ok) throw new Error("Failed to delete bank account")
}

// ---------------------------------------------------------------------------
// Application Field Values API
// ---------------------------------------------------------------------------

export async function listFieldValues(applicationId: string): Promise<ApplicationFieldValue[]> {
  const res = await apiFetchAuth(`${ONBOARDING}/applications/${applicationId}/field-values/`)
  if (!res.ok) throw new Error("Failed to load field values")
  return (await res.json()).data
}

export async function batchUpdateFieldValues(
  applicationId: string,
  data: { field_config: string; value_json: Record<string, unknown> }[]
): Promise<ApplicationFieldValue[]> {
  const res = await apiFetchAuth(`${ONBOARDING}/applications/${applicationId}/field-values/batch/`, {
    method: "PATCH",
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error("Failed to save field values")
  return (await res.json()).data
}

// ---------------------------------------------------------------------------
// Partner Types / Branches / Locations CRUD API
// ---------------------------------------------------------------------------

const PARTNERS_API = "/api/v1/partners"
const ONBOARDING_API = "/api/v1/onboarding"

export async function fetchPartnerTypes(): Promise<PartnerTypeRecord[]> {
  const res = await apiFetchAuth(`${PARTNERS_API}/types/`)
  if (!res.ok) throw new Error("Failed to fetch partner types")
  return extractList<PartnerTypeRecord>(res)
}

export async function fetchPartnerType(id: string): Promise<PartnerTypeRecord> {
  const res = await apiFetchAuth(`${PARTNERS_API}/types/${id}/`)
  if (!res.ok) throw new Error("Failed to fetch partner type")
  return extractOne<PartnerTypeRecord>(res)
}

export async function createPartnerTypeRecord(data: Partial<PartnerTypeRecord>): Promise<PartnerTypeRecord> {
  const res = await apiFetchAuth(`${PARTNERS_API}/types/`, {
    method: "POST",
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(extractError(res, body))
  }
  return res.json()
}

export async function updatePartnerTypeRecord(id: string, data: Partial<PartnerTypeRecord>): Promise<PartnerTypeRecord> {
  const res = await apiFetchAuth(`${PARTNERS_API}/types/${id}/`, {
    method: "PATCH",
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(extractError(res, body))
  }
  return res.json()
}

export async function deletePartnerTypeRecord(id: string): Promise<void> {
  const res = await apiFetchAuth(`${PARTNERS_API}/types/${id}/`, { method: "DELETE" })
  if (!res.ok) throw new Error("Failed to delete partner type")
}

// --- Partner Type Document Requirements ---

export async function fetchDocumentRequirements(partnerTypeId: string): Promise<PartnerTypeDocumentRequirement[]> {
  const res = await apiFetchAuth(`${PARTNERS_API}/types/${partnerTypeId}/documents/`)
  if (!res.ok) throw new Error("Failed to fetch document requirements")
  return extractList<PartnerTypeDocumentRequirement>(res)
}

export async function fetchAllDocumentRequirements(): Promise<PartnerTypeDocumentRequirement[]> {
  const types = await fetchPartnerTypes()
  const results = await Promise.all(
    types.map((t) => fetchDocumentRequirements(t.id).catch(() => [] as PartnerTypeDocumentRequirement[])),
  )
  return results.flat()
}

export async function createDocumentRequirement(
  partnerTypeId: string,
  data: Partial<PartnerTypeDocumentRequirement>,
): Promise<PartnerTypeDocumentRequirement> {
  const res = await apiFetchAuth(`${PARTNERS_API}/types/${partnerTypeId}/documents/`, {
    method: "POST",
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(extractError(res, body))
  }
  return res.json()
}

export async function updateDocumentRequirement(
  partnerTypeId: string,
  id: string,
  data: Partial<PartnerTypeDocumentRequirement>,
): Promise<PartnerTypeDocumentRequirement> {
  const res = await apiFetchAuth(`${PARTNERS_API}/types/${partnerTypeId}/documents/${id}/`, {
    method: "PATCH",
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(extractError(res, body))
  }
  return res.json()
}

export async function deleteDocumentRequirement(partnerTypeId: string, id: string): Promise<void> {
  const res = await apiFetchAuth(`${PARTNERS_API}/types/${partnerTypeId}/documents/${id}/`, { method: "DELETE" })
  if (!res.ok) throw new Error("Failed to delete document requirement")
}

// --- Partner Type Config Requirements (fields, contacts, banks) ---

export async function fetchFieldConfigurations(partnerTypeId: string): Promise<PartnerTypeFieldConfiguration[]> {
  const res = await apiFetchAuth(`${PARTNERS_API}/types/${partnerTypeId}/fields/`)
  if (!res.ok) throw new Error("Failed to fetch field configurations")
  return extractList<PartnerTypeFieldConfiguration>(res)
}

export async function createFieldConfiguration(
  partnerTypeId: string,
  data: Partial<PartnerTypeFieldConfiguration>,
): Promise<PartnerTypeFieldConfiguration> {
  const res = await apiFetchAuth(`${PARTNERS_API}/types/${partnerTypeId}/fields/`, {
    method: "POST",
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(extractError(res, body))
  }
  return res.json()
}

export async function updateFieldConfiguration(
  partnerTypeId: string,
  id: string,
  data: Partial<PartnerTypeFieldConfiguration>,
): Promise<PartnerTypeFieldConfiguration> {
  const res = await apiFetchAuth(`${PARTNERS_API}/types/${partnerTypeId}/fields/${id}/`, {
    method: "PATCH",
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(extractError(res, body))
  }
  return res.json()
}

export async function deleteFieldConfiguration(partnerTypeId: string, id: string): Promise<void> {
  const res = await apiFetchAuth(`${PARTNERS_API}/types/${partnerTypeId}/fields/${id}/`, { method: "DELETE" })
  if (!res.ok) throw new Error("Failed to delete field configuration")
}

export async function fetchAllFieldConfigurations(): Promise<PartnerTypeFieldConfiguration[]> {
  const types = await fetchPartnerTypes()
  const results = await Promise.all(
    types.map((t) => fetchFieldConfigurations(t.id).catch(() => [] as PartnerTypeFieldConfiguration[])),
  )
  return results.flat()
}

// --- Contact Requirements ---

export async function fetchContactRequirements(partnerTypeId: string): Promise<PartnerTypeContactRequirement[]> {
  const res = await apiFetchAuth(`${PARTNERS_API}/types/${partnerTypeId}/contacts/`)
  if (!res.ok) throw new Error("Failed to fetch contact requirements")
  return extractList<PartnerTypeContactRequirement>(res)
}

export async function createContactRequirement(
  partnerTypeId: string,
  data: Partial<PartnerTypeContactRequirement>,
): Promise<PartnerTypeContactRequirement> {
  const res = await apiFetchAuth(`${PARTNERS_API}/types/${partnerTypeId}/contacts/`, {
    method: "POST",
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(extractError(res, body))
  }
  return res.json()
}

export async function updateContactRequirement(
  partnerTypeId: string,
  id: string,
  data: Partial<PartnerTypeContactRequirement>,
): Promise<PartnerTypeContactRequirement> {
  const res = await apiFetchAuth(`${PARTNERS_API}/types/${partnerTypeId}/contacts/${id}/`, {
    method: "PATCH",
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(extractError(res, body))
  }
  return res.json()
}

export async function deleteContactRequirement(partnerTypeId: string, id: string): Promise<void> {
  const res = await apiFetchAuth(`${PARTNERS_API}/types/${partnerTypeId}/contacts/${id}/`, { method: "DELETE" })
  if (!res.ok) throw new Error("Failed to delete contact requirement")
}

export async function fetchAllContactRequirements(): Promise<PartnerTypeContactRequirement[]> {
  const types = await fetchPartnerTypes()
  const results = await Promise.all(
    types.map((t) => fetchContactRequirements(t.id).catch(() => [] as PartnerTypeContactRequirement[])),
  )
  return results.flat()
}

// --- Bank Requirements ---

export async function fetchBankRequirements(partnerTypeId: string): Promise<PartnerTypeBankRequirement[]> {
  const res = await apiFetchAuth(`${PARTNERS_API}/types/${partnerTypeId}/banks/`)
  if (!res.ok) throw new Error("Failed to fetch bank requirements")
  return extractList<PartnerTypeBankRequirement>(res)
}

export async function createBankRequirement(
  partnerTypeId: string,
  data: Partial<PartnerTypeBankRequirement>,
): Promise<PartnerTypeBankRequirement> {
  const res = await apiFetchAuth(`${PARTNERS_API}/types/${partnerTypeId}/banks/`, {
    method: "POST",
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(extractError(res, body))
  }
  return res.json()
}

export async function updateBankRequirement(
  partnerTypeId: string,
  id: string,
  data: Partial<PartnerTypeBankRequirement>,
): Promise<PartnerTypeBankRequirement> {
  const res = await apiFetchAuth(`${PARTNERS_API}/types/${partnerTypeId}/banks/${id}/`, {
    method: "PATCH",
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(extractError(res, body))
  }
  return res.json()
}

export async function deleteBankRequirement(partnerTypeId: string, id: string): Promise<void> {
  const res = await apiFetchAuth(`${PARTNERS_API}/types/${partnerTypeId}/banks/${id}/`, { method: "DELETE" })
  if (!res.ok) throw new Error("Failed to delete bank requirement")
}

export async function fetchAllBankRequirements(): Promise<PartnerTypeBankRequirement[]> {
  const types = await fetchPartnerTypes()
  const results = await Promise.all(
    types.map((t) => fetchBankRequirements(t.id).catch(() => [] as PartnerTypeBankRequirement[])),
  )
  return results.flat()
}

// ============================================================================
// Partner Assignment Setup CRUD
// ============================================================================

// --- Documents ---

export async function getAssignmentDocuments(assignmentId: string): Promise<PartnerDocument[]> {
  const res = await apiFetchAuth(`${PARTNERS_API}/assignments/${assignmentId}/setup/documents/`)
  if (!res.ok) throw new Error("Failed to fetch documents")
  return extractList<PartnerDocument>(res)
}

export async function createAssignmentDocument(
  assignmentId: string,
  data: Record<string, unknown>,
): Promise<PartnerDocument> {
  const res = await apiFetchAuth(`${PARTNERS_API}/assignments/${assignmentId}/setup/documents/`, {
    method: "POST",
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(extractError(res, body))
  }
  const json = await res.json()
  return json.data ?? json
}

export async function uploadAssignmentDocumentFile(
  assignmentId: string,
  documentRequirementId: string,
  file: File,
): Promise<PartnerDocument> {
  const formData = new FormData()
  formData.append("document_requirement", documentRequirementId)
  formData.append("file", file)
  const headers = new Headers()
  const token = sessionStorage.getItem("aims_access_token")
  if (token) headers.set("Authorization", `Bearer ${token}`)
  const res = await fetch(`${API_BASE}${PARTNERS_API}/assignments/${assignmentId}/setup/documents/`, {
    method: "POST",
    headers,
    body: formData,
  })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(extractError(res, body))
  }
  const json = await res.json()
  return json.data ?? json
}

export async function updateAssignmentDocument(
  assignmentId: string,
  docId: string,
  data: Record<string, unknown>,
): Promise<PartnerDocument> {
  const res = await apiFetchAuth(`${PARTNERS_API}/assignments/${assignmentId}/setup/documents/${docId}/`, {
    method: "PATCH",
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(extractError(res, body))
  }
  const json = await res.json()
  return json.data ?? json
}

export async function deleteAssignmentDocument(assignmentId: string, docId: string): Promise<void> {
  const res = await apiFetchAuth(`${PARTNERS_API}/assignments/${assignmentId}/setup/documents/${docId}/`, {
    method: "DELETE",
  })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(extractError(res, body))
  }
}

// --- Application partner-type scoped setup ---

function scopedPartnerTypeSetupPath(applicationId: string, partnerTypeId: string, resource: string, id?: string) {
  return `${ONBOARDING}/applications/${applicationId}/partner-types/${partnerTypeId}/setup/${resource}/${id ? `${id}/` : ""}`
}

export async function getApplicationPartnerTypeFieldValues(
  applicationId: string,
  partnerTypeId: string,
): Promise<ApplicationFieldValue[]> {
  const res = await apiFetchAuth(scopedPartnerTypeSetupPath(applicationId, partnerTypeId, "field-values"))
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(extractError(res, body) || "Failed to fetch configured field values")
  }
  return extractList<ApplicationFieldValue>(res)
}

export async function updateApplicationPartnerTypeFieldValues(
  applicationId: string,
  partnerTypeId: string,
  data: Record<string, unknown>[],
): Promise<ApplicationFieldValue[]> {
  const res = await apiFetchAuth(scopedPartnerTypeSetupPath(applicationId, partnerTypeId, "field-values"), {
    method: "PATCH",
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(extractError(res, body))
  }
  const json = await res.json()
  return Array.isArray(json.data) ? json.data : (Array.isArray(json) ? json : [])
}

export async function getApplicationPartnerTypeContacts(
  applicationId: string,
  partnerTypeId: string,
): Promise<ApplicationContact[]> {
  const res = await apiFetchAuth(scopedPartnerTypeSetupPath(applicationId, partnerTypeId, "contacts"))
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(extractError(res, body) || "Failed to fetch configured contacts")
  }
  return extractList<ApplicationContact>(res)
}

export async function createApplicationPartnerTypeContact(
  applicationId: string,
  partnerTypeId: string,
  data: Record<string, unknown>,
): Promise<ApplicationContact> {
  const res = await apiFetchAuth(scopedPartnerTypeSetupPath(applicationId, partnerTypeId, "contacts"), {
    method: "POST",
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(extractError(res, body))
  }
  const json = await res.json()
  return json.data ?? json
}

export async function updateApplicationPartnerTypeContact(
  applicationId: string,
  partnerTypeId: string,
  contactId: string,
  data: Record<string, unknown>,
): Promise<ApplicationContact> {
  const res = await apiFetchAuth(scopedPartnerTypeSetupPath(applicationId, partnerTypeId, "contacts", contactId), {
    method: "PATCH",
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(extractError(res, body))
  }
  const json = await res.json()
  return json.data ?? json
}

export async function deleteApplicationPartnerTypeContact(
  applicationId: string,
  partnerTypeId: string,
  contactId: string,
): Promise<void> {
  const res = await apiFetchAuth(scopedPartnerTypeSetupPath(applicationId, partnerTypeId, "contacts", contactId), { method: "DELETE" })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(extractError(res, body))
  }
}

export async function getApplicationPartnerTypeBankAccounts(
  applicationId: string,
  partnerTypeId: string,
): Promise<ApplicationBankAccount[]> {
  const res = await apiFetchAuth(scopedPartnerTypeSetupPath(applicationId, partnerTypeId, "bank-accounts"))
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(extractError(res, body) || "Failed to fetch configured bank accounts")
  }
  return extractList<ApplicationBankAccount>(res)
}

export async function createApplicationPartnerTypeBankAccount(
  applicationId: string,
  partnerTypeId: string,
  data: Record<string, unknown>,
): Promise<ApplicationBankAccount> {
  const res = await apiFetchAuth(scopedPartnerTypeSetupPath(applicationId, partnerTypeId, "bank-accounts"), {
    method: "POST",
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(extractError(res, body))
  }
  const json = await res.json()
  return json.data ?? json
}

export async function updateApplicationPartnerTypeBankAccount(
  applicationId: string,
  partnerTypeId: string,
  bankId: string,
  data: Record<string, unknown>,
): Promise<ApplicationBankAccount> {
  const res = await apiFetchAuth(scopedPartnerTypeSetupPath(applicationId, partnerTypeId, "bank-accounts", bankId), {
    method: "PATCH",
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(extractError(res, body))
  }
  const json = await res.json()
  return json.data ?? json
}

export async function deleteApplicationPartnerTypeBankAccount(
  applicationId: string,
  partnerTypeId: string,
  bankId: string,
): Promise<void> {
  const res = await apiFetchAuth(scopedPartnerTypeSetupPath(applicationId, partnerTypeId, "bank-accounts", bankId), { method: "DELETE" })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(extractError(res, body))
  }
}

// --- Field Values ---

export async function getAssignmentFieldValues(assignmentId: string): Promise<PartnerDynamicFieldValue[]> {
  const res = await apiFetchAuth(`${PARTNERS_API}/assignments/${assignmentId}/setup/field-values/`)
  if (!res.ok) throw new Error("Failed to fetch field values")
  return extractList<PartnerDynamicFieldValue>(res)
}

export async function updateAssignmentFieldValues(
  assignmentId: string,
  data: Record<string, unknown>[],
): Promise<PartnerDynamicFieldValue[]> {
  const res = await apiFetchAuth(`${PARTNERS_API}/assignments/${assignmentId}/setup/field-values/`, {
    method: "PATCH",
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(extractError(res, body))
  }
  const json = await res.json()
  return json.data ?? json
}

// --- Contacts ---

export async function getAssignmentContacts(assignmentId: string): Promise<PartnerAssignmentContact[]> {
  const res = await apiFetchAuth(`${PARTNERS_API}/assignments/${assignmentId}/setup/contacts/`)
  if (!res.ok) throw new Error("Failed to fetch contacts")
  return extractList<PartnerAssignmentContact>(res)
}

export async function createAssignmentContact(
  assignmentId: string,
  data: Record<string, unknown>,
): Promise<PartnerAssignmentContact> {
  const res = await apiFetchAuth(`${PARTNERS_API}/assignments/${assignmentId}/setup/contacts/`, {
    method: "POST",
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(extractError(res, body))
  }
  const json = await res.json()
  return json.data ?? json
}

export async function updateAssignmentContact(
  assignmentId: string,
  contactId: string,
  data: Record<string, unknown>,
): Promise<PartnerAssignmentContact> {
  const res = await apiFetchAuth(`${PARTNERS_API}/assignments/${assignmentId}/setup/contacts/${contactId}/`, {
    method: "PATCH",
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(extractError(res, body))
  }
  const json = await res.json()
  return json.data ?? json
}

export async function deleteAssignmentContact(assignmentId: string, contactId: string): Promise<void> {
  const res = await apiFetchAuth(`${PARTNERS_API}/assignments/${assignmentId}/setup/contacts/${contactId}/`, {
    method: "DELETE",
  })
  if (!res.ok) throw new Error("Failed to delete contact")
}

// --- Bank Accounts ---

export async function getAssignmentBankAccounts(assignmentId: string): Promise<PartnerAssignmentBankAccount[]> {
  const res = await apiFetchAuth(`${PARTNERS_API}/assignments/${assignmentId}/setup/bank-accounts/`)
  if (!res.ok) throw new Error("Failed to fetch bank accounts")
  return extractList<PartnerAssignmentBankAccount>(res)
}

export async function createAssignmentBankAccount(
  assignmentId: string,
  data: Record<string, unknown>,
): Promise<PartnerAssignmentBankAccount> {
  const res = await apiFetchAuth(`${PARTNERS_API}/assignments/${assignmentId}/setup/bank-accounts/`, {
    method: "POST",
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(extractError(res, body))
  }
  const json = await res.json()
  return json.data ?? json
}

export async function updateAssignmentBankAccount(
  assignmentId: string,
  bankId: string,
  data: Record<string, unknown>,
): Promise<PartnerAssignmentBankAccount> {
  const res = await apiFetchAuth(`${PARTNERS_API}/assignments/${assignmentId}/setup/bank-accounts/${bankId}/`, {
    method: "PATCH",
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(extractError(res, body))
  }
  const json = await res.json()
  return json.data ?? json
}

export async function deleteAssignmentBankAccount(assignmentId: string, bankId: string): Promise<void> {
  const res = await apiFetchAuth(`${PARTNERS_API}/assignments/${assignmentId}/setup/bank-accounts/${bankId}/`, {
    method: "DELETE",
  })
  if (!res.ok) throw new Error("Failed to delete bank account")
}

// --- KYC Profile ---

export async function getAssignmentKYC(assignmentId: string): Promise<PartnerKYCProfile> {
  const res = await apiFetchAuth(`${PARTNERS_API}/assignments/${assignmentId}/setup/kyc/`)
  if (!res.ok) throw new Error("Failed to fetch KYC profile")
  const json = await res.json()
  return json.data ?? json
}

export async function updateAssignmentKYC(
  assignmentId: string,
  data: Record<string, unknown>,
): Promise<PartnerKYCProfile> {
  const res = await apiFetchAuth(`${PARTNERS_API}/assignments/${assignmentId}/setup/kyc/`, {
    method: "PATCH",
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(extractError(res, body))
  }
  const json = await res.json()
  return json.data ?? json
}

export async function fetchBranches(): Promise<BranchRecord[]> {
  const res = await apiFetchAuth(`${ONBOARDING_API}/branches/`)
  if (!res.ok) throw new Error("Failed to fetch branches")
  return extractList<BranchRecord>(res)
}

export async function fetchBranch(id: string): Promise<BranchRecord> {
  const res = await apiFetchAuth(`${ONBOARDING_API}/branches/${id}/`)
  if (!res.ok) throw new Error("Failed to fetch branch")
  return extractOne<BranchRecord>(res)
}

export async function createBranchRecord(data: Partial<BranchRecord>): Promise<BranchRecord> {
  const res = await apiFetchAuth(`${ONBOARDING_API}/branches/`, {
    method: "POST",
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(extractError(res, body))
  }
  return res.json()
}

export async function updateBranchRecord(id: string, data: Partial<BranchRecord>): Promise<BranchRecord> {
  const res = await apiFetchAuth(`${ONBOARDING_API}/branches/${id}/`, {
    method: "PATCH",
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(extractError(res, body))
  }
  return res.json()
}

export async function deleteBranchRecord(id: string): Promise<void> {
  const res = await apiFetchAuth(`${ONBOARDING_API}/branches/${id}/`, { method: "DELETE" })
  if (!res.ok) throw new Error("Failed to delete branch")
}

export async function fetchLocations(branchId?: string): Promise<LocationRecord[]> {
  const url = branchId ? `${ONBOARDING_API}/locations/?branch_id=${branchId}` : `${ONBOARDING_API}/locations/`
  const res = await apiFetchAuth(url)
  if (!res.ok) throw new Error("Failed to fetch locations")
  return extractList<LocationRecord>(res)
}

export async function fetchLocation(id: string): Promise<LocationRecord> {
  const res = await apiFetchAuth(`${ONBOARDING_API}/locations/${id}/`)
  if (!res.ok) throw new Error("Failed to fetch location")
  return extractOne<LocationRecord>(res)
}

export async function createLocationRecord(data: Partial<LocationRecord>): Promise<LocationRecord> {
  const res = await apiFetchAuth(`${ONBOARDING_API}/locations/`, {
    method: "POST",
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(extractError(res, body))
  }
  return res.json()
}

export async function updateLocationRecord(id: string, data: Partial<LocationRecord>): Promise<LocationRecord> {
  const res = await apiFetchAuth(`${ONBOARDING_API}/locations/${id}/`, {
    method: "PATCH",
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(extractError(res, body))
  }
  return res.json()
}

export async function deleteLocationRecord(id: string): Promise<void> {
  const res = await apiFetchAuth(`${ONBOARDING_API}/locations/${id}/`, { method: "DELETE" })
  if (!res.ok) throw new Error("Failed to delete location")
}

// ============================================================================
// System Parameters API
// ============================================================================

const SYSTEM_PARAMS = "/api/v1/system-parameters"

async function extractList<T>(res: Response): Promise<T[]> {
  const json = await res.json()
  return (json as { data: T[] }).data ?? json.results ?? json
}

async function extractOne<T>(res: Response): Promise<T> {
  const json = await res.json()
  return (json as { data: T }).data ?? json
}

export async function listParameterGroups(): Promise<ParameterGroup[]> {
  const res = await apiFetchAuth(`${SYSTEM_PARAMS}/groups/`)
  if (!res.ok) throw new Error("Failed to load parameter groups")
  return extractList<ParameterGroup>(res)
}

export async function getParameterGroup(id: string): Promise<ParameterGroup> {
  const res = await apiFetchAuth(`${SYSTEM_PARAMS}/groups/${id}/`)
  if (!res.ok) throw new Error("Failed to load parameter group")
  return extractOne<ParameterGroup>(res)
}

export async function listSystemParameters(groupId?: string): Promise<SystemParameter[]> {
  const query = groupId ? `?group=${groupId}&per_page=200` : "?per_page=200"
  const res = await apiFetchAuth(`${SYSTEM_PARAMS}/parameters/${query}`)
  if (!res.ok) throw new Error("Failed to load system parameters")
  return extractList<SystemParameter>(res)
}

export async function createSystemParameter(data: Record<string, unknown>): Promise<SystemParameter> {
  const res = await apiFetchAuth(`${SYSTEM_PARAMS}/parameters/`, {
    method: "POST",
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(extractError(res, body))
  }
  return extractOne<SystemParameter>(res)
}

export async function updateSystemParameter(id: string, data: Record<string, unknown>): Promise<SystemParameter> {
  const res = await apiFetchAuth(`${SYSTEM_PARAMS}/parameters/${id}/`, {
    method: "PATCH",
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(extractError(res, body))
  }
  return extractOne<SystemParameter>(res)
}

export async function deleteSystemParameter(id: string): Promise<void> {
  const res = await apiFetchAuth(`${SYSTEM_PARAMS}/parameters/${id}/`, {
    method: "DELETE",
  })
  if (!res.ok) throw new Error("Failed to delete system parameter")
}

export async function listChoiceLists(): Promise<ChoiceList[]> {
  const res = await apiFetchAuth(`${SYSTEM_PARAMS}/choice-lists/?per_page=200`)
  if (!res.ok) throw new Error("Failed to load choice lists")
  return extractList<ChoiceList>(res)
}

export async function createChoiceList(data: Record<string, unknown>): Promise<ChoiceList> {
  const res = await apiFetchAuth(`${SYSTEM_PARAMS}/choice-lists/`, {
    method: "POST",
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(extractError(res, body))
  }
  return extractOne<ChoiceList>(res)
}

export async function updateChoiceList(id: string, data: Record<string, unknown>): Promise<ChoiceList> {
  const res = await apiFetchAuth(`${SYSTEM_PARAMS}/choice-lists/${id}/`, {
    method: "PATCH",
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(extractError(res, body))
  }
  return extractOne<ChoiceList>(res)
}

export async function deleteChoiceList(id: string): Promise<void> {
  const res = await apiFetchAuth(`${SYSTEM_PARAMS}/choice-lists/${id}/`, {
    method: "DELETE",
  })
  if (!res.ok) throw new Error("Failed to delete choice list")
}

export async function listChoiceOptions(choiceListId: string): Promise<ChoiceOption[]> {
  const res = await apiFetchAuth(`${SYSTEM_PARAMS}/choice-options/?choice_list=${choiceListId}&per_page=200`)
  if (!res.ok) throw new Error("Failed to load choice options")
  return extractList<ChoiceOption>(res)
}

export async function createChoiceOption(data: Record<string, unknown>): Promise<ChoiceOption> {
  const res = await apiFetchAuth(`${SYSTEM_PARAMS}/choice-options/`, {
    method: "POST",
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(extractError(res, body))
  }
  return extractOne<ChoiceOption>(res)
}

export async function updateChoiceOption(id: string, data: Record<string, unknown>): Promise<ChoiceOption> {
  const res = await apiFetchAuth(`${SYSTEM_PARAMS}/choice-options/${id}/`, {
    method: "PATCH",
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(extractError(res, body))
  }
  return extractOne<ChoiceOption>(res)
}

export async function deleteChoiceOption(id: string): Promise<void> {
  const res = await apiFetchAuth(`${SYSTEM_PARAMS}/choice-options/${id}/`, {
    method: "DELETE",
  })
  if (!res.ok) throw new Error("Failed to delete choice option")
}

// Helper to resolve group code → ID via cache
let _groupCache: ParameterGroup[] | null = null

export async function resolveGroupId(code: string): Promise<string> {
  if (!_groupCache) {
    _groupCache = await listParameterGroups()
  }
  const g = _groupCache.find((g) => g.code === code)
  if (!g) throw new Error(`Parameter group "${code}" not found`)
  return g.id
}

export function clearGroupCache() {
  _groupCache = null
}

// ============================================================================
// AI Assistant API
// ============================================================================

export async function aiAnalyzePrompt(prompt: string): Promise<{
  success: boolean
  message: string
  data: {
    status: "ready" | "needs_clarification"
    partnerType?: "INDIVIDUAL" | "CORPORATE"
    partnerData: Record<string, unknown>
    missingFields?: string[]
    explanation?: string
  }
}> {
  const res = await apiFetchAuth("/api/v1/ai/analyze-prompt/", {
    method: "POST",
    body: JSON.stringify({ prompt }),
  })
  const json = await res.json()
  if (!res.ok) throw new Error(json.message ?? "AI analysis failed")
  return json
}

export async function aiExecutePartnerCreation(
  partnerType: "INDIVIDUAL" | "CORPORATE",
  partnerData: Record<string, unknown>,
): Promise<Record<string, unknown>> {
  const res = await apiFetchAuth("/api/v1/ai/execute/", {
    method: "POST",
    body: JSON.stringify({ partner_type: partnerType, partner_data: partnerData }),
  })
  const json = await res.json()
  if (!res.ok) throw new Error(json.message ?? "Partner creation failed")
  return json.data as Record<string, unknown>
}

export async function aiClarify(
  prompt: string,
  missingFields: string[],
  partialData?: Record<string, unknown>,
): Promise<{
  success: boolean
  data: {
    status: "ready" | "needs_clarification"
    partnerType?: string
    partnerData?: Record<string, unknown>
    missingRequired?: string[]
    missingOptional?: string[]
    explanation?: string
  }
}> {
  const res = await apiFetchAuth("/api/v1/ai/clarify/", {
    method: "POST",
    body: JSON.stringify({
      prompt,
      missing_fields: missingFields,
      partial_data: partialData ?? {},
    }),
  })
  const json = await res.json()
  if (!res.ok) throw new Error(json.message ?? "Clarification failed")
  return json
}

// ============================================================================
// AI Assistant API
// ============================================================================

const AI_API = "/api/v1/ai"

export async function analyzePartnerPrompt(prompt: string): Promise<unknown> {
  const res = await apiFetchAuth(`${AI_API}/analyze-prompt/`, {
    method: "POST",
    body: JSON.stringify({ prompt }),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(extractError(res, body))
  }
  return res.json()
}

export async function executePartnerCreation(
  partnerType: string,
  partnerData: Record<string, unknown>,
): Promise<unknown> {
  const res = await apiFetchAuth(`${AI_API}/execute/`, {
    method: "POST",
    body: JSON.stringify({ partner_type: partnerType, partner_data: partnerData }),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(extractError(res, body))
  }
  return res.json()
}

export async function clarifyPartnerPrompt(
  prompt: string,
  missingFields: string[],
): Promise<unknown> {
  const res = await apiFetchAuth(`${AI_API}/clarify/`, {
    method: "POST",
    body: JSON.stringify({ prompt, missing_fields: missingFields }),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(extractError(res, body))
  }
  return res.json()
}

// ============================================================================
// User Management API
// ============================================================================

const USERS_API = "/api/v1/users"

// --- Permission Groups ---
export async function listPermissionGroups(): Promise<any[]> {
  const res = await apiFetchAuth(`${USERS_API}/permission-groups/`)
  const json = await res.json()
  if (!res.ok) throw new Error(extractError(res, json))
  return json.data ?? json
}

export async function createPermissionGroup(data: Record<string, unknown>): Promise<any> {
  const res = await apiFetchAuth(`${USERS_API}/permission-groups/`, {
    method: "POST",
    body: JSON.stringify(data),
  })
  const json = await res.json()
  if (!res.ok) throw new Error(extractError(res, json))
  return json.data ?? json
}

export async function updatePermissionGroup(id: string, data: Record<string, unknown>): Promise<any> {
  const res = await apiFetchAuth(`${USERS_API}/permission-groups/${id}/`, {
    method: "PATCH",
    body: JSON.stringify(data),
  })
  const json = await res.json()
  if (!res.ok) throw new Error(extractError(res, json))
  return json.data ?? json
}

export async function deletePermissionGroup(id: string): Promise<void> {
  const res = await apiFetchAuth(`${USERS_API}/permission-groups/${id}/`, {
    method: "DELETE",
  })
  if (!res.ok) {
    const json = await res.json().catch(() => null)
    throw new Error(extractError(res, json))
  }
}

// --- Permissions ---
export async function listPermissions(params: { module?: string; search?: string } = {}): Promise<any[]> {
  const q = new URLSearchParams()
  if (params.module) q.set("module", params.module)
  if (params.search) q.set("search", params.search)
  const query = q.toString() ? `?${q.toString()}` : ""
  const res = await apiFetchAuth(`${USERS_API}/permissions/${query}`)
  const json = await res.json()
  if (!res.ok) throw new Error(extractError(res, json))
  return json.data ?? json
}

export async function listPermissionModules(): Promise<string[]> {
  const res = await apiFetchAuth(`${USERS_API}/permissions/modules/`)
  const json = await res.json()
  if (!res.ok) throw new Error(extractError(res, json))
  return json.data ?? json
}

// --- User Groups (Roles) ---
export async function listUserGroups(): Promise<any[]> {
  const res = await apiFetchAuth(`${USERS_API}/groups/`)
  const json = await res.json()
  if (!res.ok) throw new Error(extractError(res, json))
  return json.data ?? json
}

export async function getUserGroup(id: string): Promise<any> {
  const res = await apiFetchAuth(`${USERS_API}/groups/${id}/`)
  const json = await res.json()
  if (!res.ok) throw new Error(extractError(res, json))
  return json.data ?? json
}

export async function createUserGroup(data: Record<string, unknown>): Promise<any> {
  const res = await apiFetchAuth(`${USERS_API}/groups/`, {
    method: "POST",
    body: JSON.stringify(data),
  })
  const json = await res.json()
  if (!res.ok) throw new Error(extractError(res, json))
  return json.data ?? json
}

export async function updateUserGroup(id: string, data: Record<string, unknown>): Promise<any> {
  const res = await apiFetchAuth(`${USERS_API}/groups/${id}/`, {
    method: "PATCH",
    body: JSON.stringify(data),
  })
  const json = await res.json()
  if (!res.ok) throw new Error(extractError(res, json))
  return json.data ?? json
}

export async function deleteUserGroup(id: string): Promise<void> {
  const res = await apiFetchAuth(`${USERS_API}/groups/${id}/`, {
    method: "DELETE",
  })
  if (!res.ok) {
    const json = await res.json().catch(() => null)
    throw new Error(extractError(res, json))
  }
}

export async function assignPermissionsToGroup(groupId: string, permissionIds: string[]): Promise<any> {
  const res = await apiFetchAuth(`${USERS_API}/groups/${groupId}/assign_permissions/`, {
    method: "POST",
    body: JSON.stringify({ permission_ids: permissionIds }),
  })
  const json = await res.json()
  if (!res.ok) throw new Error(extractError(res, json))
  return json.data ?? json
}

export async function removePermissionsFromGroup(groupId: string, permissionIds: string[]): Promise<any> {
  const res = await apiFetchAuth(`${USERS_API}/groups/${groupId}/remove_permissions/`, {
    method: "POST",
    body: JSON.stringify({ permission_ids: permissionIds }),
  })
  const json = await res.json()
  if (!res.ok) throw new Error(extractError(res, json))
  return json.data ?? json
}

// --- Users ---
export async function listUsers(params: { page?: number; pageSize?: number; search?: string; group?: string; is_active?: boolean } = {}): Promise<PaginatedResponse<any>> {
  const q = new URLSearchParams()
  if (params.page) q.set("page", String(params.page))
  if (params.pageSize) q.set("per_page", String(params.pageSize))
  if (params.search) q.set("search", params.search)
  if (params.group) q.set("group", params.group)
  if (params.is_active !== undefined) q.set("is_active", String(params.is_active))
  const query = q.toString() ? `?${q.toString()}` : ""
  const res = await apiFetchAuth(`${USERS_API}/users/${query}`)
  const json = await res.json()
  if (!res.ok) throw new Error(extractError(res, json))
  return {
    results: json.data ?? json,
    count: json.pagination?.total ?? json.count ?? (json.data || json).length,
    next: json.pagination?.next ?? json.next ?? null,
    previous: json.pagination?.previous ?? json.previous ?? null,
  }
}

export async function getUser(id: string): Promise<any> {
  const res = await apiFetchAuth(`${USERS_API}/users/${id}/`)
  const json = await res.json()
  if (!res.ok) throw new Error(extractError(res, json))
  return json.data ?? json
}

export async function createUser(data: Record<string, unknown>): Promise<any> {
  const res = await apiFetchAuth(`${USERS_API}/users/`, {
    method: "POST",
    body: JSON.stringify(data),
  })
  const json = await res.json()
  if (!res.ok) throw new Error(extractError(res, json))
  return json.data ?? json
}

export async function updateUser(id: string, data: Record<string, unknown>): Promise<any> {
  const res = await apiFetchAuth(`${USERS_API}/users/${id}/`, {
    method: "PATCH",
    body: JSON.stringify(data),
  })
  const json = await res.json()
  if (!res.ok) throw new Error(extractError(res, json))
  return json.data ?? json
}

export async function deleteUser(id: string): Promise<void> {
  const res = await apiFetchAuth(`${USERS_API}/users/${id}/`, {
    method: "DELETE",
  })
  if (!res.ok) {
    const json = await res.json().catch(() => null)
    throw new Error(extractError(res, json))
  }
}

export async function activateUser(id: string): Promise<void> {
  const res = await apiFetchAuth(`${USERS_API}/users/${id}/activate/`, {
    method: "POST",
  })
  if (!res.ok) {
    const json = await res.json().catch(() => null)
    throw new Error(extractError(res, json))
  }
}

export async function deactivateUser(id: string): Promise<void> {
  const res = await apiFetchAuth(`${USERS_API}/users/${id}/deactivate/`, {
    method: "POST",
  })
  if (!res.ok) {
    const json = await res.json().catch(() => null)
    throw new Error(extractError(res, json))
  }
}
