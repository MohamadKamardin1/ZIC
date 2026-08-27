import { useMemo, useState } from "react"
import { ArrowLeft, Eye, LifeBuoy, Search, ShieldCheck } from "lucide-react"
import { Link, useNavigate, useParams } from "react-router-dom"
import { ErrorCoach } from "../../components/ErrorCoach"
import Modal from "../../components/shared/Modal"
import { MoneyCell, WithdrawalStatusBadge } from "../../components/withdrawals/WithdrawalPrimitives"
import { useToast } from "../../components/ui/Toast"
import { dateLabel } from "../../lib/commitmentsDisplay"
import { usePortalWithdrawal, usePortalWithdrawalRequestMutation, usePortalWithdrawals } from "../../lib/withdrawalsHooks"
import type { PortalWithdrawal } from "../../lib/withdrawals"

export const PORTAL_WITHDRAWAL_HELP_MESSAGE = "For changes to withdrawal terms, contact ZIC Finance."

function PortalBanner() {
  return <div className="rounded-[10px] border border-[var(--info)]/25 bg-[var(--info)]/8 px-4 py-3 text-sm text-[var(--foreground)]"><div className="flex flex-wrap items-start gap-2"><ShieldCheck size={17} className="mt-0.5 shrink-0 text-[var(--info)]" aria-hidden="true" /><span>{PORTAL_WITHDRAWAL_HELP_MESSAGE}</span><Link to="/tickets" className="inline-flex items-center gap-1 font-semibold text-[var(--primary)] underline-offset-2 hover:underline"><LifeBuoy size={14} aria-hidden="true" />Raise Ticket</Link></div></div>
}

function sanitizeError(error: unknown): { message: string; steps: string[] } {
  return { message: error instanceof Error && error.message ? error.message : "Your partner-scoped withdrawal information could not be loaded.", steps: ["Retry the request in a moment.", "Confirm the withdrawal belongs to one of your linked policies.", "Contact ZIC Finance if the issue continues."] }
}

function PortalRequestModal({ withdrawal, open, onClose, onSuccess }: { withdrawal: PortalWithdrawal | null; open: boolean; onClose: () => void; onSuccess: (id: string) => void }) {
  const { toast } = useToast()
  const mutation = usePortalWithdrawalRequestMutation()
  const [amount, setAmount] = useState("")
  const [reason, setReason] = useState("")
  const [errors, setErrors] = useState<Record<string, string>>({})
  if (!withdrawal) return null

  const close = () => {
    if (mutation.isPending) return
    setAmount("")
    setReason("")
    setErrors({})
    onClose()
  }

  const submit = () => {
    const next: Record<string, string> = {}
    const numericAmount = Number(amount)
    if (!amount || !Number.isFinite(numericAmount) || numericAmount <= 0) next.amount = "Enter a requested amount greater than zero."
    if (!reason.trim()) next.reason = "Explain why the withdrawal is being requested."
    setErrors(next)
    if (Object.keys(next).length) return
    mutation.mutate({ policyId: withdrawal.policyId, amount: numericAmount.toFixed(2), reason: reason.trim() }, {
      onSuccess: (result) => {
        const id = result.withdrawal?.id || ""
        toast({ tone: "success", title: "Withdrawal request submitted", message: "Your request is pending ZIC Finance review." })
        close()
        onSuccess(id)
      },
    })
  }

  return <Modal open={open} title="Request Withdrawal" onClose={close}><div className="space-y-4"><div className="rounded-lg border bg-[var(--muted)]/30 p-4"><p className="text-xs font-bold uppercase tracking-[0.1em] text-[var(--muted-foreground)]">Policy</p><p className="mt-1 text-sm font-bold">{withdrawal.policyNumber}</p><p className="mt-1 text-xs text-[var(--muted-foreground)]">{withdrawal.productDisplay || "Ordinary Life policy"}</p></div><div className="rounded-lg border border-[var(--info)]/25 bg-[var(--info)]/8 px-3 py-3 text-sm">This portal form submits a request only. Approval, payout processing, reversal, and withdrawal-term changes remain staff-controlled.</div><label className="block space-y-1.5"><span className="text-xs font-bold">Requested Amount <span className="text-[var(--destructive)]">*</span></span><input value={amount} onChange={(event) => { setAmount(event.target.value); setErrors((current) => ({ ...current, amount: "" })) }} inputMode="decimal" aria-invalid={Boolean(errors.amount)} placeholder="Enter amount" className="h-11 w-full rounded-[10px] border bg-[var(--card)] px-3 text-sm outline-none focus:border-[var(--ring)] focus:ring-2 focus:ring-[color-mix(in_srgb,var(--ring)_18%,transparent)]" />{errors.amount && <span className="text-xs font-semibold text-[var(--destructive)]">{errors.amount}</span>}</label><label className="block space-y-1.5"><span className="text-xs font-bold">Reason <span className="text-[var(--destructive)]">*</span></span><textarea value={reason} onChange={(event) => { setReason(event.target.value); setErrors((current) => ({ ...current, reason: "" })) }} rows={4} aria-invalid={Boolean(errors.reason)} placeholder="Explain the withdrawal request" className="w-full rounded-[10px] border bg-[var(--card)] px-3 py-2 text-sm outline-none focus:border-[var(--ring)] focus:ring-2 focus:ring-[color-mix(in_srgb,var(--ring)_18%,transparent)]" />{errors.reason && <span className="text-xs font-semibold text-[var(--destructive)]">{errors.reason}</span>}</label>{mutation.error && <ErrorCoach title="Withdrawal request could not be submitted" message={mutation.error.message} resolutionSteps={["Review the amount and reason.", "Confirm the policy remains eligible.", "Retry or contact ZIC Finance."]} />}<div className="flex justify-end gap-2 border-t pt-4"><button type="button" className="button-secondary" onClick={close} disabled={mutation.isPending}>Cancel</button><button type="button" className="button-primary" onClick={submit} disabled={mutation.isPending}>{mutation.isPending ? "Submitting…" : "Submit Request"}</button></div></div></Modal>
}

function PortalWithdrawalRow({ withdrawal, onRequest }: { withdrawal: PortalWithdrawal; onRequest: (withdrawal: PortalWithdrawal) => void }) {
  const navigate = useNavigate()
  return <tr className="transition hover:bg-[var(--muted)]/25" data-testid={`portal-withdrawal-row-${withdrawal.requestNumber}`}><td className="px-4 py-3 font-semibold">{withdrawal.requestNumber || "—"}</td><td className="px-4 py-3">{withdrawal.policyNumber || "—"}</td><td className="px-4 py-3">{withdrawal.productDisplay || "—"}</td><td className="px-4 py-3"><WithdrawalStatusBadge status={withdrawal.status} statusDisplay={withdrawal.statusDisplay} /></td><td className="px-4 py-3 text-right"><MoneyCell value={withdrawal.grossAmount} currency={withdrawal.currency} /></td><td className="px-4 py-3 text-right"><MoneyCell value={withdrawal.netPayout} currency={withdrawal.currency} /></td><td className="px-4 py-3">{dateLabel(withdrawal.requestedAt)}</td><td className="px-4 py-3"><div className="flex flex-wrap gap-2"><button type="button" className="button-secondary inline-flex items-center gap-1.5 !min-h-9 !px-3 text-xs" onClick={() => navigate(`/portal/withdrawals/${encodeURIComponent(withdrawal.id)}`)}><Eye size={14} aria-hidden="true" />View</button>{withdrawal.requestAllowed && <button type="button" className="button-primary !min-h-9 !px-3 text-xs" onClick={() => onRequest(withdrawal)}>Request Withdrawal</button>}</div></td></tr>
}

export function PartnerWithdrawals() {
  const navigate = useNavigate()
  const [search, setSearch] = useState("")
  const [status, setStatus] = useState("")
  const [requestWithdrawal, setRequestWithdrawal] = useState<PortalWithdrawal | null>(null)
  const params = useMemo(() => ({ q: search || undefined, status: status || undefined, page: 1, pageSize: 20 }), [search, status])
  const list = usePortalWithdrawals(params)
  const rows = list.data?.results ?? []
  const safe = sanitizeError(list.error)
  return <div className="min-h-full px-4 py-5 sm:px-6 lg:px-8" data-testid="portal-withdrawals"><div className="mx-auto max-w-[1560px] space-y-5"><header className="flex flex-wrap items-end justify-between gap-4 border-b border-[var(--border)] pb-5"><div><div className="mb-2 flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.16em] text-[var(--muted-foreground)]"><span>ZIC</span><span>/</span><span>Partner Portal</span><span>/</span><span>Withdrawals</span></div><h1 className="text-2xl font-semibold tracking-[-0.04em]">My Withdrawals</h1><p className="mt-1 text-sm text-[var(--muted-foreground)]">View withdrawals associated with your linked policies. Financial servicing actions remain with ZIC Finance.</p></div><span className="inline-flex items-center gap-2 rounded-lg border border-[var(--border)] px-3 py-2 text-xs font-semibold"><ShieldCheck size={15} className="text-[var(--success)]" aria-hidden="true" />Partner-scoped</span></header><PortalBanner /><section className="surface-card p-4"><div className="flex flex-col gap-3 md:flex-row md:items-end"><label className="block flex-1 space-y-1.5"><span className="text-xs font-bold uppercase tracking-[0.1em] text-[var(--muted-foreground)]">Search withdrawals</span><span className="relative block"><Search size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[var(--muted-foreground)]" aria-hidden="true" /><input value={search} onChange={(event) => setSearch(event.target.value)} aria-label="Search withdrawals" placeholder="Withdrawal or policy number" className="h-10 w-full rounded-[10px] border bg-[var(--card)] pl-9 pr-3 text-sm outline-none focus:border-[var(--ring)] focus:ring-2 focus:ring-[color-mix(in_srgb,var(--ring)_18%,transparent)]" /></span></label><label className="block space-y-1.5 md:w-56"><span className="text-xs font-bold uppercase tracking-[0.1em] text-[var(--muted-foreground)]">Status</span><select value={status} onChange={(event) => setStatus(event.target.value)} aria-label="Status" className="h-10 w-full rounded-[10px] border bg-[var(--card)] px-3 text-sm outline-none focus:border-[var(--ring)] focus:ring-2 focus:ring-[color-mix(in_srgb,var(--ring)_18%,transparent)]"><option value="">All statuses</option><option value="REQUESTED">Requested</option><option value="APPROVED">Approved</option><option value="PAID">Paid</option><option value="DECLINED">Declined</option><option value="CANCELLED">Cancelled</option></select></label></div></section>{list.isLoading && <p className="py-10 text-center text-sm text-[var(--muted-foreground)]" role="status">Loading your withdrawals…</p>}{list.isError && <ErrorCoach title="Withdrawals could not be loaded" message={safe.message} resolutionSteps={safe.steps} />}{!list.isLoading && !list.isError && rows.length === 0 && <p className="py-10 text-center text-sm text-[var(--muted-foreground)]">You have no withdrawals associated with your linked policies.</p>}{rows.length > 0 && <section className="surface-card overflow-hidden" data-testid="portal-withdrawals-table"><div className="overflow-x-auto"><table className="w-full min-w-[1000px] text-left text-sm"><caption className="sr-only">Your partner-scoped withdrawals</caption><thead className="bg-[var(--muted)]/45 text-xs uppercase tracking-[0.08em] text-[var(--muted-foreground)]"><tr>{["Withdrawal", "Policy", "Product", "Status", "Gross amount", "Net payout", "Requested", "Actions"].map((heading) => <th key={heading} scope="col" className="px-4 py-2.5 font-bold">{heading}</th>)}</tr></thead><tbody className="divide-y divide-[var(--border)]">{rows.map((withdrawal) => <PortalWithdrawalRow key={withdrawal.id} withdrawal={withdrawal} onRequest={setRequestWithdrawal} />)}</tbody></table></div></section>}</div><PortalRequestModal withdrawal={requestWithdrawal} open={Boolean(requestWithdrawal)} onClose={() => setRequestWithdrawal(null)} onSuccess={(id) => { if (id) navigate(`/portal/withdrawals/${encodeURIComponent(id)}`) }} /></div>
}

export function PartnerWithdrawalDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const detail = usePortalWithdrawal(id ? decodeURIComponent(id) : undefined)
  const [requestOpen, setRequestOpen] = useState(false)
  if (!id) return null
  if (detail.isLoading) return <p className="p-8 text-center text-sm text-[var(--muted-foreground)]" role="status">Loading your withdrawal…</p>
  if (detail.isError || !detail.data) { const safe = sanitizeError(detail.error); return <div className="space-y-4 px-4 py-6"><Link to="/portal/withdrawals" className="button-secondary inline-flex items-center gap-2"><ArrowLeft size={15} aria-hidden="true" />Back to my withdrawals</Link><ErrorCoach title="Withdrawal could not be loaded" message={safe.message} resolutionSteps={safe.steps} /></div> }
  const withdrawal = detail.data
  const showSensitive = withdrawal.feeAmount !== undefined || withdrawal.cashValueBefore !== undefined
  return <div className="min-h-full space-y-5 px-4 py-5 sm:px-6 lg:px-8" data-testid="portal-withdrawal-detail"><div className="mx-auto max-w-[1200px] space-y-5"><header className="surface-card px-5 py-4"><div className="flex flex-wrap items-start justify-between gap-4"><div><div className="mb-1 flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.16em] text-[var(--muted-foreground)]"><span>ZIC</span><span>/</span><span>Partner Portal</span><span>/</span><span>{withdrawal.requestNumber}</span></div><h1 className="text-2xl font-semibold">{withdrawal.requestNumber}</h1><p className="mt-1 text-sm text-[var(--muted-foreground)]">{withdrawal.policyNumber} · {withdrawal.productDisplay || "Ordinary Life withdrawal"}</p><div className="mt-3"><WithdrawalStatusBadge status={withdrawal.status} statusDisplay={withdrawal.statusDisplay} /></div></div><Link to="/portal/withdrawals" className="button-secondary inline-flex items-center gap-2"><ArrowLeft size={15} aria-hidden="true" />Back</Link></div></header><PortalBanner /><section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4"><div className="surface-card p-4"><p className="text-xs text-[var(--muted-foreground)]">Policyholder</p><p className="mt-1 text-sm font-semibold">{withdrawal.policyholderDisplay || "—"}</p></div><div className="surface-card p-4"><p className="text-xs text-[var(--muted-foreground)]">Gross amount</p><p className="mt-1 text-lg font-bold"><MoneyCell value={withdrawal.grossAmount} currency={withdrawal.currency} /></p></div><div className="surface-card p-4"><p className="text-xs text-[var(--muted-foreground)]">Net payout</p><p className="mt-1 text-lg font-bold"><MoneyCell value={withdrawal.netPayout} currency={withdrawal.currency} /></p></div><div className="surface-card p-4"><p className="text-xs text-[var(--muted-foreground)]">Requested</p><p className="mt-1 text-sm font-semibold">{dateLabel(withdrawal.requestedAt)}</p></div></section><section className="surface-card p-5"><div className="flex flex-wrap items-start justify-between gap-3"><div><h2 className="text-base font-bold">Withdrawal overview</h2><p className="mt-1 text-xs text-[var(--muted-foreground)]">This portal response is limited to partner-safe servicing information.</p></div>{withdrawal.requestAllowed && <button type="button" className="button-primary" onClick={() => setRequestOpen(true)}>Request Withdrawal</button>}</div><dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-3"><div><dt className="text-xs text-[var(--muted-foreground)]">Reason</dt><dd className="mt-1 font-semibold">{withdrawal.reason || "—"}</dd></div><div><dt className="text-xs text-[var(--muted-foreground)]">Currency</dt><dd className="mt-1 font-semibold">{withdrawal.currency}</dd></div><div><dt className="text-xs text-[var(--muted-foreground)]">Fee</dt><dd className="mt-1 font-semibold">{showSensitive && withdrawal.feeAmount !== undefined ? <MoneyCell value={withdrawal.feeAmount} currency={withdrawal.currency} /> : "Not disclosed by partner permissions"}</dd></div>{showSensitive && <><div><dt className="text-xs text-[var(--muted-foreground)]">Cash Value Before</dt><dd className="mt-1 font-semibold"><MoneyCell value={withdrawal.cashValueBefore} currency={withdrawal.currency} /></dd></div><div><dt className="text-xs text-[var(--muted-foreground)]">Loan Balance Before</dt><dd className="mt-1 font-semibold"><MoneyCell value={withdrawal.loanBalanceBefore} currency={withdrawal.currency} /></dd></div><div><dt className="text-xs text-[var(--muted-foreground)]">Cash Value After</dt><dd className="mt-1 font-semibold"><MoneyCell value={withdrawal.cashValueAfter} currency={withdrawal.currency} /></dd></div></>}</dl></section><div className="rounded-[10px] border border-[var(--info)]/25 bg-[var(--info)]/8 px-4 py-3 text-sm"><strong>Read-only portal:</strong> Approve, Process Payout, Reverse, and withdrawal-term management actions are not available here.</div></div><PortalRequestModal withdrawal={withdrawal} open={requestOpen} onClose={() => setRequestOpen(false)} onSuccess={(nextId) => { if (nextId) navigate(`/portal/withdrawals/${encodeURIComponent(nextId)}`) }} /></div>
}

export default PartnerWithdrawals
