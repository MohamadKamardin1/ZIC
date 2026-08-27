import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen, waitFor, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { MemoryRouter } from "react-router-dom"
import { beforeEach, describe, expect, it, vi } from "vitest"
import type { WithdrawalOption, WithdrawalRecord } from "../../lib/withdrawals"

const { listWithdrawalsMock, useWithdrawalKpisMock, useWithdrawalOptionsMock, toastMock } = vi.hoisted(() => ({
  listWithdrawalsMock: vi.fn(),
  useWithdrawalKpisMock: vi.fn(),
  useWithdrawalOptionsMock: vi.fn(),
  toastMock: vi.fn(),
}))

vi.mock("../../lib/withdrawals", async () => {
  const actual = await vi.importActual<typeof import("../../lib/withdrawals")>("../../lib/withdrawals")
  return { ...actual, listWithdrawals: listWithdrawalsMock }
})

vi.mock("../../lib/withdrawalsHooks", async () => {
  const actual = await vi.importActual<typeof import("../../lib/withdrawalsHooks")>("../../lib/withdrawalsHooks")
  return { ...actual, useWithdrawalKpis: useWithdrawalKpisMock, useWithdrawalOptions: useWithdrawalOptionsMock }
})

vi.mock("../../lib/access", () => ({
  useAccess: () => ({
    access: { permissions: [
      { module: "ol_withdrawals", action: "view" },
      { module: "ol_withdrawals", action: "request" },
      { module: "ol_withdrawals", action: "approve" },
      { module: "ol_withdrawals", action: "print" },
    ], visibleModules: ["ol_withdrawals"], groups: [] },
    hasPermission: (permission: string) => ["ol_withdrawals.view", "ol_withdrawals.request", "ol_withdrawals.approve", "ol_withdrawals.print"].includes(permission),
    isSuperAdmin: false,
    canAccess: () => true,
    isLoading: false,
    isError: false,
  }),
}))

vi.mock("../../components/ui/Toast", () => ({ useToast: () => ({ toast: toastMock }) }))

import OLWithdrawals from "./OLWithdrawals"

const option = (value: string, label: string, meta: Record<string, unknown> = {}): WithdrawalOption => ({ value, label, meta })

const baseWithdrawal = (overrides: Partial<WithdrawalRecord> = {}): WithdrawalRecord => ({
  id: "withdrawal-requested-1",
  withdrawalNumber: "OL-WDR-2026-000001",
  policyId: "policy-aman-1",
  policyNumber: "ZIC-OL-2026-000001",
  policyDisplay: "ZIC-OL-2026-000001 — Amani Salum",
  policyholderName: "Amani Salum",
  policyholderDisplay: "P-000001 — Amani Salum",
  productDisplay: "OL_EDU_GROWTH — Elimu Bora Growth Plan",
  agentDisplay: "AG-0004 — Faraja Intermediaries",
  branchDisplay: "ZNZ-MAIN — Zanzibar Main Branch",
  currency: "TZS",
  grossAmount: "250000.00",
  feeAmount: "12500.00",
  netPayout: "237500.00",
  cashValueBefore: "2500000.00",
  loanBalanceBefore: "150000.00",
  cashValueAfter: "2100000.00",
  status: "REQUESTED",
  statusDisplay: "Requested",
  reason: "Education expenses",
  requestedAt: "2026-08-18T09:00:00Z",
  approvedAt: null,
  processedAt: null,
  paidAt: null,
  allowedActions: ["view", "approve", "reject", "print"],
  createdAt: "2026-08-18T09:00:00Z",
  updatedAt: "2026-08-18T09:00:00Z",
  ...overrides,
})

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={client}><MemoryRouter><OLWithdrawals /></MemoryRouter></QueryClientProvider>)
}

describe("OL Withdrawals Prompt 2 page", () => {
  beforeEach(() => {
    listWithdrawalsMock.mockReset().mockResolvedValue({ results: [baseWithdrawal(), baseWithdrawal({ id: "withdrawal-paid-1", withdrawalNumber: "OL-WDR-2026-000002", policyNumber: "ZIC-OL-2025-000021", policyDisplay: "ZIC-OL-2025-000021 — Fatma Ali", policyholderName: "Fatma Ali", status: "PAID", statusDisplay: "Paid", allowedActions: ["view", "print"] })], count: 2, next: null, previous: null, page: 1, pageSize: 20 })
    useWithdrawalKpisMock.mockReturnValue({ data: { totalWithdrawnCurrentMonth: "350000.00", totalWithdrawnCurrentMonthCount: 2, pendingApprovalsCount: 1, pendingApprovalsAmount: "250000.00", processingPayoutsCount: 0, averageFeeAmount: "8750.00", currency: "TZS", timestamp: "2026-08-27T08:00:00Z" }, isLoading: false, error: null })
    useWithdrawalOptionsMock.mockImplementation((kind: string) => ({ data: { results: kind === "policies" ? [option("policy-aman-1", "ZIC-OL-2026-000001 — Amani Salum", { status: "ACTIVE", available_limit: "2350000.00", currency: "TZS" })] : kind === "products" ? [option("OL_EDU_GROWTH", "OL_EDU_GROWTH — Elimu Bora Growth Plan")] : kind === "branches" ? [option("ZNZ-MAIN", "ZNZ-MAIN — Zanzibar Main Branch")] : [option("agent-faraja", "AG-0004 — Faraja Intermediaries")] }, isLoading: false, error: null }))
    toastMock.mockReset()
  })

  it("renders backend KPI values, labeled rows, and no internal UUIDs", async () => {
    renderPage()
    expect(await screen.findByText("OL-WDR-2026-000001")).toBeInTheDocument()
    expect(screen.getByText("Total withdrawn · current month")).toBeInTheDocument()
    expect(screen.getByText("Pending approvals")).toBeInTheDocument()
    expect(screen.getAllByText("Requested").length).toBeGreaterThan(0)
    expect(screen.getAllByText("Paid").length).toBeGreaterThan(0)
    expect(screen.queryByText("withdrawal-requested-1")).not.toBeInTheDocument()
  })

  it("shows approve and reject only for requested rows and keeps print for paid rows", async () => {
    const user = userEvent.setup()
    renderPage()
    await screen.findByText("OL-WDR-2026-000001")
    const triggers = screen.getAllByRole("button", { name: /Actions for row/ })
    await user.click(triggers[0])
    expect(screen.getByRole("button", { name: "Approve" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Reject" })).toBeInTheDocument()
    await user.click(triggers[1])
    await waitFor(() => expect(screen.queryByRole("button", { name: "Approve" })).not.toBeInTheDocument())
    expect(screen.getByRole("button", { name: "Print" })).toBeInTheDocument()
  })

  it("forwards search and status filters to the server-side list contract", async () => {
    const user = userEvent.setup()
    renderPage()
    await screen.findByText("OL-WDR-2026-000001")
    await user.type(screen.getByRole("textbox", { name: "Search" }), "Fatma")
    await user.selectOptions(screen.getByRole("combobox", { name: "Status" }), "PAID")
    await waitFor(() => expect(listWithdrawalsMock.mock.calls.some(([filters]) => filters.search === "Fatma" && filters.status === "PAID")).toBe(true))
  })

  it("opens policy selection from the primary request action", async () => {
    const user = userEvent.setup()
    renderPage()
    await screen.findByText("OL-WDR-2026-000001")
    await user.click(screen.getByRole("button", { name: "Request Withdrawal" }))
    const dialog = await screen.findByRole("dialog", { name: "Request Withdrawal" })
    expect(dialog).toHaveTextContent("Select an eligible policy")
    expect(within(dialog).getByRole("button", { name: /ZIC-OL-2026-000001/ })).toBeInTheDocument()
  })
})
