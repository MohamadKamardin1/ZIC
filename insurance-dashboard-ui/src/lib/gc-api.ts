/**
 * Group Credit — API Client
 *
 * Dedicated API functions for all Group Credit endpoints.
 * Follows the established apiFetchAuth + extractError pattern.
 */

import { apiFetchAuth } from "./api"

const GC_BASE = "/api/v1/group-credit"

// ---------------------------------------------------------------------------
// Generic helpers
// ---------------------------------------------------------------------------

function extractError(res: Response, body: unknown): string {
  if (typeof body === "object" && body !== null) {
    const b = body as Record<string, unknown>
    if (typeof b.message === "string") return b.message
    if (typeof b.detail === "string") return b.detail
    if (Array.isArray(b.non_field_errors)) return (b.non_field_errors[0] as string) ?? "Request failed."
    for (const key in b) {
      const val = b[key]
      if (Array.isArray(val) && val.length > 0) return `${key}: ${val[0] as string}`
    }
  }
  return `Request failed (${res.status}).`
}

async function gcGet(path: string): Promise<any> {
  const res = await apiFetchAuth(`${GC_BASE}${path}`)
  const json = await res.json()
  if (!res.ok) throw new Error(extractError(res, json))
  return json.data ?? json.results ?? json
}

async function gcPost(path: string, data?: Record<string, unknown>): Promise<any> {
  const res = await apiFetchAuth(`${GC_BASE}${path}`, {
    method: "POST",
    body: data ? JSON.stringify(data) : undefined,
  })
  const json = await res.json()
  if (!res.ok) throw new Error(extractError(res, json))
  return json.data ?? json
}

async function gcPatch(path: string, data: Record<string, unknown>): Promise<any> {
  const res = await apiFetchAuth(`${GC_BASE}${path}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  })
  const json = await res.json()
  if (!res.ok) throw new Error(extractError(res, json))
  return json.data ?? json
}

async function gcDelete(path: string): Promise<void> {
  const res = await apiFetchAuth(`${GC_BASE}${path}`, { method: "DELETE" })
  if (!res.ok) {
    const json = await res.json().catch(() => null)
    throw new Error(extractError(res, json))
  }
}

async function gcList(path: string, params?: Record<string, string>): Promise<any> {
  const url = params
    ? `${GC_BASE}${path}?${new URLSearchParams(params).toString()}`
    : `${GC_BASE}${path}`
  const res = await apiFetchAuth(url)
  const json = await res.json()
  if (!res.ok) throw new Error(extractError(res, json))
  return json
}

// ---------------------------------------------------------------------------
// Setup / Parameter CRUD
// ---------------------------------------------------------------------------

export const gcSetup = {
  // Lookup Values
  listLookupValues: (category?: string) => gcGet(`/lookup-values/${category ? `?category=${category}` : ""}`),
  createLookupValue: (d: any) => gcPost("/lookup-values/", d),
  updateLookupValue: (id: string, d: any) => gcPatch(`/lookup-values/${id}/`, d),
  deleteLookupValue: (id: string) => gcDelete(`/lookup-values/${id}/`),

  // Scheme Types
  listSchemeTypes: (params?: Record<string, string>) => gcList("/scheme-types/", params),
  createSchemeType: (data: Record<string, unknown>) => gcPost("/scheme-types/", data),
  updateSchemeType: (id: string, data: Record<string, unknown>) => gcPatch(`/scheme-types/${id}/`, data),
  deleteSchemeType: (id: string) => gcDelete(`/scheme-types/${id}/`),

  // Scheme Statuses
  listSchemeStatuses: (params?: Record<string, string>) => gcList("/scheme-statuses/", params),
  createSchemeStatus: (data: Record<string, unknown>) => gcPost("/scheme-statuses/", data),
  updateSchemeStatus: (id: string, data: Record<string, unknown>) => gcPatch(`/scheme-statuses/${id}/`, data),
  deleteSchemeStatus: (id: string) => gcDelete(`/scheme-statuses/${id}/`),

  // Member Statuses
  listMemberStatuses: (params?: Record<string, string>) => gcList("/member-statuses/", params),
  createMemberStatus: (data: Record<string, unknown>) => gcPost("/member-statuses/", data),
  updateMemberStatus: (id: string, data: Record<string, unknown>) => gcPatch(`/member-statuses/${id}/`, data),
  deleteMemberStatus: (id: string) => gcDelete(`/member-statuses/${id}/`),

  // Renewal Statuses
  listRenewalStatuses: (params?: Record<string, string>) => gcList("/renewal-statuses/", params),
  createRenewalStatus: (data: Record<string, unknown>) => gcPost("/renewal-statuses/", data),
  updateRenewalStatus: (id: string, data: Record<string, unknown>) => gcPatch(`/renewal-statuses/${id}/`, data),
  deleteRenewalStatus: (id: string) => gcDelete(`/renewal-statuses/${id}/`),

  // Premium Rates
  listPremiumRates: (params?: Record<string, string>) => gcList("/premium-rates/", params),
  createPremiumRate: (data: Record<string, unknown>) => gcPost("/premium-rates/", data),
  updatePremiumRate: (id: string, data: Record<string, unknown>) => gcPatch(`/premium-rates/${id}/`, data),
  deletePremiumRate: (id: string) => gcDelete(`/premium-rates/${id}/`),

  // Health Questions
  listHealthQuestions: (params?: Record<string, string>) => gcList("/health-questions/", params),
  createHealthQuestion: (data: Record<string, unknown>) => gcPost("/health-questions/", data),
  updateHealthQuestion: (id: string, data: Record<string, unknown>) => gcPatch(`/health-questions/${id}/`, data),
  deleteHealthQuestion: (id: string) => gcDelete(`/health-questions/${id}/`),

  // Health Questionnaires
  listHealthQuestionnaires: (params?: Record<string, string>) => gcList("/health-questionnaires/", params),
  createHealthQuestionnaire: (data: Record<string, unknown>) => gcPost("/health-questionnaires/", data),
  updateHealthQuestionnaire: (id: string, data: Record<string, unknown>) => gcPatch(`/health-questionnaires/${id}/`, data),
  deleteHealthQuestionnaire: (id: string) => gcDelete(`/health-questionnaires/${id}/`),

  // Sub Products
  listSubProducts: (params?: Record<string, string>) => gcList("/sub-products/", params),
  createSubProduct: (data: Record<string, unknown>) => gcPost("/sub-products/", data),
  updateSubProduct: (id: string, data: Record<string, unknown>) => gcPatch(`/sub-products/${id}/`, data),
  deleteSubProduct: (id: string) => gcDelete(`/sub-products/${id}/`),

  // Products
  listProducts: (params?: Record<string, string>) => gcList("/products/", params),
  getProduct: (id: string) => gcGet(`/products/${id}/`),
  createProduct: (data: Record<string, unknown>) => gcPost("/products/", data),
  updateProduct: (id: string, data: Record<string, unknown>) => gcPatch(`/products/${id}/`, data),
  deleteProduct: (id: string) => gcDelete(`/products/${id}/`),

  // Riders
  listRiders: (params?: Record<string, string>) => gcList("/riders/", params),
  createRider: (data: Record<string, unknown>) => gcPost("/riders/", data),
  updateRider: (id: string, data: Record<string, unknown>) => gcPatch(`/riders/${id}/`, data),
  deleteRider: (id: string) => gcDelete(`/riders/${id}/`),

  // Rider Rates
  listRiderRates: (params?: Record<string, string>) => gcList("/rider-rates/", params),
  createRiderRate: (data: Record<string, unknown>) => gcPost("/rider-rates/", data),
  updateRiderRate: (id: string, data: Record<string, unknown>) => gcPatch(`/rider-rates/${id}/`, data),
  deleteRiderRate: (id: string) => gcDelete(`/rider-rates/${id}/`),

  // Medical Codes
  listMedicalCodes: (params?: Record<string, string>) => gcList("/medical-codes/", params),
  createMedicalCode: (data: Record<string, unknown>) => gcPost("/medical-codes/", data),
  updateMedicalCode: (id: string, data: Record<string, unknown>) => gcPatch(`/medical-codes/${id}/`, data),
  deleteMedicalCode: (id: string) => gcDelete(`/medical-codes/${id}/`),

  // Medical Limits
  listMedicalLimits: (params?: Record<string, string>) => gcList("/medical-limits/", params),
  createMedicalLimit: (data: Record<string, unknown>) => gcPost("/medical-limits/", data),
  updateMedicalLimit: (id: string, data: Record<string, unknown>) => gcPatch(`/medical-limits/${id}/`, data),
  deleteMedicalLimit: (id: string) => gcDelete(`/medical-limits/${id}/`),

  // UW Decisions
  listUWDecisions: (params?: Record<string, string>) => gcList("/uw-decisions/", params),
  createUWDecision: (data: Record<string, unknown>) => gcPost("/uw-decisions/", data),
  updateUWDecision: (id: string, data: Record<string, unknown>) => gcPatch(`/uw-decisions/${id}/`, data),
  deleteUWDecision: (id: string) => gcDelete(`/uw-decisions/${id}/`),

  // Personal Habits
  listPersonalHabits: (params?: Record<string, string>) => gcList("/personal-habits/", params),
  createPersonalHabit: (data: Record<string, unknown>) => gcPost("/personal-habits/", data),
  updatePersonalHabit: (id: string, data: Record<string, unknown>) => gcPatch(`/personal-habits/${id}/`, data),
  deletePersonalHabit: (id: string) => gcDelete(`/personal-habits/${id}/`),

  // Medical History
  listMedicalHistory: (params?: Record<string, string>) => gcList("/medical-history/", params),
  createMedicalHistory: (data: Record<string, unknown>) => gcPost("/medical-history/", data),
  updateMedicalHistory: (id: string, data: Record<string, unknown>) => gcPatch(`/medical-history/${id}/`, data),
  deleteMedicalHistory: (id: string) => gcDelete(`/medical-history/${id}/`),

  // Medical Facilities
  listMedicalFacilities: (params?: Record<string, string>) => gcList("/medical-facilities/", params),
  createMedicalFacility: (data: Record<string, unknown>) => gcPost("/medical-facilities/", data),
  updateMedicalFacility: (id: string, data: Record<string, unknown>) => gcPatch(`/medical-facilities/${id}/`, data),
  deleteMedicalFacility: (id: string) => gcDelete(`/medical-facilities/${id}/`),

  // Medical Practitioners
  listMedicalPractitioners: (params?: Record<string, string>) => gcList("/medical-practitioners/", params),
  createMedicalPractitioner: (data: Record<string, unknown>) => gcPost("/medical-practitioners/", data),
  updateMedicalPractitioner: (id: string, data: Record<string, unknown>) => gcPatch(`/medical-practitioners/${id}/`, data),
  deleteMedicalPractitioner: (id: string) => gcDelete(`/medical-practitioners/${id}/`),

  // Claim Types
  listClaimTypes: (params?: Record<string, string>) => gcList("/claim-types/", params),
  createClaimType: (data: Record<string, unknown>) => gcPost("/claim-types/", data),
  updateClaimType: (id: string, data: Record<string, unknown>) => gcPatch(`/claim-types/${id}/`, data),
  deleteClaimType: (id: string) => gcDelete(`/claim-types/${id}/`),

  // Claim Reasons
  listClaimReasons: (params?: Record<string, string>) => gcList("/claim-reasons/", params),
  createClaimReason: (data: Record<string, unknown>) => gcPost("/claim-reasons/", data),
  updateClaimReason: (id: string, data: Record<string, unknown>) => gcPatch(`/claim-reasons/${id}/`, data),
  deleteClaimReason: (id: string) => gcDelete(`/claim-reasons/${id}/`),

  // Claim Statuses
  listClaimStatuses: (params?: Record<string, string>) => gcList("/claim-statuses/", params),
  createClaimStatus: (data: Record<string, unknown>) => gcPost("/claim-statuses/", data),
  updateClaimStatus: (id: string, data: Record<string, unknown>) => gcPatch(`/claim-statuses/${id}/`, data),
  deleteClaimStatus: (id: string) => gcDelete(`/claim-statuses/${id}/`),

  // Discharge Types
  listDischargeTypes: (params?: Record<string, string>) => gcList("/discharge-types/", params),
  createDischargeType: (data: Record<string, unknown>) => gcPost("/discharge-types/", data),
  updateDischargeType: (id: string, data: Record<string, unknown>) => gcPatch(`/discharge-types/${id}/`, data),
  deleteDischargeType: (id: string) => gcDelete(`/discharge-types/${id}/`),

  // Correspondent Types
  listCorrespondentTypes: (params?: Record<string, string>) => gcList("/correspondent-types/", params),
  createCorrespondentType: (data: Record<string, unknown>) => gcPost("/correspondent-types/", data),
  updateCorrespondentType: (id: string, data: Record<string, unknown>) => gcPatch(`/correspondent-types/${id}/`, data),
  deleteCorrespondentType: (id: string) => gcDelete(`/correspondent-types/${id}/`),
}

// ---------------------------------------------------------------------------
// Quotations
// ---------------------------------------------------------------------------

export const gcQuotations = {
  list: (params?: Record<string, string>) => gcList("/quotations/", params),
  get: (id: string) => gcGet(`/quotations/${id}/`),
  create: (data: Record<string, unknown>) => gcPost("/quotations/", data),
  update: (id: string, data: Record<string, unknown>) => gcPatch(`/quotations/${id}/`, data),
  delete: (id: string) => gcDelete(`/quotations/${id}/`),
  approve: (id: string) => gcPost(`/quotations/${id}/approve/`),
  decline: (id: string, notes?: string) => gcPost(`/quotations/${id}/decline/`, notes ? { notes } : {}),
  convertToScheme: (id: string, data: Record<string, unknown>) => gcPost(`/quotations/${id}/convert-to-scheme/`, data),

  // Categories
  listCategories: (quotationId: string) => gcGet(`/quotations/${quotationId}/categories/`),
  createCategory: (quotationId: string, data: Record<string, unknown>) => gcPost(`/quotations/${quotationId}/categories/`, data),
  updateCategory: (quotationId: string, catId: string, data: Record<string, unknown>) => gcPatch(`/quotations/${quotationId}/categories/${catId}/`, data),
  deleteCategory: (quotationId: string, catId: string) => gcDelete(`/quotations/${quotationId}/categories/${catId}/`),

  // Riders
  listRiders: (quotationId: string) => gcGet(`/quotations/${quotationId}/riders/`),
  addRider: (quotationId: string, data: Record<string, unknown>) => gcPost(`/quotations/${quotationId}/riders/`, data),
  removeRider: (quotationId: string, riderId: string) => gcDelete(`/quotations/${quotationId}/riders/${riderId}/`),
}

// ---------------------------------------------------------------------------
// Schemes
// ---------------------------------------------------------------------------

export const gcSchemes = {
  list: (params?: Record<string, string>) => gcList("/schemes/", params),
  get: (id: string) => gcGet(`/schemes/${id}/`),
  create: (data: Record<string, unknown>) => gcPost("/schemes/", data),
  update: (id: string, data: Record<string, unknown>) => gcPatch(`/schemes/${id}/`, data),
  delete: (id: string) => gcDelete(`/schemes/${id}/`),
  dashboardSummary: () => gcGet("/schemes/dashboard-summary/"),

  // Categories
  listCategories: (schemeId: string) => gcGet(`/schemes/${schemeId}/categories/`),
  createCategory: (schemeId: string, data: Record<string, unknown>) => gcPost(`/schemes/${schemeId}/categories/`, data),
  updateCategory: (schemeId: string, catId: string, data: Record<string, unknown>) => gcPatch(`/schemes/${schemeId}/categories/${catId}/`, data),
  deleteCategory: (schemeId: string, catId: string) => gcDelete(`/schemes/${schemeId}/categories/${catId}/`),

  // Riders
  listRiders: (schemeId: string) => gcGet(`/schemes/${schemeId}/riders/`),
  addRider: (schemeId: string, data: Record<string, unknown>) => gcPost(`/schemes/${schemeId}/riders/`, data),
  removeRider: (schemeId: string, riderId: string) => gcDelete(`/schemes/${schemeId}/riders/${riderId}/`),

  // Members (nested under scheme)
  listMembers: (schemeId: string, params?: Record<string, string>) => gcList(`/schemes/${schemeId}/members/`, params),
  createMember: (schemeId: string, data: Record<string, unknown>) => gcPost(`/schemes/${schemeId}/members/`, data),
}

// ---------------------------------------------------------------------------
// Members (top-level)
// ---------------------------------------------------------------------------

export const gcMembers = {
  list: (params?: Record<string, string>) => gcList("/members/", params),
  get: (id: string) => gcGet(`/members/${id}/`),
  update: (id: string, data: Record<string, unknown>) => gcPatch(`/members/${id}/`, data),
  delete: (id: string) => gcDelete(`/members/${id}/`),

  // Dependents
  listDependents: (memberId: string) => gcGet(`/members/${memberId}/dependents/`),
  addDependent: (memberId: string, data: Record<string, unknown>) => gcPost(`/members/${memberId}/dependents/`, data),
  updateDependent: (memberId: string, depId: string, data: Record<string, unknown>) => gcPatch(`/members/${memberId}/dependents/${depId}/`, data),
  removeDependent: (memberId: string, depId: string) => gcDelete(`/members/${memberId}/dependents/${depId}/`),
}

// ---------------------------------------------------------------------------
// Claims
// ---------------------------------------------------------------------------

export const gcClaims = {
  list: (params?: Record<string, string>) => gcList("/claims/", params),
  get: (id: string) => gcGet(`/claims/${id}/`),
  create: (data: Record<string, unknown>) => gcPost("/claims/", data),
  update: (id: string, data: Record<string, unknown>) => gcPatch(`/claims/${id}/`, data),
  delete: (id: string) => gcDelete(`/claims/${id}/`),
  assess: (id: string, data: Record<string, unknown>) => gcPost(`/claims/${id}/assess/`, data),
  approve: (id: string, data: Record<string, unknown>) => gcPost(`/claims/${id}/approve/`, data),
  reject: (id: string, reason: string) => gcPost(`/claims/${id}/reject/`, { rejection_reason: reason }),
  pay: (id: string, amount: number) => gcPost(`/claims/${id}/pay/`, { amount }),

  // Installments
  listInstallments: (claimId: string) => gcGet(`/claims/${claimId}/installments/`),
  createInstallment: (claimId: string, data: Record<string, unknown>) => gcPost(`/claims/${claimId}/installments/`, data),
}

// ---------------------------------------------------------------------------
// Medical Cases
// ---------------------------------------------------------------------------

export const gcMedicalCases = {
  list: (params?: Record<string, string>) => gcList("/medical-cases/", params),
  get: (id: string) => gcGet(`/medical-cases/${id}/`),
  create: (data: Record<string, unknown>) => gcPost("/medical-cases/", data),
  update: (id: string, data: Record<string, unknown>) => gcPatch(`/medical-cases/${id}/`, data),
  makeDecision: (id: string, data: Record<string, unknown>) => gcPost(`/medical-cases/${id}/make-decision/`, data),
}

// ---------------------------------------------------------------------------
// Renewals
// ---------------------------------------------------------------------------

export const gcRenewals = {
  list: (params?: Record<string, string>) => gcList("/renewals/", params),
  get: (id: string) => gcGet(`/renewals/${id}/`),
  create: (data: Record<string, unknown>) => gcPost("/renewals/", data),
  update: (id: string, data: Record<string, unknown>) => gcPatch(`/renewals/${id}/`, data),
  approve: (id: string) => gcPost(`/renewals/${id}/approve/`),
}

// ---------------------------------------------------------------------------
// Medical Invoices
// ---------------------------------------------------------------------------

export const gcMedicalInvoices = {
  list: (params?: Record<string, string>) => gcList("/medical-invoices/", params),
  create: (data: Record<string, unknown>) => gcPost("/medical-invoices/", data),
  update: (id: string, data: Record<string, unknown>) => gcPatch(`/medical-invoices/${id}/`, data),
}
