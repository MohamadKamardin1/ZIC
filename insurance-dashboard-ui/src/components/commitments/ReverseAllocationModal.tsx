import { useEffect, useState } from "react"
import { Undo2 } from "lucide-react"
import { Modal } from "../../components/ui/Overlays"
import { ReasonField, reasonError } from "./ReasonField"
import { ErrorCoach } from "./ErrorCoach"
import { useToast } from "../ui/Toast"
import { useCommitmentActionMutation } from "../../lib/commitmentsHooks"
import type { CommitmentAllocation } from "../../lib/commitments"
import { formatMoney, dateLabel } from "../../lib/commitmentsDisplay"

export interface ReverseAllocationModalProps {
  open: boolean
  onClose: () => void
  commitmentId: string
  allocation: CommitmentAllocation
  onSuccess: () => void
}

export function ReverseAllocationModal({ open, onClose, commitmentId, allocation, onSuccess }: ReverseAllocationModalProps) {
  const { toast } = useToast()
  const action = useCommitmentActionMutation()
  const [reason, setReason] = useState("")
  const [showErrors, setShowErrors] = useState(false)
  const [submitError, setSubmitError] = useState<unknown>(null)

  useEffect(() => {
    if (!open) return
    setReason("")
    setShowErrors(false)
    setSubmitError(null)
  }, [open, allocation.id])

  const reasonErrorText = reasonError(reason)

  const submit = () => {
    if (reasonErrorText) {
      setShowErrors(true)
      return
    }
    action.mutate(
      {
        id: commitmentId,
        action: "reverse_allocation",
        payload: { allocation_id: allocation.id, reason: reason.trim() },
      },
      {
        onSuccess: () => {
          toast({ tone: "success", title: "Payment reversed", message: "Payment reversed. Balance restored." })
          onSuccess()
        },
        onError: (reason) => setSubmitError(reason),
      },
    )
  }

  const footer = (
    <>
      <button type="button" className="button-secondary" onClick={onClose}>Cancel</button>
      <button
        type="button"
        className="inline-flex items-center gap-2 rounded-[10px] bg-[var(--destructive)] px-4 py-2 text-sm font-semibold text-[var(--destructive-foreground)] transition hover:opacity-90 disabled:opacity-50"
        disabled={action.isPending}
        onClick={submit}
        data-testid="reverse-allocation-submit"
      >
        <Undo2 size={16} aria-hidden="true" />
        {action.isPending ? "Reversing…" : "Reverse payment"}
      </button>
    </>
  )

  return (
    <Modal open={open} title="Reverse Allocation" description="Reversing restores the balance and records an audit entry. This cannot be undone." onClose={onClose} footer={footer} size="md">
      <div className="space-y-4">
        <section className="rounded-[10px] border border-[var(--border)] bg-[var(--muted)]/25 px-4 py-3" aria-label="Allocation summary">
          <dl className="grid gap-2 text-sm sm:grid-cols-2">
            <div><dt className="text-xs text-[var(--muted-foreground)]">Receipt reference</dt><dd className="font-mono text-xs text-[var(--foreground)]">{allocation.receiptReference || "—"}</dd></div>
            <div><dt className="text-xs text-[var(--muted-foreground)]">Amount</dt><dd className="tabular-nums text-[var(--foreground)]">{formatMoney(allocation.amount, allocation.currency)}</dd></div>
            <div><dt className="text-xs text-[var(--muted-foreground)]">Payment mode</dt><dd className="text-[var(--foreground)]">{allocation.paymentMode || "—"}</dd></div>
            <div><dt className="text-xs text-[var(--muted-foreground)]">Allocated at</dt><dd className="text-[var(--foreground)]">{dateLabel(allocation.allocatedAt)}</dd></div>
          </dl>
        </section>

        <ReasonField value={reason} onChange={setReason} label="Reason" hint="Mandatory — recorded on the reversal and its audit entry." showError={showErrors} />

        {submitError ? <ErrorCoach error={submitError} title="Reversal could not be completed" /> : null}
      </div>
    </Modal>
  )
}

export default ReverseAllocationModal