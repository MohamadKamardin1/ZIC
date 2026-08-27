import { fireEvent, render, screen, waitFor, within } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { ApiClientError, request } from "../../lib/apiClient"
import { fetchAuthenticatedDocument, openAuthenticatedDocument, revokeAuthenticatedDocument } from "../../lib/documentClient"
import type { WithdrawalDetail, WithdrawalPrintResult } from "../../lib/withdrawals"

const { printWithdrawalStatementMock } = vi.hoisted(() => ({ printWithdrawalStatementMock: vi.fn() }))

vi.mock("../../lib/apiClient", () => ({
  request: vi.fn(),
  ApiClientError: class ApiClientError extends Error {
    status = 409
    code = "TEMPLATE_PENDING"
    resolutionSteps = ["Configure the withdrawal statement template."]
    constructor(value: unknown) { super(typeof value === "string" ? value : String((value as { message?: unknown })?.message ?? "Api error")); this.name = "ApiClientError" }
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

vi.mock("../../lib/withdrawals", async () => {
  const actual = await vi.importActual<typeof import("../../lib/withdrawals")>("../../lib/withdrawals")
  return { ...actual, printWithdrawalStatement: printWithdrawalStatementMock }
})

import { WithdrawalDocumentsPanel } from "./WithdrawalDocumentsPanel"

const withdrawal = {
  id: "withdrawal-1",
  withdrawalNumber: "OL-WDR-2026-000001",
  policyId: "policy-1",
  policyNumber: "ZIC-OL-2026-000001",
  policyholderName: "Amani Salum",
  policyholderDisplay: "P-000001 — Amani Salum",
  productDisplay: "OL_EDU_GROWTH — Elimu Bora Growth Plan",
  agentDisplay: "AG-0004 — Faraja Intermediaries",
  branchDisplay: "ZNZ-MAIN — Zanzibar Main Branch",
  currency: "TZS",
  grossAmount: "250000.00",
  feeAmount: "12500.00",
  netPayout: "237500.00",
  cashValueBefore: "2500000.00",
  loanBalanceBefore: "150000.00",
  cashValueAfter: "2100000.00",
  status: "REQUESTED",
  statusDisplay: "Requested",
  reason: "Education expenses",
  requestedAt: "2026-08-27T09:00:00Z",
  approvedAt: null,
  processedAt: null,
  paidAt: null,
  allowedActions: ["view", "print"],
  createdAt: "2026-08-27T09:00:00Z",
  updatedAt: "2026-08-27T09:00:00Z",
  breakdown: null,
  payments: [],
  auditTimeline: [],
  policyContext: {},
} as unknown as WithdrawalDetail

const statement = {
  id: "document-statement-1",
  document_type: "OL_WITHDRAWAL_STATEMENT",
  template_name: "Withdrawal Statement",
  template_version: 1,
  generated_by_display: "Sultan Admin",
  generated_at: "2026-08-27T10:00:00Z",
  page_count: 2,
  signed_download_url: "/api/v1/documents/instances/document-statement-1/download/?ticket=withdrawal-ticket",
}

const paymentConfirmation = {
  id: "document-payment-1",
  document_type: "OL_WITHDRAWAL_PAYMENT_CONFIRMATION",
  template_name: "Payment Confirmation",
  template_version: 1,
  generated_by_display: "Finance Admin",
  generated_at: "2026-08-27T10:05:00Z",
  page_count: 1,
  signed_download_url: "/api/v1/documents/instances/document-payment-1/download/?ticket=payment-ticket",
}

const previewResult = { blob: new Blob(["%PDF"], { type: "application/pdf" }), objectUrl: "blob:withdrawal-preview", contentType: "application/pdf" }

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(request).mockResolvedValue({ results: [statement, paymentConfirmation] })
  vi.mocked(fetchAuthenticatedDocument).mockResolvedValue(previewResult)
  vi.mocked(openAuthenticatedDocument).mockResolvedValue(previewResult)
  printWithdrawalStatementMock.mockResolvedValue({ instance: statement, previewUrl: statement.signed_download_url, signedDownloadUrl: statement.signed_download_url } satisfies WithdrawalPrintResult)
})

describe("WithdrawalDocumentsPanel", () => {
  it("loads statement and payment confirmation records with secure actions", async () => {
    render(<WithdrawalDocumentsPanel withdrawal={withdrawal} canPrint />)
    expect((await screen.findAllByText("Withdrawal Statement")).length).toBeGreaterThan(0)
    expect((await screen.findAllByText("Payment Confirmation")).length).toBeGreaterThan(0)
    expect(screen.getByText("Sultan Admin")).toBeInTheDocument()
    expect(screen.getAllByRole("button", { name: "Preview" })).toHaveLength(2)
    expect(screen.getAllByRole("button", { name: "Download" })).toHaveLength(2)
    expect(screen.getByRole("button", { name: "Print Statement" })).toBeInTheDocument()
  })

  it("generates a statement and opens the authenticated PDF preview", async () => {
    render(<WithdrawalDocumentsPanel withdrawal={withdrawal} canPrint />)
    await screen.findAllByText("Withdrawal Statement")
    fireEvent.click(screen.getByRole("button", { name: "Print Statement" }))
    expect(await screen.findByTitle("Withdrawal Statement PDF")).toHaveAttribute("src", "blob:withdrawal-preview")
    expect(printWithdrawalStatementMock).toHaveBeenCalledWith("withdrawal-1")
    expect(fetchAuthenticatedDocument).toHaveBeenCalledWith(statement.signed_download_url, "pdf")
  })

  it("shows CANCELLED watermark messaging and supports authenticated download", async () => {
    const cancelled = { ...withdrawal, status: "CANCELLED", statusDisplay: "Cancelled" } as WithdrawalDetail
    render(<WithdrawalDocumentsPanel withdrawal={cancelled} canPrint />)
    expect(await screen.findByText(/generated statement carries a visible/i)).toHaveTextContent("CANCELLED")
    fireEvent.click(screen.getAllByRole("button", { name: "Preview" })[0])
    expect(await screen.findByText(/This withdrawal is CANCELLED/)).toBeInTheDocument()
    const previewDialog = await screen.findByRole("dialog", { name: "Withdrawal Statement · PDF" })
    fireEvent.click(within(previewDialog).getByRole("button", { name: "Download" }))
    await waitFor(() => expect(openAuthenticatedDocument).toHaveBeenCalledWith(statement.signed_download_url, expect.objectContaining({ kind: "pdf", mode: "download" })))
  })

  it("shows a teachable ErrorCoach when the withdrawal template is pending", async () => {
    vi.mocked(request).mockRejectedValueOnce(new ApiClientError({ status: 409, code: "TEMPLATE_PENDING", message: "The withdrawal statement template is pending.", fieldErrors: {}, resolutionSteps: ["Configure the withdrawal statement template."] }))
    render(<WithdrawalDocumentsPanel withdrawal={withdrawal} canPrint />)
    expect(await screen.findByText("The withdrawal statement template is pending.")).toBeInTheDocument()
    expect(screen.getByRole("link", { name: "Open document settings" })).toHaveAttribute("href", "/system-parameters/documents/branding")
  })

  it("revokes the authenticated preview on unmount", async () => {
    const view = render(<WithdrawalDocumentsPanel withdrawal={withdrawal} canPrint />)
    await screen.findAllByText("Withdrawal Statement")
    fireEvent.click(screen.getAllByRole("button", { name: "Preview" })[0])
    await screen.findByTitle("Withdrawal Statement PDF")
    view.unmount()
    expect(revokeAuthenticatedDocument).toHaveBeenCalled()
  })
})
