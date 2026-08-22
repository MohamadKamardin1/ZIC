import { AlertTriangle } from "lucide-react"
import { ErrorCoach } from "./ErrorCoach"
import { StatusBadge } from "../ui/StatusBadge"
import { useLapseReviewQueue } from "../../lib/commitmentsHooks"
import { dateLabel } from "../../lib/commitmentsDisplay"

export function LapseReviewQueue() {
  const queue = useLapseReviewQueue()
  const rows = queue.data ?? []

  return (
    <section className="surface-card overflow-hidden" aria-label="Lapse review queue">
      <div className="flex items-center justify-between gap-3 border-b bg-[var(--muted)]/35 px-4 py-3">
        <div>
          <p className="flex items-center gap-2 text-sm font-bold text-[var(--foreground)]"><AlertTriangle size={15} aria-hidden="true" />Lapse review queue</p>
          <p className="text-xs text-[var(--muted-foreground)]">{rows.length} commitment(s) past lapse date flagged for policy review</p>
        </div>
      </div>
      {queue.isLoading && <p className="px-4 py-6 text-center text-sm text-[var(--muted-foreground)]">Loading lapse review queue…</p>}
      {queue.isError && <div className="p-4"><ErrorCoach error={queue.error} compact /></div>}
      {!queue.isLoading && !queue.isError && rows.length === 0 && (
        <p className="px-4 py-6 text-center text-sm text-[var(--muted-foreground)]">No commitments past their lapse date need review right now.</p>
      )}
      {rows.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead className="bg-[var(--muted)]/45 text-xs uppercase tracking-[0.08em] text-[var(--muted-foreground)]">
              <tr>{["Commitment", "Policy reference", "Partner", "Due date", "Lapse date", "Status", "Recommended action"].map((heading) => <th key={heading} scope="col" className="px-4 py-2.5 font-bold">{heading}</th>)}</tr>
            </thead>
            <tbody className="divide-y divide-[var(--border)]">
              {rows.map((row) => (
                <tr key={row.id} className="hover:bg-[var(--muted)]/25">
                  <td className="px-4 py-2.5 font-semibold text-[var(--foreground)]">{row.commitmentNumber || "—"}</td>
                  <td className="px-4 py-2.5 font-mono text-xs">{row.policyReference || row.sourceReference || "—"}</td>
                  <td className="px-4 py-2.5">{row.partnerName || "—"}</td>
                  <td className="px-4 py-2.5">{dateLabel(row.dueDate)}</td>
                  <td className="px-4 py-2.5">{dateLabel(row.lapseDate)}</td>
                  <td className="px-4 py-2.5"><StatusBadge value={row.status || "—"} tone="danger" /></td>
                  <td className="px-4 py-2.5 text-xs text-[var(--muted-foreground)]">{row.recommendedAction || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}

export default LapseReviewQueue