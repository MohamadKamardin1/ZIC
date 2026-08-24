import { apiFetchAuth } from "./api"

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
  resolutionSteps?: string[]
  deepLink?: string
}

export class ApiClientError extends Error implements NormalizedApiErrorShape {
  status: number
  code: string
  fieldErrors: Record<string, string[]>
  correlationId?: string
  details?: unknown
  resolutionSteps?: string[]
  deepLink?: string

  constructor(error: NormalizedApiErrorShape) {
    super(error.message)
    this.name = "ApiClientError"
    this.status = error.status
    this.code = error.code
    this.fieldErrors = error.fieldErrors
    this.correlationId = error.correlationId
    this.details = error.details
    this.resolutionSteps = error.resolutionSteps
    this.deepLink = error.deepLink
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

function collectFieldErrors(value: unknown, prefix = ""): Record<string, string[]> {
  if (value === null || value === undefined) return {}
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return prefix ? { [prefix]: [String(value)] } : {}
  }
  if (Array.isArray(value)) {
    return value.reduce<Record<string, string[]>>((result, item, index) => {
      const isNestedRecord = item !== null && typeof item === "object" && !Array.isArray(item)
      const nestedPrefix = isNestedRecord ? (prefix ? `${prefix}.${index}` : String(index)) : prefix
      const nested = collectFieldErrors(item, nestedPrefix)
      Object.entries(nested).forEach(([key, messages]) => { result[key] = [...(result[key] ?? []), ...messages] })
      return result
    }, {})
  }
  if (typeof value !== "object") return {}
  const errors: Record<string, string[]> = {}
  Object.entries(value as Record<string, unknown>).forEach(([field, detail]) => {
    const key = prefix ? `${prefix}.${field}` : field
    const nested = collectFieldErrors(detail, key)
    Object.entries(nested).forEach(([nestedKey, messages]) => {
      errors[nestedKey] = [...(errors[nestedKey] ?? []), ...messages]
    })
  })
  return errors
}

export async function normalizeResponseError(response: Response): Promise<ApiClientError> {
  const correlationId = response.headers.get("X-Correlation-ID") ?? response.headers.get("X-Request-ID") ?? undefined
  const body = await response.json().catch(() => null)
  const bodyRecord = body && typeof body === "object" && !Array.isArray(body) ? body as Record<string, unknown> : {}
  const envelopeError = bodyRecord.error && typeof bodyRecord.error === "object" && !Array.isArray(bodyRecord.error)
    ? bodyRecord.error as Record<string, unknown>
    : {}
  const payload = ("data" in bodyRecord ? bodyRecord.data : body) as unknown
  const record = payload && typeof payload === "object" && !Array.isArray(payload) ? payload as Record<string, unknown> : {}
  const details = envelopeError.details ?? bodyRecord.details ?? bodyRecord.errors ?? bodyRecord.fieldErrors ?? bodyRecord.field_errors ?? record.errors ?? record.fieldErrors ?? record.field_errors
  const rawFieldErrors = details ?? (Object.keys(record).length ? record : undefined)
  const fieldErrors = collectFieldErrors(rawFieldErrors)
  const message = typeof envelopeError.message === "string"
    ? envelopeError.message
    : typeof bodyRecord.message === "string"
      ? bodyRecord.message
      : typeof record.detail === "string"
        ? record.detail
        : typeof record.message === "string"
          ? record.message
          : Object.values(fieldErrors).flat()[0] ?? `Request failed (${response.status}).`
  const code = typeof envelopeError.code === "string"
    ? envelopeError.code
    : typeof envelopeError.errorCode === "string"
      ? envelopeError.errorCode
      : typeof bodyRecord.code === "string"
        ? bodyRecord.code
        : typeof bodyRecord.errorCode === "string"
          ? bodyRecord.errorCode
          : typeof record.code === "string"
            ? record.code
            : typeof record.errorCode === "string" ? record.errorCode : `HTTP_${response.status}`
  const rawResolutionSteps = envelopeError.resolutionSteps ?? bodyRecord.resolutionSteps ?? record.resolutionSteps
  const resolutionSteps = Array.isArray(rawResolutionSteps) ? rawResolutionSteps.filter((step): step is string => typeof step === "string") : undefined
  const rawDeepLink = envelopeError.deepLink ?? bodyRecord.deepLink ?? record.deepLink
  const deepLink = typeof rawDeepLink === "string" ? rawDeepLink : undefined
  return new ApiClientError({ status: response.status, code, message, fieldErrors, correlationId, details: body, resolutionSteps, deepLink })
}

export interface ApiRequestOptions extends RequestInit {
  skipAuth?: boolean
  correlationId?: string
}

export async function request<T>(path: string, options: ApiRequestOptions = {}): Promise<T> {
  const headers = new Headers(options.headers)
  headers.set("Accept", "application/json")
  if (options.body && !(options.body instanceof FormData) && !headers.has("Content-Type")) headers.set("Content-Type", "application/json")
  const correlationId = options.correlationId ?? createCorrelationId()
  headers.set("X-Correlation-ID", correlationId)

  const { skipAuth, correlationId: _ignoredCorrelationId, ...fetchOptions } = options
  let response: Response
  try {
    response = skipAuth
      ? await fetch(`${API_BASE_URL}${path}`, { ...fetchOptions, headers })
      : await apiFetchAuth(path, { ...fetchOptions, headers })
  } catch (error) {
    if (error && typeof error === "object" && (error as { status?: unknown }).status === 401) {
      throw new ApiClientError({ status: 401, code: "AUTHENTICATION_REQUIRED", message: "Session expired — sign in again", fieldErrors: {}, details: error })
    }
    throw error
  }
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
