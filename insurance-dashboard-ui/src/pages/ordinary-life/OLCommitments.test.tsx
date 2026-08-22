import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react"
import { beforeEach, afterEach, describe, expect, it, vi } from "vitest"
import OLCommitments, { rowActionEnabled } from "./OLCommitments"
import type { CommitmentRecord } from "../../lib/commitments"

const { requestMock, navigateMock, toastMock } = vi.hoisted(() => ({ requestMock: vi.fn(), navigateMock: vi.fn(), toastMock: vi.fn() }))

vi.mock("../../lib/apiClient", () => ({
  request: requestMock,
}))

vi.mock("react-router-dom", () => ({
  useNavigate: () => navigateMock,
}))

vi.mock("../../lib/access", () => ({
  useAccess: () => ({
    access: { visibleModules: ["ol_commitments"], permissions: [{ module: "ol_commitments", action: "view" }, { module: "ol_commitments", action: "record_payment" }], groups: [] },
    isLoading: false,
    isSuperAdmin: false,
    canAccess: () => true,
    hasPermission: (code: string) => ["ol_commitments.view", "ol_commitments.record_payment"].includes(code.toLowerCase()),
  }),
}))

vi.mock("../../components/ui/Toast", () => ({
  useToast: () => ({ toast: toastMock, dismiss: vi.fn() }),
}))

const KPI_PAYLOAD = { totalDue: "1000000.00", totalOutstanding: "650000.00", overdueCount: 3, collectedInPeriod: "350000.00" }
const OPTIONS_PAYLOAD = {
  paymentModes: ["CASH", "M-PESA"],
  currencies: ["TZS", "USD"],
  statuses: [{ code: "PENDING", name: "Pending" }, { code: "COMPLETED", name: "Completed" }, { code: "OVERDUE", name: "Overdue" }],
}

const rowA: Record<string, unknown> = {
  id: "11111111-1111-1111-1111-111111111111",
  commitmentNumber: "OLC-2026-00001",
  sourceType: "POLICY",
  sourceReference: "POL-2026-0001",
  partnerName: "Zanzibar Trading Co.",
  productName: "Family Protection",
  planName: "Standard",
  installmentNumber: 7,
  installmentCount: 120,
  dueDate: "2026-09-01",
  premiumAmount: "50000.00",
  amountPaid: "0.00",
  balance: "50000.00",
  currency: "TZS",
  status: "PENDING",
  graceDate: "2026-10-01",
  lapseDate: "2026-10-16",
  allowedActions: ["view", "record_payment", "reschedule"],
}

const rowB: Record<string, unknown> = {
  id: "22222222-2222-2222-2222-222222222222",
  commitmentNumber: "OLC-2026-00002",
  sourceType: "PROPOSAL",
  sourceReference: "OLP-2026-0001",
  partnerName: "Amina Hassan",
  productName: "Investment Linked",
  planName: "Growth",
  installmentNumber: 1,
  installmentCount: 1,
  dueDate: "2026-08-10",
  premiumAmount: "120000.00",
  amountPaid: "120000.00",
  balance: "0.00",
  currency: "TZS",
  status: "COMPLETED",
  graceDate: "2026-09-08",
  lapseDate: "2026-09-24",
  allowedActions: ["view"],
}

const originalCreateObjectURL = URL.createObjectURL
const originalRevokeObjectURL = URL.revokeObjectURL

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <OLCommitments />
    </QueryClientProvider>,
  )
}

function isoDate(daysFromNow: number): string {
  const d = new Date()
  d.setDate(d.getDate() + daysFromNow)
  const pad = (value: number) => String(value).padStart(2, "0")
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

beforeEach(() => {
  requestMock.mockReset()
  navigateMock.mockReset()
  toastMock.mockReset()
  requestMock.mockImplementation(async (path: string) => {
    if (path.includes("/kpis/")) return KPI_PAYLOAD
    if (path.includes("/options/")) return OPTIONS_PAYLOAD
    if (path.includes("/lapse-review/")) return { results: [] }
    if (path.includes("/commitments/")) return { results: [rowA, rowB], count: 2 }
    return {}
  })
})

describe("Commitments list — KPIs", () => {
  it("renders currency-aware KPI values and the overdue count", async () => {
    renderPage()
    expect(await screen.findByText("TZS 1,000,000.00")).toBeInTheDocument()
    expect(screen.getByText("TZS 650,000.00")).toBeInTheDocument()
    expect(screen.getByText("3")).toBeInTheDocument()
    expect(screen.getByText("TZS 350,000.00")).toBeInTheDocument()
    expect(screen.getByText("Total Due")).toBeInTheDocument()
    expect(screen.getAllByText("Outstanding").length).toBeGreaterThan(0)
    expect(screen.getByText("Overdue Count")).toBeInTheDocument()
    expect(screen.getByText("Collected in Period")).toBeInTheDocument()
  })
})

describe("Commitments list — table", () => {
  it("renders names, references, statuses and balance — never UUIDs", async () => {
    renderPage()
    expect(await screen.findByText("OLC-2026-00001")).toBeInTheDocument()
    expect(screen.getByText("Zanzibar Trading Co.")).toBeInTheDocument()
    expect(screen.getByText("Amina Hassan")).toBeInTheDocument()
    expect(screen.getByText("Family Protection / Standard")).toBeInTheDocument()
    expect(screen.getByText("7 of 120")).toBeInTheDocument()
    const badges = screen.getAllByRole("status").map((node) => node.textContent)
    expect(badges).toContain("Pending")
    expect(badges).toContain("Completed")
    expect(screen.getAllByText("TZS 50,000.00").length).toBeGreaterThan(0)
    expect(screen.getAllByText("Policy").length).toBeGreaterThan(0)
    expect(screen.getAllByText("Proposal").length).toBeGreaterThan(0)
    const uuids = ["11111111-1111-1111-1111-111111111111", "22222222-2222-2222-2222-222222222222"]
    uuids.forEach((uuid) => expect(screen.queryByText(uuid)).not.toBeInTheDocument())
  })

  it("renders due-date grace/lapse warnings", async () => {
    rowA.dueDate = isoDate(-5)
    rowA.graceDate = isoDate(5)
    rowA.lapseDate = isoDate(30)
    rowB.dueDate = isoDate(-40)
    rowB.graceDate = isoDate(-30)
    rowB.lapseDate = isoDate(-20)
    renderPage()
    expect(await screen.findByText("In grace")).toBeInTheDocument()
    expect(screen.getByText("5 days past due")).toBeInTheDocument()
    expect(screen.getByText("Lapsed")).toBeInTheDocument()
  })
})

describe("Commitments list — row actions", () => {
  it("gates record_payment by allowed-actions and permissions", async () => {
    renderPage()
    await screen.findByText("OLC-2026-00001")
    const triggers = screen.getAllByLabelText(/Actions for row/)
    fireEvent.click(triggers[0])
    const menu = document.querySelector('[data-datatable-action-menu="true"]')
    expect(menu).not.toBeNull()
    const menuWithin = within(menu as HTMLElement)
    expect(menuWithin.getByText("Record Payment")).toBeInTheDocument()
    expect(menuWithin.getByText("Reschedule")).toBeInTheDocument()
    expect(menuWithin.queryByText("Reverse")).not.toBeInTheDocument()
  })

  it("hides lifecycle actions for a completed commitment surfaced only with view", async () => {
    renderPage()
    await screen.findByText("OLC-2026-00001")
    const triggers = screen.getAllByLabelText(/Actions for row/)
    fireEvent.click(triggers[1])
    const menu = document.querySelector('[data-datatable-action-menu="true"]')
    const menuWithin = within(menu as HTMLElement)
    expect(menuWithin.getByText("View")).toBeInTheDocument()
    expect(menuWithin.queryByText("Record Payment")).not.toBeInTheDocument()
  })

  it("rowActionEnabled applies allowed-actions, terminal state, and permissions", () => {
    const row = (overrides: Partial<CommitmentRecord>) => ({ ...({ status: "PENDING", allowedActions: [] as string[] } as CommitmentRecord), ...overrides })
    const permitAll = () => true

    expect(rowActionEnabled("record_payment", row({ allowedActions: ["record_payment"] }), false, permitAll)).toBe(true)
    expect(rowActionEnabled("reverse", row({ allowedActions: ["record_payment"] }), false, permitAll)).toBe(false)
    expect(rowActionEnabled("record_payment", row({ status: "COMPLETED" }), false, permitAll)).toBe(false)
    expect(rowActionEnabled("record_payment", row({}), false, () => false)).toBe(false)
    expect(rowActionEnabled("view", row({}), false, () => false)).toBe(false)
    expect(rowActionEnabled("view", row({}), true, () => false)).toBe(true)
    expect(rowActionEnabled("cancel", row({}), false, permitAll)).toBe(true)
  })
})

describe("Commitments list — filters, chips, search, export", () => {
  it("applies the Overdue quick chip as a server filter", async () => {
    renderPage()
    fireEvent.click(await screen.findByRole("button", { name: "Overdue" }))
    await waitFor(() => expect(requestMock).toHaveBeenCalledWith(expect.stringContaining("overdue_only=true")))
  })

  it("sends the search term to the backend", async () => {
    renderPage()
    await screen.findByText("OLC-2026-00001")
    fireEvent.change(screen.getByPlaceholderText("Search records"), { target: { value: "Zanzibar" } })
    await waitFor(() => expect(requestMock).toHaveBeenCalledWith(expect.stringContaining("search=Zanzibar")))
  })

  it("downloads a CSV of the loaded commitments", async () => {
    const createObjectURL = vi.fn(() => "blob:csv")
    const revokeObjectURL = vi.fn()
    Object.assign(URL, { createObjectURL, revokeObjectURL })
    renderPage()
    await screen.findByText("OLC-2026-00001")
    fireEvent.click(screen.getByRole("button", { name: "Export CSV" }))
    await waitFor(() => expect(createObjectURL).toHaveBeenCalled())
  })
})

afterEach(() => {
  Object.assign(URL, { createObjectURL: originalCreateObjectURL, revokeObjectURL: originalRevokeObjectURL })
})

describe("Commitments list — error state", () => {
  it("renders the ErrorCoach when the list request fails", async () => {
    requestMock.mockImplementation(async (path: string) => {
      if (path.includes("/kpis/")) return KPI_PAYLOAD
      if (path.includes("/options/")) return OPTIONS_PAYLOAD
      if (path.includes("/imports/")) return { results: [] }
      if (path.includes("/lapse-review/")) return { results: [] }
      throw { error_code: "PARAMETER_MISSING", message: "OL Grace Period is not configured.", resolution_steps: ["Open OL Parameters > Policy Setup > OL Grace Period."] }
    })
    renderPage()
    const coach = await screen.findByRole("alert")
    expect(coach).toHaveAttribute("aria-live", "assertive")
    expect(screen.getByTestId("error-coach-code")).toHaveTextContent("PARAMETER_MISSING")
    expect(screen.getByTestId("error-coach-deep-link")).toBeInTheDocument()
  })

  it("shows the empty-state guidance when there are no commitments", async () => {
    requestMock.mockImplementation(async (path: string) => {
      if (path.includes("/kpis/")) return { totalDue: "0.00", totalOutstanding: "0.00", overdueCount: 0, collectedInPeriod: "0.00" }
      if (path.includes("/options/")) return OPTIONS_PAYLOAD
      return { results: [], count: 0 }
    })
    renderPage()
    await screen.findByText("No commitments yet")
  })
})