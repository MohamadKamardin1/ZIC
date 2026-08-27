import { MemoryRouter, Route, Routes } from "react-router-dom"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { render, screen, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import type { PortalWithdrawal } from "../../lib/withdrawals"

const { usePortalWithdrawalsMock, usePortalWithdrawalMock, usePortalWithdrawalRequestMutationMock, toastMock } = vi.hoisted(() => ({
  usePortalWithdrawalsMock: vi.fn(),
  usePortalWithdrawalMock: vi.fn(),
  usePortalWithdrawalRequestMutationMock: vi.fn(),
  toastMock: vi.fn(),
}))

vi.mock("../../lib/withdrawalsHooks", () => ({
  usePortalWithdrawals: usePortalWithdrawalsMock,
  usePortalWithdrawal: usePortalWithdrawalMock,
  usePortalWithdrawalRequestMutation: usePortalWithdrawalRequestMutationMock,
}))

vi.mock("../../components/ui/Toast", () => ({ useToast: () => ({ toast: toastMock }) }))

import { PartnerWithdrawalDetail, PartnerWithdrawals } from "./PartnerWithdrawals"

const ownWithdrawal: PortalWithdrawal = {
  id: "portal-withdrawal-1",
  requestNumber: "WITH-2026-000001",
  policyId: "policy-portal-1",
  policyNumber: "ZIC-OL-2026-000001",
  policyholderDisplay: "P-000001 — Amani Salum",
  productDisplay: "OL_EDU_GROWTH — Elimu Bora Growth Plan",
  currency: "TZS",
  grossAmount: "250000.00",
  feeAmount: undefined,
  netPayout: "237500.00",
  cashValueBefore: undefined,
  loanBalanceBefore: undefined,
  cashValueAfter: undefined,
  status: "REQUESTED",
  statusDisplay: "Requested",
  requestedAt: "2026-08-27T09:00:00Z",
  reason: "Education expenses",
  requestAllowed: true,
}

const requestMutation = {
  isPending: false,
  error: null,
  mutate: vi.fn((_payload: unknown, options?: { onSuccess?: (result: { withdrawal?: { id?: string } }) => void }) => options?.onSuccess?.({ withdrawal: { id: "portal-withdrawal-new" } })),
}

function renderList() {
  return render(<MemoryRouter initialEntries={["/portal/withdrawals"]}><Routes><Route path="/portal/withdrawals" element={<PartnerWithdrawals />} /><Route path="/portal/withdrawals/:id" element={<span>detail destination</span>} /></Routes></MemoryRouter>)
}

function renderDetail() {
  return render(<MemoryRouter initialEntries={["/portal/withdrawals/portal-withdrawal-1"]}><Routes><Route path="/portal/withdrawals/:id" element={<PartnerWithdrawalDetail />} /></Routes></MemoryRouter>)
}

describe("Partner portal withdrawals", () => {
  beforeEach(() => {
    usePortalWithdrawalsMock.mockReset().mockReturnValue({ data: { results: [ownWithdrawal], count: 1 }, isLoading: false, isError: false, error: null })
    usePortalWithdrawalMock.mockReset().mockReturnValue({ data: ownWithdrawal, isLoading: false, isError: false, error: null })
    usePortalWithdrawalRequestMutationMock.mockReset().mockReturnValue(requestMutation)
    requestMutation.mutate.mockClear()
    toastMock.mockReset()
  })

  it("shows only the partner-scoped withdrawal row and no staff servicing actions", () => {
    renderList()
    expect(screen.getByTestId("portal-withdrawal-row-WITH-2026-000001")).toHaveTextContent("ZIC-OL-2026-000001")
    expect(screen.queryByText("Another Partner")).not.toBeInTheDocument()
    expect(screen.getByRole("button", { name: "View" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Request Withdrawal" })).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Approve" })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Process Payout" })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Reverse" })).not.toBeInTheDocument()
    expect(screen.getByText("For changes to withdrawal terms, contact ZIC Finance.")).toBeInTheDocument()
  })

  it("submits a partner withdrawal request with the scoped policy and reason", async () => {
    const user = userEvent.setup()
    renderList()
    await user.click(screen.getByRole("button", { name: "Request Withdrawal" }))
    const dialog = await screen.findByRole("dialog", { name: "Request Withdrawal" })
    await user.type(within(dialog).getByPlaceholderText("Enter amount"), "125000")
    await user.type(within(dialog).getByPlaceholderText("Explain the withdrawal request"), "Education fees")
    await user.click(within(dialog).getByRole("button", { name: "Submit Request" }))
    expect(requestMutation.mutate).toHaveBeenCalledWith(expect.objectContaining({ policyId: "policy-portal-1", amount: "125000.00", reason: "Education fees" }), expect.any(Object))
    expect(toastMock).toHaveBeenCalledWith(expect.objectContaining({ title: "Withdrawal request submitted" }))
  })

  it("keeps restricted fee and policy-impact values out of the partner-safe detail", () => {
    renderDetail()
    expect(screen.getByTestId("portal-withdrawal-detail")).toBeInTheDocument()
    expect(screen.getByText("Not disclosed by partner permissions")).toBeInTheDocument()
    expect(screen.queryByText("Cash Value Before")).not.toBeInTheDocument()
    expect(screen.queryByText("Loan Balance Before")).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Approve" })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Process Payout" })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Reverse" })).not.toBeInTheDocument()
    expect(screen.getByText("Read-only portal:")).toBeInTheDocument()
  })
})
