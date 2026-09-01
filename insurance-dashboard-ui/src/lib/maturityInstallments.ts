/**
 * OL Maturity Installments — contract-first API client.
 *
 * Mirrors the OL Maturity Installments backend contract
 * (backend/apps/ol_maturity_installments/urls.py + docs/OL_MATURITY_INSTALLMENTS_API.md).
 * The backend serializes with the global CamelCase renderer, so normalizers
 * prefer camelCase keys and fall back to snake_case so the same client also
 * works against the raw MSW wire contract. Resource IDs stay internal for API
 * navigation; components render the display fields returned by the backend
 * (planNumber, policyholderDisplay, statusDisplay, ...) instead of UUIDs.
 */

import { request, type QueryParams } from "./apiClient"

export const MATURITY_INSTALLMENTS_API_PREFIX = "/api/v1/ol/maturity-installments"

export const MI_PLAN_STATUSES = ["CREATED", "ACTIVE", "COMPLETED", "CANCELLED", "TERMINATED"] as const
export type MIPlanStatus = (typeof MI_PLAN_STATUSES)[number] | string

export const MI_ITEM_STATUSES = ["SCHEDULED", "PAYMENT_PENDING", "PAID", "MISSED", "WAIVED"] as const
export type MIItemStatus = (typeof MI_ITEM_STATUSES)[number] | string

export const MI_PAYMENT_METHODS = ["CASH", "BANK_TRANSFER", "CHEQUE"] as const
export type MIPaymentMethod = (typeof MI_PAYMENT_METHODS)[number] | string

export const MI_FREQUENCIES = ["SINGLE", "MONTHLY", "QUARTERLY", "HALF_YEARLY", "ANNUAL"] as const
export type MIFrequency = (typeof MI_FREQUENCIES)[number] | string

export type MIPlanAction = "view" | "create" | "process_payment" | "cancel" | "print" | "configure"

export interface MIPaginated<T> {
  results: T[]
  count: number
  next: boolean | string | null
  previous: boolean | string | null
  page?: number
  pageSize?: number
}

export interface MIPlanItemPage {
  results: MIPlanItem[]
  count: number
  page: number
  pageSize: number
  next: boolean
  previous: boolean
  totalAmount: string
  totalPaid: string
  totalRemaining: string
}

export interface MIOption {
  value: string
  label: string
  meta?: Record<string, unknown>
}

export interface MIPlanListFilters {
  page?: number
  pageSize?: number
  search?: string
  sort?: string
  status?: string
  frequency?: string
  policyNumber?: string
  product?: string
  branch?: string
  missedOnly?: boolean
  dateFrom?: string
  dateTo?: string
}

export interface MIPlanRecord {
  [key: string]: unknown
  id: string
  planNumber: string
  policyId?: string
  policyNumber: string
  policyholderName: string
  policyholderDisplay: string
  claimNumber: string | null
  currency: string
  frequency: MIFrequency
  status: MIPlanStatus
  statusDisplay: string
  totalAmount: string
  paidAmount: string
  balance: string
  maturityValue: string
  installmentCount: number
  startDate: string | null
  endDate: string | null
  productCode?: string | null
  productDisplay?: string | null
  completedAt?: string | null
  terminationReason?: string | null
  terminatedAt?: string | null
  allowedActions: MIPlanAction[]
  createdAt: string | null
  updatedAt: string | null
}

export interface MIPlanItem {
  id: string
  planId?: string
  installmentNumber: number
  dueDate: string | null
  amount: string
  status: MIItemStatus
  statusDisplay: string
  requisitionNumber: string | null
  paidDate: string | null
  paidByDisplay: string | null
  payerDisplay: string | null
  paymentReference: string | null
  narration: string
  paymentMethod?: string | null
  bankAccountDisplay?: string | null
}

export interface MIBankAccount {
  id: string
  accountName: string
  accountNumber: string
  bankName: string
  branch?: string | null
  isDefault: boolean
  availableBalance?: string | null
}

export interface MIPaymentHistoryEntry {
  installmentNumber: number
  dueDate: string | null
  amount: string
  status: string
  paidDate: string | null
  requisitionNumber: string | null
  paymentReference: string | null
  payerDisplay: string | null
}

export interface MIRequisitionInfo {
  requisitionNumber: string
  status: string
  statusDisplay: string
  amount: string
  department: string
}

export interface MIReconciliationDiscrepancy {
  code: string
  message: string
}

export interface MIReconciliationReport {
  status: "PASS" | "FAIL"
  maturityValue: string
  totalPayableAmount: string
  paidAmount: string
  missingAmount: string
  paidItems: number
  totalItems: number
  discrepancies: MIReconciliationDiscrepancy[]
}

export interface MIPlanDocument {
  id: string
  documentType: string
  templateName: string
  templateVersion: string | number
  pageCount: string | number
  generatedByDisplay: string
  generatedAt: string
  previewUrl?: string | null
  signedDownloadUrl?: string | null
  downloadUrl?: string | null
}

export interface MIPlanAuditEntry {
  id: string
  action: string
  actionDisplay: string
  actorDisplay: string
  timestamp: string
  channel: string
  details?: string
}

export interface MIPlanStatusHistoryEntry {
  status: string
  statusDisplay: string
  timestamp: string
  note?: string
}

export interface MIPlanDetail extends MIPlanRecord {
  maturityClaimId?: string | null
  totalPayableAmount: string
  totalPaidAmount: string
  sourceChannel: string
  sourceChannelDisplay: string
  parameterSnapshot: Record<string, unknown>
  items: MIPlanItem[]
  paymentHistory: MIPaymentHistoryEntry[]
  reconciliation?: MIReconciliationReport | null
  calculationSource?: string | null
  calculationSourceDisplay?: string | null
  documents: MIPlanDocument[]
  auditHistory: MIPlanAuditEntry[]
  statusHistory: MIPlanStatusHistoryEntry[]
  bankAccounts: MIBankAccount[]
}

export interface MIPlanKpis {
  totalPlansActive: number
  totalActivePlansValue?: string | null
  totalUpcomingPayouts: number
  upcomingNext30Days?: number | null
  missedPaymentsCount: number
  completedPlansCount: number
  filtersApplied?: Record<string, unknown>
  timestamp: string
}

export interface MIPlanCreatePayload {
  policyId: string
  maturityClaimId?: string | null
  frequency: string
  termYears: number
}

export interface MIPlanCreateResult {
  plan?: MIPlanDetail
  created?: boolean
  [key: string]: unknown
}

export interface MIPaymentResult {
  item?: MIPlanItem
  plan?: MIPlanDetail
  requisition?: MIRequisitionInfo
  planCompleted?: boolean
  confirmed?: boolean
  created?: boolean
  [key: string]: unknown
}

export interface MIProcessPaymentDetails {
  paymentMethod?: string
  referenceNumber?: string
  bankAccountId?: string
}

export interface MIReversePayload {
  reason: string
}

export interface MICancelPayload {
  reason: string
}

export interface MIPrintResult {
  instance?: Record<string, unknown>
  signedDownloadUrl?: string
  previewUrl?: string
  [key: string]: unknown
}

export interface MIPortalItem {
  id: string
  installmentNumber: number
  dueDate: string | null
  amount: string
  status: string
  statusDisplay: string
}

export interface MIPortalPlan {
  id: string
  planNumber: string
  policyNumber: string
  status: string
  statusDisplay: string
  currency: string
  frequency: string
  installmentCount: number
  paidInstallments: number
  totalAmount: string
  paidAmount: string
  startDate: string | null
  endDate: string | null
  items: MIPortalItem[]
}

export interface MIFrequencyOption extends MIOption {
  meta?: { monthsBetween?: number; payoutPerYear?: number }
}

export interface MITermOption extends MIOption {
  meta?: { source?: string }
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
  const value = pick(row, ...keys)
  if (value === undefined || value === null || value === "") return "0.00"
  return typeof value === "number" ? value.toFixed(2) : String(value)
}

function numberValue(row: Record<string, unknown>, ...keys: string[]): number {
  const value = pick(row, ...keys)
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : 0
}

function booleanValue(row: Record<string, unknown>, ...keys: string[]): boolean {
  return Boolean(pick(row, ...keys) ?? false)
}

function arrayValue(row: Record<string, unknown>, ...keys: string[]): unknown[] {
  const value = pick<unknown>(row, ...keys)
  return Array.isArray(value) ? value : []
}

export function normalizeMIPlanItem(row: Record<string, unknown>): MIPlanItem {
  return {
    id: stringValue(row, "id"),
    planId: nullableString(row, "planId", "plan_id") ?? undefined,
    installmentNumber: numberValue(row, "installmentNumber", "installment_number"),
    dueDate: nullableString(row, "dueDate", "due_date"),
    amount: amountValue(row, "amount"),
    status: stringValue(row, "status").toUpperCase(),
    statusDisplay: stringValue(row, "statusDisplay", "status_display", "status"),
    requisitionNumber: nullableString(row, "requisitionNumber", "requisition_number", "payment_requisition_ref"),
    paidDate: nullableString(row, "paidDate", "paid_date"),
    paidByDisplay: nullableString(row, "paidByDisplay", "paid_by_display", "paid_by"),
    payerDisplay: nullableString(row, "payerDisplay", "payer_display", "payer"),
    paymentReference: nullableString(row, "paymentReference", "payment_reference"),
    narration: stringValue(row, "narration"),
    paymentMethod: nullableString(row, "paymentMethod", "payment_method"),
    bankAccountDisplay: nullableString(row, "bankAccountDisplay", "bank_account_display"),
  }
}

function normalizeMIBankAccount(row: Record<string, unknown>): MIBankAccount {
  return {
    id: stringValue(row, "id", "uuid"),
    accountName: stringValue(row, "accountName", "account_name"),
    accountNumber: stringValue(row, "accountNumber", "account_number"),
    bankName: stringValue(row, "bankName", "bank_name"),
    branch: nullableString(row, "branch"),
    isDefault: booleanValue(row, "isDefault", "is_default"),
    availableBalance: nullableString(row, "availableBalance", "available_balance"),
  }
}

export function normalizeMIPlanItemPage(payload: unknown): MIPlanItemPage {
  const page = isRecord(payload) ? payload : {}
  const results = arrayValue(page, "results").filter(isRecord).map(normalizeMIPlanItem)
  const count = numberValue(page, "count")
  const pageSize = numberValue(page, "pageSize", "page_size")
  const pageNumber = numberValue(page, "page", "current_page")
  return {
    results,
    count,
    page: pageNumber || 1,
    pageSize: pageSize || 20,
    next: Boolean(pick(page, "next")),
    previous: Boolean(pick(page, "previous")),
    totalAmount: amountValue(page, "totalAmount", "total_amount"),
    totalPaid: amountValue(page, "totalPaid", "total_paid"),
    totalRemaining: amountValue(page, "totalRemaining", "total_remaining"),
  }
}

function normalizePaymentHistoryEntry(row: Record<string, unknown>): MIPaymentHistoryEntry {
  return {
    installmentNumber: numberValue(row, "installmentNumber", "installment_number"),
    dueDate: nullableString(row, "dueDate", "due_date"),
    amount: amountValue(row, "amount"),
    status: stringValue(row, "status").toUpperCase(),
    paidDate: nullableString(row, "paidDate", "paid_date"),
    requisitionNumber: nullableString(row, "requisitionNumber", "requisition_number", "payment_requisition_ref"),
    paymentReference: nullableString(row, "paymentReference", "payment_reference"),
    payerDisplay: nullableString(row, "payerDisplay", "payer_display", "payer"),
  }
}

function normalizeRequisitionInfo(row: Record<string, unknown>): MIRequisitionInfo {
  return {
    requisitionNumber: stringValue(row, "requisitionNumber", "requisition_number"),
    status: stringValue(row, "status").toUpperCase(),
    statusDisplay: stringValue(row, "statusDisplay", "status_display", "status"),
    amount: amountValue(row, "amount"),
    department: stringValue(row, "department"),
  }
}

export function normalizeMIPlanRow(row: Record<string, unknown>): MIPlanRecord {
  const policyholderDisplay = stringValue(row, "policyholderDisplay", "policyholder_display", "policyholderName", "policyholder_name", "partnerDisplay", "partner_display")
  return {
    ...row,
    id: stringValue(row, "id", "uuid"),
    planNumber: stringValue(row, "planNumber", "plan_number"),
    policyId: nullableString(row, "policyId", "policy_id") ?? undefined,
    policyNumber: stringValue(row, "policyNumber", "policy_number"),
    policyholderName: stringValue(row, "policyholderName", "policyholder_name", "partnerDisplay", "partner_display"),
    policyholderDisplay,
    claimNumber: nullableString(row, "claimNumber", "claim_number"),
    currency: stringValue(row, "currency") || "TZS",
    frequency: stringValue(row, "frequency").toUpperCase(),
    status: stringValue(row, "status").toUpperCase(),
    statusDisplay: stringValue(row, "statusDisplay", "status_display", "status"),
    totalAmount: amountValue(row, "totalAmount", "total_amount", "totalPayableAmount", "total_payable_amount"),
    paidAmount: amountValue(row, "paidAmount", "paid_amount"),
    balance: amountValue(row, "balance"),
    maturityValue: amountValue(row, "maturityValue", "maturity_value", "totalMaturityValue", "total_maturity_value"),
    installmentCount: numberValue(row, "installmentCount", "installment_count"),
    startDate: nullableString(row, "startDate", "start_date"),
    endDate: nullableString(row, "endDate", "end_date"),
    productCode: nullableString(row, "productCode", "product_code"),
    productDisplay: nullableString(row, "productDisplay", "product_display", "product_code"),
    completedAt: nullableString(row, "completedAt", "completed_at"),
    terminationReason: nullableString(row, "terminationReason", "termination_reason"),
    terminatedAt: nullableString(row, "terminatedAt", "terminated_at"),
    allowedActions: arrayValue(row, "allowedActions", "allowed_actions").map(String) as MIPlanAction[],
    createdAt: nullableString(row, "createdAt", "created_at"),
    updatedAt: nullableString(row, "updatedAt", "updated_at"),
  }
}

function normalizeReconciliation(row: Record<string, unknown>): MIReconciliationReport {
  return {
    status: stringValue(row, "status").toUpperCase() === "FAIL" ? "FAIL" : "PASS",
    maturityValue: amountValue(row, "maturityValue", "maturity_value"),
    totalPayableAmount: amountValue(row, "totalPayableAmount", "total_payable_amount"),
    paidAmount: amountValue(row, "paidAmount", "paid_amount"),
    missingAmount: amountValue(row, "missingAmount", "missing_amount"),
    paidItems: numberValue(row, "paidItems", "paid_items"),
    totalItems: numberValue(row, "totalItems", "total_items"),
    discrepancies: arrayValue(row, "discrepancies").filter(isRecord).map((item) => ({
      code: stringValue(item, "code"),
      message: stringValue(item, "message"),
    })),
  }
}

function scalarValue(value: unknown, fallback: string | number): string | number {
  return typeof value === "string" || typeof value === "number" ? value : fallback
}

function normalizeMIPlanDocument(row: Record<string, unknown>): MIPlanDocument {
  return {
    id: stringValue(row, "id", "uuid"),
    documentType: stringValue(row, "documentType", "document_type"),
    templateName: stringValue(row, "templateName", "template_name") || "Maturity Installment document",
    templateVersion: scalarValue(row.templateVersion ?? row.template_version, "—"),
    pageCount: scalarValue(row.pageCount ?? row.page_count, "—"),
    generatedByDisplay: stringValue(row, "generatedByDisplay", "generated_by_display", "generatedBy", "generated_by") || "System",
    generatedAt: stringValue(row, "generatedAt", "generated_at"),
    previewUrl: nullableString(row, "previewUrl", "preview_url"),
    signedDownloadUrl: nullableString(row, "signedDownloadUrl", "signed_download_url"),
    downloadUrl: nullableString(row, "downloadUrl", "download_url"),
  }
}

function normalizeMIPlanAuditEntry(row: Record<string, unknown>): MIPlanAuditEntry {
  return {
    id: stringValue(row, "id", "uuid"),
    action: stringValue(row, "action").toUpperCase(),
    actionDisplay: stringValue(row, "actionDisplay", "action_display", "action"),
    actorDisplay: stringValue(row, "actorDisplay", "actor_display", "actor") || "System",
    timestamp: stringValue(row, "timestamp", "created_at", "createdAt"),
    channel: stringValue(row, "channel", "sourceChannel", "source_channel"),
    details: nullableString(row, "details", "narration") ?? undefined,
  }
}

function normalizeMIPlanStatusHistoryEntry(row: Record<string, unknown>): MIPlanStatusHistoryEntry {
  return {
    status: stringValue(row, "status").toUpperCase(),
    statusDisplay: stringValue(row, "statusDisplay", "status_display", "status"),
    timestamp: stringValue(row, "timestamp"),
    note: nullableString(row, "note") ?? undefined,
  }
}

export function normalizeMIPlanDetail(payload: unknown): MIPlanDetail {
  const record = isRecord(payload) ? payload : {}
  const plan = normalizeMIPlanRow(record)
  const rawReconciliation = pick<unknown>(record, "reconciliation")
  return {
    ...plan,
    maturityClaimId: nullableString(record, "maturityClaimId", "maturity_claim_id"),
    totalPayableAmount: amountValue(record, "totalPayableAmount", "total_payable_amount", "totalAmount", "total_amount"),
    totalPaidAmount: amountValue(record, "totalPaidAmount", "total_paid_amount", "paidAmount", "paid_amount"),
    sourceChannel: stringValue(record, "sourceChannel", "source_channel"),
    sourceChannelDisplay: stringValue(record, "sourceChannelDisplay", "source_channel_display", "source_channel"),
    parameterSnapshot: isRecord(record.parameterSnapshot ?? record.parameter_snapshot) ? (record.parameterSnapshot ?? record.parameter_snapshot) as Record<string, unknown> : {},
    items: arrayValue(record, "items", "installments").filter(isRecord).map(normalizeMIPlanItem),
    paymentHistory: arrayValue(record, "paymentHistory", "payment_history").filter(isRecord).map(normalizePaymentHistoryEntry),
    reconciliation: isRecord(rawReconciliation) ? normalizeReconciliation(rawReconciliation) : null,
    calculationSource: nullableString(record, "calculationSource", "calculation_source"),
    calculationSourceDisplay: nullableString(record, "calculationSourceDisplay", "calculation_source_display", "calculation_source"),
    documents: arrayValue(record, "documents").filter(isRecord).map(normalizeMIPlanDocument),
    auditHistory: arrayValue(record, "auditHistory", "audit_history").filter(isRecord).map(normalizeMIPlanAuditEntry),
    statusHistory: arrayValue(record, "statusHistory", "status_history").filter(isRecord).map(normalizeMIPlanStatusHistoryEntry),
    bankAccounts: arrayValue(record, "bankAccounts", "bank_accounts").filter(isRecord).map(normalizeMIBankAccount),
  }
}

export function normalizeMIPlanKpis(payload: unknown): MIPlanKpis {
  const record = isRecord(payload) ? payload : {}
  const rawValue = pick<unknown>(record, "totalActivePlansValue", "total_active_plans_value")
  const rawUpcoming30 = pick<unknown>(record, "upcomingNext30Days", "upcoming_next_30_days")
  const upcoming30 = Number(rawUpcoming30)
  return {
    totalPlansActive: numberValue(record, "totalPlansActive", "total_plans_active"),
    totalActivePlansValue: rawValue === undefined || rawValue === null || rawValue === "" ? null : String(rawValue),
    totalUpcomingPayouts: numberValue(record, "totalUpcomingPayouts", "total_upcoming_payouts"),
    upcomingNext30Days: rawUpcoming30 === undefined || rawUpcoming30 === null ? null : Number.isFinite(upcoming30) ? upcoming30 : 0,
    missedPaymentsCount: numberValue(record, "missedPaymentsCount", "missed_payments_count"),
    completedPlansCount: numberValue(record, "completedPlansCount", "completed_plans_count"),
    filtersApplied: isRecord(record.filtersApplied ?? record.filters_applied) ? (record.filtersApplied ?? record.filters_applied) as Record<string, unknown> : undefined,
    timestamp: stringValue(record, "timestamp"),
  }
}

export function normalizeMIPortalPlan(payload: unknown): MIPortalPlan {
  const record = isRecord(payload) ? payload : {}
  return {
    id: stringValue(record, "id"),
    planNumber: stringValue(record, "planNumber", "plan_number"),
    policyNumber: stringValue(record, "policyNumber", "policy_number"),
    status: stringValue(record, "status").toUpperCase(),
    statusDisplay: stringValue(record, "statusDisplay", "status_display", "status"),
    currency: stringValue(record, "currency") || "TZS",
    frequency: stringValue(record, "frequency").toUpperCase(),
    installmentCount: numberValue(record, "installmentCount", "installment_count"),
    paidInstallments: numberValue(record, "paidInstallments", "paid_installments"),
    totalAmount: amountValue(record, "totalAmount", "total_amount"),
    paidAmount: amountValue(record, "paidAmount", "paid_amount"),
    startDate: nullableString(record, "startDate", "start_date"),
    endDate: nullableString(record, "endDate", "end_date"),
    items: arrayValue(record, "items", "installments").filter(isRecord).map((item) => ({
      id: stringValue(item, "id"),
      installmentNumber: numberValue(item, "installmentNumber", "installment_number"),
      dueDate: nullableString(item, "dueDate", "due_date"),
      amount: amountValue(item, "amount"),
      status: stringValue(item, "status").toUpperCase(),
      statusDisplay: stringValue(item, "statusDisplay", "status_display", "status"),
    })),
  }
}

function normalizePaymentResult(payload: unknown): MIPaymentResult {
  const record = isRecord(payload) ? payload : {}
  const rawItem = pick<unknown>(record, "item")
  const rawPlan = pick<unknown>(record, "plan")
  const rawRequisition = pick<unknown>(record, "requisition")
  return {
    ...record,
    item: isRecord(rawItem) ? normalizeMIPlanItem(rawItem) : undefined,
    plan: isRecord(rawPlan) ? normalizeMIPlanDetail(rawPlan) : undefined,
    requisition: isRecord(rawRequisition) ? normalizeRequisitionInfo(rawRequisition) : undefined,
    planCompleted: booleanValue(record, "planCompleted", "plan_completed"),
    confirmed: booleanValue(record, "confirmed"),
    created: booleanValue(record, "created"),
  }
}

function normalizeMIPlanCreateResult(payload: unknown): MIPlanCreateResult {
  const record = isRecord(payload) ? payload : {}
  const rawPlan = pick<unknown>(record, "plan")
  return {
    ...record,
    plan: isRecord(rawPlan) ? normalizeMIPlanDetail(rawPlan) : undefined,
    created: booleanValue(record, "created"),
  }
}

export function normalizeMIPaginated<T>(payload: unknown, normalizeRow?: (row: Record<string, unknown>) => T): MIPaginated<T> {
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
    page: Number(record.page ?? (isRecord(record.pagination) ? record.pagination.page : undefined) ?? 1),
    pageSize: Number(record.pageSize ?? record.page_size ?? results.length),
  }
}

export function buildMIPlanQuery(filters: MIPlanListFilters = {}): string {
  const params: QueryParams = {
    page: filters.page,
    page_size: filters.pageSize,
    q: filters.search,
    search: filters.search,
    sort: filters.sort,
    status: filters.status,
    frequency: filters.frequency,
    policy_number: filters.policyNumber,
    product: filters.product,
    branch: filters.branch,
    missed_only: filters.missedOnly,
    date_from: filters.dateFrom,
    date_to: filters.dateTo,
  }
  const search = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") search.set(key, String(value))
  })
  const query = search.toString()
  return query ? `?${query}` : ""
}

function withIdempotencyKey(idempotencyKey?: string): HeadersInit | undefined {
  return idempotencyKey ? { "X-Idempotency-Key": idempotencyKey } : undefined
}

export function listMIPlans(filters: MIPlanListFilters = {}): Promise<MIPaginated<MIPlanRecord>> {
  return request<unknown>(`${MATURITY_INSTALLMENTS_API_PREFIX}/${buildMIPlanQuery(filters)}`).then((payload) => normalizeMIPaginated(payload, normalizeMIPlanRow))
}

export function getMIPlanKpis(filters: MIPlanListFilters = {}): Promise<MIPlanKpis> {
  return request<unknown>(`${MATURITY_INSTALLMENTS_API_PREFIX}/kpis/${buildMIPlanQuery(filters)}`).then(normalizeMIPlanKpis)
}

export function getMIPlanDetail(id: string): Promise<MIPlanDetail> {
  return request<unknown>(`${MATURITY_INSTALLMENTS_API_PREFIX}/${encodeURIComponent(id)}/`).then(normalizeMIPlanDetail)
}

export function listMIPlanItems(planId: string, params: { page?: number; pageSize?: number } = {}): Promise<MIPlanItemPage> {
  const query = new URLSearchParams()
  if (params.page) query.set("page", String(params.page))
  if (params.pageSize) query.set("page_size", String(params.pageSize))
  const suffix = query.toString() ? `?${query.toString()}` : ""
  return request<unknown>(`${MATURITY_INSTALLMENTS_API_PREFIX}/${encodeURIComponent(planId)}/items/${suffix}`).then(normalizeMIPlanItemPage)
}

export function getMIFrequencyOptions(params: { q?: string; page?: number; pageSize?: number } = {}): Promise<MIPaginated<MIFrequencyOption>> {
  const search = new URLSearchParams()
  if (params.q) search.set("q", params.q)
  if (params.page) search.set("page", String(params.page))
  if (params.pageSize) search.set("page_size", String(params.pageSize))
  const query = search.toString()
  return request<unknown>(`${MATURITY_INSTALLMENTS_API_PREFIX}/options/frequencies/${query ? `?${query}` : ""}`).then((payload) => normalizeMIPaginated(payload))
}

export function getMITermOptions(params: { q?: string; product?: string; page?: number; pageSize?: number } = {}): Promise<MIPaginated<MITermOption>> {
  const search = new URLSearchParams()
  if (params.q) search.set("q", params.q)
  if (params.product) search.set("product", params.product)
  if (params.page) search.set("page", String(params.page))
  if (params.pageSize) search.set("page_size", String(params.pageSize))
  const query = search.toString()
  return request<unknown>(`${MATURITY_INSTALLMENTS_API_PREFIX}/options/terms/${query ? `?${query}` : ""}`).then((payload) => normalizeMIPaginated(payload))
}

export function createMIPlan(payload: MIPlanCreatePayload, idempotencyKey: string): Promise<MIPlanCreateResult> {
  return request<unknown>(`${MATURITY_INSTALLMENTS_API_PREFIX}/create/`, {
    method: "POST",
    headers: withIdempotencyKey(idempotencyKey),
    body: JSON.stringify({
      policy_id: payload.policyId,
      maturity_claim_id: payload.maturityClaimId ?? null,
      frequency: payload.frequency,
      term_years: payload.termYears,
    }),
  }).then(normalizeMIPlanCreateResult)
}

export function processMIPayment(itemId: string, details: MIProcessPaymentDetails = {}): Promise<MIPaymentResult> {
  const body: Record<string, unknown> = {}
  if (details.paymentMethod) body.payment_method = details.paymentMethod
  if (details.referenceNumber) body.reference_number = details.referenceNumber
  if (details.bankAccountId) body.bank_account_id = details.bankAccountId
  return request<unknown>(`${MATURITY_INSTALLMENTS_API_PREFIX}/items/${encodeURIComponent(itemId)}/process-payment/`, {
    method: "POST",
    body: JSON.stringify(body),
  }).then((payload) => normalizePaymentResult(isRecord(payload) ? payload : { item: payload }))
}

export function confirmMIPayment(itemId: string): Promise<MIPaymentResult> {
  return request<unknown>(`${MATURITY_INSTALLMENTS_API_PREFIX}/items/${encodeURIComponent(itemId)}/confirm-payment/`, {
    method: "POST",
  }).then((payload) => normalizePaymentResult(isRecord(payload) ? payload : { item: payload }))
}

export function reverseMIPayment(itemId: string, payload: MIReversePayload): Promise<MIPaymentResult> {
  return request<unknown>(`${MATURITY_INSTALLMENTS_API_PREFIX}/items/${encodeURIComponent(itemId)}/reverse-payment/`, {
    method: "POST",
    body: JSON.stringify({ reason: payload.reason }),
  }).then((payload) => normalizePaymentResult(isRecord(payload) ? payload : { item: payload }))
}

export function cancelMIPlan(planId: string, payload: MICancelPayload): Promise<MIPlanDetail> {
  return request<unknown>(`${MATURITY_INSTALLMENTS_API_PREFIX}/plans/${encodeURIComponent(planId)}/cancel/`, {
    method: "POST",
    body: JSON.stringify({ reason: payload.reason }),
  }).then(normalizeMIPlanDetail)
}

export function getMIReconciliation(planId: string): Promise<MIReconciliationReport> {
  return request<unknown>(`${MATURITY_INSTALLMENTS_API_PREFIX}/${encodeURIComponent(planId)}/reconciliation/`).then((payload) => normalizeReconciliation(isRecord(payload) ? payload : {}))
}

export function printMISchedule(planId: string): Promise<MIPrintResult> {
  return request<MIPrintResult>(`${MATURITY_INSTALLMENTS_API_PREFIX}/${encodeURIComponent(planId)}/print-schedule/`, { method: "POST" })
}

export function printMIStatement(planId: string): Promise<MIPrintResult> {
  return request<MIPrintResult>(`${MATURITY_INSTALLMENTS_API_PREFIX}/${encodeURIComponent(planId)}/print-statement/`, { method: "POST" })
}

export function listMIPortalPlans(): Promise<MIPortalPlan[]> {
  return request<unknown>(`${MATURITY_INSTALLMENTS_API_PREFIX}/portal/`).then((payload) => {
    const record = isRecord(payload) ? payload : {}
    return arrayValue(record, "results", "plans").filter(isRecord).map(normalizeMIPortalPlan)
  })
}

export function getMIPortalPlan(planId: string): Promise<MIPortalPlan> {
  return request<unknown>(`${MATURITY_INSTALLMENTS_API_PREFIX}/portal/${encodeURIComponent(planId)}/`).then(normalizeMIPortalPlan)
}
