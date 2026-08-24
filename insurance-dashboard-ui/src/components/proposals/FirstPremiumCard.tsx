import { useNavigate } from "react-router-dom"
import { ArrowRight, Landmark } from "lucide-react"
import type { FirstPremiumStatusShape } from "../../lib/proposals"
import { StatusBadge } from "../ui/StatusBadge"
import { commitmentStatusLabel, commitmentStatusTone } from "../commitments/CommitmentStatusBadge"

function money(value: number | null | undefined, currency?: string): string {
  if (value === null || value === undefined) return "—"
  const formatted = value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  return currency ? `${currency} ${formatted}` : formatted
}

/**
 * First premium settlement card.
 *
 * Shows the linked commitment (number links to the commitments workspace),
 * its status badge, due/paid/balance figures, a compact allocation history,
 * and the backend's next-action hint so the operator always knows what to do
 * next on the road to policy conversion.
 */
export function FirstPremiumCard({
  status,
  className = "",
}: {
  status: FirstPremiumStatusShape | null | undefined
  className?: string
}) {
  const navigate = useNavigate()

  if (!status || !status.linked) {
    return (
      <div className={`surface-card px-4 py-3 ${className}`} data-first-premium-card="unlinked">
        <p className="flex items-center gap-2 text-[13px] font-semibold text-[var(--foreground)]">
          <Landmark size={15} aria-hidden="true" />
          First premium not generated yet
        </p>
        <ul className="mt-1 flex flex-col gap-0.5 text-xs leading-5 text-[var(--muted-foreground)]">
          {(status?.nextActions ?? ["Mark the proposal payment-ready to generate the first premium commitment."]).map(
            (hint) => (
              <li key={hint}>{hint}</li>
            ),
          )}
        </ul>
      </div>
    )
  }

  const openCommitment = () => {
    void navigate(status.commitmentId ? `/ordinary-life/commitments/${status.commitmentId}` : "/ordinary-life/commitments")
  }

  return (
    <div className={`surface-card flex flex-col gap-3 px-4 py-3 ${className}`} data-first-premium-card="linked" data-posted={status.posted ? "true" : "false"}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="flex items-center gap-2 text-[13px] font-semibold text-[var(--foreground)]">
          <Landmark size={15} aria-hidden="true" />
          First premium
        </p>
        {status.commitmentStatus && (
          <StatusBadge value={commitmentStatusLabel(status.commitmentStatus)} tone={commitmentStatusTone(status.commitmentStatus)} />
        )}
      </div>

      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[13px]">
        <button
          type="button"
          onClick={openCommitment}
          className="font-mono text-xs font-bold underline-offset-2 hover:underline"
          data-testid="first-premium-commitment-link"
        >
          {status.commitmentNumber ?? "Commitment"}
        </button>
        <span className="text-[var(--muted-foreground)]">
          Due <strong className="text-[var(--foreground)]">{money(status.amountDue, status.currency)}</strong>
        </span>
        <span className="text-[var(--muted-foreground)]">
          Paid <strong className="text-[var(--foreground)]">{money(status.amountPaid, status.currency)}</strong>
        </span>
        <span className="text-[var(--muted-foreground)]">
          Balance{" "}
          <strong className={status.balance && status.balance > 0 ? "text-[var(--warning)]" : "text-[var(--success)]"}>
            {money(status.balance, status.currency)}
          </strong>
        </span>
      </div>

      {status.allocations.length > 0 && (
        <table className="w-full text-left text-xs" data-testid="first-premium-allocations">
          <thead>
            <tr className="text-[11px] uppercase tracking-wide text-[var(--muted-foreground)]">
              <th className="py-1 pr-2 font-semibold">Receipt</th>
              <th className="py-1 pr-2 font-semibold">Amount</th>
              <th className="py-1 font-semibold">Date</th>
            </tr>
          </thead>
          <tbody>
            {status.allocations.map((row) => (
              <tr key={`${row.receiptReference}-${row.allocatedAt ?? ""}`} className="border-t border-[var(--border)]">
                <td className="py-1 pr-2 font-mono">{row.receiptReference}</td>
                <td className="py-1 pr-2">{money(row.amount, row.currency)}</td>
                <td className="py-1">{row.allocatedAt?.slice(0, 10) ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {!status.posted && (
        <div>
          <button
            type="button"
            data-testid="record-receipt-hint"
            title="The Front Office receipts workspace ships in a later release — for now this opens the commitment detail where allocations are listed."
            onClick={openCommitment}
            className="button-secondary inline-flex h-8 items-center gap-1.5 px-2.5 text-xs font-semibold"
          >
            <ArrowRight size={13} aria-hidden="true" />
            Record receipt in Front Office
          </button>
        </div>
      )}

      <div className="flex items-start gap-2 border-t border-[var(--border)] pt-2 text-xs leading-5 text-[var(--muted-foreground)]">
        <ArrowRight size={13} aria-hidden="true" className="mt-0.5 flex-none" />
        <span data-testid="first-premium-next-action">
          {(status.nextActions.length ? status.nextActions : ["Awaiting first premium allocation."]).join(" ")}
        </span>
      </div>
    </div>
  )
}

export default FirstPremiumCard
