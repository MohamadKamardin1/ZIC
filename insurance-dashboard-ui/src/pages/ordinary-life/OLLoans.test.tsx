import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { MemoryRouter } from "react-router-dom"
import { beforeEach, describe, expect, it, vi } from "vitest"
import type { LoanRecord } from "../../lib/loans"

const { listLoansMock, useLoanKpisMock, listPoliciesMock, toastMock } = vi.hoisted(() => ({
  listLoansMock: vi.fn(),
  useLoanKpisMock: vi.fn(),
  listPoliciesMock: vi.fn(),
  toastMock: vi.fn(),
}))

vi.mock("../../lib/loans", async () => {
  const actual = await vi.importActual<typeof import("../../lib/loans")>("../../lib/loans")
  return { ...actual, listLoans: listLoansMock }
})

vi.mock("../../lib/loansHooks", async () => {
  const actual = await vi.importActual<typeof import("../../lib/loansHooks")>("../../lib/loansHooks")
  return { ...actual, useLoanKpis: useLoanKpisMock }
})

vi.mock("../../lib/policies", async () => {
  const actual = await vi.importActual<typeof import("../../lib/policies")>("../../lib/policies")
  return { ...actual, listPolicies: listPoliciesMock }
})

vi.mock("../../lib/access", () => ({
  useAccess: () => ({ access: { permissions: [{ module: "ol_loans", action: "view" }, { module: "ol_loans", action: "request" }, { module: "ol_loans", action: "repay" }, { module: "ol_loans", action: "print" }], visibleModules: ["ol_loans"], groups: [] }, hasPermission: (permission: string) => ["ol_loans.view", "ol_loans.request", "ol_loans.repay", "ol_loans.print"].includes(permission), isSuperAdmin: false, canAccess: () => true, isLoading: false, isError: false }),
}))

vi.mock("../../components/ui/Toast", () => ({ useToast: () => ({ toast: toastMock }) }))

import OLLoans from "./OLLoans"

const baseLoan = (overrides: Partial<LoanRecord> = {}): LoanRecord => ({
  id: "loan-active-1",
  loanNumber: "OL-LOAN-2026-000001",
  policyNumber: "ZIC-OL-2026-000001",
  policyDisplay: "ZIC-OL-2026-000001 — Amani Salum",
  policyholderName: "Amani Salum",
  partnerDisplay: "P-000001 — Amani Salum",
  productDisplay: "OL_EDU_GROWTH — Elimu Bora Growth Plan",
  agentDisplay: "AG-0004 — Faraja Intermediaries",
  branchDisplay: "ZNZ-MAIN — Zanzibar Main Branch",
  currency: "TZS",
  principalAmount: "1000000.00",
  cashValueSnapshot: "2500000.00",
  disbursedAmount: "1000000.00",
  repaymentMode: "MONTHLY",
  interestRate: "8.00",
  compoundingFrequency: "MONTHLY",
  termMonths: 12,
  disbursementDate: "2026-02-01",
  maturityDate: "2027-02-01",
  status: "ACTIVE",
  statusDisplay: "Active",
  totalRepaid: "250000.00",
  outstandingBalance: "750000.00",
  approvalRequired: false,
  approvedAt: null,
  rejectedAt: null,
  rejectionReason: "",
  reason: "",
  allowedActions: ["view", "repay", "offset", "print"],
  createdAt: "2026-01-20T08:00:00Z",
  updatedAt: "2026-08-01T08:00:00Z",
  ...overrides,
})

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={client}><MemoryRouter><OLLoans /></MemoryRouter></QueryClientProvider>)
}

describe("OL Loans Prompt 2 page", () => {
  beforeEach(() => {
    listLoansMock.mockReset().mockResolvedValue({ results: [baseLoan(), baseLoan({ id: "loan-settled-1", loanNumber: "OL-LOAN-2025-000014", policyNumber: "ZIC-OL-2025-000021", policyholderName: "Fatma Ali", status: "SETTLED", statusDisplay: "Settled", outstandingBalance: "0.00", allowedActions: ["view", "print"] })], count: 2, next: null, previous: null, page: 1, pageSize: 20 })
    useLoanKpisMock.mockReturnValue({ data: { totalOutstanding: "750000.00", totalDisbursedPeriod: "1000000.00", activeCount: 1, defaultedCount: 0, settledCount: 1, currency: "TZS", amountsByCurrency: {}, timestamp: "2026-08-27T08:00:00Z" }, isLoading: false, error: null })
    listPoliciesMock.mockResolvedValue({ results: [], count: 0, next: null, previous: null })
  })

  it("renders backend KPI values and labeled loan rows", async () => {
    renderPage()
    expect(await screen.findByText("OL-LOAN-2026-000001")).toBeInTheDocument()
    expect(screen.getByText("Active loans count")).toBeInTheDocument()
    expect(screen.getByText("Total loans outstanding")).toBeInTheDocument()
    expect(screen.getAllByText("Settled").length).toBeGreaterThan(0)
    expect(screen.queryByText("loan-active-1")).not.toBeInTheDocument()
  })

  it("hides repayment for a settled row and exposes it for an active row", async () => {
    const user = userEvent.setup()
    renderPage()
    await screen.findByText("OL-LOAN-2026-000001")
    const triggers = screen.getAllByRole("button", { name: /Actions for row/ })
    await user.click(triggers[0])
    expect(screen.getByRole("button", { name: "Repay" })).toBeInTheDocument()
    await user.click(triggers[1])
    await waitFor(() => expect(screen.queryByRole("button", { name: "Repay" })).not.toBeInTheDocument())
  })

  it("forwards search and filters to the server-side fetcher", async () => {
    const user = userEvent.setup()
    renderPage()
    const search = screen.getByRole("textbox", { name: "Search" })
    await user.type(search, "Fatma")
    const status = screen.getByRole("combobox", { name: "Status" })
    await user.selectOptions(status, "DEFAULTED")
    await waitFor(() => expect(listLoansMock.mock.calls.some(([filters]) => filters.search === "Fatma" && filters.status === "DEFAULTED")).toBe(true))
  })
})
