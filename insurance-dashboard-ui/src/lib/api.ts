import type {
  AuthUser,
  LoginResult,
  LoginSuccessData,
  LoginTokens,
  Setup2FAResult,
  DashboardData,
} from "./types"

export const API_BASE = import.meta.env.VITE_API_BASE ?? ""

// ---------------------------------------------------------------------------
// Token helpers (sessionStorage — cleared on tab close)
// ---------------------------------------------------------------------------

const TK_ACCESS = "aims_access_token"
const TK_REFRESH = "aims_refresh_token"

function getAccessToken(): string | null {
  return sessionStorage.getItem(TK_ACCESS)
}

function getRefreshToken(): string | null {
  return sessionStorage.getItem(TK_REFRESH)
}

function setTokens(tokens: LoginTokens) {
  sessionStorage.setItem(TK_ACCESS, tokens.accessToken)
  sessionStorage.setItem(TK_REFRESH, tokens.refreshToken)
}

function clearTokens() {
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
  const raw = json as Record<string, unknown>
  const d = raw.data as Record<string, unknown> | undefined
  console.log("[api.login] response keys:", Object.keys(raw))
  console.log("[api.login] data keys:", d ? Object.keys(d) : "undefined")
  console.log("[api.login] accessToken present:", "accessToken" in (d || {}))
  console.log("[api.login] access_token present:", "access_token" in (d || {}))

  // If login succeeded with tokens, persist them
  const data = json.data as LoginSuccessData
  const token = (data as Record<string, unknown>).accessToken as string | undefined
    ?? (data as Record<string, unknown>).access_token as string | undefined
  if (token) {
    console.log("[api.login] storing token:", token.substring(0, 30) + "...")
    setTokens({
      accessToken: (data as Record<string, unknown>).accessToken as string ?? (data as Record<string, unknown>).access_token as string,
      refreshToken: (data as Record<string, unknown>).refreshToken as string ?? (data as Record<string, unknown>).refresh_token as string,
      accessExpiresIn: Number((data as Record<string, unknown>).accessExpiresIn ?? (data as Record<string, unknown>).access_expires_in ?? 0),
      refreshExpiresIn: Number((data as Record<string, unknown>).refreshExpiresIn ?? (data as Record<string, unknown>).refresh_expires_in ?? 0),
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
): Promise<ApplicationDocument> {
  const formData = new FormData()
  formData.append("file", file)
  formData.append("document_type", documentType)
  formData.append("document_name", documentName || file.name)

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
