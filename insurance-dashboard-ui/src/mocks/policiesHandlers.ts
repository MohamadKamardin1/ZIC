import { http, HttpResponse } from "msw"
import { POLICY_OPTIONS_BASE, POLICIES_BASE, type PolicyOption } from "../lib/policies"

const ids = {
  active: "policy-active-1",
  lapsed: "policy-lapsed-1",
  cancelled: "policy-cancelled-1",
  proposal: "proposal-ready-1",
  document: "policy-document-1",
}

const basePolicies = [
  {
    id: ids.active,
    policy_number: "ZIC-OL-2026-000001",
    proposal_ref_display: "OLP-2026-000001 — Amani Salum",
    policyholder_display: "P-000018 — Amani Salum",
    policyholder_name: "Amani Salum",
    product_plan_display: "OL_EDU_GROWTH — Elimu Bora Growth Plan",
    product_name: "Elimu Bora Growth Plan",
    plan_name: "Education savings",
    agent_display: "AG-0004 — Faraja Intermediaries",
    agent_name: "Faraja Intermediaries",
    currency: "TZS",
    sum_assured: "25000000.00",
    premium_amount: "120000.00",
    premium_frequency: "MONTHLY",
    term_years: 15,
    risk_commencement_date: "2026-01-15",
    maturity_date: "2041-01-15",
    status: "ACTIVE",
    status_display: "Active",
    allowed_actions: ["view", "service", "endorse", "print", "cancel"],
    version: 1,
    created_at: "2026-01-15T09:00:00Z",
    updated_at: "2026-08-20T09:00:00Z",
  },
  {
    id: ids.lapsed,
    policy_number: "ZIC-OL-2026-000002",
    proposal_ref_display: "OLP-2026-000002 — Halima Juma",
    policyholder_display: "P-000019 — Halima Juma",
    policyholder_name: "Halima Juma",
    product_plan_display: "OL_TERM_FAMILY — ZIC Term Assurance Family",
    product_name: "ZIC Term Assurance Family",
    plan_name: "Family protection",
    agent_display: "AG-0007 — Zanzibar Life Brokers",
    agent_name: "Zanzibar Life Brokers",
    currency: "TZS",
    sum_assured: "40000000.00",
    premium_amount: "85000.00",
    premium_frequency: "MONTHLY",
    term_years: 10,
    risk_commencement_date: "2026-02-01",
    maturity_date: "2036-02-01",
    status: "LAPSED",
    status_display: "Lapsed",
    allowed_actions: ["view", "service", "reinstate", "print"],
    version: 1,
    created_at: "2026-02-01T09:00:00Z",
    updated_at: "2026-08-10T09:00:00Z",
  },
  {
    id: ids.cancelled,
    policy_number: "ZIC-OL-2026-000003",
    proposal_ref_display: "OLP-2026-000003 — Fatma Ali",
    policyholder_display: "P-000020 — Fatma Ali",
    policyholder_name: "Fatma Ali",
    product_plan_display: "OL_TERM_STANDARD — ZIC Term Assurance Standard",
    product_name: "ZIC Term Assurance Standard",
    plan_name: "Standard protection",
    agent_display: "AG-0004 — Faraja Intermediaries",
    agent_name: "Faraja Intermediaries",
    currency: "TZS",
    sum_assured: "15000000.00",
    premium_amount: "32000.00",
    premium_frequency: "MONTHLY",
    term_years: 10,
    risk_commencement_date: "2026-03-01",
    maturity_date: "2036-03-01",
    status: "CANCELLED",
    status_display: "Cancelled",
    allowed_actions: ["view", "print"],
    version: 1,
    created_at: "2026-03-01T09:00:00Z",
    updated_at: "2026-03-03T09:00:00Z",
  },
]

const policyOptions: Record<string, PolicyOption[]> = {
  products: [
    { value: "product-edu", label: "OL_EDU_GROWTH — Elimu Bora Growth Plan", meta: { plan_type: "WITH_PROFIT" } },
    { value: "product-term", label: "OL_TERM_FAMILY — ZIC Term Assurance Family", meta: { plan_type: "TERM" } },
  ],
  statuses: [
    { value: "ACTIVE", label: "Active", meta: { badge_type: "POSITIVE" } },
    { value: "LAPSED", label: "Lapsed", meta: { badge_type: "WARNING" } },
    { value: "PAID_UP", label: "Paid-up", meta: { badge_type: "INFO" } },
    { value: "SURRENDERED", label: "Surrendered", meta: { badge_type: "NEUTRAL" } },
    { value: "MATURED", label: "Matured", meta: { badge_type: "POSITIVE" } },
    { value: "CANCELLED", label: "Cancelled", meta: { badge_type: "NEGATIVE" } },
  ],
  endorsement_types: [
    { value: "PREMIUM_CHANGE", label: "Premium change" },
    { value: "ADDRESS_CHANGE", label: "Address change" },
    { value: "MEMBER_ADD", label: "Add member" },
    { value: "MEMBER_REMOVE", label: "Remove member" },
  ],
  agents: [{ value: "agent-4", label: "AG-0004 — Faraja Intermediaries", meta: { partner_type: "AGENT" } }],
  branches: [{ value: "branch-zanzibar", label: "Zanzibar Main Branch", meta: { code: "ZNZ-MAIN" } }],
  currencies: [{ value: "TZS", label: "TZS — Tanzanian Shilling", meta: { symbol: "TSh" } }],
}

function data<T>(payload: T, status = 200) {
  return HttpResponse.json({ data: payload }, { status })
}

function error(status: number, code: string, message: string, resolutionSteps: string[], fieldErrors: Record<string, string[]> = {}) {
  return HttpResponse.json({
    success: false,
    errorCode: code,
    message,
    resolutionSteps,
    fieldErrors,
    error: { code, message, details: { resolutionSteps, fieldErrors } },
  }, { status })
}

function page<T>(rows: T[], url: URL) {
  const pageSize = Math.max(1, Number(url.searchParams.get("page_size") ?? 20))
  const pageNumber = Math.max(1, Number(url.searchParams.get("page") ?? 1))
  const start = (pageNumber - 1) * pageSize
  return { results: rows.slice(start, start + pageSize), count: rows.length, page: pageNumber, page_size: pageSize, next: start + pageSize < rows.length, previous: pageNumber > 1 }
}

function detailFor(id: string) {
  const policy = basePolicies.find((item) => item.id === id)
  if (!policy) return null
  return {
    ...policy,
    contract_snapshot: {
      policy_number: policy.policy_number,
      product_plan: policy.product_plan_display,
      sum_assured: policy.sum_assured,
      premium_amount: policy.premium_amount,
      premium_frequency: policy.premium_frequency,
      term_years: policy.term_years,
      free_look_days: 30,
    },
    members: [
      { id: "member-1", member_relation: "Principal member", name: policy.policyholder_name, dob: "1990-05-12", gender: "FEMALE", benefit_amount: policy.sum_assured },
    ],
    riders: [{ id: "rider-1", rider_code: "WP — Waiver of Premium", sum_assured: policy.sum_assured, amount: "0.00", premium: "2500.00" }],
    benefits: [{ id: "benefit-1", benefit_type: "Death benefit", calculation_basis: "SUM_ASSURED", amount: policy.sum_assured }],
    endorsements: [{ id: "endorsement-1", endorsement_number: "END-2026-000001", endorsement_type: "ADDRESS_CHANGE", effective_date: "2026-06-01", description: "Updated postal address", status: "APPLIED", reason: "Customer request", source_channel: "UI", created_at: "2026-06-01T10:00:00Z" }],
    audit_logs: [{ id: "audit-1", event_type: "PolicyIssued", from_status: null, to_status: "ACTIVE", reason: "Eligible proposal with first premium posted", source_channel: "API", actor_display: "Sultan Admin", created_at: "2026-01-15T09:00:00Z" }],
    linked_proposal: { proposal_number: policy.proposal_ref_display, status: "CONVERTED" },
    linked_commitments: [{ commitment_number: "OLC-2026-000001", status: "COMPLETED", amount_paid: policy.premium_amount, balance: "0.00" }],
  }
}

function printResult(policyId: string, documentType: string) {
  return {
    instance: { id: ids.document, document_type: documentType, template_name: documentType === "POLICY_CONTRACT" ? "Policy Contract" : "Schedule of Benefits", template_version: 1, page_count: 2, generated_by_display: "Sultan Admin", generated_at: "2026-08-26T10:00:00Z" },
    preview_url: `/api/v1/documents/instances/${ids.document}/preview/`,
    signed_download_url: `/api/v1/documents/instances/${ids.document}/download/?ticket=mock-${policyId}-${documentType.toLowerCase()}`,
  }
}

export const policiesHandlers = [
  http.get(`*${POLICIES_BASE}/kpis/`, () => data({ total_active_policies: 2, total_sum_assured: "65000000.00", new_policies_this_month: 3, lapsed_policies_count: 1, lapsed_policies_value: "40000000.00", maturing_soon_count: 1, currency: "TZS", sum_assured_by_currency: { TZS: "65000000.00" }, timestamp: "2026-08-26T10:00:00Z" })),
  http.get(`*${POLICIES_BASE}/:policyId/members/`, ({ params }) => {
    const policy = detailFor(String(params.policyId))
    return policy ? data(policy.members) : error(404, "POLICY_NOT_FOUND", "The policy could not be found.", ["Return to the policy list and choose an available policy."])
  }),
  http.get(`*${POLICIES_BASE}/:policyId/riders/`, ({ params }) => {
    const policy = detailFor(String(params.policyId))
    return policy ? data(policy.riders) : error(404, "POLICY_NOT_FOUND", "The policy could not be found.", ["Return to the policy list and choose an available policy."])
  }),
  http.get(`*${POLICIES_BASE}/:policyId/benefits/`, ({ params }) => {
    const policy = detailFor(String(params.policyId))
    return policy ? data(policy.benefits) : error(404, "POLICY_NOT_FOUND", "The policy could not be found.", ["Return to the policy list and choose an available policy."])
  }),
  http.get(`*${POLICIES_BASE}/:policyId/endorsements/`, ({ params, request }) => {
    const policy = detailFor(String(params.policyId))
    return policy ? data(page(policy.endorsements, new URL(request.url))) : error(404, "POLICY_NOT_FOUND", "The policy could not be found.", ["Return to the policy list and choose an available policy."])
  }),
  http.get(`*${POLICIES_BASE}/:policyId/loans/`, ({ params, request }) => {
    const policy = detailFor(String(params.policyId))
    return policy ? data(page([{ id: "loan-1", loan_number: "LOAN-2026-000001", amount: "1000000.00", principal_amount: "1000000.00", outstanding_principal: "750000.00", outstanding_interest: "12000.00", interest_rate: "8.00", currency: "TZS", status: "DISBURSED" }], new URL(request.url))) : error(404, "POLICY_NOT_FOUND", "The policy could not be found.", ["Return to the policy list and choose an available policy."])
  }),
  http.get(`*${POLICIES_BASE}/:policyId/withdrawals/`, ({ params, request }) => {
    const policy = detailFor(String(params.policyId))
    return policy ? data(page([{ id: "withdrawal-1", request_number: "WDR-2026-000001", amount: "500000.00", net_amount: "490000.00", status: "PAID" }], new URL(request.url))) : error(404, "POLICY_NOT_FOUND", "The policy could not be found.", ["Return to the policy list and choose an available policy."])
  }),
  http.post(`*${POLICIES_BASE}/:policyId/print-contract/`, ({ params }) => detailFor(String(params.policyId)) ? data(printResult(String(params.policyId), "POLICY_CONTRACT"), 201) : error(404, "POLICY_NOT_FOUND", "The policy could not be found.", ["Return to the policy list and choose an available policy."])),
  http.post(`*${POLICIES_BASE}/:policyId/print-schedule/`, ({ params }) => detailFor(String(params.policyId)) ? data(printResult(String(params.policyId), "POLICY_SCHEDULE"), 201) : error(404, "POLICY_NOT_FOUND", "The policy could not be found.", ["Return to the policy list and choose an available policy."])),
  http.get(`*${POLICIES_BASE}/:policyId/`, ({ params }) => {
    const detail = detailFor(String(params.policyId))
    return detail ? data(detail) : error(404, "POLICY_NOT_FOUND", "The policy could not be found.", ["Return to the policy list and choose an available policy."])
  }),
  http.post(`*${POLICIES_BASE}/issue/`, async ({ request }) => {
    const body = await request.json() as { proposal_id?: string }
    if (body.proposal_id !== ids.proposal) return error(422, "POLICY_FIRST_PREMIUM_NOT_POSTED", "The proposal is not eligible for policy issuance because its first premium is not fully posted.", ["Open the proposal payment readiness panel.", "Complete and post the first premium, then retry issuance."], { proposal_id: ["Select a proposal with a fully funded first premium."] })
    return data({ id: "policy-issued-1", policy_number: "ZIC-OL-2026-000004", status: "ACTIVE", created: true }, 201)
  }),
  http.post(`*${POLICIES_BASE}/:policyId/endorsements/`, async ({ params, request }) => {
    const policy = detailFor(String(params.policyId))
    if (!policy) return error(404, "POLICY_NOT_FOUND", "The policy could not be found.", ["Return to the policy list and choose an available policy."])
    const body = await request.json() as Record<string, unknown>
    return data({ id: "endorsement-new", endorsement_number: "END-2026-000002", endorsement_type: String(body.endorsement_type ?? "ADDRESS_CHANGE"), status: "PENDING", description: String(body.description ?? ""), reason: String(body.reason ?? "") }, 201)
  }),
  http.post(`*${POLICIES_BASE}/:policyId/loans/`, ({ params }) => detailFor(String(params.policyId)) ? data({ id: "loan-new", loan_number: "LOAN-2026-000002", status: "PENDING_APPROVAL", requested_amount: "500000.00" }, 201) : error(404, "POLICY_NOT_FOUND", "The policy could not be found.", ["Return to the policy list and choose an available policy."])),
  http.post(`*${POLICIES_BASE}/loans/:loanId/approve/`, ({ params }) => data({ id: String(params.loanId), status: "APPROVED" })),
  http.post(`*${POLICIES_BASE}/loans/:loanId/disburse/`, ({ params }) => data({ id: String(params.loanId), status: "DISBURSED" })),
  http.post(`*${POLICIES_BASE}/loans/:loanId/repay/`, ({ params }) => data({ id: String(params.loanId), status: "PARTIALLY_REPAID", interest_component: "1000.00", principal_component: "9000.00" })),
  http.post(`*${POLICIES_BASE}/:policyId/withdrawals/`, ({ params }) => detailFor(String(params.policyId)) ? data({ id: "withdrawal-new", request_number: "WDR-2026-000002", status: "PENDING" }, 201) : error(404, "POLICY_NOT_FOUND", "The policy could not be found.", ["Return to the policy list and choose an available policy."])),
  http.post(`*${POLICIES_BASE}/:policyId/surrender/`, ({ params }) => detailFor(String(params.policyId)) ? data({ id: "surrender-new", request_number: "SUR-2026-000001", status: "SURRENDER_PENDING", net_surrender_value: "8750000.00" }, 201) : error(404, "POLICY_NOT_FOUND", "The policy could not be found.", ["Return to the policy list and choose an available policy."])),
  http.post(`*${POLICIES_BASE}/:policyId/maturity/`, ({ params }) => detailFor(String(params.policyId)) ? data({ id: "maturity-1", claim_number: "MAT-2026-000001", status: "PENDING_APPROVAL" }, 201) : error(404, "POLICY_NOT_FOUND", "The policy could not be found.", ["Return to the policy list and choose an available policy."])),
  http.get(`*${POLICY_OPTIONS_BASE}/:entity/`, ({ params, request }) => {
    const values = policyOptions[String(params.entity)]
    if (!values) return error(404, "OPTIONS_ENTITY_NOT_FOUND", "This policy option catalog is not registered.", ["Choose a registered policy option catalog.", "Ask an administrator to configure the policy parameter registry."])
    const url = new URL(request.url)
    const query = (url.searchParams.get("q") ?? "").toLowerCase()
    return data(page(values.filter((option) => !query || option.label.toLowerCase().includes(query)), url))
  }),
  http.get(`*${POLICIES_BASE}/`, ({ request }) => {
    const url = new URL(request.url)
    const query = (url.searchParams.get("search") ?? "").toLowerCase()
    const status = url.searchParams.get("status")
    const product = url.searchParams.get("product")
    const filtered = basePolicies.filter((policy) => (!query || `${policy.policy_number} ${policy.policyholder_name} ${policy.product_plan_display}`.toLowerCase().includes(query)) && (!status || policy.status === status) && (!product || policy.product_plan_display.toLowerCase().includes(product.toLowerCase())))
    return data(page(filtered, url))
  }),
]
