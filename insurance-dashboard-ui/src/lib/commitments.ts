/**
 * Commitments — API client and contracts.
 *
 * Contract-first client for the OL Commitments module. Endpoints follow the
 * module API prefix `/api/v1/ol-commitments/` and the contracts documented in
 * `docs/OL_COMMITMENTS_DESIGN.md` (list + KPIs) and the backend UI-series
 * prompts (generation, import, process-overdue, lifecycle actions).
 *
 * The backend renders JSON through `djangorestframework-camel-case`, so record
 * fields arrive camelCase; helpers below tolerate snake_case too so the module
 * keeps working until the backend surface lands in parallel.
 */

import { request, type ApiClientError } from "./apiClient"

export const COMMITMENTS_API_PREFIX = "/api/v1/ol-commitments"

export type CommitmentSourceType = "PROPOSAL" | "POLICY" | "MANUAL"
export type StatusTone = "success" | "info" | "warning" | "danger" | "neutral"

export interface Paginated<T> {
  results: T[]
  count: number
  next: string | null
  previous: string | null
}

export interface CommitmentStatusOption {
  code: string
  name: string
  tone?: StatusTone
}

export interface CommitmentOptions {
  paymentModes: string[]
  currencies: string[]
  statuses: CommitmentStatusOption[]
}

export interface CommitmentListFilters {
  page?: number
  pageSize?: number
  search?: string
  ordering?: string
  status?: string
  sourceType?: CommitmentSourceType
  currency?: string
  product?: string
  dueDateFrom?: string
  dueDateTo?: string
  overdueOnly?: boolean
  balanceOnly?: boolean
}

export interface CommitmentAllocation {
  id: string
  receiptReference: string
  amount: string
  paymentMode: string
  currency: string
  exchangeRate: string
  reason?: string
  reversalOf?: string | null
  allocatedAt?: string
}

export interface CommitmentNotificationLog {
  id: string
  eventType: string
  dispatchOn: string
  channel: string
  recipientType: string
  recipientIdentifier?: string
  templateCode?: string
  status: string
}

export type CommitmentRecord = {
  id: string
  commitmentNumber: string
  sourceType: CommitmentSourceType
  sourceReference?: string
  partnerId?: string | null
  partnerName: string
  productId?: string | null
  productName?: string | null
  planId?: string | null
  planName?: string | null
  currency: string
  premiumFrequency?: string
  installmentNumber: number
  installmentCount: number
  dueDate: string
  premiumAmount: string
  amountPaid: string
  amountWaived?: string
  balance: string
  status: string
  graceDate?: string | null
  warningDate?: string | null
  preLapseDate?: string | null
  lapseDate?: string | null
  approvalRequired?: boolean
  sourceChannel?: string
  reasonCode?: string
  reasonText?: string
  allowedActions?: string[]
}

export type CommitmentDetail = CommitmentRecord & {
  allocations: CommitmentAllocation[]
  notificationLogs: CommitmentNotificationLog[]
}

export interface CommitmentKPIs {
  totalDue: string
  totalOutstanding: string
  overdueCount: number
  collectedInPeriod: string
}

export interface GenerationPayload {
  sourceType: CommitmentSourceType
  sourceId?: string
  method?: "auto" | "manual"
  manual?: Record<string, unknown>
}

export const COMMITMENT_ACTIONS = [
  "record_payment",
  "reverse",
  "suspend",
  "reactivate",
  "waive",
  "cancel",
  "reschedule",
] as const
export type CommitmentAction = (typeof COMMITMENT_ACTIONS)[number]

function pick<T>(row: Record<string, unknown>, ...keys: string[]): T | undefined {
  for (const key of keys) {
    if (row[key] !== undefined && row[key] !== null) return row[key] as T
  }
  return undefined
}

export function normalizeCommitment(row: Record<string, unknown>): CommitmentRecord {
  const amount = (key: string) => String(pick(row, key, key.replace(/[A-Z]/g, (m) => `_${m.toLowerCase()}`)) ?? "")
  return {
    id: String(row.id ?? ""),
    commitmentNumber: String(pick(row, "commitmentNumber", "commitment_number") ?? ""),
    sourceType: String(pick(row, "sourceType", "source_type") ?? "MANUAL") as CommitmentSourceType,
    sourceReference: String(pick(row, "sourceReference", "source_reference") ?? ""),
    partnerId: pick(row, "partner", "partnerId", "partner_id") ? String(pick(row, "partner", "partnerId", "partner_id")) : null,
    partnerName: String(pick(row, "partnerNameSnapshot", "partner_name_snapshot", "partnerName", "partner_name", "partnerDisplay", "partner_display") ?? ""),
    productId: pick(row, "product", "productId", "product_id") ? String(pick(row, "product", "productId", "product_id")) : null,
    productName: String(pick(row, "productNameSnapshot", "product_name_snapshot", "productName", "product_name", "productDisplay", "product_display") ?? ""),
    planId: pick(row, "plan", "planId", "plan_id") ? String(pick(row, "plan", "planId", "plan_id")) : null,
    planName: String(pick(row, "planNameSnapshot", "plan_name_snapshot", "planName", "plan_name", "planDisplay", "plan_display") ?? ""),
    currency: String(pick(row, "currency") ?? "TZS"),
    premiumFrequency: String(pick(row, "premiumFrequency", "premium_frequency") ?? ""),
    installmentNumber: Number(pick(row, "installmentNumber", "installment_number") ?? 1),
    installmentCount: Number(pick(row, "installmentCount", "installment_count") ?? 1),
    dueDate: String(pick(row, "dueDate", "due_date") ?? ""),
    premiumAmount: amount("premiumAmount"),
    amountPaid: amount("amountPaid"),
    amountWaived: amount("amountWaived"),
    balance: amount("balance"),
    status: String(pick(row, "status") ?? "").toUpperCase(),
    graceDate: String(pick(row, "graceDate", "grace_date") ?? "") || null,
    warningDate: String(pick(row, "warningDate", "warning_date") ?? "") || null,
    preLapseDate: String(pick(row, "preLapseDate", "pre_lapse_date") ?? "") || null,
    lapseDate: String(pick(row, "lapseDate", "lapse_date") ?? "") || null,
    approvalRequired: Boolean(pick(row, "approvalRequired", "approval_required") ?? false),
    sourceChannel: String(pick(row, "sourceChannel", "source_channel") ?? ""),
    reasonCode: String(pick(row, "reasonCode", "reason_code") ?? ""),
    reasonText: String(pick(row, "reasonText", "reason_text") ?? ""),
    allowedActions: Array.isArray(pick(row, "allowedActions", "allowed_actions"))
      ? (pick(row, "allowedActions", "allowed_actions") as unknown[]).map(String)
      : undefined,
  }
}

export function normalizePaginated<T>(payload: unknown): Paginated<T> {
  if (payload && typeof payload === "object") {
    const record = payload as Record<string, unknown>
    const results = Array.isArray(record.results)
      ? (record.results as unknown[])
      : Array.isArray(record.data)
        ? (record.data as unknown[])
        : Array.isArray(payload)
          ? (payload as unknown[])
          : []
    const pagination = isRecordObject(record.pagination) ? (record.pagination as Record<string, unknown>) : undefined
    return {
      results: results as T[],
      count: Number(record.count ?? pagination?.total ?? results.length ?? 0),
      next: record.next ? String(record.next) : null,
      previous: record.previous ? String(record.previous) : null,
    }
  }
  return { results: [], count: 0, next: null, previous: null }
}

function isRecordObject(value: unknown): boolean {
  return typeof value === "object" && value !== null && !Array.isArray(value)
}

export function normalizeDetail(payload: unknown): CommitmentDetail {
  const record = payload && typeof payload === "object" ? (payload as Record<string, unknown>) : {}
  const commitment = normalizeCommitment(record)
  const rawAllocations = record.allocations ?? record.allocation
  const allocations = (Array.isArray(rawAllocations) ? rawAllocations : []).map<CommitmentAllocation>((entry) => {
    const row = (entry ?? {}) as Record<string, unknown>
    return {
      id: String(row.id ?? ""),
      receiptReference: String(row.receiptReference ?? row.receipt_reference ?? ""),
      amount: String(row.amount ?? ""),
      paymentMode: String(row.paymentMode ?? row.payment_mode ?? ""),
      currency: String(row.currency ?? "TZS"),
      exchangeRate: String(row.exchangeRate ?? row.exchange_rate ?? "1"),
      reason: String(row.reason ?? ""),
      reversalOf: row.reversalOf ? String(row.reversalOf) : row.reversal_of ? String(row.reversal_of) : null,
      allocatedAt: String(row.allocatedAt ?? row.allocated_at ?? ""),
    }
  })
  const rawLogs = record.notificationLogs ?? record.notification_logs
  const notificationLogs = (Array.isArray(rawLogs) ? rawLogs : []).map<CommitmentNotificationLog>((entry) => {
    const row = (entry ?? {}) as Record<string, unknown>
    return {
      id: String(row.id ?? ""),
      eventType: String(row.eventType ?? row.event_type ?? ""),
      dispatchOn: String(row.dispatchOn ?? row.dispatch_on ?? ""),
      channel: String(row.notificationChannel ?? row.notification_channel ?? row.channel ?? ""),
      recipientType: String(row.recipientType ?? row.recipient_type ?? ""),
      recipientIdentifier: String(row.recipientIdentifier ?? row.recipient_identifier ?? ""),
      templateCode: String(row.templateCode ?? row.template_code ?? ""),
      status: String(row.status ?? ""),
    }
  })
  return { ...commitment, allocations, notificationLogs }
}

export function buildCommitmentQuery(filters: CommitmentListFilters = {}): string {
  const params = new URLSearchParams()
  const set = (key: string, value: unknown) => {
    if (value !== undefined && value !== null && value !== "") params.set(key, String(value))
  }
  set("page", filters.page)
  set("page_size", filters.pageSize)
  set("search", filters.search)
  set("ordering", filters.ordering)
  set("status", filters.status)
  set("source_type", filters.sourceType)
  set("currency", filters.currency)
  set("product", filters.product)
  set("due_date_from", filters.dueDateFrom)
  set("due_date_to", filters.dueDateTo)
  set("overdue_only", filters.overdueOnly)
  set("balance_only", filters.balanceOnly)
  const query = params.toString()
  return query ? `?${query}` : ""
}

// ---------------------------------------------------------------------------
// API functions
// ---------------------------------------------------------------------------

export function listCommitments(filters: CommitmentListFilters = {}): Promise<Paginated<CommitmentRecord>> {
  return request<Paginated<CommitmentRecord>>(
    `${COMMITMENTS_API_PREFIX}/commitments/${buildCommitmentQuery(filters)}`,
  )
}

export function getCommitmentKPIs(): Promise<CommitmentKPIs> {
  return request<CommitmentKPIs>(`${COMMITMENTS_API_PREFIX}/commitments/kpis/`)
}

export function getCommitment(id: string): Promise<CommitmentDetail> {
  return request<CommitmentDetail>(`${COMMITMENTS_API_PREFIX}/commitments/${id}/`)
}

export function getCommitmentOptions(): Promise<CommitmentOptions> {
  return request<CommitmentOptions>(`${COMMITMENTS_API_PREFIX}/options/`)
}

export function generateCommitmentsPreview(payload: GenerationPayload): Promise<{ rows: unknown[] }> {
  return request(`${COMMITMENTS_API_PREFIX}/commitments/generate-preview/`, {
    method: "POST",
    body: JSON.stringify(payload),
  })
}

export function generateCommitments(payload: GenerationPayload): Promise<{ created: number; events: number }> {
  return request(`${COMMITMENTS_API_PREFIX}/commitments/generate/`, {
    method: "POST",
    body: JSON.stringify(payload),
  })
}

export function importCommitmentRows(payload: { rows: Record<string, unknown>[] }): Promise<{
  imported: number
  errors: Array<{ row: number; field_errors?: Record<string, string[]>; message?: string }>
}> {
  return request(`${COMMITMENTS_API_PREFIX}/commitments/import/`, {
    method: "POST",
    body: JSON.stringify(payload),
  })
}

export function processOverdueCommitments(): Promise<{ processed: number; overdue: number; notified: number }> {
  return request(`${COMMITMENTS_API_PREFIX}/commitments/process-overdue/`, { method: "POST" })
}

export function commitmentAction<T = CommitmentDetail>(
  id: string,
  action: string,
  payload: Record<string, unknown> = {},
): Promise<T> {
  return request<T>(`${COMMITMENTS_API_PREFIX}/commitments/${id}/${action}/`, {
    method: "POST",
    body: JSON.stringify(payload),
  })
}

export function isCommitmentAction(value: string): value is CommitmentAction {
  return (COMMITMENT_ACTIONS as readonly string[]).includes(value)
}

export { type ApiClientError }