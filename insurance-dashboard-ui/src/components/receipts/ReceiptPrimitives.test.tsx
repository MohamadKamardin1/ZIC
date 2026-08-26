import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"
import { AmountCell, AllocationProgressBar, FirstPremiumBadge, MaskedAccount, PaymentModeBadge, ReceiptStatusBadge } from "./ReceiptPrimitives"

 describe("receipt primitives", () => {
  it("renders a human-readable status badge", () => {
    render(<ReceiptStatusBadge status="PARTIALLY_ALLOCATED" />)
    expect(screen.getByRole("status")).toHaveTextContent("Partially allocated")
  })

  it("formats an amount and exposes amount in words as accessible help", () => {
    render(<AmountCell amount="150000.00" currency="TZS" amountInWords="One hundred fifty thousand Tanzanian shillings only" />)
    expect(screen.getByLabelText(/One hundred fifty thousand/)).toBeInTheDocument()
    expect(screen.getByLabelText(/TZS|TSh/)).toBeInTheDocument()
  })

  it("reports allocation ratio through an accessible progressbar", () => {
    render(<AllocationProgressBar allocated="50" total="100" currency="TZS" />)
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "50")
    expect(screen.getByText("50%")).toBeInTheDocument()
  })

  it("only exposes account reveal when permission is granted", () => {
    const { rerender } = render(<MaskedAccount account="**** 0042" canReveal={false} />)
    expect(screen.queryByRole("button", { name: /Show bank account/i })).not.toBeInTheDocument()
    rerender(<MaskedAccount account="**** 0042" canReveal />)
    expect(screen.getByRole("button", { name: /Show bank account/i })).toBeInTheDocument()
  })

  it("renders payment mode and first-premium semantic badges", () => {
    render(<><PaymentModeBadge mode="MOBILE_MONEY" /><FirstPremiumBadge proposalNumber="OLP-2026-000001" /></>)
    expect(screen.getByText("Mobile money")).toBeInTheDocument()
    expect(screen.getByText("First premium")).toBeInTheDocument()
    expect(screen.getByText("First premium").closest("span")).toHaveAttribute("title", expect.stringContaining("OLP-2026-000001"))
  })
})
