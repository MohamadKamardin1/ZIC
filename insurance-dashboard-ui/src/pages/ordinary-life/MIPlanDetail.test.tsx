import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen } from "@testing-library/react"
import { MemoryRouter, Route, Routes } from "react-router-dom"
import { beforeEach, describe, expect, it, vi } from "vitest"
import type { MIPlanDetail as MIPlanDetailType } from "../../lib/maturityInstallments"

const { useMIPlanDetailMock } = vi.hoisted(() => ({ useMIPlanDetailMock: vi.fn() }))

vi.mock("../../lib/maturityInstallmentsHooks", async () => {
  const actual = await vi.importActual<typeof import("../../lib/maturityInstallmentsHooks")>("../../lib/maturityInstallmentsHooks")
  return { ...actual, useMIPlanDetail: useMIPlanDetailMock }
})

import MIPlanDetail from "./MIPlanDetail"

const detail: MIPlanDetailType = {
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
  maturityClaimId: null,
  totalPayableAmount: "62500000.00",
  totalPaidAmount: "15625000.00",
  sourceChannel: "API",
  sourceChannelDisplay: "Maturity Installments Console",
  parameterSnapshot: {},
  items: [
    { id: "plan-active-1-item-1", planId: "plan-active-1", installmentNumber: 1, dueDate: "2026-03-01", amount: "15625000.00", status: "PAID", statusDisplay: "Paid", requisitionNumber: "FO-MIP-2026-000001", paidDate: "2026-03-01", paidByDisplay: "Finance Officer — Rehema S.", payerDisplay: "Amani Salum", paymentReference: "FO-PAY-2026-000101", narration: "" },
    { id: "plan-active-1-item-2", planId: "plan-active-1", installmentNumber: 2, dueDate: "2027-03-01", amount: "15625000.00", status: "MISSED", statusDisplay: "Missed", requisitionNumber: null, paidDate: null, paidByDisplay: null, payerDisplay: null, paymentReference: null, narration: "" },
  ],
  paymentHistory: [
    { installmentNumber: 1, dueDate: "2026-03-01", amount: "15625000.00", status: "PAID", paidDate: "2026-03-01", requisitionNumber: "FO-MIP-2026-000001", paymentReference: "FO-PAY-2026-000101", payerDisplay: "Amani Salum" },
  ],
  reconciliation: { status: "FAIL", maturityValue: "62500000.00", totalPayableAmount: "62500000.00", paidAmount: "15625000.00", missingAmount: "46875000.00", paidItems: 1, totalItems: 4, discrepancies: [{ code: "MISSING_PAYMENTS", message: "Paid 15625000.00 is below the total payable 62500000.00." }] },
}

function renderDetail() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={client}><MemoryRouter initialEntries={["/ordinary-life/maturity-installments/plan-active-1"]}><Routes><Route path="ordinary-life/maturity-installments/:planId" element={<MIPlanDetail />} /></Routes></MemoryRouter></QueryClientProvider>)
}

describe("OL Maturity Installments detail (View landing)", () => {
  beforeEach(() => { useMIPlanDetailMock.mockReset() })

  it("renders the plan header, schedule, payment history, and reconciliation without leaking record ids", async () => {
    useMIPlanDetailMock.mockReturnValue({ data: detail, isLoading: false, error: null })
    renderDetail()
    expect(await screen.findByText("MIP-20260901-9DD41C66AF")).toBeInTheDocument()
    expect(screen.getByText("Total maturity value")).toBeInTheDocument()
    expect(screen.getAllByText(/62,500,000\.00/).length).toBeGreaterThan(0)
    expect(screen.getByText("Installment schedule")).toBeInTheDocument()
    expect(screen.getByText("Payment history")).toBeInTheDocument()
    expect(screen.getByText("Reconciliation report")).toBeInTheDocument()
    expect(screen.getByText("Fail")).toBeInTheDocument()
    expect(screen.getAllByText("FO-MIP-2026-000001").length).toBeGreaterThan(0)
    expect(screen.queryByText("plan-active-1")).not.toBeInTheDocument()
    expect(screen.queryByText("plan-active-1-item-1")).not.toBeInTheDocument()
  })

  it("shows an ErrorCoach with recovery steps when the plan cannot be loaded", async () => {
    useMIPlanDetailMock.mockReturnValue({ data: undefined, isLoading: false, error: new Error("The requested installment plan could not be loaded.") })
    renderDetail()
    expect(await screen.findByText("Plan detail unavailable")).toBeInTheDocument()
    expect(screen.getByText(/Return to the Maturity Installments register/)).toBeInTheDocument()
  })
})
