import { useEffect, useState } from "react"
import { CalendarClock, ShieldCheck } from "lucide-react"
import { Modal, InfoBanner } from "../../components/ui/Overlays"
import { DateInput } from "../../components/ui/FormControls"
import { ReasonField, reasonError } from "./ReasonField"
import { ErrorCoach } from "./ErrorCoach"
import { useToast } from "../ui/Toast"
import { useCommitmentActionMutation } from "../../lib/commitmentsHooks"
import type { CommitmentDetail } from "../../lib/commitments"
import { notifyCommitmentSuccess } from "../../lib/commitmentsNotify"

export type LifecycleAction = "suspend" | "reactivate" | "waive" | "cancel" | "reschedule"

export const LIFECYCLE_ACTIONS: LifecycleAction[] = ["suspend", "reactivate", "waive", "cancel", "reschedule"]

interface ActionConfig {
  title: string
  description: string
  confirmLabel: string
  danger: boolean
  approval?: boolean
  reschedule?: boolean
}

const CONFIG: Record<LifecycleAction, ActionConfig> = {
  suspend: {
    title: "Suspend Commitment",
    description: "Freeze collection on this commitment. The reason is recorded with the status change.",
    confirmLabel: "Suspend",
    danger: true,
  },
  reactivate: {
    title: "Reactivate Commitment",
    description: "Resume collection on this suspended commitment.",
    confirmLabel: "Reactivate",
    danger: false,
  },
  waive: {
    title: "Waive Commitment",
    description: "Waive the remaining balance of this commitment.",
    confirmLabel: "Waive",
    danger: true,
    approval: true,
  },
  cancel: {
    title: "Cancel Commitment",
    description: "Close this commitment. The balance will no longer be collected.",
    confirmLabel: "Cancel",
    danger: true,
  },
  reschedule: {
    title: "Reschedule Commitment",
    description: "Move the due date. Grace and lapse dates are recomputed from the OL Grace Period parameters.",
    confirmLabel: "Reschedule",
    danger: false,
    reschedule: true,
  },
}

export interface LifecycleActionModalProps {
  open: boolean
  onClose: () => void
  commitmentId: string
  action: LifecycleAction | null
  commitment?: CommitmentDetail | null
  onSuccess: () => void
}

function rescheduleHint(commitment?: CommitmentDetail | null): string {
  const graceDays = commitment?.graceDays
  const base = "Grace and lapse windows follow the OL Grace Period parameters and are recomputed from the new due date."
  return graceDays ? `The configured grace window is ${graceDays} day(s). ${base}` : base
}

export function LifecycleActionModal({ open, onClose, commitmentId, action, commitment, onSuccess }: LifecycleActionModalProps) {
  const { toast } = useToast()
  const mutation = useCommitmentActionMutation()
  const [reason, setReason] = useState("")
  const [dueDate, setDueDate] = useState("")
  const [showErrors, setShowErrors] = useState(false)
  const [submitError, setSubmitError] = useState<unknown>(null)

  const config = action ? CONFIG[action] : null

  useEffect(() => {
    if (!open || !action) return
    setReason("")
    setDueDate("")
    setShowErrors(false)
    setSubmitError(null)
  }, [open, action])

  if (!config) return null

  const reasonErrorText = reasonError(reason)
  const dueDateError = config.reschedule && !dueDate ? "Choose a new due date on or after today." : undefined

  const submit = () => {
    if (reasonErrorText || dueDateError) {
      setShowErrors(true)
      return
    }
    mutation.mutate(
      {
        id: commitmentId,
        action: action as LifecycleAction,
        payload: {
          reason: reason.trim(),
          ...(config.reschedule ? { due_date: dueDate } : {}),
        },
      },
      {
        onSuccess: (result) => {
          const numberLabel = result?.commitmentNumber ?? commitmentId
          notifyCommitmentSuccess(
            toast,
            `${config.confirmLabel} completed`,
            `${numberLabel} updated. Open History to review the status change.`,
          )
          onSuccess()
        },
        onError: (reasonValue) => setSubmitError(reasonValue),
      },
    )
  }

  const footer = (
    <>
      <button type="button" className="button-secondary" onClick={onClose}>Cancel</button>
      <button
        type="button"
        className={config.danger
          ? "inline-flex items-center gap-2 rounded-[10px] bg-[var(--destructive)] px-4 py-2 text-sm font-semibold text-[var(--destructive-foreground)] transition hover:opacity-90 disabled:opacity-50"
          : "button-primary"}
        disabled={mutation.isPending}
        onClick={submit}
        data-testid={`lifecycle-submit-${action ?? "action"}`}
      >
        {mutation.isPending ? "Working…" : config.confirmLabel}
      </button>
    </>
  )

  return (
    <Modal open={open} title={config.title} description={config.description} onClose={onClose} footer={footer} size="md">
      <div className="space-y-4">
        {config.approval && (
          <InfoBanner title="Approval required">
            <p className="flex items-start gap-2 text-sm">
              <ShieldCheck size={16} className="mt-0.5 shrink-0" aria-hidden="true" />
              This waiver will route through the approval workflow before it takes effect. The commitment stays on its current status until an approver decides.
            </p>
          </InfoBanner>
        )}

        {config.reschedule && (
          <div className="space-y-3">
            <div className="flex items-start gap-2 rounded-[10px] border border-[var(--border)] bg-[var(--muted)]/25 px-3 py-2 text-xs text-[var(--muted-foreground)]">
              <CalendarClock size={14} className="mt-0.5 shrink-0" aria-hidden="true" />
              <span data-testid="reschedule-hint">{rescheduleHint(commitment)}</span>
            </div>
            <DateInput
              label="New due date"
              name="newDueDate"
              required
              value={dueDate}
              onChange={(event) => { setDueDate(event.target.value); setShowErrors(false) }}
              error={showErrors ? dueDateError : undefined}
              data-testid="reschedule-due-date"
            />
          </div>
        )}

        <ReasonField value={reason} onChange={setReason} label="Reason" hint="Mandatory — recorded with the status change." showError={showErrors} />

        {submitError ? <ErrorCoach error={submitError} title={`${config.confirmLabel} could not be completed`} /> : null}
      </div>
    </Modal>
  )
}

export default LifecycleActionModal