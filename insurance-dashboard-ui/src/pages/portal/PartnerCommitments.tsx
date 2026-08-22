import { Link, useNavigate, useParams } from "react-router-dom"
import { HelpCircle, LifeBuoy } from "lucide-react"
import { InfoBanner } from "../../components/ui/Overlays"
import { ErrorCoach } from "../../components/commitments/ErrorCoach"
import { CommitmentStatusBadge } from "../../components/commitments/CommitmentStatusBadge"
import { DueDateWarning } from "../../components/commitments/DueDateWarning"
import { usePortalCommitment, usePortalCommitments } from "../../lib/commitmentsHooks"
import { formatMoney, dateLabel, sourceLabel } from "../../lib/commitmentsDisplay"

export const PORTAL_HELP_MESSAGE = "To make a payment or dispute a commitment, contact your ZIC representative or raise a ticket."

export function sanitizePortalError(error: unknown) {
  return {
    error_code: "PORTAL_UNAVAILABLE",
    message: "The request could not be completed. Please try again or contact your ZIC representative.",
    resolution_steps: ["Try again in a few moments.", "Contact your ZIC representative if the issue continues."],
  }
}

function PortalBanner() {
  return (
    <InfoBanner title="Read-only view">
      <p className="flex items-start gap-2 text-sm">
        <HelpCircle size={16} className="mt-0.5 shrink-0" aria-hidden="true" />
        {PORTAL_HELP_MESSAGE}
        <Link to="/tickets" className="inline-flex items-center gap-1 font-semibold text-[var(--primary)] underline-offset-2 hover:underline" data-testid="raise-ticket">
          <LifeBuoy size={14} aria-hidden="true" />
          Raise Ticket
        </Link>
      </p>
    </InfoBanner>
  )
}

export function PartnerCommitments() {
  const navigate = useNavigate()
  const list = usePortalCommitments({ pageSize: 50 })
  const rows = list.data?.results ?? []

  return (
    <div className="min-h-full px-4 py-5 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-[1560px] space-y-5">
        <header className="flex flex-wrap items-end justify-between gap-4 border-b border-[var(--border)] pb-5">
          <div>
            <div className="mb-2 flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.16em] text-[var(--muted-foreground)]">
              <span>ZIC</span><span>/</span><span>Partner Portal</span><span>/</span><span>Commitments</span>
            </div>
            <h1 className="text-2xl font-semibold tracking-[-0.04em] text-[var(--foreground)]">My Commitments</h1>
            <p className="mt-1 text-sm text-[var(--muted-foreground)]">Your Ordinary Life premium obligations, scoped to your linked partner account.</p>
          </div>
          <Link to="/tickets" className="inline-flex items-center gap-2 text-sm font-semibold text-[var(--primary)] underline-offset-2 hover:underline">
            <LifeBuoy size={15} aria-hidden="true" />
            Raise Ticket
          </Link>
        </header>

        <PortalBanner />

        {list.isLoading && <p className="py-10 text-center text-sm text-[var(--muted-foreground)]">Loading your commitments…</p>}
        {list.isError && <ErrorCoach error={sanitizePortalError(list.error)} title="Commitments could not be loaded" />}
        {!list.isLoading && !list.isError && rows.length === 0 && (
          <p className="py-10 text-center text-sm text-[var(--muted-foreground)]">You have no commitments at this time.</p>
        )}

        {rows.length > 0 && (
          <section className="surface-card overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[820px] text-left text-sm">
                <caption className="sr-only">Your commitments</caption>
                <thead className="bg-[var(--muted)]/45 text-xs uppercase tracking-[0.08em] text-[var(--muted-foreground)]">
                  <tr>{["Commitment", "Source", "Product / Plan", "Due date", "Amount", "Paid", "Balance", "Status", "Grace / lapse"].map((heading) => <th key={heading} scope="col" className="px-4 py-2.5 font-bold">{heading}</th>)}</tr>
                </thead>
                <tbody className="divide-y divide-[var(--border)]">
                  {rows.map((row) => (
                    <tr key={row.id} className="cursor-pointer transition hover:bg-[var(--muted)]/25" onClick={() => navigate(`/portal/commitments/${row.id}`)}>
                      <td className="px-4 py-2.5 font-semibold text-[var(--foreground)]">{row.commitmentNumber || "—"}</td>
                      <td className="px-4 py-2.5">{sourceLabel(row.sourceType)}{row.sourceReference && <span className="ml-1 text-xs text-[var(--muted-foreground)]">{row.sourceReference}</span>}</td>
                      <td className="px-4 py-2.5">{row.productName || row.planName || "—"}</td>
                      <td className="px-4 py-2.5">{dateLabel(row.dueDate)}</td>
                      <td className="px-4 py-2.5 tabular-nums">{formatMoney(row.premiumAmount, row.currency)}</td>
                      <td className="px-4 py-2.5 tabular-nums">{formatMoney(row.amountPaid, row.currency)}</td>
                      <td className="px-4 py-2.5 tabular-nums font-semibold text-[var(--foreground)]">{formatMoney(row.balance, row.currency)}</td>
                      <td className="px-4 py-2.5"><CommitmentStatusBadge value={row.status} /></td>
                      <td className="px-4 py-2.5"><DueDateWarning dueDate={row.dueDate} graceDate={row.graceDate} lapseDate={row.lapseDate} showDetail={false} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}
      </div>
    </div>
  )
}

export function PartnerCommitmentDetail() {
  const { id } = useParams()
  const detail = usePortalCommitment(id)

  if (!id) return null
  if (detail.isLoading) return <p className="p-8 text-center text-sm text-[var(--muted-foreground)]">Loading commitment…</p>
  if (detail.isError || !detail.data) {
    return (
      <div className="px-4 py-6">
        <Link to="/portal/commitments" className="button-secondary">← Back to my commitments</Link>
        <div className="mt-4"><ErrorCoach error={sanitizePortalError(detail.error)} title="Commitment could not be loaded" /></div>
      </div>
    )
  }

  const d = detail.data

  return (
    <div className="min-h-full space-y-5 px-4 py-5 sm:px-6 lg:px-8">
      <header className="surface-card px-5 py-4">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="mb-1 flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.16em] text-[var(--muted-foreground)]">
              <span>ZIC</span><span>/</span><span>Partner Portal</span><span>/</span><span>{d.commitmentNumber}</span>
            </div>
            <h1 className="text-2xl font-semibold tracking-[-0.04em] text-[var(--foreground)]">{d.commitmentNumber}</h1>
            <p className="mt-1 text-sm text-[var(--muted-foreground)]">{d.productName && d.planName ? `${d.productName} / ${d.planName}` : (d.productName || d.planName || "")}</p>
            <div className="mt-3 flex flex-wrap items-center gap-2"><CommitmentStatusBadge value={d.status} /><span className="text-sm font-semibold text-[var(--foreground)]">{formatMoney(d.balance, d.currency)}</span><DueDateWarning dueDate={d.dueDate} graceDate={d.graceDate} lapseDate={d.lapseDate} /></div>
          </div>
          <Link to="/portal/commitments" className="button-secondary">← Back</Link>
        </div>
      </header>

      <PortalBanner />

      <div className="grid gap-4 lg:grid-cols-2">
        <section className="surface-card px-5 py-4">
          <h3 className="text-[10px] font-bold uppercase tracking-[0.12em] text-[var(--muted-foreground)]">Overview</h3>
          <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
            <div><dt className="text-xs text-[var(--muted-foreground)]">Source</dt><dd className="text-[var(--foreground)]">{sourceLabel(d.sourceType)}</dd></div>
            <div><dt className="text-xs text-[var(--muted-foreground)]">Reference</dt><dd className="text-[var(--foreground)]">{d.sourceReference || "—"}</dd></div>
            <div><dt className="text-xs text-[var(--muted-foreground)]">Due date</dt><dd className="text-[var(--foreground)]">{dateLabel(d.dueDate)}</dd></div>
            <div><dt className="text-xs text-[var(--muted-foreground)]">Installment</dt><dd className="tabular-nums text-[var(--foreground)]">{[String(d.installmentNumber), String(d.installmentCount)].filter(Boolean).join(" of ") || "—"}</dd></div>
            <div><dt className="text-xs text-[var(--muted-foreground)]">Amount</dt><dd className="tabular-nums text-[var(--foreground)]">{formatMoney(d.premiumAmount, d.currency)}</dd></div>
            <div><dt className="text-xs text-[var(--muted-foreground)]">Paid</dt><dd className="tabular-nums text-[var(--foreground)]">{formatMoney(d.amountPaid, d.currency)}</dd></div>
            <div><dt className="text-xs text-[var(--muted-foreground)]">Balance</dt><dd className="tabular-nums font-semibold text-[var(--foreground)]">{formatMoney(d.balance, d.currency)}</dd></div>
            <div><dt className="text-xs text-[var(--muted-foreground)]">Currency</dt><dd className="text-[var(--foreground)]">{d.currency}</dd></div>
          </dl>
        </section>

        <section className="surface-card overflow-hidden">
          <div className="border-b bg-[var(--muted)]/35 px-5 py-3"><h3 className="text-sm font-bold text-[var(--foreground)]">Payments</h3><p className="text-xs text-[var(--muted-foreground)]">{d.allocations.length} allocation(s)</p></div>
          {d.allocations.length === 0 ? (
            <p className="px-5 py-6 text-center text-sm text-[var(--muted-foreground)]">No payments recorded yet.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[560px] text-left text-sm">
                <thead className="bg-[var(--muted)]/45 text-xs uppercase tracking-[0.08em] text-[var(--muted-foreground)]">
                  <tr>{["Payment mode", "Amount", "Currency", "Receipt", "Date"].map((heading) => <th key={heading} scope="col" className="px-4 py-2.5 font-bold">{heading}</th>)}</tr>
                </thead>
                <tbody className="divide-y divide-[var(--border)]">
                  {d.allocations.map((allocation) => (
                    <tr key={allocation.id}>
                      <td className="px-4 py-2.5">{allocation.paymentMode || "—"}</td>
                      <td className="px-4 py-2.5 tabular-nums">{formatMoney(allocation.amount, allocation.currency)}</td>
                      <td className="px-4 py-2.5">{allocation.currency}</td>
                      <td className="px-4 py-2.5 font-mono text-xs">{allocation.receiptReference || "—"}</td>
                      <td className="px-4 py-2.5 text-xs">{dateLabel(allocation.allocatedAt)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>
    </div>
  )
}

export default PartnerCommitments