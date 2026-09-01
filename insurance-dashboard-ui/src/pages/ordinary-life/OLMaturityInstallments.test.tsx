import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen, waitFor, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom"
import { beforeEach, describe, expect, it, vi } from "vitest"
import type { MIPlanRecord } from "../../lib/maturityInstallments"
import type { PolicyListItem } from "../../lib/policies"

const { listMIPlansMock, useMIPlanKpisMock, listPoliciesMock, getMIPlanDetailMock, processMIPaymentMock, cancelMIPlanMock, createMIPlanMock, printMIScheduleMock, toastMock, useMIFrequencyOptionsMock, useMITermOptionsMock } = vi.hoisted(() => ({
  listMIPlansMock: vi.fn(),
  useMIPlanKpisMock: vi.fn(),
  listPoliciesMock: vi.fn(),
  getMIPlanDetailMock: vi.fn(),
  processMIPaymentMock: vi.fn(),
  cancelMIPlanMock: vi.fn(),
  createMIPlanMock: vi.fn(),
  printMIScheduleMock: vi.fn(),
  toastMock: vi.fn(),
  useMIFrequencyOptionsMock: vi.fn(),
  useMITermOptionsMock: vi.fn(),
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
  return { ...actual, useMIPlanKpis: useMIPlanKpisMock, useMIFrequencyOptions: useMIFrequencyOptionsMock, useMITermOptions: useMITermOptionsMock }
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

const policyRow = (overrides: Partial<PolicyListItem> = {}): PolicyListItem => ({
  id: "policy-matured-1",
  policyNumber: "ZIC-OL-2025-000101",
  policyholderDisplay: "P-000021 — Juma Hassan",
  policyholderName: "Juma Hassan",
  productPlanDisplay: "OL_ENDOWMENT — OL Endowment Savers",
  agentDisplay: "AG-0004 — Faraja Intermediaries",
  currency: "TZS",
  sumAssured: "60000000.00",
  maturityValue: "60000000.00",
  premiumAmount: "200000.00",
  premiumFrequency: "MONTHLY",
  termYears: 20,
  riskCommencementDate: "2025-01-15",
  maturityDate: "2026-08-15",
  status: "MATURED",
  statusDisplay: "Matured",
  allowedActions: ["view", "print", "claim", "maturity"],
  ...overrides,
})

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={client}><MemoryRouter><OLMaturityInstallments /></MemoryRouter></QueryClientProvider>)
}

function renderPageWithLocation() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  let currentPath = ""
  function LocationProbe() {
    currentPath = useLocation().pathname
    return null
  }
  const utils = render(<QueryClientProvider client={client}><MemoryRouter initialEntries={["/ordinary-life/maturity-installments"]}><OLMaturityInstallments /><Routes><Route path="*" element={<LocationProbe />} /></Routes></MemoryRouter></QueryClientProvider>)
  return { ...utils, getPathname: () => currentPath }
}

const frequencyOptions = [
  { value: "MONTHLY", label: "Monthly", meta: { monthsBetween: 1, payoutPerYear: 12 } },
  { value: "QUARTERLY", label: "Quarterly", meta: { monthsBetween: 3, payoutPerYear: 4 } },
  { value: "ANNUAL", label: "Annual", meta: { monthsBetween: 12, payoutPerYear: 1 } },
]
const termOptions = [
  { value: "1", label: "1 year", meta: { source: "DEFAULT" } },
  { value: "2", label: "2 years", meta: { source: "DEFAULT" } },
  { value: "5", label: "5 years", meta: { source: "DEFAULT" } },
]

describe("OL Maturity Installments Prompt 2 page", () => {
  beforeEach(() => {
    mockPermissions = ["ol_maturity_installments.view", "ol_maturity_installments.create", "ol_maturity_installments.process_payment", "ol_maturity_installments.print", "ol_maturity_installments.cancel"]
    listMIPlansMock.mockReset().mockResolvedValue({ results: [basePlan(), basePlan({ id: "plan-completed-1", planNumber: "MIP-20260815-9E1168C4EF", policyNumber: "ZIC-OL-2025-000021", policyholderName: "Fatma Ali", status: "COMPLETED", statusDisplay: "Completed", paidAmount: "50000000.00", balance: "0.00", allowedActions: ["view", "print"] })], count: 2, next: null, previous: null, page: 1, pageSize: 20 })
    useMIPlanKpisMock.mockReturnValue({ data: { totalPlansActive: 4, totalActivePlansValue: "122750000.00", totalUpcomingPayouts: 6, upcomingNext30Days: 1, missedPaymentsCount: 5, completedPlansCount: 1, filtersApplied: {}, timestamp: "2026-09-01T08:00:00Z" }, isLoading: false, error: null })
    useMIFrequencyOptionsMock.mockReturnValue({ data: { results: frequencyOptions, count: 3, page: 1, pageSize: 10 }, isLoading: false, error: null })
    useMITermOptionsMock.mockReturnValue({ data: { results: termOptions, count: 3, page: 1, pageSize: 10 }, isLoading: false, error: null })
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

describe("OL Maturity Installments Generate Plan wizard (Prompt 7)", () => {
  it("filters the policy search to matured policies only", async () => {
    const user = userEvent.setup()
    listPoliciesMock.mockImplementation((params: { search?: string }) => Promise.resolve({ results: params.search ? [] : [policyRow()], count: params.search ? 0 : 1, next: null, previous: null, page: 1, pageSize: 10 }))
    renderPage()
    await user.click(await screen.findByRole("button", { name: "Generate Plan" }))
    const wizard = within(await screen.findByRole("dialog"))
    await wizard.findByText("Select policy")
    await waitFor(() => expect(listPoliciesMock).toHaveBeenCalledWith(expect.objectContaining({ status: "MATURED", page: 1, pageSize: 10 })))
    expect(await wizard.findByText("ZIC-OL-2025-000101")).toBeInTheDocument()
    await user.type(wizard.getByPlaceholderText("Policy number, policyholder, or product"), "ZIC-OL-2026-000001")
    expect(await wizard.findByText("No policies match this search.")).toBeInTheDocument()
    expect(wizard.queryByText("ZIC-OL-2026-000001")).not.toBeInTheDocument()
    expect(listPoliciesMock).toHaveBeenCalledWith(expect.objectContaining({ status: "MATURED", search: expect.stringContaining("ZIC-OL-2026-000001") }))
  })

  it("updates the installment preview when the term changes", async () => {
    const user = userEvent.setup()
    listPoliciesMock.mockResolvedValue({ results: [policyRow()], count: 1, next: null, previous: null, page: 1, pageSize: 10 })
    renderPage()
    await user.click(await screen.findByRole("button", { name: "Generate Plan" }))
    await user.click(await screen.findByText("ZIC-OL-2025-000101"))
    await screen.findByText("Preview")
    await user.selectOptions(screen.getByRole("combobox", { name: "Payout frequency" }), "QUARTERLY")
    await user.selectOptions(screen.getByRole("combobox", { name: "Term (years)" }), "1")
    expect(screen.getByTestId("preview-installments").textContent).toBe("4")
    expect(screen.getByTestId("preview-amount").textContent).toContain("15,000,000.00")
    await user.selectOptions(screen.getByRole("combobox", { name: "Term (years)" }), "5")
    expect(screen.getByTestId("preview-installments").textContent).toBe("20")
    expect(screen.getByTestId("preview-amount").textContent).toContain("3,000,000.00")
  })

  it("completes the wizard, creates the plan, and navigates to the new plan detail", async () => {
    const user = userEvent.setup()
    listPoliciesMock.mockResolvedValue({ results: [policyRow()], count: 1, next: null, previous: null, page: 1, pageSize: 10 })
    createMIPlanMock.mockResolvedValue({ plan: { id: "plan-new-1" } })
    const { getPathname } = renderPageWithLocation()
    await user.click(await screen.findByRole("button", { name: "Generate Plan" }))
    await user.click(await screen.findByText("ZIC-OL-2025-000101"))
    await user.selectOptions(screen.getByRole("combobox", { name: "Term (years)" }), "2")
    await user.click(screen.getByRole("button", { name: "Review & Generate" }))
    expect(await screen.findByText("Confirm and generate")).toBeInTheDocument()
    expect(screen.getByTestId("preview-installments").textContent).toBe("24")
    await user.click(screen.getByRole("button", { name: "Generate plan" }))
    await waitFor(() => expect(createMIPlanMock).toHaveBeenCalledWith(expect.objectContaining({ policyId: "policy-matured-1", frequency: "MONTHLY", termYears: 2 }), expect.any(String)))
    await waitFor(() => expect(getPathname()).toBe("/ordinary-life/maturity-installments/plan-new-1"))
    expect(toastMock).toHaveBeenCalledWith(expect.objectContaining({ title: "Installment Plan Generated" }))
  })

  it("validates that immature policies and non-positive maturity values cannot generate a plan", async () => {
    const user = userEvent.setup()
    listPoliciesMock.mockResolvedValue({ results: [policyRow({ id: "policy-active-1", policyNumber: "ZIC-OL-2026-000001", status: "ACTIVE", statusDisplay: "Active", maturityValue: "25000000.00" })], count: 1, next: null, previous: null, page: 1, pageSize: 10 })
    const first = renderPage()
    await user.click(await screen.findByRole("button", { name: "Generate Plan" }))
    const firstWizard = within(await screen.findByRole("dialog"))
    await user.click(await firstWizard.findByText("ZIC-OL-2026-000001"))
    expect(await firstWizard.findByText(/only matured policies are eligible/i)).toBeInTheDocument()
    expect(firstWizard.getByRole("button", { name: "Next" })).toBeDisabled()
    expect(firstWizard.queryByText("Selected policy")).not.toBeInTheDocument()
    first.unmount()

    listPoliciesMock.mockResolvedValue({ results: [policyRow({ id: "policy-matured-zero", policyNumber: "ZIC-OL-2025-000103", maturityValue: "0.00" })], count: 1, next: null, previous: null, page: 1, pageSize: 10 })
    renderPage()
    await user.click(await screen.findByRole("button", { name: "Generate Plan" }))
    const secondWizard = within(await screen.findByRole("dialog"))
    await user.click(await secondWizard.findByText("ZIC-OL-2025-000103"))
    expect(await secondWizard.findByText(/does not carry a positive effective maturity value/i)).toBeInTheDocument()
    expect(secondWizard.getByRole("button", { name: "Review & Generate" })).toBeDisabled()
  })
})
