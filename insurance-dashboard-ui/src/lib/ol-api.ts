/**
 * Ordinary Life — API Client
 *
 * Dedicated API functions for all Ordinary Life endpoints.
 */

import { apiFetchAuth } from "./api"

const OL_BASE = "/api/v1/ordinary-life"

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

async function olGet(path: string): Promise<any> {
  const res = await apiFetchAuth(`${OL_BASE}${path}`)
  const json = await res.json()
  if (!res.ok) throw new Error(extractError(res, json))
  return json.data ?? json.results ?? json
}

async function olPost(path: string, data?: Record<string, unknown>): Promise<any> {
  const res = await apiFetchAuth(`${OL_BASE}${path}`, {
    method: "POST",
    body: data ? JSON.stringify(data) : undefined,
  })
  const json = await res.json()
  if (!res.ok) throw new Error(extractError(res, json))
  return json.data ?? json
}

async function olPatch(path: string, data: Record<string, unknown>): Promise<any> {
  const res = await apiFetchAuth(`${OL_BASE}${path}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  })
  const json = await res.json()
  if (!res.ok) throw new Error(extractError(res, json))
  return json.data ?? json
}

async function olDelete(path: string): Promise<void> {
  const res = await apiFetchAuth(`${OL_BASE}${path}`, { method: "DELETE" })
  if (!res.ok) {
    const json = await res.json().catch(() => null)
    throw new Error(extractError(res, json))
  }
}

async function olList(path: string, params?: Record<string, string>): Promise<any> {
  const url = params
    ? `${OL_BASE}${path}?${new URLSearchParams(params).toString()}`
    : `${OL_BASE}${path}`
  const res = await apiFetchAuth(url)
  const json = await res.json()
  if (!res.ok) throw new Error(extractError(res, json))
  return json.data ?? json.results ?? json
}

// ---------------------------------------------------------------------------
// Setup API
// ---------------------------------------------------------------------------

export const olSetup = {
  listLookupValues: (params?: Record<string, string>) => olList("/setup/lookup-values/", params),
  getLookupValue: (id: string) => olGet("/setup/lookup-values/${id}/"),
  createLookupValue: (data: any) => olPost("/setup/lookup-values/", data),
  updateLookupValue: (id: string, data: any) => olPatch("/setup/lookup-values/${id}/", data),
  deleteLookupValue: (id: string) => olDelete("/setup/lookup-values/${id}/"),
  listDefaultSystemParameters: (params?: Record<string, string>) => olList("/setup/default-system-parameters/", params),
  getDefaultSystemParameter: (id: string) => olGet("/setup/default-system-parameters/${id}/"),
  createDefaultSystemParameter: (data: any) => olPost("/setup/default-system-parameters/", data),
  updateDefaultSystemParameter: (id: string, data: any) => olPatch("/setup/default-system-parameters/${id}/", data),
  deleteDefaultSystemParameter: (id: string) => olDelete("/setup/default-system-parameters/${id}/"),
  listOverrideCommissionSetups: (params?: Record<string, string>) => olList("/setup/override-commission-setup/", params),
  getOverrideCommissionSetup: (id: string) => olGet("/setup/override-commission-setup/${id}/"),
  createOverrideCommissionSetup: (data: any) => olPost("/setup/override-commission-setup/", data),
  updateOverrideCommissionSetup: (id: string, data: any) => olPatch("/setup/override-commission-setup/${id}/", data),
  deleteOverrideCommissionSetup: (id: string) => olDelete("/setup/override-commission-setup/${id}/"),
  listComputationApproaches: (params?: Record<string, string>) => olList("/setup/computation-approaches/", params),
  getComputationApproach: (id: string) => olGet("/setup/computation-approaches/${id}/"),
  createComputationApproach: (data: any) => olPost("/setup/computation-approaches/", data),
  updateComputationApproach: (id: string, data: any) => olPatch("/setup/computation-approaches/${id}/", data),
  deleteComputationApproach: (id: string) => olDelete("/setup/computation-approaches/${id}/"),
  listMaturityClaimSetups: (params?: Record<string, string>) => olList("/setup/maturity-claim-setup/", params),
  getMaturityClaimSetup: (id: string) => olGet("/setup/maturity-claim-setup/${id}/"),
  createMaturityClaimSetup: (data: any) => olPost("/setup/maturity-claim-setup/", data),
  updateMaturityClaimSetup: (id: string, data: any) => olPatch("/setup/maturity-claim-setup/${id}/", data),
  deleteMaturityClaimSetup: (id: string) => olDelete("/setup/maturity-claim-setup/${id}/"),
  listAnticipatedEndowmentInstallmentRates: (params?: Record<string, string>) => olList("/setup/anticipated-endowment-rates/", params),
  getAnticipatedEndowmentInstallmentRate: (id: string) => olGet("/setup/anticipated-endowment-rates/${id}/"),
  createAnticipatedEndowmentInstallmentRate: (data: any) => olPost("/setup/anticipated-endowment-rates/", data),
  updateAnticipatedEndowmentInstallmentRate: (id: string, data: any) => olPatch("/setup/anticipated-endowment-rates/${id}/", data),
  deleteAnticipatedEndowmentInstallmentRate: (id: string) => olDelete("/setup/anticipated-endowment-rates/${id}/"),
  listGracePeriods: (params?: Record<string, string>) => olList("/setup/grace-periods/", params),
  getGracePeriod: (id: string) => olGet("/setup/grace-periods/${id}/"),
  createGracePeriod: (data: any) => olPost("/setup/grace-periods/", data),
  updateGracePeriod: (id: string, data: any) => olPatch("/setup/grace-periods/${id}/", data),
  deleteGracePeriod: (id: string) => olDelete("/setup/grace-periods/${id}/"),
  listPolicyStatuses: (params?: Record<string, string>) => olList("/setup/policy-statuses/", params),
  getPolicyStatus: (id: string) => olGet("/setup/policy-statuses/${id}/"),
  createPolicyStatus: (data: any) => olPost("/setup/policy-statuses/", data),
  updatePolicyStatus: (id: string, data: any) => olPatch("/setup/policy-statuses/${id}/", data),
  deletePolicyStatus: (id: string) => olDelete("/setup/policy-statuses/${id}/"),
  listPolicyRenewalStatuses: (params?: Record<string, string>) => olList("/setup/policy-renewal-statuses/", params),
  getPolicyRenewalStatus: (id: string) => olGet("/setup/policy-renewal-statuses/${id}/"),
  createPolicyRenewalStatus: (data: any) => olPost("/setup/policy-renewal-statuses/", data),
  updatePolicyRenewalStatus: (id: string, data: any) => olPatch("/setup/policy-renewal-statuses/${id}/", data),
  deletePolicyRenewalStatus: (id: string) => olDelete("/setup/policy-renewal-statuses/${id}/"),
  listBeneficiaryTypes: (params?: Record<string, string>) => olList("/setup/beneficiary-types/", params),
  getBeneficiaryType: (id: string) => olGet("/setup/beneficiary-types/${id}/"),
  createBeneficiaryType: (data: any) => olPost("/setup/beneficiary-types/", data),
  updateBeneficiaryType: (id: string, data: any) => olPatch("/setup/beneficiary-types/${id}/", data),
  deleteBeneficiaryType: (id: string) => olDelete("/setup/beneficiary-types/${id}/"),
  listMemberCoverConfigurations: (params?: Record<string, string>) => olList("/setup/member-cover-configurations/", params),
  getMemberCoverConfiguration: (id: string) => olGet("/setup/member-cover-configurations/${id}/"),
  createMemberCoverConfiguration: (data: any) => olPost("/setup/member-cover-configurations/", data),
  updateMemberCoverConfiguration: (id: string, data: any) => olPatch("/setup/member-cover-configurations/${id}/", data),
  deleteMemberCoverConfiguration: (id: string) => olDelete("/setup/member-cover-configurations/${id}/"),
  listSurrenderSetups: (params?: Record<string, string>) => olList("/setup/surrender-setup/", params),
  getSurrenderSetup: (id: string) => olGet("/setup/surrender-setup/${id}/"),
  createSurrenderSetup: (data: any) => olPost("/setup/surrender-setup/", data),
  updateSurrenderSetup: (id: string, data: any) => olPatch("/setup/surrender-setup/${id}/", data),
  deleteSurrenderSetup: (id: string) => olDelete("/setup/surrender-setup/${id}/"),
  listPaidUpSetups: (params?: Record<string, string>) => olList("/setup/paid-up-setup/", params),
  getPaidUpSetup: (id: string) => olGet("/setup/paid-up-setup/${id}/"),
  createPaidUpSetup: (data: any) => olPost("/setup/paid-up-setup/", data),
  updatePaidUpSetup: (id: string, data: any) => olPatch("/setup/paid-up-setup/${id}/", data),
  deletePaidUpSetup: (id: string) => olDelete("/setup/paid-up-setup/${id}/"),
  listSurrenderValueRates: (params?: Record<string, string>) => olList("/setup/surrender-value-rates/", params),
  getSurrenderValueRate: (id: string) => olGet("/setup/surrender-value-rates/${id}/"),
  createSurrenderValueRate: (data: any) => olPost("/setup/surrender-value-rates/", data),
  updateSurrenderValueRate: (id: string, data: any) => olPatch("/setup/surrender-value-rates/${id}/", data),
  deleteSurrenderValueRate: (id: string) => olDelete("/setup/surrender-value-rates/${id}/"),
  listPaidUpRates: (params?: Record<string, string>) => olList("/setup/paid-up-rates/", params),
  getPaidUpRate: (id: string) => olGet("/setup/paid-up-rates/${id}/"),
  createPaidUpRate: (data: any) => olPost("/setup/paid-up-rates/", data),
  updatePaidUpRate: (id: string, data: any) => olPatch("/setup/paid-up-rates/${id}/", data),
  deletePaidUpRate: (id: string) => olDelete("/setup/paid-up-rates/${id}/"),
  listCommitmentStatuses: (params?: Record<string, string>) => olList("/setup/commitment-statuses/", params),
  getCommitmentStatus: (id: string) => olGet("/setup/commitment-statuses/${id}/"),
  createCommitmentStatus: (data: any) => olPost("/setup/commitment-statuses/", data),
  updateCommitmentStatus: (id: string, data: any) => olPatch("/setup/commitment-statuses/${id}/", data),
  deleteCommitmentStatus: (id: string) => olDelete("/setup/commitment-statuses/${id}/"),
  listHealthQuestions: (params?: Record<string, string>) => olList("/setup/health-questions/", params),
  getHealthQuestion: (id: string) => olGet("/setup/health-questions/${id}/"),
  createHealthQuestion: (data: any) => olPost("/setup/health-questions/", data),
  updateHealthQuestion: (id: string, data: any) => olPatch("/setup/health-questions/${id}/", data),
  deleteHealthQuestion: (id: string) => olDelete("/setup/health-questions/${id}/"),
  listHealthQuestionnaires: (params?: Record<string, string>) => olList("/setup/health-questionnaires/", params),
  getHealthQuestionnaire: (id: string) => olGet("/setup/health-questionnaires/${id}/"),
  createHealthQuestionnaire: (data: any) => olPost("/setup/health-questionnaires/", data),
  updateHealthQuestionnaire: (id: string, data: any) => olPatch("/setup/health-questionnaires/${id}/", data),
  deleteHealthQuestionnaire: (id: string) => olDelete("/setup/health-questionnaires/${id}/"),
  listGracePeriodNotificationSchedules: (params?: Record<string, string>) => olList("/setup/grace-period-notification-schedules/", params),
  getGracePeriodNotificationSchedule: (id: string) => olGet("/setup/grace-period-notification-schedules/${id}/"),
  createGracePeriodNotificationSchedule: (data: any) => olPost("/setup/grace-period-notification-schedules/", data),
  updateGracePeriodNotificationSchedule: (id: string, data: any) => olPatch("/setup/grace-period-notification-schedules/${id}/", data),
  deleteGracePeriodNotificationSchedule: (id: string) => olDelete("/setup/grace-period-notification-schedules/${id}/"),
  listReinstatementWindows: (params?: Record<string, string>) => olList("/setup/reinstatement-windows/", params),
  getReinstatementWindow: (id: string) => olGet("/setup/reinstatement-windows/${id}/"),
  createReinstatementWindow: (data: any) => olPost("/setup/reinstatement-windows/", data),
  updateReinstatementWindow: (id: string, data: any) => olPatch("/setup/reinstatement-windows/${id}/", data),
  deleteReinstatementWindow: (id: string) => olDelete(`/setup/reinstatement-windows/${id}/`),
}

// ---------------------------------------------------------------------------
// Core Operations API
// ---------------------------------------------------------------------------

export const olCore = {
  // PRODUCTS
  listProducts: (params?: Record<string, string>) => olList("/core/products/", params),
  getProduct: (id: string) => olGet(`/core/products/${id}/`),
  createProduct: (data: any) => olPost("/core/products/", data),
  updateProduct: (id: string, data: any) => olPatch(`/core/products/${id}/`, data),
  deleteProduct: (id: string) => olDelete(`/core/products/${id}/`),

  // CLIENTS
  listClients: (params?: Record<string, string>) => olList("/core/clients/", params),
  getClient: (id: string) => olGet(`/core/clients/${id}/`),
  createClient: (data: any) => olPost("/core/clients/", data),
  updateClient: (id: string, data: any) => olPatch(`/core/clients/${id}/`, data),
  deleteClient: (id: string) => olDelete(`/core/clients/${id}/`),

  // QUOTATIONS
  listQuotations: (params?: Record<string, string>) => olList("/core/quotations/", params),
  getQuotation: (id: string) => olGet(`/core/quotations/${id}/`),
  createQuotation: (data: any) => olPost("/core/quotations/", data),
  updateQuotation: (id: string, data: any) => olPatch(`/core/quotations/${id}/`, data),
  deleteQuotation: (id: string) => olDelete(`/core/quotations/${id}/`),

  // PROPOSALS
  listProposals: (params?: Record<string, string>) => olList("/core/proposals/", params),
  getProposal: (id: string) => olGet(`/core/proposals/${id}/`),
  createProposal: (data: any) => olPost("/core/proposals/", data),
  updateProposal: (id: string, data: any) => olPatch(`/core/proposals/${id}/`, data),
  deleteProposal: (id: string) => olDelete(`/core/proposals/${id}/`),

  // COMMITMENTS
  listCommitments: (params?: Record<string, string>) => olList("/core/commitments/", params),
  getCommitment: (id: string) => olGet(`/core/commitments/${id}/`),
  createCommitment: (data: any) => olPost("/core/commitments/", data),
  updateCommitment: (id: string, data: any) => olPatch(`/core/commitments/${id}/`, data),
  deleteCommitment: (id: string) => olDelete(`/core/commitments/${id}/`),

  // POLICIES
  listPolicies: (params?: Record<string, string>) => olList("/core/policies/", params),
  getPolicy: (id: string) => olGet(`/core/policies/${id}/`),
  createPolicy: (data: any) => olPost("/core/policies/", data),
  updatePolicy: (id: string, data: any) => olPatch(`/core/policies/${id}/`, data),
  deletePolicy: (id: string) => olDelete(`/core/policies/${id}/`),

  // LOANS
  listLoans: (params?: Record<string, string>) => olList("/core/loans/", params),
  getLoan: (id: string) => olGet(`/core/loans/${id}/`),
  createLoan: (data: any) => olPost("/core/loans/", data),
  updateLoan: (id: string, data: any) => olPatch(`/core/loans/${id}/`, data),
  deleteLoan: (id: string) => olDelete(`/core/loans/${id}/`),

  // WITHDRAWALS
  listWithdrawals: (params?: Record<string, string>) => olList("/core/withdrawals/", params),
  getWithdrawal: (id: string) => olGet(`/core/withdrawals/${id}/`),
  createWithdrawal: (data: any) => olPost("/core/withdrawals/", data),
  updateWithdrawal: (id: string, data: any) => olPatch(`/core/withdrawals/${id}/`, data),
  deleteWithdrawal: (id: string) => olDelete(`/core/withdrawals/${id}/`),

  // CLAIMS
  listClaims: (params?: Record<string, string>) => olList("/core/claims/", params),
  getClaim: (id: string) => olGet(`/core/claims/${id}/`),
  createClaim: (data: any) => olPost("/core/claims/", data),
  updateClaim: (id: string, data: any) => olPatch(`/core/claims/${id}/`, data),
  deleteClaim: (id: string) => olDelete(`/core/claims/${id}/`),

  // MATURITY INSTALLMENTS
  listMaturityInstallments: (params?: Record<string, string>) => olList("/core/maturity-installments/", params),
  getMaturityInstallment: (id: string) => olGet(`/core/maturity-installments/${id}/`),
  createMaturityInstallment: (data: any) => olPost("/core/maturity-installments/", data),
  updateMaturityInstallment: (id: string, data: any) => olPatch(`/core/maturity-installments/${id}/`, data),
  deleteMaturityInstallment: (id: string) => olDelete(`/core/maturity-installments/${id}/`),
}



// ---------------------------------------------------------------------------
// Phase 8 workflow API
// ---------------------------------------------------------------------------

export type OrdinaryLifeResource =
  | "applications"
  | "quotations"
  | "proposals"
  | "underwriting-cases"
  | "medical-requirements"
  | "policies"
  | "endorsements"
  | "renewals"
  | "reinstatements"
  | "premium-schedules"
  | "documents"
  | "notes"
  | "approvals"
  | "workflow-events"
  | "audit-history"
  | "payment-obligations"
  | "payment-allocations"
  | "commitments"
  | "loans"
  | "withdrawals"
  | "claims"
  | "maturity-installments"
  | "policy-transactions"
  | "policy-status-history"

export const olWorkflow = {
  list: (resource: OrdinaryLifeResource, params?: Record<string, string>) =>
    olList(`/core/${resource}/`, params),
  get: (resource: OrdinaryLifeResource, id: string) =>
    olGet(`/core/${resource}/${id}/`),
  create: (resource: OrdinaryLifeResource, data: Record<string, unknown>) =>
    olPost(`/core/${resource}/`, data),
  action: (resource: OrdinaryLifeResource, id: string, action: string, data: Record<string, unknown> = {}) =>
    olPost(`/core/${resource}/${id}/${action}/`, data),
  collectionAction: (resource: OrdinaryLifeResource, action: string, data: Record<string, unknown> = {}) =>
    olPost(`/core/${resource}/${action}/`, data),
}

export const olReference = {
  listProducts: (params?: Record<string, string>) => olList("/core/products/", params),
  listPlans: (params?: Record<string, string>) => olList("/core/plans/", params),
  listProductVersions: (params?: Record<string, string>) => olList("/core/product-versions/", params),
  listPartners: (params?: Record<string, string>) => olList("/core/clients/", params),
}
