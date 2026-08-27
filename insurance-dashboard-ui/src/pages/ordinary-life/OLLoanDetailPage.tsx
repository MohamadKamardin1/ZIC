import { useMemo, useState, type ReactNode } from "react"
import { Check, Clipboard, ExternalLink, FileText, ShieldCheck } from "lucide-react"
import { useNavigate, useParams, useSearchParams } from "react-router-dom"
import { ErrorCoach } from "../../components/ErrorCoach"
import { ActionButtonGroup, LoanStatusBadge, MoneyCell } from "../../components/loans/LoanPrimitives"
import { MasterDetailPage } from "../../components/ui/Patterns"
import { useAccess } from "../../lib/access"
import { useLoanDetail } from "../../lib/loansHooks"
import { type LoanDetail } from "../../lib/loans"

const TABS = [
  { id: "overview", label: "Overview" },
  { id: "schedule", label: "Repayment Schedule" },
  { id: "repayments", label: "Repayments" },
  { id: "offsets", label: "Offsets" },
  { id: "documents", label: "Documents" },
  { id: "audit", label: "Audit" },
]

const TIMELINE_STEPS = [
  { id: "REQUESTED", label: "Requested" },
  { id: "APPROVED", label: "Approved" },
  { id: "DISBURSED", label: "Disbursed" },
]

function dateLabel(value?: string | null): string {
  if (!value) return "—"
  const parsed = new Date(`${value.slice(0, 10)}T00:00:00`)
  return Number.isNaN(parsed.getTime()) ? value : new Intl.DateTimeFormat("en-GB", { dateStyle: "medium" }).format(parsed)
}

function lifecyclePosition(status: string): number {
  if (status === "REQUESTED" || status === "REJECTED") return 0
  if (status === "APPROVED") return 1
  return 2
}

function copyText(value: string): Promise<void> {
  if (navigator.clipboard?.writeText) return navigator.clipboard.writeText(value)
  return Promise.resolve()
}

function DetailStat({ label, children, helper }: { label: string; children: ReactNode; helper?: string }) {
  return <div className="surface-card min-w-0 p-4"><p className="text-xs font-bold uppercase tracking-[0.1em] text-[var(--muted-foreground)]">{label}</p><p className="mt-2 break-words text-xl font-extrabold tracking-tight">{children}</p>{helper && <p className="mt-1 text-xs text-[var(--muted-foreground)]">{helper}</p>}</div>
}

function LoanHeader({ loan, onCopy, copied, onPolicy }: { loan: LoanDetail; onCopy: () => void; copied: boolean; onPolicy: () => void }) {
  return <section className="section-header p-5"><div className="flex flex-col gap-5 xl:flex-row xl:items-start xl:justify-between"><div className="min-w-0"><div className="flex flex-wrap items-center gap-2 text-xs font-bold uppercase tracking-[0.12em] text-white/70"><span>Ordinary Life</span><span>/</span><span>Policy loans</span><span>/</span><span>Loan detail</span></div><div className="mt-3 flex flex-wrap items-center gap-3"><h1 className="break-all text-2xl font-extrabold tracking-tight sm:text-3xl">{loan.loanNumber || "Loan detail"}</h1><button type="button" className="inline-flex min-h-9 items-center gap-2 rounded-lg border border-white/30 bg-white/10 px-3 text-xs font-bold text-white transition hover:bg-white/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white" onClick={onCopy} aria-label={copied ? "Loan number copied" : "Copy loan number"}>{copied ? <Check size={14} aria-hidden="true" /> : <Clipboard size={14} aria-hidden="true" />}{copied ? "Copied" : "Copy"}</button><LoanStatusBadge status={loan.status} statusDisplay={loan.statusDisplay} className="border-white/20 bg-white/15 text-white" /></div><button type="button" onClick={onPolicy} className="mt-3 inline-flex max-w-full items-center gap-2 truncate text-left text-sm font-bold text-white underline decoration-white/40 underline-offset-4 transition hover:decoration-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white" title="Open linked policy"><ExternalLink size={15} className="shrink-0" aria-hidden="true" /><span className="truncate">{loan.policyDisplay || loan.policyNumber || "Linked policy unavailable"}</span></button><p className="mt-2 text-sm text-white/80">Policyholder: <span className="font-semibold text-white">{loan.policyholderName || loan.partnerDisplay || "—"}</span></p></div><div className="flex flex-wrap items-center gap-2 xl:max-w-[42%] xl:justify-end"><span className="inline-flex items-center gap-2 rounded-lg border border-white/20 bg-white/10 px-3 py-2 text-xs font-semibold text-white/85"><ShieldCheck size={15} aria-hidden="true" />Financial facts from backend</span></div></div></section>
}

function StatusTimeline({ loan }: { loan: LoanDetail }) {
  const currentPosition = lifecyclePosition(String(loan.status).toUpperCase())
  return <section className="surface-card p-5"><div className="flex flex-wrap items-start justify-between gap-3"><div><h2 className="text-base font-bold">Status timeline</h2><p className="mt-1 text-xs text-[var(--muted-foreground)]">Requested → Approved → Disbursed lifecycle checkpoints</p></div><LoanStatusBadge status={loan.status} statusDisplay={loan.statusDisplay} /></div><ol className="mt-5 grid gap-3 md:grid-cols-3">{TIMELINE_STEPS.map((step, index) => { const complete = index <= currentPosition && loan.status !== "REJECTED"; const date = index === 0 ? loan.createdAt : index === 1 ? loan.approvedAt : loan.disbursementDate; return <li key={step.id} className={`relative rounded-lg border p-3 ${complete ? "border-[var(--success)]/40 bg-[var(--success)]/5" : "border-[var(--border)] bg-[var(--muted)]/20"}`}><div className="flex items-center gap-2"><span className={`flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold ${complete ? "bg-[var(--success)] text-white" : "bg-[var(--muted)] text-[var(--muted-foreground)]"}`}>{complete ? <Check size={14} aria-hidden="true" /> : index + 1}</span><span className={`text-sm font-bold ${complete ? "text-[var(--foreground)]" : "text-[var(--muted-foreground)]"}`}>{step.label}</span></div><p className="mt-2 pl-9 text-xs text-[var(--muted-foreground)]">{date ? dateLabel(date) : complete ? "Completed" : "Pending"}</p></li>})}</ol>{loan.status === "REJECTED" && <p className="mt-4 rounded-lg border border-[var(--destructive)]/30 bg-[var(--destructive)]/5 px-3 py-2 text-sm text-[var(--destructive)]">This request was rejected. {loan.rejectionReason || "Review the audit trail for the recorded reason."}</p>}</section>
}

function OverviewTab({ loan }: { loan: LoanDetail }) {
  const offsetTotal = loan.offsets.reduce((sum, row) => sum + Number(row.offsetAmount || 0), 0)
  return <div className="space-y-5"><div className="grid gap-4 lg:grid-cols-2"><section className="surface-card p-5"><div className="flex items-center gap-2"><FileText size={17} className="text-[var(--primary)]" aria-hidden="true" /><h2 className="text-base font-bold">Loan terms</h2></div><dl className="mt-4 grid gap-3 sm:grid-cols-2"><div><dt className="text-xs text-[var(--muted-foreground)]">Product</dt><dd className="mt-1 text-sm font-semibold">{loan.productDisplay || "—"}</dd></div><div><dt className="text-xs text-[var(--muted-foreground)]">Repayment mode</dt><dd className="mt-1 text-sm font-semibold">{loan.repaymentMode || "—"}</dd></div><div><dt className="text-xs text-[var(--muted-foreground)]">Disbursement date</dt><dd className="mt-1 text-sm font-semibold">{dateLabel(loan.disbursementDate)}</dd></div><div><dt className="text-xs text-[var(--muted-foreground)]">Effective interest rate</dt><dd className="mt-1 text-sm font-semibold">{loan.interestRate || "0.00"}% · {loan.compoundingFrequency || "—"}</dd></div><div><dt className="text-xs text-[var(--muted-foreground)]">Term</dt><dd className="mt-1 text-sm font-semibold">{loan.termMonths ? `${loan.termMonths} months` : "—"}</dd></div><div><dt className="text-xs text-[var(--muted-foreground)]">Maturity date</dt><dd className="mt-1 text-sm font-semibold">{dateLabel(loan.maturityDate)}</dd></div></dl></section><section className="surface-card p-5"><h2 className="text-base font-bold">Linked policy</h2><p className="mt-1 text-xs text-[var(--muted-foreground)]">The policy remains the source transaction for this loan.</p><dl className="mt-4 space-y-3"><div className="flex flex-wrap items-start justify-between gap-3 border-b border-[var(--border)] pb-3"><dt className="text-xs text-[var(--muted-foreground)]">Policy</dt><dd className="max-w-[70%] text-right text-sm font-semibold">{loan.policyDisplay || loan.policyNumber || "—"}</dd></div><div className="flex flex-wrap items-start justify-between gap-3 border-b border-[var(--border)] pb-3"><dt className="text-xs text-[var(--muted-foreground)]">Policyholder</dt><dd className="max-w-[70%] text-right text-sm font-semibold">{loan.policyholderName || loan.partnerDisplay || "—"}</dd></div><div className="flex flex-wrap items-start justify-between gap-3"><dt className="text-xs text-[var(--muted-foreground)]">Agent</dt><dd className="max-w-[70%] text-right text-sm font-semibold">{loan.agentDisplay || "—"}</dd></div></dl></section></div><div className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]"><StatusTimeline loan={loan} /><section className="surface-card p-5"><h2 className="text-base font-bold">Offset history</h2><p className="mt-1 text-xs text-[var(--muted-foreground)]">Automatic claim, surrender, or maturity settlement reconciliation.</p>{loan.offsets.length === 0 ? <p className="mt-5 rounded-lg border border-dashed border-[var(--border)] px-3 py-5 text-sm text-[var(--muted-foreground)]">No offsets have been applied to this loan.</p> : <div className="mt-4 space-y-3">{loan.offsets.slice(0, 3).map((offset) => <div key={offset.id} className="flex items-start justify-between gap-3 rounded-lg border border-[var(--border)] p-3"><div><p className="text-sm font-semibold">{offset.sourceType || "Settlement"}</p><p className="mt-1 text-xs text-[var(--muted-foreground)]">{dateLabel(offset.createdAt)}</p></div><MoneyCell value={offset.offsetAmount} currency={loan.currency} /></div>)}<div className="flex items-center justify-between border-t border-[var(--border)] pt-3 text-sm font-bold"><span>Total offset</span><MoneyCell value={offsetTotal} currency={loan.currency} /></div></div>}</section></div></div>
}

export default function OLLoanDetailPage() {
  const { loanId } = useParams<{ loanId: string }>()
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const [copied, setCopied] = useState(false)
  const { access, hasPermission, isSuperAdmin } = useAccess()
  const detailQuery = useLoanDetail(loanId)
  const loan = detailQuery.data
  const activeTab = TABS.some((tab) => tab.id === searchParams.get("tab")) ? searchParams.get("tab") || "overview" : "overview"
  const permissions = useMemo(() => access.permissions.map((permission) => `${permission.module}.${permission.action}`), [access.permissions])
  const can = (permission: string) => isSuperAdmin || Boolean(hasPermission?.(permission) || permissions.includes(permission))

  const copyLoanNumber = () => {
    if (!loan?.loanNumber) return
    void copyText(loan.loanNumber).then(() => { setCopied(true); window.setTimeout(() => setCopied(false), 1800) })
  }

  if (detailQuery.isLoading) return <div className="space-y-4 p-2" aria-label="Loading loan detail"><div className="h-48 animate-pulse rounded-xl bg-[var(--muted)]" /><div className="grid gap-4 sm:grid-cols-3"><div className="h-28 animate-pulse rounded-xl bg-[var(--muted)]" /><div className="h-28 animate-pulse rounded-xl bg-[var(--muted)]" /><div className="h-28 animate-pulse rounded-xl bg-[var(--muted)]" /></div><div className="h-64 animate-pulse rounded-xl bg-[var(--muted)]" /></div>
  if (detailQuery.error || !loan) return <div className="p-2"><ErrorCoach title="Loan detail unavailable" message={detailQuery.error?.message || "The requested loan could not be loaded."} resolutionSteps={["Return to the Loans register and choose an available record.", "Confirm your `ol_loans.view` permission and retry."]} onDismiss={() => navigate("/ordinary-life/loans")} /></div>

  const actionPermissions = permissions
  return <div className="space-y-5 p-1 md:p-2"><LoanHeader loan={loan} onCopy={copyLoanNumber} copied={copied} onPolicy={() => navigate(`/ordinary-life/policies/${loan.policyId ?? loan.policyNumber}`)} /><div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4"><DetailStat label="Principal amount"><MoneyCell value={loan.principalAmount} currency={loan.currency} /></DetailStat><DetailStat label="Disbursed amount"><MoneyCell value={loan.disbursedAmount} currency={loan.currency} /></DetailStat><DetailStat label="Outstanding balance" helper={loan.currency}><MoneyCell value={loan.outstandingBalance} currency={loan.currency} /></DetailStat><DetailStat label="Interest / term" helper={`Matures ${dateLabel(loan.maturityDate)}`}>{loan.interestRate || "0.00"}% <span className="text-base font-semibold">· {loan.termMonths || "—"} months</span></DetailStat></div><div className="surface-card flex flex-wrap items-center justify-between gap-3 p-3"><div><p className="text-xs font-bold uppercase tracking-[0.1em] text-[var(--muted-foreground)]">Available servicing actions</p><p className="mt-1 text-xs text-[var(--muted-foreground)]">Actions are shown only when allowed by both the backend state matrix and your permission.</p></div><div className="flex flex-wrap items-center justify-end gap-2"><button type="button" className="button-secondary" onClick={() => navigate("/ordinary-life/loans?request=1")} disabled={!can("ol_loans.request")}>Request Loan</button><ActionButtonGroup loan={loan} onAction={(action) => navigate(`/ordinary-life/loans/${loan.id}?action=${action}`)} permissions={actionPermissions} actions={["disburse", "repay", "offset"]} /></div></div><nav className="surface-card flex gap-1 overflow-x-auto p-1" aria-label="Loan detail tabs">{TABS.map((tab) => <button key={tab.id} type="button" onClick={() => setSearchParams({ tab: tab.id })} className={`whitespace-nowrap rounded-[9px] px-4 py-2.5 text-sm font-bold transition ${activeTab === tab.id ? "bg-[var(--primary)] text-[var(--primary-foreground)]" : "text-[var(--muted-foreground)] hover:bg-[var(--secondary)] hover:text-[var(--foreground)]"}`} aria-current={activeTab === tab.id ? "page" : undefined}>{tab.label}</button>)}</nav>{activeTab === "overview" ? <OverviewTab loan={loan} /> : <div className="surface-card p-6"><h2 className="text-base font-bold">{TABS.find((tab) => tab.id === activeTab)?.label}</h2><p className="mt-2 text-sm leading-6 text-[var(--muted-foreground)]">This tab is connected to the same loan detail contract and will render its dedicated servicing history in the next sequential prompt.</p></div>}</div>
}
