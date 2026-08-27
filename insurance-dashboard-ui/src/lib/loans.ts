/**
 * OL Loans — contract-first API client.
 *
 * This module is intentionally independent from the older generic OL workflow
 * helper. It follows the dedicated backend loan contract and keeps all UUIDs
 * internal while exposing human-readable display fields for the UI.
 */

import { request, type QueryParams } from "./apiClient"

export const LOANS_API_PREFIX = "/api/v1/ol"

export const LOAN_STATUSES = [
  "REQUESTED",
  "APPROVED",
  "DISBURSED",
  "ACTIVE",
  "PARTIALLY_REPAID",
  "SETTLED",
  "DEFAULTED",
  "OFFSET_ON_SURRENDER",
  "OFFSET_ON_MATURITY",
  "OFFSET_ON_CLAIM",
  "CLOSED",
  "REJECTED",
] as const

export type LoanStatus = (typeof LOAN_STATUSES)[number] | string
export type LoanAction = "approve" | "disburse" | "repay" | "offset" | "reverse" | "reject"

export interface Paginated<T> {
  results: T[]
  count: number
  next: boolean | string | null
  previous: boolean | string | null
  page?: number
  pageSize?: number
  aggregates?: Record<string, string | number>
}

export interface LoanScheduleAggregates {
  totalScheduled: string
  totalPaid: string
  remainingBalance: string
}

export interface LoanOption {
  value: string
  label: string
  meta?: Record<string, unknown>
}

export type LoanOptionKind = "repayment-terms" | "compounding-frequencies" | "offset-rules" | string

export interface LoanListFilters {
  page?: number
  pageSize?: number
  search?: string
  ordering?: string
  status?: string
  currency?: string
  product?: string
  productId?: string
  agent?: string
  agentId?: string
  branch?: string
  branchId?: string
  policyId?: string
  partnerId?: string
  dateFrom?: string
  dateTo?: string
  maturityFrom?: string
  maturityTo?: string
  createdFrom?: string
  createdTo?: string
  overdueOnly?: boolean
  balanceOnly?: boolean
}

export interface LoanRecord {
  [key: string]: unknown
  id: string
  loanNumber: string
  policyId?: string
  policyNumber: string
  policyDisplay: string
  policyholderName: string
  partnerDisplay: string
  productDisplay: string
  agentDisplay: string
  branchDisplay: string
  currency: string
  principalAmount: string
  cashValueSnapshot: string
  disbursedAmount: string
  repaymentMode: string
  interestRate: string
  compoundingFrequency: string
  termMonths: number
  disbursementDate: string | null
  maturityDate: string | null
  status: LoanStatus
  statusDisplay: string
  totalRepaid: string
  outstandingBalance: string
  approvalRequired: boolean
  approvedAt: string | null
  rejectedAt: string | null
  rejectionReason: string
  reason: string
  allowedActions: string[]
  createdAt: string
  updatedAt: string
}

export interface LoanScheduleRow {
  id: string
  installmentNumber: number
  dueDate: string
  principalDue: string
  interestDue: string
  penaltyDue: string
  principalPaid: string
  interestPaid: string
  penaltyPaid: string
  amountPaid: string
  balance: string
  totalDue: string
  status: string
  statusDisplay: string
}

export interface LoanRepaymentRow {
  id: string
  receiptRef: string
  receiptNumber: string
  receiptId?: string
  amount: string
  currency: string
  exchangeRate: string
  allocationBreakdown: Record<string, unknown>
  reason: string
  sourceChannel: string
  createdAt: string
}

export interface LoanInterestAccrualRow {
  id: string
  periodStart: string
  periodEnd: string
  principalBase: string
  interestAmount: string
  penaltyAmount: string
  cumulativeInterest: string
  sourceChannel: string
  createdAt: string
}

export interface LoanOffsetRow {
  id: string
  sourceType: string
  sourceId: string
  offsetAmount: string
  remainingPayout: string
  reason: string
  createdAt: string
}

export interface LoanDisbursement {
  id: string
  amount: string
  currency: string
  paymentMode: string
  bankAccountCode: string
  disbursementDate: string | null
  status: string
  idempotencyKey: string
  requisitionNumber: string
  reason: string
  createdAt: string
}

export interface LoanDetail extends LoanRecord {
  header?: Record<string, unknown>
  disbursement?: LoanDisbursement | null
  schedules: LoanScheduleRow[]
  repayments: LoanRepaymentRow[]
  interestAccruals: LoanInterestAccrualRow[]
  offsets: LoanOffsetRow[]
  auditTimeline: Record<string, unknown>[]
}

export interface LoanKpis {
  totalDisbursedPeriod: string | Record<string, string>
  totalOutstanding: string | Record<string, string>
  activeCount: number
  defaultedCount: number
  settledCount: number
  currency: string
  amountsByCurrency: Record<string, { totalDisbursedPeriod: string; totalOutstanding: string }>
  timestamp: string
}

export interface LoanRequestPayload {
  requestedAmount: string | number
  termMonths: number
  repaymentMode: string
  reason: string
  asOf?: string
}

export interface LoanDisbursementPayload {
  paymentMode: string
  bankAccountCode?: string
  asOf?: string
  reason?: string
}

export interface LoanRepaymentPayload {
  amount: string | number
  currency: string
  exchangeRate?: string | number
  receiptRef?: string
  reason?: string
  paymentDate?: string
}

export interface LoanOffsetPayload {
  sourceType: string
  sourceId: string
  payoutAmount: string | number
  reason?: string
}

export interface LoanActionResult {
  loan?: LoanRecord
  disbursement?: LoanDisbursement
  schedules?: LoanScheduleRow[]
  repayment?: LoanRepaymentRow
  offset?: LoanOffsetRow
  meta?: Record<string, unknown>
  [key: string]: unknown
}

export interface LoanPrintResult {
  instance: Record<string, unknown>
  previewBlobBase64OrUrl?: string
  previewUrl?: string
  signedDownloadUrl?: string
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value)
}

function pick<T>(row: Record<string, unknown>, ...keys: string[]): T | undefined {
  for (const key of keys) {
    if (row[key] !== undefined && row[key] !== null) return row[key] as T
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

export function normalizeLoan(row: Record<string, unknown>): LoanRecord {
  return {
    id: stringValue(row, "id", "uuid"),
    loanNumber: stringValue(row, "loanNumber", "loan_number"),
    policyId: nullableString(row, "policyId", "policy_id") ?? undefined,
    policyNumber: stringValue(row, "policyNumber", "policy_number", "policyDisplay", "policy_display"),
    policyDisplay: stringValue(row, "policyDisplay", "policy_display", "policyNumber", "policy_number"),
    policyholderName: stringValue(row, "policyholderName", "policyholder_name", "partnerDisplay", "partner_display"),
    partnerDisplay: stringValue(row, "partnerDisplay", "partner_display", "policyholderName", "policyholder_name"),
    productDisplay: stringValue(row, "productDisplay", "product_display", "productName", "product_name"),
    agentDisplay: stringValue(row, "agentDisplay", "agent_display"),
    branchDisplay: stringValue(row, "branchDisplay", "branch_display"),
    currency: stringValue(row, "currency") || "TZS",
    principalAmount: amountValue(row, "principalAmount", "principal_amount"),
    cashValueSnapshot: amountValue(row, "cashValueSnapshot", "cash_value_snapshot"),
    disbursedAmount: amountValue(row, "disbursedAmount", "disbursed_amount"),
    repaymentMode: stringValue(row, "repaymentMode", "repayment_mode"),
    interestRate: stringValue(row, "interestRate", "interest_rate"),
    compoundingFrequency: stringValue(row, "compoundingFrequency", "compounding_frequency"),
    termMonths: Number(pick(row, "termMonths", "term_months") ?? 0),
    disbursementDate: nullableString(row, "disbursementDate", "disbursement_date"),
    maturityDate: nullableString(row, "maturityDate", "maturity_date"),
    status: stringValue(row, "status").toUpperCase(),
    statusDisplay: stringValue(row, "statusDisplay", "status_display", "status"),
    totalRepaid: amountValue(row, "totalRepaid", "total_repaid"),
    outstandingBalance: amountValue(row, "outstandingBalance", "outstanding_balance"),
    approvalRequired: Boolean(pick(row, "approvalRequired", "approval_required") ?? false),
    approvedAt: nullableString(row, "approvedAt", "approved_at"),
    rejectedAt: nullableString(row, "rejectedAt", "rejected_at"),
    rejectionReason: stringValue(row, "rejectionReason", "rejection_reason"),
    reason: stringValue(row, "reason"),
    allowedActions: Array.isArray(pick(row, "allowedActions", "allowed_actions"))
      ? (pick(row, "allowedActions", "allowed_actions") as unknown[]).map(String)
      : [],
    createdAt: stringValue(row, "createdAt", "created_at"),
    updatedAt: stringValue(row, "updatedAt", "updated_at"),
  }
}

export function normalizeSchedule(row: Record<string, unknown>): LoanScheduleRow {
  return {
    id: stringValue(row, "id"),
    installmentNumber: Number(pick(row, "installmentNumber", "installment_number") ?? 0),
    dueDate: stringValue(row, "dueDate", "due_date"),
    principalDue: amountValue(row, "principalDue", "principal_due"),
    interestDue: amountValue(row, "interestDue", "interest_due"),
    penaltyDue: amountValue(row, "penaltyDue", "penalty_due"),
    principalPaid: amountValue(row, "principalPaid", "principal_paid"),
    interestPaid: amountValue(row, "interestPaid", "interest_paid"),
    penaltyPaid: amountValue(row, "penaltyPaid", "penalty_paid"),
    amountPaid: amountValue(row, "amountPaid", "amount_paid"),
    balance: amountValue(row, "balance"),
    totalDue: amountValue(row, "totalDue", "total_due") !== "0.00" ? amountValue(row, "totalDue", "total_due") : (Number(amountValue(row, "principalDue", "principal_due")) + Number(amountValue(row, "interestDue", "interest_due")) + Number(amountValue(row, "penaltyDue", "penalty_due"))).toFixed(2),
    status: stringValue(row, "status").toUpperCase(),
    statusDisplay: stringValue(row, "statusDisplay", "status_display", "status"),
  }
}

function normalizeRepayment(row: Record<string, unknown>): LoanRepaymentRow {
  return {
    id: stringValue(row, "id"),
    receiptRef: stringValue(row, "receiptRef", "receipt_ref"),
    receiptNumber: stringValue(row, "receiptNumber", "receipt_number"),
    receiptId: nullableString(row, "receiptId", "receipt_id") ?? undefined,
    amount: amountValue(row, "amount"),
    currency: stringValue(row, "currency") || "TZS",
    exchangeRate: stringValue(row, "exchangeRate", "exchange_rate") || "1",
    allocationBreakdown: isRecord(pick(row, "allocationBreakdown", "allocation_breakdown"))
      ? pick(row, "allocationBreakdown", "allocation_breakdown") as Record<string, unknown>
      : {},
    reason: stringValue(row, "reason"),
    sourceChannel: stringValue(row, "sourceChannel", "source_channel"),
    createdAt: stringValue(row, "createdAt", "created_at"),
  }
}

function normalizeAccrual(row: Record<string, unknown>): LoanInterestAccrualRow {
  return {
    id: stringValue(row, "id"),
    periodStart: stringValue(row, "periodStart", "period_start"),
    periodEnd: stringValue(row, "periodEnd", "period_end"),
    principalBase: amountValue(row, "principalBase", "principal_base"),
    interestAmount: amountValue(row, "interestAmount", "interest_amount"),
    penaltyAmount: amountValue(row, "penaltyAmount", "penalty_amount"),
    cumulativeInterest: amountValue(row, "cumulativeInterest", "cumulative_interest"),
    sourceChannel: stringValue(row, "sourceChannel", "source_channel"),
    createdAt: stringValue(row, "createdAt", "created_at"),
  }
}

function normalizeOffset(row: Record<string, unknown>): LoanOffsetRow {
  return {
    id: stringValue(row, "id"),
    sourceType: stringValue(row, "sourceType", "source_type"),
    sourceId: stringValue(row, "sourceId", "source_id"),
    offsetAmount: amountValue(row, "offsetAmount", "offset_amount"),
    remainingPayout: amountValue(row, "remainingPayout", "remaining_payout"),
    reason: stringValue(row, "reason"),
    createdAt: stringValue(row, "createdAt", "created_at"),
  }
}

function normalizeDisbursement(row: Record<string, unknown>): LoanDisbursement {
  return {
    id: stringValue(row, "id"),
    amount: amountValue(row, "amount"),
    currency: stringValue(row, "currency") || "TZS",
    paymentMode: stringValue(row, "paymentMode", "payment_mode"),
    bankAccountCode: stringValue(row, "bankAccountCode", "bank_account_code"),
    disbursementDate: nullableString(row, "disbursementDate", "disbursement_date"),
    status: stringValue(row, "status"),
    idempotencyKey: stringValue(row, "idempotencyKey", "idempotency_key"),
    requisitionNumber: stringValue(row, "requisitionNumber", "requisition_number"),
    reason: stringValue(row, "reason"),
    createdAt: stringValue(row, "createdAt", "created_at"),
  }
}

export function normalizePaginated<T>(payload: unknown, normalizeRow?: (row: Record<string, unknown>) => T): Paginated<T> {
  const record = isRecord(payload) ? payload : {}
  const results = Array.isArray(record.results)
    ? record.results
    : Array.isArray(record.items)
      ? record.items
      : Array.isArray(payload)
        ? payload
        : []
  const convert = normalizeRow ?? ((row: Record<string, unknown>) => row as T)
  return {
    results: results.filter(isRecord).map(convert),
    count: Number(record.count ?? record.total ?? results.length),
    next: (record.next as boolean | string | null | undefined) ?? null,
    previous: (record.previous as boolean | string | null | undefined) ?? null,
    page: Number(record.page ?? 1),
    pageSize: Number(record.pageSize ?? record.page_size ?? results.length),
  }
}

export function normalizeLoanDetail(payload: unknown): LoanDetail {
  const record = isRecord(payload) ? payload : {}
  const loan = normalizeLoan(record)
  const rawDisbursement = pick<unknown>(record, "disbursement")
  const schedules = Array.isArray(record.schedules) ? record.schedules : []
  const repayments = Array.isArray(record.repayments) ? record.repayments : []
  const accruals = Array.isArray(record.interestAccruals)
    ? record.interestAccruals
    : Array.isArray(record.interest_accruals)
      ? record.interest_accruals
      : []
  const offsets = Array.isArray(record.offsets) ? record.offsets : []
  const auditTimeline = Array.isArray(record.auditTimeline)
    ? record.auditTimeline
    : Array.isArray(record.audit_timeline)
      ? record.audit_timeline
      : []
  return {
    ...loan,
    header: isRecord(record.header) ? record.header : undefined,
    disbursement: isRecord(rawDisbursement) ? normalizeDisbursement(rawDisbursement) : null,
    schedules: schedules.filter(isRecord).map(normalizeSchedule),
    repayments: repayments.filter(isRecord).map(normalizeRepayment),
    interestAccruals: accruals.filter(isRecord).map(normalizeAccrual),
    offsets: offsets.filter(isRecord).map(normalizeOffset),
    auditTimeline: auditTimeline.filter(isRecord),
  }
}

export function normalizeKpis(payload: unknown): LoanKpis {
  const record = isRecord(payload) ? payload : {}
  const rawAmounts = isRecord(record.amountsByCurrency ?? record.amounts_by_currency)
    ? record.amountsByCurrency ?? record.amounts_by_currency
    : {}
  const amountsByCurrency = Object.fromEntries(
    Object.entries(rawAmounts as Record<string, unknown>).map(([currency, value]) => {
      const row = isRecord(value) ? value : {}
      return [currency, {
        totalDisbursedPeriod: amountValue(row, "totalDisbursedPeriod", "total_disbursed_period"),
        totalOutstanding: amountValue(row, "totalOutstanding", "total_outstanding"),
      }]
    }),
  )
  return {
    totalDisbursedPeriod: (record.totalDisbursedPeriod ?? record.total_disbursed_period ?? "0.00") as string | Record<string, string>,
    totalOutstanding: (record.totalOutstanding ?? record.total_outstanding ?? "0.00") as string | Record<string, string>,
    activeCount: Number(record.activeCount ?? record.active_count ?? 0),
    defaultedCount: Number(record.defaultedCount ?? record.defaulted_count ?? 0),
    settledCount: Number(record.settledCount ?? record.settled_count ?? 0),
    currency: String(record.currency ?? "TZS"),
    amountsByCurrency,
    timestamp: String(record.timestamp ?? ""),
  }
}

export function buildLoanQuery(filters: LoanListFilters = {}): string {
  const params: QueryParams = {
    page: filters.page,
    page_size: filters.pageSize,
    q: filters.search,
    ordering: filters.ordering,
    status: filters.status,
    currency: filters.currency,
    product: filters.product ?? filters.productId,
    agent: filters.agent ?? filters.agentId,
    branch: filters.branch ?? filters.branchId,
    policy_id: filters.policyId,
    partner_id: filters.partnerId,
    date_from: filters.dateFrom,
    date_to: filters.dateTo,
    maturity_from: filters.maturityFrom,
    maturity_to: filters.maturityTo,
    created_from: filters.createdFrom,
    created_to: filters.createdTo,
    overdue_only: filters.overdueOnly,
    balance_only: filters.balanceOnly,
  }
  const search = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") search.set(key, String(value))
  })
  const query = search.toString()
  return query ? `?${query}` : ""
}

export function buildLoanOptionQuery(params: { q?: string; page?: number; pageSize?: number; asOf?: string; productId?: string; planId?: string } = {}): string {
  const search = new URLSearchParams()
  if (params.q) search.set("q", params.q)
  if (params.page) search.set("page", String(params.page))
  if (params.pageSize) search.set("page_size", String(params.pageSize))
  if (params.asOf) search.set("as_of", params.asOf)
  if (params.productId) search.set("product_id", params.productId)
  if (params.planId) search.set("plan_id", params.planId)
  const query = search.toString()
  return query ? `?${query}` : ""
}

export function listLoans(filters: LoanListFilters = {}): Promise<Paginated<LoanRecord>> {
  return request<unknown>(`${LOANS_API_PREFIX}/loans/${buildLoanQuery(filters)}`).then((payload) => normalizePaginated(payload, normalizeLoan))
}

export function getLoanKPIs(filters: LoanListFilters = {}): Promise<LoanKpis> {
  return request<unknown>(`${LOANS_API_PREFIX}/loans/kpis/${buildLoanQuery(filters)}`).then(normalizeKpis)
}

export function getLoanOptions(kind: LoanOptionKind, params: { q?: string; page?: number; pageSize?: number; asOf?: string; productId?: string; planId?: string } = {}): Promise<Paginated<LoanOption>> {
  return request<unknown>(`${LOANS_API_PREFIX}/loans/options/${encodeURIComponent(kind)}/${buildLoanOptionQuery(params)}`).then((payload) => normalizePaginated(payload))
}

export function getLoan(id: string): Promise<LoanDetail> {
  return request<unknown>(`${LOANS_API_PREFIX}/loans/${encodeURIComponent(id)}/`).then(normalizeLoanDetail)
}

export function getLoanBalance(id: string): Promise<Record<string, unknown>> {
  return request<Record<string, unknown>>(`${LOANS_API_PREFIX}/loans/${encodeURIComponent(id)}/balance/`)
}

export function getLoanRepayments(id: string, params: { page?: number; pageSize?: number } = {}): Promise<Paginated<LoanRepaymentRow>> {
  const search = new URLSearchParams()
  if (params.page) search.set("page", String(params.page))
  if (params.pageSize) search.set("page_size", String(params.pageSize))
  const query = search.toString()
  return request<unknown>(`${LOANS_API_PREFIX}/loans/${encodeURIComponent(id)}/repayments/${query ? `?${query}` : ""}`).then((payload) => normalizePaginated(payload, normalizeRepayment))
}

export function getLoanAccruals(id: string, params: { page?: number; pageSize?: number } = {}): Promise<Paginated<LoanInterestAccrualRow>> {
  const search = new URLSearchParams()
  if (params.page) search.set("page", String(params.page))
  if (params.pageSize) search.set("page_size", String(params.pageSize))
  const query = search.toString()
  return request<unknown>(`${LOANS_API_PREFIX}/loans/${encodeURIComponent(id)}/accruals/${query ? `?${query}` : ""}`).then((payload) => normalizePaginated(payload, normalizeAccrual))
}

export function getLoanSchedule(id: string, params: { page?: number; pageSize?: number } = {}): Promise<Paginated<LoanScheduleRow> & { aggregates?: LoanScheduleAggregates }> {
  const search = new URLSearchParams()
  if (params.page) search.set("page", String(params.page))
  if (params.pageSize) search.set("page_size", String(params.pageSize))
  const query = search.toString()
  return request<unknown>(`${LOANS_API_PREFIX}/loans/${encodeURIComponent(id)}/schedule/${query ? `?${query}` : ""}`).then((payload) => {
    const page = normalizePaginated(payload, normalizeSchedule)
    const record = isRecord(payload) ? payload : {}
    const rawAggregates = isRecord(record.aggregates) ? record.aggregates : {}
    return {
      ...page,
      aggregates: {
        totalScheduled: amountValue(rawAggregates, "totalScheduled", "total_scheduled"),
        totalPaid: amountValue(rawAggregates, "totalPaid", "total_paid"),
        remainingBalance: amountValue(rawAggregates, "remainingBalance", "remaining_balance"),
      },
    }
  })
}

function withIdempotencyKey(headers: HeadersInit | undefined, idempotencyKey?: string): HeadersInit | undefined {
  if (!idempotencyKey) return headers
  const next = new Headers(headers)
  next.set("X-Idempotency-Key", idempotencyKey)
  return next
}

export function createLoanRequest(policyId: string, payload: LoanRequestPayload, idempotencyKey?: string): Promise<LoanActionResult> {
  return request<unknown>(`${LOANS_API_PREFIX}/policies/${encodeURIComponent(policyId)}/loans/request/`, {
    method: "POST",
    headers: withIdempotencyKey(undefined, idempotencyKey),
    body: JSON.stringify(payload),
  }).then(normalizeActionResult)
}

export function disburseLoan(id: string, payload: LoanDisbursementPayload, idempotencyKey?: string): Promise<LoanActionResult> {
  return request<unknown>(`${LOANS_API_PREFIX}/loans/${encodeURIComponent(id)}/disburse/`, {
    method: "POST",
    headers: withIdempotencyKey(undefined, idempotencyKey),
    body: JSON.stringify(payload),
  }).then(normalizeActionResult)
}

export function repayLoan(id: string, payload: LoanRepaymentPayload, idempotencyKey?: string): Promise<LoanActionResult> {
  return request<unknown>(`${LOANS_API_PREFIX}/loans/${encodeURIComponent(id)}/repay/`, {
    method: "POST",
    headers: withIdempotencyKey(undefined, idempotencyKey),
    body: JSON.stringify(payload),
  }).then(normalizeActionResult)
}

export function offsetLoan(id: string, payload: LoanOffsetPayload, idempotencyKey?: string): Promise<LoanActionResult> {
  return request<unknown>(`${LOANS_API_PREFIX}/loans/${encodeURIComponent(id)}/offset/`, {
    method: "POST",
    headers: withIdempotencyKey(undefined, idempotencyKey),
    body: JSON.stringify(payload),
  }).then(normalizeActionResult)
}

export function reverseLoan(id: string, payload: { reason: string }, idempotencyKey?: string): Promise<LoanActionResult> {
  return request<unknown>(`${LOANS_API_PREFIX}/loans/${encodeURIComponent(id)}/reverse/`, {
    method: "POST",
    headers: withIdempotencyKey(undefined, idempotencyKey),
    body: JSON.stringify(payload),
  }).then(normalizeActionResult)
}

export function loanAction(id: string, action: LoanAction | string, payload: Record<string, unknown> = {}, idempotencyKey?: string): Promise<LoanActionResult> {
  switch (action) {
    case "disburse": return disburseLoan(id, payload as unknown as LoanDisbursementPayload, idempotencyKey)
    case "repay": return repayLoan(id, payload as unknown as LoanRepaymentPayload, idempotencyKey)
    case "offset": return offsetLoan(id, payload as unknown as LoanOffsetPayload, idempotencyKey)
    case "reverse": return reverseLoan(id, payload as { reason: string }, idempotencyKey)
    default:
      return request<unknown>(`${LOANS_API_PREFIX}/loans/${encodeURIComponent(id)}/${encodeURIComponent(action)}/`, {
        method: "POST",
        headers: withIdempotencyKey(undefined, idempotencyKey),
        body: JSON.stringify(payload),
      }).then(normalizeActionResult)
  }
}

export function normalizeActionResult(payload: unknown): LoanActionResult {
  const record = isRecord(payload) ? payload : {}
  const rawLoan = isRecord(record.loan) ? record.loan : record.id || record.loanNumber || record.loan_number ? record : undefined
  const schedules = Array.isArray(record.schedules) ? record.schedules : []
  return {
    ...record,
    loan: rawLoan ? normalizeLoan(rawLoan) : undefined,
    disbursement: isRecord(record.disbursement) ? normalizeDisbursement(record.disbursement) : undefined,
    schedules: schedules.filter(isRecord).map(normalizeSchedule),
    repayment: isRecord(record.repayment) ? normalizeRepayment(record.repayment) : undefined,
    offset: isRecord(record.offset) ? normalizeOffset(record.offset) : undefined,
  }
}

export function printLoanDocument(id: string, documentType: "agreement" | "schedule"): Promise<LoanPrintResult> {
  return request<unknown>(`${LOANS_API_PREFIX}/loans/${encodeURIComponent(id)}/print-${documentType}/`, { method: "POST" }).then((payload) => {
    const record = isRecord(payload) ? payload : {}
    return {
      instance: isRecord(record.instance) ? record.instance : {},
      previewBlobBase64OrUrl: String(record.previewBlobBase64OrUrl ?? record.preview_blob_base64_or_url ?? record.previewUrl ?? record.preview_url ?? "") || undefined,
      previewUrl: String(record.previewUrl ?? record.preview_url ?? "") || undefined,
      signedDownloadUrl: String(record.signedDownloadUrl ?? record.signed_download_url ?? "") || undefined,
    }
  })
}
