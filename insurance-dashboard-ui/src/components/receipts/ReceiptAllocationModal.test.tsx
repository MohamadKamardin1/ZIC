import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { MemoryRouter } from "react-router-dom"
import { ToastProvider } from "../../components/ui/Toast"
import { ApiClientError } from "../../lib/apiClient"
import type { ReceiptRecord } from "../../lib/receipts-api"
import { ReceiptAllocationModal } from "./ReceiptAllocationModal"

const apiMocks = vi.hoisted(() => ({ allocationOptions: vi.fn(), allocate: vi.fn(), autoAllocate: vi.fn() }))
vi.mock("../../lib/receipts-api", () => ({ receiptsApi: apiMocks }))

const receipt: ReceiptRecord = {
  id: "receipt-prompt5",
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
  allowed_actions: ["allocate", "auto_allocate"],
}

const options = [{ id: "commitment-1", commitment_number: "OLC-2026-000001", source_display: "OL Proposal OLP-2026-000001", product_display: "Elimu Bora", plan_display: "Growth Plan", due_date: "2026-08-24", balance: "50000.00", currency: "TZS", status: "PENDING", is_first_premium: true, proposal_number: "OLP-2026-000001" }]

function renderModal(overrides: Partial<ReceiptRecord> = {}) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={client}><MemoryRouter><ToastProvider><ReceiptAllocationModal open receipt={{ ...receipt, ...overrides }} onClose={vi.fn()} onSuccess={vi.fn()} /></ToastProvider></MemoryRouter></QueryClientProvider>)
}

beforeEach(() => {
  vi.clearAllMocks()
  apiMocks.allocationOptions.mockResolvedValue({ count: 1, next: null, previous: null, results: options })
  apiMocks.allocate.mockResolvedValue({ receipt: { ...receipt, allocated_amount: "100000.00", unallocated_amount: "50000.00" }, allocations: [] })
  apiMocks.autoAllocate.mockResolvedValue({ receipt: { ...receipt, allocated_amount: receipt.receipt_amount, unallocated_amount: "0.00", status: "ALLOCATED" }, allocations: [{ id: "allocation-1", target_display: "OLC-2026-000001 — OL Proposal OLP-2026-000001", amount: "50000.00", currency: "TZS", is_first_premium: true, proposal_number: "OLP-2026-000001" }], remaining_unallocated_amount: "0.00", first_premium_completed: true, first_premium_proposal_number: "OLP-2026-000001" })
})

describe("ReceiptAllocationModal Prompt 5", () => {
  it("blocks running total over-allocation before submitting", async () => {
    renderModal()
    const amount = await screen.findByLabelText(/Amount for OLC-2026-000001/)
    fireEvent.change(amount, { target: { value: "120000" } })
    fireEvent.click(screen.getByRole("button", { name: "Record Allocation" }))
    expect(await screen.findByText(/exceeds the unallocated receipt balance/)).toBeInTheDocument()
    expect(apiMocks.allocate).not.toHaveBeenCalled()
  })

  it("confirms oldest-first auto-allocation and renders its result summary", async () => {
    renderModal()
    await screen.findByText("OLC-2026-000001")
    fireEvent.click(screen.getByRole("button", { name: "Auto-Allocate oldest-first" }))
    const confirmDialog = screen.getAllByRole("dialog").find((dialog) => dialog.textContent?.includes("oldest eligible open commitments"))
    expect(confirmDialog).toBeDefined()
    expect(confirmDialog).toHaveTextContent("oldest eligible open commitments")
    fireEvent.click(within(confirmDialog as HTMLElement).getByRole("button", { name: "Run Auto-Allocate" }))
    await waitFor(() => expect(apiMocks.autoAllocate).toHaveBeenCalledWith(receipt.id))
    expect(await screen.findByText("Auto-allocation complete")).toBeInTheDocument()
    expect(screen.getByText(/Remaining unallocated amount/)).toBeInTheDocument()
    expect(screen.getByText("OLC-2026-000001 — OL Proposal OLP-2026-000001")).toBeInTheDocument()
  })

  it("shows a first-premium completion banner linking to the proposal", async () => {
    renderModal()
    await screen.findByText("OLC-2026-000001")
    fireEvent.click(screen.getByRole("button", { name: "Auto-Allocate oldest-first" }))
    fireEvent.click(await screen.findByRole("button", { name: "Run Auto-Allocate" }))
    expect(await screen.findByText(/First premium posted/)).toBeInTheDocument()
    expect(screen.getByRole("link", { name: "OLP-2026-000001" })).toHaveAttribute("href", "/ordinary-life/quotations?search=OLP-2026-000001")
  })

  it("previews cross-currency conversion and coaches when the rate is missing", async () => {
    apiMocks.allocationOptions.mockResolvedValueOnce({ count: 1, next: null, previous: null, results: [{ ...options[0], currency: "USD", balance: "100.00", is_first_premium: false, proposal_number: null }] })
    renderModal()
    const amount = await screen.findByLabelText(/Amount for OLC-2026-000001/)
    fireEvent.change(amount, { target: { value: "10" } })
    expect(screen.getByText(/Exchange rate is required/)).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText(/Exchange rate for OLC-2026-000001/), { target: { value: "2500" } })
    expect(screen.getByText(/Converted:\s*TSh\s*25,000\.00/)).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText(/Exchange rate for OLC-2026-000001/), { target: { value: "" } })
    fireEvent.click(screen.getByRole("button", { name: "Record Allocation" }))
    expect(await screen.findByRole("link", { name: "Open exchange-rate parameters" })).toHaveAttribute("href", "/ordinary-life/parameters/default-setup?focus=exchange-rate")
    expect(apiMocks.allocate).not.toHaveBeenCalled()
  })

  it("renders a structured invalid-status allocation error from the backend", async () => {
    apiMocks.allocate.mockRejectedValueOnce(new ApiClientError({ status: 422, code: "RECEIPT_INVALID_STATUS", message: "Only posted receipts can be allocated.", fieldErrors: {}, resolutionSteps: ["Post the receipt before allocating it."] }))
    renderModal()
    const amount = await screen.findByLabelText(/Amount for OLC-2026-000001/)
    fireEvent.change(amount, { target: { value: "10000" } })
    fireEvent.click(screen.getByRole("button", { name: "Record Allocation" }))
    expect(await screen.findByText("Only posted receipts can be allocated.")).toBeInTheDocument()
    expect(screen.getByText("Post the receipt before allocating it.")).toBeInTheDocument()
  })
})
