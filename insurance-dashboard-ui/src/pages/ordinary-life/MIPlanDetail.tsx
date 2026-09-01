import type { ReactNode } from "react"
import { useNavigate, useParams } from "react-router-dom"
import { ArrowLeft, Check, ShieldCheck } from "lucide-react"
import { ErrorCoach } from "../../components/ErrorCoach"
import { ItemStatusBadge, MoneyCell, PlanStatusBadge, ProgressCell } from "../../components/maturityInstallments/MIPrimitives"
import { StatusBadge, type StatusTone } from "../../components/ui/StatusBadge"
import { useMIPlanDetail } from "../../lib/maturityInstallmentsHooks"
import { toStructuredError } from "../../lib/structuredError"

const FREQUENCY_LABELS: Record<string, string> = {
  SINGLE: "Single lump sum",
  MONTHLY: "Monthly",
  QUARTERLY: "Quarterly",
  HALF_YEARLY: "Half-yearly",
  ANNUAL: "Annual",
}

function frequencyLabel(value: string): string {
  return FREQUENCY_LABELS[value.toUpperCase()] ?? value.toLowerCase().replace(/_/g, " ")
}

function dateLabel(value?: string | null): string {
  if (!value) return "—"
  const parsed = new Date(`${value.slice(0, 10)}T00:00:00`)
  return Number.isNaN(parsed.getTime()) ? value : new Intl.DateTimeFormat("en-GB", { dateStyle: "medium" }).format(parsed)
}

function DetailStat({ label, children, helper }: { label: string; children: ReactNode; helper?: string }) {
  return <div className="surface-card min-w-0 p-4"><p className="text-xs font-bold uppercase tracking-[0.1em] text-[var(--muted-foreground)]">{label}</p><p className="mt-2 break-words text-xl font-extrabold tracking-tight">{children}</p>{helper && <p className="mt-1 text-xs text-[var(--muted-foreground)]">{helper}</p>}</div>
}

function reconciliationTone(status: string): StatusTone {
  return status === "PASS" ? "success" : status === "FAIL" ? "danger" : "neutral"
}

export default function MIPlanDetail() {
  const { planId } = useParams<{ planId: string }>()
  const navigate = useNavigate()
  const detailQuery = useMIPlanDetail(planId)
  const plan = detailQuery.data

  if (detailQuery.isLoading) return <div className="space-y-4 p-2" aria-label="Loading plan detail"><div className="h-48 animate-pulse rounded-xl bg-[var(--muted)]" /><div className="grid gap-4 sm:grid-cols-3"><div className="h-28 animate-pulse rounded-xl bg-[var(--muted)]" /><div className="h-28 animate-pulse rounded-xl bg-[var(--muted)]" /><div className="h-28 animate-pulse rounded-xl bg-[var(--muted)]" /></div><div className="h-64 animate-pulse rounded-xl bg-[var(--muted)]" /></div>

  if (detailQuery.error || !plan) {
    const structured = toStructuredError(detailQuery.error, "The requested installment plan could not be loaded.")
    return <div className="p-2"><ErrorCoach title="Plan detail unavailable" message={structured.message} resolutionSteps={["Return to the Maturity Installments register and choose an available record.", "Confirm your `ol_maturity_installments.view` permission and retry."]} onDismiss={() => navigate("/ordinary-life/maturity-installments")} /></div>
  }

  const reconciliation = plan.reconciliation
  return <div className="space-y-5 p-1 md:p-2">
    <section className="section-header p-5">
      <div className="flex flex-col gap-5 xl:flex-row xl:items-start xl:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2 text-xs font-bold uppercase tracking-[0.12em] text-white/70"><button type="button" onClick={() => navigate("/ordinary-life/maturity-installments")} className="inline-flex items-center gap-1 text-white/70 transition hover:text-white" aria-label="Back to maturity installment plans"><ArrowLeft size={14} aria-hidden="true" />Maturity installments</button><span>/</span><span>Plan detail</span></div>
          <div className="mt-3 flex flex-wrap items-center gap-3"><h1 className="break-all text-2xl font-extrabold tracking-tight sm:text-3xl">{plan.planNumber || "Plan detail"}</h1><PlanStatusBadge status={plan.status} statusDisplay={plan.statusDisplay} className="border-white/20 bg-white/15 text-white" /></div>
          <button type="button" onClick={() => navigate(`/ordinary-life/policies/${plan.policyId ?? plan.policyNumber}`)} className="mt-3 inline-flex max-w-full items-center gap-2 truncate text-left text-sm font-bold text-white underline decoration-white/40 underline-offset-4 transition hover:decoration-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white"><span className="truncate">{plan.policyNumber || "Linked policy unavailable"}</span></button>
          <p className="mt-2 text-sm text-white/80">Policyholder: <span className="font-semibold text-white">{plan.policyholderDisplay || plan.policyholderName || "—"}</span></p>
        </div>
        <div className="flex flex-wrap items-center gap-2 xl:max-w-[42%] xl:justify-end"><span className="inline-flex items-center gap-2 rounded-lg border border-white/20 bg-white/10 px-3 py-2 text-xs font-semibold text-white/85"><ShieldCheck size={15} aria-hidden="true" />Financial facts from backend</span></div>
      </div>
    </section>

    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <DetailStat label="Total maturity value"><MoneyCell value={plan.maturityValue} currency={plan.currency} /></DetailStat>
      <DetailStat label="Total paid"><MoneyCell value={plan.paidAmount} currency={plan.currency} variant="paid" /></DetailStat>
      <DetailStat label="Remaining balance" helper={plan.currency}><MoneyCell value={plan.balance} currency={plan.currency} variant="balance" /></DetailStat>
      <DetailStat label="Frequency" helper={`${plan.installmentCount} installments`}>{frequencyLabel(plan.frequency)}</DetailStat>
    </div>

    <section className="surface-card overflow-hidden" aria-label="Installment schedule">
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-[var(--border)] bg-[var(--muted)]/30 px-4 py-4">
        <div><h2 className="text-base font-bold">Installment schedule</h2><p className="mt-1 text-xs text-[var(--muted-foreground)]">Contractual payouts read from the backend schedule and retained for display here.</p></div>
      </div>
      <div className="border-b border-[var(--border)] p-4"><ProgressCell paid={plan.paidAmount} maturityValue={plan.totalPayableAmount} currency={plan.currency} /></div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[820px] text-left text-sm"><caption className="sr-only">Maturity installment schedule</caption>
          <thead className="bg-[var(--muted)]/45 text-xs uppercase tracking-[0.08em] text-[var(--muted-foreground)]"><tr><th scope="col" className="px-4 py-3">Installment #</th><th scope="col" className="px-4 py-3">Due date</th><th scope="col" className="px-4 py-3 text-right">Amount</th><th scope="col" className="px-4 py-3">Status</th><th scope="col" className="px-4 py-3">Requisition</th></tr></thead>
          <tbody className="divide-y divide-[var(--border)]">
            {plan.items.map((item) => <tr key={item.id} className="transition hover:bg-[var(--muted)]/25"><td className="px-4 py-3 font-semibold">{item.installmentNumber}</td><td className="px-4 py-3">{dateLabel(item.dueDate)}</td><td className="px-4 py-3 text-right"><MoneyCell value={item.amount} currency={plan.currency} /></td><td className="px-4 py-3"><ItemStatusBadge status={item.status} statusDisplay={item.statusDisplay} /></td><td className="px-4 py-3">{item.requisitionNumber || "—"}</td></tr>)}
          </tbody>
        </table>
      </div>
    </section>

    <section className="surface-card overflow-hidden" aria-label="Payment history">
      <div className="border-b border-[var(--border)] bg-[var(--muted)]/30 px-4 py-4"><h2 className="text-base font-bold">Payment history</h2><p className="mt-1 text-xs text-[var(--muted-foreground)]">Immutable disbursements recorded against {plan.planNumber || "this plan"}, including the Front Office requisition and payer.</p></div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[760px] text-left text-sm"><caption className="sr-only">Payments made against the plan</caption>
          <thead className="bg-[var(--muted)]/45 text-xs uppercase tracking-[0.08em] text-[var(--muted-foreground)]"><tr><th scope="col" className="px-4 py-3">Installment</th><th scope="col" className="px-4 py-3">Due date</th><th scope="col" className="px-4 py-3">Paid date</th><th scope="col" className="px-4 py-3 text-right">Amount</th><th scope="col" className="px-4 py-3">Requisition</th><th scope="col" className="px-4 py-3">Reference</th></tr></thead>
          <tbody className="divide-y divide-[var(--border)]">
            {plan.paymentHistory.length === 0 && <tr><td colSpan={6} className="px-4 py-10 text-center text-[var(--muted-foreground)]">No payments have been recorded for this plan.</td></tr>}
            {plan.paymentHistory.map((entry, index) => <tr key={`${entry.installmentNumber}-${index}`} className="transition hover:bg-[var(--muted)]/25"><td className="px-4 py-3 font-semibold">{entry.installmentNumber}</td><td className="px-4 py-3">{dateLabel(entry.dueDate)}</td><td className="px-4 py-3">{dateLabel(entry.paidDate)}</td><td className="px-4 py-3 text-right"><MoneyCell value={entry.amount} currency={plan.currency} /></td><td className="px-4 py-3">{entry.requisitionNumber || "—"}</td><td className="px-4 py-3">{entry.paymentReference || "—"}</td></tr>)}
          </tbody>
        </table>
      </div>
    </section>

    {reconciliation && <section className="surface-card p-5" aria-label="Reconciliation report">
      <div className="flex flex-wrap items-start justify-between gap-3"><div><h2 className="text-base font-bold">Reconciliation report</h2><p className="mt-1 text-xs text-[var(--muted-foreground)]">Cross-checks the total payable against recorded payments to keep the plan balanced.</p></div><StatusBadge value={reconciliation.status === "PASS" ? "Pass" : "Fail"} tone={reconciliationTone(reconciliation.status)} /></div>
      <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-lg bg-[var(--muted)]/45 p-3"><p className="text-xs text-[var(--muted-foreground)]">Maturity value</p><p className="mt-1 text-lg font-bold"><MoneyCell value={reconciliation.maturityValue} currency={plan.currency} /></p></div>
        <div className="rounded-lg bg-[var(--muted)]/45 p-3"><p className="text-xs text-[var(--muted-foreground)]">Total payable</p><p className="mt-1 text-lg font-bold"><MoneyCell value={reconciliation.totalPayableAmount} currency={plan.currency} /></p></div>
        <div className="rounded-lg bg-[var(--success)]/8 p-3"><p className="text-xs text-[var(--muted-foreground)]">Paid</p><p className="mt-1 text-lg font-bold text-[var(--success)]"><MoneyCell value={reconciliation.paidAmount} currency={plan.currency} /></p></div>
        <div className="rounded-lg bg-[var(--warning)]/8 p-3"><p className="text-xs text-[var(--muted-foreground)]">Missing amount</p><p className="mt-1 text-lg font-bold"><MoneyCell value={reconciliation.missingAmount} currency={plan.currency} /></p></div>
      </div>
      {reconciliation.discrepancies.length > 0 && <div className="mt-4 space-y-2">{reconciliation.discrepancies.map((discrepancy) => <p key={discrepancy.code} className="rounded-lg border border-[var(--destructive)]/30 bg-[var(--destructive)]/5 px-3 py-2 text-sm text-[var(--destructive)]"><span className="font-bold">{discrepancy.code}:</span> {discrepancy.message}</p>)}</div>}
      {reconciliation.status === "PASS" && <p className="mt-4 flex items-center gap-2 rounded-lg border border-[var(--success)]/30 bg-[var(--success)]/5 px-3 py-2 text-sm text-[var(--success)]"><Check size={15} aria-hidden="true" />All {reconciliation.totalItems} installments reconcile exactly.</p>}
    </section>}
  </div>
}
