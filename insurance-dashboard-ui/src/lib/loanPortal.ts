import { request, type QueryParams } from "./apiClient"

export const LOAN_PORTAL_API_PREFIX = "/api/v1/ol/loans/portal"

export interface PortalLoanScheduleRow {
  installmentNumber: number
  dueDate: string | null
  principalDue: string
  interestDue: string
  penaltyDue: string
  amountPaid: string
  balance: string
  status: string
}

export interface PortalLoan {
  loanNumber: string
  policyNumber: string
  policyholder: string
  status: string
  currency: string
  principalAmount: string
  disbursedAmount: string
  outstandingBalance: string
  interestRate: string
  termMonths: number
  repaymentMode: string
  disbursementDate: string | null
  maturityDate: string | null
  product: string
  requestAllowed: boolean
  totalRepaid?: string
  compoundingFrequency?: string
  schedule?: PortalLoanScheduleRow[]
}

export interface PortalLoanPage {
  count: number
  results: PortalLoan[]
}

export interface PortalLoanRequestPayload {
  policyNumber: string
  requestedAmount: string | number
  termMonths: number
  repaymentMode: string
  reason: string
  asOf?: string
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value)
}

function pick(row: Record<string, unknown>, ...keys: string[]): unknown {
  for (const key of keys) {
    if (row[key] !== undefined && row[key] !== null) return row[key]
  }
  return undefined
}

function stringValue(row: Record<string, unknown>, ...keys: string[]): string {
  return String(pick(row, ...keys) ?? "")
}

function nullableString(row: Record<string, unknown>, ...keys: string[]): string | null {
  const value = pick(row, ...keys)
  return value === undefined || value === null || value === "" ? null : String(value)
}

function amountValue(row: Record<string, unknown>, ...keys: string[]): string {
  return String(pick(row, ...keys) ?? "0.00")
}

export function normalizePortalLoanSchedule(row: Record<string, unknown>): PortalLoanScheduleRow {
  return {
    installmentNumber: Number(pick(row, "installmentNumber", "installment_number") ?? 0),
    dueDate: nullableString(row, "dueDate", "due_date"),
    principalDue: amountValue(row, "principalDue", "principal_due"),
    interestDue: amountValue(row, "interestDue", "interest_due"),
    penaltyDue: amountValue(row, "penaltyDue", "penalty_due"),
    amountPaid: amountValue(row, "amountPaid", "amount_paid"),
    balance: amountValue(row, "balance"),
    status: stringValue(row, "status", "statusDisplay", "status_display"),
  }
}

export function normalizePortalLoan(payload: unknown): PortalLoan {
  const row = isRecord(payload) ? payload : {}
  const rawSchedule = pick(row, "schedule")
  return {
    loanNumber: stringValue(row, "loanNumber", "loan_number"),
    policyNumber: stringValue(row, "policyNumber", "policy_number"),
    policyholder: stringValue(row, "policyholder", "policyholder_name"),
    status: stringValue(row, "status", "status_display"),
    currency: stringValue(row, "currency") || "TZS",
    principalAmount: amountValue(row, "principalAmount", "principal_amount"),
    disbursedAmount: amountValue(row, "disbursedAmount", "disbursed_amount"),
    outstandingBalance: amountValue(row, "outstandingBalance", "outstanding_balance"),
    interestRate: amountValue(row, "interestRate", "interest_rate"),
    termMonths: Number(pick(row, "termMonths", "term_months") ?? 0),
    repaymentMode: stringValue(row, "repaymentMode", "repayment_mode"),
    disbursementDate: nullableString(row, "disbursementDate", "disbursement_date"),
    maturityDate: nullableString(row, "maturityDate", "maturity_date"),
    product: stringValue(row, "product", "product_display"),
    requestAllowed: Boolean(pick(row, "requestAllowed", "request_allowed") ?? false),
    totalRepaid: amountValue(row, "totalRepaid", "total_repaid"),
    compoundingFrequency: stringValue(row, "compoundingFrequency", "compounding_frequency"),
    schedule: Array.isArray(rawSchedule) ? rawSchedule.filter(isRecord).map(normalizePortalLoanSchedule) : undefined,
  }
}

export function normalizePortalLoanPage(payload: unknown): PortalLoanPage {
  const record = isRecord(payload) ? payload : {}
  const results = Array.isArray(record.results) ? record.results : []
  return {
    count: Number(record.count ?? results.length),
    results: results.map(normalizePortalLoan),
  }
}

export function listPortalLoans(): Promise<PortalLoanPage> {
  const params: QueryParams = { page: 1, page_size: 100 }
  const query = new URLSearchParams(Object.entries(params).map(([key, value]) => [key, String(value)]))
  return request<unknown>(`${LOAN_PORTAL_API_PREFIX}/?${query.toString()}`).then(normalizePortalLoanPage)
}

export function getPortalLoan(loanNumber: string): Promise<PortalLoan> {
  return request<unknown>(`${LOAN_PORTAL_API_PREFIX}/${encodeURIComponent(loanNumber)}/`).then(normalizePortalLoan)
}

export function createPortalLoanRequest(payload: PortalLoanRequestPayload, idempotencyKey: string): Promise<PortalLoan> {
  return request<unknown>(`${LOAN_PORTAL_API_PREFIX}/request/`, {
    method: "POST",
    headers: { "X-Idempotency-Key": idempotencyKey },
    body: JSON.stringify({
      policy_number: payload.policyNumber,
      requested_amount: payload.requestedAmount,
      term_months: payload.termMonths,
      repayment_mode: payload.repaymentMode,
      reason: payload.reason,
      ...(payload.asOf ? { as_of: payload.asOf } : {}),
    }),
  }).then(normalizePortalLoan)
}
