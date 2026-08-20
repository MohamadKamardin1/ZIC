import { CheckCircle2, CircleAlert, Info, X, XCircle } from "lucide-react"
import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react"
import type { StatusTone } from "./StatusBadge"

type Toast = { id: string; title: string; message?: string; tone: StatusTone }
type ToastContextValue = { toast: (input: Omit<Toast, "id">) => void; dismiss: (id: string) => void }
const ToastContext = createContext<ToastContextValue | null>(null)
const icons = { success: CheckCircle2, info: Info, warning: CircleAlert, danger: XCircle, neutral: Info }

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])
  const dismiss = useCallback((id: string) => setToasts((current) => current.filter((toast) => toast.id !== id)), [])
  const toast = useCallback((input: Omit<Toast, "id">) => { const id = `toast-${Date.now()}-${Math.random().toString(16).slice(2)}`; setToasts((current) => [...current, { ...input, id }]); window.setTimeout(() => dismiss(id), 5000) }, [dismiss])
  const value = useMemo(() => ({ toast, dismiss }), [dismiss, toast])
  return <ToastContext.Provider value={value}>{children}<div className="pointer-events-none fixed bottom-6 right-6 z-[70] flex w-[min(380px,calc(100vw-2rem))] flex-col gap-3" aria-live="polite" aria-atomic="false">{toasts.map((item) => { const Icon = icons[item.tone]; return <div key={item.id} className={`pointer-events-none surface-card flex items-start gap-3 border-l-4 p-4 ${item.tone === "success" ? "border-l-[var(--success)]" : item.tone === "danger" ? "border-l-[var(--destructive)]" : item.tone === "warning" ? "border-l-[var(--warning)]" : "border-l-[var(--primary)]"}`} role="status"><Icon size={18} className="mt-0.5 shrink-0" aria-hidden="true" /><div className="min-w-0 flex-1"><p className="text-sm font-bold">{item.title}</p>{item.message && <p className="mt-1 text-xs leading-5 text-[var(--muted-foreground)]">{item.message}</p>}</div><button type="button" onClick={() => dismiss(item.id)} aria-label={`Dismiss ${item.title}`} className="pointer-events-auto rounded-md p-1 hover:bg-[var(--secondary)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]"><X size={15} aria-hidden="true" /></button></div>})}</div></ToastContext.Provider>
}

export function useToast() {
  const value = useContext(ToastContext)
  if (!value) throw new Error("useToast must be used inside ToastProvider")
  return value
}
