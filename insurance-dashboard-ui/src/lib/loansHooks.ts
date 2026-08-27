import { keepPreviousData, useMutation, useQuery, useQueryClient, type UseMutationResult } from "@tanstack/react-query"
import {
  createLoanRequest,
  getLoan,
  getLoanBalance,
  getLoanKPIs,
  getLoanOptions,
  getLoanSchedule,
  listLoans,
  loanAction,
  printLoanDocument,
  type LoanAction,
  type LoanActionResult,
  type LoanDetail,
  type LoanDisbursementPayload,
  type LoanListFilters,
  type LoanKpis,
  type LoanOption,
  type LoanOptionKind,
  type LoanPrintResult,
  type LoanRecord,
  type LoanRepaymentPayload,
  type LoanOffsetPayload,
  type LoanRequestPayload,
  type Paginated,
} from "./loans"

export const loanListKey = (filters: LoanListFilters = {}) => ["ol-loans", "list", filters] as const
export const loanKpisKey = (filters: LoanListFilters = {}) => ["ol-loans", "kpis", filters] as const
export const loanOptionsKey = (kind: LoanOptionKind, params: Record<string, unknown> = {}) => ["ol-loans", "options", kind, params] as const
export const loanDetailKey = (id?: string | null) => ["ol-loans", "detail", id ?? "none"] as const
export const loanBalanceKey = (id?: string | null) => ["ol-loans", "balance", id ?? "none"] as const
export const loanScheduleKey = (id?: string | null, page = 1, pageSize = 20) => ["ol-loans", "schedule", id ?? "none", page, pageSize] as const

export function invalidateLoanQueries(queryClient: ReturnType<typeof useQueryClient>, id?: string | null) {
  void queryClient.invalidateQueries({ queryKey: ["ol-loans", "list"] })
  void queryClient.invalidateQueries({ queryKey: ["ol-loans", "kpis"] })
  void queryClient.invalidateQueries({ queryKey: ["ol-loans", "options"] })
  if (id) {
    void queryClient.invalidateQueries({ queryKey: loanDetailKey(id) })
    void queryClient.invalidateQueries({ queryKey: loanBalanceKey(id) })
    void queryClient.invalidateQueries({ queryKey: ["ol-loans", "schedule", id] })
  }
}

export function useLoanList(filters: LoanListFilters = {}) {
  return useQuery<Paginated<LoanRecord>>({
    queryKey: loanListKey(filters),
    queryFn: () => listLoans(filters),
    placeholderData: keepPreviousData,
  })
}

export function useLoanKpis(filters: LoanListFilters = {}, enabled = true) {
  return useQuery<LoanKpis>({
    queryKey: loanKpisKey(filters),
    queryFn: () => getLoanKPIs(filters),
    enabled,
    placeholderData: keepPreviousData,
  })
}

export function useLoanOptions(kind: LoanOptionKind, params: { q?: string; page?: number; pageSize?: number; asOf?: string; productId?: string; planId?: string } = {}, enabled = true) {
  return useQuery<Paginated<LoanOption>>({
    queryKey: loanOptionsKey(kind, params),
    queryFn: () => getLoanOptions(kind, params),
    enabled: Boolean(kind) && enabled,
    staleTime: 5 * 60 * 1000,
    placeholderData: keepPreviousData,
  })
}

export function useLoanDetail(id?: string | null, enabled = true) {
  return useQuery<LoanDetail>({
    queryKey: loanDetailKey(id),
    queryFn: () => getLoan(id as string),
    enabled: Boolean(id) && enabled,
  })
}

export function useLoanBalance(id?: string | null, enabled = true) {
  return useQuery<Record<string, unknown>>({
    queryKey: loanBalanceKey(id),
    queryFn: () => getLoanBalance(id as string),
    enabled: Boolean(id) && enabled,
    staleTime: 30_000,
  })
}

export function useLoanSchedule(id?: string | null, page = 1, pageSize = 20, enabled = true) {
  return useQuery({
    queryKey: loanScheduleKey(id, page, pageSize),
    queryFn: () => getLoanSchedule(id as string, { page, pageSize }),
    enabled: Boolean(id) && enabled,
    placeholderData: keepPreviousData,
  })
}

export interface CreateLoanRequestVariables {
  policyId: string
  payload: LoanRequestPayload
  idempotencyKey?: string
}

export function useCreateLoanRequestMutation(): UseMutationResult<LoanActionResult, Error, CreateLoanRequestVariables> {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ policyId, payload, idempotencyKey }: CreateLoanRequestVariables) => createLoanRequest(policyId, payload, idempotencyKey),
    onSuccess: (result) => invalidateLoanQueries(queryClient, result.loan?.id),
  })
}

export interface LoanActionVariables {
  id: string
  action: LoanAction | string
  payload?: Record<string, unknown>
  idempotencyKey?: string
}

export function useLoanActionMutation(): UseMutationResult<LoanActionResult, Error, LoanActionVariables> {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, action, payload = {}, idempotencyKey }: LoanActionVariables) => loanAction(id, action, payload, idempotencyKey),
    onSuccess: (result, variables) => invalidateLoanQueries(queryClient, result.loan?.id ?? variables.id),
  })
}

export interface DisburseLoanVariables {
  id: string
  payload: LoanDisbursementPayload
  idempotencyKey?: string
}

export function useDisburseLoanMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, payload, idempotencyKey }: DisburseLoanVariables) => loanAction(id, "disburse", payload as unknown as Record<string, unknown>, idempotencyKey),
    onSuccess: (result, variables) => invalidateLoanQueries(queryClient, result.loan?.id ?? variables.id),
  })
}

export interface RepayLoanVariables {
  id: string
  payload: LoanRepaymentPayload
  idempotencyKey?: string
}

export function useRepayLoanMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, payload, idempotencyKey }: RepayLoanVariables) => loanAction(id, "repay", payload as unknown as Record<string, unknown>, idempotencyKey),
    onSuccess: (result, variables) => invalidateLoanQueries(queryClient, result.loan?.id ?? variables.id),
  })
}

export interface OffsetLoanVariables {
  id: string
  payload: LoanOffsetPayload
  idempotencyKey?: string
}

export function useOffsetLoanMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, payload, idempotencyKey }: OffsetLoanVariables) => loanAction(id, "offset", payload as unknown as Record<string, unknown>, idempotencyKey),
    onSuccess: (result, variables) => invalidateLoanQueries(queryClient, result.loan?.id ?? variables.id),
  })
}

export interface PrintLoanDocumentVariables {
  id: string
  documentType: "agreement" | "schedule"
}

export function usePrintLoanDocumentMutation(): UseMutationResult<LoanPrintResult, Error, PrintLoanDocumentVariables> {
  return useMutation({
    mutationFn: ({ id, documentType }: PrintLoanDocumentVariables) => printLoanDocument(id, documentType),
  })
}

export type { LoanDetail, LoanKpis, LoanOption, LoanRecord }
