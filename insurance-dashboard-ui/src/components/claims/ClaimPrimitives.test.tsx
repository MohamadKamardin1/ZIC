import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"
import { toStructuredError } from "../../lib/structuredError"
import { ErrorCoach } from "../ErrorCoach"
import { ClaimMoneySummary, ClaimantBadge, ClaimStatusBadge, MoneyCell, ProgressionGuardBanner } from "./ClaimPrimitives"

describe("claim primitives", () => {
  it("renders every lifecycle status as a human-readable badge", () => {
    const cases: Array<[string, string]> = [
      ["REGISTERED", "Registered"],
      ["PENDING_MEDICAL", "Pending Medical"],
      ["ASSESSED", "Assessed"],
      ["REQUISITIONED", "Requisitioned"],
      ["APPROVED", "Approved"],
      ["SETTLED", "Settled"],
      ["REJECTED", "Rejected"],
      ["CANCELLED", "Cancelled"],
    ]
    for (const [status, label] of cases) {
      const { unmount } = render(<ClaimStatusBadge status={status} />)
      expect(screen.getByRole("status")).toHaveTextContent(label)
      unmount()
    }
  })

  it("never leaks a raw uuid as a status label", () => {
    render(<ClaimStatusBadge status="3f9c1a4e-7b0a-4f2d-9c8e-2a1b3c4d5e6f" />)
    expect(screen.getByRole("status")).not.toHaveTextContent("3f9c1a4e")
  })

  it("renders claimant types as labeled badges", () => {
    const { unmount } = render(<ClaimantBadge claimantType="POLICYHOLDER" />)
    expect(screen.getByRole("status")).toHaveTextContent("Policyholder")
    unmount()
    render(<ClaimantBadge claimantType="DEPENDENT" />)
    expect(screen.getByRole("status")).toHaveTextContent("Dependent")
  })

  it("renders monetary values with currency and precision for calculated, approved, and net", () => {
    render(<MoneyCell value="1234567.891" currency="TZS" variant="calculated" label="Calculated amount" />)
    expect(screen.getByLabelText(/TZS\s+1,234,567\.89/)).toBeInTheDocument()
  })

  it("summarizes calculated, approved, and net payout for auditability", () => {
    render(<ClaimMoneySummary calculated="250000.00" approved="240000.00" net="228000.00" currency="TZS" />)
    expect(screen.getByText(/TZS\s+250,000\.00/)).toBeInTheDocument()
    expect(screen.getByText(/TZS\s+240,000\.00/)).toBeInTheDocument()
    expect(screen.getByText(/TZS\s+228,000\.00/)).toBeInTheDocument()
  })

  it("renders nothing when all progression steps are complete", () => {
    const { container } = render(<ProgressionGuardBanner steps={[{ key: "docs", label: "Mandatory documents", complete: true }, { key: "medical", label: "Medical review", complete: true }]} />)
    expect(container.firstChild).toBeNull()
  })

  it("blocks an action and teaches the user what is missing", () => {
    render(<ProgressionGuardBanner blockedActionLabel="settle this claim" steps={[{ key: "docs", label: "Mandatory documents", complete: false, hint: "Medical report is missing." }, { key: "medical", label: "Medical review", complete: true }]} />)
    expect(screen.getByRole("alert")).toHaveTextContent(/Complete the mandatory steps before you can settle this claim\./)
    expect(screen.getByRole("alert")).toHaveTextContent(/Medical report is missing\./)
    expect(screen.getByRole("alert")).not.toHaveTextContent("Medical review")
  })
})

describe("claim ErrorCoach integration", () => {
  it("turns a CLAIM_MANDATORY_DOC_MISSING payload into teachable resolution steps", () => {
    const error = toStructuredError({
      errorCode: "CLAIM_MANDATORY_DOC_MISSING",
      message: "One or more mandatory claim documents are missing.",
      resolutionSteps: ["Open the claim Documents section and upload every required document."],
      error: { code: "CLAIM_MANDATORY_DOC_MISSING", message: "One or more mandatory claim documents are missing." },
    })
    expect(error.code).toBe("CLAIM_MANDATORY_DOC_MISSING")
    expect(error.resolutionSteps[0]).toContain("upload every required document")
    expect(error.retryable).toBe(true)
  })

  it("renders the teachable claim error through ErrorCoach", () => {
    const error = toStructuredError({
      errorCode: "CLAIM_REQUISITION_REQUIRED",
      message: "The claim must be assessed before a payment requisition can be raised.",
      resolutionSteps: [
        "Complete mandatory documents and medical review in the claim file.",
        "Assess the covered benefit and approve the payable claim amount, then retry.",
      ],
    })
    render(<ErrorCoach title="The claim is not ready" message={error.message} resolutionSteps={error.resolutionSteps} />)
    expect(screen.getByRole("alert")).toHaveTextContent(/must be assessed before a payment requisition/)
    expect(screen.getByRole("alert")).toHaveTextContent(/Complete mandatory documents and medical review/)
    expect(screen.getByRole("alert")).toHaveTextContent(/approve the payable claim amount/i)
  })

  it("marks non-retryable claim codes so the UI does not offer a blind retry", () => {
    const error = toStructuredError({ errorCode: "CLAIM_NOT_FOUND", message: "The requested claim could not be found." })
    expect(error.retryable).toBe(false)
  })
})
