/**
 * Group Life — API Client
 *
 * Dedicated API functions for all Group Life endpoints.
 * Follows the established apiFetchAuth + extractError pattern.
 */

import { apiFetchAuth } from "./api"

const GL_BASE = "/api/v1/group-life"

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

async function glGet(path: string): Promise<any> {
  const res = await apiFetchAuth(`${GL_BASE}${path}`)
  const json = await res.json()
  if (!res.ok) throw new Error(extractError(res, json))
  return json.data ?? json.results ?? json
}

async function glPost(path: string, data?: Record<string, unknown>): Promise<any> {
  const res = await apiFetchAuth(`${GL_BASE}${path}`, {
    method: "POST",
    body: data ? JSON.stringify(data) : undefined,
  })
  const json = await res.json()
  if (!res.ok) throw new Error(extractError(res, json))
  return json.data ?? json
}

async function glPatch(path: string, data: Record<string, unknown>): Promise<any> {
  const res = await apiFetchAuth(`${GL_BASE}${path}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  })
  const json = await res.json()
  if (!res.ok) throw new Error(extractError(res, json))
  return json.data ?? json
}

async function glDelete(path: string): Promise<void> {
  const res = await apiFetchAuth(`${GL_BASE}${path}`, { method: "DELETE" })
  if (!res.ok) {
    const json = await res.json().catch(() => null)
    throw new Error(extractError(res, json))
  }
}

async function glList(path: string, params?: Record<string, string>): Promise<any> {
  const url = params
    ? `${GL_BASE}${path}?${new URLSearchParams(params).toString()}`
    : `${GL_BASE}${path}`
  const res = await apiFetchAuth(url)
  const json = await res.json()
  if (!res.ok) throw new Error(extractError(res, json))
  return json
}

// ---------------------------------------------------------------------------
// Setup / Parameter CRUD
// ---------------------------------------------------------------------------

export const glSetup = {
  listLookupValues: (params?: Record<string, string>) => glList("/setup/lookup-values/", params),
  getLookupValue: (id: string) => glGet("/setup/lookup-values/${id}/"),
  createLookupValue: (data: any) => glPost("/setup/lookup-values/", data),
  updateLookupValue: (id: string, data: any) => glPatch("/setup/lookup-values/${id}/", data),
  deleteLookupValue: (id: string) => glDelete("/setup/lookup-values/${id}/"),
  listSchemeTypes: (params?: Record<string, string>) => glList("/setup/scheme-types/", params),
  getSchemeType: (id: string) => glGet("/setup/scheme-types/${id}/"),
  createSchemeType: (data: any) => glPost("/setup/scheme-types/", data),
  updateSchemeType: (id: string, data: any) => glPatch("/setup/scheme-types/${id}/", data),
  deleteSchemeType: (id: string) => glDelete("/setup/scheme-types/${id}/"),
  listPremiumRates: (params?: Record<string, string>) => glList("/setup/premium-rates/", params),
  getPremiumRate: (id: string) => glGet("/setup/premium-rates/${id}/"),
  createPremiumRate: (data: any) => glPost("/setup/premium-rates/", data),
  updatePremiumRate: (id: string, data: any) => glPatch("/setup/premium-rates/${id}/", data),
  deletePremiumRate: (id: string) => glDelete("/setup/premium-rates/${id}/"),
  listMemberStatuses: (params?: Record<string, string>) => glList("/setup/member-statuses/", params),
  getMemberStatus: (id: string) => glGet("/setup/member-statuses/${id}/"),
  createMemberStatus: (data: any) => glPost("/setup/member-statuses/", data),
  updateMemberStatus: (id: string, data: any) => glPatch("/setup/member-statuses/${id}/", data),
  deleteMemberStatus: (id: string) => glDelete("/setup/member-statuses/${id}/"),
  listSchemeStatuses: (params?: Record<string, string>) => glList("/setup/scheme-statuses/", params),
  getSchemeStatus: (id: string) => glGet("/setup/scheme-statuses/${id}/"),
  createSchemeStatus: (data: any) => glPost("/setup/scheme-statuses/", data),
  updateSchemeStatus: (id: string, data: any) => glPatch("/setup/scheme-statuses/${id}/", data),
  deleteSchemeStatus: (id: string) => glDelete("/setup/scheme-statuses/${id}/"),
  listRenewalStatuses: (params?: Record<string, string>) => glList("/setup/renewal-statuses/", params),
  getRenewalStatus: (id: string) => glGet("/setup/renewal-statuses/${id}/"),
  createRenewalStatus: (data: any) => glPost("/setup/renewal-statuses/", data),
  updateRenewalStatus: (id: string, data: any) => glPatch("/setup/renewal-statuses/${id}/", data),
  deleteRenewalStatus: (id: string) => glDelete("/setup/renewal-statuses/${id}/"),
  listHealthQuestions: (params?: Record<string, string>) => glList("/setup/health-questions/", params),
  getHealthQuestion: (id: string) => glGet("/setup/health-questions/${id}/"),
  createHealthQuestion: (data: any) => glPost("/setup/health-questions/", data),
  updateHealthQuestion: (id: string, data: any) => glPatch("/setup/health-questions/${id}/", data),
  deleteHealthQuestion: (id: string) => glDelete("/setup/health-questions/${id}/"),
  listHealthQuestionnaires: (params?: Record<string, string>) => glList("/setup/health-questionnaires/", params),
  getHealthQuestionnaire: (id: string) => glGet("/setup/health-questionnaires/${id}/"),
  createHealthQuestionnaire: (data: any) => glPost("/setup/health-questionnaires/", data),
  updateHealthQuestionnaire: (id: string, data: any) => glPatch("/setup/health-questionnaires/${id}/", data),
  deleteHealthQuestionnaire: (id: string) => glDelete("/setup/health-questionnaires/${id}/"),
  listSubProducts: (params?: Record<string, string>) => glList("/setup/sub-products/", params),
  getSubProduct: (id: string) => glGet("/setup/sub-products/${id}/"),
  createSubProduct: (data: any) => glPost("/setup/sub-products/", data),
  updateSubProduct: (id: string, data: any) => glPatch("/setup/sub-products/${id}/", data),
  deleteSubProduct: (id: string) => glDelete("/setup/sub-products/${id}/"),
  listProducts: (params?: Record<string, string>) => glList("/setup/products/", params),
  getProduct: (id: string) => glGet("/setup/products/${id}/"),
  createProduct: (data: any) => glPost("/setup/products/", data),
  updateProduct: (id: string, data: any) => glPatch("/setup/products/${id}/", data),
  deleteProduct: (id: string) => glDelete("/setup/products/${id}/"),
  listRiders: (params?: Record<string, string>) => glList("/setup/riders/", params),
  getRider: (id: string) => glGet("/setup/riders/${id}/"),
  createRider: (data: any) => glPost("/setup/riders/", data),
  updateRider: (id: string, data: any) => glPatch("/setup/riders/${id}/", data),
  deleteRider: (id: string) => glDelete("/setup/riders/${id}/"),
  listRiderRates: (params?: Record<string, string>) => glList("/setup/rider-rates/", params),
  getRiderRate: (id: string) => glGet("/setup/rider-rates/${id}/"),
  createRiderRate: (data: any) => glPost("/setup/rider-rates/", data),
  updateRiderRate: (id: string, data: any) => glPatch("/setup/rider-rates/${id}/", data),
  deleteRiderRate: (id: string) => glDelete("/setup/rider-rates/${id}/"),
  listMedicalCodes: (params?: Record<string, string>) => glList("/setup/medical-codes/", params),
  getMedicalCode: (id: string) => glGet("/setup/medical-codes/${id}/"),
  createMedicalCode: (data: any) => glPost("/setup/medical-codes/", data),
  updateMedicalCode: (id: string, data: any) => glPatch("/setup/medical-codes/${id}/", data),
  deleteMedicalCode: (id: string) => glDelete("/setup/medical-codes/${id}/"),
  listMedicalLimits: (params?: Record<string, string>) => glList("/setup/medical-limits/", params),
  getMedicalLimit: (id: string) => glGet("/setup/medical-limits/${id}/"),
  createMedicalLimit: (data: any) => glPost("/setup/medical-limits/", data),
  updateMedicalLimit: (id: string, data: any) => glPatch("/setup/medical-limits/${id}/", data),
  deleteMedicalLimit: (id: string) => glDelete("/setup/medical-limits/${id}/"),
  listUnderwritingDecisions: (params?: Record<string, string>) => glList("/setup/uw-decisions/", params),
  getUnderwritingDecision: (id: string) => glGet("/setup/uw-decisions/${id}/"),
  createUnderwritingDecision: (data: any) => glPost("/setup/uw-decisions/", data),
  updateUnderwritingDecision: (id: string, data: any) => glPatch("/setup/uw-decisions/${id}/", data),
  deleteUnderwritingDecision: (id: string) => glDelete("/setup/uw-decisions/${id}/"),
  listPersonalHabits: (params?: Record<string, string>) => glList("/setup/personal-habits/", params),
  getPersonalHabit: (id: string) => glGet("/setup/personal-habits/${id}/"),
  createPersonalHabit: (data: any) => glPost("/setup/personal-habits/", data),
  updatePersonalHabit: (id: string, data: any) => glPatch("/setup/personal-habits/${id}/", data),
  deletePersonalHabit: (id: string) => glDelete("/setup/personal-habits/${id}/"),
  listMedicalHistories: (params?: Record<string, string>) => glList("/setup/medical-histories/", params),
  getMedicalHistory: (id: string) => glGet("/setup/medical-histories/${id}/"),
  createMedicalHistory: (data: any) => glPost("/setup/medical-histories/", data),
  updateMedicalHistory: (id: string, data: any) => glPatch("/setup/medical-histories/${id}/", data),
  deleteMedicalHistory: (id: string) => glDelete("/setup/medical-histories/${id}/"),
  listMedicalFacilities: (params?: Record<string, string>) => glList("/setup/medical-facilities/", params),
  getMedicalFacility: (id: string) => glGet("/setup/medical-facilities/${id}/"),
  createMedicalFacility: (data: any) => glPost("/setup/medical-facilities/", data),
  updateMedicalFacility: (id: string, data: any) => glPatch("/setup/medical-facilities/${id}/", data),
  deleteMedicalFacility: (id: string) => glDelete("/setup/medical-facilities/${id}/"),
  listMedicalPractitioners: (params?: Record<string, string>) => glList("/setup/medical-practitioners/", params),
  getMedicalPractitioner: (id: string) => glGet("/setup/medical-practitioners/${id}/"),
  createMedicalPractitioner: (data: any) => glPost("/setup/medical-practitioners/", data),
  updateMedicalPractitioner: (id: string, data: any) => glPatch("/setup/medical-practitioners/${id}/", data),
  deleteMedicalPractitioner: (id: string) => glDelete("/setup/medical-practitioners/${id}/"),
  listClaimTypes: (params?: Record<string, string>) => glList("/setup/claim-types/", params),
  getClaimType: (id: string) => glGet("/setup/claim-types/${id}/"),
  createClaimType: (data: any) => glPost("/setup/claim-types/", data),
  updateClaimType: (id: string, data: any) => glPatch("/setup/claim-types/${id}/", data),
  deleteClaimType: (id: string) => glDelete("/setup/claim-types/${id}/"),
  listClaimReasons: (params?: Record<string, string>) => glList("/setup/claim-reasons/", params),
  getClaimReason: (id: string) => glGet("/setup/claim-reasons/${id}/"),
  createClaimReason: (data: any) => glPost("/setup/claim-reasons/", data),
  updateClaimReason: (id: string, data: any) => glPatch("/setup/claim-reasons/${id}/", data),
  deleteClaimReason: (id: string) => glDelete("/setup/claim-reasons/${id}/"),
  listClaimStatuses: (params?: Record<string, string>) => glList("/setup/claim-statuses/", params),
  getClaimStatus: (id: string) => glGet("/setup/claim-statuses/${id}/"),
  createClaimStatus: (data: any) => glPost("/setup/claim-statuses/", data),
  updateClaimStatus: (id: string, data: any) => glPatch("/setup/claim-statuses/${id}/", data),
  deleteClaimStatus: (id: string) => glDelete("/setup/claim-statuses/${id}/"),
  listDischargeTypes: (params?: Record<string, string>) => glList("/setup/discharge-types/", params),
  getDischargeType: (id: string) => glGet("/setup/discharge-types/${id}/"),
  createDischargeType: (data: any) => glPost("/setup/discharge-types/", data),
  updateDischargeType: (id: string, data: any) => glPatch("/setup/discharge-types/${id}/", data),
  deleteDischargeType: (id: string) => glDelete("/setup/discharge-types/${id}/"),
  listCorrespondentTypes: (params?: Record<string, string>) => glList("/setup/correspondent-types/", params),
  getCorrespondentType: (id: string) => glGet("/setup/correspondent-types/${id}/"),
  createCorrespondentType: (data: any) => glPost("/setup/correspondent-types/", data),
  updateCorrespondentType: (id: string, data: any) => glPatch("/setup/correspondent-types/${id}/", data),
  deleteCorrespondentType: (id: string) => glDelete("/setup/correspondent-types/${id}/"),
  listMedicalInvoices: (params?: Record<string, string>) => glList("/medical-invoices/", params),
  getMedicalInvoice: (id: string) => glGet("/medical-invoices/${id}/"),
  createMedicalInvoice: (data: any) => glPost("/medical-invoices/", data),
  updateMedicalInvoice: (id: string, data: any) => glPatch("/medical-invoices/${id}/", data),
  deleteMedicalInvoice: (id: string) => glDelete("/medical-invoices/${id}/"),
}

export const glQuotations = {
  list: (params?: Record<string, string>) => glList("/quotations/", params),
  get: (id: string) => glGet(`/quotations/${id}/`),
  create: (data: Record<string, unknown>) => glPost("/quotations/", data),
  update: (id: string, data: Record<string, unknown>) => glPatch(`/quotations/${id}/`, data),
  delete: (id: string) => glDelete(`/quotations/${id}/`),
  approve: (id: string) => glPost(`/quotations/${id}/approve/`),
  decline: (id: string, notes?: string) => glPost(`/quotations/${id}/decline/`, notes ? { notes } : {}),
  convertToScheme: (id: string, data: Record<string, unknown>) => glPost(`/quotations/${id}/convert-to-scheme/`, data),

  // Categories
  listCategories: (quotationId: string) => glGet(`/quotations/${quotationId}/categories/`),
  createCategory: (quotationId: string, data: Record<string, unknown>) => glPost(`/quotations/${quotationId}/categories/`, data),
  updateCategory: (quotationId: string, catId: string, data: Record<string, unknown>) => glPatch(`/quotations/${quotationId}/categories/${catId}/`, data),
  deleteCategory: (quotationId: string, catId: string) => glDelete(`/quotations/${quotationId}/categories/${catId}/`),

  // Riders
  listRiders: (quotationId: string) => glGet(`/quotations/${quotationId}/riders/`),
  addRider: (quotationId: string, data: Record<string, unknown>) => glPost(`/quotations/${quotationId}/riders/`, data),
  removeRider: (quotationId: string, riderId: string) => glDelete(`/quotations/${quotationId}/riders/${riderId}/`),
}

// ---------------------------------------------------------------------------
// Schemes
// ---------------------------------------------------------------------------

export const glSchemes = {
  list: (params?: Record<string, string>) => glList("/schemes/", params),
  get: (id: string) => glGet(`/schemes/${id}/`),
  create: (data: Record<string, unknown>) => glPost("/schemes/", data),
  update: (id: string, data: Record<string, unknown>) => glPatch(`/schemes/${id}/`, data),
  delete: (id: string) => glDelete(`/schemes/${id}/`),
  dashboardSummary: () => glGet("/schemes/dashboard-summary/"),

  // Categories
  listCategories: (schemeId: string) => glGet(`/schemes/${schemeId}/categories/`),
  createCategory: (schemeId: string, data: Record<string, unknown>) => glPost(`/schemes/${schemeId}/categories/`, data),
  updateCategory: (schemeId: string, catId: string, data: Record<string, unknown>) => glPatch(`/schemes/${schemeId}/categories/${catId}/`, data),
  deleteCategory: (schemeId: string, catId: string) => glDelete(`/schemes/${schemeId}/categories/${catId}/`),

  // Riders
  listRiders: (schemeId: string) => glGet(`/schemes/${schemeId}/riders/`),
  addRider: (schemeId: string, data: Record<string, unknown>) => glPost(`/schemes/${schemeId}/riders/`, data),
  removeRider: (schemeId: string, riderId: string) => glDelete(`/schemes/${schemeId}/riders/${riderId}/`),

  // Members (nested under scheme)
  listMembers: (schemeId: string, params?: Record<string, string>) => glList(`/schemes/${schemeId}/members/`, params),
  createMember: (schemeId: string, data: Record<string, unknown>) => glPost(`/schemes/${schemeId}/members/`, data),
}

// ---------------------------------------------------------------------------
// Members (top-level)
// ---------------------------------------------------------------------------

export const glMembers = {
  list: (params?: Record<string, string>) => glList("/members/", params),
  get: (id: string) => glGet(`/members/${id}/`),
  update: (id: string, data: Record<string, unknown>) => glPatch(`/members/${id}/`, data),
  delete: (id: string) => glDelete(`/members/${id}/`),

  // Dependents
  listDependents: (memberId: string) => glGet(`/members/${memberId}/dependents/`),
  addDependent: (memberId: string, data: Record<string, unknown>) => glPost(`/members/${memberId}/dependents/`, data),
  updateDependent: (memberId: string, depId: string, data: Record<string, unknown>) => glPatch(`/members/${memberId}/dependents/${depId}/`, data),
  removeDependent: (memberId: string, depId: string) => glDelete(`/members/${memberId}/dependents/${depId}/`),
}

// ---------------------------------------------------------------------------
// Claims
// ---------------------------------------------------------------------------

export const glClaims = {
  list: (params?: Record<string, string>) => glList("/claims/", params),
  get: (id: string) => glGet(`/claims/${id}/`),
  create: (data: Record<string, unknown>) => glPost("/claims/", data),
  update: (id: string, data: Record<string, unknown>) => glPatch(`/claims/${id}/`, data),
  delete: (id: string) => glDelete(`/claims/${id}/`),
  assess: (id: string, data: Record<string, unknown>) => glPost(`/claims/${id}/assess/`, data),
  approve: (id: string, data: Record<string, unknown>) => glPost(`/claims/${id}/approve/`, data),
  reject: (id: string, reason: string) => glPost(`/claims/${id}/reject/`, { rejectionReason: reason }),
  pay: (id: string, amount: number) => glPost(`/claims/${id}/pay/`, { amount }),

  // Installments
  listInstallments: (claimId: string) => glGet(`/claims/${claimId}/installments/`),
  createInstallment: (claimId: string, data: Record<string, unknown>) => glPost(`/claims/${claimId}/installments/`, data),
}

// ---------------------------------------------------------------------------
// Medical Cases
// ---------------------------------------------------------------------------

export const glMedicalCases = {
  list: (params?: Record<string, string>) => glList("/medical-cases/", params),
  get: (id: string) => glGet(`/medical-cases/${id}/`),
  create: (data: Record<string, unknown>) => glPost("/medical-cases/", data),
  update: (id: string, data: Record<string, unknown>) => glPatch(`/medical-cases/${id}/`, data),
  makeDecision: (id: string, data: Record<string, unknown>) => glPost(`/medical-cases/${id}/make-decision/`, data),
}

// ---------------------------------------------------------------------------
// Renewals
// ---------------------------------------------------------------------------

export const glRenewals = {
  list: (params?: Record<string, string>) => glList("/renewals/", params),
  get: (id: string) => glGet(`/renewals/${id}/`),
  create: (data: Record<string, unknown>) => glPost("/renewals/", data),
  update: (id: string, data: Record<string, unknown>) => glPatch(`/renewals/${id}/`, data),
  approve: (id: string) => glPost(`/renewals/${id}/approve/`),
}

// ---------------------------------------------------------------------------
// Medical Invoices
// ---------------------------------------------------------------------------

export const glMedicalInvoices = {
  list: (params?: Record<string, string>) => glList("/medical-invoices/", params),
  create: (data: Record<string, unknown>) => glPost("/medical-invoices/", data),
  update: (id: string, data: Record<string, unknown>) => glPatch(`/medical-invoices/${id}/`, data),

  getSchemeType: (id: string) => glGet("/setup/scheme-types/${id}/"),
  getPremiumRate: (id: string) => glGet("/setup/premium-rates/${id}/"),
  listSchemeStatuss: (params?: Record<string, string>) => glGet("/setup/scheme-statuses/"),
  getSchemeStatus: (id: string) => glGet("/setup/scheme-statuses/${id}/"),
  getHealthQuestion: (id: string) => glGet("/setup/health-questions/${id}/"),
  createHealthQuestion: (data: any) => glPost("/setup/health-questions/", data),
  updateHealthQuestion: (id: string, data: any) => glPatch("/setup/health-questions/${id}/", data),
  deleteHealthQuestion: (id: string) => glDelete("/setup/health-questions/${id}/"),
  getHealthQuestionnaire: (id: string) => glGet("/setup/health-questionnaires/${id}/"),
  createHealthQuestionnaire: (data: any) => glPost("/setup/health-questionnaires/", data),
  updateHealthQuestionnaire: (id: string, data: any) => glPatch("/setup/health-questionnaires/${id}/", data),
  deleteHealthQuestionnaire: (id: string) => glDelete("/setup/health-questionnaires/${id}/"),
  getSubProduct: (id: string) => glGet("/setup/sub-products/${id}/"),
  deleteSubProduct: (id: string) => glDelete("/setup/sub-products/${id}/"),
  getMedicalCode: (id: string) => glGet("/setup/medical-codes/${id}/"),
  updateMedicalCode: (id: string, data: any) => glPatch("/setup/medical-codes/${id}/", data),
  deleteMedicalCode: (id: string) => glDelete("/setup/medical-codes/${id}/"),
  listMedicalHistories: (params?: Record<string, string>) => glGet("/setup/medical-histories/"),
  getMedicalFacility: (id: string) => glGet("/setup/medical-facilities/${id}/"),
  deleteMedicalFacility: (id: string) => glDelete("/setup/medical-facilities/${id}/"),
  getClaimType: (id: string) => glGet("/setup/claim-types/${id}/"),
  deleteClaimType: (id: string) => glDelete("/setup/claim-types/${id}/"),
}
