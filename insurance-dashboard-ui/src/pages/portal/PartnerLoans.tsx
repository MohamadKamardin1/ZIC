import { ArrowLeft, Eye, HelpCircle, LifeBuoy, ShieldCheck } from "lucide-react"
import { useState } from "react"
import { Link, useNavigate, useParams } from "react-router-dom"
import { ErrorCoach } from "../../components/ErrorCoach"
import { DecimalInput, FormGrid, TextInput } from "../../components/ui/FormControls"
import { InfoBanner, Modal } from "../../components/ui/Overlays"
import { useToast } from "../../components/ui/Toast"
import { usePortalLoan, usePortalLoanRequestMutation, usePortalLoans } from "../../lib/loanPortalHooks"
import type { PortalLoan, PortalLoanScheduleRow } from "../../lib/loanPortal"
import { formatMoney } from "../../lib/commitmentsDisplay"

export const PORTAL_LOAN_HELP_MESSAGE = "For changes to loan terms, contact ZIC Finance."

function dateLabel(value?: string | null): string {
  if (!value) return "—"
  const parsed = new Date(`${String(value).slice(0, 10)}T00:00:00`)
  return Number.isNaN(parsed.getTime()) ? String(value) : new Intl.DateTimeFormat("en-GB", { dateStyle: "medium" }).format(parsed)
}

function statusTone(status: string): "success" | "info" | "warning" | "danger" | "neutral" {
  const normalized = status.toUpperCase()
  if (["ACTIVE", "PARTIALLY REPAID", "DISBURSED"].includes(normalized)) return "success"
  if (["REQUESTED", "APPROVED", "DEFAULTED"].includes(normalized)) return normalized === "DEFAULTED" ? "danger" : "warning"
  if (["SETTLED", "CLOSED", "OFFSET ON CLAIM", "OFFSET ON SURRENDER", "OFFSET ON MATURITY"].includes(normalized)) return "neutral"
  return "info"
}

function StatusPill({ status }: { status: string }) {
  const classes = {
    success: "bg-[var(--success)]/12 text-[var(--success)]",
    info: "bg-[var(--info)]/12 text-[var(--info)]",
    warning: "bg-[var(--warning)]/15 text-[var(--foreground)]",
    danger: "bg-[var(--destructive)]/12 text-[var(--destructive)]",
    neutral: "bg-[var(--muted)] text-[var(--muted-foreground)]",
  }
  const tone = statusTone(status)
  return <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-bold ${classes[tone]}`} role="status">{status || "Not recorded"}</span>
}

function PortalBanner() {
  return <InfoBanner title="Partner portal — read-only"><p className="flex flex-wrap items-start gap-2 text-sm"><HelpCircle size={16} className="mt-0.5 shrink-0" aria-hidden="true" /><span>{PORTAL_LOAN_HELP_MESSAGE}</span><Link to="/tickets" className="inline-flex items-center gap-1 font-semibold text-[var(--primary)] underline-offset-2 hover:underline" data-testid="loan-portal-raise-ticket"><LifeBuoy size={14} aria-hidden="true" />Raise Ticket</Link></p></InfoBanner>
}

function sanitizePortalLoanError(error: unknown): { message: string; steps: string[] } {
  const message = error instanceof Error && error.message ? error.message : "Your partner-scoped loan information could not be loaded."
  return { message, steps: ["Retry the request in a moment.", "Confirm the loan belongs to your linked partner profile.", "Contact ZIC Finance if the issue continues."] }
}

function ScheduleTable({ rows, currency }: { rows: PortalLoanScheduleRow[]; currency: string }) {
  return <section className="surface-card overflow-hidden" data-testid="portal-loan-schedule"><div className="border-b border-[var(--border)] bg-[var(--muted)]/35 px-5 py-3"><h2 className="text-sm font-bold">Repayment schedule</h2><p className="text-xs text-[var(--muted-foreground)]">Contractual schedule details are visible for planning; changes remain staff-controlled.</p></div><div className="overflow-x-auto"><table className="w-full min-w-[760px] text-left text-sm"><caption className="sr-only">Your loan repayment schedule</caption><thead className="bg-[var(--muted)]/45 text-xs uppercase tracking-[0.08em] text-[var(--muted-foreground)]"><tr>{["Installment", "Due date", "Principal", "Interest", "Amount paid", "Balance", "Status"].map((heading) => <th key={heading} scope="col" className="px-4 py-2.5 font-bold">{heading}</th>)}</tr></thead><tbody className="divide-y divide-[var(--border)]">{rows.map((row) => <tr key={`${row.installmentNumber}-${row.dueDate}`}><td className="px-4 py-2.5 font-semibold">{row.installmentNumber}</td><td className="px-4 py-2.5">{dateLabel(row.dueDate)}</td><td className="px-4 py-2.5 tabular-nums">{formatMoney(row.principalDue, currency)}</td><td className="px-4 py-2.5 tabular-nums">{formatMoney(row.interestDue, currency)}</td><td className="px-4 py-2.5 tabular-nums">{formatMoney(row.amountPaid, currency)}</td><td className="px-4 py-2.5 tabular-nums font-semibold">{formatMoney(row.balance, currency)}</td><td className="px-4 py-2.5"><StatusPill status={row.status} /></td></tr>)}</tbody></table></div></section>
}

function RequestLoanModal({ loan, open, onClose }: { loan: PortalLoan | null; open: boolean; onClose: () => void }) {
  const { toast } = useToast()
  const mutation = usePortalLoanRequestMutation()
  const [amount, setAmount] = useState("")
  const [termMonths, setTermMonths] = useState("12")
  const [repaymentMode, setRepaymentMode] = useState("")
  const [reason, setReason] = useState("")
  const [errors, setErrors] = useState<Record<string, string>>({})
  if (!loan) return null

  const clearAndClose = () => {
    setAmount("")
    setTermMonths("12")
    setRepaymentMode("")
    setReason("")
    setErrors({})
    onClose()
  }

  const resetAndClose = () => {
    if (mutation.isPending) return
    clearAndClose()
  }

  const submit = () => {
    const next: Record<string, string> = {}
    const parsedAmount = Number(amount)
    const parsedTerm = Number(termMonths)
    if (!amount || !Number.isFinite(parsedAmount) || parsedAmount <= 0) next.amount = "Enter a requested amount greater than zero."
    if (!termMonths || !Number.isInteger(parsedTerm) || parsedTerm <= 0) next.termMonths = "Enter a whole number of months greater than zero."
    if (!repaymentMode.trim()) next.repaymentMode = "Enter the configured repayment mode for this policy."
    if (!reason.trim()) next.reason = "Explain why the loan is being requested."
    setErrors(next)
    if (Object.keys(next).length > 0) return
    mutation.mutate(
      {
        payload: { policyNumber: loan.policyNumber, requestedAmount: parsedAmount.toFixed(2), termMonths: parsedTerm, repaymentMode: repaymentMode.trim(), reason: reason.trim() },
        idempotencyKey: `portal-loan-request-${loan.policyNumber}-${Date.now()}`,
      },
      {
        onSuccess: () => {
          toast({ title: "Loan request submitted", message: "Your request is pending ZIC Finance review.", tone: "success" })
          clearAndClose()
        },
      },
    )
  }

  return <Modal open={open} title="Request Loan" description={`Submit a request against policy ${loan.policyNumber}. ZIC Finance will validate the configured limits before approval.`} onClose={resetAndClose} size="lg" footer={<><button type="button" className="button-secondary" onClick={resetAndClose} disabled={mutation.isPending}>Cancel</button><button type="button" className="button-primary" onClick={submit} disabled={mutation.isPending}>{mutation.isPending ? "Submitting…" : "Submit Request"}</button></>}><div className="space-y-4"><InfoBanner title="Partner request">This form sends a request only. Disbursement, repayment, offset, and term changes are not available in the partner portal.</InfoBanner><div className="grid gap-3 sm:grid-cols-2"><div className="rounded-[10px] border border-[var(--border)] bg-[var(--muted)]/25 px-3 py-3"><p className="text-xs text-[var(--muted-foreground)]">Policy</p><p className="mt-1 text-sm font-semibold">{loan.policyNumber}</p></div><div className="rounded-[10px] border border-[var(--border)] bg-[var(--muted)]/25 px-3 py-3"><p className="text-xs text-[var(--muted-foreground)]">Product</p><p className="mt-1 text-sm font-semibold">{loan.product || "—"}</p></div></div><FormGrid columns={2}><DecimalInput label="Requested amount" name="portal-request-amount" required value={amount} onChange={(event) => { setAmount(event.target.value); setErrors((current) => ({ ...current, amount: "" })) }} error={errors.amount} placeholder="Enter amount" /><TextInput label="Term (months)" name="portal-request-term" required value={termMonths} onChange={(event) => { setTermMonths(event.target.value); setErrors((current) => ({ ...current, termMonths: "" })) }} error={errors.termMonths} inputMode="numeric" placeholder="e.g. 12" /><TextInput label="Repayment mode" name="portal-request-mode" required value={repaymentMode} onChange={(event) => { setRepaymentMode(event.target.value); setErrors((current) => ({ ...current, repaymentMode: "" })) }} error={errors.repaymentMode} placeholder="Configured mode" /><TextInput label="Reason" name="portal-request-reason" required value={reason} onChange={(event) => { setReason(event.target.value); setErrors((current) => ({ ...current, reason: "" })) }} error={errors.reason} placeholder="Explain the request" /></FormGrid>{mutation.error && <ErrorCoach title="Loan request could not be submitted" message={mutation.error.message} resolutionSteps={["Review the requested amount, term, and repayment mode.", "Confirm the policy is eligible and has no active loan.", "Retry or contact ZIC Finance for assistance."]} />}</div></Modal>
}

export function PartnerLoans() {
  const navigate = useNavigate()
  const list = usePortalLoans()
  const [requestLoan, setRequestLoan] = useState<PortalLoan | null>(null)
  const rows = list.data?.results ?? []
  return <div className="min-h-full px-4 py-5 sm:px-6 lg:px-8" data-testid="portal-loans"><div className="mx-auto max-w-[1560px] space-y-5"><header className="flex flex-wrap items-end justify-between gap-4 border-b border-[var(--border)] pb-5"><div><div className="mb-2 flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.16em] text-[var(--muted-foreground)]"><span>ZIC</span><span>/</span><span>Partner Portal</span><span>/</span><span>Loans</span></div><h1 className="text-2xl font-semibold tracking-[-0.04em] text-[var(--foreground)]">My Loans</h1><p className="mt-1 text-sm text-[var(--muted-foreground)]">View loans associated with your linked policies. Financial servicing actions remain with ZIC Finance.</p></div><div className="flex flex-wrap items-center gap-2"><span className="inline-flex items-center gap-2 rounded-lg border border-[var(--border)] px-3 py-2 text-xs font-semibold"><ShieldCheck size={15} className="text-[var(--success)]" aria-hidden="true" />Partner-scoped</span><Link to="/tickets" className="inline-flex items-center gap-2 text-sm font-semibold text-[var(--primary)] underline-offset-2 hover:underline"><LifeBuoy size={15} aria-hidden="true" />Raise Ticket</Link></div></header><PortalBanner />{list.isLoading && <p className="py-10 text-center text-sm text-[var(--muted-foreground)]" role="status">Loading your loans…</p>}{list.isError && <ErrorCoach title="Loans could not be loaded" message={sanitizePortalLoanError(list.error).message} resolutionSteps={sanitizePortalLoanError(list.error).steps} />}{!list.isLoading && !list.isError && rows.length === 0 && <p className="py-10 text-center text-sm text-[var(--muted-foreground)]">You have no loans associated with your linked policies.</p>}{rows.length > 0 && <section className="surface-card overflow-hidden" data-testid="portal-loans-table"><div className="overflow-x-auto"><table className="w-full min-w-[1120px] text-left text-sm"><caption className="sr-only">Your partner-scoped loans</caption><thead className="bg-[var(--muted)]/45 text-xs uppercase tracking-[0.08em] text-[var(--muted-foreground)]"><tr>{["Loan", "Policy", "Product", "Status", "Principal", "Outstanding", "Rate / term", "Disbursement", "Maturity", "Actions"].map((heading) => <th key={heading} scope="col" className="px-4 py-2.5 font-bold">{heading}</th>)}</tr></thead><tbody className="divide-y divide-[var(--border)]">{rows.map((row) => <tr key={row.loanNumber} data-testid={`portal-loan-row-${row.loanNumber}`} className="transition hover:bg-[var(--muted)]/25"><td className="px-4 py-2.5 font-semibold">{row.loanNumber}</td><td className="px-4 py-2.5">{row.policyNumber}</td><td className="px-4 py-2.5">{row.product || "—"}</td><td className="px-4 py-2.5"><StatusPill status={row.status} /></td><td className="px-4 py-2.5 tabular-nums">{formatMoney(row.principalAmount, row.currency)}</td><td className="px-4 py-2.5 tabular-nums font-semibold">{formatMoney(row.outstandingBalance, row.currency)}</td><td className="px-4 py-2.5">{row.interestRate}% · {row.termMonths} months</td><td className="px-4 py-2.5">{dateLabel(row.disbursementDate)}</td><td className="px-4 py-2.5">{dateLabel(row.maturityDate)}</td><td className="px-4 py-2.5"><div className="flex flex-wrap gap-2"><button type="button" className="button-secondary inline-flex items-center gap-1.5 !min-h-9 !px-3 text-xs" onClick={() => navigate(`/portal/loans/${encodeURIComponent(row.loanNumber)}`)}><Eye size={14} aria-hidden="true" />View</button>{row.requestAllowed && <button type="button" className="button-primary !min-h-9 !px-3 text-xs" onClick={() => setRequestLoan(row)}>Request Loan</button>}</div></td></tr>)}</tbody></table></div></section>}</div><RequestLoanModal loan={requestLoan} open={Boolean(requestLoan)} onClose={() => setRequestLoan(null)} /></div>
}

export function PartnerLoanDetail() {
  const { loanNumber } = useParams<{ loanNumber: string }>()
  const detail = usePortalLoan(loanNumber ? decodeURIComponent(loanNumber) : undefined)
  const d = detail.data
  if (!loanNumber) return null
  if (detail.isLoading) return <p className="p-8 text-center text-sm text-[var(--muted-foreground)]" role="status">Loading your loan…</p>
  if (detail.isError || !d) { const safe = sanitizePortalLoanError(detail.error); return <div className="space-y-4 px-4 py-6"><Link to="/portal/loans" className="button-secondary inline-flex items-center gap-2"><ArrowLeft size={15} aria-hidden="true" />Back to my loans</Link><ErrorCoach title="Loan could not be loaded" message={safe.message} resolutionSteps={safe.steps} /></div> }
  return <div className="min-h-full space-y-5 px-4 py-5 sm:px-6 lg:px-8" data-testid="portal-loan-detail"><header className="surface-card px-5 py-4"><div className="flex flex-wrap items-start justify-between gap-4"><div><div className="mb-1 flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.16em] text-[var(--muted-foreground)]"><span>ZIC</span><span>/</span><span>Partner Portal</span><span>/</span><span>{d.loanNumber}</span></div><h1 className="text-2xl font-semibold tracking-[-0.04em] text-[var(--foreground)]">{d.loanNumber}</h1><p className="mt-1 text-sm text-[var(--muted-foreground)]">{d.policyNumber} · {d.product || "Loan"}</p><div className="mt-3 flex flex-wrap items-center gap-2"><StatusPill status={d.status} /><span className="text-sm font-semibold">{formatMoney(d.outstandingBalance, d.currency)} outstanding</span></div></div><Link to="/portal/loans" className="button-secondary inline-flex items-center gap-2"><ArrowLeft size={15} aria-hidden="true" />Back</Link></div></header><PortalBanner /><section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4" data-testid="portal-loan-overview"><div className="surface-card p-4"><p className="text-xs text-[var(--muted-foreground)]">Policyholder</p><p className="mt-1 text-sm font-semibold">{d.policyholder || "—"}</p></div><div className="surface-card p-4"><p className="text-xs text-[var(--muted-foreground)]">Principal amount</p><p className="mt-1 text-lg font-bold">{formatMoney(d.principalAmount, d.currency)}</p></div><div className="surface-card p-4"><p className="text-xs text-[var(--muted-foreground)]">Outstanding balance</p><p className="mt-1 text-lg font-bold">{formatMoney(d.outstandingBalance, d.currency)}</p></div><div className="surface-card p-4"><p className="text-xs text-[var(--muted-foreground)]">Interest / term</p><p className="mt-1 text-sm font-semibold">{d.interestRate}% · {d.termMonths} months</p></div></section><section className="surface-card px-5 py-4"><div className="flex flex-wrap items-start justify-between gap-3"><div><h2 className="text-base font-bold">Loan overview</h2><p className="mt-1 text-xs text-[var(--muted-foreground)]">This portal response is intentionally limited to partner-safe servicing information.</p></div><span className="inline-flex items-center gap-2 text-xs font-semibold text-[var(--muted-foreground)]"><ShieldCheck size={15} aria-hidden="true" />Read-only</span></div><dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-4"><div><dt className="text-xs text-[var(--muted-foreground)]">Repayment mode</dt><dd className="mt-1 font-semibold">{d.repaymentMode || "—"}</dd></div><div><dt className="text-xs text-[var(--muted-foreground)]">Compounding</dt><dd className="mt-1 font-semibold">{d.compoundingFrequency || "—"}</dd></div><div><dt className="text-xs text-[var(--muted-foreground)]">Disbursement date</dt><dd className="mt-1 font-semibold">{dateLabel(d.disbursementDate)}</dd></div><div><dt className="text-xs text-[var(--muted-foreground)]">Maturity date</dt><dd className="mt-1 font-semibold">{dateLabel(d.maturityDate)}</dd></div>{d.totalRepaid !== undefined && <div><dt className="text-xs text-[var(--muted-foreground)]">Total repaid</dt><dd className="mt-1 font-semibold">{formatMoney(d.totalRepaid, d.currency)}</dd></div>}</dl></section>{d.schedule && d.schedule.length > 0 ? <ScheduleTable rows={d.schedule} currency={d.currency} /> : <section className="surface-card px-5 py-6 text-sm text-[var(--muted-foreground)]">No repayment schedule is currently available in the partner portal.</section>}<InfoBanner title="Servicing restrictions">View is available for your linked partner account. Disburse, repay, offset, reverse, and loan-term management actions are not available here.</InfoBanner></div>
}

export default PartnerLoans
