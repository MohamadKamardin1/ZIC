import { fireEvent, render, screen } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import PolicyDetailPage from "./PolicyDetailPage"
import { UUID_RE } from "../../lib/display"

const { navigateMock, setSearchParamsMock, searchParamsMock, usePolicyDetailMock, usePolicyOptionsMock, usePolicyMembersMock, usePolicyRidersMock, usePolicyBenefitsMock, usePolicyEndorsementsMock, usePolicyLoansMock, usePolicyWithdrawalsMock, useCreatePolicyEndorsementMutationMock, useRequestPolicySurrenderMutationMock, useRequestPolicyPaidUpMutationMock, useCancelPolicyMutationMock, surrenderMutateMock, paidUpMutateMock, cancelMutateMock } = vi.hoisted(() => ({
  navigateMock: vi.fn(),
  setSearchParamsMock: vi.fn(),
  searchParamsMock: new URLSearchParams(),
  usePolicyDetailMock: vi.fn(),
  usePolicyOptionsMock: vi.fn(),
  usePolicyMembersMock: vi.fn(),
  usePolicyRidersMock: vi.fn(),
  usePolicyBenefitsMock: vi.fn(),
  usePolicyEndorsementsMock: vi.fn(),
  usePolicyLoansMock: vi.fn(),
  usePolicyWithdrawalsMock: vi.fn(),
  useCreatePolicyEndorsementMutationMock: vi.fn(),
  useRequestPolicySurrenderMutationMock: vi.fn(),
  useRequestPolicyPaidUpMutationMock: vi.fn(),
  useCancelPolicyMutationMock: vi.fn(),
  surrenderMutateMock: vi.fn(),
  paidUpMutateMock: vi.fn(),
  cancelMutateMock: vi.fn(),
}))

vi.mock("react-router-dom", () => ({
  useParams: () => ({ policyId: "policy-1" }),
  useNavigate: () => navigateMock,
  useSearchParams: () => [searchParamsMock, setSearchParamsMock],
}))
vi.mock("../../components/ui/Toast", () => ({ useToast: () => ({ toast: vi.fn() }) }))
vi.mock("../../lib/access", () => ({
  useAccess: () => ({
    access: { permissions: [
      { module: "ol_policies", action: "view" },
      { module: "ol_policies", action: "endorse" },
      { module: "ol_policies", action: "service" },
      { module: "ol_policies", action: "print" },
      { module: "ol_policies", action: "reinstate" },
      { module: "ol_policies", action: "cancel" },
    ] },
    isSuperAdmin: false,
  }),
}))
vi.mock("../../lib/policiesHooks", () => ({
  usePolicyDetail: usePolicyDetailMock,
  usePolicyOptions: usePolicyOptionsMock,
  usePolicyMembers: usePolicyMembersMock,
  usePolicyRiders: usePolicyRidersMock,
  usePolicyBenefits: usePolicyBenefitsMock,
  usePolicyEndorsements: usePolicyEndorsementsMock,
  usePolicyLoans: usePolicyLoansMock,
  usePolicyWithdrawals: usePolicyWithdrawalsMock,
  useCreatePolicyEndorsementMutation: useCreatePolicyEndorsementMutationMock,
  useRequestPolicySurrenderMutation: useRequestPolicySurrenderMutationMock,
  useRequestPolicyPaidUpMutation: useRequestPolicyPaidUpMutationMock,
  useCancelPolicyMutation: useCancelPolicyMutationMock,
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
  allowedActions: ["view", "endorse", "service", "print", "cancel"],
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
  searchParamsMock.delete("tab")
  usePolicyDetailMock.mockReset().mockReturnValue({ data: activePolicy, isPending: false, isError: false, error: null, refetch: vi.fn() })
  usePolicyOptionsMock.mockReturnValue({ data: [{ value: "ACTIVE", label: "Active", meta: { badge_type: "POSITIVE" } }], isPending: false })
  usePolicyMembersMock.mockReturnValue({ data: activePolicy.members, isPending: false })
  usePolicyRidersMock.mockReturnValue({ data: activePolicy.riders, isPending: false })
  usePolicyBenefitsMock.mockReturnValue({ data: activePolicy.benefits, isPending: false })
  usePolicyEndorsementsMock.mockReturnValue({ data: { results: activePolicy.endorsements, count: activePolicy.endorsements.length }, isPending: false })
  usePolicyLoansMock.mockReturnValue({ data: { results: [], count: 0 }, isPending: false })
  usePolicyWithdrawalsMock.mockReturnValue({ data: { results: [], count: 0 }, isPending: false })
  useCreatePolicyEndorsementMutationMock.mockReturnValue({ mutate: vi.fn(), reset: vi.fn(), isPending: false, error: null })
  surrenderMutateMock.mockReset()
  paidUpMutateMock.mockReset()
  cancelMutateMock.mockReset()
  useRequestPolicySurrenderMutationMock.mockReturnValue({ mutate: surrenderMutateMock, reset: vi.fn(), isPending: false, error: null })
  useRequestPolicyPaidUpMutationMock.mockReturnValue({ mutate: paidUpMutateMock, reset: vi.fn(), isPending: false, error: null })
  useCancelPolicyMutationMock.mockReturnValue({ mutate: cancelMutateMock, reset: vi.fn(), isPending: false, error: null })
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

  it("renders members, riders, and benefits tables with Add actions only when endorsement is allowed", () => {
    searchParamsMock.set("tab", "members")
    const firstRender = render(<PolicyDetailPage />)
    expect(screen.getByRole("heading", { name: "Members" })).toBeInTheDocument()
    expect(screen.getByText("Amani Salum")).toBeInTheDocument()
    expect(screen.getByRole("heading", { name: "Attached riders" })).toBeInTheDocument()
    expect(screen.getByText("WP — Waiver of Premium")).toBeInTheDocument()
    expect(screen.getByRole("heading", { name: "Benefits" })).toBeInTheDocument()
    expect(screen.getByText("Death benefit")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Add Member" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Add Rider" })).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "Add Rider" }))
    expect(navigateMock).toHaveBeenCalledWith("/ordinary-life/policies/policy-1?action=endorse")
    firstRender.unmount()

    usePolicyDetailMock.mockReturnValue({ data: { ...activePolicy, allowedActions: ["view"] }, isPending: false, isError: false, error: null, refetch: vi.fn() })
    searchParamsMock.set("tab", "members")
    render(<PolicyDetailPage />)
    expect(screen.queryByRole("button", { name: "Add Member" })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Add Rider" })).not.toBeInTheDocument()
  })

  it("loads endorsement history and opens before-and-after detail", () => {
    searchParamsMock.set("tab", "endorsements")
    usePolicyEndorsementsMock.mockReturnValue({ data: { results: [{ id: "endorsement-1", endorsementNumber: "END-2026-000001", endorsementType: "ADDRESS_CHANGE", effectiveDate: "2026-06-01", status: "APPLIED", description: "Updated postal address", beforeSnapshot: { address: "Old address" }, afterSnapshot: { address: "New address" }, sourceChannel: "UI", createdAt: "2026-06-01T10:00:00Z" }], count: 1 }, isPending: false })
    render(<PolicyDetailPage />)
    expect(screen.getByRole("heading", { name: "Endorsement history" })).toBeInTheDocument()
    expect(screen.getByText("END-2026-000001")).toBeInTheDocument()
    expect(screen.getByText("Updated postal address")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "View Detail" })).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "View Detail" }))
    expect(screen.getByText("Before")).toBeInTheDocument()
    expect(screen.getByText("After")).toBeInTheDocument()
    expect(screen.getByText(/Old address/)).toBeInTheDocument()
    expect(screen.getByText(/New address/)).toBeInTheDocument()
  })

  it("opens surrender and cancellation modals with reason and confirmation safeguards", () => {
    render(<PolicyDetailPage />)
    fireEvent.click(screen.getByRole("button", { name: "Surrender" }))
    expect(screen.getByRole("dialog", { name: "Surrender Policy" })).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "Confirm surrender" }))
    expect(screen.getByText("Enter the reason for surrender so the request can be reviewed.")).toBeInTheDocument()
    fireEvent.change(screen.getByRole("textbox"), { target: { value: "Customer request" } })
    fireEvent.click(screen.getByRole("button", { name: "Confirm surrender" }))
    expect(screen.getByText("Confirm that you understand this action will terminate the policy.")).toBeInTheDocument()
    fireEvent.click(screen.getByRole("checkbox"))
    fireEvent.click(screen.getByRole("button", { name: "Confirm surrender" }))
    expect(surrenderMutateMock).toHaveBeenCalledWith(expect.objectContaining({ id: "policy-1", payload: { reason: "Customer request" } }), expect.any(Object))

    fireEvent.click(screen.getByRole("button", { name: "Cancel" }))
    fireEvent.click(screen.getByRole("button", { name: "Cancel Policy" }))
    expect(screen.getByRole("dialog", { name: "Cancel Policy" })).toBeInTheDocument()
    fireEvent.change(screen.getByRole("textbox"), { target: { value: "Free-look cancellation" } })
    fireEvent.click(screen.getByRole("checkbox"))
    fireEvent.click(screen.getByRole("button", { name: "Confirm cancellation" }))
    expect(cancelMutateMock).toHaveBeenCalledWith(expect.objectContaining({ id: "policy-1", payload: { reason: "Free-look cancellation" } }), expect.any(Object))
  })

  it("shows paid-up conversion only for a lapsed policy with service permission", () => {
    usePolicyDetailMock.mockReturnValue({ data: { ...activePolicy, status: "LAPSED", statusDisplay: "Lapsed", allowedActions: ["view", "service", "reinstate", "print"], contractSnapshot: { ...activePolicy.contractSnapshot, lapse_date: "2026-04-01" } }, isPending: false, isError: false, error: null, refetch: vi.fn() })
    render(<PolicyDetailPage />)
    expect(screen.getByRole("button", { name: "Convert to Paid-Up" })).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "Convert to Paid-Up" }))
    expect(screen.getByRole("dialog", { name: "Convert to Paid-Up" })).toBeInTheDocument()
    fireEvent.click(screen.getByRole("checkbox"))
    fireEvent.click(screen.getByRole("button", { name: "Confirm paid-up conversion" }))
    expect(paidUpMutateMock).toHaveBeenCalledWith(expect.objectContaining({ id: "policy-1", payload: {} }), expect.any(Object))
  })

  it("hides loan and servicing actions when a policy is lapsed and shows reinstatement guidance", async () => {
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
