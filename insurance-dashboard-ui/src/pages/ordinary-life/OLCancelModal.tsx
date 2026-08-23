import { useState } from "react"
import { ConfirmModal, Modal } from "../../components/ui/Overlays"
import ReasonField from "../../components/commitments/ReasonField"

/**
 * Cancel-proposal flow: mandatory teachable reason, then a danger confirm.
 * Money-affecting lifecycle actions are always double-confirmed.
 */
export function OLCancelModal({
  open,
  proposalNumber,
  onClose,
  onConfirm,
  pending,
}: {
  open: boolean
  proposalNumber: string
  onClose: () => void
  onConfirm: (reason: string) => void
  pending: boolean
}) {
  const [reason, setReason] = useState("")
  const [confirmStage, setConfirmStage] = useState(false)

  const close = () => {
    setReason("")
    setConfirmStage(false)
    onClose()
  }

  if (confirmStage) {
    return (
      <ConfirmModal
        open={open}
        title="Cancel this proposal?"
        description={`“${reason.trim()}” will be recorded as the cancellation reason for ${proposalNumber}, the proposal becomes read-only, and any linked premium commitment stops accruing.`}
        confirmLabel="Yes — cancel proposal"
        tone="danger"
        onClose={() => setConfirmStage(false)}
        onConfirm={() => {
          onConfirm(reason.trim())
          setReason("")
          setConfirmStage(false)
        }}
      />
    )
  }

  return (
    <Modal
      open={open}
      title="Cancel proposal"
      description="Explain why this proposal is being abandoned. The reason is stored on the audit trail."
      onClose={close}
      footer={
        <>
          <button type="button" className="button-secondary" onClick={close}>
            Keep proposal
          </button>
          <button
            type="button"
            className="inline-flex min-h-10 items-center justify-center rounded-[10px] bg-[var(--destructive)] px-4 text-sm font-bold text-white disabled:cursor-not-allowed disabled:opacity-60"
            data-testid="cancel-continue"
            disabled={!reason.trim() || pending}
            onClick={() => setConfirmStage(true)}
          >
            {pending ? "Cancelling…" : "Continue"}
          </button>
        </>
      }
    >
      <ReasonField value={reason} onChange={setReason} label="Cancellation reason *" testId="cancel-reason-field" minLength={10} />
    </Modal>
  )
}

export default OLCancelModal
