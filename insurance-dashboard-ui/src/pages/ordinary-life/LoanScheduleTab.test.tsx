import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, it, vi } from "vitest"
import type { LoanDetail, LoanScheduleRow } from "../../lib/loans"
import { LoanScheduleTab } from "./OLLoanDetailPage"

const loan = { currency: "TZS", loanNumber: "OL-LOAN-2026-000001" } as LoanDetail

const rows: LoanScheduleRow[] = [
  { id: "schedule-1", installmentNumber: 1, dueDate: "2026-01-01", principalDue: "80000.00", interestDue: "6666.67", penaltyDue: "0.00", principalPaid: "80000.00", interestPaid: "6666.67", penaltyPaid: "0.00", amountPaid: "86666.67", balance: "0.00", totalDue: "86666.67", status: "PAID", statusDisplay: "Paid" },
  { id: "schedule-2", installmentNumber: 2, dueDate: "2026-04-01", principalDue: "80000.00", interestDue: "6666.67", penaltyDue: "500.00", principalPaid: "0.00", interestPaid: "0.00", penaltyPaid: "0.00", amountPaid: "0.00", balance: "87166.67", totalDue: "87166.67", status: "OVERDUE", statusDisplay: "Overdue" },
  { id: "schedule-3", installmentNumber: 3, dueDate: "2026-12-01", principalDue: "80000.00", interestDue: "6666.66", penaltyDue: "0.00", principalPaid: "0.00", interestPaid: "0.00", penaltyPaid: "0.00", amountPaid: "0.00", balance: "86666.66", totalDue: "86666.66", status: "PENDING", statusDisplay: "Due" },
]

describe("LoanScheduleTab", () => {
  it("renders the contractual columns, aggregates, and status rows", () => {
    render(<LoanScheduleTab loan={loan} rows={rows} aggregates={{ totalScheduled: "260500.00", totalPaid: "86666.67", remainingBalance: "173833.33" }} page={1} hasNext={false} isLoading={false} onPageChange={vi.fn()} />)
    expect(screen.getByRole("heading", { name: "Repayment schedule" })).toBeInTheDocument()
    expect(screen.getByText("Installment #")).toBeInTheDocument()
    expect(screen.getByText("Total scheduled")).toBeInTheDocument()
    expect(screen.getByText(/260,500\.00/)).toBeInTheDocument()
    expect(screen.getByText("Paid")).toBeInTheDocument()
    expect(screen.getByText("Overdue")).toBeInTheDocument()
    expect(screen.getByText("Due")).toBeInTheDocument()
    expect(screen.getByText("Overdue").closest("tr")).toHaveClass("bg-[var(--destructive)]/8")
  })

  it("uses pagination controls for long schedules", async () => {
    const user = userEvent.setup()
    const onPageChange = vi.fn()
    render(<LoanScheduleTab loan={loan} rows={rows.slice(0, 1)} page={2} hasNext={true} isLoading={false} onPageChange={onPageChange} />)
    expect(screen.getByRole("button", { name: "Previous" })).not.toBeDisabled()
    expect(screen.getByRole("button", { name: "Next" })).not.toBeDisabled()
    await user.click(screen.getByRole("button", { name: "Next" }))
    expect(onPageChange).toHaveBeenCalledWith(3)
  })

  it("exposes a CSV export control", () => {
    render(<LoanScheduleTab loan={loan} rows={rows.slice(0, 1)} page={1} hasNext={false} isLoading={false} onPageChange={vi.fn()} />)
    expect(screen.getByRole("button", { name: /Export CSV/ })).toBeInTheDocument()
  })
})
