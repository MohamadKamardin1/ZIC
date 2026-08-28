import { keepPreviousData, useMutation, useQuery, useQueryClient, type UseMutationResult } from "@tanstack/react-query"
import {
  addClaimFileNote,
  assessClaim,
  getClaim,
  getClaimFinancialSummary,
  getClaimKpis,
  getClaimOptions,
  listClaimDocuments,
  listClaimNotes,
  listClaims,
  printClaimDischargeVoucher,
  raiseClaimRequisition,
  registerClaim,
  requireMedicalReview,
  settleClaim,
  submitMedicalResult,
  uploadClaimDocument,
  type ClaimAction,
  type ClaimActionResult,
  type ClaimAssessmentPayload,
  type ClaimDetail,
  type ClaimDocumentsResult,
  type ClaimFileNote,
  type ClaimFinancialSummary,
  type ClaimKpis,
  type ClaimListFilters,
  type ClaimOption,
  type ClaimOptionKind,
  type ClaimPrintResult,
  type ClaimRecord,
  type ClaimRegisterPayload,
  type ClaimRequisitionPayload,
  type ClaimSettlementPayload,
  type MedicalRequirePayload,
  type MedicalResultPayload,
  type Paginated,
} from "./claims"

export const claimListKey = (filters: ClaimListFilters = {}) => ["ol-claims", "list", filters] as const
export const claimKpisKey = (filters: ClaimListFilters = {}) => ["ol-claims", "kpis", filters] as const
export const claimOptionsKey = (kind: ClaimOptionKind, params: Record<string, unknown> = {}) => ["ol-claims", "options", kind, params] as const
export const claimDetailKey = (id?: string | null) => ["ol-claims", "detail", id ?? "none"] as const
export const claimDocumentsKey = (id?: string | null, page = 1, pageSize = 20) => ["ol-claims", "documents", id ?? "none", page, pageSize] as const
export const claimNotesKey = (id?: string | null) => ["ol-claims", "notes", id ?? "none"] as const
export const claimFinancialSummaryKey = (id?: string | null) => ["ol-claims", "financial-summary", id ?? "none"] as const

export function invalidateClaimQueries(queryClient: ReturnType<typeof useQueryClient>, id?: string | null) {
  void queryClient.invalidateQueries({ queryKey: ["ol-claims", "list"] })
  void queryClient.invalidateQueries({ queryKey: ["ol-claims", "kpis"] })
  void queryClient.invalidateQueries({ queryKey: ["ol-claims", "options"] })
  if (id) {
    void queryClient.invalidateQueries({ queryKey: claimDetailKey(id) })
    void queryClient.invalidateQueries({ queryKey: ["ol-claims", "documents", id] })
    void queryClient.invalidateQueries({ queryKey: ["ol-claims", "notes", id] })
    void queryClient.invalidateQueries({ queryKey: ["ol-claims", "financial-summary", id] })
  }
}

export function useClaimList(filters: ClaimListFilters = {}, enabled = true) {
  return useQuery<Paginated<ClaimRecord>>({
    queryKey: claimListKey(filters),
    queryFn: () => listClaims(filters),
    enabled,
    placeholderData: keepPreviousData,
  })
}

export function useClaimKpis(filters: ClaimListFilters = {}, enabled = true) {
  return useQuery<ClaimKpis>({
    queryKey: claimKpisKey(filters),
    queryFn: () => getClaimKpis(filters),
    enabled,
    placeholderData: keepPreviousData,
  })
}

export function useClaimOptions(kind: ClaimOptionKind, params: { q?: string; page?: number; pageSize?: number; policyId?: string } = {}, enabled = true) {
  return useQuery<Paginated<ClaimOption>>({
    queryKey: claimOptionsKey(kind, params),
    queryFn: () => getClaimOptions(kind, params),
    enabled: Boolean(kind) && enabled,
    staleTime: 5 * 60 * 1000,
    placeholderData: keepPreviousData,
  })
}

export function useClaimDetail(id?: string | null, enabled = true) {
  return useQuery<ClaimDetail>({
    queryKey: claimDetailKey(id),
    queryFn: () => getClaim(id as string),
    enabled: Boolean(id) && enabled,
  })
}

export function useClaimDocuments(id?: string | null, page = 1, pageSize = 20, enabled = true) {
  return useQuery<ClaimDocumentsResult>({
    queryKey: claimDocumentsKey(id, page, pageSize),
    queryFn: () => listClaimDocuments(id as string, { page, pageSize }),
    enabled: Boolean(id) && enabled,
    placeholderData: keepPreviousData,
  })
}

export function useClaimNotes(id?: string | null, enabled = true) {
  return useQuery<ClaimFileNote[]>({
    queryKey: claimNotesKey(id),
    queryFn: () => listClaimNotes(id as string),
    enabled: Boolean(id) && enabled,
  })
}

export function useClaimFinancialSummary(id?: string | null, enabled = true) {
  return useQuery<ClaimFinancialSummary>({
    queryKey: claimFinancialSummaryKey(id),
    queryFn: () => getClaimFinancialSummary(id as string),
    enabled: Boolean(id) && enabled,
  })
}

export interface RegisterClaimVariables {
  policyId: string
  payload: ClaimRegisterPayload
  idempotencyKey?: string
}

export function useRegisterClaimMutation(): UseMutationResult<ClaimActionResult, Error, RegisterClaimVariables> {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ policyId, payload, idempotencyKey }: RegisterClaimVariables) => registerClaim(policyId, payload, idempotencyKey),
    onSuccess: (result) => invalidateClaimQueries(queryClient, result.claim?.id),
  })
}

export interface UploadClaimDocumentVariables {
  id: string
  documentType: string
  file: File
  fileReference?: string
  idempotencyKey?: string
}

export function useUploadClaimDocumentMutation(): UseMutationResult<ClaimDocumentsResult, Error, UploadClaimDocumentVariables> {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, documentType, file, fileReference = "", idempotencyKey }: UploadClaimDocumentVariables) =>
      uploadClaimDocument(id, documentType, file, fileReference, idempotencyKey),
    onSuccess: (_result, variables) => invalidateClaimQueries(queryClient, variables.id),
  })
}

export interface ClaimMutationVariables {
  id: string
}

export function useRequireMedicalReviewMutation(): UseMutationResult<ClaimDetail, Error, ClaimMutationVariables & MedicalRequirePayload> {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, reason = "" }: ClaimMutationVariables & MedicalRequirePayload) => requireMedicalReview(id, reason),
    onSuccess: (_result, variables) => invalidateClaimQueries(queryClient, variables.id),
  })
}

export function useSubmitMedicalResultMutation(): UseMutationResult<ClaimDetail, Error, ClaimMutationVariables & MedicalResultPayload> {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, result, reason = "", loadingFactor, loadingPercentage }: ClaimMutationVariables & MedicalResultPayload) =>
      submitMedicalResult(id, { result, reason, loadingFactor, loadingPercentage }),
    onSuccess: (_result, variables) => invalidateClaimQueries(queryClient, variables.id),
  })
}

export function useAssessClaimMutation(): UseMutationResult<ClaimDetail, Error, ClaimMutationVariables & ClaimAssessmentPayload> {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, assessedAmount, assessmentNotes, fraudFlag = false, fraudFlagReason = "", waiverOfPremiumDays = 0 }: ClaimMutationVariables & ClaimAssessmentPayload) =>
      assessClaim(id, { assessedAmount, assessmentNotes, fraudFlag, fraudFlagReason, waiverOfPremiumDays }),
    onSuccess: (_result, variables) => invalidateClaimQueries(queryClient, variables.id),
  })
}

export function useAddClaimFileNoteMutation(): UseMutationResult<ClaimFileNote, Error, ClaimMutationVariables & { noteText: string }> {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, noteText }: ClaimMutationVariables & { noteText: string }) => addClaimFileNote(id, noteText),
    onSuccess: (_result, variables) => invalidateClaimQueries(queryClient, variables.id),
  })
}

export function useRaiseClaimRequisitionMutation(): UseMutationResult<ClaimActionResult, Error, ClaimMutationVariables & ClaimRequisitionPayload> {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, bankDetails = {}, narration = "" }: ClaimMutationVariables & ClaimRequisitionPayload) =>
      raiseClaimRequisition(id, { bankDetails, narration }),
    onSuccess: (_result, variables) => invalidateClaimQueries(queryClient, variables.id),
  })
}

export function useSettleClaimMutation(): UseMutationResult<ClaimActionResult, Error, ClaimMutationVariables & ClaimSettlementPayload> {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, paymentReference, paymentStatus }: ClaimMutationVariables & ClaimSettlementPayload) =>
      settleClaim(id, { paymentReference, paymentStatus }),
    onSuccess: (_result, variables) => invalidateClaimQueries(queryClient, variables.id),
  })
}

export interface ClaimPrintVariables {
  id: string
}

export function usePrintClaimDischargeVoucherMutation(): UseMutationResult<ClaimPrintResult, Error, ClaimPrintVariables> {
  return useMutation({
    mutationFn: ({ id }: ClaimPrintVariables) => printClaimDischargeVoucher(id),
  })
}

export type { ClaimAction }
