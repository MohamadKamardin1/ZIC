import { render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"
import { ActionButtonGroup, LoanStatusBadge, MoneyCell, ProgressCell } from "./LoanPrimitives"

describe("LoanStatusBadge", () => {
  it.each([
    ["ACTIVE", "Active", "badge-success"],
    ["DEFAULTED", "Defaulted", "badge-danger"],
    ["SETTLED", "Settled", "badge-neutral"],
    ["OFFSET_ON_SURRENDER", "Offset on surrender", "badge-neutral"],
  ])("renders %s with the expected label and tone", (status, label, tone) => {
    render(<LoanStatusBadge status={status} />)
    expect(screen.getByRole("status")).toHaveTextContent(label)
    expect(screen.getByRole("status").className).toContain(tone)
  })
})

describe("MoneyCell", () => {
  it("formats the loan amount with its currency and accessible label", () => {
    render(<MoneyCell value="1250000.50" currency="TZS" label="Outstanding balance" />)
    expect(screen.getByText(/1,250,000\.50/)).toBeInTheDocument()
    expect(screen.getByLabelText(/Outstanding balance/)).toBeInTheDocument()
  })
})

describe("ProgressCell", () => {
  it("shows remaining balance as an accessible progress bar", () => {
    render(<ProgressCell principal="1000.00" balance="750.00" currency="TZS" />)
    const progress = screen.getByRole("progressbar", { name: "Loan balance remaining" })
    expect(progress).toHaveAttribute("aria-valuenow", "750")
    expect(screen.getByText("25% paid")).toBeInTheDocument()
  })
})

describe("ActionButtonGroup", () => {
  it("does not offer repayment for a settled loan", () => {
    render(<ActionButtonGroup loan={{ status: "SETTLED", allowedActions: ["print"] }} onAction={vi.fn()} permissions={["ol_loans.print"]} />)
    expect(screen.queryByRole("button", { name: /repay/i })).not.toBeInTheDocument()
    expect(screen.getByRole("button", { name: /print/i })).toBeInTheDocument()
  })

  it("requires both the backend action and the permission", () => {
    const onAction = vi.fn()
    render(<ActionButtonGroup loan={{ status: "ACTIVE", allowedActions: ["repay", "offset", "print"] }} onAction={onAction} permissions={["ol_loans.repay"]} />)
    expect(screen.getByRole("button", { name: /repay/i })).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /offset/i })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /print/i })).not.toBeInTheDocument()
  })
})
