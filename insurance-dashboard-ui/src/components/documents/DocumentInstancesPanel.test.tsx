import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { ApiClientError, request } from "../../lib/apiClient"
import { fetchAuthenticatedDocument, openAuthenticatedDocument, revokeAuthenticatedDocument } from "../../lib/documentClient"
import { DocumentInstancesPanel } from "./DocumentInstancesPanel"

vi.mock("../../lib/apiClient", () => ({
  request: vi.fn(),
  ApiClientError: class ApiClientError extends Error {
    status = 409
    code = "TEMPLATE_PENDING"
    fieldErrors = {}
    constructor(message: string) { super(message); this.name = "ApiClientError" }
  },
}))

vi.mock("../../lib/documentClient", () => ({
  AuthenticatedDocumentError: class AuthenticatedDocumentError extends Error {
    requiresLogin = false
    loginUrl = "/login"
  },
  fetchAuthenticatedDocument: vi.fn(),
  openAuthenticatedDocument: vi.fn(),
  revokeAuthenticatedDocument: vi.fn(),
}))

describe("DocumentInstancesPanel", () => {
  const row = {
    id: "instance-1",
    document_type: "OL_QUOTATION",
    template_name: "Ordinary Life Quotation",
    template_version: 1,
    generated_by_display: "Super Admin",
    generated_at: "2026-08-23T10:00:00Z",
    page_count: 2,
    signed_download_url: "/api/v1/documents/instances/instance-1/download/?ticket=signed-ticket",
  }

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(request).mockResolvedValue({ count: 1, page: 1, page_size: 50, results: [row] })
    vi.mocked(fetchAuthenticatedDocument).mockResolvedValue({ blob: new Blob(["%PDF"]), objectUrl: "blob:pdf-preview", contentType: "application/pdf" })
  })

  it("renders unified metadata and previews a PDF as a blob URL", async () => {
    render(<DocumentInstancesPanel sourceType="ol_quotations.olquotation" objectId="quote-1" documentType="OL_QUOTATION" />)
    expect(await screen.findByText("Ordinary Life Quotation")).toBeInTheDocument()
    expect(screen.getByText("Super Admin")).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "Preview" }))
    expect(await screen.findByTitle("Documents PDF")).toHaveAttribute("src", "blob:pdf-preview")
    expect(fetchAuthenticatedDocument).toHaveBeenCalledWith(row.signed_download_url, "pdf")
    expect(screen.queryByText("instance-1")).not.toBeInTheDocument()
  })

  it("opens a signed ticket only and never navigates a raw protected API URL", async () => {
    const open = vi.spyOn(window, "open").mockImplementation(() => null)
    render(<DocumentInstancesPanel sourceType="ol_quotations.olquotation" objectId="quote-1" documentType="OL_QUOTATION" />)
    await screen.findByText("Ordinary Life Quotation")
    fireEvent.click(screen.getByRole("button", { name: "Open in new tab" }))
    expect(open).toHaveBeenCalledWith(row.signed_download_url, "_blank", "noopener,noreferrer")
    expect(open.mock.calls.some(([url]) => String(url).includes("/api/") && !String(url).includes("ticket=") )).toBe(false)
    open.mockRestore()
  })

  it("uses authenticated download for the Download action", async () => {
    render(<DocumentInstancesPanel sourceType="ol_quotations.olquotation" objectId="quote-1" documentType="OL_QUOTATION" />)
    await screen.findByText("Ordinary Life Quotation")
    fireEvent.click(screen.getByRole("button", { name: "Download" }))
    await waitFor(() => expect(openAuthenticatedDocument).toHaveBeenCalledWith(row.signed_download_url, expect.objectContaining({ kind: "pdf", mode: "download" })))
  })

  it("shows an ErrorCoach branding deep link for pending templates", async () => {
    const pending = new ApiClientError({ status: 409, code: "TEMPLATE_PENDING", message: "The Receipt template is not configured. Configure document branding in System Parameters.", fieldErrors: {} })
    vi.mocked(request).mockRejectedValueOnce(pending)
    render(<DocumentInstancesPanel sourceType="documents.pending" objectId="pending" documentType="RECEIPT" />)
    expect(await screen.findByText(/Configure document branding/)).toBeInTheDocument()
    expect(screen.getByRole("link", { name: "Open branding settings" })).toHaveAttribute("href", "/system-parameters/documents/branding")
  })

  it("revokes the blob preview when the panel unmounts", async () => {
    const view = render(<DocumentInstancesPanel sourceType="ol_quotations.olquotation" objectId="quote-1" documentType="OL_QUOTATION" />)
    await screen.findByText("Ordinary Life Quotation")
    fireEvent.click(screen.getByRole("button", { name: "Preview" }))
    await screen.findByTitle("Documents PDF")
    view.unmount()
    expect(revokeAuthenticatedDocument).toHaveBeenCalled()
  })
})
