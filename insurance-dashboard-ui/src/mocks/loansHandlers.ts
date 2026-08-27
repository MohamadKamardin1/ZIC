import { http, HttpResponse } from "msw"

const LOANS_BASE = "/api/v1/ol/loans"

export type LoanMockRow = {
  id: string
  loan_number: string
  policy_number: string
  policy_display: string
  policyholder_name: string
  partner_display: string
  product_display: string
  agent_display: string
  branch_display: string
  currency: string
  principal_amount: string
  cash_value_snapshot: string
  disbursed_amount: string
  repayment_mode: string
  interest_rate: string
  compounding_frequency: string
  term_months: number
  disbursement_date: string | null
  maturity_date: string | null
  status: string
  status_display: string
  total_repaid: string
  outstanding_balance: string
  approval_required: boolean
  allowed_actions: string[]
  created_at: string
  updated_at: string
}

const initialLoans: LoanMockRow[] = [
  {
    id: "loan-active-1",
    loan_number: "OL-LOAN-2026-000001",
    policy_number: "ZIC-OL-2026-000001",
    policy_display: "ZIC-OL-2026-000001 — Amani Salum",
    policyholder_name: "Amani Salum",
    partner_display: "P-000001 — Amani Salum",
    product_display: "OL_EDU_GROWTH — Elimu Bora Growth Plan",
    agent_display: "AG-0004 — Faraja Intermediaries",
    branch_display: "ZNZ-MAIN — Zanzibar Main Branch",
    currency: "TZS",
    principal_amount: "1000000.00",
    cash_value_snapshot: "2500000.00",
    disbursed_amount: "1000000.00",
    repayment_mode: "MONTHLY",
    interest_rate: "8.00",
    compounding_frequency: "MONTHLY",
    term_months: 12,
    disbursement_date: "2026-02-01",
    maturity_date: "2027-02-01",
    status: "ACTIVE",
    status_display: "Active",
    total_repaid: "250000.00",
    outstanding_balance: "750000.00",
    approval_required: false,
    allowed_actions: ["view", "repay", "offset", "print"],
    created_at: "2026-01-20T08:00:00Z",
    updated_at: "2026-08-01T08:00:00Z",
  },
  {
    id: "loan-defaulted-1",
    loan_number: "OL-LOAN-2025-000014",
    policy_number: "ZIC-OL-2025-000021",
    policy_display: "ZIC-OL-2025-000021 — Fatma Ali",
    policyholder_name: "Fatma Ali",
    partner_display: "P-000021 — Fatma Ali",
    product_display: "OL_TERM_FAMILY — ZIC Term Assurance Family",
    agent_display: "AG-0007 — Zanzibar Life Brokers",
    branch_display: "ZNZ-NORTH — North Region Branch",
    currency: "TZS",
    principal_amount: "800000.00",
    cash_value_snapshot: "1200000.00",
    disbursed_amount: "800000.00",
    repayment_mode: "DEDUCTION_FROM_MATURITY",
    interest_rate: "9.00",
    compounding_frequency: "MONTHLY",
    term_months: 24,
    disbursement_date: "2025-05-12",
    maturity_date: "2027-05-12",
    status: "DEFAULTED",
    status_display: "Defaulted",
    total_repaid: "100000.00",
    outstanding_balance: "700000.00",
    approval_required: false,
    allowed_actions: ["view", "repay", "offset", "print"],
    created_at: "2025-05-01T08:00:00Z",
    updated_at: "2026-08-10T08:00:00Z",
  },
]

let loans = initialLoans.map((loan) => ({ ...loan, allowed_actions: [...loan.allowed_actions] }))

export function resetLoanMockState() {
  loans = initialLoans.map((loan) => ({ ...loan, allowed_actions: [...loan.allowed_actions] }))
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

function findLoan(id: string) {
  return loans.find((loan) => loan.id === id)
}

function detailFor(loan: LoanMockRow) {
  return {
    ...loan,
    disbursement: loan.disbursement_date ? {
      id: `${loan.id}-disbursement`,
      amount: loan.disbursed_amount,
      currency: loan.currency,
      payment_mode: "BANK_TRANSFER",
      bank_account_code: "BANK-ACCOUNT-001",
      disbursement_date: loan.disbursement_date,
      status: "COMPLETED",
      idempotency_key: `${loan.id}:disburse`,
      requisition_number: `REQ-${loan.loan_number.slice(-6)}`,
      reason: "Approved policy loan disbursement",
      created_at: loan.disbursement_date,
    } : null,
    schedules: [
      { id: `${loan.id}-schedule-1`, installment_number: 1, due_date: "2026-03-01", principal_due: "80000.00", interest_due: "6666.67", penalty_due: "0.00", principal_paid: "80000.00", interest_paid: "6666.67", penalty_paid: "0.00", amount_paid: "86666.67", balance: "0.00", status: "PAID" },
      { id: `${loan.id}-schedule-2`, installment_number: 2, due_date: "2026-04-01", principal_due: "80000.00", interest_due: "6666.67", penalty_due: "0.00", principal_paid: "0.00", interest_paid: "0.00", penalty_paid: "0.00", amount_paid: "0.00", balance: "86666.67", status: "DUE" },
    ],
    repayments: loan.total_repaid !== "0.00" ? [{ id: `${loan.id}-repayment-1`, receipt_ref: "RCT-2026-000013", receipt_number: "RCT-2026-000013", receipt_id: `${loan.id}-receipt-1`, amount: loan.total_repaid, currency: loan.currency, exchange_rate: "1.00000000", allocation_breakdown: { principal: loan.total_repaid, interest: "0.00", penalty: "0.00" }, reason: "Monthly payroll deduction", source_channel: "SYSTEM", created_at: "2026-07-01T10:00:00Z" }] : [],
    interest_accruals: [{ id: `${loan.id}-accrual-1`, period_start: "2026-02-01", period_end: "2026-03-01", principal_base: loan.principal_amount, interest_amount: "6666.67", penalty_amount: "0.00", cumulative_interest: "6666.67", source_channel: "SYSTEM", created_at: "2026-03-01T00:00:00Z" }],
    offsets: [],
    audit_timeline: [{ action: "REQUEST", actor_name: "Sultan Admin", source_channel: "API", created_at: loan.created_at }, { action: "DISBURSE", actor_name: "Sultan Admin", source_channel: "API", created_at: loan.disbursement_date }],
    header: { loan_number: loan.loan_number, policy_number: loan.policy_number, policyholder_name: loan.policyholder_name, product: loan.product_display, agent: loan.agent_display, branch: loan.branch_display, principal: loan.principal_amount, outstanding_balance: loan.outstanding_balance, currency: loan.currency, status: loan.status, status_display: loan.status_display },
  }
}

const optionCatalogs: Record<string, { value: string; label: string; meta: Record<string, unknown> }[]> = {
  "repayment-terms": [
    { value: "MONTHLY", label: "Monthly repayment", meta: { unit: "month" } },
    { value: "DEDUCTION_FROM_MATURITY", label: "Deduction from maturity", meta: { unit: "maturity" } },
  ],
  "compounding-frequencies": [
    { value: "MONTHLY", label: "Monthly", meta: { periods_per_year: 12 } },
    { value: "ANNUALLY", label: "Annually", meta: { periods_per_year: 1 } },
  ],
  "offset-rules": [
    { value: "OFFSET_FULL_BALANCE", label: "Offset full outstanding balance", meta: { source_types: ["CLAIM", "SURRENDER", "MATURITY"] } },
    { value: "OFFSET_UP_TO_PAYOUT", label: "Offset up to available payout", meta: { source_types: ["CLAIM", "SURRENDER", "MATURITY"] } },
  ],
}

export const loansHandlers = [
  http.get(`*${LOANS_BASE}/options/:kind/`, ({ params, request }) => {
    const options = optionCatalogs[String(params.kind)]
    if (!options) return error(404, "OPTIONS_ENTITY_NOT_FOUND", "This loan option catalog is not registered.", ["Choose a registered loan option catalog.", "Ask an administrator to configure the loan parameters."])
    const url = new URL(request.url)
    const q = (url.searchParams.get("q") ?? "").toLowerCase()
    return data(page(options.filter((option) => !q || `${option.value} ${option.label}`.toLowerCase().includes(q)), url))
  }),
  http.get(`*${LOANS_BASE}/kpis/`, ({ request }) => {
    const url = new URL(request.url)
    const status = url.searchParams.get("status")
    const filtered = status ? loans.filter((loan) => loan.status === status) : loans
    const byCurrency = Object.fromEntries([...new Set(filtered.map((loan) => loan.currency))].map((currency) => {
      const rows = filtered.filter((loan) => loan.currency === currency)
      return [currency, { total_disbursed_period: rows.reduce((sum, loan) => sum + Number(loan.disbursed_amount), 0).toFixed(2), total_outstanding: rows.reduce((sum, loan) => sum + Number(loan.outstanding_balance), 0).toFixed(2) }]
    }))
    const currencyCodes = Object.keys(byCurrency)
    return data({ total_disbursed_period: currencyCodes.length === 1 ? byCurrency[currencyCodes[0]].total_disbursed_period : byCurrency, total_outstanding: currencyCodes.length === 1 ? byCurrency[currencyCodes[0]].total_outstanding : byCurrency, active_count: filtered.filter((loan) => ["ACTIVE", "PARTIALLY_REPAID"].includes(loan.status)).length, defaulted_count: filtered.filter((loan) => loan.status === "DEFAULTED").length, settled_count: filtered.filter((loan) => ["SETTLED", "CLOSED"].includes(loan.status)).length, currency: currencyCodes.length === 1 ? currencyCodes[0] : "MULTI", amounts_by_currency: byCurrency, timestamp: "2026-08-27T08:00:00Z" })
  }),
  http.get(`*${LOANS_BASE}/:loanId/balance/`, ({ params }) => {
    const loan = findLoan(String(params.loanId))
    return loan ? data({ loan_id: loan.id, currency: loan.currency, principal: loan.principal_amount, total_repaid: loan.total_repaid, outstanding_balance: loan.outstanding_balance, accrued_interest: "6666.67", accrued_penalty: "0.00", as_of: "2026-08-27" }) : error(404, "LOAN_NOT_FOUND", "The loan could not be found.", ["Return to the Loans register and choose an available loan."])
  }),
  http.get(`*${LOANS_BASE}/:loanId/schedule/`, ({ params, request }) => {
    const loan = findLoan(String(params.loanId))
    if (!loan) return error(404, "LOAN_NOT_FOUND", "The loan could not be found.", ["Return to the Loans register and choose an available loan."])
    const detail = detailFor(loan)
    const rows = detail.schedules
    const totalScheduled = rows.reduce((sum, row) => sum + Number(row.principal_due) + Number(row.interest_due) + Number(row.penalty_due), 0).toFixed(2)
    const totalPaid = rows.reduce((sum, row) => sum + Number(row.amount_paid), 0).toFixed(2)
    const remainingBalance = rows.reduce((sum, row) => sum + Number(row.balance), 0).toFixed(2)
    return data({ ...page(rows, new URL(request.url)), aggregates: { total_scheduled: totalScheduled, total_paid: totalPaid, remaining_balance: remainingBalance } })
  }),
  http.get(`*${LOANS_BASE}/:loanId/repayments/`, ({ params, request }) => {
    const loan = findLoan(String(params.loanId))
    if (!loan) return error(404, "LOAN_NOT_FOUND", "The loan could not be found.", ["Return to the Loans register and choose an available loan."])
    return data(page(detailFor(loan).repayments, new URL(request.url)))
  }),
  http.get(`*${LOANS_BASE}/:loanId/accruals/`, ({ params, request }) => {
    const loan = findLoan(String(params.loanId))
    if (!loan) return error(404, "LOAN_NOT_FOUND", "The loan could not be found.", ["Return to the Loans register and choose an available loan."])
    return data(page(detailFor(loan).interest_accruals, new URL(request.url)))
  }),
  http.get(`*${LOANS_BASE}/:loanId/`, ({ params }) => {
    const loan = findLoan(String(params.loanId))
    return loan ? data(detailFor(loan)) : error(404, "LOAN_NOT_FOUND", "The loan could not be found.", ["Return to the Loans register and choose an available loan."])
  }),
  http.get(`*${LOANS_BASE}/`, ({ request }) => {
    const url = new URL(request.url)
    const q = (url.searchParams.get("q") ?? url.searchParams.get("search") ?? "").toLowerCase()
    const status = url.searchParams.get("status")
    const product = (url.searchParams.get("product") ?? "").toLowerCase()
    const filtered = loans.filter((loan) => (!q || `${loan.loan_number} ${loan.policy_number} ${loan.policyholder_name} ${loan.partner_display}`.toLowerCase().includes(q)) && (!status || loan.status === status) && (!product || loan.product_display.toLowerCase().includes(product)))
    return data(page(filtered, url))
  }),
  http.post(`*${LOANS_BASE.replace("/loans", "/policies")}/:policyId/loans/request/`, async ({ params, request }) => {
    const body = await request.json() as { requested_amount?: string | number; term_months?: number; repayment_mode?: string; reason?: string }
    const amount = Number(body.requested_amount ?? 0)
    if (!amount || amount <= 0) return error(400, "LOAN_REQUEST_AMOUNT_REQUIRED", "Enter a requested amount greater than zero.", ["Enter an amount within the available loan limit."], { requested_amount: ["Requested amount must be greater than zero."] })
    const loan: LoanMockRow = { ...initialLoans[0], id: `loan-request-${String(params.policyId)}`, loan_number: "OL-LOAN-2026-000003", policy_number: String(params.policyId), policy_display: `${String(params.policyId)} — Selected policy`, policyholder_name: "Selected policyholder", partner_display: "P-000001 — Amani Salum", principal_amount: amount.toFixed(2), cash_value_snapshot: "2500000.00", disbursed_amount: "0.00", repayment_mode: String(body.repayment_mode ?? "MONTHLY"), term_months: Number(body.term_months ?? 12), disbursement_date: null, maturity_date: null, status: "REQUESTED", status_display: "Requested", total_repaid: "0.00", outstanding_balance: amount.toFixed(2), approval_required: true, allowed_actions: ["view", "approve", "reject", "print"], created_at: "2026-08-27T08:00:00Z", updated_at: "2026-08-27T08:00:00Z" }
    loans = [loan, ...loans.filter((item) => item.id !== loan.id)]
    return data(loan, 201)
  }),
  http.post(`*${LOANS_BASE}/:loanId/disburse/`, ({ params }) => {
    const loan = findLoan(String(params.loanId))
    if (!loan) return error(404, "LOAN_NOT_FOUND", "The loan could not be found.", ["Return to the Loans register and choose an available loan."])
    loan.status = "ACTIVE"; loan.status_display = "Active"; loan.disbursed_amount = loan.principal_amount; loan.allowed_actions = ["view", "repay", "offset", "print"]
    return data({ loan, disbursement: detailFor(loan).disbursement, schedules: detailFor(loan).schedules }, 201)
  }),
  http.post(`*${LOANS_BASE}/:loanId/repay/`, async ({ params, request }) => {
    const loan = findLoan(String(params.loanId))
    const body = await request.json() as { amount?: string | number }
    const amount = Number(body.amount ?? 0)
    if (!loan) return error(404, "LOAN_NOT_FOUND", "The loan could not be found.", ["Return to the Loans register and choose an available loan."])
    if (amount <= 0 || amount > Number(loan.outstanding_balance)) return error(400, "LOAN_REPAYMENT_OVERPAYMENT", "Repayment amount cannot exceed the outstanding balance.", ["Review the current balance.", "Enter a repayment amount at or below the outstanding balance."], { amount: ["Enter an amount no greater than the outstanding balance."] })
    loan.total_repaid = (Number(loan.total_repaid) + amount).toFixed(2); loan.outstanding_balance = (Number(loan.outstanding_balance) - amount).toFixed(2); loan.status = Number(loan.outstanding_balance) === 0 ? "SETTLED" : "PARTIALLY_REPAID"; loan.status_display = loan.status === "SETTLED" ? "Settled" : "Partially repaid"; loan.allowed_actions = loan.status === "SETTLED" ? ["view", "print"] : ["view", "repay", "offset", "print"]
    return data({ loan, repayment: { id: `${loan.id}-repayment-new`, receipt_ref: String(body.amount ?? "manual"), receipt_number: "RCT-2026-000014", amount: String(amount.toFixed(2)), currency: loan.currency, exchange_rate: "1.00000000", allocation_breakdown: { principal: amount.toFixed(2), interest: "0.00", penalty: "0.00" }, reason: "Manual repayment", created_at: "2026-08-27T08:00:00Z" } }, 201)
  }),
  http.post(`*${LOANS_BASE}/:loanId/offset/`, async ({ params, request }) => {
    const loan = findLoan(String(params.loanId))
    const body = await request.json() as { payout_amount?: string | number; source_type?: string; source_id?: string }
    if (!loan) return error(404, "LOAN_NOT_FOUND", "The loan could not be found.", ["Return to the Loans register and choose an available loan."])
    if (loan.status === "SETTLED") return error(400, "LOAN_OFFSET_INVALID", "A settled loan has no outstanding balance to offset.", ["Choose an active or defaulted loan with an outstanding balance."])
    const offsetAmount = Math.min(Number(body.payout_amount ?? loan.outstanding_balance), Number(loan.outstanding_balance))
    loan.outstanding_balance = (Number(loan.outstanding_balance) - offsetAmount).toFixed(2); loan.status = Number(loan.outstanding_balance) === 0 ? "CLOSED" : "DEFAULTED"; loan.status_display = loan.status === "CLOSED" ? "Closed" : "Defaulted"; loan.allowed_actions = ["view", "print"]
    return data({ loan, offset: { id: `${loan.id}-offset-new`, source_type: String(body.source_type ?? "CLAIM"), source_id: String(body.source_id ?? "payout-1"), offset_amount: offsetAmount.toFixed(2), remaining_payout: "0.00", reason: "Automatic payout offset", created_at: "2026-08-27T08:00:00Z" } }, 201)
  }),
  http.post(`*${LOANS_BASE}/:loanId/reverse/`, ({ params }) => {
    const loan = findLoan(String(params.loanId))
    return loan ? data({ loan, meta: { changed: false, idempotent_replay: true } }) : error(404, "LOAN_NOT_FOUND", "The loan could not be found.", ["Return to the Loans register and choose an available loan."])
  }),
  http.post(`*${LOANS_BASE}/:loanId/print-agreement/`, ({ params }) => {
    const loan = findLoan(String(params.loanId))
    return loan ? data({ instance: { id: `${loan.id}-agreement`, document_type: "OL_LOAN_AGREEMENT", template_name: "OL Loan Agreement", template_version: 1, page_count: 3, generated_by_display: "Sultan Admin", generated_at: "2026-08-27T08:00:00Z" }, preview_url: `/api/v1/documents/instances/${loan.id}-agreement/preview/`, signed_download_url: `/api/v1/documents/instances/${loan.id}-agreement/download/?ticket=mock-agreement-${loan.id}` }, 201) : error(404, "LOAN_NOT_FOUND", "The loan could not be found.", ["Return to the Loans register and choose an available loan."])
  }),
  http.post(`*${LOANS_BASE}/:loanId/print-schedule/`, ({ params }) => {
    const loan = findLoan(String(params.loanId))
    return loan ? data({ instance: { id: `${loan.id}-schedule`, document_type: "OL_LOAN_SCHEDULE", template_name: "OL Loan Repayment Schedule", template_version: 1, page_count: 2, generated_by_display: "Sultan Admin", generated_at: "2026-08-27T08:00:00Z" }, preview_url: `/api/v1/documents/instances/${loan.id}-schedule/preview/`, signed_download_url: `/api/v1/documents/instances/${loan.id}-schedule/download/?ticket=mock-schedule-${loan.id}` }, 201) : error(404, "LOAN_NOT_FOUND", "The loan could not be found.", ["Return to the Loans register and choose an available loan."])
  }),
]
