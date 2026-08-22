/**
 * Commitments — TanStack Query hooks.
 *
 * One hook per API capability (list + KPIs, detail, options, actions,
 * generation preview/execute, import, process-overdue) with a shared cache
 * invalidation helper so mutations keep the list, KPI cards, and detail in sync.
 */

import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  type CommitmentAction,
  type CommitmentDetail,
  type CommitmentListFilters,
  type CommitmentOptions,
  type CommitmentSourceType,
  commitmentAction,
  createManualCommitment,
  generateCommitments,
  generateCommitmentsPreview,
  getCommitment,
  getCommitmentKPIs,
  getCommitmentOptions,
  getCommitmentReferenceOptions,
  getCommitmentSources,
  importCommitmentRows,
  listCommitments,
  getCommitmentImport,
  getLapseReviewQueue,
  getOverdueNotifications,
  listCommitmentImports,
  normalizeCommitment,
  normalizeDetail,
  normalizeImportHistory,
  normalizeLapseReviewRows,
  normalizeOverdueNotifications,
  normalizePaginated,
  processOverdueCommitments,
} from "./commitments"

export function commitmentListKey(filters: CommitmentListFilters = {}) {
  return ["commitments", "list", filters] as const
}

export const commitmentKPIsKey = ["commitments", "kpis"] as const
export const commitmentOptionsKey = ["commitments", "options"] as const

export function commitmentDetailKey(id?: string | null) {
  return ["commitments", "detail", id ?? "none"] as const
}

export function invalidateCommitmentQueries(queryClient: ReturnType<typeof useQueryClient>, id?: string | null) {
  void queryClient.invalidateQueries({ queryKey: ["commitments", "list"] })
  void queryClient.invalidateQueries({ queryKey: ["commitments", "kpis"] })
  void queryClient.invalidateQueries({ queryKey: ["commitments", "options"] })
  if (id) void queryClient.invalidateQueries({ queryKey: ["commitments", "detail", id] })
}

export function useCommitmentList(filters: CommitmentListFilters = {}) {
  return useQuery({
    queryKey: commitmentListKey(filters),
    queryFn: async ({ signal }) => normalizePaginated(await listCommitments(filters)),
    placeholderData: keepPreviousData,
  })
}

export function useCommitmentKPIs(enabled = true) {
  return useQuery({
    queryKey: commitmentKPIsKey,
    queryFn: () => getCommitmentKPIs(),
    enabled,
  })
}

export function useCommitmentDetail(id?: string | null, enabled = true) {
  return useQuery({
    queryKey: commitmentDetailKey(id),
    queryFn: async () => (id ? normalizeDetail(await getCommitment(id)) : ({} as CommitmentDetail)),
    enabled: Boolean(id) && enabled,
  })
}

export function useCommitmentOptions() {
  return useQuery({
    queryKey: commitmentOptionsKey,
    queryFn: () => getCommitmentOptions(),
    staleTime: 5 * 60 * 1000,
  })
}

export interface CommitmentActionVariables {
  id: string
  action: CommitmentAction | string
  payload?: Record<string, unknown>
}

export function useCommitmentActionMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, action, payload = {} }: CommitmentActionVariables) => commitmentAction(id, action, payload),
    onSuccess: (_data, variables) => {
      invalidateCommitmentQueries(queryClient, variables.id)
    },
    onError: (_error, variables) => {
      void queryClient.cancelQueries({ queryKey: commitmentDetailKey(variables.id) })
    },
  })
}

export function useGenerateCommitmentsMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: generateCommitments,
    onSuccess: () => invalidateCommitmentQueries(queryClient),
  })
}

export function useGenerateCommitmentsPreviewMutation() {
  return useMutation({ mutationFn: generateCommitmentsPreview })
}

export function useImportCommitmentsMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ rows, dryRun = false }: { rows: Record<string, unknown>[]; dryRun?: boolean }) =>
      importCommitmentRows({ rows }, { dryRun }),
    onSuccess: (result) => {
      if (result.imported > 0 || result.created > 0) invalidateCommitmentQueries(queryClient)
      void queryClient.invalidateQueries({ queryKey: ["commitments", "imports"] })
    },
  })
}

export function useCommitmentImports() {
  return useQuery({
    queryKey: ["commitments", "imports"],
    queryFn: async () => normalizeImportHistory(await listCommitmentImports()),
    staleTime: 30_000,
  })
}

export function useCommitmentImportDetail(id?: string | null) {
  return useQuery({
    queryKey: ["commitments", "imports", "detail", id ?? "none"],
    queryFn: () => (id ? getCommitmentImport(id) : null),
    enabled: Boolean(id),
  })
}

export function useLapseReviewQueue() {
  return useQuery({
    queryKey: ["commitments", "lapse-review"],
    queryFn: async () => normalizeLapseReviewRows(await getLapseReviewQueue()),
    staleTime: 30_000,
  })
}

export function useOverdueNotifications() {
  return useQuery({
    queryKey: ["commitments", "notifications", "overdue"],
    queryFn: async () => normalizeOverdueNotifications(await getOverdueNotifications()),
    staleTime: 30_000,
  })
}

export function useProcessOverdueMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: processOverdueCommitments,
    onSuccess: () => invalidateCommitmentQueries(queryClient),
  })
}

export function useCommitmentSources(sourceType: CommitmentSourceType | null) {
  return useQuery({
    queryKey: ["commitments", "sources", sourceType ?? "none"],
    queryFn: () => getCommitmentSources(sourceType as CommitmentSourceType),
    enabled: Boolean(sourceType) && sourceType !== "MANUAL",
    staleTime: 30_000,
  })
}

export function useCommitmentReferenceOptions() {
  return useQuery({
    queryKey: ["commitments", "references"],
    queryFn: getCommitmentReferenceOptions,
    staleTime: 5 * 60 * 1000,
  })
}

export function useCreateManualCommitmentMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createManualCommitment,
    onSuccess: (commitment) => {
      invalidateCommitmentQueries(queryClient, commitment?.id)
    },
  })
}

/** Convenience: convert one raw row to a typed record client-side. */
export function normalizeCommitmentRow(row: Record<string, unknown>) {
  return normalizeCommitment(row)
}

export { normalizeDetail, normalizePaginated, commitmentAction, getCommitmentOptions }