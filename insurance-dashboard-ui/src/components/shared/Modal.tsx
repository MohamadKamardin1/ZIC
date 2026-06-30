import { X } from "lucide-react"

interface ModalProps {
  open: boolean
  title: string
  onClose: () => void
  children: React.ReactNode
}

export default function Modal({ open, title, onClose, children }: ModalProps) {
  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-0" style={{ backgroundColor: "var(--color-bg-overlay, rgba(0,0,0,0.4))" }}>
      <div className="mx-auto w-full max-w-md overflow-hidden rounded-xl bg-card shadow-2xl sm:mx-4 animate-in fade-in zoom-in-95 duration-200">
        <div className="flex items-center justify-between border-b border-border px-5 py-4">
          <h2 className="text-base font-semibold text-foreground">{title}</h2>
          <button onClick={onClose} className="rounded p-1.5 text-muted-foreground transition hover:bg-secondary hover:text-foreground">
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="p-5">
          {children}
        </div>
      </div>
    </div>
  )
}
