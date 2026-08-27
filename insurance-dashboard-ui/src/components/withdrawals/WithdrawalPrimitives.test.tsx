import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"
import { ImpactAlert, MoneyCell, WithdrawalMoneySummary, WithdrawalStatusBadge } from "./WithdrawalPrimitives"

describe("withdrawal primitives", () => {
  it("renders a human-readable status badge", () => {
    render(<WithdrawalStatusBadge status="PROCESSING" />)
    expect(screen.getByRole("status")).toHaveTextContent("Processing")
  })

  it("renders monetary values with currency and precision", () => {
    render(<MoneyCell value="1234567.891" currency="TZS" label="Gross amount" />)
    expect(screen.getByText(/TZS\s+1,234,567\.89/)).toBeInTheDocument()
  })

  it("explains the policy cash-value impact", () => {
    render(<ImpactAlert grossAmount="250000.00" currency="TZS" />)
    expect(screen.getByRole("alert")).toHaveTextContent(/Cash Value will reduce by TZS\s+250,000\.00\./)
  })

  it("labels gross, fee, and net payout values for auditability", () => {
    render(<WithdrawalMoneySummary grossAmount="100000" feeAmount="5000" netPayout="95000" currency="TZS" />)
    expect(screen.getByText(/TZS\s+100,000\.00/)).toBeInTheDocument()
    expect(screen.getByText(/TZS\s+5,000\.00/)).toBeInTheDocument()
    expect(screen.getByText(/TZS\s+95,000\.00/)).toBeInTheDocument()
  })
})
