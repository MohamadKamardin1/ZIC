import ConfirmDialog, { type ConfirmDialogVariant } from "../shared/ConfirmDialog"

export interface CommitmentConfirmDialogProps {
  open: boolean
  title: string
  message: string
  confirmLabel?: string
  cancelLabel?: string
  loading?: boolean
  variant?: ConfirmDialogVariant
  hint?: string
  onConfirm: () => void
  onCancel: () => void
}

/** Commitment confirm dialog: danger/warning/info variants + next-step hint. */
export function CommitmentConfirmDialog({ confirmLabel = "Confirm", ...props }: CommitmentConfirmDialogProps) {
  return <ConfirmDialog confirmLabel={confirmLabel} {...props} />
}

export default CommitmentConfirmDialog