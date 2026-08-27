import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { MemoryRouter, Route, Routes } from "react-router-dom"
import { beforeEach, describe, expect, it, vi } from "vitest"
import type { LoanDetail } from "../../lib/loans"

const { useLoanDetailMock } = vi.hoisted(() => ({ useLoanDetailMock: vi.fn() }))

vi.mock("../../lib/loansHooks", async () => {
  const actual = await vi.importActual<typeof import("../../lib/loansHooks")>("../../lib/loansHooks")
  return { ...actual, useLoanDetail: useLoanDetailMock }
})

vi.mock("../../lib/access", () => ({
  useAccess: () => ({ access: { permissions: [{ module: "ol_loans", action: "view" }, { module: "ol_loans", action: "repay" }, { module: "ol_loans", action: "offset" }], visibleModules: ["ol_loans"], groups: [] }, hasPermission: (permission: string) => ["ol_loans.view", "ol_loans.repay", "ol_loans.offset"].includes(permission), isSuperAdmin: false, canAccess: () => true, isLoading: false, isError: false }),
}))

import OLLoanDetailPage from "./OLLoanDetailPage"

const detail: LoanDetail = {
  id: "loan-active-1",
  policyId: "policy-active-1",
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
  approvedAt: "2026-01-28T08:00:00Z",
  rejectedAt: null,
  rejectionReason: "",
  reason: "Education expenses",
  allowedActions: ["view", "repay", "offset", "print"],
  createdAt: "2026-01-20T08:00:00Z",
  updatedAt: "2026-08-01T08:00:00Z",
  schedules: [],
  repayments: [],
  interestAccruals: [],
  offsets: [],
  auditTimeline: [],
}

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={client}><MemoryRouter initialEntries={["/ordinary-life/loans/loan-active-1"]}><Routes><Route path="/ordinary-life/loans/:loanId" element={<OLLoanDetailPage />} /><Route path="/ordinary-life/policies/:policyId" element={<span>Policy destination</span>} /></Routes></MemoryRouter></QueryClientProvider>)
}

describe("OL Loan detail Prompt 3", () => {
  beforeEach(() => {
    useLoanDetailMock.mockReset().mockReturnValue({ data: detail, isLoading: false, error: null })
  })

  it("renders the header’s key financial facts and timeline", () => {
    renderPage()
    expect(screen.getByRole("heading", { name: "OL-LOAN-2026-000001" })).toBeInTheDocument()
    expect(screen.getByText("Principal amount")).toBeInTheDocument()
    expect(screen.getByText("Disbursed amount")).toBeInTheDocument()
    expect(screen.getByText("Outstanding balance")).toBeInTheDocument()
    expect(screen.getAllByText(/8\.00%/).length).toBeGreaterThan(0)
    expect(screen.getByText("Requested")).toBeInTheDocument()
    expect(screen.getByText("Approved")).toBeInTheDocument()
    expect(screen.getByText("Disbursed")).toBeInTheDocument()
  })

  it("shows only actions permitted by both status and permission", () => {
    renderPage()
    expect(screen.getByRole("button", { name: "Repay" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Offset" })).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Disburse" })).not.toBeInTheDocument()
  })

  it("navigates from the visible policy link without exposing a raw internal id", async () => {
    const user = userEvent.setup()
    renderPage()
    await user.click(screen.getByRole("button", { name: /ZIC-OL-2026-000001/ }))
    expect(await screen.findByText("Policy destination")).toBeInTheDocument()
    expect(screen.queryByText("policy-active-1")).not.toBeInTheDocument()
  })
})
