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
const QUOTATIONS_BASE = "/api/v1/ol/quotations/quotations"

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
  statusName?: string
  partnerName: string
  agentName?: string
  employerName?: string
  productName?: string
  planName?: string
  quotationNumber?: string
  totalPremium?: number | null
  currency?: string
  expiryDate?: string | null
  medicalRequired?: boolean
  createdAt?: string | null
  paymentReady: boolean
  firstPremiumPosted: boolean
  allowedActions: ProposalAction[]
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
  beneficialTypeName?: string
  guardianName?: string
  guardianRelationship?: string
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
  mandatory?: boolean
  uploadedAt?: string
}

export interface ProposalDocumentRequirement {
  code: string
  name: string
  documentType: string
  mandatory: boolean
}

export interface OLHealthQuestion {
  id: string
  questionId: string
  sequence: number
  mandatory: boolean
  triggerMedicalRequirement: boolean
  questionCode: string
  questionText: string
  answerType: string
  category?: string | null
  underwritingImpact?: string | null
}

export interface OLHealthQuestionnairePayload {
  questionnaire: string | null
  questions: OLHealthQuestion[]
}

// --- Carried quotation children (detail payload) ---

export interface ProposalPlanConfigRow {
  id: string
  planName: string
  subProductCode?: string
  sectionNumber?: string
  baseSumAssured?: number | null
  termYears?: number | null
  paymentPeriodYears?: number | null
  premiumFrequency?: string
  quoteBasis?: string
  estimatedMaturityValue?: number | null
  premiumAmount?: number | null
  isSelected: boolean
}

export interface ProposalMemberRow {
  id: string
  memberType?: string
  fullName: string
  identityNumber?: string
  dateOfBirth?: string | null
  ageAtQuote?: number | null
  gender?: string
  smokerStatus?: string
  relationship?: string
  memberSumAssured?: number | null
  coverageBasis?: string
}

export interface ProposalInstallmentRow {
  id: string
  frequency?: string
  numberOfInstallments?: number | null
  installmentAmount?: number | null
  firstDueDate?: string | null
  currency?: string
  isSelected: boolean
}

export interface ProposalFundRow {
  id: string
  fundName: string
  allocationPercentage?: number | null
  allocationAmount?: number | null
  isSelected: boolean
}

export interface ProposalRiderRow {
  id: string
  riderName: string
  riderSumAssured?: number | null
  riderTermYears?: number | null
  benefitBasis?: string
  benefitValue?: number | null
  premiumAmount?: number | null
  isSelected: boolean
}

export interface ProposalBenefitRow {
  id: string
  code?: string
  name: string
  benefitType?: string
  basis?: string
  value?: number | null
  sumAssured?: number | null
  premiumAmount?: number | null
  isSelected: boolean
}

export interface ProposalQuotationVersionRow {
  versionNumber: number
  status?: string
  changeReason?: string
  createdAt?: string | null
}

export interface ProposalCompleteness {
  missing: string[]
  requiredMissing: string[]
  complete: boolean
}

export interface ProposalDetail extends ProposalListItem {
  quotationId?: string
  quotationVersion?: number | null
  agentPartnerId?: string
  employerPartnerId?: string
  underwritingStatus?: string
  reasonCode?: string
  reasonText?: string
  sourceChannel?: string
  employmentReference?: string
  payrollDeduction?: boolean | null
  intermediaryChannel?: string
  declarationPep: boolean | null
  declarationAml: boolean | null
  existingPoliciesCount?: number | null
  occupationRiskNote?: string
  declarationsFreeText?: string
  bankName?: string
  bankAccountName?: string
  bankAccountNumberMasked?: string
  paymentReadyAt?: string | null
  convertedPolicyId?: string
  completeness: ProposalCompleteness | null
  quotationVersions: ProposalQuotationVersionRow[]
  planConfigs: ProposalPlanConfigRow[]
  members: ProposalMemberRow[]
  installmentConfigs: ProposalInstallmentRow[]
  fundAllocations: ProposalFundRow[]
  riders: ProposalRiderRow[]
  benefits: ProposalBenefitRow[]
  beneficiaries: BeneficiaryRecord[]
  documents: ProposalDocumentRecord[]
  readiness: ReadinessReport | null
  firstPremium: FirstPremiumStatusShape | null
}

export interface ProposalListParams extends TableQuery {
  status?: string
  product?: string
  agent?: string
  hasEmployer?: boolean
  expiryFrom?: string
  expiryTo?: string
  paymentReady?: boolean
  firstPremiumPosted?: boolean
}

/** Register KPIs from ``GET /proposals/kpis/`` (snake_case payload). */
export interface RegisterKPIs {
  totalProposals: number
  pendingUnderwriting: number
  paymentReady: number
  awaitingFirstPremium: number
  awaitingFirstPremiumAmount: number
  converted: number
  convertedInPeriod: number
  expiringSoon: number
  expiringIn7Days: number
  cancelled: number
  expired: number
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
  const badge = asRecord(record.status_badge)
  return {
    id: str(record, "id") ?? "",
    proposalNumber: str(record, "proposal_number", "proposalNumber") ?? "—",
    status: str(record, "status") ?? "",
    statusName: str(badge, "name", "label"),
    partnerName: str(record, "policyholder", "partner_name", "partnerName") ?? str(record, "partner_display") ?? "—",
    agentName: str(record, "agent_name_snapshot", "agent_name", "agent"),
    employerName: str(record, "employer_name_snapshot", "employer_name"),
    productName: str(record, "product_name", "productName", "product"),
    planName: str(record, "plan_name", "planName", "plan"),
    quotationNumber: str(record, "quotation_number", "quotationNumber"),
    totalPremium: num(record, "total_premium", "premium_amount", "totalPremium"),
    currency: str(record, "currency"),
    expiryDate: str(record, "expiry_date", "expiryDate") ?? null,
    medicalRequired: bool(record, "medical_required"),
    createdAt: str(record, "created_at") ?? null,
    paymentReady: bool(record, "payment_ready", "paymentReady"),
    firstPremiumPosted: bool(record, "first_premium_posted", "firstPremiumPosted"),
    allowedActions: normalizeAllowedActions(record.allowed_actions),
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

function rowsOf(record: Raw, ...keys: string[]): Raw[] {
  for (const key of keys) {
    const value = record[key]
    if (Array.isArray(value)) return value.map((row) => asRecord(row))
  }
  return []
}

function triBool(source: unknown, ...keys: string[]): boolean | null {
  const record = asRecord(source)
  for (const key of keys) {
    if (typeof record[key] === "boolean") return record[key] as boolean
  }
  return null
}

export function normalizeProposalDetail(raw: unknown): ProposalDetail {
  const base = normalizeProposalListItem(raw)
  const record = asRecord(raw)

  const planConfigs = rowsOf(record, "plan_configs").map((item) => ({
    id: str(item, "id") ?? "",
    planName: str(item, "plan_name_snapshot", "plan_name") ?? "—",
    subProductCode: str(item, "sub_product_code"),
    sectionNumber: str(item, "section_number"),
    baseSumAssured: num(item, "base_sum_assured"),
    termYears: num(item, "term_years"),
    paymentPeriodYears: num(item, "payment_period_years"),
    premiumFrequency: str(item, "premium_frequency"),
    quoteBasis: str(item, "quote_basis"),
    estimatedMaturityValue: num(item, "estimated_maturity_value"),
    premiumAmount: num(item, "premium_amount"),
    isSelected: bool(item, "is_selected"),
  }))

  const selectedPlan = planConfigs.find((plan) => plan.isSelected) ?? planConfigs[0]

  const detail: ProposalDetail = {
    ...base,
    partnerName: str(record, "partner_name_snapshot") ?? base.partnerName,
    agentName: str(record, "agent_name_snapshot") ?? base.agentName,
    employerName: str(record, "employer_name_snapshot") ?? base.employerName,
    productName: str(record, "product_name") ?? (selectedPlan ? `Plan ${selectedPlan.planName}` : undefined),
    planName: str(record, "plan_name") ?? selectedPlan?.planName,
    quotationId: str(record, "quotation", "quotation_id"),
    quotationNumber: str(record, "quotation_number") ?? base.quotationNumber,
    quotationVersion: num(record, "quotation_version"),
    agentPartnerId: str(record, "agent_partner"),
    employerPartnerId: str(record, "employer_partner"),
    underwritingStatus: str(record, "underwriting_status"),
    reasonCode: str(record, "reason_code"),
    reasonText: str(record, "reason_text"),
    sourceChannel: str(record, "source_channel"),
    employmentReference: str(record, "employment_reference"),
    payrollDeduction: triBool(record, "payroll_deduction"),
    intermediaryChannel: str(record, "intermediary_channel"),
    declarationPep: triBool(record, "declaration_pep_flag"),
    declarationAml: triBool(record, "declaration_aml_flag"),
    existingPoliciesCount: num(record, "existing_policies_count"),
    occupationRiskNote: str(record, "occupation_risk_note"),
    declarationsFreeText: str(record, "declarations_free_text"),
    bankName: str(record, "bank_name"),
    bankAccountName: str(record, "bank_account_name"),
    bankAccountNumberMasked: str(record, "bank_account_number"),
    paymentReadyAt: str(record, "payment_ready_at") ?? null,
    convertedPolicyId: str(record, "converted_policy"),
    completeness: record.completeness
      ? {
          missing: strArray(asRecord(record.completeness), "missing"),
          requiredMissing: strArray(asRecord(record.completeness), "required_missing"),
          complete: bool(asRecord(record.completeness), "complete"),
        }
      : null,
    quotationVersions: rowsOf(record, "quotation_versions").map((item) => ({
      versionNumber: num(item, "version_number", "version") ?? 0,
      status: str(item, "status"),
      changeReason: str(item, "change_reason"),
      createdAt: str(item, "created_at") ?? null,
    })),
    planConfigs,
    members: rowsOf(record, "members").map((item) => ({
      id: str(item, "id") ?? "",
      memberType: str(item, "member_type"),
      fullName:
        str(item, "full_name_snapshot") ??
        ([str(item, "first_name"), str(item, "last_name")].filter(Boolean).join(" ") || "—"),
      identityNumber: str(item, "identity_number"),
      dateOfBirth: str(item, "date_of_birth") ?? null,
      ageAtQuote: num(item, "age_at_quote"),
      gender: str(item, "gender"),
      smokerStatus: str(item, "smoker_status"),
      relationship: str(item, "relationship"),
      memberSumAssured: num(item, "member_sum_assured"),
      coverageBasis: str(item, "coverage_basis"),
    })),
    installmentConfigs: rowsOf(record, "installment_configs").map((item) => ({
      id: str(item, "id") ?? "",
      frequency: str(item, "frequency"),
      numberOfInstallments: num(item, "number_of_installments"),
      installmentAmount: num(item, "installment_amount"),
      firstDueDate: str(item, "first_due_date") ?? null,
      currency: str(item, "currency"),
      isSelected: bool(item, "is_selected"),
    })),
    fundAllocations: rowsOf(record, "fund_allocations").map((item) => ({
      id: str(item, "id") ?? "",
      fundName: str(item, "fund_name_snapshot", "fund") ?? "—",
      allocationPercentage: num(item, "allocation_percentage"),
      allocationAmount: num(item, "allocation_amount"),
      isSelected: bool(item, "is_selected"),
    })),
    riders: rowsOf(record, "riders").map((item) => ({
      id: str(item, "id") ?? "",
      riderName: str(item, "rider_name_snapshot", "rider") ?? "—",
      riderSumAssured: num(item, "rider_sum_assured"),
      riderTermYears: num(item, "rider_term_years"),
      benefitBasis: str(item, "benefit_basis"),
      benefitValue: num(item, "benefit_value"),
      premiumAmount: num(item, "premium_amount"),
      isSelected: bool(item, "is_selected"),
    })),
    benefits: rowsOf(record, "benefits").map((item) => ({
      id: str(item, "id") ?? "",
      code: str(item, "code"),
      name: str(item, "name") ?? "—",
      benefitType: str(item, "benefit_type"),
      basis: str(item, "basis"),
      value: num(item, "value"),
      sumAssured: num(item, "sum_assured"),
      premiumAmount: num(item, "premium_amount"),
      isSelected: bool(item, "is_selected"),
    })),
    beneficiaries: rowsOf(record, "beneficiaries").map((item) => ({
      id: str(item, "id") ?? "",
      personName: str(item, "person_name") ?? "—",
      sharePercent: num(item, "share_percent") ?? 0,
      isPrimary: bool(item, "is_primary"),
      isMinor: bool(item, "is_minor"),
      identityType: str(item, "identity_type"),
      identityNumber: str(item, "identity_number"),
      beneficialTypeName: str(item, "beneficial_type_name_snapshot"),
      guardianName: str(item, "guardian_name"),
      guardianRelationship: str(item, "guardian_relationship"),
    })),
    documents: rowsOf(record, "documents").map((item) => ({
      id: str(item, "id") ?? "",
      documentType: str(item, "document_type") ?? "",
      documentTypeDisplay: str(item, "document_type_display"),
      status: str(item, "status") ?? "",
      fileReference: str(item, "file_reference"),
      mandatory: bool(item, "mandatory"),
      uploadedAt: str(item, "uploaded_at"),
    })),
    allowedActions: normalizeAllowedActions(record.allowed_actions),
    // The detail payload evaluates readiness inline under ``checklist``.
    readiness: record.checklist || record.readiness ? normalizeReadiness(record.checklist ?? record.readiness) : null,
    firstPremium: record.first_premium ? normalizeFirstPremium(record.first_premium) : null,
  }
  return detail
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

export function normalizeProposalDocument(raw: unknown): ProposalDocumentRecord {
  const record = asRecord(raw)
  return {
    id: str(record, "id") ?? "",
    documentType: str(record, "document_type") ?? "",
    documentTypeDisplay: str(record, "document_type_display"),
    status: str(record, "status") ?? "",
    fileReference: str(record, "file_reference"),
    mandatory: bool(record, "mandatory"),
    uploadedAt: str(record, "uploaded_at"),
  }
}

export function normalizeProposalDocumentRequirement(raw: unknown): ProposalDocumentRequirement {
  const record = asRecord(raw)
  return {
    code: str(record, "code") ?? "",
    name: str(record, "name") ?? str(record, "document_type") ?? "",
    documentType: str(record, "document_type") ?? "",
    mandatory: bool(record, "mandatory"),
  }
}

export interface ProposalDocumentsPayload {
  rows: ProposalDocumentRecord[]
  requirements: ProposalDocumentRequirement[]
}

export function normalizeProposalDocuments(payload: unknown): ProposalDocumentsPayload {
  const record = asRecord(payload)
  const rawRows = Array.isArray(record.results) ? record.results : []
  const rawRequirements = Array.isArray(record.requirements) ? record.requirements : []
  return {
    rows: rawRows.map(normalizeProposalDocument),
    requirements: rawRequirements.map(normalizeProposalDocumentRequirement),
  }
}

export function normalizeHealthQuestions(payload: unknown): OLHealthQuestionnairePayload {
  const record = asRecord(payload)
  const rows = Array.isArray(record.results) ? record.results : []
  return {
    questionnaire: str(record, "questionnaire") ?? null,
    questions: rows.map((raw) => {
      const item = asRecord(raw)
      return {
        id: str(item, "id") ?? "",
        questionId: str(item, "question_id") ?? "",
        sequence: num(item, "sequence") ?? 0,
        mandatory: bool(item, "mandatory"),
        triggerMedicalRequirement: bool(item, "trigger_medical_requirement"),
        questionCode: str(item, "question_code") ?? "",
        questionText: str(item, "question_text") ?? "",
        answerType: str(item, "answer_type") ?? "BOOLEAN",
        category: str(item, "category"),
        underwritingImpact: str(item, "underwriting_impact"),
      }
    }),
  }
}

export function normalizeKPIs(payload: unknown): RegisterKPIs {
  const record = asRecord(payload)
  const pick = (...keys: string[]): number => {
    for (const key of keys) {
      const value = num(record, key)
      if (value !== null) return value
    }
    return 0
  }
  return {
    totalProposals: pick("total_proposals", "total"),
    pendingUnderwriting: pick("pending_underwriting"),
    paymentReady: pick("payment_ready"),
    awaitingFirstPremium: pick("awaiting_first_premium"),
    awaitingFirstPremiumAmount: pick("awaiting_first_premium_amount"),
    converted: pick("converted"),
    convertedInPeriod: pick("converted_in_period", "converted"),
    expiringSoon: pick("expiring_soon"),
    expiringIn7Days: pick("expiring_in_7_days", "expiring_soon"),
    cancelled: pick("cancelled"),
    expired: pick("expired"),
  }
}

// ---------------------------------------------------------------------------
// Fetchers
// ---------------------------------------------------------------------------

export async function listProposals(params: ProposalListParams = {}) {
  return request<unknown>(
    `${BASE}/proposals/${buildTableQuery({
      page: params.page,
      pageSize: params.pageSize,
      search: params.search,
      ordering: params.ordering,
      filters: {
        status: params.status,
        product: params.product,
        agent: params.agent,
        has_employer: params.hasEmployer === undefined ? "" : String(params.hasEmployer),
        expiry_from: params.expiryFrom,
        expiry_to: params.expiryTo,
        payment_ready: params.paymentReady === undefined ? "" : String(params.paymentReady),
        first_premium_posted: params.firstPremiumPosted === undefined ? "" : String(params.firstPremiumPosted),
      },
    })}`,
  )
}

/** Server-side CSV export — mirrors the list filter contract. */
export async function exportProposalsCsv(params: ProposalListParams = {}): Promise<PrintResult> {
  const query = buildTableQuery({
    search: params.search,
    ordering: params.ordering,
    filters: {
      status: params.status,
      product: params.product,
      agent: params.agent,
      has_employer: params.hasEmployer === undefined ? "" : String(params.hasEmployer),
      expiry_from: params.expiryFrom,
      expiry_to: params.expiryTo,
      payment_ready: params.paymentReady === undefined ? "" : String(params.paymentReady),
      first_premium_posted: params.firstPremiumPosted === undefined ? "" : String(params.firstPremiumPosted),
    },
  })
  const response = await fetch(`${BASE}/proposals/export/${query}`, {
    headers: {
      Authorization: `Bearer ${localStorage.getItem("aims_access_token") ?? sessionStorage.getItem("aims_access_token") ?? ""}`,
      Accept: "text/csv",
    },
  })
  if (!response.ok) throw await (await import("./apiClient")).normalizeResponseError(response)
  const blob = await response.blob()
  return { fileName: "ol-proposals.csv", blobUrl: URL.createObjectURL(blob) }
}

export async function getProposalKPIs() {
  return request<unknown>(`${BASE}/proposals/kpis/`)
}

export async function getProposal(id: string) {
  return request<unknown>(`${BASE}/proposals/${id}/`)
}

// ---------------------------------------------------------------------------
// History timeline + quotation version snapshots
// ---------------------------------------------------------------------------

export interface ProposalHistoryEvent {
  id: string
  eventType: string
  eventTypeLabel: string
  occurredAt?: string | null
  actor?: string
  fromStatus?: string
  toStatus?: string
  reason?: string
  sourceChannel?: string
}

export function normalizeProposalHistoryEvent(raw: unknown): ProposalHistoryEvent {
  const record = asRecord(raw)
  const eventType = str(record, "event_type") ?? ""
  return {
    id: str(record, "id") ?? "",
    eventType,
    eventTypeLabel: eventType.replace(/([a-z])([A-Z])/g, "$1 $2"),
    occurredAt: str(record, "occurred_at") ?? null,
    actor: str(record, "actor"),
    fromStatus: str(record, "from_status"),
    toStatus: str(record, "to_status"),
    reason: str(record, "reason"),
    sourceChannel: str(record, "source_channel"),
  }
}

export async function getProposalHistory(id: string): Promise<ProposalHistoryEvent[]> {
  const payload = await request<unknown>(`${BASE}/proposals/${id}/history/`)
  const rows = Array.isArray(payload) ? payload : rowsOf(asRecord(payload), "events")
  return rows.map(normalizeProposalHistoryEvent)
}

export interface QuotationVersionSnapshot {
  quotationId: string
  quoteNumber: string
  versionNumber: number
  status?: string
  changeReason?: string
  createdAt?: string | null
  snapshot: Raw
}

export async function getQuotationVersionSnapshot(quotationId: string, versionNumber: number): Promise<QuotationVersionSnapshot> {
  const payload = await request<unknown>(`${QUOTATIONS_BASE}/${quotationId}/as-of-version/${versionNumber}/`)
  const record = asRecord(payload)
  return {
    quotationId: str(record, "quotation_id") ?? quotationId,
    quoteNumber: str(record, "quote_number") ?? "",
    versionNumber: num(record, "version_number") ?? versionNumber,
    status: str(record, "status"),
    changeReason: str(record, "change_reason"),
    createdAt: str(record, "created_at") ?? null,
    snapshot: asRecord(record.snapshot),
  }
}

export async function createProposalFromQuotation(quotationId: string, version?: number) {
  const query = version != null ? `?version=${version}` : ""
  return request<unknown>(`${CREATE_BASE}/from-quotation/${quotationId}/${query}`, { method: "POST" })
}

// ---------------------------------------------------------------------------
// Finalized quotations (conversion source)
// ---------------------------------------------------------------------------

export interface QuotationOption {
  id: string
  quoteNumber: string
  quoteName: string
  policyholder: string
  partnerVerified: boolean
  version: number
  plansSummary?: string
  totalPremium?: number | null
  currency?: string
}

export function normalizeQuotationOption(raw: unknown): QuotationOption {
  const record = asRecord(raw)
  const actions = asRecord(record.row_actions).convert_to_proposal as Record<string, unknown> | undefined
  return {
    id: str(record, "id") ?? "",
    quoteNumber: str(record, "quote_number", "quoteNumber") ?? "—",
    quoteName: str(record, "quote_name", "quoteName") ?? "",
    policyholder: str(record, "prospect_name", "prospectName") ?? "",
    // The list payload signals BR-01 readiness via the convert row action.
    partnerVerified:
      actions?.state_allowed === true || bool(record, "partner_verified") || bool(record, "compliant"),
    version: num(record, "version", "current_version_number") ?? 1,
    plansSummary: str(record, "plans_summary", "plansSummary"),
    totalPremium: num(record, "total_premium", "totalPremium"),
    currency: str(record, "currency"),
  }
}

export async function listFinalizedQuotations(search = ""): Promise<QuotationOption[]> {
  const payload = await request<unknown>(
    `${QUOTATIONS_BASE}/${buildTableQuery({ pageSize: 50, search: search || undefined, filters: { status: "FINALIZED" } })}`,
  )
  return normalizePaginated(payload, normalizeQuotationOption).results
}

export interface QuotationVersionRow {
  versionNumber: number
  createdAt?: string | null
  createdBy?: string
}

export interface QuotationVersionsResult {
  currentVersionNumber: number | null
  versions: QuotationVersionRow[]
}

export async function listQuotationVersions(quotationId: string): Promise<QuotationVersionsResult> {
  const payload = await request<unknown>(`${QUOTATIONS_BASE}/${quotationId}/versions/`)
  const record = asRecord(payload)
  const rows = Array.isArray(record.versions) ? record.versions : []
  return {
    currentVersionNumber: num(record, "current_version_number"),
    versions: rows.map((row) => {
      const item = asRecord(row)
      return {
        versionNumber: num(item, "version_number", "version") ?? 0,
        createdAt: str(item, "created_at") ?? null,
        createdBy: str(item, "created_by_display", "created_by"),
      }
    }),
  }
}

/** PATCH /enrich/ expects { section_name: {fields} } with one or more sections. */
export async function enrichProposalSections(id: string, sections: Record<string, Record<string, unknown>>) {
  return request<unknown>(`${BASE}/proposals/${id}/enrich/`, {
    method: "PATCH",
    body: JSON.stringify(sections),
  })
}

export async function enrichProposalSection(id: string, section: string, data: Record<string, unknown>) {
  return enrichProposalSections(id, { [section]: data })
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
