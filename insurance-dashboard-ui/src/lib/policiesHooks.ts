/** TanStack Query hooks for the Ordinary Life Policies bounded context. */

import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  approvePolicyLoan,
  createPolicyEndorsement,
  disbursePolicyLoan,
  getPolicy,
  getPolicyKpis,
  listPolicyBenefits,
  listPolicyMembers,
  listPolicyRiders,
  getPolicyOptions,
  issuePolicy,
  listPolicies,
  listPolicyEndorsements,
  listPolicyLoans,
  listPolicyOptions,
  listPolicyWithdrawals,
  normalizePolicyDetail,
  processPolicyMaturity,
  printPolicyContract,
  printPolicySchedule,
  repayPolicyLoan,
  requestPolicyLoan,
  requestPolicySurrender,
  requestPolicyWithdrawal,
  type PolicyDetail,
  type PolicyEndorsement,
  type PolicyKpis,
  type PolicyListItem,
  type PolicyListParams,
  type PolicyOption,
  type PolicyPrintResult,
} from "./policies"
import type { QueryParams } from "./apiClient"
import { listProposals, normalizePaginated, normalizeProposalListItem, type ProposalListItem } from "./proposals"

export const policyListKey = (filters: PolicyListParams = {}) => ["policies", "list", filters] as const
export const policyKpisKey = (filters: QueryParams = {}) => ["policies", "kpis", filters] as const
export const policyOptionsKey = (entity: string, params: QueryParams = {}) => ["policies", "options", entity, params] as const
export const policyDetailKey = (id?: string | null) => ["policies", "detail", id ?? "none"] as const
export const policyEndorsementsKey = (id?: string | null) => ["policies", "endorsements", id ?? "none"] as const
export const policyMembersKey = (id?: string | null) => ["policies", "members", id ?? "none"] as const
export const policyRidersKey = (id?: string | null) => ["policies", "riders", id ?? "none"] as const
export const policyBenefitsKey = (id?: string | null) => ["policies", "benefits", id ?? "none"] as const
export const policyLoansKey = (id?: string | null) => ["policies", "loans", id ?? "none"] as const
export const policyWithdrawalsKey = (id?: string | null) => ["policies", "withdrawals", id ?? "none"] as const

export function invalidatePolicyQueries(queryClient: ReturnType<typeof useQueryClient>, id?: string | null) {
  void queryClient.invalidateQueries({ queryKey: ["policies", "list"] })
  void queryClient.invalidateQueries({ queryKey: ["policies", "kpis"] })
  if (!id) return
  void queryClient.invalidateQueries({ queryKey: policyDetailKey(id) })
  void queryClient.invalidateQueries({ queryKey: policyEndorsementsKey(id) })
  void queryClient.invalidateQueries({ queryKey: policyMembersKey(id) })
  void queryClient.invalidateQueries({ queryKey: policyRidersKey(id) })
  void queryClient.invalidateQueries({ queryKey: policyBenefitsKey(id) })
  void queryClient.invalidateQueries({ queryKey: policyLoansKey(id) })
  void queryClient.invalidateQueries({ queryKey: policyWithdrawalsKey(id) })
}

export function usePolicyList(filters: PolicyListParams = {}) {
  return useQuery({
    queryKey: policyListKey(filters),
    queryFn: () => listPolicies(filters),
    placeholderData: keepPreviousData,
  })
}

export function usePolicyKpis(filters: QueryParams = {}, enabled = true) {
  return useQuery<PolicyKpis>({
    queryKey: policyKpisKey(filters),
    queryFn: () => getPolicyKpis(filters),
    enabled,
  })
}

export function usePolicyDetail(id?: string | null, enabled = true) {
  return useQuery<PolicyDetail | null>({
    queryKey: policyDetailKey(id),
    queryFn: () => id ? getPolicy(id).then(normalizePolicyDetail) : null,
    enabled: Boolean(id) && enabled,
  })
}

export function usePolicyOptions(entity: string, params: QueryParams = {}, enabled = true) {
  return useQuery<PolicyOption[]>({
    queryKey: policyOptionsKey(entity, params),
    queryFn: () => getPolicyOptions(entity, params),
    staleTime: 5 * 60 * 1000,
    enabled: Boolean(entity) && enabled,
  })
}

export function usePolicyOptionsPage(entity: string, params: QueryParams = {}, enabled = true) {
  return useQuery({
    queryKey: policyOptionsKey(entity, params),
    queryFn: () => listPolicyOptions(entity, params),
    staleTime: 5 * 60 * 1000,
    enabled: Boolean(entity) && enabled,
  })
}

export function useIssuableProposals(search = "", enabled = true) {
  return useQuery<ProposalListItem[]>({
    queryKey: ["policies", "issuable-proposals", search],
    queryFn: async () => {
      const [awaiting, ready] = await Promise.all([
        listProposals({ status: "AWAITING_FIRST_PREMIUM", search, page: 1, pageSize: 50 }),
        listProposals({ status: "PAYMENT_READY", search, page: 1, pageSize: 50 }),
      ])
      const rows = [...normalizePaginated(awaiting, normalizeProposalListItem).results, ...normalizePaginated(ready, normalizeProposalListItem).results]
      return rows.filter((row, index, all) => all.findIndex((candidate) => candidate.id === row.id) === index)
    },
    staleTime: 60 * 1000,
    enabled,
  })
}

export function usePolicyMembers(id?: string | null, enabled = true) {
  return useQuery({
    queryKey: policyMembersKey(id),
    queryFn: () => id ? listPolicyMembers(id) : [],
    enabled: Boolean(id) && enabled,
  })
}

export function usePolicyRiders(id?: string | null, enabled = true) {
  return useQuery({
    queryKey: policyRidersKey(id),
    queryFn: () => id ? listPolicyRiders(id) : [],
    enabled: Boolean(id) && enabled,
  })
}

export function usePolicyBenefits(id?: string | null, enabled = true) {
  return useQuery({
    queryKey: policyBenefitsKey(id),
    queryFn: () => id ? listPolicyBenefits(id) : [],
    enabled: Boolean(id) && enabled,
  })
}

export function usePolicyEndorsements(id?: string | null, enabled = true) {
  return useQuery({
    queryKey: policyEndorsementsKey(id),
    queryFn: () => id ? listPolicyEndorsements(id) : { results: [], count: 0, page: 1, pageSize: 0 },
    enabled: Boolean(id) && enabled,
  })
}

export function usePolicyLoans(id?: string | null, enabled = true) {
  return useQuery({
    queryKey: policyLoansKey(id),
    queryFn: () => id ? listPolicyLoans(id) : { results: [], count: 0, page: 1, pageSize: 0 },
    enabled: Boolean(id) && enabled,
  })
}

export function usePolicyWithdrawals(id?: string | null, enabled = true) {
  return useQuery({
    queryKey: policyWithdrawalsKey(id),
    queryFn: () => id ? listPolicyWithdrawals(id) : { results: [], count: 0, page: 1, pageSize: 0 },
    enabled: Boolean(id) && enabled,
  })
}

export function useIssuePolicyMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: issuePolicy,
    onSuccess: (data) => invalidatePolicyQueries(queryClient, typeof data.id === "string" ? data.id : undefined),
  })
}

export function useCreatePolicyEndorsementMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Record<string, unknown> }) => createPolicyEndorsement(id, payload),
    onSuccess: (_data, variables) => invalidatePolicyQueries(queryClient, variables.id),
  })
}

export function useRequestPolicyLoanMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Record<string, unknown> }) => requestPolicyLoan(id, payload),
    onSuccess: (_data, variables) => invalidatePolicyQueries(queryClient, variables.id),
  })
}

export function useApprovePolicyLoanMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ loanId, payload }: { loanId: string; payload?: Record<string, unknown> }) => approvePolicyLoan(loanId, payload),
    onSuccess: () => invalidatePolicyQueries(queryClient),
  })
}

export function useDisbursePolicyLoanMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ loanId, payload }: { loanId: string; payload?: Record<string, unknown> }) => disbursePolicyLoan(loanId, payload),
    onSuccess: () => invalidatePolicyQueries(queryClient),
  })
}

export function useRepayPolicyLoanMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ loanId, payload }: { loanId: string; payload: Record<string, unknown> }) => repayPolicyLoan(loanId, payload),
    onSuccess: () => invalidatePolicyQueries(queryClient),
  })
}

export function useRequestPolicyWithdrawalMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Record<string, unknown> }) => requestPolicyWithdrawal(id, payload),
    onSuccess: (_data, variables) => invalidatePolicyQueries(queryClient, variables.id),
  })
}

export function useRequestPolicySurrenderMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, payload = {} }: { id: string; payload?: Record<string, unknown> }) => requestPolicySurrender(id, payload),
    onSuccess: (_data, variables) => invalidatePolicyQueries(queryClient, variables.id),
  })
}

export function useProcessPolicyMaturityMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, payload = {} }: { id: string; payload?: Record<string, unknown> }) => processPolicyMaturity(id, payload),
    onSuccess: (_data, variables) => invalidatePolicyQueries(queryClient, variables.id),
  })
}

export function usePrintPolicyContractMutation() {
  return useMutation<PolicyPrintResult, Error, string>({ mutationFn: printPolicyContract })
}

export function usePrintPolicyScheduleMutation() {
  return useMutation<PolicyPrintResult, Error, string>({ mutationFn: printPolicySchedule })
}

export type { PolicyDetail, PolicyEndorsement, PolicyKpis, PolicyListItem, PolicyListParams, PolicyOption }
