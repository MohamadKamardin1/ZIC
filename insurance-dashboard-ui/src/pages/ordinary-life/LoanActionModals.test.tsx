import { fireEvent, render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it, vi } from "vitest"
import type { LoanDetail } from "../../lib/loans"

const { mutateMock, resetMock, toastMock } = vi.hoisted(() => ({
  mutateMock: vi.fn(),
  resetMock: vi.fn(),
  toastMock: vi.fn(),
}))

vi.mock("../../lib/loansHooks", () => ({
  useLoanActionMutation: () => ({ mutate: mutateMock, isPending: false, reset: resetMock }),
}))

vi.mock("../../components/ui/Toast", () => ({
  useToast: () => ({ toast: toastMock }),
}))

vi.mock("../../components/ui/SmartSelect", () => ({
  SmartSelect: ({ label, value, onChange, error }: { label: string; value?: string; onChange?: (value: string) => void; error?: string }) => <div><label htmlFor={`${label}-select`}>{label}</label><select id={`${label}-select`} aria-label={label} value={value ?? ""} onChange={(event) => onChange?.(event.target.value)}><option value="">Select</option><option value="BANK_TRANSFER">Bank transfer</option><option value="CASH">Cash</option></select>{error && <span role="alert">{error}</span>}</div>,
}))

import { DisburseLoanModal, LoanActionModal, OffsetLoanModal, RepayLoanModal } from "./LoanActionModals"

const loan = {
  id: "loan-action-1",
  loanNumber: "OL-LOAN-2026-000100",
  policyId: "policy-action-1",
  policyNumber: "ZIC-OL-2026-000100",
  policyDisplay: "ZIC-OL-2026-000100 — Amani Salum",
  policyholderName: "Amani Salum",
  partnerDisplay: "P-000100 — Amani Salum",
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
  allowedActions: ["repay", "offset", "print"],
  createdAt: "2026-01-20T08:00:00Z",
  updatedAt: "2026-08-01T08:00:00Z",
  schedules: [],
  repayments: [],
  interestAccruals: [],
  offsets: [],
  auditTimeline: [],
} satisfies LoanDetail

const baseProps = { open: true, loan, onClose: vi.fn(), onSuccess: vi.fn() }

beforeEach(() => {
  mutateMock.mockReset()
  resetMock.mockReset()
  toastMock.mockReset()
})

describe("Prompt 7 loan action modals", () => {
  it("blocks repayment amounts above the outstanding balance", async () => {
    const user = userEvent.setup()
    render(<RepayLoanModal {...baseProps} />)
    await user.type(screen.getByTestId("repayment-amount"), "750000.01")
    await user.selectOptions(screen.getByRole("combobox", { name: "Payment mode" }), "BANK_TRANSFER")
    await user.type(screen.getByPlaceholderText("Receipt number or manual reference"), "RCT-100")
    await user.click(screen.getByRole("checkbox"))
    await user.click(screen.getByRole("button", { name: "Process Repayment" }))
    expect(screen.getByText(/no greater than the outstanding balance/i)).toBeInTheDocument()
    expect(mutateMock).not.toHaveBeenCalled()
  })

  it("requires strict confirmation before disbursement and shows the destination copy", async () => {
    const user = userEvent.setup()
    render(<DisburseLoanModal {...baseProps} loan={{ ...loan, status: "APPROVED", statusDisplay: "Approved", allowedActions: ["disburse"] }} />)
    expect(screen.getByText(/confirm disbursement of/i)).toHaveTextContent("Active company settlement account selected by backend in TZS")
    await user.selectOptions(screen.getByRole("combobox", { name: "Payment mode" }), "BANK_TRANSFER")
    await user.click(screen.getByRole("button", { name: "Disburse Funds" }))
    expect(screen.getByText(/confirm the amount and destination/i)).toBeInTheDocument()
    expect(mutateMock).not.toHaveBeenCalled()
  })

  it("displays the exact offset warning and defaults to the full balance", () => {
    render(<OffsetLoanModal {...baseProps} />)
    expect(screen.getByText(/this amount will be deducted from the policy payout/i)).toBeInTheDocument()
    expect(screen.getByDisplayValue("750000.00")).toBeInTheDocument()
  })

  it("refreshes through the success callback after a valid repayment", async () => {
    const user = userEvent.setup()
    mutateMock.mockImplementation((_variables: unknown, options: { onSuccess: (result: object) => void }) => options.onSuccess({ loan }))
    render(<LoanActionModal action="repay" {...baseProps} />)
    fireEvent.change(screen.getByTestId("repayment-amount"), { target: { value: "100.00" } })
    await user.selectOptions(screen.getByRole("combobox", { name: "Payment mode" }), "BANK_TRANSFER")
    await user.type(screen.getByPlaceholderText("Receipt number or manual reference"), "RCT-101")
    await user.click(screen.getByRole("checkbox"))
    await user.click(screen.getByRole("button", { name: "Process Repayment" }))
    expect(mutateMock).toHaveBeenCalledWith(expect.objectContaining({ action: "repay", payload: expect.objectContaining({ amount: "100.00", payment_mode: "BANK_TRANSFER", receipt_ref: "RCT-101" }) }), expect.any(Object))
    expect(baseProps.onSuccess).toHaveBeenCalledWith({ loan })
    expect(toastMock).toHaveBeenCalledWith(expect.objectContaining({ title: "Repayment processed", tone: "success" }))
  })
})
