import { request } from "./apiClient"

export const POLICY_PORTAL_BASE = "/api/v1/ol/policies/portal"

export interface PortalPolicyListItem {
  id: string
  policyNumber: string
  status: string
  productPlanDisplay: string
  riskCommencementDate: string | null
  maturityDate: string | null
  currency: string
}

export interface PortalPolicyDetail extends PortalPolicyListItem {
  sumAssured?: string | number | null
  premiumAmount?: string | number | null
  premiumFrequency?: string | null
}

export interface PortalDocumentInstance {
  id: string
  documentType: string
  templateName: string
  templateVersion: number | string | null
  generatedByDisplay: string
  generatedAt: string
  pageCount: number | null
}

function recordValue(value: unknown): Record<string, unknown> {
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

function normalizePolicy(raw: unknown): PortalPolicyDetail {
  const record = recordValue(raw)
  return {
    id: stringValue(record, "id", "policy_id"),
    policyNumber: stringValue(record, "policy_number", "policyNumber") || "Policy",
    status: stringValue(record, "status", "status_display") || "UNKNOWN",
    productPlanDisplay: stringValue(record, "product_plan_display", "product_plan", "product_plan_ref") || "Unspecified product",
    riskCommencementDate: optionalString(record, "risk_commencement_date", "riskCommencementDate"),
    maturityDate: optionalString(record, "maturity_date", "maturityDate"),
    currency: stringValue(record, "currency") || "TZS",
    sumAssured: record.sum_assured as string | number | null ?? null,
    premiumAmount: record.premium_amount as string | number | null ?? null,
    premiumFrequency: optionalString(record, "premium_frequency", "premiumFrequency"),
  }
}

function normalizeDocuments(payload: unknown): PortalDocumentInstance[] {
  const record = recordValue(payload)
  const rows = Array.isArray(record.results) ? record.results : Array.isArray(payload) ? payload : []
  return rows.map((value) => {
    const item = recordValue(value)
    const templateVersion = item.template_version ?? item.templateVersion
    const pageCount = Number(item.page_count ?? item.pageCount)
    return {
      id: stringValue(item, "id"),
      documentType: stringValue(item, "document_type", "documentType") || "Document",
      templateName: stringValue(item, "template_name", "templateName") || "Document",
      templateVersion: templateVersion === null || templateVersion === undefined ? null : String(templateVersion),
      generatedByDisplay: stringValue(item, "generated_by_display", "generatedByDisplay") || "ZIC",
      generatedAt: stringValue(item, "generated_at", "generatedAt"),
      pageCount: Number.isFinite(pageCount) ? pageCount : null,
    }
  })
}

export async function listPortalPolicies(): Promise<{ count: number; results: PortalPolicyListItem[] }> {
  const payload = recordValue(await request<unknown>(`${POLICY_PORTAL_BASE}/`))
  const rows = Array.isArray(payload.results) ? payload.results.map(normalizePolicy) : []
  return { count: Number(payload.count ?? rows.length), results: rows }
}

export async function getPortalPolicy(policyId: string): Promise<PortalPolicyDetail> {
  return normalizePolicy(await request<unknown>(`${POLICY_PORTAL_BASE}/${encodeURIComponent(policyId)}/`))
}

export async function listPortalPolicyDocuments(policyId: string): Promise<PortalDocumentInstance[]> {
  const query = new URLSearchParams({ source_type: "ol_policies.policy", object_id: policyId, page_size: "50" })
  return normalizeDocuments(await request<unknown>(`/api/v1/documents/instances/?${query.toString()}`))
}
