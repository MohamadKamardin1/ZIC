import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen, waitFor, fireEvent } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import { beforeEach, describe, expect, it, vi } from "vitest"
import FOReceipts from "./FOReceipts"
import { receiptsApi } from "../../lib/receipts-api"

vi.mock("../../lib/access", () => ({
  useAccess: () => ({
    access: {
      permissions: [
        { module: "front_office.receipts", action: "view" },
        { module: "front_office.receipts", action: "create" },
        { module: "front_office.receipts", action: "import" },
        { module: "front_office.receipts", action: "print" },
      ],
    },
    isSuperAdmin: false,
    hasPermission: (code: string) => ["front_office.receipts.view", "front_office.receipts.create", "front_office.receipts.import", "front_office.receipts.print"].includes(code),
  }),
}))

vi.mock("../../lib/receipts-api", () => ({ receiptsApi: {
  list: vi.fn(),
  kpis: vi.fn(),
  options: { branches: vi.fn(), currencies: vi.fn(), paymentModes: vi.fn(), statuses: vi.fn() },
  importDryRun: vi.fn(),
} }))

const mockedReceiptsApi = vi.mocked(receiptsApi)

const row: import("../../lib/receipts-api").ReceiptRecord = {
  id: "receipt-1",
  receipt_number: "RCT-2026-000001",
  receipt_date: "2026-08-24",
  payer_display: "Amani Assurance Partner",
  branch_display: "Zanzibar Main Branch",
  payment_mode_display: "Mobile Money",
  payment_mode: "MOBILE_MONEY",
  currency_display: "TZS — Tanzanian Shilling",
  currency: "TZS",
  receipt_amount: "150000.00",
  allocated_amount: "50000.00",
  unallocated_amount: "100000.00",
  source_module: "OL_PROPOSAL",
  created_by_display: "Sultan Admin",
  posted_by_display: "Sultan Admin",
  status: "PARTIALLY_ALLOCATED",
  allowed_actions: ["view", "print"],
}

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={client}><MemoryRouter><FOReceipts /></MemoryRouter></QueryClientProvider>)
}

beforeEach(() => {
  vi.clearAllMocks()
  mockedReceiptsApi.list.mockResolvedValue({ count: 1, next: null, previous: null, results: [row], page: 1, page_size: 20 })
  mockedReceiptsApi.kpis.mockResolvedValue({ received_today: "150000.00", allocated_in_period: "50000.00", unallocated_amount: "100000.00", receipt_count: 1, reversed_amount: "0.00" })
  vi.mocked(receiptsApi.options.branches).mockResolvedValue({ count: 1, next: null, previous: null, results: [{ value: "branch-1", label: "Zanzibar Main Branch" }] })
  vi.mocked(receiptsApi.options.currencies).mockResolvedValue({ count: 1, next: null, previous: null, results: [{ value: "TZS", label: "TZS — Tanzanian Shilling" }] })
  vi.mocked(receiptsApi.options.paymentModes).mockResolvedValue({ count: 1, next: null, previous: null, results: [{ value: "MOBILE_MONEY", label: "Mobile Money" }] })
  vi.mocked(receiptsApi.options.statuses).mockResolvedValue({ count: 1, next: null, previous: null, results: [{ value: "PARTIALLY_ALLOCATED", label: "Partially allocated" }] })
})

describe("FOReceipts Prompt 2 work queue", () => {
  it("renders all KPI cards and contract columns", async () => {
    renderPage()
    expect(await screen.findByText("Received Today")).toBeInTheDocument()
    expect(screen.getByText("Allocated in Period")).toBeInTheDocument()
    expect(screen.getByText("Unallocated Amount")).toBeInTheDocument()
    expect(screen.getByText("Receipt Count")).toBeInTheDocument()
    expect(screen.getByText("Reversed Amount")).toBeInTheDocument()
    expect(await screen.findByText("RCT-2026-000001")).toBeInTheDocument()
    expect(screen.getByText("Amani Assurance Partner")).toBeInTheDocument()
    expect(screen.getAllByText("Zanzibar Main Branch").length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText("Mobile Money").length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText("Partially allocated").length).toBeGreaterThanOrEqual(1)
  })

  it("maps quick chips and filters into the server query", async () => {
    renderPage()
    await screen.findByText("RCT-2026-000001")
    fireEvent.click(screen.getByRole("button", { name: "Unallocated Only" }))
    await waitFor(() => expect(mockedReceiptsApi.list).toHaveBeenCalledWith(expect.objectContaining({ unallocated_only: true })))
    fireEvent.change(screen.getByLabelText("Search"), { target: { value: "Amani" } })
    await waitFor(() => expect(mockedReceiptsApi.list).toHaveBeenCalledWith(expect.objectContaining({ search: "Amani", unallocated_only: true })))
  })

  it("shows only permission- and backend-allowed row actions", async () => {
    renderPage()
    await screen.findByText("RCT-2026-000001")
    fireEvent.click(screen.getByRole("button", { name: "Actions for row 1" }))
    expect(screen.getByRole("button", { name: "View" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Print" })).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Post" })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Reverse" })).not.toBeInTheDocument()
  })

  it("exposes New Receipt, Import CSV, and filtered export controls", async () => {
    const createObjectUrl = vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:receipts-export")
    const revokeObjectUrl = vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => undefined)
    renderPage()
    await screen.findByText("RCT-2026-000001")
    fireEvent.click(screen.getByRole("button", { name: "Reversed Only" }))
    await waitFor(() => expect(mockedReceiptsApi.list).toHaveBeenCalledWith(expect.objectContaining({ reversed_only: true })))
    expect(screen.getByRole("button", { name: /New Receipt/i })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /Import CSV/i })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /Export CSV/i })).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: /Export CSV/i }))
    expect(createObjectUrl).toHaveBeenCalledWith(expect.any(Blob))
    expect(revokeObjectUrl).toHaveBeenCalledWith("blob:receipts-export")
    createObjectUrl.mockRestore()
    revokeObjectUrl.mockRestore()
  })

  it("shows an ErrorCoach when the receipts fetch fails", async () => {
    mockedReceiptsApi.list.mockRejectedValueOnce(new Error("Receipts API is unavailable."))
    renderPage()
    expect(await screen.findByRole("alert")).toHaveTextContent("Receipts API is unavailable.")
  })
})
