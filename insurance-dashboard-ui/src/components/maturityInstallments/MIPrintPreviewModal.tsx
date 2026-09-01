import { LoaderCircle, RotateCcw } from "lucide-react"
import { ErrorCoach } from "../ErrorCoach"
import { ItemStatusBadge, MoneyCell } from "./MIPrimitives"
import { Modal } from "../ui/Overlays"
import type { StructuredError } from "../../lib/structuredError"
import type { MIPlanDetail, MIPlanDocument } from "../../lib/maturityInstallments"

export type MIPrintKind = "schedule" | "statement"

export interface MIPrintPreviewState {
  kind: MIPrintKind
  document?: MIPlanDocument
  url: string | null
  busy: boolean
  error: StructuredError | null
}

function watermarkFor(plan: MIPlanDetail): "TERMINATED" | "MISSED" | null {
  if (plan.status === "TERMINATED") return "TERMINATED"
  if (plan.items.some((item) => item.status === "MISSED")) return "MISSED"
  return null
}

function documentTitle(kind: MIPrintKind): string {
  return kind === "schedule" ? "Maturity Schedule" : "Payment Statement"
}

function dateLabel(value?: string | null): string {
  if (!value) return "—"
  const parsed = new Date(`${value.slice(0, 10)}T00:00:00`)
  return Number.isNaN(parsed.getTime()) ? value : new Intl.DateTimeFormat("en-GB", { dateStyle: "medium" }).format(parsed)
}

export function MIPrintPreviewModal({ state, plan, onClose, onRetry }: { state: MIPrintPreviewState | null; plan: MIPlanDetail; onClose: () => void; onRetry: () => void }) {
  const open = state !== null
  const watermark = watermarkFor(plan)
  const templatePending = state?.error?.code === "TEMPLATE_PENDING"
  const title = state ? `Preview — ${documentTitle(state.kind)}` : "Print preview"

  return <Modal open={open} title={title} size="xl" onClose={onClose} footer={state?.error && !state.document ? <button type="button" className="button-secondary inline-flex items-center gap-2" onClick={onRetry}><RotateCcw size={14} aria-hidden="true" />Retry print</button> : undefined}>
    <div className="space-y-4">
      <div className="rounded-[10px] border border-[var(--border)] bg-[var(--muted)]/35 p-4 text-sm">
        <div className="grid gap-3 sm:grid-cols-2">
          <div><p className="text-xs font-bold uppercase tracking-[0.1em] text-[var(--muted-foreground)]">Plan number</p><p className="mt-1 font-bold">{plan.planNumber || "—"}</p></div>
          <div><p className="text-xs font-bold uppercase tracking-[0.1em] text-[var(--muted-foreground)]">Policyholder</p><p className="mt-1 font-bold">{plan.policyholderDisplay || plan.policyholderName || "—"}</p></div>
        </div>
        <p className="mt-4 text-xs font-bold uppercase tracking-[0.1em] text-[var(--muted-foreground)]">Table of installments</p>
        <div className="mt-2 overflow-x-auto">
          <table className="w-full min-w-[560px] text-left text-xs"><caption className="sr-only">Installment schedule included on the printed document</caption>
            <thead><tr className="border-b text-[var(--muted-foreground)]"><th className="px-2 py-2">#</th><th className="px-2 py-2">Due date</th><th className="px-2 py-2 text-right">Amount</th><th className="px-2 py-2">Status</th></tr></thead>
            <tbody>{plan.items.map((item) => <tr key={item.id} className="border-b last:border-0"><td className="px-2 py-2 tabular-nums">{item.installmentNumber}</td><td className="px-2 py-2">{dateLabel(item.dueDate)}</td><td className="px-2 py-2 text-right"><MoneyCell value={item.amount} currency={plan.currency} /></td><td className="px-2 py-2"><ItemStatusBadge status={item.status} statusDisplay={item.statusDisplay} /></td></tr>)}</tbody>
          </table>
        </div>
        <p className="mt-3 text-xs text-[var(--muted-foreground)]">Signatures: authorised ZIC Life signatories appear on the printed copy.</p>
      </div>

      <div className="relative overflow-hidden rounded-[10px] border border-[var(--border)] bg-[var(--muted)]/20">
        {state?.busy ? <div className="flex min-h-[420px] flex-col items-center justify-center gap-3 text-sm text-[var(--muted-foreground)]" role="status"><LoaderCircle size={22} className="animate-spin" aria-hidden="true" />Rendering {documentTitle(state.kind).toLowerCase()}…</div>
          : state?.url ? <div className="relative" data-testid="mi-print-pdf-frame"><iframe title={`${documentTitle(state.kind)} PDF preview`} src={state.url} className="h-[420px] w-full" />
            {watermark && <div className="pointer-events-none absolute inset-0 flex items-center justify-center"><span className={`-rotate-12 rounded border-4 px-6 py-2 text-2xl font-black uppercase tracking-[0.2em] opacity-30 ${watermark === "TERMINATED" ? "border-[var(--destructive)] text-[var(--destructive)]" : "border-[var(--warning)] text-[var(--warning)]"}`}>{watermark}</span></div>}
          </div>
          : <div className="flex min-h-[420px] items-center justify-center text-sm text-[var(--muted-foreground)]">No PDF preview is available for this document.</div>}
      </div>

      {state?.error && <ErrorCoach title={templatePending ? "Print template is still rendering" : "Print preview unavailable"} message={state.error.message} resolutionSteps={state.error.resolutionSteps} />}
    </div>
  </Modal>
}
