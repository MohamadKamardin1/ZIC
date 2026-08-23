import { useState } from "react"
import { AlertTriangle, CheckCircle2, ExternalLink, Landmark } from "lucide-react"
import { ErrorCoach } from "../../components/commitments/ErrorCoach"
import { Modal } from "../../components/ui/Overlays"
import { StatusBadge } from "../../components/ui/StatusBadge"
import { commitmentStatusLabel, commitmentStatusTone } from "../../components/commitments/CommitmentStatusBadge"
import { useConvertToPolicyMutation, useFirstPremiumStatus } from "../../lib/proposalsHooks"
import type { FirstPremiumStatusShape } from "../../lib/proposals"
import { ApiClientError } from "../../lib/apiClient"

function money(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—"
  return value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

/** BR-03 status summary rendered from the first-premium endpoint. */
function Br03Summary({ status }: { status: FirstPremiumStatusShape }) {
  return (
    <div className="rounded-[10px] border border-[var(--border)] p-3" data-testid="br03-summary">
      <div className="mb-2 flex items-center justify-between gap-2">
        <p className="flex items-center gap-2 text-sm font-bold">
          <Landmark size={15} aria-hidden="true" />
          BR-03 · first premium check
        </p>
        {status.linked ? (
          <span className={`inline-flex items-center gap-1 text-xs font-bold ${status.posted ? "text-[var(--success)]" : "text-[var(--warning)]"}`}>
            {status.posted ? <CheckCircle2 size={14} aria-hidden="true" /> : <AlertTriangle size={14} aria-hidden="true" />}
            {status.posted ? "Posted" : "Not posted"}
          </span>
        ) : (
          <span className="text-xs font-bold text-[var(--muted-foreground)]">No commitment</span>
        )}
      </div>
      {status.linked ? (
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-[var(--muted-foreground)]">
          {status.commitmentNumber && <span className="font-mono font-bold text-[var(--foreground)]">{status.commitmentNumber}</span>}
          {status.commitmentStatus && (
            <StatusBadge value={commitmentStatusLabel(status.commitmentStatus)} tone={commitmentStatusTone(status.commitmentStatus)} />
          )}
          <span>Due {money(status.amountDue)}</span>
          <span>Paid {money(status.amountPaid)}</span>
          <span>Balance {money(status.balance)}</span>
        </div>
      ) : (
        <p className="text-xs leading-5 text-[var(--muted-foreground)]">
          The first premium commitment has not been generated yet.
        </p>
      )}
    </div>
  )
}

/**
 * Convert-to-Policy modal (BR-03 gated).
 *
 * Shows the live BR-03 status; blocks with PROPOSAL_FIRST_PREMIUM_NOT_POSTED
 * until the commitment is fully allocated, then confirms before issuing and
 * finally surfaces the issued policy number as a link plus lifecycle context.
 */
export function OLConvertToPolicyModal({
  open,
  proposalId,
  policyNumber: linkedPolicyNumber,
  onClose,
  onError,
}: {
  open: boolean
  proposalId: string
  policyNumber?: string | null
  onClose: () => void
  onError: (error: unknown) => void
}) {
  const statusQuery = useFirstPremiumStatus(proposalId, open)
  const status = statusQuery.data ?? null
  const convert = useConvertToPolicyMutation()
  const [issuedPolicyNumber, setIssuedPolicyNumber] = useState<string | null>(null)
  const [confirmed, setConfirmed] = useState(false)

  const br03Blocked = Boolean(status && (!status.linked || !status.posted))
  const busy = statusQuery.isLoading || convert.isPending

  const close = () => {
    setIssuedPolicyNumber(null)
    setConfirmed(false)
    onClose()
  }

  const issuePolicy = () => {
    if (br03Blocked) return
    onError(null)
    convert.mutate(proposalId, {
      onSuccess: (payload) => {
        const record = (payload ?? {}) as Record<string, unknown>
        setIssuedPolicyNumber(String(record.policy_number ?? ""))
      },
      onError: (error) => onError(error),
    })
  }

  if (issuedPolicyNumber) {
    return (
      <Modal open={open} title="Policy issued" onClose={close} size="sm">
        <div className="space-y-3 text-center" data-testid="convert-success">
          <CheckCircle2 size={34} className="mx-auto text-[var(--success)]" aria-hidden="true" />
          <p className="text-sm font-semibold">The proposal was converted into a policy.</p>
          <a
            href={`/ordinary-life/policies?policy_number=${encodeURIComponent(issuedPolicyNumber)}`}
            data-testid="policy-number-link"
            className="inline-flex items-center gap-1.5 rounded-full bg-[var(--secondary)] px-3 py-1 font-mono text-sm font-bold underline-offset-2 hover:underline"
          >
            {issuedPolicyNumber}
            <ExternalLink size={13} aria-hidden="true" />
          </a>
          <p className="text-xs text-[var(--muted-foreground)]">Open the policy register to review the issued contract.</p>
        </div>
      </Modal>
    )
  }

  return (
    <Modal
      open={open}
      title="Convert to Policy"
      description="BR-03: a policy is only issued once the first premium is fully posted."
      onClose={close}
      footer={
        <>
          <button type="button" className="button-secondary" onClick={close}>
            Close
          </button>
          <button type="button" className="button-primary" data-testid="confirm-convert" disabled={br03Blocked || busy || confirmed} onClick={issuePolicy}>
            {busy ? "Checking…" : "Confirm — issue policy"}
          </button>
        </>
      }
    >
      <div className="space-y-4">
        {statusQuery.isError ? (
          <ErrorCoach error={statusQuery.error} title="The first premium status could not be loaded" compact onRetry={() => void statusQuery.refetch()} />
        ) : statusQuery.isLoading ? (
          <div className="h-20 animate-pulse rounded-[10px] bg-[var(--muted)]" aria-busy="true" />
        ) : status ? (
          <Br03Summary status={status} />
        ) : null}

        {statusQuery.isError === false && !statusQuery.isLoading && br03Blocked && (
          <div data-testid="br03-blocked-coach">
            <ErrorCoach
              error={
                new ApiClientError({
                  message: "The first premium has not been posted against this proposal.",
                  status: 422,
                  code: "PROPOSAL_FIRST_PREMIUM_NOT_POSTED",
                  fieldErrors: {},
                  details: {},
                })
              }
              title="Conversion blocked by BR-03"
              compact
            />
            <ul className="mt-2 list-disc pl-5 text-xs leading-5 text-[var(--muted-foreground)]">
              <li>Record the receipt in Front Office against the commitment above.</li>
              <li>Allocate the receipt until the balance reaches zero.</li>
              <li>Return here and issue the policy.</li>
            </ul>
          </div>
        )}

        {!br03Blocked && status?.linked && (
          <p className="text-sm leading-6 text-[var(--muted-foreground)]" data-testid="convert-confirm-copy">
            Issuing creates the policy from this proposal and locks it to{" "}
            <strong className="text-[var(--foreground)]">CONVERTED</strong>. This cannot be undone.
          </p>
        )}
      </div>
    </Modal>
  )
}

export default OLConvertToPolicyModal
