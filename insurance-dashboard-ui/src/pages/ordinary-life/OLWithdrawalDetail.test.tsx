import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { MemoryRouter, Route, Routes } from "react-router-dom"
import { beforeEach, describe, expect, it, vi } from "vitest"
import type { WithdrawalAuditEntry, WithdrawalBreakdown, WithdrawalDetail, WithdrawalPayment } from "../../lib/withdrawals"

const { useWithdrawalDetailMock, useWithdrawalBreakdownMock, useWithdrawalPaymentsMock, useWithdrawalAuditMock, useWithdrawalActionMutationMock, useAccessMock, toastMock } = vi.hoisted(() => ({
  useWithdrawalDetailMock: vi.fn(),
  useWithdrawalBreakdownMock: vi.fn(),
  useWithdrawalPaymentsMock: vi.fn(),
  useWithdrawalAuditMock: vi.fn(),
  useWithdrawalActionMutationMock: vi.fn(),
  useAccessMock: vi.fn(),
  toastMock: vi.fn(),
}))

vi.mock("../../lib/withdrawalsHooks", () => ({
  useWithdrawalDetail: useWithdrawalDetailMock,
  useWithdrawalBreakdown: useWithdrawalBreakdownMock,
  useWithdrawalPayments: useWithdrawalPaymentsMock,
  useWithdrawalAudit: useWithdrawalAuditMock,
  useWithdrawalActionMutation: useWithdrawalActionMutationMock,
}))

vi.mock("../../components/ui/Toast", () => ({ useToast: () => ({ toast: toastMock }) }))

vi.mock("../../lib/access", () => ({ useAccess: useAccessMock }))

import OLWithdrawalDetail from "./OLWithdrawalDetail"

const breakdown: WithdrawalBreakdown = {
  withdrawalId: "withdrawal-requested-1",
  currency: "TZS",
  cashValueBefore: "2500000.00",
  grossWithdrawal: "250000.00",
  withdrawalFee: "12500.00",
  feeRate: "5.0000",
  feeBasis: "5% fixed",
  netPayout: "237500.00",
  cashValueAfter: "2100000.00",
  sumAssuredBefore: "10000000.00",
  sumAssuredAfter: "9000000.00",
  adjustmentRatio: "10.0000",
  auditTrail: [{ action: "CALCULATED", actor_name: "Sultan Admin", created_at: "2026-08-18T09:00:00Z" }],
}

const payments: WithdrawalPayment[] = [{ id: "payment-1", paymentMode: "BANK_TRANSFER", paymentModeDisplay: "Bank transfer", receiptReference: "RCT-2026-000001", amount: "237500.00", currency: "TZS", paymentDate: "2026-08-20T10:00:00Z", status: "COMPLETED", createdAt: "2026-08-20T10:00:00Z" }]
const actionMutationState = { isPending: false, mutateAsync: vi.fn().mockResolvedValue({ withdrawal: { statusDisplay: "Approved" } }) }
const fullAccess = { access: { permissions: [
  { module: "ol_withdrawals", action: "view" },
  { module: "ol_withdrawals", action: "approve" },
  { module: "ol_withdrawals", action: "process_payout" },
  { module: "ol_withdrawals", action: "cancel" },
  { module: "ol_withdrawals", action: "reverse" },
  { module: "ol_withdrawals", action: "print" },
], visibleModules: ["ol_withdrawals"], groups: [] }, hasPermission: (permission: string) => ["ol_withdrawals.view", "ol_withdrawals.approve", "ol_withdrawals.process_payout", "ol_withdrawals.cancel", "ol_withdrawals.reverse", "ol_withdrawals.print"].includes(permission), isSuperAdmin: false, canAccess: () => true, isLoading: false, isError: false }
const audit: WithdrawalAuditEntry[] = [{ id: "event-1", action: "REQUESTED", actorDisplay: "Sultan Admin", sourceChannel: "API", reason: "Education expenses", createdAt: "2026-08-18T09:00:00Z" }]

const detail: WithdrawalDetail = {
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
  allowedActions: ["approve", "reject", "cancel", "print"],
  createdAt: "2026-08-18T09:00:00Z",
  updatedAt: "2026-08-18T09:00:00Z",
  breakdown,
  payments,
  auditTimeline: audit,
  documents: [],
  policyContext: { sum_assured_before: "10000000.00", sum_assured_after: "9000000.00" },
}

function renderDetail(record = detail) {
  useWithdrawalDetailMock.mockReturnValue({ data: record, isLoading: false, error: null })
  useWithdrawalBreakdownMock.mockReturnValue({ data: breakdown, isLoading: false, error: null })
  useWithdrawalPaymentsMock.mockReturnValue({ data: { results: payments, count: 1 }, isLoading: false, error: null })
  useWithdrawalAuditMock.mockReturnValue({ data: { results: audit, count: 1 }, isLoading: false, error: null })
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={client}><MemoryRouter initialEntries={[`/ordinary-life/withdrawals/${record.id}`]}><Routes><Route path="/ordinary-life/withdrawals/:id" element={<OLWithdrawalDetail />} /></Routes></MemoryRouter></QueryClientProvider>)
}

describe("OL Withdrawal detail Prompt 4", () => {
  beforeEach(() => {
    toastMock.mockReset()
    useWithdrawalDetailMock.mockReset()
    useWithdrawalBreakdownMock.mockReset()
    useWithdrawalPaymentsMock.mockReset()
    useWithdrawalAuditMock.mockReset()
    useWithdrawalActionMutationMock.mockReset().mockReturnValue(actionMutationState)
    actionMutationState.mutateAsync.mockReset().mockImplementation(({ action }: { action: string }) => Promise.resolve({ withdrawal: { statusDisplay: action === "reject" ? "Rejected" : "Approved" } }))
    useAccessMock.mockReset().mockReturnValue(fullAccess)
  })

  it("renders the header, financial cards, dates, and policy link", async () => {
    renderDetail()
    expect((await screen.findAllByText("OL-WDR-2026-000001")).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/Amani Salum/).length).toBeGreaterThan(0)
    expect(screen.getAllByText("Requested").length).toBeGreaterThan(0)
    expect(screen.getAllByText(/TZS\s+250,000\.00/).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/TZS\s+12,500\.00/).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/TZS\s+237,500\.00/).length).toBeGreaterThan(0)
    expect(screen.getByRole("link", { name: /Policy ZIC-OL-2026-000001/ })).toHaveAttribute("href", "/ordinary-life/policies/policy-aman-1")
    expect(screen.getAllByText("Requested").length).toBeGreaterThan(0)
  })

  it("confirms approval only after a reason and refreshes status feedback", async () => {
    const user = userEvent.setup()
    renderDetail()
    await screen.findAllByText("OL-WDR-2026-000001")
    await user.click(screen.getByRole("button", { name: "Approve" }))
    const approvalDialog = await screen.findByRole("dialog", { name: "Approve withdrawal" })
    expect(within(approvalDialog).getByRole("button", { name: "Confirm Approval" })).toBeInTheDocument()
    await user.click(within(approvalDialog).getByRole("button", { name: "Confirm Approval" }))
    expect(await within(approvalDialog).findByText(/Reason for approval is required/)).toBeInTheDocument()
    await user.type(within(approvalDialog).getByRole("textbox", { name: /Reason for Approval/ }), "Eligibility checks completed")
    await user.click(within(approvalDialog).getByRole("button", { name: "Confirm Approval" }))
    await expect.poll(() => actionMutationState.mutateAsync).toHaveBeenCalledWith(expect.objectContaining({ id: "withdrawal-requested-1", action: "approve", payload: { reason: "Eligibility checks completed" } }))
    expect(toastMock).toHaveBeenCalledWith(expect.objectContaining({ title: "Approve withdrawal", message: "Status updated to Approved." }))
  })

  it("requires a rejection reason and then submits the rejection action", async () => {
    const user = userEvent.setup()
    renderDetail()
    await screen.findAllByText("OL-WDR-2026-000001")
    await user.click(screen.getByRole("button", { name: "Reject" }))
    const rejectDialog = await screen.findByRole("dialog", { name: "Reject withdrawal" })
    await user.click(within(rejectDialog).getByRole("button", { name: "Reject" }))
    expect(await within(rejectDialog).findByText(/Reason for Rejection is required/)).toBeInTheDocument()
    await user.type(within(rejectDialog).getByRole("textbox", { name: /Reason for Rejection/ }), "Insufficient documentation")
    await user.click(within(rejectDialog).getByRole("button", { name: "Reject" }))
    await expect.poll(() => actionMutationState.mutateAsync).toHaveBeenCalledWith(expect.objectContaining({ id: "withdrawal-requested-1", action: "reject", payload: { reason: "Insufficient documentation" } }))
    expect(toastMock).toHaveBeenCalledWith(expect.objectContaining({ title: "Reject withdrawal", message: "Status updated to Rejected." }))
  })

  it("hides approval and rejection actions when the permission is absent", async () => {
    useAccessMock.mockReturnValue({ ...fullAccess, access: { ...fullAccess.access, permissions: [{ module: "ol_withdrawals", action: "view" }, { module: "ol_withdrawals", action: "print" }] }, hasPermission: (permission: string) => permission === "ol_withdrawals.view" || permission === "ol_withdrawals.print" })
    renderDetail()
    await screen.findAllByText("OL-WDR-2026-000001")
    expect(screen.queryByRole("button", { name: "Approve" })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Reject" })).not.toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Print" })).toBeInTheDocument()
  })

  it("renders the backend breakdown and payment data when tabs are selected", async () => {
    const user = userEvent.setup()
    renderDetail()
    await screen.findAllByText("OL-WDR-2026-000001")
    await user.click(screen.getByRole("button", { name: "Breakdown" }))
    expect(await screen.findByText("Withdrawal Calculation")).toBeInTheDocument()
    expect(screen.getByText(/TZS\s+2,500,000\.00/)).toBeInTheDocument()
    expect(screen.getAllByText(/TZS\s+250,000\.00/).length).toBeGreaterThan(0)
    expect(screen.getByText(/Withdrawal Fee.*5% fixed/)).toBeInTheDocument()
    expect(screen.getAllByText(/TZS\s+12,500\.00/).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/TZS\s+237,500\.00/).length).toBeGreaterThan(0)
    expect(screen.getByText(/TZS\s+2,100,000\.00/)).toBeInTheDocument()
    expect(screen.getByText("Policy Impact")).toBeInTheDocument()
    expect(screen.getByText(/TZS\s+10,000,000\.00/)).toBeInTheDocument()
    expect(screen.getByText(/TZS\s+9,000,000\.00/)).toBeInTheDocument()
    expect(screen.getByText("10.0000%")).toBeInTheDocument()
    expect(screen.getByText("Calculation Audit Trail")).toBeInTheDocument()
    expect(screen.getByText(/CALCULATED.*Sultan Admin/)).toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: "Payments" }))
    expect(await screen.findByText("Payout Payments")).toBeInTheDocument()
    expect(screen.getByText("RCT-2026-000001")).toBeInTheDocument()
  })

  it("displays a Reversed watermark for reversed withdrawals", async () => {
    renderDetail({ ...detail, status: "REVERSED", statusDisplay: "Reversed", allowedActions: ["view", "print"] })
    const reversedLabels = screen.getAllByText("Reversed", { selector: "span" })
    expect(reversedLabels.some((element) => element.className.includes("text-red-500/10"))).toBe(true)
  })
})
