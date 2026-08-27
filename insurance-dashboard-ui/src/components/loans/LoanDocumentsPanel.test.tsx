import { fireEvent, render, screen, waitFor, within } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { LoanDocumentsPanel } from "./LoanDocumentsPanel"
import type { LoanDetail } from "../../lib/loans"

const { requestMock, printLoanDocumentMock, fetchAuthenticatedDocumentMock, openAuthenticatedDocumentMock, revokeAuthenticatedDocumentMock } = vi.hoisted(() => ({
  requestMock: vi.fn(),
  printLoanDocumentMock: vi.fn(),
  fetchAuthenticatedDocumentMock: vi.fn(),
  openAuthenticatedDocumentMock: vi.fn(),
  revokeAuthenticatedDocumentMock: vi.fn(),
}))

vi.mock("../../lib/apiClient", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../lib/apiClient")>()
  return { ...actual, request: requestMock }
})

vi.mock("../../lib/loans", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../lib/loans")>()
  return { ...actual, printLoanDocument: printLoanDocumentMock }
})

vi.mock("../../lib/documentClient", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../lib/documentClient")>()
  return { ...actual, fetchAuthenticatedDocument: fetchAuthenticatedDocumentMock, openAuthenticatedDocument: openAuthenticatedDocumentMock, revokeAuthenticatedDocument: revokeAuthenticatedDocumentMock }
})

const loan = {
  id: "loan-internal-id",
  loanNumber: "OL-LOAN-2026-000001",
  policyNumber: "POL-2026-000001",
  policyDisplay: "POL-2026-000001 — Asha Mussa",
  policyholderName: "Asha Mussa",
  partnerDisplay: "Asha Mussa",
  productDisplay: "Elimu Bora Growth Plan",
  agentDisplay: "ZIC Agent",
  branchDisplay: "ZIC Main Branch",
  currency: "TZS",
  principalAmount: "1000000.00",
  cashValueSnapshot: "2000000.00",
  disbursedAmount: "1000000.00",
  repaymentMode: "MONTHLY",
  interestRate: "12.00",
  compoundingFrequency: "MONTHLY",
  termMonths: 12,
  disbursementDate: "2026-01-01",
  maturityDate: "2027-01-01",
  status: "DEFAULTED",
  statusDisplay: "Defaulted",
  totalRepaid: "250000.00",
  outstandingBalance: "750000.00",
  approvalRequired: false,
  approvedAt: null,
  rejectedAt: null,
  rejectionReason: "",
  reason: "",
  allowedActions: [],
  createdAt: "2026-01-01T10:00:00Z",
  updatedAt: "2026-01-01T10:00:00Z",
  schedules: [],
  repayments: [],
  interestAccruals: [],
  offsets: [],
  auditTimeline: [],
} as unknown as LoanDetail

beforeEach(() => {
  requestMock.mockResolvedValue({ count: 1, results: [{ id: "document-1", document_type: "OL_LOAN_AGREEMENT", template_name: "Loan Agreement", template_version: 2, generated_by_display: "ZIC Finance", generated_at: "2026-08-27T10:00:00Z", page_count: 2, signed_download_url: "/api/v1/documents/instances/document-1/download/?ticket=valid" }] })
  printLoanDocumentMock.mockResolvedValue({ instance: { id: "document-2", document_type: "OL_LOAN_AGREEMENT", template_name: "Loan Agreement", template_version: 3, generated_by_display: "ZIC Finance", generated_at: "2026-08-27T10:00:00Z", page_count: 2 }, previewUrl: "/api/v1/documents/instances/document-2/download/?ticket=preview", signedDownloadUrl: "/api/v1/documents/instances/document-2/download/?ticket=signed" })
  fetchAuthenticatedDocumentMock.mockResolvedValue({ blob: new Blob(["%PDF-test"], { type: "application/pdf" }), objectUrl: "blob:loan-preview", contentType: "application/pdf" })
  openAuthenticatedDocumentMock.mockResolvedValue(undefined)
  revokeAuthenticatedDocumentMock.mockImplementation(() => undefined)
})

describe("LoanDocumentsPanel", () => {
  it("lists documents, generates an agreement, previews the PDF, and shows defaulted watermark", async () => {
    render(<LoanDocumentsPanel loan={loan} canPrint />)
    expect(await screen.findByTestId("loan-documents-panel")).toBeInTheDocument()
    expect(screen.getByText(/DEFAULTED loan document watermark/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "Print Agreement" }))
    await waitFor(() => expect(printLoanDocumentMock).toHaveBeenCalledWith("loan-internal-id", "agreement"))
    expect(await screen.findByTitle("Loan Agreement PDF")).toBeInTheDocument()
    expect(fetchAuthenticatedDocumentMock).toHaveBeenCalledWith("/api/v1/documents/instances/document-2/download/?ticket=signed", "pdf")
    fireEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Download" }))
    await waitFor(() => expect(openAuthenticatedDocumentMock).toHaveBeenCalledWith("/api/v1/documents/instances/document-2/download/?ticket=signed", expect.objectContaining({ kind: "pdf", mode: "download" })))
  })

  it("generates the schedule through the same print pipeline and opens only a signed ticket", async () => {
    printLoanDocumentMock.mockResolvedValue({ instance: { id: "document-3", document_type: "OL_LOAN_SCHEDULE", template_name: "Repayment Schedule", template_version: 1, page_count: 3 }, previewUrl: "/preview", signedDownloadUrl: "/signed-schedule" })
    const openSpy = vi.spyOn(window, "open").mockImplementation(() => null)
    render(<LoanDocumentsPanel loan={{ ...loan, status: "SETTLED", statusDisplay: "Settled" }} canPrint />)
    await screen.findByTestId("loan-documents-panel")
    fireEvent.click(screen.getByRole("button", { name: "Print Schedule" }))
    await waitFor(() => expect(printLoanDocumentMock).toHaveBeenCalledWith("loan-internal-id", "schedule"))
    expect(await screen.findByTitle("Repayment Schedule PDF")).toBeInTheDocument()
    fireEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Open in New Tab" }))
    expect(openSpy).toHaveBeenCalledWith("/signed-schedule", "_blank", "noopener,noreferrer")
    openSpy.mockRestore()
  })

  it("turns a pending-template failure into a teachable ErrorCoach message", async () => {
    const { ApiClientError } = await import("../../lib/apiClient")
    printLoanDocumentMock.mockRejectedValue(new ApiClientError({ status: 409, code: "TEMPLATE_PENDING", message: "No active loan template is configured.", fieldErrors: {}, resolutionSteps: ["Configure the loan template."] }))
    render(<LoanDocumentsPanel loan={loan} canPrint />)
    await screen.findByTestId("loan-documents-panel")
    fireEvent.click(screen.getByRole("button", { name: "Print Agreement" }))
    expect(await screen.findByText(/Configure the loan document template and branding/)).toBeInTheDocument()
    expect(screen.getByRole("link", { name: "Open document settings" })).toHaveAttribute("href", "/system-parameters/documents/branding")
  })
})
