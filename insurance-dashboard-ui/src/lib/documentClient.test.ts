import { beforeEach, describe, expect, it, vi } from "vitest"
import { AuthenticatedDocumentError, fetchAuthenticatedDocument, openAuthenticatedDocument } from "./documentClient"

function setTokens(access = "old-access", refresh = "refresh-token") {
  localStorage.setItem("aims_access_token", access)
  localStorage.setItem("aims_refresh_token", refresh)
}

function response(body: BodyInit | null, status: number, contentType?: string) {
  return new Response(body, { status, headers: contentType ? { "Content-Type": contentType } : undefined })
}

describe("authenticated document client", () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    localStorage.clear()
    sessionStorage.clear()
    setTokens()
    Object.defineProperty(URL, "createObjectURL", { configurable: true, value: vi.fn(() => "blob:document-preview") })
    Object.defineProperty(URL, "revokeObjectURL", { configurable: true, value: vi.fn() })
  })

  it("sends bearer auth, refreshes once on 401, and returns a PDF blob", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(response("", 401))
      .mockResolvedValueOnce(response(JSON.stringify({ data: { access: "new-access", refresh: "new-refresh" } }), 200, "application/json"))
      .mockResolvedValueOnce(response("%PDF-1.7", 200, "application/pdf"))
    vi.stubGlobal("fetch", fetchMock)

    const result = await fetchAuthenticatedDocument("/api/v1/ol-quotations/documents/1/download/", "pdf")

    expect(result.contentType).toContain("application/pdf")
    expect(result.objectUrl).toBe("blob:document-preview")
    expect(fetchMock).toHaveBeenCalledTimes(3)
    expect((fetchMock.mock.calls[0]?.[1]?.headers as Headers).get("Authorization")).toBe("Bearer old-access")
    expect((fetchMock.mock.calls[2]?.[1]?.headers as Headers).get("Authorization")).toBe("Bearer new-access")
  })

  it("reports a session-expiry error when refresh and retry cannot authenticate", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(response("", 401))
      .mockResolvedValueOnce(response(JSON.stringify({ detail: "Refresh expired" }), 401, "application/json"))
    vi.stubGlobal("fetch", fetchMock)

    await expect(fetchAuthenticatedDocument("/api/v1/ol-quotations/documents/1/download/", "pdf")).rejects.toMatchObject({
      name: "AuthenticatedDocumentError",
      status: 401,
      requiresLogin: true,
      message: "Session expired — sign in again",
    })
  })

  it("rejects an unexpected document content type", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response(JSON.stringify({ detail: "Not a document" }), 200, "application/json")))

    await expect(fetchAuthenticatedDocument("/api/v1/ol-quotations/documents/1/download/", "pdf")).rejects.toBeInstanceOf(AuthenticatedDocumentError)
  })

  it("opens only a blob preview URL and never a raw API URL", async () => {
    const openMock = vi.fn((url: string) => ({ location: { href: url } }))
    vi.stubGlobal("open", openMock)
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response("<html>Preview</html>", 200, "text/html")))

    await openAuthenticatedDocument("/api/v1/ol-quotations/documents/1/html/", { kind: "html", mode: "preview" })

    expect(openMock).toHaveBeenCalledWith("about:blank", "_blank", "noopener,noreferrer")
    expect(openMock.mock.calls.some(([url]) => String(url).includes("/api/"))).toBe(false)
  })
})
