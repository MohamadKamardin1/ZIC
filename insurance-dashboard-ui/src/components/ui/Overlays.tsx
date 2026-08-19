import { X } from "lucide-react"
import { useEffect, type ReactNode } from "react"
import type { ReactElement } from "react"

export function InfoBanner({ title, children, className = "" }: { title?: string; children: ReactNode; className?: string }) {
  return <div className={`flex gap-3 rounded-[10px] border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-900 dark:border-blue-900/60 dark:bg-blue-950/35 dark:text-blue-100 ${className}`} role="status"><span className="mt-0.5 h-2 w-2 shrink-0 rounded-full bg-blue-500" aria-hidden="true" /><div>{title && <p className="font-bold">{title}</p>}<div className="leading-6">{children}</div></div></div>
}

type ModalProps = { open: boolean; title: string; description?: string; onClose: () => void; children: ReactNode; footer?: ReactNode; size?: "sm" | "md" | "lg" | "xl" }

const sizeClasses = { sm: "max-w-md", md: "max-w-xl", lg: "max-w-3xl", xl: "max-w-5xl" }

export function Modal({ open, title, description, onClose, children, footer, size = "md" }: ModalProps): ReactElement | null {
  useEffect(() => {
    if (!open) return undefined
    const listener = (event: KeyboardEvent) => { if (event.key === "Escape") onClose() }
    document.addEventListener("keydown", listener)
    const previous = document.body.style.overflow
    document.body.style.overflow = "hidden"
    return () => { document.removeEventListener("keydown", listener); document.body.style.overflow = previous }
  }, [open, onClose])
  if (!open) return null
  return <div className="fixed inset-0 z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true" aria-labelledby="modal-title"><button type="button" aria-label="Close dialog" className="absolute inset-0 cursor-default bg-slate-950/45 backdrop-blur-[2px]" onClick={onClose} /><div className={`relative flex max-h-[90vh] w-full flex-col overflow-hidden rounded-[12px] border bg-[var(--card)] shadow-2xl ${sizeClasses[size]}`}><header className="flex items-start justify-between border-b px-5 py-4"><div><h2 id="modal-title" className="text-lg font-bold">{title}</h2>{description && <p className="mt-1 text-sm text-[var(--muted-foreground)]">{description}</p>}</div><button type="button" onClick={onClose} aria-label="Close dialog" className="rounded-md p-1.5 text-[var(--muted-foreground)] hover:bg-[var(--secondary)] hover:text-[var(--foreground)]"><X size={18} aria-hidden="true" /></button></header><div className="min-h-0 flex-1 overflow-auto p-5">{children}</div>{footer && <footer className="flex items-center justify-end gap-3 border-t bg-[var(--muted)]/45 px-5 py-4">{footer}</footer>}</div></div>
}

export function FormModal({ open, title, description, onClose, onSave, saving = false, saveLabel = "Save changes", children }: Omit<ModalProps, "footer"> & { onSave: () => void; saving?: boolean; saveLabel?: string }) {
  return <Modal open={open} title={title} description={description} onClose={onClose} footer={<><button type="button" className="button-secondary" onClick={onClose} disabled={saving}>Cancel</button><button type="button" className="button-primary" onClick={onSave} disabled={saving}>{saving ? "Saving…" : saveLabel}</button></>}>{children}</Modal>
}

export function ConfirmModal({ open, title = "Confirm action", description, confirmLabel = "Confirm", onClose, onConfirm, tone = "danger" }: { open: boolean; title?: string; description: string; confirmLabel?: string; onClose: () => void; onConfirm: () => void; tone?: "danger" | "primary" }) {
  return <Modal open={open} title={title} onClose={onClose} size="sm" footer={<><button type="button" className="button-secondary" onClick={onClose}>Cancel</button><button type="button" className={tone === "danger" ? "inline-flex min-h-10 items-center justify-center rounded-[10px] bg-[var(--destructive)] px-4 text-sm font-bold text-white" : "button-primary"} onClick={onConfirm}>{confirmLabel}</button></>}><p className="text-sm leading-6 text-[var(--muted-foreground)]">{description}</p></Modal>
}

export function Drawer({ open, title, description, onClose, children, width = "max-w-xl" }: Omit<ModalProps, "footer" | "size"> & { width?: string }) {
  useEffect(() => {
    if (!open) return undefined
    const listener = (event: KeyboardEvent) => { if (event.key === "Escape") onClose() }
    document.addEventListener("keydown", listener)
    return () => document.removeEventListener("keydown", listener)
  }, [open, onClose])
  if (!open) return null
  return <div className="fixed inset-0 z-50" role="dialog" aria-modal="true" aria-labelledby="drawer-title"><button type="button" aria-label="Close drawer" className="absolute inset-0 bg-slate-950/40" onClick={onClose} /><aside className={`absolute right-0 top-0 flex h-full w-full flex-col border-l bg-[var(--card)] shadow-2xl ${width}`}><header className="flex items-start justify-between border-b px-5 py-4"><div><h2 id="drawer-title" className="text-lg font-bold">{title}</h2>{description && <p className="mt-1 text-sm text-[var(--muted-foreground)]">{description}</p>}</div><button type="button" onClick={onClose} aria-label="Close drawer" className="rounded-md p-1.5 text-[var(--muted-foreground)] hover:bg-[var(--secondary)]"><X size={18} aria-hidden="true" /></button></header><div className="min-h-0 flex-1 overflow-auto p-5">{children}</div></aside></div>
}
