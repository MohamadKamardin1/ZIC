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
  approvalRequired?: boolean
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
  statusHistory?: CommitmentHistoryEntry[]
  graceDays?: number
}

export interface CommitmentHistoryEntry {
  fromStatus?: string
  toStatus?: string
  actorName?: string
  createdAt?: string
  reason?: string
  sourceChannel?: string
}

export interface CommitmentKPIs {
  totalDue: string
  totalOutstanding: string
  overdueCount: number
  collectedInPeriod: string
  approvalsPending?: number
}

export interface GenerationPayload {
  sourceType: CommitmentSourceType
  sourceId?: string
  method?: "auto" | "manual"
  manual?: Record<string, unknown>
}

export interface CommitmentSourceOption {
  id: string
  label: string
  reference?: string
}

export interface CommitmentReferenceOptions {
  partners: CommitmentSourceOption[]
  products: CommitmentSourceOption[]
  plans: CommitmentSourceOption[]
}

export interface CommitmentPreviewRow {
  installmentNumber: number
  dueDate: string
  amount: string
  currency: string
  graceDate?: string | null
  lapseDate?: string | null
  status: string
}

export interface ManualCommitmentPayload {
  partner?: string
  product?: string
  plan?: string
  currency?: string
  installmentNumber?: number
  dueDate: string
  premiumAmount: string
  paymentMode?: string
  reason?: string
}

export interface GenerateResult {
  created: number
  events: number
  existing?: Array<{ id?: string; commitment_number?: string; installment_number?: number }>
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
  const rawHistory = record.statusHistory ?? record.status_history ?? record.events
  const statusHistory = (Array.isArray(rawHistory) ? rawHistory : []).map<CommitmentHistoryEntry>((entry) => {
    const row = (entry ?? {}) as Record<string, unknown>
    return {
      fromStatus: String(row.fromStatus ?? row.from_status ?? ""),
      toStatus: String(row.toStatus ?? row.to_status ?? ""),
      actorName: String(row.actorName ?? row.actor_name ?? row.changedBy ?? row.changed_by ?? ""),
      createdAt: String(row.createdAt ?? row.created_at ?? ""),
      reason: String(row.reason ?? ""),
      sourceChannel: String(row.sourceChannel ?? row.source_channel ?? ""),
    }
  })
  const graceDays = Number(record.graceDays ?? record.grace_days ?? undefined)
  return {
    ...commitment,
    allocations,
    notificationLogs,
    statusHistory: statusHistory.length ? statusHistory : undefined,
    graceDays: Number.isFinite(graceDays) ? graceDays : undefined,
  }
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
  set("approval_required", filters.approvalRequired)
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

export function getCommitmentSources(sourceType: CommitmentSourceType): Promise<{ results: CommitmentSourceOption[] }> {
  return request(`${COMMITMENTS_API_PREFIX}/options/sources/?source_type=${encodeURIComponent(sourceType)}`)
}

export function getCommitmentReferenceOptions(): Promise<CommitmentReferenceOptions> {
  return request<CommitmentReferenceOptions>(`${COMMITMENTS_API_PREFIX}/options/references/`)
}

export function createManualCommitment(payload: ManualCommitmentPayload): Promise<CommitmentDetail> {
  return request(`${COMMITMENTS_API_PREFIX}/commitments/manual/`, {
    method: "POST",
    body: JSON.stringify(payload),
  })
}

export function normalizePreviewRows(payload: { rows?: unknown[] } | unknown[] | unknown): CommitmentPreviewRow[] {
  const rows = Array.isArray(payload)
    ? payload
    : payload && typeof payload === "object" && Array.isArray((payload as { rows?: unknown[] }).rows)
      ? (payload as { rows: unknown[] }).rows
      : []
  return rows.map((raw) => {
    const row = raw && typeof raw === "object" ? (raw as Record<string, unknown>) : {}
    return {
      installmentNumber: Number(row.installmentNumber ?? row.installment_number ?? 1),
      dueDate: String(row.dueDate ?? row.due_date ?? ""),
      amount: String(row.amount ?? row.premiumAmount ?? row.premium_amount ?? ""),
      currency: String(row.currency ?? "TZS"),
      graceDate: String(row.graceDate ?? row.grace_date ?? "") || null,
      lapseDate: String(row.lapseDate ?? row.lapse_date ?? "") || null,
      status: String(row.status ?? "PENDING"),
    }
  })
}

export function normalizeGenerateResult(payload: unknown): GenerateResult {
  const record = payload && typeof payload === "object" ? (payload as Record<string, unknown>) : {}
  return {
    created: Number(record.created ?? 0),
    events: Number(record.events ?? 0),
    existing: Array.isArray(record.existing)
      ? record.existing.map((entry) => {
          const item = (entry ?? {}) as Record<string, unknown>
          return {
            id: item.id ? String(item.id) : undefined,
            commitment_number: item.commitment_number ?? item.commitmentNumber ? String(item.commitment_number ?? item.commitmentNumber) : undefined,
            installment_number: item.installment_number ?? item.installmentNumber ? Number(item.installment_number ?? item.installmentNumber) : undefined,
          }
        })
      : undefined,
  }
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

export interface ImportRowError {
  row: number
  field_errors?: Record<string, string[]>
  message?: string
}

export interface ImportRunResult {
  dry_run: boolean
  imported: number
  created: number
  errors: ImportRowError[]
}

export interface ImportHistoryRecord {
  id: string
  fileName: string
  uploadedByName?: string
  createdAt: string
  okCount: number
  errorCount: number
  createdCount: number
  status: string
}

export interface ImportDetail {
  errors: ImportRowError[]
  okCount: number
  errorCount: number
}

export function importCommitmentRows(
  payload: { rows: Record<string, unknown>[] },
  options: { dryRun?: boolean } = {},
): Promise<ImportRunResult> {
  const query = options.dryRun ? "?dry_run=true" : ""
  return request<ImportRunResult>(`${COMMITMENTS_API_PREFIX}/commitments/import/${query}`, {
    method: "POST",
    body: JSON.stringify(payload),
  })
}

export function listCommitmentImports(): Promise<{ results: ImportHistoryRecord[] }> {
  return request(`${COMMITMENTS_API_PREFIX}/imports/`)
}

export function getCommitmentImport(id: string): Promise<ImportDetail> {
  return request(`${COMMITMENTS_API_PREFIX}/imports/${id}/`)
}

export const COMMITMENT_IMPORT_TEMPLATE_COLUMNS = [
  "source_type",
  "source_reference",
  "partner",
  "product",
  "plan",
  "currency",
  "installment_number",
  "installment_count",
  "due_date",
  "premium_amount",
  "payment_mode",
  "reason",
]

export function commitmentImportTemplate(): string {
  const header = COMMITMENT_IMPORT_TEMPLATE_COLUMNS.join(",")
  const sampleRow = [
    "POLICY",
    "POL-2026-0001",
    "Zanzibar Trading Co.",
    "Family Protection",
    "Standard",
    "TZS",
    "1",
    "12",
    "2026-09-01",
    "50000.00",
    "CASH",
    "Imported renewal commitment",
  ].join(",")
  return `${header}\n${sampleRow}\n`
}

export function normalizeImportHistory(payload: unknown): ImportHistoryRecord[] {
  if (Array.isArray(payload)) {
    return payload.map((entry) => normalizeImportRecord(entry)).filter((item): item is ImportHistoryRecord => Boolean(item))
  }
  if (payload && typeof payload === "object") {
    const record = payload as Record<string, unknown>
    const results = Array.isArray(record.results) ? record.results : Array.isArray(record.items) ? record.items : []
    return results.map((entry) => normalizeImportRecord(entry)).filter((item): item is ImportHistoryRecord => Boolean(item))
  }
  return []
}

function normalizeImportRecord(value: unknown): ImportHistoryRecord | null {
  if (!value || typeof value !== "object") return null
  const row = value as Record<string, unknown>
  if (!row.id) return null
  return {
    id: String(row.id),
    fileName: String(row.file_name ?? row.fileName ?? "Commitment import"),
    uploadedByName: String(row.uploaded_by_name ?? row.uploadedByName ?? ""),
    createdAt: String(row.created_at ?? row.createdAt ?? ""),
    okCount: Number(row.ok_count ?? row.okCount ?? 0),
    errorCount: Number(row.error_count ?? row.errorCount ?? 0),
    createdCount: Number(row.created_count ?? row.createdCount ?? 0),
    status: String(row.status ?? "COMPLETED"),
  }
}

export function processOverdueCommitments(): Promise<OverdueRunResult> {
  return request<OverdueRunResult>(`${COMMITMENTS_API_PREFIX}/commitments/process-overdue/`, { method: "POST" }).then(normalizeOverdueResult)
}

export function getLapseReviewQueue(): Promise<{ results: LapseReviewRow[] }> {
  return request(`${COMMITMENTS_API_PREFIX}/commitments/lapse-review/`)
}

export function getOverdueNotifications(): Promise<{ results: OverdueNotificationItem[] }> {
  return request(`${COMMITMENTS_API_PREFIX}/notifications/overdue/`)
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

// ---------------------------------------------------------------------------
// Overdue processing / lapse review / overdue notifications
// ---------------------------------------------------------------------------

export interface OverdueRunResult {
  processed: number
  overdue: number
  notified: number
  lapseReviews: number
}

export interface LapseReviewRow {
  id: string
  commitmentNumber?: string
  sourceReference?: string
  partnerName?: string
  productName?: string
  planName?: string
  policyReference?: string
  dueDate?: string
  lapseDate?: string
  status?: string
  recommendedAction?: string
}

export interface OverdueNotificationItem {
  id: string
  title: string
  message: string
  deepLink?: string
  createdAt?: string
}

export function normalizeOverdueResult(payload: unknown): OverdueRunResult {
  const record = payload && typeof payload === "object" ? (payload as Record<string, unknown>) : {}
  return {
    processed: Number(record.processed ?? 0),
    overdue: Number(record.overdue ?? 0),
    notified: Number(record.notified ?? 0),
    lapseReviews: Number(record.lapse_reviews ?? record.lapseReviews ?? 0),
  }
}

export function normalizeLapseReviewRows(payload: unknown): LapseReviewRow[] {
  const source = Array.isArray(payload)
    ? payload
    : payload && typeof payload === "object" && Array.isArray((payload as { results?: unknown }).results)
      ? (payload as { results: unknown[] }).results
      : []
  return source.map((raw) => {
    const row = raw && typeof raw === "object" ? (raw as Record<string, unknown>) : {}
    return {
      id: String(row.id ?? ""),
      commitmentNumber: String(row.commitment_number ?? row.commitmentNumber ?? ""),
      sourceReference: String(row.source_reference ?? row.sourceReference ?? ""),
      partnerName: String(row.partner_name ?? row.partnerName ?? ""),
      productName: String(row.product_name ?? row.productName ?? ""),
      planName: String(row.plan_name ?? row.planName ?? ""),
      policyReference: String(row.policy_reference ?? row.policyReference ?? row.source_reference ?? ""),
      dueDate: String(row.due_date ?? row.dueDate ?? "") || undefined,
      lapseDate: String(row.lapse_date ?? row.lapseDate ?? "") || undefined,
      status: String(row.status ?? ""),
      recommendedAction: String(row.recommended_action ?? row.recommendedAction ?? ""),
    }
  })
}

export function normalizeOverdueNotifications(payload: unknown): OverdueNotificationItem[] {
  const source = Array.isArray(payload)
    ? payload
    : payload && typeof payload === "object" && Array.isArray((payload as { results?: unknown }).results)
      ? (payload as { results: unknown[] }).results
      : []
  return source.map((raw) => {
    const row = raw && typeof raw === "object" ? (raw as Record<string, unknown>) : {}
    return {
      id: String(row.id ?? ""),
      title: String(row.title ?? ""),
      message: String(row.message ?? ""),
      deepLink: typeof row.deep_link === "string" ? row.deep_link : undefined,
      createdAt: String(row.created_at ?? row.createdAt ?? ""),
    }
  })
}

// ---------------------------------------------------------------------------
// Partner portal (strictly read-only, partner-scoped on the backend)
// ---------------------------------------------------------------------------

export function listPortalCommitments(filters: CommitmentListFilters = {}): Promise<Paginated<CommitmentRecord>> {
  return request<Paginated<CommitmentRecord>>(`${COMMITMENTS_API_PREFIX}/portal/commitments/${buildCommitmentQuery(filters)}`)
}

export function getPortalCommitment(id: string): Promise<CommitmentDetail> {
  return request<CommitmentDetail>(`${COMMITMENTS_API_PREFIX}/portal/commitments/${id}/`)
}

export { type ApiClientError }