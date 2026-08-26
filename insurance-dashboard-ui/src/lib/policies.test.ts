import { beforeEach, describe, expect, it, vi } from "vitest"
const { requestMock } = vi.hoisted(() => ({ requestMock: vi.fn() }))

vi.mock("./apiClient", async () => {
  const actual = await vi.importActual<typeof import("./apiClient")>("./apiClient")
  return { ...actual, request: requestMock }
})

import { cancelPolicy, getPolicy, getPolicyKpis, getPolicyOptions, issuePolicy, listPolicies, listPolicyBenefits, listPolicyMembers, listPolicyRiders, requestPolicyPaidUp, requestPolicySurrender } from "./policies"

beforeEach(() => requestMock.mockReset())

describe("OL Policies API contract", () => {
  it("maps list filters to the canonical policy endpoint and human-readable fields", async () => {
    requestMock.mockResolvedValue({
      results: [{ id: "policy-1", policy_number: "ZIC-OL-2026-000001", policyholder_display: "P-000018 — Amani Salum", product_plan_display: "OL_EDU_GROWTH — Elimu Bora Growth Plan", agent_display: "AG-0004 — Faraja Intermediaries", currency: "TZS", sum_assured: "25000000.00", premium_amount: "120000.00", status: "ACTIVE", status_display: "Active" }],
      count: 1,
      page: 1,
      page_size: 10,
    })

    const result = await listPolicies({ search: "Amani", status: "ACTIVE", branch: "branch-zanzibar", page: 1, pageSize: 10 })

    expect(requestMock).toHaveBeenCalledWith(expect.stringContaining("/api/v1/ol/policies/?"))
    expect(requestMock.mock.calls[0][0]).toContain("search=Amani")
    expect(requestMock.mock.calls[0][0]).toContain("status=ACTIVE")
    expect(result.results[0]).toMatchObject({
      policyNumber: "ZIC-OL-2026-000001",
      policyholderDisplay: "P-000018 — Amani Salum",
      productPlanDisplay: "OL_EDU_GROWTH — Elimu Bora Growth Plan",
      agentDisplay: "AG-0004 — Faraja Intermediaries",
      status: "ACTIVE",
    })
  })

  it("normalizes detail children and contract snapshot without presenting foreign-key UUIDs", async () => {
    requestMock.mockResolvedValue({
      id: "policy-1",
      policy_number: "ZIC-OL-2026-000001",
      policyholder_display: "P-000018 — Amani Salum",
      policyholder_name: "Amani Salum",
      product_plan_display: "OL_EDU_GROWTH — Elimu Bora Growth Plan",
      agent_display: "AG-0004 — Faraja Intermediaries",
      currency: "TZS",
      sum_assured: "25000000.00",
      premium_amount: "120000.00",
      status: "ACTIVE",
      contract_snapshot: { policy_number: "ZIC-OL-2026-000001" },
      members: [{ id: "member-1", member_relation: "Principal member", name: "Amani Salum", benefit_amount: "25000000.00" }],
      riders: [{ id: "rider-1", rider_code: "WP — Waiver of Premium", sum_assured: "25000000.00" }],
      benefits: [{ id: "benefit-1", benefit_type: "Death benefit", calculation_basis: "SUM_ASSURED", amount: "25000000.00" }],
      endorsements: [],
      audit_logs: [],
      linked_proposal: { proposal_number: "OLP-2026-000001", status: "CONVERTED" },
    })

    const result = await getPolicy("policy-1")

    expect(requestMock).toHaveBeenCalledWith("/api/v1/ol/policies/policy-1/")
    expect(result.policyholderName).toBe("Amani Salum")
    expect(result.members[0]).toMatchObject({ name: "Amani Salum", memberRelation: "Principal member" })
    expect(result.riders[0].riderCode).toContain("WP")
    expect(result.benefits[0].benefitType).toBe("Death benefit")
    expect(result.contractSnapshot.policy_number).toBe("ZIC-OL-2026-000001")
    expect(result.linkedProposal).toMatchObject({ status: "CONVERTED" })
  })

  it("normalizes KPI totals and currency breakdown", async () => {
    requestMock.mockResolvedValue({ total_active_policies: 2, total_sum_assured: "65000000.00", new_policies_this_month: 3, lapsed_policies_count: 1, lapsed_policies_value: "40000000.00", maturing_soon_count: 1, currency: "TZS", sum_assured_by_currency: { TZS: "65000000.00" }, timestamp: "2026-08-26T10:00:00Z" })

    const result = await getPolicyKpis({ status: "ACTIVE", currency: "TZS" })

    expect(requestMock).toHaveBeenCalledWith("/api/v1/ol/policies/kpis/?status=ACTIVE&currency=TZS")
    expect(result).toMatchObject({ totalActivePolicies: 2, totalSumAssured: "65000000.00", lapsedPoliciesCount: 1, currency: "TZS", sumAssuredByCurrency: { TZS: "65000000.00" } })
    expect(result.timestamp).toBe("2026-08-26T10:00:00Z")
  })

  it("loads standard policy options with labels and metadata", async () => {
    requestMock.mockResolvedValue({ results: [{ value: "ACTIVE", label: "Active", meta: { badge_type: "POSITIVE" } }, { value: "LAPSED", label: "Lapsed" }], count: 2, page: 1, page_size: 20 })

    const options = await getPolicyOptions("statuses", { q: "lapsed" })

    expect(requestMock).toHaveBeenCalledWith("/api/v1/ol/options/statuses/?q=lapsed")
    expect(options).toEqual(expect.arrayContaining([expect.objectContaining({ value: "ACTIVE", label: "Active" }), expect.objectContaining({ value: "LAPSED", label: "Lapsed" })]))
  })

  it("loads dedicated composition collections from canonical member, rider, and benefit endpoints", async () => {
    requestMock
      .mockResolvedValueOnce([{ id: "member-1", member_relation: "Spouse", name: "Halima Salum", dob: "1992-06-09", gender: "FEMALE", benefit_amount: "10000000.00" }])
      .mockResolvedValueOnce([{ id: "rider-1", rider_code: "AD — Accidental Death", sum_assured: "15000000.00", premium: "2500.00" }])
      .mockResolvedValueOnce([{ id: "benefit-1", benefit_type: "Death benefit", calculation_basis: "SUM_ASSURED", amount: "25000000.00" }])

    const [members, riders, benefits] = await Promise.all([listPolicyMembers("policy-1"), listPolicyRiders("policy-1"), listPolicyBenefits("policy-1")])

    expect(requestMock).toHaveBeenNthCalledWith(1, "/api/v1/ol/policies/policy-1/members/")
    expect(requestMock).toHaveBeenNthCalledWith(2, "/api/v1/ol/policies/policy-1/riders/")
    expect(requestMock).toHaveBeenNthCalledWith(3, "/api/v1/ol/policies/policy-1/benefits/")
    expect(members[0]).toMatchObject({ name: "Halima Salum", memberRelation: "Spouse" })
    expect(riders[0]).toMatchObject({ riderCode: "AD — Accidental Death", premium: "2500.00" })
    expect(benefits[0]).toMatchObject({ benefitType: "Death benefit", calculationBasis: "SUM_ASSURED" })
  })

  it("posts surrender, paid-up, and cancellation actions to canonical terminal endpoints", async () => {
    requestMock
      .mockResolvedValueOnce({ surrender_request: { status: "SURRENDER_PENDING", net_surrender_value: "8750000.00" }, policy: { id: "policy-1" }, created: true })
      .mockResolvedValueOnce({ id: "policy-1", policy_number: "ZIC-OL-2026-000001", status: "PAID_UP" })
      .mockResolvedValueOnce({ policy: { id: "policy-1", status: "CANCELLED" }, refund: { amount: "120000.00" } })

    const surrender = await requestPolicySurrender("policy-1", { reason: "Customer request" })
    const paidUp = await requestPolicyPaidUp("policy-1")
    const cancelled = await cancelPolicy("policy-1", { reason: "Free-look cancellation" })

    expect(surrender).toMatchObject({ created: true, surrender_request: { status: "SURRENDER_PENDING" } })
    expect(paidUp).toMatchObject({ id: "policy-1", policyNumber: "ZIC-OL-2026-000001", status: "PAID_UP" })
    expect(cancelled).toMatchObject({ refund: { amount: "120000.00" } })
    expect(requestMock).toHaveBeenNthCalledWith(1, "/api/v1/ol/policies/policy-1/surrender/", expect.objectContaining({ method: "POST", body: JSON.stringify({ reason: "Customer request" }) }))
    expect(requestMock).toHaveBeenNthCalledWith(2, "/api/v1/ol/policies/policy-1/paid-up/", expect.objectContaining({ method: "POST", body: JSON.stringify({}) }))
    expect(requestMock).toHaveBeenNthCalledWith(3, "/api/v1/ol/policies/policy-1/cancel/", expect.objectContaining({ method: "POST", body: JSON.stringify({ reason: "Free-look cancellation" }) }))
  })

  it("posts an eligible proposal to the canonical issue endpoint", async () => {
    requestMock.mockResolvedValue({ id: "policy-1", policy_number: "ZIC-OL-2026-000001", status: "ACTIVE" })

    const result = await issuePolicy("proposal-ready")

    expect(result).toMatchObject({ id: "policy-1", policy_number: "ZIC-OL-2026-000001", status: "ACTIVE" })
    expect(requestMock).toHaveBeenCalledWith("/api/v1/ol/policies/issue/", expect.objectContaining({ method: "POST", body: JSON.stringify({ proposal_id: "proposal-ready" }) }))
  })
})
