import { API_BASE, apiFetchAuth } from "./api"

export type AuthenticatedDocumentKind = "pdf" | "html" | "any"
export type AuthenticatedDocumentMode = "preview" | "download"

export interface AuthenticatedDocumentResult {
  blob: Blob
  objectUrl: string
  contentType: string
  filename?: string
}

export interface OpenAuthenticatedDocumentOptions {
  kind?: AuthenticatedDocumentKind
  mode?: AuthenticatedDocumentMode
  filename?: string
}

export class AuthenticatedDocumentError extends Error {
  status?: number
  requiresLogin: boolean
  loginUrl: string

  constructor(message: string, options: { status?: number; requiresLogin?: boolean } = {}) {
    super(message)
    this.name = "AuthenticatedDocumentError"
    this.status = options.status
    this.requiresLogin = options.requiresLogin ?? false
    const returnTo = typeof window === "undefined" ? "/" : `${window.location.pathname}${window.location.search}`
    this.loginUrl = `/login?returnTo=${encodeURIComponent(returnTo)}`
  }
}

function normalizeDocumentPath(url: string): string {
  if (!/^https?:\/\//i.test(url)) return url
  const parsed = new URL(url)
  const apiOrigin = API_BASE ? new URL(API_BASE, window.location.origin).origin : window.location.origin
  if (parsed.origin === apiOrigin || parsed.origin === window.location.origin) return `${parsed.pathname}${parsed.search}`
  return url
}

function acceptsContentType(contentType: string, kind: AuthenticatedDocumentKind): boolean {
  if (!contentType || contentType.includes("application/json") || contentType.includes("text/json")) return false
  if (kind === "pdf") return contentType.includes("application/pdf")
  if (kind === "html") return contentType.includes("text/html") || contentType.includes("application/xhtml+xml")
  return true
}

function filenameFromResponse(response: Response): string | undefined {
  const disposition = response.headers.get("content-disposition") ?? ""
  const encoded = disposition.match(/filename\*=UTF-8''([^;]+)/i)?.[1]
  if (encoded) return decodeURIComponent(encoded)
  return disposition.match(/filename="?([^";]+)"?/i)?.[1]
}

function statusOf(error: unknown): number | undefined {
  if (!error || typeof error !== "object") return undefined
  const status = (error as { status?: unknown }).status
  return typeof status === "number" ? status : undefined
}

function sessionError(status?: number): AuthenticatedDocumentError {
  return new AuthenticatedDocumentError("Session expired — sign in again", { status: status ?? 401, requiresLogin: true })
}

export async function fetchAuthenticatedDocument(
  url: string,
  kind: AuthenticatedDocumentKind = "any",
): Promise<AuthenticatedDocumentResult> {
  if (!url) throw new AuthenticatedDocumentError("The document URL was not returned by the server.")

  let response: Response
  try {
    response = await apiFetchAuth(normalizeDocumentPath(url), {
      method: "GET",
      headers: { Accept: "application/pdf, text/html, application/xhtml+xml" },
    })
  } catch (error) {
    if (statusOf(error) === 401) throw sessionError(401)
    throw error
  }

  if (response.status === 401) throw sessionError(401)
  if (!response.ok) {
    throw new AuthenticatedDocumentError(`Unable to retrieve the document (${response.status}).`, { status: response.status })
  }

  const contentType = (response.headers.get("content-type") ?? "").toLowerCase()
  if (!acceptsContentType(contentType, kind)) {
    throw new AuthenticatedDocumentError("The server returned an invalid document type. Please try generating the document again.", { status: response.status })
  }

  const blob = await response.blob()
  return {
    blob,
    objectUrl: URL.createObjectURL(blob),
    contentType,
    filename: filenameFromResponse(response),
  }
}

export async function openAuthenticatedDocument(
  url: string,
  options: OpenAuthenticatedDocumentOptions = {},
): Promise<AuthenticatedDocumentResult> {
  const previewWindow = options.mode === "preview" ? window.open("about:blank", "_blank", "noopener,noreferrer") : null
  try {
    const result = await fetchAuthenticatedDocument(url, options.kind ?? "any")
    if (options.mode === "download") {
    const anchor = document.createElement("a")
    anchor.href = result.objectUrl
    anchor.download = options.filename ?? result.filename ?? "document"
    anchor.rel = "noopener"
    document.body.appendChild(anchor)
    anchor.click()
    anchor.remove()
      return result
    }

    if (previewWindow) previewWindow.location.href = result.objectUrl
    return result
  } catch (error) {
    previewWindow?.close()
    throw error
  }
}

export function revokeAuthenticatedDocument(result?: Pick<AuthenticatedDocumentResult, "objectUrl"> | null): void {
  if (result?.objectUrl?.startsWith("blob:")) URL.revokeObjectURL(result.objectUrl)
}
