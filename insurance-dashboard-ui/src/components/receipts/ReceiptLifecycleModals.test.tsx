import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { ToastProvider } from "../../components/ui/Toast"
import { ApiClientError } from "../../lib/apiClient"
import type { ReceiptAllocation, ReceiptRecord } from "../../lib/receipts-api"
import { AllocationReversalModal, CancelDraftModal, ReceiptReversalModal } from "./ReceiptLifecycleModals"

const apiMocks = vi.hoisted(() => ({ allocations: vi.fn(), reverse: vi.fn(), reverseAllocation: vi.fn(), cancel: vi.fn() }))
vi.mock("../../lib/receipts-api", () => ({ receiptsApi: apiMocks }))

const receipt: ReceiptRecord = {
  id: "receipt-prompt6",
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
  status: "POSTED",
  created_by_display: "Sultan Admin",
  bank_account_display: "**** 0042",
  allowed_actions: ["reverse", "cancel", "allocate"],
}

const allocation: ReceiptAllocation = {
  id: "allocation-1",
  target_display: "OLC-2026-000001 — OL Proposal OLP-2026-000001",
  commitment_number: "OLC-2026-000001",
  source_display: "OL Proposal OLP-2026-000001",
  amount: "50000.00",
  currency: "TZS",
  exchange_rate: null,
  status: "ACTIVE",
  reversed_at: null,
  is_first_premium: true,
  proposal_number: "OLP-2026-000001",
  restored_balance: "50000.00",
}

function renderWithProviders(children: React.ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={client}><MemoryRouter><ToastProvider>{children}</ToastProvider></MemoryRouter></QueryClientProvider>)
}

beforeEach(() => {
  vi.clearAllMocks()
  apiMocks.allocations.mockResolvedValue({ count: 1, next: null, previous: null, results: [allocation] })
  apiMocks.reverse.mockResolvedValue({ ...receipt, status: "REVERSED", reversed_reason: "Duplicate payment" })
  apiMocks.reverseAllocation.mockResolvedValue({ ...allocation, status: "REVERSED", reversed_at: "2026-08-24T09:10:00Z" })
  apiMocks.cancel.mockResolvedValue({ ...receipt, status: "CANCELLED", cancelled_reason: "Draft error" })
})

describe("ReceiptLifecycleModals Prompt 6", () => {
  it("lists every impacted allocation and warns about first-premium conversion", async () => {
    renderWithProviders(<ReceiptReversalModal open receipt={receipt} onClose={vi.fn()} onSuccess={vi.fn()} />)
    expect((await screen.findAllByText("OLC-2026-000001 — OL Proposal OLP-2026-000001")).length).toBeGreaterThan(0)
    expect(screen.getByText("Restored balance")).toBeInTheDocument()
    expect(screen.getByText(/Proposal conversion guard will return to false/)).toBeInTheDocument()
    expect(screen.getAllByText(/50,000\.00/).length).toBeGreaterThan(0)
  })

  it("requires a reason before receipt reversal and allocation reversal", async () => {
    renderWithProviders(<ReceiptReversalModal open receipt={receipt} onClose={vi.fn()} onSuccess={vi.fn()} />)
    await screen.findByText("Impact preview")
    fireEvent.click(screen.getByRole("button", { name: "Confirm reversal" }))
    expect(await screen.findByText(/Enter a reason so the audit trail explains/)).toBeInTheDocument()
    expect(apiMocks.reverse).not.toHaveBeenCalled()

    cleanup()
    renderWithProviders(<AllocationReversalModal open receipt={receipt} allocation={allocation} onClose={vi.fn()} onSuccess={vi.fn()} />)
    fireEvent.click(screen.getByRole("button", { name: "Confirm allocation reversal" }))
    expect(await screen.findByText(/Enter a reason so the audit trail explains/)).toBeInTheDocument()
    expect(apiMocks.reverseAllocation).not.toHaveBeenCalled()
  })

  it("renders the lock-period coach returned by the reversal endpoint", async () => {
    apiMocks.reverse.mockRejectedValueOnce(new ApiClientError({ status: 422, code: "RECEIPT_REVERSAL_LOCKED", message: "This receipt is outside the permitted reversal period.", fieldErrors: {}, resolutionSteps: ["Ask Finance Control to approve an exception.", "Review the configured reversal lock period."], deepLink: "/ordinary-life/parameters/default-setup?focus=reversal-lock-period" }))
    renderWithProviders(<ReceiptReversalModal open receipt={receipt} onClose={vi.fn()} onSuccess={vi.fn()} />)
    await screen.findByText("Impact preview")
    fireEvent.change(screen.getByLabelText(/Reason/), { target: { value: "Correction requested" } })
    fireEvent.click(screen.getByRole("button", { name: "Confirm reversal" }))
    expect(await screen.findByText("This receipt is outside the permitted reversal period.")).toBeInTheDocument()
    expect(screen.getByText("Ask Finance Control to approve an exception.")).toBeInTheDocument()
    expect(screen.getByRole("link", { name: "Open resolution page" })).toHaveAttribute("href", "/ordinary-life/parameters/default-setup?focus=reversal-lock-period")
  })

  it("submits cancellation only for a draft and shows its success mutation", async () => {
    renderWithProviders(<CancelDraftModal open receipt={{ ...receipt, status: "DRAFT" }} onClose={vi.fn()} onSuccess={vi.fn()} />)
    fireEvent.change(screen.getByLabelText(/Reason/), { target: { value: "Duplicate draft" } })
    fireEvent.click(screen.getByRole("button", { name: "Confirm cancellation" }))
    await waitFor(() => expect(apiMocks.cancel).toHaveBeenCalledWith(receipt.id, { reason: "Duplicate draft" }))

    cleanup()
    renderWithProviders(<CancelDraftModal open receipt={receipt} onClose={vi.fn()} onSuccess={vi.fn()} />)
    expect(screen.getByText(/Only receipts in Draft status can be cancelled/)).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Confirm cancellation" })).toBeDisabled()
  })
})
