import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { ToastProvider } from "../../components/ui/Toast"
import { ApiClientError } from "../../lib/apiClient"
import type { ReceiptDocument, ReceiptRecord } from "../../lib/receipts-api"
import { ReceiptDocumentsPanel, ReceiptPrintPreviewModal } from "./ReceiptPrintPreview"

const apiMocks = vi.hoisted(() => ({ print: vi.fn(), documents: vi.fn() }))
const documentMocks = vi.hoisted(() => ({ fetchAuthenticatedDocument: vi.fn(), openAuthenticatedDocument: vi.fn(), revokeAuthenticatedDocument: vi.fn() }))

vi.mock("../../lib/receipts-api", () => ({ receiptsApi: apiMocks }))
vi.mock("../../lib/documentClient", async () => {
  const actual = await vi.importActual<typeof import("../../lib/documentClient")>("../../lib/documentClient")
  return { ...actual, fetchAuthenticatedDocument: documentMocks.fetchAuthenticatedDocument, openAuthenticatedDocument: documentMocks.openAuthenticatedDocument, revokeAuthenticatedDocument: documentMocks.revokeAuthenticatedDocument }
})

const receipt: ReceiptRecord = {
  id: "receipt-print-1",
  receipt_number: "RCT-2026-000001",
  receipt_date: "2026-08-24",
  payer_display: "Amani Assurance Partner",
  payer_id: "partner-1",
  branch_display: "Zanzibar Main Branch",
  branch_id: "branch-1",
  payment_mode_display: "Cash",
  payment_mode: "CASH",
  currency_display: "TZS — Tanzanian Shilling",
  currency: "TZS",
  receipt_amount: "150000.00",
  allocated_amount: "50000.00",
  unallocated_amount: "100000.00",
  status: "REVERSED",
  created_by_display: "Sultan Admin",
  allowed_actions: ["view", "print"],
}

const document: ReceiptDocument = {
  id: "document-1",
  document_type: "RECEIPT",
  template_name: "Official Receipt",
  template_version: 2,
  generated_by_display: "Sultan Admin",
  generated_at: "2026-08-24T08:35:00Z",
  page_count: 2,
  signed_download_url: "/api/v1/front-office/receipts/receipt-print-1/documents/document-1/download/?ticket=receipt-ticket",
}

function renderWithProviders(children: React.ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={client}><MemoryRouter><ToastProvider>{children}</ToastProvider></MemoryRouter></QueryClientProvider>)
}

beforeEach(() => {
  vi.clearAllMocks()
  apiMocks.print.mockResolvedValue({ receipt, document })
  apiMocks.documents.mockResolvedValue({ count: 1, next: null, previous: null, results: [document] })
  documentMocks.fetchAuthenticatedDocument.mockResolvedValue({ blob: new Blob(["%PDF-1.7"], { type: "application/pdf" }), objectUrl: "blob:receipt-preview", contentType: "application/pdf" })
  documentMocks.openAuthenticatedDocument.mockResolvedValue({ blob: new Blob(["%PDF-1.7"], { type: "application/pdf" }), objectUrl: "blob:receipt-download", contentType: "application/pdf" })
})

describe("ReceiptPrintPreview Prompt 8", () => {
  it("renders an authenticated PDF blob and displays the reversed watermark", async () => {
    renderWithProviders(<ReceiptPrintPreviewModal open receipt={receipt} onClose={vi.fn()} />)
    expect(await screen.findByTitle("RCT-2026-000001 branded PDF")).toHaveAttribute("src", "blob:receipt-preview")
    expect(screen.getAllByText("REVERSED").length).toBeGreaterThan(0)
    expect(documentMocks.fetchAuthenticatedDocument).toHaveBeenCalledWith(document.signed_download_url, "pdf")
  })

  it("downloads through the authenticated client and opens only the signed ticket in a new tab", async () => {
    const openMock = vi.spyOn(window, "open").mockImplementation(() => null)
    renderWithProviders(<ReceiptDocumentsPanel receipt={receipt} canPrint onGenerate={vi.fn()} onPreview={vi.fn()} />)
    await screen.findByText("Official Receipt")
    expect(screen.queryByText("document-1")).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "Download" }))
    await waitFor(() => expect(documentMocks.openAuthenticatedDocument).toHaveBeenCalledWith(document.signed_download_url, expect.objectContaining({ kind: "pdf", mode: "download" })))
    fireEvent.click(screen.getByRole("button", { name: "Open in new tab" }))
    expect(openMock).toHaveBeenCalledWith(document.signed_download_url, "_blank", "noopener,noreferrer")
    expect(openMock.mock.calls.some(([url]) => String(url).includes("/api/") && url !== document.signed_download_url)).toBe(false)
    openMock.mockRestore()
  })

  it("shows the branding settings coach when print generation is pending", async () => {
    apiMocks.print.mockRejectedValueOnce(new ApiClientError({ status: 422, code: "PARAMETER_MISSING", message: "Receipt branding is not configured.", fieldErrors: {}, resolutionSteps: ["Configure the company logo and contact details."] }))
    renderWithProviders(<ReceiptPrintPreviewModal open receipt={receipt} onClose={vi.fn()} />)
    expect(await screen.findByText(/Configure receipt document branding in System Parameters/)).toBeInTheDocument()
    expect(screen.getByRole("link", { name: "Open branding settings" })).toHaveAttribute("href", "/system-parameters/documents/branding")
  })
})
