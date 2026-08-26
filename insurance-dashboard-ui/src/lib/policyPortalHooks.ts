import { useQuery } from "@tanstack/react-query"
import { getPortalPolicy, listPortalPolicies, listPortalPolicyDocuments } from "./policyPortal"

export const portalPolicyListKey = ["policy-portal", "list"] as const
export const portalPolicyDetailKey = (id?: string | null) => ["policy-portal", "detail", id ?? "none"] as const
export const portalPolicyDocumentsKey = (id?: string | null) => ["policy-portal", "documents", id ?? "none"] as const

export function usePortalPolicies() {
  return useQuery({ queryKey: portalPolicyListKey, queryFn: listPortalPolicies })
}

export function usePortalPolicy(id?: string | null) {
  return useQuery({ queryKey: portalPolicyDetailKey(id), queryFn: () => getPortalPolicy(id as string), enabled: Boolean(id) })
}

export function usePortalPolicyDocuments(id?: string | null, enabled = true) {
  return useQuery({ queryKey: portalPolicyDocumentsKey(id), queryFn: () => listPortalPolicyDocuments(id as string), enabled: Boolean(id) && enabled })
}
