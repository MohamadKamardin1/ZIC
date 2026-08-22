import { fireEvent, render, screen } from "@testing-library/react"
import type { ComponentProps } from "react"
import { describe, expect, it, vi, beforeEach } from "vitest"
import { ErrorCoach } from "./ErrorCoach"
import { toStructuredError } from "../../lib/structuredError"
import { ApiClientError } from "../../lib/apiClient"

const { navigateMock } = vi.hoisted(() => ({ navigateMock: vi.fn() }))

vi.mock("react-router-dom", () => ({
  useNavigate: () => navigateMock,
}))

function renderCoach(props: ComponentProps<typeof ErrorCoach> = {}) {
  return render(<ErrorCoach {...props} />)
}

const duplicateBody = {
  success: false,
  status_code: 422,
  error_code: "COMMITMENT_DUPLICATE",
  message: "A commitment already exists for this source and installment.",
  resolution_steps: ["Open the existing commitment to record the payment against it."],
  field_errors: {},
  doc_ref: "docs/OL_COMMITMENTS_USER_GUIDE.md",
  error: {
    code: "COMMITMENT_DUPLICATE",
    message: "A commitment already exists for this source and installment.",
    details: { commitment_number: "OLC-2026-00041", commitment_id: "abc-123" },
  },
}

describe("toStructuredError", () => {
  it("maps the flat backend error shape", () => {
    const structured = toStructuredError({
      error_code: "COMMITMENT_OVERPAYMENT",
      message: "The payment amount exceeds the outstanding balance.",
      resolution_steps: ["Adjust the amount."],
      field_errors: { amount: ["Cannot exceed balance of 100000.00."] },
      doc_ref: "docs/OL_COMMITMENTS_DESIGN.md",
    })
    expect(structured.code).toBe("COMMITMENT_OVERPAYMENT")
    expect(structured.message).toContain("exceeds")
    expect(structured.resolutionSteps).toEqual(["Adjust the amount."])
    expect(structured.fieldErrors.amount).toEqual(["Cannot exceed balance of 100000.00."])
    expect(structured.docRef).toContain("docs/")
  })

  it("maps ApiClientError nested details into steps and deep link", () => {
    const body = {
      error_code: "PARAMETER_MISSING",
      status_code: 422,
      message: "The required parameter 'OL Grace Period' is missing or inactive.",
      resolution_steps: ["Configure OL Grace Period.", "retry"],
      field_errors: {},
      error: {
        code: "PARAMETER_MISSING",
        message: "The required parameter 'OL Grace Period' is missing or inactive.",
        details: { parameter: "OL Grace Period", navigation_path: "/ordinary-life/parameters/policy-setup" },
      },
    }
    const apiError = new ApiClientError({
      status: 422,
      code: "PARAMETER_MISSING",
      message: body.message,
      fieldErrors: {},
      details: body,
    })
    const structured = toStructuredError(apiError)
    expect(structured.code).toBe("PARAMETER_MISSING")
    expect(structured.resolutionSteps).toEqual(["Configure OL Grace Period.", "retry"])
    expect(structured.deepLink).toBe("/ordinary-life/parameters/policy-setup")
    expect(structured.retryable).toBe(false)
  })

  it("extracts the existing commitment reference for duplicates", () => {
    const apiError = new ApiClientError({
      status: 422,
      code: "COMMITMENT_DUPLICATE",
      message: duplicateBody.message,
      fieldErrors: {},
      details: duplicateBody,
    })
    const structured = toStructuredError(apiError)
    expect(structured.existing?.number).toBe("OLC-2026-00041")
    expect(structured.existing?.href).toBe("/ordinary-life/commitments/abc-123")
  })

  it("falls back to teach-first registry steps for plain errors", () => {
    const structured = toStructuredError(new Error("boom"))
    expect(structured.code).toBe("UNKNOWN")
    expect(structured.message).toBe("boom")
    expect(structured.resolutionSteps.length).toBeGreaterThan(0)
    expect(structured.retryable).toBe(true)
  })
})

describe("ErrorCoach", () => {
  beforeEach(() => navigateMock.mockReset())

  it("renders code chip, message, and numbered resolution steps", () => {
    renderCoach({
      error: {
        error_code: "COMMITMENT_OVERPAYMENT",
        message: "The payment amount exceeds the outstanding balance.",
        resolution_steps: ["Adjust the amount.", "Review the outstanding balance."],
      },
    })
    expect(screen.getByTestId("error-coach-code")).toHaveTextContent("COMMITMENT_OVERPAYMENT")
    expect(screen.getByTestId("error-coach-message")).toHaveTextContent("exceeds the outstanding balance")
    const steps = screen.getAllByRole("listitem").map((node) => node.textContent)
    expect(steps).toEqual(expect.arrayContaining(["1Adjust the amount.", "2Review the outstanding balance."]))
  })

  it("renders inline field errors from field_errors", () => {
    renderCoach({
      error: {
        error_code: "VALIDATION_ERROR",
        message: "Fix the highlighted fields.",
        field_errors: { amount: ["Cannot exceed balance of 100000.00."] },
      },
    })
    expect(screen.getByTestId("error-coach-fields")).toHaveTextContent("Cannot exceed balance of 100000.00.")
  })

  it("offers the deep-link configuration action for PARAMETER_MISSING", () => {
    const error = toStructuredError({
      error_code: "PARAMETER_MISSING",
      message: "missing",
      deep_link: "/ordinary-life/parameters/policy-setup",
    })
    renderCoach({ error })
    const button = screen.getByTestId("error-coach-deep-link")
    expect(button).toHaveTextContent("Open configuration")
    fireEvent.click(button)
    expect(navigateMock).toHaveBeenCalledWith("/ordinary-life/parameters/policy-setup")
  })

  it("offers the view-existing link for duplicate commitments", () => {
    renderCoach({ error: duplicateBody })
    const button = screen.getByTestId("error-coach-existing")
    fireEvent.click(button)
    expect(navigateMock).toHaveBeenCalledWith("/ordinary-life/commitments/abc-123")
  })

  it("hides retry for non-retryable codes even when onRetry is provided", () => {
    renderCoach({
      error: { error_code: "PARAMETER_MISSING", message: "missing parameter" },
      onRetry: vi.fn(),
    })
    expect(screen.queryByTestId("error-coach-retry")).not.toBeInTheDocument()
  })

  it("calls onRetry for retryable failures", () => {
    const onRetry = vi.fn()
    renderCoach({ error: new Error("network"), onRetry })
    const retry = screen.getByTestId("error-coach-retry")
    expect(retry).toHaveTextContent("Try again")
    fireEvent.click(retry)
    expect(onRetry).toHaveBeenCalled()
  })

  it("is announced via role alert / aria-live", () => {
    renderCoach({ error: new Error("boom") })
    const region = screen.getByRole("alert")
    expect(region).toHaveAttribute("aria-live", "assertive")
  })

  it("renders nothing when no error is present", () => {
    const { container } = renderCoach({})
    expect(container.firstChild).toBeNull()
  })
})