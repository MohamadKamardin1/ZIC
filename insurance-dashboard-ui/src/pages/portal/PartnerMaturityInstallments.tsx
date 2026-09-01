import { ArrowLeft, Eye, HelpCircle, LifeBuoy, ShieldCheck } from "lucide-react"
import { Link, useNavigate, useParams } from "react-router-dom"
import { ErrorCoach } from "../../components/ErrorCoach"
import { ItemStatusBadge, MoneyCell, PlanStatusBadge } from "../../components/maturityInstallments/MIPrimitives"
import { InfoBanner } from "../../components/ui/Overlays"
import type { MIPortalPlan } from "../../lib/maturityInstallments"
import { useMIPortalPlanDetail, useMIPortalPlanList } from "../../lib/maturityInstallmentsHooks"

export const MI_PORTAL_HELP_MESSAGE = "Payout schedule. Payments are processed by ZIC Finance."

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
  const parsed = new Date(`${String(value).slice(0, 10)}T00:00:00`)
  return Number.isNaN(parsed.getTime()) ? String(value) : new Intl.DateTimeFormat("en-GB", { dateStyle: "medium" }).format(parsed)
}

function sanitizePortalMaturityError(error: unknown): { message: string; steps: string[] } {
  const message = error instanceof Error && error.message ? error.message : "Your partner-scoped installment information could not be loaded."
  return { message, steps: ["Retry the request in a moment.", "Confirm the plan belongs to your linked partner profile.", "Contact ZIC Finance if the issue continues."] }
}

function PortalBanner() {
  return <InfoBanner title="Payout schedule"><p className="flex flex-wrap items-start gap-2 text-sm"><HelpCircle size={16} className="mt-0.5 shrink-0" aria-hidden="true" /><span>Payments are processed by ZIC Finance.</span><Link to="/tickets" className="inline-flex items-center gap-1 font-semibold text-[var(--primary)] underline-offset-2 hover:underline" data-testid="mi-portal-raise-ticket"><LifeBuoy size={14} aria-hidden="true" />Raise Ticket</Link></p></InfoBanner>
}

export function PartnerMaturityInstallments() {
  const navigate = useNavigate()
  const list = useMIPortalPlanList()
  const rows = list.data ?? []
  return <div className="min-h-full px-4 py-5 sm:px-6 lg:px-8" data-testid="portal-maturity-installments"><div className="mx-auto max-w-[1560px] space-y-5"><header className="flex flex-wrap items-end justify-between gap-4 border-b border-[var(--border)] pb-5"><div><div className="mb-2 flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.16em] text-[var(--muted-foreground)]"><span>ZIC</span><span>/</span><span>Partner Portal</span><span>/</span><span>Maturity Installments</span></div><h1 className="text-2xl font-semibold tracking-[-0.04em] text-[var(--foreground)]">My Installments</h1><p className="mt-1 text-sm text-[var(--muted-foreground)]">View the payout schedule associated with your linked policies. Payments are processed by ZIC Finance.</p></div><div className="flex flex-wrap items-center gap-2"><span className="inline-flex items-center gap-2 rounded-lg border border-[var(--border)] px-3 py-2 text-xs font-semibold"><ShieldCheck size={15} className="text-[var(--success)]" aria-hidden="true" />Partner-scoped</span><Link to="/tickets" className="inline-flex items-center gap-2 text-sm font-semibold text-[var(--primary)] underline-offset-2 hover:underline"><LifeBuoy size={15} aria-hidden="true" />Raise Ticket</Link></div></header><PortalBanner />{list.isLoading && <p className="py-10 text-center text-sm text-[var(--muted-foreground)]" role="status">Loading your installment plans…</p>}{list.isError && <ErrorCoach title="Installment plans could not be loaded" message={sanitizePortalMaturityError(list.error).message} resolutionSteps={sanitizePortalMaturityError(list.error).steps} />}{!list.isLoading && !list.isError && rows.length === 0 && <p className="py-10 text-center text-sm text-[var(--muted-foreground)]">You have no installment plans associated with your linked policies.</p>}{rows.length > 0 && <section className="surface-card overflow-hidden" data-testid="portal-mi-table"><div className="overflow-x-auto"><table className="w-full min-w-[1080px] text-left text-sm"><caption className="sr-only">Your partner-scoped maturity installment plans</caption><thead className="bg-[var(--muted)]/45 text-xs uppercase tracking-[0.08em] text-[var(--muted-foreground)]"><tr>{["Plan", "Policy", "Status", "Frequency", "Installments", "Total payout", "Paid to date", "Start", "End", "Actions"].map((heading) => <th key={heading} scope="col" className="px-4 py-2.5 font-bold">{heading}</th>)}</tr></thead><tbody className="divide-y divide-[var(--border)]">{rows.map((row) => <tr key={row.id} data-testid={`portal-mi-row-${row.planNumber}`} className="transition hover:bg-[var(--muted)]/25"><td className="px-4 py-2.5 font-semibold">{row.planNumber}</td><td className="px-4 py-2.5">{row.policyNumber}</td><td className="px-4 py-2.5"><PlanStatusBadge status={row.status} statusDisplay={row.statusDisplay} /></td><td className="px-4 py-2.5">{frequencyLabel(row.frequency)}</td><td className="px-4 py-2.5 tabular-nums">{row.paidInstallments} of {row.installmentCount}</td><td className="px-4 py-2.5 tabular-nums"><MoneyCell value={row.totalAmount} currency={row.currency} /></td><td className="px-4 py-2.5 tabular-nums"><MoneyCell value={row.paidAmount} currency={row.currency} variant="paid" /></td><td className="px-4 py-2.5">{dateLabel(row.startDate)}</td><td className="px-4 py-2.5">{dateLabel(row.endDate)}</td><td className="px-4 py-2.5"><button type="button" className="button-secondary inline-flex items-center gap-1.5 !min-h-9 !px-3 text-xs" onClick={() => navigate(`/portal/maturity-installments/${encodeURIComponent(row.planNumber)}`)}><Eye size={14} aria-hidden="true" />View</button></td></tr>)}</tbody></table></div></section>}</div></div>
}

export function PartnerMaturityInstallmentDetail() {
  const { planId } = useParams<{ planId: string }>()
  const detail = useMIPortalPlanDetail(planId ? decodeURIComponent(planId) : undefined)
  const d = detail.data
  if (!planId) return null
  if (detail.isLoading) return <p className="p-8 text-center text-sm text-[var(--muted-foreground)]" role="status">Loading your installment plan…</p>
  if (detail.isError || !d) { const safe = sanitizePortalMaturityError(detail.error); return <div className="space-y-4 px-4 py-6"><Link to="/portal/maturity-installments" className="button-secondary inline-flex items-center gap-2"><ArrowLeft size={15} aria-hidden="true" />Back to my installments</Link><ErrorCoach title="Installment plan could not be loaded" message={safe.message} resolutionSteps={safe.steps} /></div> }
  const balance = (Number(d.totalAmount) - Number(d.paidAmount)).toFixed(2)
  return <div className="min-h-full space-y-5 px-4 py-5 sm:px-6 lg:px-8" data-testid="portal-mi-detail"><header className="surface-card px-5 py-4"><div className="flex flex-wrap items-start justify-between gap-4"><div><div className="mb-1 flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.16em] text-[var(--muted-foreground)]"><span>ZIC</span><span>/</span><span>Partner Portal</span><span>/</span><span>Maturity Installments</span></div><h1 className="break-all text-2xl font-semibold tracking-[-0.04em] text-[var(--foreground)]">{d.planNumber}</h1><p className="mt-1 text-sm text-[var(--muted-foreground)]">{d.policyNumber} · {frequencyLabel(d.frequency)}</p><div className="mt-3 flex flex-wrap items-center gap-2"><PlanStatusBadge status={d.status} statusDisplay={d.statusDisplay} /><span className="text-sm font-semibold"><MoneyCell value={balance} currency={d.currency} /> remaining</span></div></div><Link to="/portal/maturity-installments" className="button-secondary inline-flex items-center gap-2"><ArrowLeft size={15} aria-hidden="true" />Back</Link></div></header><PortalBanner /><section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4" data-testid="portal-mi-overview"><div className="surface-card p-4"><p className="text-xs text-[var(--muted-foreground)]">Total payout</p><p className="mt-1 text-lg font-bold"><MoneyCell value={d.totalAmount} currency={d.currency} /></p></div><div className="surface-card p-4"><p className="text-xs text-[var(--muted-foreground)]">Paid to date</p><p className="mt-1 text-lg font-bold"><MoneyCell value={d.paidAmount} currency={d.currency} variant="paid" /></p></div><div className="surface-card p-4"><p className="text-xs text-[var(--muted-foreground)]">Balance remaining</p><p className="mt-1 text-lg font-bold"><MoneyCell value={balance} currency={d.currency} /></p></div><div className="surface-card p-4"><p className="text-xs text-[var(--muted-foreground)]">Installments</p><p className="mt-1 text-sm font-semibold">{d.paidInstallments} paid of {d.installmentCount}</p></div></section>{d.items && d.items.length > 0 ? <section className="surface-card overflow-hidden" data-testid="portal-mi-schedule"><div className="border-b border-[var(--border)] bg-[var(--muted)]/35 px-5 py-3"><h2 className="text-sm font-bold">Payout schedule</h2><p className="text-xs text-[var(--muted-foreground)]">Schedule details are visible for planning; changes remain controlled by ZIC Finance.</p></div><div className="overflow-x-auto"><table className="w-full min-w-[640px] text-left text-sm"><caption className="sr-only">Your maturity installment payout schedule</caption><thead className="bg-[var(--muted)]/45 text-xs uppercase tracking-[0.08em] text-[var(--muted-foreground)]"><tr>{["Installment", "Due date", "Amount", "Status"].map((heading) => <th key={heading} scope="col" className="px-4 py-2.5 font-bold">{heading}</th>)}</tr></thead><tbody className="divide-y divide-[var(--border)]">{d.items.map((item) => <tr key={item.id}><td className="px-4 py-2.5 font-semibold">{item.installmentNumber}</td><td className="px-4 py-2.5">{dateLabel(item.dueDate)}</td><td className="px-4 py-2.5 tabular-nums"><MoneyCell value={item.amount} currency={d.currency} /></td><td className="px-4 py-2.5"><ItemStatusBadge status={item.status} statusDisplay={item.statusDisplay} /></td></tr>)}</tbody></table></div></section> : <section className="surface-card px-5 py-6 text-sm text-[var(--muted-foreground)]">No payout schedule is currently available in the partner portal.</section>}<InfoBanner title="Read-only partner view">View is available for your linked partner account. Process payment, reverse, and other servicing actions are not available here.</InfoBanner></div>
}

export default PartnerMaturityInstallments
