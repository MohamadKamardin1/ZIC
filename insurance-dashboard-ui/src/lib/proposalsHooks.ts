/**
 * OL Proposals — TanStack Query hooks.
 *
 * One hook per API capability with a shared cache invalidation helper so
 * mutations keep the list, KPIs, and detail in sync. Query payloads are
 * normalized into camelCase view models (names, never UUIDs).
 */

import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  type ProposalDetail,
  type ProposalListFilters,
  type FirstPremiumStatusShape,
  addBeneficiary,
  cancelProposal,
  convertToPolicy,
  createProposalFromQuotation,
  deleteBeneficiary,
  enrichProposalSection,
  getFirstPremiumStatus,
  getHealthQuestions,
  getPaymentReadiness,
  getProposal,
  getProposalKPIs,
  getProposalOptions,
  listGeneratedDocuments,
  listProposals,
  listProposalDocuments,
  markPaymentReady,
  normalizeFirstPremium,
  normalizeKPIs,
  normalizePaginated,
  normalizeProposalDetail,
  normalizeProposalListItem,
  printProposal,
  type PrintResult,
  reactivateProposal,
  submitHealthAnswers,
  submitUnderwritingDecision,
  updateBeneficiary,
  uploadProposalDocument,
} from "./proposals"

export function proposalListKey(filters: ProposalListFilters = {}) {
  return ["proposals", "list", filters] as const
}

export const proposalKPIsKey = ["proposals", "kpis"] as const
export const proposalOptionsKey = (kind: string) => ["proposals", "options", kind] as const

export function proposalDetailKey(id?: string | null) {
  return ["proposals", "detail", id ?? "none"] as const
}

export function invalidateProposalQueries(
  queryClient: ReturnType<typeof useQueryClient>,
  id?: string | null,
) {
  void queryClient.invalidateQueries({ queryKey: ["proposals", "list"] })
  void queryClient.invalidateQueries({ queryKey: ["proposals", "kpis"] })
  void queryClient.invalidateQueries({ queryKey: ["proposals", "readiness"] })
  void queryClient.invalidateQueries({ queryKey: ["proposals", "first-premium"] })
  if (id) {
    void queryClient.invalidateQueries({ queryKey: ["proposals", "detail", id] })
    void queryClient.invalidateQueries({ queryKey: ["proposals", "documents", id] })
    void queryClient.invalidateQueries({ queryKey: ["proposals", "generated-documents", id] })
    void queryClient.invalidateQueries({ queryKey: ["proposals", "health-questions", id] })
    void queryClient.invalidateQueries({ queryKey: ["proposals", "first-premium", id] })
    void queryClient.invalidateQueries({ queryKey: ["proposals", "readiness", id] })
  }
}

export function useProposalList(filters: ProposalListFilters = {}) {
  return useQuery({
    queryKey: proposalListKey(filters),
    queryFn: async () => normalizePaginated(await listProposals(filters), normalizeProposalListItem),
    placeholderData: keepPreviousData,
  })
}

export function useProposalKPIs(enabled = true) {
  return useQuery({
    queryKey: proposalKPIsKey,
    queryFn: async () => normalizeKPIs(await getProposalKPIs()),
    enabled,
  })
}

export function useProposalDetail(id?: string | null, enabled = true) {
  return useQuery({
    queryKey: proposalDetailKey(id),
    queryFn: async () => (id ? (normalizeProposalDetail(await getProposal(id)) as ProposalDetail) : null),
    enabled: Boolean(id) && enabled,
  })
}

export function useCreateProposalFromQuotationMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (quotationId: string) => createProposalFromQuotation(quotationId),
    onSuccess: (data) => {
      const created = normalizeProposalDetail(data)
      invalidateProposalQueries(queryClient, created.id || undefined)
    },
  })
}

export interface EnrichSectionVariables {
  id: string
  section: string
  data: Record<string, unknown>
}

export function useEnrichSectionMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, section, data }: EnrichSectionVariables) => enrichProposalSection(id, section, data),
    onSuccess: (_data, variables) => invalidateProposalQueries(queryClient, variables.id),
  })
}

export interface BeneficiaryVariables {
  id: string
  beneficiaryId?: string
  data?: Record<string, unknown>
}

export function useAddBeneficiaryMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data = {} }: BeneficiaryVariables) => addBeneficiary(id, data),
    onSuccess: (_data, variables) => invalidateProposalQueries(queryClient, variables.id),
  })
}

export function useUpdateBeneficiaryMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, beneficiaryId, data = {} }: BeneficiaryVariables) =>
      updateBeneficiary(id, String(beneficiaryId), data),
    onSuccess: (_data, variables) => invalidateProposalQueries(queryClient, variables.id),
  })
}

export function useDeleteBeneficiaryMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, beneficiaryId }: BeneficiaryVariables) => deleteBeneficiary(id, String(beneficiaryId)),
    onSuccess: (_data, variables) => invalidateProposalQueries(queryClient, variables.id),
  })
}

export function useProposalDocuments(id?: string | null, enabled = true) {
  return useQuery({
    queryKey: ["proposals", "documents", id ?? "none"],
    queryFn: async () => normalizePaginated(await listProposalDocuments(String(id)), (row) => row),
    enabled: Boolean(id) && enabled,
  })
}

export function useUploadDocumentMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Record<string, unknown> }) => uploadProposalDocument(id, data),
    onSuccess: (_data, variables) => invalidateProposalQueries(queryClient, variables.id),
  })
}

export function useHealthQuestions(id?: string | null, enabled = true) {
  return useQuery({
    queryKey: ["proposals", "health-questions", id ?? "none"],
    queryFn: () => getHealthQuestions(String(id)),
    enabled: Boolean(id) && enabled,
  })
}

export function useSubmitHealthAnswersMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, answers }: { id: string; answers: Array<Record<string, unknown>> }) =>
      submitHealthAnswers(id, answers),
    onSuccess: (_data, variables) => invalidateProposalQueries(queryClient, variables.id),
  })
}

export interface UnderwritingDecisionVariables {
  id: string
  decision: "clear" | "load" | "decline"
  reason?: string
}

export function useUnderwritingDecisionMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, decision, reason }: UnderwritingDecisionVariables) =>
      submitUnderwritingDecision(id, { decision, reason }),
    onSuccess: (_data, variables) => invalidateProposalQueries(queryClient, variables.id),
  })
}

export function usePaymentReadiness(id?: string | null, enabled = true) {
  return useQuery({
    queryKey: ["proposals", "readiness", id ?? "none"],
    queryFn: async () => {
      const payload = await getPaymentReadiness(String(id))
      const record = payload && typeof payload === "object" ? (payload as Record<string, unknown>) : {}
      const items = Array.isArray(record.items) ? record.items : []
      return {
        passed: record.passed === true,
        items,
        status: typeof record.status === "string" ? record.status : undefined,
      } satisfies { passed: boolean; items: unknown[]; status?: string }
    },
    enabled: Boolean(id) && enabled,
  })
}

export function useMarkPaymentReadyMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => markPaymentReady(id),
    onSuccess: (_data, id) => invalidateProposalQueries(queryClient, id),
  })
}

export function useFirstPremiumStatus(id?: string | null, enabled = true) {
  return useQuery({
    queryKey: ["proposals", "first-premium", id ?? "none"],
    queryFn: async () => normalizeFirstPremium(await getFirstPremiumStatus(String(id))) as FirstPremiumStatusShape,
    enabled: Boolean(id) && enabled,
  })
}

export function useConvertToPolicyMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => convertToPolicy(id),
    onSuccess: (_data, id) => invalidateProposalQueries(queryClient, id),
  })
}

export interface CancelProposalVariables {
  id: string
  reason: string
}

export function useCancelProposalMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, reason }: CancelProposalVariables) => cancelProposal(id, reason),
    onSuccess: (_data, variables) => invalidateProposalQueries(queryClient, variables.id),
  })
}

export function useReactivateProposalMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => reactivateProposal(id),
    onSuccess: (_data, id) => invalidateProposalQueries(queryClient, id),
  })
}

export function usePrintProposalMutation() {
  return useMutation({
    mutationFn: (id: string): Promise<PrintResult> => printProposal(id),
  })
}

export function useGeneratedDocuments(id?: string | null, enabled = true) {
  return useQuery({
    queryKey: ["proposals", "generated-documents", id ?? "none"],
    queryFn: () => listGeneratedDocuments(String(id)),
    enabled: Boolean(id) && enabled,
  })
}

export function useProposalOptions(kind: string, enabled = true) {
  return useQuery({
    queryKey: proposalOptionsKey(kind),
    queryFn: () => getProposalOptions(kind),
    staleTime: 5 * 60 * 1000,
    enabled,
  })
}
