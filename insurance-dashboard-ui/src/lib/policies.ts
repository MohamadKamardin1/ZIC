/**
 * Ordinary Life Policies — typed API contract and normalizers.
 *
 * Policy IDs are retained for API navigation only. User-facing fields always
 * prefer the backend's display fields and never fall back to raw UUID values.
 */

import { buildQueryString, buildTableQuery, request, type QueryParams, type TableQuery } from "./apiClient"

export const POLICIES_BASE = "/api/v1/ol/policies"
export const POLICY_OPTIONS_BASE = "/api/v1/ol/options"

export type PolicyAction = string

export interface PolicyListItem {
  id: string
  policyNumber: string
  proposalRefDisplay?: string | null
  policyholderDisplay: string
  policyholderName: string
  productPlanDisplay: string
  productName?: string | null
  planName?: string | null
  agentDisplay: string
  agentName?: string | null
  currency: string
  sumAssured: string | number | null
  premiumAmount: string | number | null
  premiumFrequency?: string | null
  termYears?: number | null
  riskCommencementDate?: string | null
  maturityDate?: string | null
  status: string
  statusDisplay: string
  allowedActions: PolicyAction[]
  version?: number | null
  createdAt?: string | null
  updatedAt?: string | null
}

export interface PolicyMember {
  id: string
  memberRelation: string
  name: string
  dob?: string | null
  gender?: string | null
  benefitAmount: string | number | null
}

export interface PolicyRider {
  id: string
  riderCode: string
  sumAssured: string | number | null
  amount: string | number | null
  premium: string | number | null
}

export interface PolicyBenefit {
  id: string
  benefitType: string
  calculationBasis: string
  amount: string | number | null
}

export interface PolicyEndorsement {
  id: string
  endorsementNumber: string
  endorsementType: string
  effectiveDate?: string | null
  description?: string | null
  status: string
  beforeSnapshot?: Record<string, unknown>
  afterSnapshot?: Record<string, unknown>
  reason?: string | null
  sourceChannel?: string | null
  createdAt?: string | null
}

export interface PolicyAuditEntry {
  id: string
  eventType: string
  fromStatus?: string | null
  toStatus?: string | null
  beforeSnapshot?: Record<string, unknown>
  afterSnapshot?: Record<string, unknown>
  reason?: string | null
  sourceChannel?: string | null
  correlationId?: string | null
  actorDisplay: string
  createdAt?: string | null
}

export interface PolicyDetail extends PolicyListItem {
  contractSnapshot: Record<string, unknown>
  members: PolicyMember[]
  riders: PolicyRider[]
  benefits: PolicyBenefit[]
  endorsements: PolicyEndorsement[]
  auditLogs: PolicyAuditEntry[]
  linkedProposal?: Record<string, unknown> | null
  linkedCommitments?: Array<Record<string, unknown>>
}

export interface PolicyListParams extends TableQuery {
  status?: string
  product?: string
  branch?: string
  agent?: string
  currency?: string
  commencementFrom?: string
  commencementTo?: string
  maturityFrom?: string
  maturityTo?: string
}

export interface PolicyKpis {
  totalActivePolicies: number
  totalSumAssured: string
  newPoliciesThisMonth: number
  lapsedPoliciesCount: number
  lapsedPoliciesValue: string
  maturingSoonCount: number
  currency: string
  sumAssuredByCurrency: Record<string, string>
  timestamp?: string | null
}

export interface PolicyOption {
  value: string
  label: string
  meta?: Record<string, unknown>
}

export interface Paginated<T> {
  results: T[]
  count: number
  page: number
  pageSize: number
  next?: boolean | string | null
  previous?: boolean | string | null
}

export interface PolicyPrintResult {
  instance?: Record<string, unknown>
  document?: Record<string, unknown>
  previewUrl?: string
  signedDownloadUrl?: string
  [key: string]: unknown
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {}
}

function stringValue(record: Record<string, unknown>, ...keys: string[]): string {
  for (const key of keys) {
    const value = record[key]
    if (value !== null && value !== undefined && value !== "") return String(value)
  }
  return ""
}

function optionalString(record: Record<string, unknown>, ...keys: string[]): string | null {
  const value = stringValue(record, ...keys)
  return value || null
}

function nullableNumber(record: Record<string, unknown>, ...keys: string[]): number | null {
  for (const key of keys) {
    const value = record[key]
    if (value === null || value === undefined || value === "") continue
    const number = Number(value)
    return Number.isFinite(number) ? number : null
  }
  return null
}

function actionList(value: unknown): PolicyAction[] {
  if (Array.isArray(value)) return value.map(String)
  if (value && typeof value === "object") return Object.entries(asRecord(value)).filter(([, enabled]) => enabled === true).map(([key]) => key)
  return []
}

export function normalizePolicyListItem(raw: unknown): PolicyListItem {
  const record = asRecord(raw)
  const status = stringValue(record, "status") || "UNKNOWN"
  return {
    id: stringValue(record, "id"),
    policyNumber: stringValue(record, "policy_number", "policyNumber"),
    proposalRefDisplay: optionalString(record, "proposal_ref_display", "proposalRefDisplay"),
    policyholderDisplay: stringValue(record, "policyholder_display", "policyholderDisplay", "policyholder_name", "policyholderName") || "Unnamed policyholder",
    policyholderName: stringValue(record, "policyholder_name", "policyholderName", "policyholder_display", "policyholderDisplay") || "Unnamed policyholder",
    productPlanDisplay: stringValue(record, "product_plan_display", "productPlanDisplay", "product_plan_ref") || "Unspecified product",
    productName: optionalString(record, "product_name", "productName"),
    planName: optionalString(record, "plan_name", "planName"),
    agentDisplay: stringValue(record, "agent_display", "agentDisplay", "agent_name", "agentName") || "—",
    agentName: optionalString(record, "agent_name", "agentName", "agent_display", "agentDisplay"),
    currency: stringValue(record, "currency") || "TZS",
    sumAssured: record.sum_assured as string | number | null ?? record.sumAssured as string | number | null ?? null,
    premiumAmount: record.premium_amount as string | number | null ?? record.premiumAmount as string | number | null ?? null,
    premiumFrequency: optionalString(record, "premium_frequency", "premiumFrequency"),
    termYears: nullableNumber(record, "term_years", "termYears"),
    riskCommencementDate: optionalString(record, "risk_commencement_date", "riskCommencementDate"),
    maturityDate: optionalString(record, "maturity_date", "maturityDate"),
    status,
    statusDisplay: stringValue(record, "status_display", "statusDisplay") || status,
    allowedActions: actionList(record.allowed_actions ?? record.allowedActions),
    version: nullableNumber(record, "version"),
    createdAt: optionalString(record, "created_at", "createdAt"),
    updatedAt: optionalString(record, "updated_at", "updatedAt"),
  }
}

export function normalizePaginated<T>(payload: unknown, mapRow: (value: unknown) => T): Paginated<T> {
  const record = asRecord(payload)
  const rawRows = Array.isArray(payload) ? payload : Array.isArray(record.results) ? record.results : Array.isArray(record.items) ? record.items : []
  const pageSize = Number((record.page_size ?? record.pageSize ?? rawRows.length) || 0)
  return {
    results: rawRows.map(mapRow),
    count: Number(record.count ?? record.total ?? rawRows.length),
    page: Number(record.page ?? 1),
    pageSize: Number.isFinite(pageSize) ? pageSize : rawRows.length,
    next: record.next as boolean | string | null | undefined,
    previous: record.previous as boolean | string | null | undefined,
  }
}

export function normalizePolicyDetail(raw: unknown): PolicyDetail {
  const record = asRecord(raw)
  const base = normalizePolicyListItem(record)
  const members = Array.isArray(record.members) ? record.members.map((value) => {
    const row = asRecord(value)
    return {
      id: stringValue(row, "id"),
      memberRelation: stringValue(row, "member_relation", "memberRelation", "relation") || "—",
      name: stringValue(row, "name", "full_name", "fullName") || "Unnamed member",
      dob: optionalString(row, "dob", "date_of_birth", "dateOfBirth"),
      gender: optionalString(row, "gender"),
      benefitAmount: row.benefit_amount as string | number | null ?? row.benefitAmount as string | number | null ?? null,
    } satisfies PolicyMember
  }) : []
  const riders = Array.isArray(record.riders) ? record.riders.map((value) => {
    const row = asRecord(value)
    return {
      id: stringValue(row, "id"),
      riderCode: stringValue(row, "rider_code", "riderCode", "rider_display") || "—",
      sumAssured: row.sum_assured as string | number | null ?? row.sumAssured as string | number | null ?? null,
      amount: row.amount as string | number | null ?? null,
      premium: row.premium as string | number | null ?? null,
    } satisfies PolicyRider
  }) : []
  const benefits = Array.isArray(record.benefits) ? record.benefits.map((value) => {
    const row = asRecord(value)
    return {
      id: stringValue(row, "id"),
      benefitType: stringValue(row, "benefit_type", "benefitType", "benefit_type_display") || "—",
      calculationBasis: stringValue(row, "calculation_basis", "calculationBasis") || "—",
      amount: row.amount as string | number | null ?? null,
    } satisfies PolicyBenefit
  }) : []
  const endorsements = Array.isArray(record.endorsements) ? record.endorsements.map(normalizeEndorsement) : []
  const auditLogs = Array.isArray(record.audit_logs) ? record.audit_logs.map(normalizeAuditEntry) : Array.isArray(record.auditLogs) ? record.auditLogs.map(normalizeAuditEntry) : []
  return {
    ...base,
    contractSnapshot: asRecord(record.contract_snapshot ?? record.contractSnapshot),
    members,
    riders,
    benefits,
    endorsements,
    auditLogs,
    linkedProposal: record.linked_proposal as Record<string, unknown> | null ?? record.linkedProposal as Record<string, unknown> | null ?? null,
    linkedCommitments: Array.isArray(record.linked_commitments) ? record.linked_commitments as Array<Record<string, unknown>> : [],
  }
}

function normalizeEndorsement(raw: unknown): PolicyEndorsement {
  const record = asRecord(raw)
  return {
    id: stringValue(record, "id"),
    endorsementNumber: stringValue(record, "endorsement_number", "endorsementNumber"),
    endorsementType: stringValue(record, "endorsement_type", "endorsementType") || "—",
    effectiveDate: optionalString(record, "effective_date", "effectiveDate"),
    description: optionalString(record, "description"),
    status: stringValue(record, "status") || "PENDING",
    beforeSnapshot: asRecord(record.before_snapshot ?? record.beforeSnapshot),
    afterSnapshot: asRecord(record.after_snapshot ?? record.afterSnapshot),
    reason: optionalString(record, "reason"),
    sourceChannel: optionalString(record, "source_channel", "sourceChannel"),
    createdAt: optionalString(record, "created_at", "createdAt"),
  }
}

function normalizeAuditEntry(raw: unknown): PolicyAuditEntry {
  const record = asRecord(raw)
  return {
    id: stringValue(record, "id"),
    eventType: stringValue(record, "event_type", "eventType") || "PolicyChanged",
    fromStatus: optionalString(record, "from_status", "fromStatus"),
    toStatus: optionalString(record, "to_status", "toStatus"),
    beforeSnapshot: asRecord(record.before_snapshot ?? record.beforeSnapshot),
    afterSnapshot: asRecord(record.after_snapshot ?? record.afterSnapshot),
    reason: optionalString(record, "reason"),
    sourceChannel: optionalString(record, "source_channel", "sourceChannel"),
    correlationId: optionalString(record, "correlation_id", "correlationId"),
    actorDisplay: stringValue(record, "actor_display", "actorDisplay") || "System",
    createdAt: optionalString(record, "created_at", "createdAt"),
  }
}

export function normalizePolicyKpis(raw: unknown): PolicyKpis {
  const record = asRecord(raw)
  const byCurrency = asRecord(record.sum_assured_by_currency ?? record.sumAssuredByCurrency)
  return {
    totalActivePolicies: Number(record.total_active_policies ?? record.totalActivePolicies ?? 0),
    totalSumAssured: String(record.total_sum_assured ?? record.totalSumAssured ?? "0.00"),
    newPoliciesThisMonth: Number(record.new_policies_this_month ?? record.newPoliciesThisMonth ?? 0),
    lapsedPoliciesCount: Number(record.lapsed_policies_count ?? record.lapsedPoliciesCount ?? 0),
    lapsedPoliciesValue: String(record.lapsed_policies_value ?? record.lapsedPoliciesValue ?? "0.00"),
    maturingSoonCount: Number(record.maturing_soon_count ?? record.maturingSoonCount ?? 0),
    currency: stringValue(record, "currency") || "MULTI",
    sumAssuredByCurrency: Object.fromEntries(Object.entries(byCurrency).map(([key, value]) => [key, String(value)])),
    timestamp: optionalString(record, "timestamp"),
  }
}

function normalizeOption(raw: unknown): PolicyOption {
  const record = asRecord(raw)
  const value = stringValue(record, "value", "id", "code")
  return {
    value,
    label: stringValue(record, "label", "display", "name") || value,
    meta: asRecord(record.meta),
  }
}

function withQuery(path: string, params?: QueryParams): string {
  return `${path}${buildQueryString(params)}`
}

export async function listPolicies(params: PolicyListParams = {}): Promise<Paginated<PolicyListItem>> {
  const { filters, ...table } = params
  const query = buildTableQuery({ ...table, filters: {
    ...(filters ?? {}),
    status: params.status,
    product: params.product,
    branch: params.branch,
    agent: params.agent,
    currency: params.currency,
    commencement_from: params.commencementFrom,
    commencement_to: params.commencementTo,
    maturity_from: params.maturityFrom,
    maturity_to: params.maturityTo,
  } })
  return normalizePaginated(await request<unknown>(`${POLICIES_BASE}/${query}`), normalizePolicyListItem)
}

export async function getPolicy(id: string): Promise<PolicyDetail> {
  return normalizePolicyDetail(await request<unknown>(`${POLICIES_BASE}/${id}/`))
}

function collectionRows(payload: unknown, key: string): unknown[] {
  const record = asRecord(payload)
  if (Array.isArray(payload)) return payload
  if (Array.isArray(record.results)) return record.results
  if (Array.isArray(record[key])) return record[key] as unknown[]
  return []
}

export async function listPolicyMembers(id: string): Promise<PolicyMember[]> {
  return normalizePolicyDetail({ members: collectionRows(await request<unknown>(`${POLICIES_BASE}/${id}/members/`), "members") }).members
}

export async function listPolicyRiders(id: string): Promise<PolicyRider[]> {
  return normalizePolicyDetail({ riders: collectionRows(await request<unknown>(`${POLICIES_BASE}/${id}/riders/`), "riders") }).riders
}

export async function listPolicyBenefits(id: string): Promise<PolicyBenefit[]> {
  return normalizePolicyDetail({ benefits: collectionRows(await request<unknown>(`${POLICIES_BASE}/${id}/benefits/`), "benefits") }).benefits
}

export async function getPolicyKpis(params: QueryParams = {}): Promise<PolicyKpis> {
  return normalizePolicyKpis(await request<unknown>(withQuery(`${POLICIES_BASE}/kpis/`, params)))
}

export async function issuePolicy(proposalId: string): Promise<Record<string, unknown>> {
  return request<Record<string, unknown>>(`${POLICIES_BASE}/issue/`, { method: "POST", body: JSON.stringify({ proposal_id: proposalId }) })
}

export async function createPolicyEndorsement(policyId: string, payload: Record<string, unknown>): Promise<PolicyEndorsement> {
  return normalizeEndorsement(await request<unknown>(`${POLICIES_BASE}/${policyId}/endorsements/`, { method: "POST", body: JSON.stringify(payload) }))
}

export async function listPolicyEndorsements(policyId: string, params?: QueryParams): Promise<Paginated<PolicyEndorsement>> {
  return normalizePaginated(await request<unknown>(withQuery(`${POLICIES_BASE}/${policyId}/endorsements/`, params)), normalizeEndorsement)
}

export async function requestPolicyLoan(policyId: string, payload: Record<string, unknown>): Promise<Record<string, unknown>> {
  return request<Record<string, unknown>>(`${POLICIES_BASE}/${policyId}/loans/`, { method: "POST", body: JSON.stringify(payload) })
}

export async function listPolicyLoans(policyId: string, params?: QueryParams): Promise<Paginated<Record<string, unknown>>> {
  return normalizePaginated(await request<unknown>(withQuery(`${POLICIES_BASE}/${policyId}/loans/`, params)), (value) => asRecord(value))
}

export async function approvePolicyLoan(loanId: string, payload: Record<string, unknown> = {}): Promise<Record<string, unknown>> {
  return request<Record<string, unknown>>(`${POLICIES_BASE}/loans/${loanId}/approve/`, { method: "POST", body: JSON.stringify(payload) })
}

export async function disbursePolicyLoan(loanId: string, payload: Record<string, unknown> = {}): Promise<Record<string, unknown>> {
  return request<Record<string, unknown>>(`${POLICIES_BASE}/loans/${loanId}/disburse/`, { method: "POST", body: JSON.stringify(payload) })
}

export async function repayPolicyLoan(loanId: string, payload: Record<string, unknown>): Promise<Record<string, unknown>> {
  return request<Record<string, unknown>>(`${POLICIES_BASE}/loans/${loanId}/repay/`, { method: "POST", body: JSON.stringify(payload) })
}

export async function requestPolicyWithdrawal(policyId: string, payload: Record<string, unknown>): Promise<Record<string, unknown>> {
  return request<Record<string, unknown>>(`${POLICIES_BASE}/${policyId}/withdrawals/`, { method: "POST", body: JSON.stringify(payload) })
}

export async function listPolicyWithdrawals(policyId: string, params?: QueryParams): Promise<Paginated<Record<string, unknown>>> {
  return normalizePaginated(await request<unknown>(withQuery(`${POLICIES_BASE}/${policyId}/withdrawals/`, params)), (value) => asRecord(value))
}

export async function requestPolicySurrender(policyId: string, payload: Record<string, unknown> = {}): Promise<Record<string, unknown>> {
  return request<Record<string, unknown>>(`${POLICIES_BASE}/${policyId}/surrender/`, { method: "POST", body: JSON.stringify(payload) })
}

export async function requestPolicyPaidUp(policyId: string, payload: Record<string, unknown> = {}): Promise<PolicyDetail> {
  return normalizePolicyDetail(await request<unknown>(`${POLICIES_BASE}/${policyId}/paid-up/`, { method: "POST", body: JSON.stringify(payload) }))
}

export async function cancelPolicy(policyId: string, payload: Record<string, unknown> = {}): Promise<Record<string, unknown>> {
  return request<Record<string, unknown>>(`${POLICIES_BASE}/${policyId}/cancel/`, { method: "POST", body: JSON.stringify(payload) })
}

export async function processPolicyMaturity(policyId: string, payload: Record<string, unknown> = {}): Promise<Record<string, unknown>> {
  return request<Record<string, unknown>>(`${POLICIES_BASE}/${policyId}/maturity/`, { method: "POST", body: JSON.stringify(payload) })
}

export async function printPolicyContract(policyId: string): Promise<PolicyPrintResult> {
  return normalizePrintResult(await request<unknown>(`${POLICIES_BASE}/${policyId}/print-contract/`, { method: "POST", body: JSON.stringify({}) }))
}

export async function printPolicySchedule(policyId: string): Promise<PolicyPrintResult> {
  return normalizePrintResult(await request<unknown>(`${POLICIES_BASE}/${policyId}/print-schedule/`, { method: "POST", body: JSON.stringify({}) }))
}

function normalizePrintResult(raw: unknown): PolicyPrintResult {
  const record = asRecord(raw)
  return {
    ...record,
    instance: asRecord(record.instance),
    document: asRecord(record.document),
    previewUrl: stringValue(record, "preview_url", "previewUrl") || undefined,
    signedDownloadUrl: stringValue(record, "signed_download_url", "signedDownloadUrl") || undefined,
  }
}

export async function listPolicyOptions(entity: string, params: QueryParams = {}): Promise<Paginated<PolicyOption>> {
  return normalizePaginated(await request<unknown>(withQuery(`${POLICY_OPTIONS_BASE}/${entity}/`, params)), normalizeOption)
}

export async function getPolicyOptions(entity: string, params: QueryParams = {}): Promise<PolicyOption[]> {
  return (await listPolicyOptions(entity, params)).results
}
