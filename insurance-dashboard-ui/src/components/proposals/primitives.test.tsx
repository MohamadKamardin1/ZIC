import { fireEvent, render, screen } from "@testing-library/react"
import { describe, expect, it, vi, beforeEach } from "vitest"
import {
  ExpiryWarning,
  FirstPremiumCard,
  ProposalStatusBadge,
  ReadinessChecklist,
  ShareTotalIndicator,
  expiryWarning,
  shareTotal,
} from "./index"
import { ErrorCoach } from "../commitments/ErrorCoach"
import { toStructuredError } from "../../lib/structuredError"
import { ApiClientError } from "../../lib/apiClient"
import type { ChecklistItem, FirstPremiumStatusShape } from "../../lib/proposals"

const { navigateMock } = vi.hoisted(() => ({ navigateMock: vi.fn() }))

vi.mock("react-router-dom", () => ({
  useNavigate: () => navigateMock,
}))

beforeEach(() => {
  navigateMock.mockReset()
})

// ---------------------------------------------------------------------------
// ProposalStatusBadge
// ---------------------------------------------------------------------------

describe("ProposalStatusBadge", () => {
  it.each([
    ["CONVERTED", "Converted", "badge-success"],
    ["ENRICHMENT", "Enrichment", "badge-info"],
    ["PENDING_UNDERWRITING", "Pending underwriting", "badge-warning"],
    ["AWAITING_FIRST_PREMIUM", "Awaiting first premium", "badge-warning"],
    ["CANCELLED", "Cancelled", "badge-danger"],
    ["EXPIRED", "Expired", "badge-danger"],
  ])("renders %s with the parameter-driven tone", (status, label, badgeClass) => {
    render(<ProposalStatusBadge status={status} />)
    const badge = screen.getByRole("status")
    expect(badge).toHaveTextContent(label)
    expect(badge.className).toContain(badgeClass)
  })

  it("falls back to neutral and Title Case for unknown parameterized codes", () => {
    render(<ProposalStatusBadge status="NEW_CATALOG_STATE" />)
    const badge = screen.getByRole("status")
    expect(badge).toHaveTextContent("New Catalog State")
    expect(badge.className).toContain("badge-neutral")
  })
})

// ---------------------------------------------------------------------------
// ExpiryWarning
// ---------------------------------------------------------------------------

describe("expiryWarning", () => {
  const today = new Date(2026, 7, 23)

  it("flags dates in the past as expired (red)", () => {
    const result = expiryWarning("2026-08-20", today)
    expect(result.level).toBe("expired")
    expect(result.tone).toBe("danger")
    expect(result.detail).toBe("3 days past expiry")
  })

  it("enters the amber window inside 7 days", () => {
    const result = expiryWarning("2026-08-28", today)
    expect(result.level).toBe("expiring")
    expect(result.tone).toBe("warning")
    expect(result.label).toBe("Expires in 5 days")
  })

  it("treats expiry day as expiring today", () => {
    const result = expiryWarning("2026-08-23", today)
    expect(result.level).toBe("expiring")
    expect(result.label).toBe("Expires today")
  })

  it("stays neutral beyond the 7 day window", () => {
    const result = expiryWarning("2026-09-05", today)
    expect(result.level).toBe("valid")
    expect(result.tone).toBe("neutral")
  })
})

describe("ExpiryWarning component", () => {
  it("renders nothing without an expiry date", () => {
    const { container } = render(<ExpiryWarning expiryDate={null} />)
    expect(container).toBeEmptyDOMElement()
  })

  it("shows the red expired state past expiry", () => {
    render(<ExpiryWarning expiryDate="2026-08-01" today={new Date(2026, 7, 23)} />)
    expect(screen.getByRole("status")).toHaveTextContent("Expired")
    expect(screen.getByRole("status").className).toContain("badge-danger")
  })

  it("shows the amber window under 7 days", () => {
    render(<ExpiryWarning expiryDate="2026-08-25" today={new Date(2026, 7, 23)} />)
    expect(screen.getByRole("status")).toHaveTextContent("Expires in 2 days")
    expect(screen.getByRole("status").className).toContain("badge-warning")
  })
})

// ---------------------------------------------------------------------------
// ShareTotalIndicator
// ---------------------------------------------------------------------------

describe("shareTotal", () => {
  it("accepts exactly 100%", () => expect(shareTotal(100)).toBe("valid"))
  it("tolerates four-decimal float dust", () => expect(shareTotal(99.99995)).toBe("valid"))
  it("flags under-allocation", () => expect(shareTotal(75)).toBe("under"))
  it("flags over-allocation", () => expect(shareTotal(120)).toBe("over"))
})

describe("ShareTotalIndicator", () => {
  it("teaches how much is missing when under 100%", () => {
    render(<ShareTotalIndicator shares={[50, 25]} />)
    expect(screen.getByRole("status")).toHaveAttribute("data-share-total", "under")
    expect(screen.getByRole("status")).toHaveTextContent("allocate 25.00% more")
  })

  it("teaches how much to reduce when over 100%", () => {
    render(<ShareTotalIndicator shares={[60, 60]} />)
    expect(screen.getByRole("status")).toHaveAttribute("data-share-total", "over")
    expect(screen.getByRole("status")).toHaveTextContent("reduce 20.00%")
  })

  it("confirms readiness at exactly 100%", () => {
    render(<ShareTotalIndicator shares={[100]} />)
    expect(screen.getByRole("status")).toHaveAttribute("data-share-total", "valid")
    expect(screen.getByRole("status")).toHaveTextContent("ready to save")
  })
})

// ---------------------------------------------------------------------------
// ReadinessChecklist
// ---------------------------------------------------------------------------

const checklistItems: ChecklistItem[] = [
  {
    key: "enrichment_complete",
    passed: true,
    errorCode: "",
    message: "",
    resolutionSteps: [],
  },
  {
    key: "mandatory_documents_complete",
    passed: false,
    errorCode: "PROPOSAL_MANDATORY_DOCUMENTS_MISSING",
    message: "Required documents are missing.",
    resolutionSteps: ["Upload each listed document type under Documents."],
    deepLink: "/proposals/{id}/documents",
  },
]

describe("ReadinessChecklist", () => {
  it("renders an empty-state hint before evaluation", () => {
    render(<ReadinessChecklist items={[]} />)
    expect(screen.getByText(/has not been evaluated yet/i)).toBeInTheDocument()
  })

  it("marks passing items and failing items distinctly", () => {
    const { container } = render(<ReadinessChecklist items={checklistItems} proposalId="P1" />)
    expect(
      container.querySelector('[data-checklist-item="enrichment_complete"]'),
    ).toHaveAttribute("data-checklist-passed", "true")
    expect(
      container.querySelector('[data-checklist-item="mandatory_documents_complete"]'),
    ).toHaveAttribute("data-checklist-passed", "false")
  })

  it("shows failure message, resolution text, and a deep-link Resolve button", () => {
    render(<ReadinessChecklist items={checklistItems} proposalId="P1" />)
    expect(screen.getByText("Required documents are missing.")).toBeInTheDocument()
    expect(screen.getByText(/upload each listed document type/i)).toBeInTheDocument()
    expect(screen.getByTestId("checklist-link-mandatory_documents_complete")).toBeInTheDocument()
    expect(screen.queryByTestId("checklist-link-enrichment_complete")).not.toBeInTheDocument()
  })

  it("translates backend deep links into in-app routes and navigates", () => {
    const onNavigateItem = vi.fn()
    render(<ReadinessChecklist items={checklistItems} proposalId="P1" onNavigateItem={onNavigateItem} />)
    fireEvent.click(screen.getByTestId("checklist-link-mandatory_documents_complete"))
    expect(onNavigateItem).toHaveBeenCalledWith("/ordinary-life/proposals/P1/documents")
  })
})

// ---------------------------------------------------------------------------
// FirstPremiumCard
// ---------------------------------------------------------------------------

const linkedPremium: FirstPremiumStatusShape = {
  linked: true,
  commitmentNumber: "OLC-2026-000041",
  commitmentId: "cmt-9",
  commitmentStatus: "PARTIALLY_PAID",
  amountDue: 50000,
  amountPaid: 25000,
  balance: 25000,
  currency: "TZS",
  lastPaymentDate: null,
  allocations: [
    { receiptReference: "RCT-1001", amount: 25000, currency: "TZS", allocatedAt: "2026-08-20T09:00:00Z" },
  ],
  posted: false,
  nextActions: ["Record receipt in Front Office.", "Allocate against commitment OLC-2026-000041."],
}

describe("FirstPremiumCard", () => {
  it("guides the operator before a commitment exists", () => {
    render(<FirstPremiumCard status={{ linked: false, allocations: [], posted: false, nextActions: [] }} />)
    expect(screen.getByText(/first premium not generated yet/i)).toBeInTheDocument()
  })

  it("shows commitment number link, status, and due/paid/balance", () => {
    render(<FirstPremiumCard status={linkedPremium} />)
    expect(screen.getByTestId("first-premium-commitment-link")).toHaveTextContent("OLC-2026-000041")
    expect(screen.getByText("TZS 50,000.00")).toBeInTheDocument()
    // Paid, balance, and the allocation row all show TZS 25,000.00.
    expect(screen.getAllByText("TZS 25,000.00")).toHaveLength(3)
    expect(screen.getByTestId("first-premium-next-action")).toHaveTextContent(/record receipt in front office/i)
  })

  it("lists allocations in the mini-table", () => {
    render(<FirstPremiumCard status={linkedPremium} />)
    expect(screen.getByTestId("first-premium-allocations")).toHaveTextContent("RCT-1001")
  })

  it("links the commitment number to the commitments workspace", () => {
    render(<FirstPremiumCard status={linkedPremium} />)
    fireEvent.click(screen.getByTestId("first-premium-commitment-link"))
    expect(navigateMock).toHaveBeenCalledWith("/ordinary-life/commitments/cmt-9")
  })
})

// ---------------------------------------------------------------------------
// ErrorCoach — proposal error codes
// ---------------------------------------------------------------------------

describe("ErrorCoach with proposal error codes", () => {
  const notReadyBody = {
    success: false,
    status_code: 409,
    error_code: "PROPOSAL_NOT_PAYMENT_READY",
    message: "This proposal is not payment-ready; resolve each failed checklist item.",
    resolution_steps: [
      "Open the proposal's Payment Readiness panel.",
      "Resolve each failed checklist item using its deep link.",
    ],
    field_errors: {},
    doc_ref: "docs/OL_PROPOSALS_USER_GUIDE.md",
    error: {
      code: "PROPOSAL_NOT_PAYMENT_READY",
      message: "This proposal is not payment-ready; resolve each failed checklist item.",
      details: {
        status: "ENRICHMENT",
        checklist: [
          { key: "partner_verified", passed: true },
          {
            key: "mandatory_documents_complete",
            passed: false,
            error_code: "PROPOSAL_MANDATORY_DOCUMENTS_MISSING",
            deep_link: "/proposals/{id}/documents",
          },
        ],
      },
    },
  }

  it("surfaces the proposal doc ref, code chip, and backend resolution steps", () => {
    const structured = toStructuredError(notReadyBody)
    expect(structured.code).toBe("PROPOSAL_NOT_PAYMENT_READY")
    expect(structured.docRef).toBe("docs/OL_PROPOSALS_USER_GUIDE.md")
    expect(structured.resolutionSteps[0]).toContain("Payment Readiness panel")

    render(<ErrorCoach error={structured} title="Not payment-ready" />)
    expect(screen.getByTestId("error-coach-code")).toHaveTextContent("PROPOSAL_NOT_PAYMENT_READY")
    expect(screen.getByTestId("error-coach-message")).toHaveTextContent(/not payment-ready/i)
    expect(screen.getByTestId("error-coach-steps")).toHaveTextContent(/payment readiness panel/i)
  })

  it("renders a deep link from the first unresolved checklist item", () => {
    render(<ErrorCoach error={toStructuredError(notReadyBody)} />)
    const deepLink = screen.getByTestId("error-coach-deep-link")
    expect(deepLink).toBeInTheDocument()
    fireEvent.click(deepLink)
    expect(navigateMock).toHaveBeenCalledWith("/ordinary-life/proposals")
  })

  it("keeps PARAMETER_MISSING navigation paths working for proposals", () => {
    const body = {
      success: false,
      status_code: 422,
      error_code: "PARAMETER_MISSING",
      message: "No active health questionnaire applies.",
      resolution_steps: [],
      field_errors: {},
      doc_ref: "docs/OL_PROPOSALS_USER_GUIDE.md",
      error: {
        code: "PARAMETER_MISSING",
        message: "No active health questionnaire applies.",
        details: { navigation_path: "/ordinary-life/parameters/policy-setup" },
      },
    }
    render(<ErrorCoach error={new ApiClientError({ status: 422, code: "PARAMETER_MISSING", message: body.message, fieldErrors: {}, details: body })} />)
    fireEvent.click(screen.getByTestId("error-coach-deep-link"))
    expect(navigateMock).toHaveBeenCalledWith("/ordinary-life/parameters/policy-setup")
  })

  it("offers View policy for PROPOSAL_ALREADY_CONVERTED", () => {
    const body = {
      success: false,
      status_code: 409,
      error_code: "PROPOSAL_ALREADY_CONVERTED",
      message: "This proposal was already converted.",
      resolution_steps: ["Return the existing policy reference."],
      field_errors: {},
      doc_ref: "docs/OL_PROPOSALS_USER_GUIDE.md",
      error: {
        code: "PROPOSAL_ALREADY_CONVERTED",
        message: "This proposal was already converted.",
        details: { converted_policy_id: "pol-77" },
      },
    }
    render(<ErrorCoach error={toStructuredError(body)} />)
    const existing = screen.getByTestId("error-coach-existing")
    expect(existing).toHaveTextContent("View policy")
    fireEvent.click(existing)
    expect(navigateMock).toHaveBeenCalledWith("/ordinary-life/policies/pol-77")
  })
})
