/**
 * OL Claims — contract-first API client.
 *
 * Mirrors the OL Claims backend contract (backend/apps/ol_claims/urls.py).
 * Resource IDs stay internal for API navigation; components render the display
 * fields returned by the backend (claim_number, policyholder_display, etc.)
 * instead of UUIDs.
 */

import { request, type QueryParams } from "./apiClient"

export const CLAIMS_API_PREFIX = "/api/v1/ol/claims"
export const POLICY_CLAIMS_API_PREFIX = "/api/v1/ol/policies"

export const CLAIM_STATUSES = [
  "REGISTERED",
  "PENDING_MEDICAL",
  "ASSESSMENT",
  "ASSESSED",
  "REQUISITION",
  "REQUISITIONED",
  "APPROVED",
  "SETTLED",
  "REJECTED",
  "CANCELLED",
] as const

export type ClaimStatus = (typeof CLAIM_STATUSES)[number] | string
export type ClaimantType = "POLICYHOLDER" | "INSURED" | "DEPENDENT" | string
export type ClaimAction = "view" | "assess" | "requisition" | "settle" | "cancel" | "print"
export type ClaimOptionKind = "types" | "reasons" | "benefits" | "members" | string

export interface Paginated<T> {
  results: T[]
  count: number
  next: boolean | string | null
  previous: boolean | string | null
  page?: number
  pageSize?: number
}

export interface ClaimOption {
  value: string
  label: string
  meta?: Record<string, unknown>
}

export interface ClaimListFilters {
  page?: number
  pageSize?: number
  search?: string
  ordering?: string
  sort?: string
  status?: string
  claimType?: string
  product?: string
  branch?: string
  fraudFlag?: boolean
  dateFrom?: string
  dateTo?: string
}

export interface ClaimRecord {
  [key: string]: unknown
  id: string
  claimNumber: string
  policyId?: string
  policyNumber: string
  policyholderName: string
  policyholderDisplay: string
  productDisplay: string
  claimType: string
  claimDate: string | null
  admittedDate: string | null
  amount: string
  currency: string
  status: ClaimStatus
  statusDisplay: string
  fraudFlag: boolean
  allowedActions: string[]
  createdAt: string | null
  updatedAt: string | null
}

export interface ClaimantInfo {
  id?: string
  claimantType: string
  claimantTypeDisplay: string
  relationship: string
  name: string
  identityNumber: string
  age: number | null
  gender: string
}

export interface ClaimItem {
  id: string
  benefitType: string
  sumAssured: string
  calculatedAmount: string
  approvedAmount: string | null
  adjustmentReason: string
}

export interface ClaimDocument {
  id: string
  documentType: string
  fileReference: string
  mandatoryFlag: boolean
  uploadedByDisplay: string
  uploadedAt: string | null
}

export interface ClaimFileNote {
  id: string
  noteText: string
  authorDisplay: string
  sourceChannel: string
  createdAt: string | null
}

export interface ClaimRequisition {
  id: string
  requisitionNumber: string
  amount: string
  bankDetailsJson: Record<string, unknown>
  paymentRequisitionNumber: string | null
  approvalRequestStatus: string | null
  approvalRequired: boolean
  narration: string
  status: string
  statusDisplay: string
  createdAt: string | null
  updatedAt: string | null
}

export interface ClaimLoanOffset {
  id?: string
  grossAmount: string
  offsetAmount: string
  netPayout: string
  status: string
  loanBreakdown: Record<string, unknown>[]
}

export interface ClaimAuditEntry {
  id: string
  action: string
  actorDisplay: string
  sourceChannel: string
  reason: string
  createdAt: string | null
}

export interface ClaimFinancialSummary {
  claimNumber: string
  policyNumber: string
  currency: string
  grossAmount: string
  loanOffset: string
  netPayout: string
  loanOffsetApplied: boolean
  loanBreakdown: Record<string, unknown>[]
}

export interface ClaimDetail extends ClaimRecord {
  causeOfClaim: string
  description: string
  assessmentNotes: string
  fraudFlagReason: string
  waiverOfPremiumDays: number
  waiverOfPremiumUntil: string | null
  waiverOfPremiumApplied: boolean
  settledDate: string | null
  settlementAmount: string | null
  paymentReference: string
  sourceChannel: string
  sourceChannelDisplay: string
  medicalStatus: string
  medicalStatusDisplay: string
  medicalResult: string
  medicalReason: string
  medicalRequestedAt: string | null
  medicalReviewedByDisplay: string
  medicalReviewedAt: string | null
  medicalLoadingFactor: string | null
  registeredByDisplay: string
  admittedByDisplay: string
  claimant: ClaimantInfo | null
  items: ClaimItem[]
  documents: ClaimDocument[]
  fileNotes: ClaimFileNote[]
  requisition: ClaimRequisition | null
  loanOffset: ClaimLoanOffset | null
  policyContext?: Record<string, unknown>
  financialSummary: ClaimFinancialSummary | null
  auditTimeline: ClaimAuditEntry[]
}

export interface ClaimKpis {
  totalClaims: number
  outstandingAmount: string
  settledAmountPeriod: string
  pendingAssessmentCount: number
  currency: string
  currencyTotals?: Record<string, Record<string, string>>
  timestamp: string
}

export interface ClaimDocumentsResult {
  claimNumber: string
  results: ClaimDocument[]
  documents: ClaimDocument[]
  requiredDocumentTypes: string[]
  missingDocumentTypes: string[]
  allMandatoryUploaded: boolean
  mandatory: number
  uploaded: number
  requirements: Array<{ documentType: string; mandatory: boolean; uploaded: boolean }>
}

export interface ClaimRegisterPayload {
  claimType: string
  claimDate: string
  causeOfClaim?: string
  description?: string
  memberId?: string
  claimantDetails?: Record<string, unknown>
  benefitType?: string
}

export interface MedicalRequirePayload {
  reason?: string
}

export interface MedicalResultPayload {
  result: "CLEARED" | "REJECTED" | "LOADING"
  reason?: string
  loadingFactor?: string | number
  loadingPercentage?: string | number
}

export interface ClaimAssessmentPayload {
  assessedAmount: string | number
  assessmentNotes: string
  fraudFlag?: boolean
  fraudFlagReason?: string
  waiverOfPremiumDays?: number
}

export interface ClaimRequisitionPayload {
  bankDetails?: Record<string, unknown>
  narration?: string
}

export interface ClaimSettlementPayload {
  paymentReference: string
  paymentStatus?: string
}

export interface ClaimActionResult {
  claim?: ClaimDetail
  requisition?: ClaimRequisition
  [key: string]: unknown
}

export interface ClaimPrintResult {
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
  const value = pick(row, ...keys)
  if (value === undefined || value === null || value === "") return "0.00"
  return typeof value === "number" ? value.toFixed(2) : String(value)
}

function arrayValue(row: Record<string, unknown>, ...keys: string[]): unknown[] {
  const value = pick<unknown>(row, ...keys)
  return Array.isArray(value) ? value : []
}

function numberValue(row: Record<string, unknown>, ...keys: string[]): number {
  const value = pick(row, ...keys)
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : 0
}

function booleanValue(row: Record<string, unknown>, ...keys: string[]): boolean {
  return Boolean(pick(row, ...keys) ?? false)
}

export function normalizeClaim(row: Record<string, unknown>): ClaimRecord {
  const policyholderDisplay = stringValue(row, "policyholderDisplay", "policyholder_display", "policyholderName", "policyholder_name", "partnerDisplay", "partner_display")
  return {
    ...row,
    id: stringValue(row, "id", "uuid"),
    claimNumber: stringValue(row, "claimNumber", "claim_number"),
    policyId: nullableString(row, "policyId", "policy_id") ?? undefined,
    policyNumber: stringValue(row, "policyNumber", "policy_number"),
    policyholderName: stringValue(row, "policyholderName", "policyholder_name", "partnerDisplay", "partner_display"),
    policyholderDisplay,
    productDisplay: stringValue(row, "productDisplay", "product_display", "productName", "product_name"),
    claimType: stringValue(row, "claimType", "claim_type"),
    claimDate: nullableString(row, "claimDate", "claim_date"),
    admittedDate: nullableString(row, "admittedDate", "admitted_date"),
    amount: amountValue(row, "amount"),
    currency: stringValue(row, "currency") || "TZS",
    status: stringValue(row, "status").toUpperCase(),
    statusDisplay: stringValue(row, "statusDisplay", "status_display", "status"),
    fraudFlag: booleanValue(row, "fraudFlag", "fraud_flag"),
    allowedActions: arrayValue(row, "allowedActions", "allowed_actions").map(String),
    createdAt: nullableString(row, "createdAt", "created_at"),
    updatedAt: nullableString(row, "updatedAt", "updated_at"),
  }
}

function normalizeClaimant(row: Record<string, unknown>): ClaimantInfo {
  return {
    id: nullableString(row, "id") ?? undefined,
    claimantType: stringValue(row, "claimantType", "claimant_type"),
    claimantTypeDisplay: stringValue(row, "claimantTypeDisplay", "claimant_type_display", "claimant_type"),
    relationship: stringValue(row, "relationship"),
    name: stringValue(row, "name"),
    identityNumber: stringValue(row, "identityNumber", "identity_number"),
    age: pick<number | null>(row, "age") ?? null,
    gender: stringValue(row, "gender"),
  }
}

function normalizeItem(row: Record<string, unknown>): ClaimItem {
  return {
    id: stringValue(row, "id"),
    benefitType: stringValue(row, "benefitType", "benefit_type"),
    sumAssured: amountValue(row, "sumAssured", "sum_assured"),
    calculatedAmount: amountValue(row, "calculatedAmount", "calculated_amount"),
    approvedAmount: nullableString(row, "approvedAmount", "approved_amount"),
    adjustmentReason: stringValue(row, "adjustmentReason", "adjustment_reason"),
  }
}

function normalizeDocument(row: Record<string, unknown>): ClaimDocument {
  return {
    id: stringValue(row, "id"),
    documentType: stringValue(row, "documentType", "document_type"),
    fileReference: stringValue(row, "fileReference", "file_reference"),
    mandatoryFlag: booleanValue(row, "mandatoryFlag", "mandatory_flag"),
    uploadedByDisplay: stringValue(row, "uploadedByDisplay", "uploaded_by_display", "uploaded_by"),
    uploadedAt: nullableString(row, "uploadedAt", "uploaded_at", "upload_date"),
  }
}

function normalizeFileNote(row: Record<string, unknown>): ClaimFileNote {
  return {
    id: stringValue(row, "id"),
    noteText: stringValue(row, "noteText", "note_text"),
    authorDisplay: stringValue(row, "authorDisplay", "author_display", "author"),
    sourceChannel: stringValue(row, "sourceChannel", "source_channel"),
    createdAt: nullableString(row, "createdAt", "created_at"),
  }
}

function normalizeRequisition(row: Record<string, unknown>): ClaimRequisition {
  const rawBank = pick<unknown>(row, "bankDetailsJson", "bank_details_json", "bank_details")
  return {
    id: stringValue(row, "id"),
    requisitionNumber: stringValue(row, "requisitionNumber", "requisition_number"),
    amount: amountValue(row, "amount"),
    bankDetailsJson: isRecord(rawBank) ? rawBank : {},
    paymentRequisitionNumber: nullableString(row, "paymentRequisitionNumber", "payment_requisition_number"),
    approvalRequestStatus: nullableString(row, "approvalRequestStatus", "approval_request_status"),
    approvalRequired: booleanValue(row, "approvalRequired", "approval_required"),
    narration: stringValue(row, "narration"),
    status: stringValue(row, "status"),
    statusDisplay: stringValue(row, "statusDisplay", "status_display", "status"),
    createdAt: nullableString(row, "createdAt", "created_at"),
    updatedAt: nullableString(row, "updatedAt", "updated_at"),
  }
}

function normalizeLoanOffset(row: Record<string, unknown>): ClaimLoanOffset {
  return {
    id: nullableString(row, "id") ?? undefined,
    grossAmount: amountValue(row, "grossAmount", "gross_amount"),
    offsetAmount: amountValue(row, "offsetAmount", "offset_amount"),
    netPayout: amountValue(row, "netPayout", "net_payout"),
    status: stringValue(row, "status"),
    loanBreakdown: arrayValue(row, "loanBreakdown", "loan_breakdown").filter(isRecord),
  }
}

function normalizeAuditEntry(row: Record<string, unknown>): ClaimAuditEntry {
  return {
    id: stringValue(row, "id", "event_id"),
    action: stringValue(row, "action", "event_type", "action_type"),
    actorDisplay: stringValue(row, "actorDisplay", "actor_display", "actorName", "actor_name", "actor"),
    sourceChannel: stringValue(row, "sourceChannel", "source_channel"),
    reason: stringValue(row, "reason"),
    createdAt: nullableString(row, "createdAt", "created_at"),
  }
}

export function normalizeClaimFinancialSummary(row: Record<string, unknown>): ClaimFinancialSummary {
  return {
    claimNumber: stringValue(row, "claimNumber", "claim_number"),
    policyNumber: stringValue(row, "policyNumber", "policy_number"),
    currency: stringValue(row, "currency") || "TZS",
    grossAmount: amountValue(row, "grossAmount", "gross_amount"),
    loanOffset: amountValue(row, "loanOffset", "loan_offset"),
    netPayout: amountValue(row, "netPayout", "net_payout"),
    loanOffsetApplied: booleanValue(row, "loanOffsetApplied", "loan_offset_applied"),
    loanBreakdown: arrayValue(row, "loanBreakdown", "loan_breakdown").filter(isRecord),
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
    page: Number(record.page ?? (isRecord(record.pagination) ? record.pagination.page : undefined) ?? 1),
    pageSize: Number(record.pageSize ?? record.page_size ?? results.length),
  }
}

export function normalizeClaimDetail(payload: unknown): ClaimDetail {
  const record = isRecord(payload) ? payload : {}
  const claim = normalizeClaim(record)
  const rawClaimant = pick<unknown>(record, "claimant")
  const rawRequisition = pick<unknown>(record, "requisition")
  const rawLoanOffset = pick<unknown>(record, "loanOffset", "loan_offset")
  const rawFinancial = pick<unknown>(record, "financialSummary", "financial_summary")
  return {
    ...claim,
    causeOfClaim: stringValue(record, "causeOfClaim", "cause_of_claim"),
    description: stringValue(record, "description"),
    assessmentNotes: stringValue(record, "assessmentNotes", "assessment_notes"),
    fraudFlagReason: stringValue(record, "fraudFlagReason", "fraud_flag_reason"),
    waiverOfPremiumDays: numberValue(record, "waiverOfPremiumDays", "waiver_of_premium_days"),
    waiverOfPremiumUntil: nullableString(record, "waiverOfPremiumUntil", "waiver_of_premium_until"),
    waiverOfPremiumApplied: booleanValue(record, "waiverOfPremiumApplied", "waiver_of_premium_applied"),
    settledDate: nullableString(record, "settledDate", "settled_date"),
    settlementAmount: nullableString(record, "settlementAmount", "settlement_amount"),
    paymentReference: stringValue(record, "paymentReference", "payment_reference"),
    sourceChannel: stringValue(record, "sourceChannel", "source_channel"),
    sourceChannelDisplay: stringValue(record, "sourceChannelDisplay", "source_channel_display", "source_channel"),
    medicalStatus: stringValue(record, "medicalStatus", "medical_status"),
    medicalStatusDisplay: stringValue(record, "medicalStatusDisplay", "medical_status_display", "medical_status"),
    medicalResult: stringValue(record, "medicalResult", "medical_result"),
    medicalReason: stringValue(record, "medicalReason", "medical_reason"),
    medicalRequestedAt: nullableString(record, "medicalRequestedAt", "medical_requested_at"),
    medicalReviewedByDisplay: stringValue(record, "medicalReviewedByDisplay", "medical_reviewed_by_display"),
    medicalReviewedAt: nullableString(record, "medicalReviewedAt", "medical_reviewed_at"),
    medicalLoadingFactor: nullableString(record, "medicalLoadingFactor", "medical_loading_factor"),
    registeredByDisplay: stringValue(record, "registeredByDisplay", "registered_by_display"),
    admittedByDisplay: stringValue(record, "admittedByDisplay", "admitted_by_display"),
    claimant: isRecord(rawClaimant) ? normalizeClaimant(rawClaimant) : null,
    items: arrayValue(record, "items").filter(isRecord).map(normalizeItem),
    documents: arrayValue(record, "documents").filter(isRecord).map(normalizeDocument),
    fileNotes: arrayValue(record, "fileNotes", "file_notes").filter(isRecord).map(normalizeFileNote),
    requisition: isRecord(rawRequisition) ? normalizeRequisition(rawRequisition) : null,
    loanOffset: isRecord(rawLoanOffset) ? normalizeLoanOffset(rawLoanOffset) : null,
    policyContext: isRecord(record.policyContext ?? record.policy_context) ? (record.policyContext ?? record.policy_context) as Record<string, unknown> : undefined,
    financialSummary: isRecord(rawFinancial) ? normalizeClaimFinancialSummary(rawFinancial) : null,
    auditTimeline: arrayValue(record, "auditTimeline", "audit_timeline").filter(isRecord).map(normalizeAuditEntry),
  }
}

export function normalizeClaimKpis(payload: unknown): ClaimKpis {
  const record = isRecord(payload) ? payload : {}
  const rawTotals = isRecord(record.currencyTotals ?? record.currency_totals) ? record.currencyTotals ?? record.currency_totals : undefined
  return {
    totalClaims: numberValue(record, "totalClaims", "total_claims"),
    outstandingAmount: amountValue(record, "outstandingAmount", "outstanding_amount"),
    settledAmountPeriod: amountValue(record, "settledAmountPeriod", "settled_amount_period"),
    pendingAssessmentCount: numberValue(record, "pendingAssessmentCount", "pending_assessment_count"),
    currency: stringValue(record, "currency") || "TZS",
    currencyTotals: rawTotals as Record<string, Record<string, string>> | undefined,
    timestamp: stringValue(record, "timestamp"),
  }
}

export function normalizeClaimDocuments(payload: unknown): ClaimDocumentsResult {
  const record = isRecord(payload) ? payload : {}
  const rows = arrayValue(record, "results", "documents", "items").filter(isRecord)
  const requirements = arrayValue(record, "requirements").filter(isRecord).map((item) => ({
    documentType: stringValue(item, "documentType", "document_type"),
    mandatory: booleanValue(item, "mandatory"),
    uploaded: booleanValue(item, "uploaded"),
  }))
  return {
    claimNumber: stringValue(record, "claimNumber", "claim_number"),
    results: rows.map(normalizeDocument),
    documents: rows.map(normalizeDocument),
    requiredDocumentTypes: arrayValue(record, "requiredDocumentTypes", "required_document_types").map(String),
    missingDocumentTypes: arrayValue(record, "missingDocumentTypes", "missing_document_types").map(String),
    allMandatoryUploaded: booleanValue(record, "allMandatoryUploaded", "all_mandatory_uploaded"),
    mandatory: numberValue(record, "mandatory"),
    uploaded: numberValue(record, "uploaded"),
    requirements,
  }
}

function normalizeClaimActionResult(payload: unknown): ClaimActionResult {
  const record = isRecord(payload) ? payload : {}
  const rawClaim = pick<unknown>(record, "claim")
  const rawRequisition = pick<unknown>(record, "requisition")
  return {
    ...record,
    claim: isRecord(rawClaim) ? normalizeClaimDetail(rawClaim) : undefined,
    requisition: isRecord(rawRequisition) ? normalizeRequisition(rawRequisition) : undefined,
  }
}

export function buildClaimQuery(filters: ClaimListFilters = {}): string {
  const params: QueryParams = {
    page: filters.page,
    page_size: filters.pageSize,
    q: filters.search,
    ordering: filters.ordering,
    sort: filters.sort,
    status: filters.status,
    claim_type: filters.claimType,
    product: filters.product,
    branch: filters.branch,
    fraud_flag: filters.fraudFlag,
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

export function listClaims(filters: ClaimListFilters = {}): Promise<Paginated<ClaimRecord>> {
  return request<unknown>(`${CLAIMS_API_PREFIX}/${buildClaimQuery(filters)}`).then((payload) => normalizePaginated(payload, normalizeClaim))
}

export function getClaimKpis(filters: ClaimListFilters = {}): Promise<ClaimKpis> {
  return request<unknown>(`${CLAIMS_API_PREFIX}/kpis/${buildClaimQuery(filters)}`).then(normalizeClaimKpis)
}

export function getClaimOptions(kind: ClaimOptionKind, params: { q?: string; page?: number; pageSize?: number; policyId?: string } = {}): Promise<Paginated<ClaimOption>> {
  const search = new URLSearchParams()
  if (params.q) search.set("q", params.q)
  if (params.page) search.set("page", String(params.page))
  if (params.pageSize) search.set("page_size", String(params.pageSize))
  if (params.policyId) search.set("policy_id", params.policyId)
  const query = search.toString()
  return request<unknown>(`${CLAIMS_API_PREFIX}/options/${encodeURIComponent(kind)}/${query ? `?${query}` : ""}`).then((payload) => normalizePaginated(payload))
}

export function registerClaim(policyId: string, payload: ClaimRegisterPayload, idempotencyKey?: string): Promise<ClaimActionResult> {
  return request<unknown>(`${POLICY_CLAIMS_API_PREFIX}/${encodeURIComponent(policyId)}/claims/`, {
    method: "POST",
    headers: withIdempotencyKey(idempotencyKey),
    body: JSON.stringify({
      claim_type: payload.claimType,
      claim_date: payload.claimDate,
      cause_of_claim: payload.causeOfClaim ?? "",
      description: payload.description ?? "",
      member_id: payload.memberId ?? null,
      claimant_details: payload.claimantDetails ?? {},
      benefit_type: payload.benefitType ?? "",
    }),
  }).then((payload) => normalizeClaimActionResult(payload))
}

export function getClaim(id: string): Promise<ClaimDetail> {
  return request<unknown>(`${CLAIMS_API_PREFIX}/${encodeURIComponent(id)}/`).then(normalizeClaimDetail)
}

export function listClaimDocuments(id: string, params: { page?: number; pageSize?: number } = {}): Promise<ClaimDocumentsResult> {
  const search = new URLSearchParams()
  if (params.page) search.set("page", String(params.page))
  if (params.pageSize) search.set("page_size", String(params.pageSize))
  const query = search.toString()
  return request<unknown>(`${CLAIMS_API_PREFIX}/${encodeURIComponent(id)}/documents/${query ? `?${query}` : ""}`).then(normalizeClaimDocuments)
}

export function uploadClaimDocument(id: string, documentType: string, file: File, fileReference = "", idempotencyKey?: string): Promise<ClaimDocumentsResult> {
  const form = new FormData()
  form.append("document_type", documentType)
  form.append("file", file)
  if (fileReference) form.append("file_reference", fileReference)
  return request<unknown>(`${CLAIMS_API_PREFIX}/${encodeURIComponent(id)}/documents/`, {
    method: "POST",
    headers: withIdempotencyKey(idempotencyKey),
    body: form,
  }).then(normalizeClaimDocuments)
}

export function requireMedicalReview(id: string, reason = ""): Promise<ClaimDetail> {
  return request<unknown>(`${CLAIMS_API_PREFIX}/${encodeURIComponent(id)}/medical/require/`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  }).then(normalizeClaimDetail)
}

export function submitMedicalResult(id: string, payload: MedicalResultPayload): Promise<ClaimDetail> {
  return request<unknown>(`${CLAIMS_API_PREFIX}/${encodeURIComponent(id)}/medical/result/`, {
    method: "POST",
    body: JSON.stringify({
      result: payload.result,
      reason: payload.reason ?? "",
      loading_factor: payload.loadingFactor ?? null,
      loading_percentage: payload.loadingPercentage ?? null,
    }),
  }).then(normalizeClaimDetail)
}

export function assessClaim(id: string, payload: ClaimAssessmentPayload): Promise<ClaimDetail> {
  return request<unknown>(`${CLAIMS_API_PREFIX}/${encodeURIComponent(id)}/assess/`, {
    method: "POST",
    body: JSON.stringify({
      assessed_amount: payload.assessedAmount,
      assessment_notes: payload.assessmentNotes,
      fraud_flag: payload.fraudFlag ?? false,
      fraud_flag_reason: payload.fraudFlagReason ?? "",
      waiver_of_premium_days: payload.waiverOfPremiumDays ?? 0,
    }),
  }).then(normalizeClaimDetail)
}

export function addClaimFileNote(id: string, noteText: string): Promise<ClaimFileNote> {
  return request<unknown>(`${CLAIMS_API_PREFIX}/${encodeURIComponent(id)}/notes/`, {
    method: "POST",
    body: JSON.stringify({ note_text: noteText }),
  }).then((payload) => normalizeFileNote(isRecord(payload) ? payload : {}))
}

export function listClaimNotes(id: string): Promise<ClaimFileNote[]> {
  return request<unknown>(`${CLAIMS_API_PREFIX}/${encodeURIComponent(id)}/notes/`).then((payload) => arrayValue(isRecord(payload) ? payload : { notes: Array.isArray(payload) ? payload : [] }, "notes").filter(isRecord).map(normalizeFileNote))
}

export function getClaimFinancialSummary(id: string): Promise<ClaimFinancialSummary> {
  return request<unknown>(`${CLAIMS_API_PREFIX}/${encodeURIComponent(id)}/financial-summary/`).then((payload) => normalizeClaimFinancialSummary(isRecord(payload) ? payload : {}))
}

export function raiseClaimRequisition(id: string, payload: ClaimRequisitionPayload): Promise<ClaimActionResult> {
  return request<unknown>(`${CLAIMS_API_PREFIX}/${encodeURIComponent(id)}/raise-requisition/`, {
    method: "POST",
    body: JSON.stringify({
      bank_details: payload.bankDetails ?? {},
      narration: payload.narration ?? "",
    }),
  }).then((payload) => normalizeClaimActionResult(isRecord(payload) ? payload : { requisition: payload }))
}

export function settleClaim(id: string, payload: ClaimSettlementPayload): Promise<ClaimActionResult> {
  return request<unknown>(`${CLAIMS_API_PREFIX}/${encodeURIComponent(id)}/settle/`, {
    method: "POST",
    body: JSON.stringify({
      payment_reference: payload.paymentReference,
      payment_status: payload.paymentStatus ?? "CONFIRMED",
    }),
  }).then(normalizeClaimActionResult)
}

export function printClaimDischargeVoucher(id: string): Promise<ClaimPrintResult> {
  return request<ClaimPrintResult>(`${CLAIMS_API_PREFIX}/${encodeURIComponent(id)}/print-discharge-voucher/`, {
    method: "POST",
  })
}
