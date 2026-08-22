import { useState } from "react"
import { Eye, EyeOff, History } from "lucide-react"
import { StatusBadge, type StatusTone } from "../ui/StatusBadge"
import { ErrorCoach } from "./ErrorCoach"
import { useCommitmentImportDetail, useCommitmentImports } from "../../lib/commitmentsHooks"
import { dateLabel } from "../../lib/commitmentsDisplay"
import type { ImportHistoryRecord } from "../../lib/commitments"

function importStatusTone(status: string): StatusTone {
  const normalized = (status || "").toUpperCase()
  if (/COMPLETED/i.test(normalized)) return "success"
  if (/FAILED|REJECTED/i.test(normalized)) return "danger"
  if (/PARTIAL|WARNING/i.test(normalized)) return "warning"
  return "neutral"
}

function ImportErrorRows({ id }: { id: string }) {
  const detail = useCommitmentImportDetail(id)
  if (detail.isLoading) return <p className="px-3 py-2 text-xs text-[var(--muted-foreground)]">Loading errors…</p>
  if (detail.isError) return <ErrorCoach error={detail.error} compact />
  const errors = detail.data?.errors ?? []
  if (errors.length === 0) return <p className="px-3 py-2 text-xs text-[var(--muted-foreground)]">No row errors recorded for this import.</p>
  return (
    <ul className="space-y-1 px-3 py-2">
      {errors.map((error, index) => (
        <li key={`${error.row}-${index}`} className="flex items-start gap-2 text-xs">
          <span className="font-mono tabular-nums text-[var(--muted-foreground)]">Row {error.row}</span>
          <span className="text-[var(--foreground)]">
            {error.field_errors
              ? Object.entries(error.field_errors).map(([field, messages]) => `${field}: ${messages.join(", ")}`).join(" · ")
              : (error.message ?? "Row rejected.")}
          </span>
        </li>
      ))}
    </ul>
  )
}

export function CommitmentImportHistory() {
  const imports = useCommitmentImports()
  const [expanded, setExpanded] = useState<string | null>(null)
  const records = imports.data ?? []

  return (
    <section className="surface-card overflow-hidden" aria-label="Commitment import history">
      <div className="flex items-center justify-between gap-3 border-b bg-[var(--muted)]/35 px-4 py-3">
        <div>
          <p className="flex items-center gap-2 text-sm font-bold text-[var(--foreground)]"><History size={15} aria-hidden="true" />Import history</p>
          <p className="text-xs text-[var(--muted-foreground)]">{records.length} recorded import run(s)</p>
        </div>
      </div>
      {imports.isLoading && <p className="px-4 py-6 text-center text-sm text-[var(--muted-foreground)]">Loading import history…</p>}
      {imports.isError && <div className="p-4"><ErrorCoach error={imports.error} compact /></div>}
      {!imports.isLoading && !imports.isError && records.length === 0 && (
        <p className="px-4 py-6 text-center text-sm text-[var(--muted-foreground)]">
          No imports recorded yet. Use Import CSV to bulk-load commitments.
        </p>
      )}
      {records.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[680px] text-left text-sm">
            <thead className="bg-[var(--muted)]/45 text-xs uppercase tracking-[0.08em] text-[var(--muted-foreground)]">
              <tr>
                <th scope="col" className="px-4 py-2.5 font-bold">File</th>
                <th scope="col" className="px-4 py-2.5 font-bold">Uploaded by</th>
                <th scope="col" className="px-4 py-2.5 font-bold">Date</th>
                <th scope="col" className="px-4 py-2.5 text-right font-bold">OK</th>
                <th scope="col" className="px-4 py-2.5 text-right font-bold">Errors</th>
                <th scope="col" className="px-4 py-2.5 text-right font-bold">Created</th>
                <th scope="col" className="px-4 py-2.5 font-bold">Status</th>
                <th scope="col" className="px-4 py-2.5" />
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border)]">
              {records.map((record) => (
                <ImportHistoryRow
                  key={record.id}
                  record={record}
                  open={expanded === record.id}
                  onToggle={() => setExpanded((current) => (current === record.id ? null : record.id))}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}

function ImportHistoryRow({ record, open, onToggle }: { record: ImportHistoryRecord; open: boolean; onToggle: () => void }) {
  return (
    <>
      <tr className="transition hover:bg-[var(--muted)]/25">
        <td className="px-4 py-2.5 font-semibold text-[var(--foreground)]">{record.fileName}</td>
        <td className="px-4 py-2.5">{record.uploadedByName || "—"}</td>
        <td className="px-4 py-2.5">{dateLabel(record.createdAt)}</td>
        <td className="px-4 py-2.5 text-right tabular-nums">{record.okCount.toLocaleString()}</td>
        <td className="px-4 py-2.5 text-right tabular-nums text-[var(--destructive)]">{record.errorCount.toLocaleString()}</td>
        <td className="px-4 py-2.5 text-right tabular-nums">{record.createdCount.toLocaleString()}</td>
        <td className="px-4 py-2.5"><StatusBadge value={record.status} tone={importStatusTone(record.status)} /></td>
        <td className="px-4 py-2.5 text-right">
          <button
            type="button"
            className="inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-xs font-semibold text-[var(--primary)] outline-none transition hover:bg-[var(--secondary)] focus-visible:ring-2 focus-visible:ring-[var(--ring)]"
            onClick={onToggle}
            aria-expanded={open}
            data-testid={`import-errors-${record.id}`}
          >
            {open ? <EyeOff size={13} aria-hidden="true" /> : <Eye size={13} aria-hidden="true" />}
            {open ? "Hide errors" : "View errors"}
          </button>
        </td>
      </tr>
      {open && (
        <tr>
          <td colSpan={8} className="bg-[var(--muted)]/15 px-4 py-1">
            <ImportErrorRows id={record.id} />
          </td>
        </tr>
      )}
    </>
  )
}


export default CommitmentImportHistory