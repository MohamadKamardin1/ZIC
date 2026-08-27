import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { createPortalLoanRequest, getPortalLoan, listPortalLoans, type PortalLoanRequestPayload } from "./loanPortal"

export const portalLoanListKey = ["loan-portal", "list"] as const
export const portalLoanDetailKey = (loanNumber?: string | null) => ["loan-portal", "detail", loanNumber ?? "none"] as const

export function usePortalLoans() {
  return useQuery({
    queryKey: portalLoanListKey,
    queryFn: listPortalLoans,
  })
}

export function usePortalLoan(loanNumber?: string | null) {
  return useQuery({
    queryKey: portalLoanDetailKey(loanNumber),
    queryFn: () => getPortalLoan(loanNumber as string),
    enabled: Boolean(loanNumber),
  })
}

export interface PortalLoanRequestVariables {
  payload: PortalLoanRequestPayload
  idempotencyKey: string
}

export function usePortalLoanRequestMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ payload, idempotencyKey }: PortalLoanRequestVariables) => createPortalLoanRequest(payload, idempotencyKey),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: portalLoanListKey })
    },
  })
}
