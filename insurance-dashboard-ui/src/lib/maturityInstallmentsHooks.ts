import { keepPreviousData, useMutation, useQuery, useQueryClient, type UseMutationResult } from "@tanstack/react-query"
import {
  cancelMIPlan,
  confirmMIPayment,
  createMIPlan,
  getMIReconciliation,
  getMIFrequencyOptions,
  getMIPlanDetail,
  getMIPlanKpis,
  getMIPortalPlan,
  getMITermOptions,
  listMIPlans,
  listMIPortalPlans,
  printMIAdvice,
  printMISchedule,
  processMIPayment,
  reverseMIPayment,
  type MIFrequencyOption,
  type MICancelPayload,
  type MIPaginated,
  type MIPaymentResult,
  type MIPlanCreatePayload,
  type MIPlanCreateResult,
  type MIPlanDetail,
  type MIPlanKpis,
  type MIPlanListFilters,
  type MIPlanRecord,
  type MIPortalPlan,
  type MIPrintResult,
  type MIReconciliationReport,
  type MIReversePayload,
  type MITermOption,
} from "./maturityInstallments"

export const miPlanListKey = (filters: MIPlanListFilters = {}) => ["ol-maturity-installments", "list", filters] as const
export const miPlanKpisKey = (filters: MIPlanListFilters = {}) => ["ol-maturity-installments", "kpis", filters] as const
export const miFrequencyOptionsKey = (params: { q?: string; page?: number; pageSize?: number } = {}) => ["ol-maturity-installments", "options", "frequencies", params] as const
export const miTermOptionsKey = (params: { q?: string; product?: string; page?: number; pageSize?: number } = {}) => ["ol-maturity-installments", "options", "terms", params] as const
export const miPlanDetailKey = (id?: string | null) => ["ol-maturity-installments", "detail", id ?? "none"] as const
export const miReconciliationKey = (id?: string | null) => ["ol-maturity-installments", "reconciliation", id ?? "none"] as const
export const miPortalListKey = () => ["ol-maturity-installments", "portal", "list"] as const
export const miPortalDetailKey = (id?: string | null) => ["ol-maturity-installments", "portal", id ?? "none"] as const

export function invalidateMaturityInstallmentQueries(queryClient: ReturnType<typeof useQueryClient>, id?: string | null) {
  void queryClient.invalidateQueries({ queryKey: ["ol-maturity-installments", "list"] })
  void queryClient.invalidateQueries({ queryKey: ["ol-maturity-installments", "kpis"] })
  void queryClient.invalidateQueries({ queryKey: ["ol-maturity-installments", "options"] })
  if (id) {
    void queryClient.invalidateQueries({ queryKey: miPlanDetailKey(id) })
    void queryClient.invalidateQueries({ queryKey: miReconciliationKey(id) })
  }
}

export function useMIPlanList(filters: MIPlanListFilters = {}, enabled = true) {
  return useQuery<MIPaginated<MIPlanRecord>>({
    queryKey: miPlanListKey(filters),
    queryFn: () => listMIPlans(filters),
    enabled,
    placeholderData: keepPreviousData,
  })
}

export function useMIPlanKpis(filters: MIPlanListFilters = {}, enabled = true) {
  return useQuery<MIPlanKpis>({
    queryKey: miPlanKpisKey(filters),
    queryFn: () => getMIPlanKpis(filters),
    enabled,
    placeholderData: keepPreviousData,
  })
}

export function useMIFrequencyOptions(params: { q?: string; page?: number; pageSize?: number } = {}, enabled = true) {
  return useQuery<MIPaginated<MIFrequencyOption>>({
    queryKey: miFrequencyOptionsKey(params),
    queryFn: () => getMIFrequencyOptions(params),
    enabled,
    staleTime: 5 * 60 * 1000,
    placeholderData: keepPreviousData,
  })
}

export function useMITermOptions(params: { q?: string; product?: string; page?: number; pageSize?: number } = {}, enabled = true) {
  return useQuery<MIPaginated<MITermOption>>({
    queryKey: miTermOptionsKey(params),
    queryFn: () => getMITermOptions(params),
    enabled,
    staleTime: 5 * 60 * 1000,
    placeholderData: keepPreviousData,
  })
}

export function useMIPlanDetail(id?: string | null, enabled = true) {
  return useQuery<MIPlanDetail>({
    queryKey: miPlanDetailKey(id),
    queryFn: () => getMIPlanDetail(id as string),
    enabled: Boolean(id) && enabled,
  })
}

export function useMIReconciliation(id?: string | null, enabled = true) {
  return useQuery<MIReconciliationReport>({
    queryKey: miReconciliationKey(id),
    queryFn: () => getMIReconciliation(id as string),
    enabled: Boolean(id) && enabled,
  })
}

export interface MIPlanCreateVariables extends MIPlanCreatePayload {
  idempotencyKey: string
}

export function useCreateMIPlanMutation(): UseMutationResult<MIPlanCreateResult, Error, MIPlanCreateVariables> {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ idempotencyKey, policyId, maturityClaimId, frequency, termYears }: MIPlanCreateVariables) =>
      createMIPlan({ policyId, maturityClaimId, frequency, termYears }, idempotencyKey),
    onSuccess: (result) => invalidateMaturityInstallmentQueries(queryClient, result.plan?.id),
  })
}

export interface MIItemMutationVariables {
  itemId: string
}

export function useProcessItemPaymentMutation(): UseMutationResult<MIPaymentResult, Error, MIItemMutationVariables> {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ itemId }: MIItemMutationVariables) => processMIPayment(itemId),
    onSuccess: (result) => invalidateMaturityInstallmentQueries(queryClient, result.plan?.id ?? result.item?.planId),
  })
}

export function useConfirmItemPaymentMutation(): UseMutationResult<MIPaymentResult, Error, MIItemMutationVariables> {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ itemId }: MIItemMutationVariables) => confirmMIPayment(itemId),
    onSuccess: (result) => invalidateMaturityInstallmentQueries(queryClient, result.plan?.id ?? result.item?.planId),
  })
}

export function useReverseItemPaymentMutation(): UseMutationResult<MIPaymentResult, Error, MIItemMutationVariables & MIReversePayload> {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ itemId, reason }: MIItemMutationVariables & MIReversePayload) => reverseMIPayment(itemId, { reason }),
    onSuccess: (result) => invalidateMaturityInstallmentQueries(queryClient, result.plan?.id ?? result.item?.planId),
  })
}

export interface MIPlanCancelVariables extends MICancelPayload {
  planId: string
}

export function useCancelMIPlanMutation(): UseMutationResult<MIPlanDetail, Error, MIPlanCancelVariables> {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ planId, reason }: MIPlanCancelVariables) => cancelMIPlan(planId, { reason }),
    onSuccess: (result) => invalidateMaturityInstallmentQueries(queryClient, result?.id),
  })
}

export interface MIPlanPrintVariables {
  planId: string
}

export function usePrintMIScheduleMutation(): UseMutationResult<MIPrintResult, Error, MIPlanPrintVariables> {
  return useMutation({
    mutationFn: ({ planId }: MIPlanPrintVariables) => printMISchedule(planId),
  })
}

export function usePrintMIAdviceMutation(): UseMutationResult<MIPrintResult, Error, MIPlanPrintVariables> {
  return useMutation({
    mutationFn: ({ planId }: MIPlanPrintVariables) => printMIAdvice(planId),
  })
}

export function useMIPortalPlanList(enabled = true) {
  return useQuery<MIPortalPlan[]>({
    queryKey: miPortalListKey(),
    queryFn: () => listMIPortalPlans(),
    enabled,
    staleTime: 5 * 60 * 1000,
  })
}

export function useMIPortalPlanDetail(id?: string | null, enabled = true) {
  return useQuery<MIPortalPlan>({
    queryKey: miPortalDetailKey(id),
    queryFn: () => getMIPortalPlan(id as string),
    enabled: Boolean(id) && enabled,
    staleTime: 5 * 60 * 1000,
  })
}
