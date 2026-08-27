import { http, HttpResponse } from "msw"

const WITHDRAWALS_BASE = "/api/v1/ol/withdrawals"
const POLICY_WITHDRAWALS_BASE = "/api/v1/ol/policies"

export type WithdrawalMockRow = {
  id: string
  withdrawal_number: string
  policy_id: string
  policy_number: string
  policy_display: string
  policyholder_name: string
  policyholder_display: string
  product_display: string
  agent_display: string
  branch_display: string
  currency: string
  gross_amount: string
  fee_amount: string
  net_payout: string
  cash_value_before: string
  loan_balance_before: string
  cash_value_after: string
  status: string
  status_display: string
  reason: string
  requested_at: string
  approved_at: string | null
  processed_at: string | null
  paid_at: string | null
  allowed_actions: string[]
  created_at: string
  updated_at: string
}

const initialWithdrawals: WithdrawalMockRow[] = [
  {
    id: "withdrawal-requested-1",
    withdrawal_number: "OL-WDR-2026-000001",
    policy_id: "policy-aman-1",
    policy_number: "ZIC-OL-2026-000001",
    policy_display: "ZIC-OL-2026-000001 — Amani Salum",
    policyholder_name: "Amani Salum",
    policyholder_display: "P-000001 — Amani Salum",
    product_display: "OL_EDU_GROWTH — Elimu Bora Growth Plan",
    agent_display: "AG-0004 — Faraja Intermediaries",
    branch_display: "ZNZ-MAIN — Zanzibar Main Branch",
    currency: "TZS",
    gross_amount: "250000.00",
    fee_amount: "12500.00",
    net_payout: "237500.00",
    cash_value_before: "2500000.00",
    loan_balance_before: "150000.00",
    cash_value_after: "2100000.00",
    status: "REQUESTED",
    status_display: "Requested",
    reason: "Education expenses",
    requested_at: "2026-08-18T09:00:00Z",
    approved_at: null,
    processed_at: null,
    paid_at: null,
    allowed_actions: ["view", "approve", "reject", "print"],
    created_at: "2026-08-18T09:00:00Z",
    updated_at: "2026-08-18T09:00:00Z",
  },
  {
    id: "withdrawal-paid-1",
    withdrawal_number: "OL-WDR-2026-000002",
    policy_id: "policy-fatma-1",
    policy_number: "ZIC-OL-2025-000021",
    policy_display: "ZIC-OL-2025-000021 — Fatma Ali",
    policyholder_name: "Fatma Ali",
    policyholder_display: "P-000021 — Fatma Ali",
    product_display: "OL_TERM_FAMILY — ZIC Term Assurance Family",
    agent_display: "AG-0007 — Zanzibar Life Brokers",
    branch_display: "ZNZ-NORTH — North Region Branch",
    currency: "TZS",
    gross_amount: "100000.00",
    fee_amount: "5000.00",
    net_payout: "95000.00",
    cash_value_before: "1200000.00",
    loan_balance_before: "0.00",
    cash_value_after: "1100000.00",
    status: "PAID",
    status_display: "Paid",
    reason: "Family emergency",
    requested_at: "2026-07-12T09:00:00Z",
    approved_at: "2026-07-13T10:00:00Z",
    processed_at: "2026-07-14T11:00:00Z",
    paid_at: "2026-07-14T12:00:00Z",
    allowed_actions: ["view", "print"],
    created_at: "2026-07-12T09:00:00Z",
    updated_at: "2026-07-14T12:00:00Z",
  },
]

const policyOptions = [
  { value: "policy-aman-1", label: "ZIC-OL-2026-000001 — Amani Salum", meta: { policy_number: "ZIC-OL-2026-000001", policyholder_name: "Amani Salum", status: "ACTIVE", currency: "TZS", cash_value: "2500000.00", loan_balance: "150000.00", available_limit: "2350000.00" } },
  { value: "policy-fatma-1", label: "ZIC-OL-2025-000021 — Fatma Ali", meta: { policy_number: "ZIC-OL-2025-000021", policyholder_name: "Fatma Ali", status: "ACTIVE", currency: "TZS", cash_value: "1200000.00", loan_balance: "0.00", available_limit: "1200000.00" } },
]

const optionCatalogs: Record<string, { value: string; label: string; meta: Record<string, unknown> }[]> = {
  policies: policyOptions,
  products: [{ value: "OL_EDU_GROWTH", label: "OL_EDU_GROWTH — Elimu Bora Growth Plan", meta: { active: true } }, { value: "OL_TERM_FAMILY", label: "OL_TERM_FAMILY — ZIC Term Assurance Family", meta: { active: true } }],
  branches: [{ value: "ZNZ-MAIN", label: "ZNZ-MAIN — Zanzibar Main Branch", meta: { active: true } }, { value: "ZNZ-NORTH", label: "ZNZ-NORTH — North Region Branch", meta: { active: true } }],
  agents: [{ value: "agent-faraja", label: "AG-0004 — Faraja Intermediaries", meta: { active: true } }, { value: "agent-brokers", label: "AG-0007 — Zanzibar Life Brokers", meta: { active: true } }],
  "payment-modes": [{ value: "BANK_TRANSFER", label: "Bank transfer", meta: { active: true } }, { value: "MOBILE_MONEY", label: "Mobile money", meta: { active: true } }],
}

let withdrawals = cloneRows(initialWithdrawals)

function cloneRows(rows: WithdrawalMockRow[]) {
  return rows.map((row) => ({ ...row, allowed_actions: [...row.allowed_actions] }))
}

export function resetWithdrawalMockState() {
  withdrawals = cloneRows(initialWithdrawals)
}

function data<T>(payload: T, status = 200) {
  return HttpResponse.json({ data: payload }, { status })
}

function error(status: number, code: string, message: string, resolutionSteps: string[], fieldErrors: Record<string, string[]> = {}) {
  return HttpResponse.json({ success: false, errorCode: code, message, resolutionSteps, fieldErrors, error: { code, message, details: { resolutionSteps, fieldErrors } } }, { status })
}

function page<T>(rows: T[], url: URL) {
  const pageSize = Math.max(1, Number(url.searchParams.get("page_size") ?? 20))
  const pageNumber = Math.max(1, Number(url.searchParams.get("page") ?? 1))
  const start = (pageNumber - 1) * pageSize
  return { results: rows.slice(start, start + pageSize), count: rows.length, page: pageNumber, page_size: pageSize, next: start + pageSize < rows.length, previous: pageNumber > 1 }
}

function findWithdrawal(id: string) {
  return withdrawals.find((row) => row.id === id)
}

function detailFor(row: WithdrawalMockRow) {
  return {
    ...row,
    breakdown: {
      withdrawal_id: row.id,
      currency: row.currency,
      cash_value_before: row.cash_value_before,
      gross_withdrawal: row.gross_amount,
      withdrawal_fee: row.fee_amount,
      fee_rate: "5.0000",
      fee_basis: "5% fixed",
      net_payout: row.net_payout,
      cash_value_after: row.cash_value_after,
      sum_assured_before: "10000000.00",
      sum_assured_after: "9000000.00",
      adjustment_ratio: "10.0000",
      audit_trail: [{ action: "CALCULATED", actor_name: "Sultan Admin", source_channel: "API", created_at: row.created_at }],
    },
    payments: row.status === "PAID" ? [{ id: `${row.id}-payment`, payment_mode: "BANK_TRANSFER", payment_mode_display: "Bank transfer", receipt_reference: "RCT-2026-000001", amount: row.net_payout, currency: row.currency, payment_date: row.paid_at, status: "COMPLETED", created_at: row.paid_at }] : [],
    audit_timeline: [
      { id: `${row.id}-event-1`, action: "REQUESTED", actor_display: "Sultan Admin", source_channel: "API", reason: row.reason, created_at: row.requested_at },
      ...(row.approved_at ? [{ id: `${row.id}-event-2`, action: "APPROVED", actor_display: "Finance Admin", source_channel: "API", reason: "Withdrawal approved", created_at: row.approved_at }] : []),
      ...(row.paid_at ? [{ id: `${row.id}-event-3`, action: "PAID", actor_display: "Finance Admin", source_channel: "API", reason: "Payout completed", created_at: row.paid_at }] : []),
    ],
    documents: [],
    policy_context: { policy_number: row.policy_number, cash_value_before: row.cash_value_before, cash_value_after: row.cash_value_after },
  }
}

export const withdrawalsHandlers = [
  http.get(`*${WITHDRAWALS_BASE}/options/:kind/`, ({ params, request }) => {
    const options = optionCatalogs[String(params.kind)]
    if (!options) return error(404, "OPTIONS_ENTITY_NOT_FOUND", "This withdrawal option catalog is not registered.", ["Choose a registered withdrawal option catalog.", "Ask an administrator to configure the withdrawal parameters."])
    const url = new URL(request.url)
    const q = (url.searchParams.get("q") ?? "").toLowerCase()
    return data(page(options.filter((option) => !q || `${option.value} ${option.label}`.toLowerCase().includes(q)), url))
  }),
  http.get(`*${WITHDRAWALS_BASE}/kpis/`, ({ request }) => {
    const url = new URL(request.url)
    const status = url.searchParams.get("status")
    const filtered = status ? withdrawals.filter((row) => row.status === status) : withdrawals
    const totalWithdrawn = filtered.reduce((sum, row) => sum + Number(row.gross_amount), 0).toFixed(2)
    const pending = filtered.filter((row) => row.status === "REQUESTED")
    return data({ total_withdrawn_current_month: totalWithdrawn, total_withdrawn_current_month_count: filtered.length, pending_approvals_count: pending.length, pending_approvals_amount: pending.reduce((sum, row) => sum + Number(row.gross_amount), 0).toFixed(2), processing_payouts_count: filtered.filter((row) => row.status === "PROCESSING").length, average_fee_amount: filtered.length ? (filtered.reduce((sum, row) => sum + Number(row.fee_amount), 0) / filtered.length).toFixed(2) : "0.00", currency: "TZS", timestamp: "2026-08-27T08:00:00Z" })
  }),
  http.get(`*${WITHDRAWALS_BASE}/:withdrawalId/breakdown/`, ({ params }) => {
    const row = findWithdrawal(String(params.withdrawalId))
    return row ? data(detailFor(row).breakdown) : error(404, "WITHDRAWAL_NOT_FOUND", "The withdrawal could not be found.", ["Return to the Withdrawals register and choose an available request."])
  }),
  http.get(`*${WITHDRAWALS_BASE}/:withdrawalId/payments/`, ({ params, request }) => {
    const row = findWithdrawal(String(params.withdrawalId))
    return row ? data(page(detailFor(row).payments, new URL(request.url))) : error(404, "WITHDRAWAL_NOT_FOUND", "The withdrawal could not be found.", ["Return to the Withdrawals register and choose an available request."])
  }),
  http.get(`*${WITHDRAWALS_BASE}/:withdrawalId/audit/`, ({ params, request }) => {
    const row = findWithdrawal(String(params.withdrawalId))
    return row ? data(page(detailFor(row).audit_timeline, new URL(request.url))) : error(404, "WITHDRAWAL_NOT_FOUND", "The withdrawal could not be found.", ["Return to the Withdrawals register and choose an available request."])
  }),
  http.post(`*${WITHDRAWALS_BASE}/:withdrawalId/print-statement/`, ({ params }) => {
    const row = findWithdrawal(String(params.withdrawalId))
    return row ? data({ instance: { id: `${row.id}-statement`, document_type: "OL_WITHDRAWAL_STATEMENT", template_version: 1, generated_by_display: "Sultan Admin" }, preview_url: `/api/v1/documents/instances/${row.id}-statement/preview/`, signed_download_url: `/api/v1/documents/instances/${row.id}-statement/download/?ticket=mock-withdrawal-${row.id}` }, 201) : error(404, "WITHDRAWAL_NOT_FOUND", "The withdrawal could not be found.", ["Return to the Withdrawals register and choose an available request."])
  }),
  http.post(`*${WITHDRAWALS_BASE}/:withdrawalId/:action/`, async ({ params, request }) => {
    const row = findWithdrawal(String(params.withdrawalId))
    if (!row) return error(404, "WITHDRAWAL_NOT_FOUND", "The withdrawal could not be found.", ["Return to the Withdrawals register and choose an available request."])
    const action = String(params.action)
    const body = await request.json().catch(() => ({})) as { reason?: string }
    if (["reject", "cancel", "reverse"].includes(action) && !String(body.reason ?? "").trim()) return error(400, "REASON_REQUIRED", "A reason is required before this withdrawal can be changed.", ["Explain why the withdrawal is being changed."], { reason: ["Enter a reason."] })
    if (action === "approve") { row.status = "APPROVED"; row.status_display = "Approved"; row.approved_at = "2026-08-27T09:00:00Z"; row.allowed_actions = ["view", "process-payout", "print"] }
    if (action === "process-payout") { row.status = "PAID"; row.status_display = "Paid"; row.processed_at = "2026-08-27T10:00:00Z"; row.paid_at = "2026-08-27T10:00:00Z"; row.allowed_actions = ["view", "reverse", "print"] }
    if (action === "reject") { row.status = "DECLINED"; row.status_display = "Declined"; row.allowed_actions = ["view", "print"] }
    if (action === "cancel") { row.status = "CANCELLED"; row.status_display = "Cancelled"; row.allowed_actions = ["view", "print"] }
    if (action === "reverse") { row.status = "REVERSED"; row.status_display = "Reversed"; row.allowed_actions = ["view", "print"] }
    if (action === "offset") row.allowed_actions = ["view", "print"]
    row.updated_at = "2026-08-27T10:00:00Z"
    return data({ withdrawal: row })
  }),
  http.get(`*${WITHDRAWALS_BASE}/:withdrawalId/`, ({ params }) => {
    const row = findWithdrawal(String(params.withdrawalId))
    return row ? data(detailFor(row)) : error(404, "WITHDRAWAL_NOT_FOUND", "The withdrawal could not be found.", ["Return to the Withdrawals register and choose an available request."])
  }),
  http.get(`*${WITHDRAWALS_BASE}/`, ({ request }) => {
    const url = new URL(request.url)
    const q = (url.searchParams.get("q") ?? "").toLowerCase()
    const status = url.searchParams.get("status")
    const product = (url.searchParams.get("product") ?? "").toLowerCase()
    const branch = (url.searchParams.get("branch") ?? "").toLowerCase()
    const agent = (url.searchParams.get("agent") ?? "").toLowerCase()
    const pendingOnly = url.searchParams.get("pending_approval_only") === "true"
    const filtered = withdrawals.filter((row) => (!q || `${row.withdrawal_number} ${row.policy_number} ${row.policyholder_name} ${row.policyholder_display}`.toLowerCase().includes(q)) && (!status || row.status === status) && (!product || row.product_display.toLowerCase().includes(product)) && (!branch || row.branch_display.toLowerCase().includes(branch)) && (!agent || row.agent_display.toLowerCase().includes(agent)) && (!pendingOnly || row.status === "REQUESTED"))
    return data(page(filtered, url))
  }),
  http.post(`*${POLICY_WITHDRAWALS_BASE}/:policyId/withdrawals/`, async ({ params, request }) => {
    const body = await request.json() as { amount?: string | number; reason?: string }
    const policy = policyOptions.find((item) => item.value === String(params.policyId))
    if (!policy) return error(404, "POLICY_NOT_FOUND", "The selected policy could not be found.", ["Search again and select an active policy."])
    const amount = Number(body.amount ?? 0)
    const available = Number(policy.meta.available_limit)
    if (amount <= 0) return error(400, "WITHDRAWAL_AMOUNT_REQUIRED", "Enter a withdrawal amount greater than zero.", ["Enter an amount within the Available Limit."], { amount: ["Amount must be greater than zero."] })
    if (amount > available) return error(422, "WITHDRAWAL_LIMIT_EXCEEDED", "Amount exceeds the available cash value limit.", ["Reduce the requested amount to the Available Limit or review active loan balances."], { amount: [`The maximum available amount is ${available.toFixed(2)}.`] })
    const id = `withdrawal-request-${String(params.policyId)}`
    const row: WithdrawalMockRow = { ...initialWithdrawals[0], id, withdrawal_number: "OL-WDR-2026-000003", policy_id: String(params.policyId), policy_number: String(policy.meta.policy_number), policy_display: policy.label, policyholder_name: String(policy.meta.policyholder_name), policyholder_display: policy.label, gross_amount: amount.toFixed(2), fee_amount: (amount * 0.05).toFixed(2), net_payout: (amount * 0.95).toFixed(2), cash_value_before: String(policy.meta.cash_value), loan_balance_before: String(policy.meta.loan_balance), cash_value_after: (Number(policy.meta.cash_value) - amount).toFixed(2), status: "REQUESTED", status_display: "Requested", reason: String(body.reason ?? ""), requested_at: "2026-08-27T08:00:00Z", approved_at: null, processed_at: null, paid_at: null, allowed_actions: ["view", "approve", "reject", "print"], created_at: "2026-08-27T08:00:00Z", updated_at: "2026-08-27T08:00:00Z" }
    withdrawals = [row, ...withdrawals.filter((item) => item.id !== id)]
    return data({ withdrawal: row }, 201)
  }),
]
