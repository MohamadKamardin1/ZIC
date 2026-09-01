import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"
import { toStructuredError } from "../../lib/structuredError"
import { ErrorCoach } from "../ErrorCoach"
import { ItemStatusBadge, MoneyCell, PlanStatusBadge, ProgressCell } from "./MIPrimitives"

describe("maturity installment primitives", () => {
  it("renders every plan lifecycle status as a human-readable badge", () => {
    const cases: Array<[string, string]> = [
      ["CREATED", "Created"],
      ["ACTIVE", "Active"],
      ["COMPLETED", "Completed"],
      ["TERMINATED", "Terminated"],
      ["CANCELLED", "Cancelled"],
    ]
    for (const [status, label] of cases) {
      const { unmount } = render(<PlanStatusBadge status={status} />)
      expect(screen.getByRole("status")).toHaveTextContent(label)
      unmount()
    }
  })

  it("renders every installment item status as a human-readable badge", () => {
    const cases: Array<[string, string]> = [
      ["SCHEDULED", "Scheduled"],
      ["PAYMENT_PENDING", "Payment pending"],
      ["PAID", "Paid"],
      ["MISSED", "Missed"],
      ["WAIVED", "Waived"],
    ]
    for (const [status, label] of cases) {
      const { unmount } = render(<ItemStatusBadge status={status} />)
      expect(screen.getByRole("status")).toHaveTextContent(label)
      unmount()
    }
  })

  it("never leaks a raw uuid as a status label", () => {
    const plan = render(<PlanStatusBadge status="3f9c1a4e-7b0a-4f2d-9c8e-2a1b3c4d5e6f" />)
    expect(screen.getByRole("status")).not.toHaveTextContent("3f9c1a4e")
    plan.unmount()
    render(<ItemStatusBadge status="5a2b4c6d-8e9f-4a1b-9c2d-0e3f4a5b6c7d" />)
    expect(screen.getByRole("status")).not.toHaveTextContent("5a2b4c6d")
  })

  it("renders amounts with currency and two-decimal precision", () => {
    const first = render(<MoneyCell value="15625000.123" currency="TZS" label="Paid amount" />)
    expect(screen.getByLabelText(/TZS\s+15,625,000\.12/)).toBeInTheDocument()
    first.unmount()
    render(<MoneyCell value="250000" currency="TZS" label="Maturity value" />)
    expect(screen.getByLabelText(/TZS\s+250,000\.00/)).toBeInTheDocument()
  })

  it("shows payout progress from paid against maturity value", () => {
    render(<ProgressCell paid="31250000.00" maturityValue="62500000.00" currency="TZS" />)
    const bar = screen.getByRole("progressbar")
    expect(bar).toHaveAttribute("aria-valuenow", "50")
    expect(bar).toHaveTextContent("50%")
    expect(bar).toHaveTextContent(/TZS\s+31,250,000\.00/)
    expect(bar).toHaveTextContent(/TZS\s+62,500,000\.00/)
  })

  it("shows a full bar once the maturity value is fully paid", () => {
    render(<ProgressCell paid="62500000.00" maturityValue="62500000.00" currency="TZS" />)
    const bar = screen.getByRole("progressbar")
    expect(bar).toHaveAttribute("aria-valuenow", "100")
    expect(bar).toHaveTextContent("100%")
  })

  it("shows an empty bar when no maturity value is available yet", () => {
    render(<ProgressCell paid={null} maturityValue={null} currency="TZS" />)
    const bar = screen.getByRole("progressbar")
    expect(bar).toHaveAttribute("aria-valuenow", "0")
    expect(bar).toHaveTextContent("0%")
  })
})

describe("maturity installment ErrorCoach integration", () => {
  it("turns an INSTALLMENT_POLICY_NOT_MATURED payload into teachable resolution steps", () => {
    const error = toStructuredError({
      errorCode: "INSTALLMENT_POLICY_NOT_MATURED",
      message: "An installment plan can only be created against a matured policy.",
      resolutionSteps: [
        "Confirm the policy status is Matured or Matured pending payment before creating an installment plan.",
        "Ask Policy Administration to process the maturity event if the policy has not been matured yet.",
      ],
      error: { code: "INSTALLMENT_POLICY_NOT_MATURED", message: "An installment plan can only be created against a matured policy." },
    })
    expect(error.code).toBe("INSTALLMENT_POLICY_NOT_MATURED")
    expect(error.resolutionSteps[0]).toContain("Matured")
    expect(error.retryable).toBe(true)
  })

  it("renders a reversal failure through ErrorCoach so the user knows the window and path forward", () => {
    const error = toStructuredError({
      errorCode: "INSTALLMENT_REVERSAL_WINDOW_EXPIRED",
      message: "The payment is older than the reversal window.",
      resolutionSteps: [
        "The reversal window is 7 days from payment.",
        "Raise a finance review instead of reversing this installment.",
      ],
    })
    render(<ErrorCoach title="Payment cannot be reversed" message={error.message} resolutionSteps={error.resolutionSteps} />)
    expect(screen.getByRole("alert")).toHaveTextContent(/older than the reversal window/)
    expect(screen.getByRole("alert")).toHaveTextContent(/7 days from payment/)
    expect(screen.getByRole("alert")).toHaveTextContent(/finance review/)
  })
})
