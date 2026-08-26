import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen } from "@testing-library/react"
import { MemoryRouter, Route, Routes } from "react-router-dom"
import { beforeEach, describe, expect, it, vi } from "vitest"
import type { PortalReceiptRecord } from "../../lib/receipts-api"
import { PortalReceiptDetail, PortalReceipts, PORTAL_RECEIPTS_HELP_MESSAGE } from "./PortalReceipts"

const apiMocks = vi.hoisted(() => ({ portalList: vi.fn(), portalGet: vi.fn() }))
vi.mock("../../lib/receipts-api", () => ({ receiptsApi: { portal: { list: apiMocks.portalList, get: apiMocks.portalGet } } }))

const receipt: PortalReceiptRecord = {
  id: "portal-receipt-1",
  receipt_number: "RCT-2026-000001",
  receipt_date: "2026-08-24",
  payer_display: "Amani Assurance Partner",
  payer_id: "partner-1",
  branch_display: "Zanzibar Main Branch",
  branch_id: "branch-1",
  payment_mode_display: "Mobile Money",
  payment_mode: "MOBILE_MONEY",
  currency_display: "TZS — Tanzanian Shilling",
  currency: "TZS",
  receipt_amount: "150000.00",
  allocated_amount: "50000.00",
  unallocated_amount: "100000.00",
  status: "PARTIALLY_ALLOCATED",
  created_by_display: "Sultan Admin",
  allowed_actions: [],
  allocations: [{ id: "portal-allocation-1", commitment_display: "OLC-2026-000001 — Elimu Bora Growth", amount: "50000.00", currency: "TZS", payment_mode_display: "Mobile Money", receipt_reference: "RCT-2026-000001", allocated_at: "2026-08-24T08:45:00Z" }],
}

function renderWithQuery(children: React.ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={client}><MemoryRouter>{children}</MemoryRouter></QueryClientProvider>)
}

beforeEach(() => {
  vi.clearAllMocks()
  apiMocks.portalList.mockResolvedValue({ count: 1, next: null, previous: null, results: [receipt] })
  apiMocks.portalGet.mockResolvedValue(receipt)
})

describe("PortalReceipts Prompt 9", () => {
  it("shows only the server-scoped partner receipt list and no staff actions", async () => {
    renderWithQuery(<PortalReceipts />)
    expect(await screen.findByText("RCT-2026-000001")).toBeInTheDocument()
    expect(screen.getByText("My Receipts")).toBeInTheDocument()
    expect(screen.getByText(PORTAL_RECEIPTS_HELP_MESSAGE)).toBeInTheDocument()
    expect(screen.getByTestId("raise-ticket")).toHaveAttribute("href", "/tickets")
    expect(screen.queryByRole("button", { name: /post|reverse|cancel|allocate/i })).not.toBeInTheDocument()
    expect(apiMocks.portalList).toHaveBeenCalledWith({ page: 1, page_size: 50 })
  })

  it("renders the read-only detail with only own allocations and no lifecycle actions", async () => {
    render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter initialEntries={["/portal/receipts/portal-receipt-1"]}><Routes><Route path="/portal/receipts/:id" element={<PortalReceiptDetail />} /></Routes></MemoryRouter></QueryClientProvider>)
    expect(await screen.findByText("My payment allocations")).toBeInTheDocument()
    expect(screen.getByText("OLC-2026-000001 — Elimu Bora Growth")).toBeInTheDocument()
    expect(screen.getByText(PORTAL_RECEIPTS_HELP_MESSAGE)).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /post|reverse|cancel|allocate|print/i })).not.toBeInTheDocument()
    expect(apiMocks.portalGet).toHaveBeenCalledWith("portal-receipt-1")
  })

  it("sanitizes portal failures instead of exposing backend details", async () => {
    apiMocks.portalList.mockRejectedValueOnce(new Error("Database UUID 8b7d internal stack trace"))
    renderWithQuery(<PortalReceipts />)
    expect(await screen.findByText("The request could not be completed. Please try again or contact your ZIC representative.")).toBeInTheDocument()
    expect(screen.queryByText(/Database UUID|internal stack trace/)).not.toBeInTheDocument()
  })
})
