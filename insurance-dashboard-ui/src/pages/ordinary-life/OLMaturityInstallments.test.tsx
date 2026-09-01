import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { MemoryRouter } from "react-router-dom"
import { beforeEach, describe, expect, it, vi } from "vitest"
import type { MIPlanRecord } from "../../lib/maturityInstallments"

const { listMIPlansMock, useMIPlanKpisMock, listPoliciesMock, getMIPlanDetailMock, processMIPaymentMock, cancelMIPlanMock, createMIPlanMock, printMIScheduleMock, toastMock } = vi.hoisted(() => ({
  listMIPlansMock: vi.fn(),
  useMIPlanKpisMock: vi.fn(),
  listPoliciesMock: vi.fn(),
  getMIPlanDetailMock: vi.fn(),
  processMIPaymentMock: vi.fn(),
  cancelMIPlanMock: vi.fn(),
  createMIPlanMock: vi.fn(),
  printMIScheduleMock: vi.fn(),
  toastMock: vi.fn(),
}))

vi.mock("../../lib/maturityInstallments", async () => {
  const actual = await vi.importActual<typeof import("../../lib/maturityInstallments")>("../../lib/maturityInstallments")
  return {
    ...actual,
    listMIPlans: listMIPlansMock,
    getMIPlanDetail: getMIPlanDetailMock,
    processMIPayment: processMIPaymentMock,
    cancelMIPlan: cancelMIPlanMock,
    createMIPlan: createMIPlanMock,
    printMISchedule: printMIScheduleMock,
  }
})

vi.mock("../../lib/maturityInstallmentsHooks", async () => {
  const actual = await vi.importActual<typeof import("../../lib/maturityInstallmentsHooks")>("../../lib/maturityInstallmentsHooks")
  return { ...actual, useMIPlanKpis: useMIPlanKpisMock }
})

vi.mock("../../lib/policies", async () => {
  const actual = await vi.importActual<typeof import("../../lib/policies")>("../../lib/policies")
  return { ...actual, listPolicies: listPoliciesMock }
})

let mockPermissions: string[]

vi.mock("../../lib/access", () => ({
  useAccess: () => ({
    access: {
      permissions: mockPermissions.map((code) => { const [module, action] = code.split("."); return { module, action } }),
      visibleModules: ["ol_maturity_installments"],
      groups: [],
    },
    hasPermission: (permission: string) => mockPermissions.includes(permission),
    isSuperAdmin: false,
    canAccess: () => true,
    isLoading: false,
    isError: false,
  }),
}))

vi.mock("../../components/ui/Toast", () => ({ useToast: () => ({ toast: toastMock }) }))

import OLMaturityInstallments from "./OLMaturityInstallments"

const basePlan = (overrides: Partial<MIPlanRecord> = {}): MIPlanRecord => ({
  id: "plan-active-1",
  planNumber: "MIP-20260901-9DD41C66AF",
  policyId: "policy-aman-1",
  policyNumber: "ZIC-OL-2026-000001",
  policyholderName: "Amani Salum",
  policyholderDisplay: "P-000001 — Amani Salum",
  claimNumber: null,
  currency: "TZS",
  frequency: "ANNUAL",
  status: "ACTIVE",
  statusDisplay: "Active",
  totalAmount: "62500000.00",
  paidAmount: "15625000.00",
  balance: "46875000.00",
  maturityValue: "62500000.00",
  installmentCount: 4,
  startDate: "2026-03-01",
  endDate: "2029-03-01",
  allowedActions: ["view", "create", "process_payment", "cancel", "print"],
  createdAt: "2026-09-01T08:00:00Z",
  updatedAt: "2026-09-01T08:00:00Z",
  ...overrides,
})

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={client}><MemoryRouter><OLMaturityInstallments /></MemoryRouter></QueryClientProvider>)
}

describe("OL Maturity Installments Prompt 2 page", () => {
  beforeEach(() => {
    mockPermissions = ["ol_maturity_installments.view", "ol_maturity_installments.create", "ol_maturity_installments.process_payment", "ol_maturity_installments.print", "ol_maturity_installments.cancel"]
    listMIPlansMock.mockReset().mockResolvedValue({ results: [basePlan(), basePlan({ id: "plan-completed-1", planNumber: "MIP-20260815-9E1168C4EF", policyNumber: "ZIC-OL-2025-000021", policyholderName: "Fatma Ali", status: "COMPLETED", statusDisplay: "Completed", paidAmount: "50000000.00", balance: "0.00", allowedActions: ["view", "print"] })], count: 2, next: null, previous: null, page: 1, pageSize: 20 })
    useMIPlanKpisMock.mockReturnValue({ data: { totalPlansActive: 4, totalActivePlansValue: "122750000.00", totalUpcomingPayouts: 6, upcomingNext30Days: 1, missedPaymentsCount: 5, completedPlansCount: 1, filtersApplied: {}, timestamp: "2026-09-01T08:00:00Z" }, isLoading: false, error: null })
    listPoliciesMock.mockResolvedValue({ results: [], count: 0, next: null, previous: null })
    getMIPlanDetailMock.mockReset()
    processMIPaymentMock.mockReset()
    cancelMIPlanMock.mockReset()
    createMIPlanMock.mockReset()
    printMIScheduleMock.mockReset()
  })

  it("renders dashboard KPI values and labeled plan rows without leaking record ids", async () => {
    renderPage()
    expect(await screen.findByText("MIP-20260901-9DD41C66AF")).toBeInTheDocument()
    expect(screen.getByText("Total active plans")).toBeInTheDocument()
    expect(screen.getByText("Total value of active plans")).toBeInTheDocument()
    expect(screen.getByText("Upcoming payments (next 30 days)")).toBeInTheDocument()
    expect(screen.getByText("Missed payments")).toBeInTheDocument()
    expect(screen.getByText(/122,750,000\.00/)).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Generate Plan" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Export CSV" })).toBeInTheDocument()
    expect(screen.queryByText("plan-active-1")).not.toBeInTheDocument()
    expect(screen.queryByText("plan-completed-1")).not.toBeInTheDocument()
  })

  it("hides Process payments and Cancel for a completed plan while exposing them for an active plan", async () => {
    const user = userEvent.setup()
    renderPage()
    await screen.findByText("MIP-20260901-9DD41C66AF")
    const triggers = screen.getAllByRole("button", { name: /Actions for row/ })
    await user.click(triggers[0])
    expect(screen.getByRole("button", { name: "Process payments" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Cancel plan" })).toBeInTheDocument()
    await user.click(triggers[1])
    await waitFor(() => expect(screen.queryByRole("button", { name: "Process payments" })).not.toBeInTheDocument())
    expect(screen.queryByRole("button", { name: "Cancel plan" })).not.toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Print schedule" })).toBeInTheDocument()
  })

  it("withholds actions the user lacks permission for even when the backend matrix allows them", async () => {
    mockPermissions = ["ol_maturity_installments.view", "ol_maturity_installments.print"]
    const user = userEvent.setup()
    renderPage()
    await screen.findByText("MIP-20260901-9DD41C66AF")
    const triggers = screen.getAllByRole("button", { name: /Actions for row/ })
    await user.click(triggers[0])
    expect(screen.queryByRole("button", { name: "Process payments" })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Cancel plan" })).not.toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Print schedule" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Generate Plan" })).toBeDisabled()
  })

  it("forwards search and filters to the server-side fetcher", async () => {
    const user = userEvent.setup()
    renderPage()
    await screen.findByText("MIP-20260901-9DD41C66AF")
    await user.type(screen.getByRole("textbox", { name: "Search" }), "Fatma")
    await user.selectOptions(screen.getByRole("combobox", { name: "Status" }), "COMPLETED")
    await user.selectOptions(screen.getByRole("combobox", { name: "Frequency" }), "QUARTERLY")
    await user.type(screen.getByLabelText("Product"), "OL_ENDOWMENT")
    await waitFor(() => expect(listMIPlansMock.mock.calls.some(([filters]) => filters.search === "Fatma" && filters.status === "COMPLETED" && filters.frequency === "QUARTERLY" && filters.product === "OL_ENDOWMENT")).toBe(true))
  })
})
