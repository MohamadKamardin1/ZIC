/**
 * OL Proposals — API types, fetchers, and normalizers.
 *
 * Every fetcher goes through the shared ``request`` client so failures surface
 * as ``ApiClientError`` with the backend structured error shape attached
 * (``error_code``, ``resolution_steps``, ``details.checklist``) for ErrorCoach.
 * Display payloads carry names — never raw UUIDs.
 */

import { buildTableQuery, request, type TableQuery } from "./apiClient"

const BASE = "/api/v1/ol-proposals"
const CREATE_BASE = "/api/v1/ol/proposals"

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type ProposalAction =
  | "view"
  | "enrich"
  | "upload_documents"
  | "mark_payment_ready"
  | "convert"
  | "cancel"
  | "print"
  | (string & {})

export interface ProposalListItem {
  id: string
  proposalNumber: string
  status: string
  partnerName: string
  productName?: string
  quotationNumber?: string
  employerName?: string
  premiumAmount?: number | null
  currency?: string
  expiryDate?: string | null
  medicalRequired?: boolean
  createdAt?: string | null
}

export interface ChecklistItem {
  key: string
  passed: boolean
  errorCode: string
  message: string
  resolutionSteps: string[]
  deepLink?: string
}

export interface ReadinessReport {
  passed: boolean
  items: ChecklistItem[]
  status?: string
  expiryDate?: string | null
}

export interface BeneficiaryRecord {
  id: string
  personName: string
  sharePercent: number
  isPrimary: boolean
  isMinor?: boolean
  identityType?: string
  identityNumber?: string
}

export interface ProposalAllocationRow {
  receiptReference: string
  amount: number
  paymentMode?: string
  currency?: string
  allocatedAt?: string | null
}

export interface FirstPremiumStatusShape {
  linked: boolean
  commitmentNumber?: string
  commitmentId?: string
  commitmentStatus?: string
  amountDue?: number | null
  amountPaid?: number | null
  balance?: number | null
  currency?: string
  lastPaymentDate?: string | null
  allocations: ProposalAllocationRow[]
  posted: boolean
  nextActions: string[]
}

export interface ProposalDocumentRecord {
  id: string
  documentType: string
  documentTypeDisplay?: string
  status: string
  fileReference?: string
}

export interface ProposalDetail extends ProposalListItem {
  beneficiaries: BeneficiaryRecord[]
  documents: ProposalDocumentRecord[]
  allowedActions: ProposalAction[]
  readiness: ReadinessReport | null
  firstPremium: FirstPremiumStatusShape | null
}

export interface ProposalListFilters extends TableQuery {
  status?: string
}

export interface ProposalKPIs {
  total: number
  byStatus: Record<string, number>
}

// ---------------------------------------------------------------------------
// Defensive pick helpers (backend keys are snake_case)
// ---------------------------------------------------------------------------

type Raw = Record<string, unknown>

function asRecord(value: unknown): Raw {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Raw) : {}
}

function str(source: unknown, ...keys: string[]): string | undefined {
  const record = asRecord(source)
  for (const key of keys) {
    const value = record[key]
    if (typeof value === "string" && value.trim()) return value
    if (typeof value === "number") return String(value)
  }
  return undefined
}

function num(source: unknown, ...keys: string[]): number | null {
  const record = asRecord(source)
  for (const key of keys) {
    const value = record[key]
    if (typeof value === "number" && Number.isFinite(value)) return value
    if (typeof value === "string" && value.trim() !== "" && Number.isFinite(Number(value))) return Number(value)
  }
  return null
}

function bool(source: unknown, ...keys: string[]): boolean {
  const record = asRecord(source)
  for (const key of keys) {
    if (typeof record[key] === "boolean") return record[key] as boolean
  }
  return false
}

function strArray(source: unknown, ...keys: string[]): string[] {
  const record = asRecord(source)
  for (const key of keys) {
    const value = record[key]
    if (Array.isArray(value)) return value.map((item) => String(item))
  }
  return []
}

// ---------------------------------------------------------------------------
// Normalizers
// ---------------------------------------------------------------------------

export function normalizeChecklistItem(raw: unknown): ChecklistItem {
  const record = asRecord(raw)
  const steps = Array.isArray(record.resolution_steps) ? record.resolution_steps.map(String) : []
  return {
    key: str(record, "key") ?? "",
    passed: bool(record, "passed"),
    errorCode: str(record, "error_code") ?? "",
    message: str(record, "message") ?? "",
    resolutionSteps: steps,
    deepLink: str(record, "deep_link", "deepLink"),
  }
}

export function normalizeReadiness(raw: unknown): ReadinessReport {
  const record = asRecord(raw)
  const items = Array.isArray(record.items) ? record.items.map(normalizeChecklistItem) : []
  return {
    passed: bool(record, "passed"),
    items,
    status: str(record, "status"),
    expiryDate: str(record, "expiry_date", "expiryDate") ?? null,
  }
}

/**
 * Translate a backend checklist ``deep_link`` ("/proposals/{id}/documents")
 * into an in-app route ("/ordinary-life/proposals/{id}/documents"). Without a
 * proposal id the operator lands on the proposals list instead of a broken URL.
 */
export function proposalDeepLink(deepLink?: string | null, id?: string | null): string | undefined {
  if (!deepLink) return undefined
  const base = "/ordinary-life/proposals"
  const match = deepLink.trim().match(/^\/proposals(?:\/(\{id\}|[^/]+))?(\/.*)?$/)
  if (!match) {
    if (deepLink.startsWith("/") && !/^https?:/i.test(deepLink)) return deepLink
    return undefined
  }
  if (!id) return base
  return `${base}/${id}${match[2] ?? ""}`
}

export function normalizeFirstPremium(raw: unknown): FirstPremiumStatusShape {
  const record = asRecord(raw)
  const commitment = asRecord(record.commitment)
  const allocationsRaw = Array.isArray(commitment.allocations) ? commitment.allocations : []
  return {
    linked: bool(record, "linked"),
    commitmentNumber: str(commitment, "commitment_number"),
    commitmentId: str(commitment, "commitment_id", "id"),
    commitmentStatus: str(commitment, "status"),
    amountDue: num(commitment, "amount_due"),
    amountPaid: num(commitment, "amount_paid"),
    balance: num(commitment, "balance"),
    currency: str(commitment, "currency"),
    lastPaymentDate: str(commitment, "last_payment_date") ?? null,
    allocations: allocationsRaw.map((row) => {
      const item = asRecord(row)
      return {
        receiptReference: str(item, "receipt_reference") ?? "—",
        amount: num(item, "amount") ?? 0,
        paymentMode: str(item, "payment_mode"),
        currency: str(item, "currency"),
        allocatedAt: str(item, "allocated_at") ?? null,
      }
    }),
    posted: bool(record, "first_premium_posted"),
    nextActions: strArray(record, "next_actions"),
  }
}

export function normalizeProposalListItem(raw: unknown): ProposalListItem {
  const record = asRecord(raw)
  return {
    id: str(record, "id") ?? "",
    proposalNumber: str(record, "proposal_number", "proposalNumber") ?? "—",
    status: str(record, "status") ?? "",
    partnerName: str(record, "partner_name", "partnerName") ?? str(record, "partner_display") ?? "—",
    productName: str(record, "product_name", "productName", "plan_display"),
    quotationNumber: str(record, "quotation_number", "quotationNumber"),
    employerName: str(record, "employer_name_snapshot", "employer_name"),
    premiumAmount: num(record, "premium_amount", "premiumAmount"),
    currency: str(record, "currency"),
    expiryDate: str(record, "expiry_date", "expiryDate") ?? null,
    medicalRequired: bool(record, "medical_required"),
    createdAt: str(record, "created_at") ?? null,
  }
}

export function normalizeAllowedActions(raw: unknown): ProposalAction[] {
  if (Array.isArray(raw)) return raw.map((item) => String(item))
  if (raw && typeof raw === "object") {
    return Object.entries(asRecord(raw))
      .filter(([, enabled]) => enabled === true)
      .map(([action]) => action)
  }
  return []
}

export function normalizeProposalDetail(raw: unknown): ProposalDetail {
  const base = normalizeProposalListItem(raw)
  const record = asRecord(raw)
  const beneficiaries = Array.isArray(record.beneficiaries) ? record.beneficiaries : []
  const documents = Array.isArray(record.documents) ? record.documents : []
  return {
    ...base,
    employerName: base.employerName ?? str(record, "employer_partner_name"),
    beneficiaries: beneficiaries.map((row) => {
      const item = asRecord(row)
      return {
        id: str(item, "id") ?? "",
        personName: str(item, "person_name") ?? "—",
        sharePercent: num(item, "share_percent") ?? 0,
        isPrimary: bool(item, "is_primary"),
        isMinor: bool(item, "is_minor"),
        identityType: str(item, "identity_type"),
        identityNumber: str(item, "identity_number"),
      }
    }),
    documents: documents.map((row) => {
      const item = asRecord(row)
      return {
        id: str(item, "id") ?? "",
        documentType: str(item, "document_type") ?? "",
        documentTypeDisplay: str(item, "document_type_display"),
        status: str(item, "status") ?? "",
        fileReference: str(item, "file_reference"),
      }
    }),
    allowedActions: normalizeAllowedActions(record.allowed_actions),
    readiness: record.readiness ? normalizeReadiness(record.readiness) : null,
    firstPremium: record.first_premium ? normalizeFirstPremium(record.first_premium) : null,
  }
}

export interface Paginated<T> {
  results: T[]
  count: number
}

/** Accept both `{count, results}` DRF pages and bare arrays. */
export function normalizePaginated<T>(payload: unknown, mapRow: (row: unknown) => T): Paginated<T> {
  const record = asRecord(payload)
  const rows = Array.isArray(payload) ? payload : Array.isArray(record.results) ? record.results : []
  const count = typeof record.count === "number" ? record.count : rows.length
  return { results: rows.map(mapRow), count }
}

export function normalizeKPIs(payload: unknown): ProposalKPIs {
  const record = asRecord(payload)
  const byStatus: Record<string, number> = {}
  for (const [key, value] of Object.entries(record)) {
    if (typeof value === "number" && key !== "total") byStatus[key] = value
  }
  const nested = asRecord(record.by_status ?? record.statuses)
  for (const [key, value] of Object.entries(nested)) {
    if (typeof value === "number") byStatus[key] = value
  }
  let total = num(record, "total") ?? 0
  if (!total) total = Object.values(byStatus).reduce((sum, value) => sum + value, 0)
  return { total, byStatus }
}

// ---------------------------------------------------------------------------
// Fetchers
// ---------------------------------------------------------------------------

export async function listProposals(filters: ProposalListFilters = {}) {
  return request<unknown>(`${BASE}/proposals/${buildTableQuery(filters)}`)
}

export async function getProposalKPIs() {
  return request<unknown>(`${BASE}/proposals/kpis/`)
}

export async function getProposal(id: string) {
  return request<unknown>(`${BASE}/proposals/${id}/`)
}

export async function createProposalFromQuotation(quotationId: string) {
  return request<unknown>(`${CREATE_BASE}/from-quotation/${quotationId}/`, { method: "POST" })
}

export async function enrichProposalSection(id: string, section: string, data: Record<string, unknown>) {
  return request<unknown>(`${BASE}/proposals/${id}/enrich/`, {
    method: "PATCH",
    body: JSON.stringify({ section, ...data }),
  })
}

export async function addBeneficiary(id: string, data: Record<string, unknown>) {
  return request<unknown>(`${BASE}/proposals/${id}/beneficiaries/`, {
    method: "POST",
    body: JSON.stringify(data),
  })
}

export async function updateBeneficiary(id: string, beneficiaryId: string, data: Record<string, unknown>) {
  return request<unknown>(`${BASE}/proposals/${id}/beneficiaries/${beneficiaryId}/`, {
    method: "PATCH",
    body: JSON.stringify(data),
  })
}

export async function deleteBeneficiary(id: string, beneficiaryId: string) {
  return request<unknown>(`${BASE}/proposals/${id}/beneficiaries/${beneficiaryId}/`, { method: "DELETE" })
}

export async function listProposalDocuments(id: string) {
  return request<unknown>(`${BASE}/proposals/${id}/documents/`)
}

export async function uploadProposalDocument(id: string, data: Record<string, unknown>) {
  return request<unknown>(`${BASE}/proposals/${id}/documents/`, {
    method: "POST",
    body: JSON.stringify(data),
  })
}

export async function getHealthQuestions(id: string) {
  return request<unknown>(`${BASE}/proposals/${id}/health-questions/`)
}

export async function submitHealthAnswers(id: string, answers: Array<Record<string, unknown>>) {
  return request<unknown>(`${BASE}/proposals/${id}/health-answers/`, {
    method: "POST",
    body: JSON.stringify({ answers }),
  })
}

export async function submitUnderwritingDecision(
  id: string,
  data: { decision: string; reason?: string },
) {
  return request<unknown>(`${BASE}/proposals/${id}/underwriting-decision/`, {
    method: "POST",
    body: JSON.stringify(data),
  })
}

export async function getPaymentReadiness(id: string) {
  return request<unknown>(`${BASE}/proposals/${id}/payment-readiness/`)
}

export async function markPaymentReady(id: string) {
  return request<unknown>(`${BASE}/proposals/${id}/mark-payment-ready/`, { method: "POST" })
}

export async function getFirstPremiumStatus(id: string) {
  return request<unknown>(`${BASE}/proposals/${id}/first-premium/`)
}

export async function convertToPolicy(id: string) {
  return request<unknown>(`${BASE}/proposals/${id}/convert/`, { method: "POST" })
}

export async function cancelProposal(id: string, reason: string) {
  return request<unknown>(`${BASE}/proposals/${id}/cancel/`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  })
}

export async function reactivateProposal(id: string) {
  return request<unknown>(`${BASE}/proposals/${id}/reactivate/`, { method: "POST" })
}

export interface PrintResult {
  fileName: string
  blobUrl: string
}

export async function printProposal(id: string): Promise<PrintResult> {
  const response = await fetch(`${BASE}/proposals/${id}/print/?format=pdf`, {
    headers: {
      Authorization: `Bearer ${localStorage.getItem("aims_access_token") ?? sessionStorage.getItem("aims_access_token") ?? ""}`,
      Accept: "application/pdf",
    },
  })
  if (!response.ok) throw await (await import("./apiClient")).normalizeResponseError(response)
  const blob = await response.blob()
  return {
    fileName: `proposal-${id}.pdf`,
    blobUrl: URL.createObjectURL(blob),
  }
}

export async function listGeneratedDocuments(id: string) {
  const payload = await listProposalDocuments(id)
  const record = asRecord(payload)
  const rows = Array.isArray(payload) ? payload : Array.isArray(record.results) ? record.results : []
  return rows
    .map((row) => asRecord(row))
    .filter((item) => str(item, "status") === "GENERATED")
    .map((item) => ({
      id: str(item, "id") ?? "",
      documentType: str(item, "document_type") ?? "",
      documentTypeDisplay: str(item, "document_type_display") ?? str(item, "document_type") ?? "",
      status: str(item, "status") ?? "",
      fileReference: str(item, "file_reference"),
    }))
}

export async function getProposalOptions(kind: string) {
  return request<unknown>(`${BASE}/proposals/options/${encodeURIComponent(kind)}/`)
}
