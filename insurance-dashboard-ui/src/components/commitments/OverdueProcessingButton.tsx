import { Zap } from "lucide-react"

export interface OverdueProcessingButtonProps {
  hasPermission: boolean
  onRun: () => void
  disabled?: boolean
}

/** Permission-gated trigger for the overdue processing batch action. */
export function OverdueProcessingButton({ hasPermission, onRun, disabled = false }: OverdueProcessingButtonProps) {
  if (!hasPermission) return null
  return (
    <button type="button" className="button-secondary" disabled={disabled} onClick={onRun} title="Run safe, idempotent overdue batch processing">
      <Zap size={16} aria-hidden="true" />
      Run Overdue Processing
    </button>
  )
}

export default OverdueProcessingButton