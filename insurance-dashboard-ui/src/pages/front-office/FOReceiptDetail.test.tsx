import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { MemoryRouter, Route, Routes } from "react-router-dom"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { ToastProvider } from "../../components/ui/Toast"
import FOReceiptDetail from "./FOReceiptDetail"

const apiMocks = vi.hoisted(() => ({
  get: vi.fn(),
  allocations: vi.fn(),
  reversals: vi.fn(),
  documents: vi.fn(),
  auditTimeline: vi.fn(),
  revealBankAccount: vi.fn(),
}))

vi.mock("../../lib/access", () => ({
  useAccess: () => ({
    access: { permissions: [
      { module: "front_office.receipts", action: "view" },
      { module: "front_office.receipts", action: "view_bank_account" },
      { module: "front_office.receipts", action: "edit" },
      { module: "front_office.receipts", action: "post" },
      { module: "front_office.receipts", action: "allocate" },
      { module: "front_office.receipts", action: "reverse" },
      { module: "front_office.receipts", action: "cancel" },
      { module: "front_office.receipts", action: "print" },
    ] },
    isSuperAdmin: false,
    hasPermission: (code: string) => [
      "front_office.receipts.view", "front_office.receipts.view_bank_account", "front_office.receipts.edit", "front_office.receipts.post",
      "front_office.receipts.allocate", "front_office.receipts.reverse", "front_office.receipts.cancel", "front_office.receipts.print",
    ].includes(code),
  }),
}))

vi.mock("../../lib/receipts-api", () => ({ receiptsApi: apiMocks }))

const receipt = {
  id: "receipt-detail-1",
  receipt_number: "RCT-2026-000001",
  receipt_date: "2026-08-24",
  payer_display: "Amani Assurance Partner",
  payer_id: "partner-1",
  branch_display: "Zanzibar Main Branch",
  branch_id: "branch-1",
  payment_mode_display: "Bank Transfer",
  payment_mode: "BANK_TRANSFER",
  currency_display: "TZS — Tanzanian Shilling",
  currency: "TZS",
  receipt_amount: "150000.00",
  allocated_amount: "50000.00",
  unallocated_amount: "100000.00",
  source_module: "OL_PROPOSAL",
  source_reference_display: "OLP-2026-000001",
  payment_reference: "CRDB-20260824-001",
  bank_account_display: "**** 0042",
  status: "PARTIALLY_ALLOCATED",
  created_by_display: "Sultan Admin",
  posted_by_display: "Sultan Admin",
  posted_at: "2026-08-24T08:30:00Z",
  allowed_actions: ["view", "edit", "post", "allocate", "auto_allocate", "reverse", "cancel", "print"],
}

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={client}><MemoryRouter initialEntries={["/front-office/receipts/receipt-detail-1"]}><ToastProvider><Routes><Route path="/front-office/receipts/:id" element={<FOReceiptDetail />} /></Routes></ToastProvider></MemoryRouter></QueryClientProvider>)
}

beforeEach(() => {
  vi.clearAllMocks()
  apiMocks.get.mockResolvedValue(receipt)
  apiMocks.allocations.mockResolvedValue({ count: 1, next: null, previous: null, results: [{ id: "allocation-1", target_display: "OLC-2026-000001 — OL Proposal OLP-2026-000001", commitment_number: "OLC-2026-000001", source_display: "OL Proposal OLP-2026-000001", amount: "50000.00", currency: "TZS", exchange_rate: null, status: "ACTIVE", reversed_at: null }] })
  apiMocks.reversals.mockResolvedValue({ count: 0, next: null, previous: null, results: [] })
  apiMocks.documents.mockResolvedValue({ count: 1, next: null, previous: null, results: [{ id: "document-1", document_type: "RECEIPT", template_name: "Official Receipt", template_version: 1, generated_by_display: "Sultan Admin", generated_at: "2026-08-24T08:35:00Z", page_count: 1, preview_url: "/documents/preview", signed_download_url: "/documents/download?ticket=short" }] })
  apiMocks.auditTimeline.mockResolvedValue({ count: 6, next: null, previous: null, results: [
    { id: "audit-create", action: "create", actor_display: "Sultan Admin", occurred_at: "2026-08-24T08:00:00Z", after_summary: "Draft receipt created", reason: "Payment captured", source_channel: "UI" },
    { id: "audit-post", action: "post", actor_display: "Sultan Admin", occurred_at: "2026-08-24T08:30:00Z", before_summary: "DRAFT", after_summary: "POSTED", reason: "Payment verified", source_channel: "UI" },
    { id: "audit-allocate", action: "allocate", actor_display: "Sultan Admin", occurred_at: "2026-08-24T08:45:00Z", before_summary: "Unallocated", after_summary: "Allocated", reason: "Commitment selected", source_channel: "UI" },
    { id: "audit-reverse", action: "reverse", actor_display: "Sultan Admin", occurred_at: "2026-08-24T09:00:00Z", before_summary: "POSTED", after_summary: "REVERSED", reason: "Correction", source_channel: "UI" },
    { id: "audit-cancel", action: "cancel", actor_display: "Sultan Admin", occurred_at: "2026-08-24T09:15:00Z", before_summary: "DRAFT", after_summary: "CANCELLED", reason: "Duplicate", source_channel: "UI" },
    { id: "audit-print", action: "print", actor_display: "Sultan Admin", occurred_at: "2026-08-24T09:30:00Z", before_summary: "No document", after_summary: "Official Receipt v1", reason: "Print requested", source_channel: "UI" },
  ] })
  apiMocks.revealBankAccount.mockResolvedValue({ bank_account_display: "CRDB Zanzibar Operations · Account ending 0042" })
})

describe("FOReceiptDetail Prompt 4", () => {
  it("renders the master-detail header, account details, tabs, allocation payload, and documents payload", async () => {
    renderPage()
    expect(await screen.findByText("RCT-2026-000001")).toBeInTheDocument()
    expect(screen.getByText(/Amani Assurance Partner · Zanzibar Main Branch/)).toBeInTheDocument()
    expect(screen.getAllByText(/OLP-2026-000001/).length).toBeGreaterThan(0)
    expect(screen.getByRole("button", { name: "Allocations" })).toHaveAttribute("aria-current", "page")
    expect(await screen.findByText("OLC-2026-000001 — OL Proposal OLP-2026-000001")).toBeInTheDocument()
    fireEvent.click(await screen.findByRole("button", { name: "Documents" }))
    expect(await screen.findByText("Official Receipt")).toBeInTheDocument()
    expect(screen.getByText("v1")).toBeInTheDocument()
  })

  it("reveals and hides the bank account only with the view-bank-account permission", async () => {
    renderPage()
    expect(await screen.findByText("**** 0042")).toBeInTheDocument()
    fireEvent.click(await screen.findByRole("button", { name: "Show account" }))
    expect(await screen.findByText("CRDB Zanzibar Operations · Account ending 0042")).toBeInTheDocument()
    expect(apiMocks.revealBankAccount).toHaveBeenCalledWith("receipt-detail-1")
    fireEvent.click(screen.getByRole("button", { name: "Hide account" }))
    expect(screen.getByText("**** 0042")).toBeInTheDocument()
  })

  it("renders a complete audit timeline with lifecycle action labels and no UUIDs", async () => {
    renderPage()
    fireEvent.click(await screen.findByRole("button", { name: "Audit Timeline" }))
    expect(await screen.findByRole("heading", { name: "Audit Timeline" })).toBeInTheDocument()
    for (const action of ["Create", "Post", "Allocate", "Reverse", "Cancel", "Print"]) expect((await screen.findAllByText(action)).length).toBeGreaterThan(0)
    expect(document.body.textContent).toContain("Sultan Admin")
    expect(document.body.textContent).not.toMatch(/[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}/i)
  })
})
