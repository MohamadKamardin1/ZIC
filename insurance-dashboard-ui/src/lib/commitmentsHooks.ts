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
  commitmentAction,
  generateCommitments,
  generateCommitmentsPreview,
  getCommitment,
  getCommitmentKPIs,
  getCommitmentOptions,
  importCommitmentRows,
  listCommitments,
  normalizeCommitment,
  normalizeDetail,
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
    mutationFn: importCommitmentRows,
    onSuccess: (result) => {
      if (result.imported > 0) invalidateCommitmentQueries(queryClient)
    },
  })
}

export function useProcessOverdueMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: processOverdueCommitments,
    onSuccess: () => invalidateCommitmentQueries(queryClient),
  })
}

/** Convenience: convert one raw row to a typed record client-side. */
export function normalizeCommitmentRow(row: Record<string, unknown>) {
  return normalizeCommitment(row)
}

export { normalizeDetail, normalizePaginated, commitmentAction, getCommitmentOptions }