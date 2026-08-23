import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { beforeEach, describe, expect, it, vi } from "vitest"
import OLProposals, { proposalRowActionEnabled } from "./OLProposals"

const {
  navigateMock,
  listProposalsMock,
  kpisMock,
  optionsMock,
  exportCsvMock,
  printMock,
  createFromQuotationMock,
} = vi.hoisted(() => ({
  navigateMock: vi.fn(),
  listProposalsMock: vi.fn(),
  kpisMock: vi.fn(),
  optionsMock: vi.fn(),
  exportCsvMock: vi.fn(),
  printMock: vi.fn(),
  createFromQuotationMock: vi.fn(),
}))

vi.mock("../../lib/proposals", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../lib/proposals")>()
  return {
    ...actual,
    listProposals: listProposalsMock,
    getProposalKPIs: kpisMock,
    getProposalOptions: optionsMock,
    exportProposalsCsv: exportCsvMock,
    printProposal: printMock,
    createProposalFromQuotation: createFromQuotationMock,
  }
})

vi.mock("react-router-dom", () => ({
  useNavigate: () => navigateMock,
  Link: ({ children }: { children: React.ReactNode }) => <a>{children}</a>,
}))

let grantedPermissions: string[]

vi.mock("../../lib/access", () => ({
  useAccess: () => ({
    access: {
      permissions: grantedPermissions.map((code) => {
        const [module, action] = code.split(".")
        return { module, action }
      }),
    },
    isSuperAdmin: false,
    canAccess: (module: string) => module === "ol_proposals",
  }),
}))

vi.mock("../../components/ui/Toast", () => ({
  useToast: () => ({ toast: vi.fn(), dismiss: vi.fn() }),
}))

function rowFixture(overrides: Record<string, unknown> = {}) {
  return {
    id: "prop-1",
    proposal_number: "OLP-2026-000001",
    policyholder: "Asha Said",
    agent: "Juma Agent",
    employer: "-",
    product: "OL001 - Family Protection",
    plan: "Plan A",
    total_premium: "125.50",
    currency: "TZS",
    status: "PAYMENT_READY",
    status_badge: { code: "PAYMENT_READY", name: "Payment Ready" },
    payment_ready: true,
    first_premium_posted: false,
    expiry_date: "2026-08-25",
    created_at: "2026-08-01T09:00:00Z",
    allowed_actions: ["view", "enrich", "mark_payment_ready", "print", "convert", "cancel"],
    ...overrides,
  }
}

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <OLProposals />
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  navigateMock.mockReset()
  listProposalsMock.mockReset()
  kpisMock.mockReset()
  optionsMock.mockReset()
  exportCsvMock.mockReset()
  printMock.mockReset()
  createFromQuotationMock.mockReset()

  grantedPermissions = [
    "ol_proposals.view",
    "ol_proposals.create",
    "ol_proposals.enrich",
    "ol_proposals.mark_payment_ready",
    "ol_proposals.convert",
    "ol_proposals.cancel",
    "ol_proposals.print",
  ]

  kpisMock.mockResolvedValue({
    total_proposals: 42,
      pending_underwriting: 7,
      payment_ready: 5,
      awaiting_first_premium: 9,
      awaiting_first_premium_amount: "45000.00",
      converted: 11,
      converted_in_period: 4,
      expiring_soon: 6,
      expiring_in_7_days: 3,
      cancelled: 2,
    expired: 1,
  })
  optionsMock.mockImplementation(async (kind: string) => {
    if (kind === "statuses") {
      return {
        kind,
        results: [
          { id: "ENRICHMENT", label: "Enrichment", value: "ENRICHMENT" },
          { id: "PAYMENT_READY", label: "Payment Ready", value: "PAYMENT_READY" },
          { id: "AWAITING_FIRST_PREMIUM", label: "Awaiting First Premium", value: "AWAITING_FIRST_PREMIUM" },
          { id: "CONVERTED", label: "Converted", value: "CONVERTED" },
          { id: "PENDING_UNDERWRITING", label: "Pending Underwriting", value: "PENDING_UNDERWRITING" },
        ],
      }
    }
    if (kind === "intermediaries") {
      return { kind, results: [{ id: "agent-uuid-1", label: "Juma Agent", reference: "AG-001" }] }
    }
    return { kind, results: [] }
  })
  listProposalsMock.mockResolvedValue({ results: [rowFixture()], count: 1, page: 1, page_size: 20 })
})

describe("OL Proposals register", () => {
  it("renders KPI cards with values and deep links that apply filters", async () => {
    renderPage()

    expect(await screen.findByTestId("kpi-total")).toHaveTextContent("42")
    expect(screen.getByTestId("kpi-pending_underwriting")).toHaveTextContent("7")
    expect(screen.getByTestId("kpi-payment_ready")).toHaveTextContent("5")
    expect(screen.getByTestId("kpi-awaiting_first_premium")).toHaveTextContent("9")
    expect(screen.getByTestId("kpi-awaiting_first_premium")).toHaveTextContent(/45,000\.00 outstanding/)
    expect(screen.getByTestId("kpi-converted_period")).toHaveTextContent("4")
    expect(screen.getByTestId("kpi-expiring_soon")).toHaveTextContent("3")

    fireEvent.click(screen.getByTestId("kpi-payment_ready"))
    await waitFor(() =>
      expect(listProposalsMock).toHaveBeenCalledWith(expect.objectContaining({ paymentReady: true })),
    )
  })

  it("applies chip presets to the register query", async () => {
    const today = new Date()
    const plus7 = new Date()
    plus7.setDate(plus7.getDate() + 7)
    const iso = (value: Date) =>
      `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, "0")}-${String(value.getDate()).padStart(2, "0")}`

    renderPage()

    fireEvent.click(await screen.findByTestId("chip-expiring_7_days"))
    await waitFor(() =>
      expect(listProposalsMock).toHaveBeenCalledWith(
        expect.objectContaining({ expiryFrom: iso(today), expiryTo: iso(plus7) }),
      ),
    )

    fireEvent.click(screen.getByTestId("chip-expiring_7_days"))
    fireEvent.click(screen.getByTestId("chip-awaiting_first_premium"))
    await waitFor(() =>
      expect(listProposalsMock).toHaveBeenCalledWith(expect.objectContaining({ status: "AWAITING_FIRST_PREMIUM" })),
    )

    fireEvent.change(screen.getByLabelText("Product"), { target: { value: "OL001" } })
    await waitFor(() =>
      expect(listProposalsMock).toHaveBeenCalledWith(
        expect.objectContaining({ status: "AWAITING_FIRST_PREMIUM", product: "OL001" }),
      ),
    )
  })

  it("gates row actions by backend allowed_actions and permissions", async () => {
    renderPage()

    const trigger = await screen.findByRole("button", { name: /actions for row 1/i })
    fireEvent.click(trigger)

    const menu = document.querySelector('[data-datatable-action-menu="true"]') as HTMLElement
    expect(menu).not.toBeNull()
    expect(Array.from(menu.querySelectorAll("button")).map((button) => button.textContent)).toEqual([
      "View",
      "Enrich",
      "Mark Payment Ready",
      "Convert to Policy",
      "Cancel",
      "Print",
    ])
  })

  it("hides actions the operator lacks permission for even when allowed", async () => {
    grantedPermissions = ["ol_proposals.view", "ol_proposals.print"]

    renderPage()

    const trigger = await screen.findByRole("button", { name: /actions for row 1/i })
    fireEvent.click(trigger)

    const menu = document.querySelector('[data-datatable-action-menu="true"]') as HTMLElement
    const labels = Array.from(menu.querySelectorAll("button")).map((button) => button.textContent)
    expect(labels).toEqual(["View", "Print"])
  })

  it("exports CSV respecting the active filters", async () => {
    exportCsvMock.mockResolvedValue({ fileName: "ol-proposals.csv", blobUrl: "blob:export" })

    renderPage()

    await screen.findByText("OLP-2026-000001")

    fireEvent.change(screen.getByLabelText("Status"), { target: { value: "PAYMENT_READY" } })
    await waitFor(() => expect(listProposalsMock).toHaveBeenCalledWith(expect.objectContaining({ status: "PAYMENT_READY" })))

    fireEvent.click(screen.getByTestId("export-proposals-csv"))
    await waitFor(() =>
      expect(exportCsvMock).toHaveBeenCalledWith(
        expect.objectContaining({ status: "PAYMENT_READY", page: undefined, pageSize: undefined }),
      ),
    )
  })

  it("shows the empty-state guidance linking to quotations when there are no proposals", async () => {
    listProposalsMock.mockResolvedValue({ results: [], count: 0 })

    renderPage()

    expect(await screen.findByTestId("empty-proposals-link")).toBeInTheDocument()
    fireEvent.click(screen.getByTestId("empty-proposals-link"))
    expect(navigateMock).toHaveBeenCalledWith("/ordinary-life/quotations")
  })
})

describe("proposalRowActionEnabled", () => {
  const hasPermission = (code: string) => code === "ol_proposals.view"

  it("requires both permission and backend allowance", () => {
    const row = { allowedActions: ["view", "convert"] }
    expect(proposalRowActionEnabled("view", row, false, hasPermission)).toBe(true)
    expect(proposalRowActionEnabled("convert", row, false, hasPermission)).toBe(false)
    expect(proposalRowActionEnabled("cancel", row, false, hasPermission)).toBe(false)
  })

  it("falls back to permissions when the backend sends no allowed_actions", () => {
    expect(proposalRowActionEnabled("print", { allowedActions: [] }, false, hasPermission)).toBe(false)
    expect(proposalRowActionEnabled("print", { allowedActions: [] }, true, hasPermission)).toBe(true)
  })
})
