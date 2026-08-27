/**
 * OL Withdrawals — contract-first API client.
 *
 * Resource IDs stay internal for API navigation. Components should render the
 * display fields returned by the backend instead of UUIDs.
 */

import { request, type QueryParams } from "./apiClient"

export const WITHDRAWALS_API_PREFIX = "/api/v1/ol/withdrawals"
export const POLICY_WITHDRAWALS_API_PREFIX = "/api/v1/ol/policies"

export const WITHDRAWAL_STATUSES = [
  "REQUESTED",
  "APPROVED",
  "PROCESSING",
  "PAID",
  "REVERSED",
  "DECLINED",
  "CANCELLED",
] as const

export type WithdrawalStatus = (typeof WITHDRAWAL_STATUSES)[number] | string
export type WithdrawalAction = "approve" | "reject" | "process_payout" | "cancel" | "reverse" | "offset"
export type WithdrawalOptionKind = "policies" | "products" | "branches" | "agents" | "payment-modes" | string

export interface Paginated<T> {
  results: T[]
  count: number
  next: boolean | string | null
  previous: boolean | string | null
  page?: number
  pageSize?: number
}

export interface WithdrawalOption {
  value: string
  label: string
  meta?: Record<string, unknown>
}

export interface WithdrawalListFilters {
  page?: number
  pageSize?: number
  search?: string
  ordering?: string
  status?: string
  product?: string
  productId?: string
  branch?: string
  branchId?: string
  agent?: string
  agentId?: string
  dateFrom?: string
  dateTo?: string
  pendingApprovalOnly?: boolean
}

export interface WithdrawalRecord {
  [key: string]: unknown
  id: string
  withdrawalNumber: string
  policyId?: string
  policyNumber: string
  policyDisplay: string
  policyholderName: string
  policyholderDisplay: string
  productDisplay: string
  agentDisplay: string
  branchDisplay: string
  currency: string
  grossAmount: string
  feeAmount: string
  netPayout: string
  cashValueBefore: string
  loanBalanceBefore: string
  cashValueAfter?: string
  status: WithdrawalStatus
  statusDisplay: string
  reason: string
  requestedAt: string | null
  approvedAt: string | null
  processedAt: string | null
  paidAt: string | null
  allowedActions: string[]
  createdAt: string | null
  updatedAt: string | null
}

export interface WithdrawalBreakdown {
  withdrawalId: string
  currency: string
  cashValueBefore: string
  grossWithdrawal: string
  withdrawalFee: string
  feeRate?: string | null
  feeBasis?: string | null
  netPayout: string
  cashValueAfter: string
  sumAssuredBefore?: string | null
  sumAssuredAfter?: string | null
  adjustmentRatio?: string | null
  auditTrail: Record<string, unknown>[]
}

export interface WithdrawalPayment {
  id: string
  paymentMode: string
  paymentModeDisplay: string
  receiptReference: string
  amount: string
  currency: string
  paymentDate: string | null
  status: string
  createdAt: string | null
}

export interface WithdrawalAuditEntry {
  id: string
  action: string
  actorDisplay: string
  sourceChannel: string
  reason: string
  createdAt: string | null
}

export interface WithdrawalDetail extends WithdrawalRecord {
  breakdown?: WithdrawalBreakdown | null
  payments: WithdrawalPayment[]
  auditTimeline: WithdrawalAuditEntry[]
  documents: Record<string, unknown>[]
  policyContext?: Record<string, unknown>
}

export interface WithdrawalKpis {
  totalWithdrawnCurrentMonth: string
  totalWithdrawnCurrentMonthCount: number
  pendingApprovalsCount: number
  pendingApprovalsAmount: string
  processingPayoutsCount: number
  averageFeeAmount: string
  currency: string
  amountsByCurrency?: Record<string, Record<string, string | number>>
  timestamp: string
}

export interface WithdrawalRequestPayload {
  amount: string | number
  reason: string
  asOf?: string
}

export interface WithdrawalActionResult {
  withdrawal?: WithdrawalRecord
  breakdown?: WithdrawalBreakdown
  payment?: WithdrawalPayment
  meta?: Record<string, unknown>
  [key: string]: unknown
}

export interface WithdrawalPrintResult {
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

function arrayValue(row: Record<string, unknown>, ...keys: string[]): unknown[] {
  const value = pick<unknown>(row, ...keys)
  return Array.isArray(value) ? value : []
}

export function normalizeWithdrawal(row: Record<string, unknown>): WithdrawalRecord {
  const policyDisplay = stringValue(row, "policyDisplay", "policy_display", "policyNumber", "policy_number")
  const policyholderDisplay = stringValue(row, "policyholderDisplay", "policyholder_display", "policyholderName", "policyholder_name", "partnerDisplay", "partner_display")
  return {
    ...row,
    id: stringValue(row, "id", "uuid"),
    withdrawalNumber: stringValue(row, "withdrawalNumber", "withdrawal_number", "requestNumber", "request_number"),
    policyId: nullableString(row, "policyId", "policy_id") ?? undefined,
    policyNumber: stringValue(row, "policyNumber", "policy_number", "policyDisplay", "policy_display"),
    policyDisplay,
    policyholderName: stringValue(row, "policyholderName", "policyholder_name", "partnerDisplay", "partner_display"),
    policyholderDisplay,
    productDisplay: stringValue(row, "productDisplay", "product_display", "productName", "product_name"),
    agentDisplay: stringValue(row, "agentDisplay", "agent_display"),
    branchDisplay: stringValue(row, "branchDisplay", "branch_display"),
    currency: stringValue(row, "currency") || "TZS",
    grossAmount: amountValue(row, "grossAmount", "gross_amount", "amount"),
    feeAmount: amountValue(row, "feeAmount", "fee_amount", "withdrawalFee", "withdrawal_fee"),
    netPayout: amountValue(row, "netPayout", "net_payout", "netAmount", "net_amount"),
    cashValueBefore: amountValue(row, "cashValueBefore", "cash_value_before"),
    loanBalanceBefore: amountValue(row, "loanBalanceBefore", "loan_balance_before"),
    cashValueAfter: nullableString(row, "cashValueAfter", "cash_value_after") ?? undefined,
    status: stringValue(row, "status").toUpperCase(),
    statusDisplay: stringValue(row, "statusDisplay", "status_display", "status"),
    reason: stringValue(row, "reason"),
    requestedAt: nullableString(row, "requestedAt", "requested_at", "requestDate", "request_date"),
    approvedAt: nullableString(row, "approvedAt", "approved_at"),
    processedAt: nullableString(row, "processedAt", "processed_at", "processedDate", "processed_date"),
    paidAt: nullableString(row, "paidAt", "paid_at", "paidDate", "paid_date"),
    allowedActions: arrayValue(row, "allowedActions", "allowed_actions").map(String),
    createdAt: nullableString(row, "createdAt", "created_at"),
    updatedAt: nullableString(row, "updatedAt", "updated_at"),
  }
}

function normalizeBreakdown(row: Record<string, unknown>): WithdrawalBreakdown {
  return {
    withdrawalId: stringValue(row, "withdrawalId", "withdrawal_id"),
    currency: stringValue(row, "currency") || "TZS",
    cashValueBefore: amountValue(row, "cashValueBefore", "cash_value_before"),
    grossWithdrawal: amountValue(row, "grossWithdrawal", "gross_withdrawal", "amount"),
    withdrawalFee: amountValue(row, "withdrawalFee", "withdrawal_fee", "feeAmount", "fee_amount"),
    feeRate: nullableString(row, "feeRate", "fee_rate"),
    feeBasis: nullableString(row, "feeBasis", "fee_basis"),
    netPayout: amountValue(row, "netPayout", "net_payout", "netAmount", "net_amount"),
    cashValueAfter: amountValue(row, "cashValueAfter", "cash_value_after"),
    sumAssuredBefore: nullableString(row, "sumAssuredBefore", "sum_assured_before"),
    sumAssuredAfter: nullableString(row, "sumAssuredAfter", "sum_assured_after"),
    adjustmentRatio: nullableString(row, "adjustmentRatio", "adjustment_ratio"),
    auditTrail: arrayValue(row, "auditTrail", "audit_trail").filter(isRecord),
  }
}

function normalizePayment(row: Record<string, unknown>): WithdrawalPayment {
  return {
    id: stringValue(row, "id"),
    paymentMode: stringValue(row, "paymentMode", "payment_mode"),
    paymentModeDisplay: stringValue(row, "paymentModeDisplay", "payment_mode_display", "paymentMode", "payment_mode"),
    receiptReference: stringValue(row, "receiptReference", "receipt_reference", "receiptRef", "receipt_ref"),
    amount: amountValue(row, "amount"),
    currency: stringValue(row, "currency") || "TZS",
    paymentDate: nullableString(row, "paymentDate", "payment_date"),
    status: stringValue(row, "status"),
    createdAt: nullableString(row, "createdAt", "created_at"),
  }
}

function normalizeAuditEntry(row: Record<string, unknown>): WithdrawalAuditEntry {
  return {
    id: stringValue(row, "id", "event_id"),
    action: stringValue(row, "action", "event_type"),
    actorDisplay: stringValue(row, "actorDisplay", "actor_display", "actorName", "actor_name", "actor"),
    sourceChannel: stringValue(row, "sourceChannel", "source_channel"),
    reason: stringValue(row, "reason"),
    createdAt: nullableString(row, "createdAt", "created_at"),
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

export function normalizeWithdrawalDetail(payload: unknown): WithdrawalDetail {
  const record = isRecord(payload) ? payload : {}
  const withdrawal = normalizeWithdrawal(record)
  const rawBreakdown = pick<unknown>(record, "breakdown")
  const payments = arrayValue(record, "payments").filter(isRecord).map(normalizePayment)
  const auditTimeline = arrayValue(record, "auditTimeline", "audit_timeline").filter(isRecord).map(normalizeAuditEntry)
  return {
    ...withdrawal,
    breakdown: isRecord(rawBreakdown) ? normalizeBreakdown(rawBreakdown) : null,
    payments,
    auditTimeline,
    documents: arrayValue(record, "documents").filter(isRecord),
    policyContext: isRecord(record.policyContext ?? record.policy_context) ? (record.policyContext ?? record.policy_context) as Record<string, unknown> : undefined,
  }
}

export function normalizeWithdrawalKpis(payload: unknown): WithdrawalKpis {
  const record = isRecord(payload) ? payload : {}
  const rawAmounts = isRecord(record.amountsByCurrency ?? record.amounts_by_currency) ? record.amountsByCurrency ?? record.amounts_by_currency : undefined
  return {
    totalWithdrawnCurrentMonth: amountValue(record, "totalWithdrawnCurrentMonth", "total_withdrawn_current_month", "total_withdrawn"),
    totalWithdrawnCurrentMonthCount: Number(pick(record, "totalWithdrawnCurrentMonthCount", "total_withdrawn_current_month_count", "total_withdrawn_count") ?? 0),
    pendingApprovalsCount: Number(pick(record, "pendingApprovalsCount", "pending_approvals_count") ?? 0),
    pendingApprovalsAmount: amountValue(record, "pendingApprovalsAmount", "pending_approvals_amount"),
    processingPayoutsCount: Number(pick(record, "processingPayoutsCount", "processing_payouts_count") ?? 0),
    averageFeeAmount: amountValue(record, "averageFeeAmount", "average_fee_amount", "average_fee"),
    currency: stringValue(record, "currency") || "TZS",
    amountsByCurrency: rawAmounts as Record<string, Record<string, string | number>> | undefined,
    timestamp: stringValue(record, "timestamp"),
  }
}

export function buildWithdrawalQuery(filters: WithdrawalListFilters = {}): string {
  const params: QueryParams = {
    page: filters.page,
    page_size: filters.pageSize,
    q: filters.search,
    ordering: filters.ordering,
    status: filters.status,
    product: filters.product ?? filters.productId,
    branch: filters.branch ?? filters.branchId,
    agent: filters.agent ?? filters.agentId,
    date_from: filters.dateFrom,
    date_to: filters.dateTo,
    pending_approval_only: filters.pendingApprovalOnly,
  }
  const search = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") search.set(key, String(value))
  })
  const query = search.toString()
  return query ? `?${query}` : ""
}

export function buildWithdrawalOptionQuery(params: { q?: string; page?: number; pageSize?: number; policyId?: string } = {}): string {
  const search = new URLSearchParams()
  if (params.q) search.set("q", params.q)
  if (params.page) search.set("page", String(params.page))
  if (params.pageSize) search.set("page_size", String(params.pageSize))
  if (params.policyId) search.set("policy_id", params.policyId)
  const query = search.toString()
  return query ? `?${query}` : ""
}

function withIdempotencyKey(idempotencyKey?: string): HeadersInit | undefined {
  return idempotencyKey ? { "X-Idempotency-Key": idempotencyKey } : undefined
}

function actionPath(action: WithdrawalAction): string {
  return action === "process_payout" ? "process-payout" : action
}

export function listWithdrawals(filters: WithdrawalListFilters = {}): Promise<Paginated<WithdrawalRecord>> {
  return request<unknown>(`${WITHDRAWALS_API_PREFIX}/${buildWithdrawalQuery(filters)}`).then((payload) => normalizePaginated(payload, normalizeWithdrawal))
}

export function getWithdrawalKpis(filters: WithdrawalListFilters = {}): Promise<WithdrawalKpis> {
  return request<unknown>(`${WITHDRAWALS_API_PREFIX}/kpis/${buildWithdrawalQuery(filters)}`).then(normalizeWithdrawalKpis)
}

export function getWithdrawalOptions(kind: WithdrawalOptionKind, params: { q?: string; page?: number; pageSize?: number; policyId?: string } = {}): Promise<Paginated<WithdrawalOption>> {
  return request<unknown>(`${WITHDRAWALS_API_PREFIX}/options/${encodeURIComponent(kind)}/${buildWithdrawalOptionQuery(params)}`).then((payload) => normalizePaginated(payload))
}

export function getWithdrawal(id: string): Promise<WithdrawalDetail> {
  return request<unknown>(`${WITHDRAWALS_API_PREFIX}/${encodeURIComponent(id)}/`).then(normalizeWithdrawalDetail)
}

export function getWithdrawalBreakdown(id: string): Promise<WithdrawalBreakdown> {
  return request<unknown>(`${WITHDRAWALS_API_PREFIX}/${encodeURIComponent(id)}/breakdown/`).then((payload) => normalizeBreakdown(isRecord(payload) ? payload : {}))
}

export function getWithdrawalPayments(id: string, params: { page?: number; pageSize?: number } = {}): Promise<Paginated<WithdrawalPayment>> {
  const search = new URLSearchParams()
  if (params.page) search.set("page", String(params.page))
  if (params.pageSize) search.set("page_size", String(params.pageSize))
  const query = search.toString()
  return request<unknown>(`${WITHDRAWALS_API_PREFIX}/${encodeURIComponent(id)}/payments/${query ? `?${query}` : ""}`).then((payload) => normalizePaginated(payload, normalizePayment))
}

export function getWithdrawalAudit(id: string, params: { page?: number; pageSize?: number } = {}): Promise<Paginated<WithdrawalAuditEntry>> {
  const search = new URLSearchParams()
  if (params.page) search.set("page", String(params.page))
  if (params.pageSize) search.set("page_size", String(params.pageSize))
  const query = search.toString()
  return request<unknown>(`${WITHDRAWALS_API_PREFIX}/${encodeURIComponent(id)}/audit/${query ? `?${query}` : ""}`).then((payload) => normalizePaginated(payload, normalizeAuditEntry))
}

export function requestWithdrawal(policyId: string, payload: WithdrawalRequestPayload, idempotencyKey?: string): Promise<WithdrawalActionResult> {
  return request<unknown>(`${POLICY_WITHDRAWALS_API_PREFIX}/${encodeURIComponent(policyId)}/withdrawals/`, {
    method: "POST",
    headers: withIdempotencyKey(idempotencyKey),
    body: JSON.stringify({
      amount: payload.amount,
      reason: payload.reason,
      ...(payload.asOf ? { as_of: payload.asOf } : {}),
    }),
  }).then((result) => normalizeActionResult(result))
}

export function withdrawalAction(id: string, action: WithdrawalAction, payload: Record<string, unknown> = {}, idempotencyKey?: string): Promise<WithdrawalActionResult> {
  return request<unknown>(`${WITHDRAWALS_API_PREFIX}/${encodeURIComponent(id)}/${actionPath(action)}/`, {
    method: "POST",
    headers: withIdempotencyKey(idempotencyKey),
    body: JSON.stringify(payload),
  }).then((result) => normalizeActionResult(result))
}

export function printWithdrawalStatement(id: string, payload: Record<string, unknown> = {}): Promise<WithdrawalPrintResult> {
  return request<WithdrawalPrintResult>(`${WITHDRAWALS_API_PREFIX}/${encodeURIComponent(id)}/print-statement/`, {
    method: "POST",
    body: JSON.stringify(payload),
  })
}

function normalizeActionResult(payload: unknown): WithdrawalActionResult {
  const record = isRecord(payload) ? payload : {}
  const rawWithdrawal = pick<unknown>(record, "withdrawal")
  return {
    ...record,
    withdrawal: isRecord(rawWithdrawal) ? normalizeWithdrawal(rawWithdrawal) : normalizeWithdrawal(record),
    breakdown: isRecord(record.breakdown) ? normalizeBreakdown(record.breakdown) : undefined,
    payment: isRecord(record.payment) ? normalizePayment(record.payment) : undefined,
  }
}
