import { AlertTriangle, CircleAlert, Info, X } from "lucide-react"

export type ConfirmDialogVariant = "danger" | "warning" | "info"

interface Props {
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

const variantMeta: Record<ConfirmDialogVariant, { icon: typeof AlertTriangle; buttonClass: string; iconClass: string }> = {
  danger: { icon: AlertTriangle, buttonClass: "bg-destructive hover:opacity-90 text-destructive-foreground", iconClass: "text-destructive" },
  warning: { icon: CircleAlert, buttonClass: "bg-warning hover:opacity-90 text-warning-foreground", iconClass: "text-warning" },
  info: { icon: Info, buttonClass: "bg-primary hover:opacity-90 text-primary-foreground", iconClass: "text-primary" },
}

export default function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = "Delete",
  cancelLabel = "Cancel",
  loading = false,
  variant = "danger",
  hint,
  onConfirm,
  onCancel,
}: Props) {
  if (!open) return null
  const { icon: DialogIcon, buttonClass, iconClass } = variantMeta[variant]

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ backgroundColor: "var(--color-bg-overlay)" }}>
      <div className="mx-4 w-full max-w-sm rounded-xl bg-card shadow-xl">
        <div className="flex items-center justify-between border-b border-border px-5 py-4">
          <div className="flex items-center gap-2">
            <DialogIcon className={`h-5 w-5 ${iconClass}`} />
            <h2 className="text-base font-semibold text-foreground">{title}</h2>
          </div>
          <button onClick={onCancel} className="rounded p-1 text-muted-foreground transition hover:bg-secondary hover:text-foreground">
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="px-5 py-4">
          <p className="text-sm text-muted-foreground">{message}</p>
          {hint && <p className="mt-2 text-xs text-muted-foreground">{hint}</p>}
        </div>
        <div className="flex justify-end gap-2 border-t border-border px-5 py-3">
          <button
            onClick={onCancel}
            disabled={loading}
            className="rounded-lg border border-border px-4 py-2 text-sm font-medium text-foreground transition hover:bg-secondary disabled:opacity-50"
          >
            {cancelLabel}
          </button>
          <button
            onClick={onConfirm}
            disabled={loading}
            className={`rounded-lg px-4 py-2 text-sm font-semibold transition disabled:opacity-50 ${buttonClass}`}
          >
            {loading ? "Working..." : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}
