import { AlertTriangle, X } from "lucide-react"

interface Props {
  open: boolean
  title: string
  message: string
  confirmLabel?: string
  cancelLabel?: string
  loading?: boolean
  onConfirm: () => void
  onCancel: () => void
}

export default function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = "Delete",
  cancelLabel = "Cancel",
  loading = false,
  onConfirm,
  onCancel,
}: Props) {
  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ backgroundColor: "var(--color-bg-overlay)" }}>
      <div className="mx-4 w-full max-w-sm rounded-xl bg-card shadow-xl">
        <div className="flex items-center justify-between border-b border-border px-5 py-4">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-destructive" />
            <h2 className="text-base font-semibold text-foreground">{title}</h2>
          </div>
          <button onClick={onCancel} className="rounded p-1 text-muted-foreground transition hover:bg-secondary hover:text-foreground">
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="px-5 py-4">
          <p className="text-sm text-muted-foreground">{message}</p>
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
            className="rounded-lg bg-destructive px-4 py-2 text-sm font-semibold text-destructive-foreground transition hover:opacity-90 disabled:opacity-50"
          >
            {loading ? "Deleting..." : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}
