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
  // Scheme Types
  listSchemeTypes: (params?: Record<string, string>) => glList("/setup/scheme-types/", params),
  createSchemeType: (data: Record<string, unknown>) => glPost("/setup/scheme-types/", data),
  updateSchemeType: (id: string, data: Record<string, unknown>) => glPatch(`/setup/scheme-types/${id}/`, data),
  deleteSchemeType: (id: string) => glDelete(`/setup/scheme-types/${id}/`),

  // Scheme Statuses
  listSchemeStatuses: (params?: Record<string, string>) => glList("/setup/scheme-statuses/", params),
  createSchemeStatus: (data: Record<string, unknown>) => glPost("/setup/scheme-statuses/", data),
  updateSchemeStatus: (id: string, data: Record<string, unknown>) => glPatch(`/setup/scheme-statuses/${id}/`, data),
  deleteSchemeStatus: (id: string) => glDelete(`/setup/scheme-statuses/${id}/`),

  // Member Statuses
  listMemberStatuses: (params?: Record<string, string>) => glList("/setup/member-statuses/", params),
  createMemberStatus: (data: Record<string, unknown>) => glPost("/setup/member-statuses/", data),
  updateMemberStatus: (id: string, data: Record<string, unknown>) => glPatch(`/setup/member-statuses/${id}/`, data),
  deleteMemberStatus: (id: string) => glDelete(`/setup/member-statuses/${id}/`),

  // Renewal Statuses
  listRenewalStatuses: (params?: Record<string, string>) => glList("/setup/renewal-statuses/", params),

  // Products
  listProducts: (params?: Record<string, string>) => glList("/setup/products/", params),
  getProduct: (id: string) => glGet(`/setup/products/${id}/`),
  createProduct: (data: Record<string, unknown>) => glPost("/setup/products/", data),
  updateProduct: (id: string, data: Record<string, unknown>) => glPatch(`/setup/products/${id}/`, data),
  deleteProduct: (id: string) => glDelete(`/setup/products/${id}/`),

  // Sub Products
  listSubProducts: (params?: Record<string, string>) => glList("/setup/sub-products/", params),
  createSubProduct: (data: Record<string, unknown>) => glPost("/setup/sub-products/", data),
  updateSubProduct: (id: string, data: Record<string, unknown>) => glPatch(`/setup/sub-products/${id}/`, data),

  // Riders
  listRiders: (params?: Record<string, string>) => glList("/setup/riders/", params),
  createRider: (data: Record<string, unknown>) => glPost("/setup/riders/", data),
  updateRider: (id: string, data: Record<string, unknown>) => glPatch(`/setup/riders/${id}/`, data),

  // Premium Rates
  listPremiumRates: (params?: Record<string, string>) => glList("/setup/premium-rates/", params),
  createPremiumRate: (data: Record<string, unknown>) => glPost("/setup/premium-rates/", data),
  updatePremiumRate: (id: string, data: Record<string, unknown>) => glPatch(`/setup/premium-rates/${id}/`, data),
  deletePremiumRate: (id: string) => glDelete(`/setup/premium-rates/${id}/`),

  // Claim Types
  listClaimTypes: (params?: Record<string, string>) => glList("/setup/claim-types/", params),
  createClaimType: (data: Record<string, unknown>) => glPost("/setup/claim-types/", data),
  updateClaimType: (id: string, data: Record<string, unknown>) => glPatch(`/setup/claim-types/${id}/`, data),

  // Claim Statuses
  listClaimStatuses: (params?: Record<string, string>) => glList("/setup/claim-statuses/", params),
  createClaimStatus: (data: Record<string, unknown>) => glPost("/setup/claim-statuses/", data),
  updateClaimStatus: (id: string, data: Record<string, unknown>) => glPatch(`/setup/claim-statuses/${id}/`, data),

  // Medical Codes
  listMedicalCodes: (params?: Record<string, string>) => glList("/setup/medical-codes/", params),
  createMedicalCode: (data: Record<string, unknown>) => glPost("/setup/medical-codes/", data),

  // Medical Facilities
  listMedicalFacilities: (params?: Record<string, string>) => glList("/setup/medical-facilities/", params),
  createMedicalFacility: (data: Record<string, unknown>) => glPost("/setup/medical-facilities/", data),
  updateMedicalFacility: (id: string, data: Record<string, unknown>) => glPatch(`/setup/medical-facilities/${id}/`, data),

  // UW Decisions
  listUWDecisions: (params?: Record<string, string>) => glList("/setup/uw-decisions/", params),

  // Health Questions & Questionnaires
  listHealthQuestions: (params?: Record<string, string>) => glList("/setup/health-questions/", params),
  listHealthQuestionnaires: (params?: Record<string, string>) => glList("/setup/health-questionnaires/", params),
}

// ---------------------------------------------------------------------------
// Quotations
// ---------------------------------------------------------------------------

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
}
