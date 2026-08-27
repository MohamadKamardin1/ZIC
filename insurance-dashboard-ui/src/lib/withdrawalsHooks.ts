import { keepPreviousData, useMutation, useQuery, useQueryClient, type UseMutationResult } from "@tanstack/react-query"
import {
  getWithdrawal,
  getWithdrawalAudit,
  getWithdrawalBreakdown,
  getPortalWithdrawal,
  getWithdrawalEligibility,
  getWithdrawalKpis,
  getWithdrawalOptions,
  getWithdrawalPayments,
  estimateWithdrawal,
  listPortalWithdrawals,
  listWithdrawals,
  printWithdrawalStatement,
  requestPortalWithdrawal,
  requestWithdrawal,
  withdrawalAction,
  type Paginated,
  type WithdrawalAction,
  type WithdrawalActionResult,
  type WithdrawalAuditEntry,
  type WithdrawalBreakdown,
  type WithdrawalDetail,
  type WithdrawalEligibility,
  type WithdrawalEstimate,
  type WithdrawalKpis,
  type WithdrawalListFilters,
  type PortalWithdrawal,
  type PortalWithdrawalRequestPayload,
  type WithdrawalOption,
  type WithdrawalOptionKind,
  type WithdrawalPayment,
  type WithdrawalPrintResult,
  type WithdrawalRecord,
  type WithdrawalRequestPayload,
} from "./withdrawals"

export const portalWithdrawalListKey = (params: Record<string, unknown> = {}) => ["portal-withdrawals", "list", params] as const
export const portalWithdrawalDetailKey = (id?: string | null) => ["portal-withdrawals", "detail", id ?? "none"] as const
export const withdrawalListKey = (filters: WithdrawalListFilters = {}) => ["ol-withdrawals", "list", filters] as const
export const withdrawalKpisKey = (filters: WithdrawalListFilters = {}) => ["ol-withdrawals", "kpis", filters] as const
export const withdrawalOptionsKey = (kind: WithdrawalOptionKind, params: Record<string, unknown> = {}) => ["ol-withdrawals", "options", kind, params] as const
export const withdrawalDetailKey = (id?: string | null) => ["ol-withdrawals", "detail", id ?? "none"] as const
export const withdrawalEligibilityKey = (policyId?: string | null, asOf?: string) => ["ol-withdrawals", "eligibility", policyId ?? "none", asOf ?? "today"] as const
export const withdrawalBreakdownKey = (id?: string | null) => ["ol-withdrawals", "breakdown", id ?? "none"] as const
export const withdrawalPaymentsKey = (id?: string | null, page = 1, pageSize = 20) => ["ol-withdrawals", "payments", id ?? "none", page, pageSize] as const
export const withdrawalAuditKey = (id?: string | null, page = 1, pageSize = 20) => ["ol-withdrawals", "audit", id ?? "none", page, pageSize] as const

export function invalidateWithdrawalQueries(queryClient: ReturnType<typeof useQueryClient>, id?: string | null) {
  void queryClient.invalidateQueries({ queryKey: ["ol-withdrawals", "list"] })
  void queryClient.invalidateQueries({ queryKey: ["ol-withdrawals", "kpis"] })
  void queryClient.invalidateQueries({ queryKey: ["ol-withdrawals", "options"] })
  if (id) {
    void queryClient.invalidateQueries({ queryKey: withdrawalDetailKey(id) })
    void queryClient.invalidateQueries({ queryKey: withdrawalBreakdownKey(id) })
    void queryClient.invalidateQueries({ queryKey: ["ol-withdrawals", "payments", id] })
    void queryClient.invalidateQueries({ queryKey: ["ol-withdrawals", "audit", id] })
  }
}

export function usePortalWithdrawals(params: { q?: string; status?: string; page?: number; pageSize?: number } = {}, enabled = true) {
  return useQuery<Paginated<PortalWithdrawal>>({
    queryKey: portalWithdrawalListKey(params),
    queryFn: () => listPortalWithdrawals(params),
    enabled,
    placeholderData: keepPreviousData,
  })
}

export function usePortalWithdrawal(id?: string | null, enabled = true) {
  return useQuery<PortalWithdrawal>({
    queryKey: portalWithdrawalDetailKey(id),
    queryFn: () => getPortalWithdrawal(id as string),
    enabled: Boolean(id) && enabled,
  })
}

export function useWithdrawalList(filters: WithdrawalListFilters = {}, enabled = true) {
  return useQuery<Paginated<WithdrawalRecord>>({
    queryKey: withdrawalListKey(filters),
    queryFn: () => listWithdrawals(filters),
    enabled,
    placeholderData: keepPreviousData,
  })
}

export function useWithdrawalKpis(filters: WithdrawalListFilters = {}, enabled = true) {
  return useQuery<WithdrawalKpis>({
    queryKey: withdrawalKpisKey(filters),
    queryFn: () => getWithdrawalKpis(filters),
    enabled,
    placeholderData: keepPreviousData,
  })
}

export function useWithdrawalOptions(kind: WithdrawalOptionKind, params: { q?: string; page?: number; pageSize?: number; policyId?: string } = {}, enabled = true) {
  return useQuery<Paginated<WithdrawalOption>>({
    queryKey: withdrawalOptionsKey(kind, params),
    queryFn: () => getWithdrawalOptions(kind, params),
    enabled: Boolean(kind) && enabled,
    staleTime: 5 * 60 * 1000,
    placeholderData: keepPreviousData,
  })
}

export function useWithdrawalEligibility(policyId?: string | null, asOf?: string, enabled = true) {
  return useQuery<WithdrawalEligibility>({
    queryKey: withdrawalEligibilityKey(policyId, asOf),
    queryFn: () => getWithdrawalEligibility(policyId as string, asOf),
    enabled: Boolean(policyId) && enabled,
    staleTime: 30_000,
  })
}

export function useWithdrawalDetail(id?: string | null, enabled = true) {
  return useQuery<WithdrawalDetail>({
    queryKey: withdrawalDetailKey(id),
    queryFn: () => getWithdrawal(id as string),
    enabled: Boolean(id) && enabled,
  })
}

export function useWithdrawalBreakdown(id?: string | null, enabled = true) {
  return useQuery<WithdrawalBreakdown>({
    queryKey: withdrawalBreakdownKey(id),
    queryFn: () => getWithdrawalBreakdown(id as string),
    enabled: Boolean(id) && enabled,
  })
}

export function useWithdrawalPayments(id?: string | null, page = 1, pageSize = 20, enabled = true) {
  return useQuery<Paginated<WithdrawalPayment>>({
    queryKey: withdrawalPaymentsKey(id, page, pageSize),
    queryFn: () => getWithdrawalPayments(id as string, { page, pageSize }),
    enabled: Boolean(id) && enabled,
    placeholderData: keepPreviousData,
  })
}

export function useWithdrawalAudit(id?: string | null, page = 1, pageSize = 20, enabled = true) {
  return useQuery<Paginated<WithdrawalAuditEntry>>({
    queryKey: withdrawalAuditKey(id, page, pageSize),
    queryFn: () => getWithdrawalAudit(id as string, { page, pageSize }),
    enabled: Boolean(id) && enabled,
    placeholderData: keepPreviousData,
  })
}

export function useEstimateWithdrawalMutation() {
  return useMutation<WithdrawalEstimate, Error, { policyId: string; amount: string | number }>({
    mutationFn: ({ policyId, amount }) => estimateWithdrawal(policyId, amount),
  })
}

export function usePortalWithdrawalRequestMutation() {
  const queryClient = useQueryClient()
  return useMutation<WithdrawalActionResult, Error, PortalWithdrawalRequestPayload>({
    mutationFn: (payload) => requestPortalWithdrawal(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["portal-withdrawals"] })
      void queryClient.invalidateQueries({ queryKey: ["ol-withdrawals"] })
    },
  })
}

export interface RequestWithdrawalVariables {
  policyId: string
  payload: WithdrawalRequestPayload
  idempotencyKey?: string
}

export function useRequestWithdrawalMutation(): UseMutationResult<WithdrawalActionResult, Error, RequestWithdrawalVariables> {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ policyId, payload, idempotencyKey }: RequestWithdrawalVariables) => requestWithdrawal(policyId, payload, idempotencyKey),
    onSuccess: (result) => invalidateWithdrawalQueries(queryClient, result.withdrawal?.id),
  })
}

export interface WithdrawalActionVariables {
  id: string
  action: WithdrawalAction
  payload?: Record<string, unknown>
  idempotencyKey?: string
}

export function useWithdrawalActionMutation(): UseMutationResult<WithdrawalActionResult, Error, WithdrawalActionVariables> {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, action, payload = {}, idempotencyKey }: WithdrawalActionVariables) => withdrawalAction(id, action, payload, idempotencyKey),
    onSuccess: (result, variables) => invalidateWithdrawalQueries(queryClient, result.withdrawal?.id ?? variables.id),
  })
}

export interface PrintWithdrawalVariables {
  id: string
  payload?: Record<string, unknown>
}

export function usePrintWithdrawalStatementMutation(): UseMutationResult<WithdrawalPrintResult, Error, PrintWithdrawalVariables> {
  return useMutation({
    mutationFn: ({ id, payload = {} }: PrintWithdrawalVariables) => printWithdrawalStatement(id, payload),
  })
}
