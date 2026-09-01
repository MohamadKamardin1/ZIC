import { useCallback, useMemo, useState, type ReactNode } from "react"
import { useQueryClient } from "@tanstack/react-query"
import { useNavigate, useParams, useSearchParams } from "react-router-dom"
import { ArrowLeft, Check, CheckCircle2, Clipboard, ExternalLink, FileText, ShieldCheck, TriangleAlert } from "lucide-react"
import { ErrorCoach } from "../../components/ErrorCoach"
import { ItemStatusBadge, MoneyCell, PlanStatusBadge, planStatusLabel, ProgressCell } from "../../components/maturityInstallments/MIPrimitives"
import { MIPlanDocumentsPanel } from "../../components/maturityInstallments/MIPlanDocumentsPanel"
import { StatusBadge, type StatusTone } from "../../components/ui/StatusBadge"
import { ConfirmModal, Modal } from "../../components/ui/Overlays"
import { useToast } from "../../components/ui/Toast"
import { useAccess } from "../../lib/access"
import { cancelMIPlan, printMISchedule, processMIPayment, type MIPlanDetail, type MIPlanItem } from "../../lib/maturityInstallments"
import { invalidateMaturityInstallmentQueries, useMIPlanDetail } from "../../lib/maturityInstallmentsHooks"
import { toStructuredError, type StructuredError } from "../../lib/structuredError"

const TABS = [
  { id: "overview", label: "Overview" },
  { id: "schedule", label: "Schedule" },
  { id: "payments", label: "Payments" },
  { id: "audit", label: "Audit" },
  { id: "documents", label: "Documents" },
]

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

function dateTimeLabel(value?: string | null): string {
  if (!value) return "—"
  const parsed = new Date(value)
  return Number.isNaN(parsed.getTime()) ? value : new Intl.DateTimeFormat("en-GB", { dateStyle: "medium", timeStyle: "short" }).format(parsed)
}

function todayLocal(): string {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`
}

function copyText(value: string): Promise<void> {
  if (navigator.clipboard?.writeText) return navigator.clipboard.writeText(value)
  return Promise.resolve()
}

function DetailStat({ label, children, helper }: { label: string; children: ReactNode; helper?: string }) {
  return <div className="surface-card min-w-0 p-4"><p className="text-xs font-bold uppercase tracking-[0.1em] text-[var(--muted-foreground)]">{label}</p><p className="mt-2 break-words text-xl font-extrabold tracking-tight">{children}</p>{helper && <p className="mt-1 text-xs text-[var(--muted-foreground)]">{helper}</p>}</div>
}

function reconciliationTone(status: string): StatusTone {
  return status === "PASS" ? "success" : status === "FAIL" ? "danger" : "neutral"
}

function nextDueItem(plan: MIPlanDetail): MIPlanItem | null {
  const today = todayLocal()
  return plan.items
    .filter((item) => (item.status === "SCHEDULED" || item.status === "MISSED") && (!item.dueDate || item.dueDate <= today))
    .sort((a, b) => (a.dueDate ?? "").localeCompare(b.dueDate ?? ""))[0] ?? null
}

function StatusTimeline({ plan }: { plan: MIPlanDetail }) {
  const history = plan.statusHistory ?? []
  return <section className="surface-card p-5" aria-label="Status timeline">
    <div className="flex flex-wrap items-start justify-between gap-3"><div><h2 className="text-base font-bold">Status timeline</h2><p className="mt-1 text-xs text-[var(--muted-foreground)]">Lifecycle checkpoints recorded for this plan</p></div><PlanStatusBadge status={plan.status} statusDisplay={plan.statusDisplay} /></div>
    {history.length === 0 ? <p className="mt-5 rounded-lg border border-dashed border-[var(--border)] px-3 py-5 text-sm text-[var(--muted-foreground)]">No lifecycle checkpoints have been recorded for this plan.</p> : <ol className="mt-5">{history.map((entry, index) => { const isCurrent = index === history.length - 1; return <li key={`${entry.status}-${entry.timestamp}`} className="relative flex gap-4 pb-5 last:pb-0"><div className="flex flex-col items-center"><span className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-bold ${isCurrent ? "bg-[var(--primary)] text-white" : "bg-[var(--success)] text-white"}`}>{isCurrent ? <Check size={14} aria-hidden="true" /> : index + 1}</span>{index < history.length - 1 && <span className="mt-1 w-px flex-1 bg-[var(--border)]" aria-hidden="true" />}</div><div className="min-w-0"><p className="text-sm font-bold">{planStatusLabel(entry.status, entry.statusDisplay)}</p><p className="mt-0.5 text-xs text-[var(--muted-foreground)]">{dateLabel(entry.timestamp)}</p>{entry.note && <p className="mt-1 text-sm leading-5 text-[var(--muted-foreground)]">{entry.note}</p>}</div></li> }) }</ol>}
  </section>
}

function OverviewTab({ plan }: { plan: MIPlanDetail }) {
  const navigate = useNavigate()
  const calculationSource = plan.calculationSourceDisplay ?? (plan.maturityClaimId ? "Maturity Claim" : "Rate Table")
  return <div className="space-y-5">
    <div className="grid gap-4 lg:grid-cols-2">
      <section className="surface-card p-5" aria-label="Plan context">
        <div className="flex items-center gap-2"><FileText size={17} className="text-[var(--primary)]" aria-hidden="true" /><h2 className="text-base font-bold">Plan context</h2></div>
        <dl className="mt-4 grid gap-3 sm:grid-cols-2">
          <div><dt className="text-xs text-[var(--muted-foreground)]">Frequency</dt><dd className="mt-1 text-sm font-semibold">{frequencyLabel(plan.frequency)}</dd></div>
          <div><dt className="text-xs text-[var(--muted-foreground)]">Number of installments</dt><dd className="mt-1 text-sm font-semibold">{plan.installmentCount}</dd></div>
          <div><dt className="text-xs text-[var(--muted-foreground)]">Calculation source</dt><dd className="mt-1 text-sm font-semibold">{calculationSource}</dd></div>
          <div><dt className="text-xs text-[var(--muted-foreground)]">Start date</dt><dd className="mt-1 text-sm font-semibold">{dateLabel(plan.startDate)}</dd></div>
          <div><dt className="text-xs text-[var(--muted-foreground)]">End date</dt><dd className="mt-1 text-sm font-semibold">{dateLabel(plan.endDate)}</dd></div>
          <div><dt className="text-xs text-[var(--muted-foreground)]">Source channel</dt><dd className="mt-1 text-sm font-semibold">{plan.sourceChannelDisplay || "—"}</dd></div>
        </dl>
      </section>
      <section className="surface-card p-5" aria-label="Policy details">
        <h2 className="text-base font-bold">Policy details</h2>
        <p className="mt-1 text-xs text-[var(--muted-foreground)]">The policy remains the source transaction for this maturity schedule.</p>
        <dl className="mt-4 space-y-3">
          <div className="flex flex-wrap items-start justify-between gap-3 border-b border-[var(--border)] pb-3"><dt className="text-xs text-[var(--muted-foreground)]">Policy</dt><dd className="max-w-[70%] text-right text-sm font-semibold"><button type="button" onClick={() => navigate(`/ordinary-life/policies/${plan.policyId ?? plan.policyNumber}`)} className="text-[var(--primary)] underline-offset-2 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]">{plan.policyNumber || "—"}</button></dd></div>
          <div className="flex flex-wrap items-start justify-between gap-3 border-b border-[var(--border)] pb-3"><dt className="text-xs text-[var(--muted-foreground)]">Product</dt><dd className="max-w-[70%] text-right text-sm font-semibold">{plan.productDisplay || plan.productCode || "—"}</dd></div>
          <div className="flex flex-wrap items-start justify-between gap-3 border-b border-[var(--border)] pb-3"><dt className="text-xs text-[var(--muted-foreground)]">Policyholder</dt><dd className="max-w-[70%] text-right text-sm font-semibold">{plan.policyholderDisplay || plan.policyholderName || "—"}</dd></div>
          <div className="flex flex-wrap items-start justify-between gap-3"><dt className="text-xs text-[var(--muted-foreground)]">Source channel</dt><dd className="max-w-[70%] text-right text-sm font-semibold">{plan.sourceChannelDisplay || plan.sourceChannel || "—"}</dd></div>
          {plan.claimNumber && <div className="flex flex-wrap items-start justify-between gap-3"><dt className="text-xs text-[var(--muted-foreground)]">Linked maturity claim</dt><dd className="max-w-[70%] text-right text-sm font-semibold">{plan.claimNumber}</dd></div>}
        </dl>
      </section>
    </div>
    <StatusTimeline plan={plan} />
  </div>
}

function ScheduleTab({ plan }: { plan: MIPlanDetail }) {
  return <section className="surface-card overflow-hidden" aria-label="Installment schedule">
    <div className="flex flex-wrap items-start justify-between gap-3 border-b border-[var(--border)] bg-[var(--muted)]/30 px-4 py-4">
      <div><h2 className="text-base font-bold">Installment schedule</h2><p className="mt-1 text-xs text-[var(--muted-foreground)]">Contractual payouts read from the backend schedule and retained for display here.</p></div>
      <PlanStatusBadge status={plan.status} statusDisplay={plan.statusDisplay} />
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
}

function ReconciliationReport({ plan }: { plan: MIPlanDetail }) {
  const reconciliation = plan.reconciliation
  if (!reconciliation) return null
  return <section className="surface-card p-5" aria-label="Reconciliation report">
    <div className="flex flex-wrap items-start justify-between gap-3"><div><h2 className="text-base font-bold">Reconciliation report</h2><p className="mt-1 text-xs text-[var(--muted-foreground)]">Cross-checks the total payable against recorded payments to keep the plan balanced.</p></div><StatusBadge value={reconciliation.status === "PASS" ? "Pass" : "Fail"} tone={reconciliationTone(reconciliation.status)} /></div>
    <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      <div className="rounded-lg bg-[var(--muted)]/45 p-3"><p className="text-xs text-[var(--muted-foreground)]">Maturity value</p><p className="mt-1 text-lg font-bold"><MoneyCell value={reconciliation.maturityValue} currency={plan.currency} /></p></div>
      <div className="rounded-lg bg-[var(--muted)]/45 p-3"><p className="text-xs text-[var(--muted-foreground)]">Total payable</p><p className="mt-1 text-lg font-bold"><MoneyCell value={reconciliation.totalPayableAmount} currency={plan.currency} /></p></div>
      <div className="rounded-lg bg-[var(--success)]/8 p-3"><p className="text-xs text-[var(--muted-foreground)]">Paid</p><p className="mt-1 text-lg font-bold text-[var(--success)]"><MoneyCell value={reconciliation.paidAmount} currency={plan.currency} /></p></div>
      <div className="rounded-lg bg-[var(--warning)]/8 p-3"><p className="text-xs text-[var(--muted-foreground)]">Missing amount</p><p className="mt-1 text-lg font-bold"><MoneyCell value={reconciliation.missingAmount} currency={plan.currency} /></p></div>
    </div>
    {reconciliation.discrepancies.length > 0 && <div className="mt-4 space-y-2">{reconciliation.discrepancies.map((discrepancy) => <p key={discrepancy.code} className="rounded-lg border border-[var(--destructive)]/30 bg-[var(--destructive)]/5 px-3 py-2 text-sm text-[var(--destructive)]"><span className="font-bold">{discrepancy.code}:</span> {discrepancy.message}</p>)}</div>}
    {reconciliation.status === "PASS" && <p className="mt-4 flex items-center gap-2 rounded-lg border border-[var(--success)]/30 bg-[var(--success)]/5 px-3 py-2 text-sm text-[var(--success)]"><Check size={15} aria-hidden="true" />All {reconciliation.totalItems} installments reconcile exactly.</p>}
  </section>
}

function PaymentsTab({ plan }: { plan: MIPlanDetail }) {
  return <div className="space-y-5">
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
    <ReconciliationReport plan={plan} />
  </div>
}

function AuditTab({ plan }: { plan: MIPlanDetail }) {
  const auditHistory = plan.auditHistory ?? []
  return <section className="surface-card overflow-hidden" aria-label="Audit trail">
    <div className="border-b border-[var(--border)] bg-[var(--muted)]/30 px-4 py-4"><h2 className="text-base font-bold">Audit trail</h2><p className="mt-1 text-xs text-[var(--muted-foreground)]">Actor, channel, and timestamp for every financial change recorded against {plan.planNumber || "this plan"}.</p></div>
    {auditHistory.length === 0 ? <p className="px-4 py-10 text-center text-sm text-[var(--muted-foreground)]">No audit events have been recorded for this plan.</p> : <div className="overflow-x-auto">
      <table className="w-full min-w-[820px] text-left text-sm"><caption className="sr-only">Maturity installment plan audit events</caption>
        <thead className="bg-[var(--muted)]/45 text-xs uppercase tracking-[0.08em] text-[var(--muted-foreground)]"><tr><th scope="col" className="px-4 py-3">Timestamp</th><th scope="col" className="px-4 py-3">Action</th><th scope="col" className="px-4 py-3">Actor</th><th scope="col" className="px-4 py-3">Channel</th><th scope="col" className="px-4 py-3">Details</th></tr></thead>
        <tbody className="divide-y divide-[var(--border)]">{auditHistory.map((entry) => <tr key={entry.id} className="transition hover:bg-[var(--muted)]/25"><td className="px-4 py-3">{dateTimeLabel(entry.timestamp)}</td><td className="px-4 py-3"><span className="font-semibold">{entry.actionDisplay || entry.action}</span></td><td className="px-4 py-3">{entry.actorDisplay}</td><td className="px-4 py-3"><span className="rounded-full bg-[var(--secondary)] px-2 py-0.5 text-xs font-bold">{entry.channel || "—"}</span></td><td className="px-4 py-3 text-[var(--muted-foreground)]">{entry.details || "—"}</td></tr>)}</tbody>
      </table>
    </div>}
  </section>
}

export default function MIPlanDetail() {
  const { planId } = useParams<{ planId: string }>()
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const { access, hasPermission, isSuperAdmin } = useAccess()
  const [copied, setCopied] = useState(false)
  const [processItem, setProcessItem] = useState<MIPlanItem | null>(null)
  const [processBusy, setProcessBusy] = useState(false)
  const [processError, setProcessError] = useState<StructuredError | null>(null)
  const [cancelOpen, setCancelOpen] = useState(false)
  const [cancelBusy, setCancelBusy] = useState(false)
  const [cancelError, setCancelError] = useState<StructuredError | null>(null)
  const [cancelReason, setCancelReason] = useState("")

  const detailQuery = useMIPlanDetail(planId)
  const plan = detailQuery.data
  const activeTab = TABS.some((tab) => tab.id === searchParams.get("tab")) ? searchParams.get("tab") || "overview" : "overview"

  const permissionCodes = useMemo(() => access.permissions.map((permission) => `${permission.module}.${permission.action}`.toLowerCase()), [access.permissions])
  const can = useCallback((permission: string) => isSuperAdmin || Boolean(hasPermission?.(permission) || permissionCodes.includes(permission.toLowerCase())), [hasPermission, isSuperAdmin, permissionCodes])

  if (detailQuery.isLoading) return <div className="space-y-4 p-2" aria-label="Loading plan detail"><div className="h-48 animate-pulse rounded-xl bg-[var(--muted)]" /><div className="grid gap-4 sm:grid-cols-3"><div className="h-28 animate-pulse rounded-xl bg-[var(--muted)]" /><div className="h-28 animate-pulse rounded-xl bg-[var(--muted)]" /><div className="h-28 animate-pulse rounded-xl bg-[var(--muted)]" /></div><div className="h-64 animate-pulse rounded-xl bg-[var(--muted)]" /></div>

  if (detailQuery.error || !plan) {
    const structured = toStructuredError(detailQuery.error, "The requested installment plan could not be loaded.")
    return <div className="p-2"><ErrorCoach title="Plan detail unavailable" message={structured.message} resolutionSteps={["Return to the Maturity Installments register and choose an available record.", "Confirm your `ol_maturity_installments.view` permission and retry."]} onDismiss={() => navigate("/ordinary-life/maturity-installments")} /></div>
  }

  const canAction = (key: "process_payment" | "print" | "cancel") => {
    const allowed = new Set((plan.allowedActions ?? []).map((item) => String(item).toLowerCase()))
    const permissions: Record<string, string> = { process_payment: "ol_maturity_installments.process_payment", print: "ol_maturity_installments.print", cancel: "ol_maturity_installments.cancel" }
    return allowed.has(key) && can(permissions[key])
  }

  const copyPlanNumber = () => {
    if (!plan.planNumber) return
    void copyText(plan.planNumber).then(() => { setCopied(true); window.setTimeout(() => setCopied(false), 1800) })
  }

  const handlePrint = async () => {
    try {
      const result = await printMISchedule(plan.id)
      const url = result.signedDownloadUrl ?? result.previewUrl
      if (url) window.open(url, "_blank", "noopener,noreferrer")
      else toast({ tone: "info", title: "Schedule generated", message: "The schedule document has been generated for this plan." })
    } catch (error) {
      toast({ tone: "danger", title: "Schedule could not be printed", message: toStructuredError(error, "The schedule could not be generated.").message })
    }
  }

  const openProcess = () => {
    setProcessError(null)
    const target = nextDueItem(plan)
    if (!target) {
      toast({ tone: "info", title: "No due installments", message: `${plan.planNumber} has no scheduled or missed installments due for payment yet.` })
      return
    }
    setProcessItem(target)
  }

  const confirmProcess = async () => {
    if (!processItem) return
    setProcessBusy(true); setProcessError(null)
    try {
      await processMIPayment(processItem.id)
      invalidateMaturityInstallmentQueries(queryClient, plan.id)
      toast({ tone: "success", title: "Payment processed", message: `Installment ${processItem.installmentNumber} on ${plan.planNumber} moved to payment pending.` })
      setProcessItem(null)
    } catch (error) {
      setProcessError(toStructuredError(error, "The installment payment could not be processed."))
    } finally {
      setProcessBusy(false)
    }
  }

  const confirmCancel = async () => {
    if (!cancelReason.trim()) {
      setCancelError({ code: "REASON_REQUIRED", message: "A reason is required to cancel an installment plan.", resolutionSteps: ["Describe why the plan is being cancelled.", "Do not include sensitive credentials in the reason."], fieldErrors: {}, retryable: false, status: 400, raw: null })
      return
    }
    setCancelBusy(true); setCancelError(null)
    try {
      await cancelMIPlan(plan.id, { reason: cancelReason.trim() })
      invalidateMaturityInstallmentQueries(queryClient, plan.id)
      toast({ tone: "success", title: "Plan cancelled", message: `${plan.planNumber} has been cancelled and the remaining installments waived.` })
      setCancelOpen(false); setCancelReason("")
    } catch (error) {
      setCancelError(toStructuredError(error, "The plan could not be cancelled."))
    } finally {
      setCancelBusy(false)
    }
  }

  const product = plan.productDisplay || plan.productCode
  return <div className="space-y-5 p-1 md:p-2">
    <section className="section-header p-5">
      <div className="flex flex-col gap-5 xl:flex-row xl:items-start xl:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2 text-xs font-bold uppercase tracking-[0.12em] text-white/70"><button type="button" onClick={() => navigate("/ordinary-life/maturity-installments")} className="inline-flex items-center gap-1 text-white/70 transition hover:text-white" aria-label="Back to maturity installment plans"><ArrowLeft size={14} aria-hidden="true" />Maturity installments</button><span>/</span><span>Plan detail</span></div>
          <div className="mt-3 flex flex-wrap items-center gap-3"><h1 className="break-all text-2xl font-extrabold tracking-tight sm:text-3xl">{plan.planNumber || "Plan detail"}</h1><button type="button" className="inline-flex min-h-9 items-center gap-2 rounded-lg border border-white/30 bg-white/10 px-3 text-xs font-bold text-white transition hover:bg-white/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white" onClick={copyPlanNumber} aria-label={copied ? "Plan number copied" : "Copy plan number"}>{copied ? <Check size={14} aria-hidden="true" /> : <Clipboard size={14} aria-hidden="true" />}{copied ? "Copied" : "Copy"}</button><PlanStatusBadge status={plan.status} statusDisplay={plan.statusDisplay} className="border-white/20 bg-white/15 text-white" /></div>
          <button type="button" onClick={() => navigate(`/ordinary-life/policies/${plan.policyId ?? plan.policyNumber}`)} className="mt-3 inline-flex max-w-full items-center gap-2 text-left text-sm font-bold text-white underline decoration-white/40 underline-offset-4 transition hover:decoration-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white" title="Open linked policy"><ExternalLink size={15} className="shrink-0" aria-hidden="true" /><span className="min-w-0"><span className="block truncate">{plan.policyNumber || "Linked policy unavailable"}</span>{product && <span className="mt-0.5 block truncate text-xs font-semibold text-white/70">{product}</span>}</span></button>
          <p className="mt-2 text-sm text-white/80">Policyholder: <span className="font-semibold text-white">{plan.policyholderDisplay || plan.policyholderName || "—"}</span></p>
          <div className="mt-3 flex flex-wrap items-center gap-2 text-xs font-semibold text-white/85"><span className="rounded-lg border border-white/20 bg-white/10 px-3 py-1.5">Start {dateLabel(plan.startDate)}</span><span className="rounded-lg border border-white/20 bg-white/10 px-3 py-1.5">End {dateLabel(plan.endDate)}</span></div>
        </div>
        <div className="flex flex-wrap items-center gap-2 xl:max-w-[42%] xl:justify-end"><span className="inline-flex items-center gap-2 rounded-lg border border-white/20 bg-white/10 px-3 py-2 text-xs font-semibold text-white/85"><ShieldCheck size={15} aria-hidden="true" />Financial facts from backend</span></div>
      </div>
    </section>

    {plan.status === "TERMINATED" && <div className="flex gap-3 rounded-[10px] border border-[var(--destructive)]/40 bg-[var(--destructive)]/10 px-4 py-3 text-sm text-[var(--destructive)]" role="alert"><TriangleAlert size={18} className="mt-0.5 shrink-0" aria-hidden="true" /><div><p className="font-bold">Plan terminated</p><p className="mt-1 leading-6">{plan.terminationReason || "This plan was terminated; the remaining maturity schedule was waived."}</p></div></div>}
    {plan.status === "COMPLETED" && <div className="flex gap-3 rounded-[10px] border border-[var(--success)]/40 bg-[var(--success)]/10 px-4 py-3 text-sm text-[var(--success)]" role="status"><CheckCircle2 size={18} className="mt-0.5 shrink-0" aria-hidden="true" /><div><p className="font-bold">Plan completed</p><p className="mt-1 leading-6">All {plan.installmentCount} installments have been paid and reconciled.{plan.completedAt ? ` Completed on ${dateLabel(plan.completedAt)}.` : ""}</p></div></div>}

    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
      <DetailStat label="Total maturity value"><MoneyCell value={plan.maturityValue} currency={plan.currency} /></DetailStat>
      <DetailStat label="Amount paid"><MoneyCell value={plan.paidAmount} currency={plan.currency} variant="paid" /></DetailStat>
      <DetailStat label="Balance remaining" helper={plan.currency}><MoneyCell value={plan.balance} currency={plan.currency} variant="balance" /></DetailStat>
    </div>

    <div className="surface-card flex flex-wrap items-center justify-between gap-3 p-3">
      <div><p className="text-xs font-bold uppercase tracking-[0.1em] text-[var(--muted-foreground)]">Available servicing actions</p><p className="mt-1 text-xs text-[var(--muted-foreground)]">Actions are shown only when allowed by both the backend state matrix and your permission.</p></div>
      <div className="flex flex-wrap items-center justify-end gap-2">
        {canAction("process_payment") && <button type="button" className="button-primary inline-flex items-center gap-2" onClick={openProcess}>Process Payment</button>}
        {canAction("print") && <button type="button" className="button-secondary" onClick={() => void handlePrint()}>Print schedule</button>}
        {canAction("cancel") && <button type="button" className="inline-flex min-h-10 items-center justify-center rounded-[10px] bg-[var(--destructive)] px-4 text-sm font-bold text-white" onClick={() => { setCancelError(null); setCancelReason(""); setCancelOpen(true) }}>Cancel plan</button>}
      </div>
    </div>

    <nav className="surface-card flex gap-1 overflow-x-auto p-1" aria-label="Maturity installment detail tabs">{TABS.map((tab) => <button key={tab.id} type="button" onClick={() => setSearchParams({ tab: tab.id })} className={`whitespace-nowrap rounded-[9px] px-4 py-2.5 text-sm font-bold transition ${activeTab === tab.id ? "bg-[var(--primary)] text-[var(--primary-foreground)]" : "text-[var(--muted-foreground)] hover:bg-[var(--secondary)] hover:text-[var(--foreground)]"}`} aria-current={activeTab === tab.id ? "page" : undefined}>{tab.label}</button>)}</nav>

    {activeTab === "overview" ? <OverviewTab plan={plan} /> : activeTab === "schedule" ? <ScheduleTab plan={plan} /> : activeTab === "payments" ? <PaymentsTab plan={plan} /> : activeTab === "audit" ? <AuditTab plan={plan} /> : <MIPlanDocumentsPanel plan={plan} canPrint={can("ol_maturity_installments.print")} />}

    <ConfirmModal open={Boolean(processItem)} title="Process installment payment" description={processItem ? `Installment ${processItem.installmentNumber} of ${plan.currency} ${processItem.amount} (due ${dateLabel(processItem.dueDate)}) will be moved to payment pending and a Front Office requisition raised.` : ""} confirmLabel={processBusy ? "Processing…" : "Process payment"} onClose={() => { if (!processBusy) setProcessItem(null) }} onConfirm={() => void confirmProcess()} tone="primary" />
    <Modal open={cancelOpen} title="Cancel plan" onClose={() => { if (!cancelBusy) { setCancelOpen(false); setCancelError(null) } }} size="md">
      <div className="space-y-4">
        <div className="rounded-lg border border-[var(--border)] bg-[var(--muted)]/35 p-4">
          <p className="text-xs font-bold uppercase tracking-[0.1em] text-[var(--muted-foreground)]">Selected plan</p>
          <p className="mt-1 text-sm font-bold">{plan.planNumber}</p>
          <p className="mt-1 text-xs text-[var(--muted-foreground)]">{plan.policyholderDisplay || plan.policyholderName} · {plan.policyNumber}</p>
          <div className="mt-3 flex flex-wrap items-center gap-3 text-sm"><PlanStatusBadge status={plan.status} statusDisplay={plan.statusDisplay} /><MoneyCell value={plan.balance} currency={plan.currency} label="Remaining balance" /></div>
        </div>
        <label className="block space-y-1.5"><span className="text-xs font-bold">Reason <span className="text-[var(--destructive)]">*</span></span><textarea value={cancelReason} onChange={(event) => { setCancelReason(event.target.value); setCancelError(null) }} rows={3} className="w-full rounded-[10px] border border-[var(--border)] bg-[var(--card)] px-3 py-2 text-sm outline-none focus:border-[var(--ring)] focus:ring-2 focus:ring-[color-mix(in_srgb,var(--ring)_18%,transparent)]" placeholder="Explain why the plan is being cancelled. Remaining installments will be waived." /></label>
        {cancelError && <ErrorCoach title="Plan could not be cancelled" message={cancelError.message} resolutionSteps={cancelError.resolutionSteps} />}
        <div className="flex flex-wrap justify-end gap-2 border-t border-[var(--border)] pt-4">
          <button type="button" className="button-secondary" onClick={() => { setCancelOpen(false); setCancelError(null) }} disabled={cancelBusy}>Cancel</button>
          <button type="button" className="inline-flex min-h-10 items-center justify-center rounded-[10px] bg-[var(--destructive)] px-4 text-sm font-bold text-white" onClick={() => void confirmCancel()} disabled={cancelBusy}>{cancelBusy ? "Cancelling…" : "Cancel plan"}</button>
        </div>
      </div>
    </Modal>
  </div>
}
