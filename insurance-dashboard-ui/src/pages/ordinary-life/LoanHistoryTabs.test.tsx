import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, it, vi } from "vitest"
import type { LoanDetail, LoanInterestAccrualRow, LoanRepaymentRow } from "../../lib/loans"
import { AccrualsTab, RepaymentsTab } from "./OLLoanDetailPage"

const loan = { loanNumber: "OL-LOAN-2026-000001", currency: "TZS" } as LoanDetail

const repayments: LoanRepaymentRow[] = [{
  id: "repayment-1",
  receiptRef: "RCT-2026-000013",
  receiptNumber: "RCT-2026-000013",
  receiptId: "receipt-1",
  amount: "250000.00",
  currency: "TZS",
  exchangeRate: "1.00000000",
  allocationBreakdown: { principal: "200000.00", interest: "45000.00", penalty: "5000.00" },
  reason: "Monthly payroll deduction",
  sourceChannel: "SYSTEM",
  createdAt: "2026-07-01T10:00:00Z",
}]

const accruals: LoanInterestAccrualRow[] = [{
  id: "accrual-1",
  periodStart: "2026-02-01",
  periodEnd: "2026-03-01",
  principalBase: "1000000.00",
  interestAmount: "6666.67",
  penaltyAmount: "500.00",
  cumulativeInterest: "7166.67",
  sourceChannel: "SYSTEM",
  createdAt: "2026-03-01T00:00:00Z",
}]

describe("Loan history tabs", () => {
  it("renders repayment allocation breakdown, source, and receipt navigation", async () => {
    const user = userEvent.setup()
    const onReceipt = vi.fn()
    render(<RepaymentsTab loan={loan} rows={repayments} page={1} hasNext={false} isLoading={false} onPageChange={vi.fn()} onReceipt={onReceipt} />)
    expect(screen.getByRole("heading", { name: "Repayment history" })).toBeInTheDocument()
    expect(screen.getByText("Principal")).toBeInTheDocument()
    expect(screen.getByText("Interest")).toBeInTheDocument()
    expect(screen.getByText("Penalty")).toBeInTheDocument()
    expect(screen.getByText(/250,000\.00/)).toBeInTheDocument()
    expect(screen.getAllByText(/200,000\.00/).length).toBeGreaterThan(0)
    expect(screen.getByText("Auto")).toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: "RCT-2026-000013" }))
    expect(onReceipt).toHaveBeenCalledWith("receipt-1")
  })

  it("renders accrual period amounts for audit review", () => {
    render(<AccrualsTab rows={accruals} currency="TZS" page={1} hasNext={false} isLoading={false} onPageChange={vi.fn()} />)
    expect(screen.getByRole("heading", { name: "Interest accrual history" })).toBeInTheDocument()
    expect(screen.getByText("1 Feb 2026")).toBeInTheDocument()
    expect(screen.getByText(/6,666\.67/)).toBeInTheDocument()
    expect(screen.getByText(/7,166\.67/)).toBeInTheDocument()
  })

  it("shows separate empty states when no immutable history exists", () => {
    const { rerender } = render(<RepaymentsTab loan={loan} rows={[]} page={1} hasNext={false} isLoading={false} onPageChange={vi.fn()} onReceipt={vi.fn()} />)
    expect(screen.getByText("No repayments have been recorded for this loan.")).toBeInTheDocument()
    rerender(<AccrualsTab rows={[]} currency="TZS" page={1} hasNext={false} isLoading={false} onPageChange={vi.fn()} />)
    expect(screen.getByText("No interest accruals have been recorded for this loan.")).toBeInTheDocument()
  })
})
