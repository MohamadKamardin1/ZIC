import { fireEvent, render, screen } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import PolicyDetailPage from "./PolicyDetailPage"
import { UUID_RE } from "../../lib/display"

const { navigateMock, setSearchParamsMock, usePolicyDetailMock, usePolicyOptionsMock } = vi.hoisted(() => ({
  navigateMock: vi.fn(),
  setSearchParamsMock: vi.fn(),
  usePolicyDetailMock: vi.fn(),
  usePolicyOptionsMock: vi.fn(),
}))

vi.mock("react-router-dom", () => ({
  useParams: () => ({ policyId: "policy-1" }),
  useNavigate: () => navigateMock,
  useSearchParams: () => [new URLSearchParams(), setSearchParamsMock],
}))
vi.mock("../../lib/access", () => ({
  useAccess: () => ({
    access: { permissions: [
      { module: "ol_policies", action: "view" },
      { module: "ol_policies", action: "endorse" },
      { module: "ol_policies", action: "loan" },
      { module: "ol_policies", action: "withdraw" },
      { module: "ol_policies", action: "surrender" },
      { module: "ol_policies", action: "print" },
      { module: "ol_policies", action: "reinstate" },
    ] },
    isSuperAdmin: false,
  }),
}))
vi.mock("../../lib/policiesHooks", () => ({
  usePolicyDetail: usePolicyDetailMock,
  usePolicyOptions: usePolicyOptionsMock,
}))

const activePolicy = {
  id: "policy-1",
  policyNumber: "ZIC-OL-2026-000001",
  policyholderDisplay: "P-000018 — Amani Salum",
  policyholderName: "Amani Salum",
  productPlanDisplay: "OL_EDU_GROWTH — Elimu Bora Growth Plan",
  agentDisplay: "AG-0004 — Faraja Intermediaries",
  currency: "TZS",
  sumAssured: "25000000.00",
  premiumAmount: "120000.00",
  premiumFrequency: "MONTHLY",
  termYears: 15,
  riskCommencementDate: "2026-01-15",
  maturityDate: "2041-01-15",
  status: "ACTIVE",
  statusDisplay: "Active",
  allowedActions: ["view", "endorse", "loan", "withdraw", "surrender", "print"],
  version: 1,
  contractSnapshot: {
    term_years: 15,
    payment_period_years: 15,
    premium_frequency: "MONTHLY",
    quote_basis: "SUM_ASSURED",
    premium_factor: "1.20",
    estimated_maturity_value: "35000000.00",
    joint_life: false,
    mortgage: false,
    pa: true,
    wp: false,
  },
  members: [{ id: "member-1", memberRelation: "Principal member", name: "Amani Salum", dob: "1990-03-12", gender: "MALE", benefitAmount: "25000000.00" }],
  riders: [{ id: "rider-1", riderCode: "WP — Waiver of Premium", sumAssured: "25000000.00", amount: "0.00", premium: "0.00" }],
  benefits: [{ id: "benefit-1", benefitType: "Death benefit", calculationBasis: "SUM_ASSURED", amount: "25000000.00" }],
  endorsements: [],
  auditLogs: [
    { id: "audit-1", eventType: "PolicyIssued", fromStatus: "AWAITING_FIRST_PREMIUM", toStatus: "ACTIVE", reason: "First premium posted", sourceChannel: "API", actorDisplay: "Sultan Admin", createdAt: "2026-01-15T10:00:00Z" },
    { id: "audit-2", eventType: "PolicyEndorsed", fromStatus: "ACTIVE", toStatus: "ACTIVE", reason: "Address correction", sourceChannel: "API", actorDisplay: "Sultan Admin", createdAt: "2026-02-02T10:00:00Z" },
  ],
  linkedProposal: { proposal_number: "OLP-2026-000001", status: "CONVERTED", quotation_number: "Q-2026-000001", partner_display: "P-000018 — Amani Salum" },
  linkedCommitments: [],
}

beforeEach(() => {
  navigateMock.mockReset()
  setSearchParamsMock.mockReset()
  usePolicyDetailMock.mockReset().mockReturnValue({ data: activePolicy, isPending: false, isError: false, error: null, refetch: vi.fn() })
  usePolicyOptionsMock.mockReturnValue({ data: [{ value: "ACTIVE", label: "Active", meta: { badge_type: "POSITIVE" } }], isPending: false })
})

describe("PolicyDetailPage", () => {
  it("renders the complete policy header and overview facts", () => {
    const { container } = render(<PolicyDetailPage />)
    expect(screen.getAllByRole("heading", { name: "ZIC-OL-2026-000001" }).length).toBeGreaterThanOrEqual(2)
    expect(screen.getAllByText("P-000018 — Amani Salum").length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText("OL_EDU_GROWTH — Elimu Bora Growth Plan").length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText("Policy term")).toBeInTheDocument()
    expect(screen.getByText("Payment frequency")).toBeInTheDocument()
    expect(screen.getByText("Linked proposal reference")).toBeInTheDocument()
    expect(screen.getByText("OLP-2026-000001")).toBeInTheDocument()
    expect(screen.getByText("PolicyIssued")).toBeInTheDocument()
    expect(screen.getByText("AWAITING_FIRST_PREMIUM → ACTIVE · Sultan Admin")).toBeInTheDocument()
    expect(UUID_RE.test(container.textContent ?? "")).toBe(false)
  })

  it("shows active policy actions and switches detail tabs", () => {
    render(<PolicyDetailPage />)
    expect(screen.getByRole("button", { name: "Endorse" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Loan" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Withdraw" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Surrender" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Print" })).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "Members & Riders" }))
    expect(setSearchParamsMock).toHaveBeenCalledWith({ tab: "members" })
  })

  it("hides loan and servicing actions when a policy is lapsed and shows reinstatement guidance", () => {
    usePolicyDetailMock.mockReturnValue({ data: { ...activePolicy, status: "LAPSED", statusDisplay: "Lapsed", allowedActions: ["view", "reinstate", "print"], contractSnapshot: { ...activePolicy.contractSnapshot, lapse_date: "2026-04-01" } }, isPending: false, isError: false, error: null, refetch: vi.fn() })
    render(<PolicyDetailPage />)
    expect(screen.getByText(/Lapsed Since/)).toHaveTextContent("Apr 2026")
    expect(screen.getByRole("button", { name: "Reinstate" })).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Loan" })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Withdraw" })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Surrender" })).not.toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Print" })).toBeInTheDocument()
  })
})
