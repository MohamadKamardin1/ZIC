export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? import.meta.env.VITE_API_BASE ?? "").replace(/\/$/, "")

export type QueryValue = string | number | boolean | null | undefined
export type QueryParams = Record<string, QueryValue>

export interface NormalizedApiErrorShape {
  status: number
  code: string
  message: string
  fieldErrors: Record<string, string[]>
  correlationId?: string
  details?: unknown
}

export class ApiClientError extends Error implements NormalizedApiErrorShape {
  status: number
  code: string
  fieldErrors: Record<string, string[]>
  correlationId?: string
  details?: unknown

  constructor(error: NormalizedApiErrorShape) {
    super(error.message)
    this.name = "ApiClientError"
    this.status = error.status
    this.code = error.code
    this.fieldErrors = error.fieldErrors
    this.correlationId = error.correlationId
    this.details = error.details
  }
}

export interface TableQuery {
  page?: number
  pageSize?: number
  search?: string
  ordering?: string
  filters?: QueryParams
}

export function buildQueryString(params: QueryParams = {}): string {
  const search = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== null && value !== undefined && value !== "") search.set(key, String(value))
  })
  const result = search.toString()
  return result ? `?${result}` : ""
}

export function buildTableQuery(query: TableQuery = {}): string {
  return buildQueryString({
    page: query.page,
    page_size: query.pageSize,
    search: query.search,
    ordering: query.ordering,
    ...(query.filters ?? {}),
  })
}

function createCorrelationId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) return crypto.randomUUID()
  return `zic-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

function collectFieldErrors(value: unknown): Record<string, string[]> {
  if (!value || typeof value !== "object" || Array.isArray(value)) return {}
  const errors: Record<string, string[]> = {}
  Object.entries(value as Record<string, unknown>).forEach(([field, detail]) => {
    if (Array.isArray(detail)) errors[field] = detail.map(String)
    else if (typeof detail === "string") errors[field] = [detail]
    else if (detail && typeof detail === "object") errors[field] = [JSON.stringify(detail)]
  })
  return errors
}

export async function normalizeResponseError(response: Response): Promise<ApiClientError> {
  const correlationId = response.headers.get("X-Correlation-ID") ?? response.headers.get("X-Request-ID") ?? undefined
  const body = await response.json().catch(() => null)
  const bodyRecord = body && typeof body === "object" && !Array.isArray(body) ? body as Record<string, unknown> : {}
  const payload = ("data" in bodyRecord ? bodyRecord.data : body) as unknown
  const record = payload && typeof payload === "object" && !Array.isArray(payload) ? payload as Record<string, unknown> : {}
  const rawFieldErrors = bodyRecord.errors ?? bodyRecord.fieldErrors ?? bodyRecord.field_errors ?? record.errors ?? record.fieldErrors ?? record.field_errors ?? record
  const fieldErrors = collectFieldErrors(rawFieldErrors)
  const message = typeof bodyRecord.message === "string"
    ? bodyRecord.message
    : typeof record.detail === "string"
      ? record.detail
      : typeof record.message === "string"
        ? record.message
        : Object.values(fieldErrors)[0]?.[0] ?? `Request failed (${response.status}).`
  const code = typeof bodyRecord.code === "string" ? bodyRecord.code : typeof record.code === "string" ? record.code : `HTTP_${response.status}`
  return new ApiClientError({ status: response.status, code, message, fieldErrors, correlationId, details: body })
}

export interface ApiRequestOptions extends RequestInit {
  skipAuth?: boolean
  correlationId?: string
}

export async function request<T>(path: string, options: ApiRequestOptions = {}): Promise<T> {
  const headers = new Headers(options.headers)
  headers.set("Accept", "application/json")
  if (options.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json")
  const correlationId = options.correlationId ?? createCorrelationId()
  headers.set("X-Correlation-ID", correlationId)

  const token = options.skipAuth ? null : (localStorage.getItem("aims_access_token") ?? sessionStorage.getItem("aims_access_token"))
  if (token) headers.set("Authorization", `Bearer ${token}`)

  const response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers })
  if (!response.ok) throw await normalizeResponseError(response)
  if (response.status === 204) return undefined as T
  const payload = await response.json()
  return (payload && typeof payload === "object" && "data" in payload ? payload.data : payload) as T
}

export interface AccessPermission {
  module: string
  action: string
}

export interface AccessMetadata {
  visibleModules: string[]
  permissions: AccessPermission[]
  groups: string[]
  isSuperuser?: boolean
  fetchedAt?: string
}

export async function fetchAccessMetadata(): Promise<AccessMetadata | null> {
  const normalize = (payload: unknown): AccessMetadata | null => {
    if (!payload || typeof payload !== "object") return null
    const envelope = payload as Record<string, unknown>
    const raw = envelope.access && typeof envelope.access === "object"
      ? envelope.access as Record<string, unknown>
      : envelope
    const profile = raw.user && typeof raw.user === "object"
      ? raw.user as Record<string, unknown>
      : raw
    const permissions = (raw.permissions ?? profile.permissions ?? []) as AccessMetadata["permissions"]
    const groups = (raw.groups ?? profile.groups ?? []) as string[]
    const visibleModules = (raw.visibleModules ?? profile.visibleModules ?? permissions.map((permission) => permission.module)) as string[]
    const isSuperuser = raw.isSuperuser ?? raw.is_superuser ?? profile.isSuperuser ?? profile.is_superuser
    return {
      visibleModules,
      permissions,
      groups,
      ...(typeof isSuperuser === "boolean" ? { isSuperuser } : {}),
      fetchedAt: new Date().toISOString(),
    }
  }

  try {
    const payload = await request<Partial<AccessMetadata> | { access?: Partial<AccessMetadata> }>("/api/v1/iam/me/access/")
    const access = normalize(payload)
    try {
      const profile = await request<unknown>("/api/v1/auth/me/")
      const profileAccess = normalize(profile)
      if (access && profileAccess) {
        return {
          ...access,
          groups: profileAccess.groups.length ? profileAccess.groups : access.groups,
          isSuperuser: profileAccess.isSuperuser ?? access.isSuperuser,
        }
      }
      return profileAccess ?? access
    } catch (profileError) {
      if (profileError instanceof ApiClientError && [404, 405].includes(profileError.status)) return access
      throw profileError
    }
  } catch (error) {
    if (!(error instanceof ApiClientError) || ![404, 405].includes(error.status)) throw error
  }

  try {
    const payload = await request<{ user?: Partial<AccessMetadata> }>("/api/v1/auth/me/")
    return normalize(payload)
  } catch (error) {
    if (error instanceof ApiClientError && [404, 405].includes(error.status)) return null
    throw error
  }
}

export async function getExchangeRate(): Promise<{ baseCurrency: string; quoteCurrency: string; rate: string } | null> {
  try {
    return await request("/api/v1/dashboard/currencies/current/")
  } catch (error) {
    if (error instanceof ApiClientError && [404, 405].includes(error.status)) return null
    throw error
  }
}
