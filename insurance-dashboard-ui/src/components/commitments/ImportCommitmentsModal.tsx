import { useMemo, useRef, useState } from "react"
import { Download, FileUp, Upload, RefreshCw } from "lucide-react"
import { Modal, InfoBanner } from "../../components/ui/Overlays"
import { ErrorCoach } from "./ErrorCoach"
import { StatusBadge } from "../ui/StatusBadge"
import { useQueryClient } from "@tanstack/react-query"
import { useToast } from "../ui/Toast"
import {
  COMMITMENT_IMPORT_TEMPLATE_COLUMNS,
  commitmentImportTemplate,
  importCommitmentRows,
  type ImportRowError,
} from "../../lib/commitments"
import { parseCsv } from "../../lib/csv"
import { notifyCommitmentSuccess } from "../../lib/commitmentsNotify"

export interface ImportCommitmentsModalProps {
  open: boolean
  onClose: () => void
  onComplete: () => void
}

function downloadTemplate() {
  const csv = commitmentImportTemplate()
  const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }))
  const link = document.createElement("a")
  link.href = url
  link.download = "zic-commitments-import-template.csv"
  link.click()
  URL.revokeObjectURL(url)
}

function fieldMessages(error: ImportRowError): Array<{ field: string; messages: string[] }> {
  if (error.field_errors && Object.keys(error.field_errors).length > 0) {
    return Object.entries(error.field_errors).map(([field, messages]) => ({ field, messages }))
  }
  return [{ field: "row", messages: [error.message ?? "Row could not be imported."] }]
}

export function ImportCommitmentsModal({ open, onClose, onComplete }: ImportCommitmentsModalProps) {
  const { toast } = useToast()
  const queryClient = useQueryClient()

  const fileRef = useRef<HTMLInputElement>(null)
  const [fileName, setFileName] = useState("")
  const [rows, setRows] = useState<Array<Record<string, string>>>([])
  const [dryRunning, setDryRunning] = useState(false)
  const [dryRunResult, setDryRunResult] = useState<{ ok: number; errors: ImportRowError[] } | null>(null)
  const [committing, setCommitting] = useState(false)
  const [commitError, setCommitError] = useState<unknown>(null)

  const reset = () => {
    setFileName("")
    setRows([])
    setDryRunResult(null)
    setCommitError(null)
    if (fileRef.current) fileRef.current.value = ""
  }

  const onFileChange = (file: File | undefined) => {
    setCommitError(null)
    setDryRunResult(null)
    if (!file) return
    setFileName(file.name)
    void file.text().then((text) => {
      const parsed = parseCsv(text)
      setRows(parsed)
      if (parsed.length === 0) setCommitError({ message: "The CSV must contain a header row and at least one data row." })
    }).catch((reason) => setCommitError(reason))
  }

  const runDryRun = async () => {
    if (rows.length === 0) return
    setDryRunning(true)
    setCommitError(null)
    try {
      const result = await importCommitmentRows({ rows }, { dryRun: true })
      setDryRunResult({ ok: result.imported, errors: result.errors ?? [] })
    } catch (error) {
      setCommitError(error)
    } finally {
      setDryRunning(false)
    }
  }

  const runCommit = async () => {
    if (!dryRunResult || dryRunResult.errors.length > 0) return
    setCommitting(true)
    setCommitError(null)
    try {
      const result = await importCommitmentRows({ rows }, { dryRun: false })
      if (result.created > 0 || result.imported > 0) {
        notifyCommitmentSuccess(
          toast,
          "Commitments imported",
          `${result.created ?? result.imported} commitment(s) created. Open the register to review.`,
        )
        void queryClient.invalidateQueries({ queryKey: ["commitments", "imports"] })
        onComplete()
        reset()
      }
      if ((result.errors ?? []).length > 0) {
        setDryRunResult({ ok: result.imported, errors: result.errors ?? [] })
        setCommitError({ message: "Some rows were rejected during commit. Review the row errors below." })
      }
    } catch (error) {
      setCommitError(error)
    } finally {
      setCommitting(false)
    }
  }

  const dryRunSummary = dryRunResult ? dryRunResult.ok + dryRunResult.errors.length : 0
  const blockingErrors = (dryRunResult?.errors.length ?? 0) > 0

  const footer = (
    <>
      <button type="button" className="button-secondary" onClick={onClose}>Cancel</button>
      <button type="button" className="button-secondary" data-testid="dry-run" disabled={rows.length === 0 || dryRunning} onClick={() => void runDryRun()}>
        <RefreshCw size={15} aria-hidden="true" />
        {dryRunning ? "Checking…" : "Run dry run"}
      </button>
      <button
        type="button"
        className="button-primary"
        data-testid="commit-import"
        disabled={!dryRunResult || blockingErrors || committing}
        title={blockingErrors ? "Fix the row errors above before creating commitments." : "Create the validated commitments"}
        onClick={() => void runCommit()}
      >
        <Upload size={15} aria-hidden="true" />
        {committing ? "Creating…" : "Create commitments"}
      </button>
    </>
  )

  const columnsSection = useMemo(
    () => (
      <div className="rounded-[10px] border border-[var(--border)] px-3 py-2 text-xs text-[var(--muted-foreground)]">
        Expected columns: <code className="text-[var(--foreground)]">{COMMITMENT_IMPORT_TEMPLATE_COLUMNS.join(", ")}</code>
      </div>
    ),
    [],
  )

  return (
    <Modal open={open} title="Import Commitments" description="Upload a CSV, dry-run it first, fix any rows, then create. Nothing is written during a dry run." onClose={onClose} footer={footer} size="lg">
      <div className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <button type="button" className="inline-flex items-center gap-2 text-sm font-semibold text-[var(--primary)] outline-none transition hover:underline focus-visible:ring-2 focus-visible:ring-[var(--ring)]" onClick={downloadTemplate} data-testid="import-template">
            <Download size={16} aria-hidden="true" />
            Download CSV template
          </button>
          {columnsSection}
        </div>

        <div className="flex flex-wrap items-center gap-3 rounded-[10px] border border-[var(--border)] bg-[var(--muted)]/20 px-4 py-3">
          <button type="button" className="button-secondary" onClick={() => fileRef.current?.click()} data-testid="choose-file">
            <FileUp size={15} aria-hidden="true" />
            Choose CSV file
          </button>
          <input ref={fileRef} type="file" accept=".csv,text/csv" className="hidden" data-testid="import-file-input" onChange={(event) => onFileChange(event.target.files?.[0])} />
          <span className="text-sm text-[var(--muted-foreground)]">{fileName || "No file selected"}</span>
          {rows.length > 0 && <span className="rounded-full bg-[var(--secondary)] px-2.5 py-1 text-xs text-[var(--foreground)]">{rows.length} data row(s)</span>}
        </div>

        {commitError && !dryRunResult ? <ErrorCoach error={commitError} title="The file could not be processed" /> : null}

        {dryRunResult && (
          <section aria-label="Dry-run results">
            <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
              <h3 className="text-sm font-bold text-[var(--foreground)]">Dry-run results · {dryRunSummary} rows</h3>
              <div className="flex items-center gap-3 text-xs">
                <StatusBadge value={`${dryRunResult.ok} OK`} tone="success" />
                <StatusBadge value={`${dryRunResult.errors.length} errors`} tone={blockingErrors ? "danger" : "success"} />
              </div>
            </div>

            {blockingErrors && (
              <InfoBanner title="Fix and reprocess before creating">
                <ul className="mt-1 list-disc pl-5 text-sm">
                  <li>Review the error messages for each rejected row.</li>
                  <li>Correct the highlighted fields in your CSV.</li>
                  <li>Re-upload the corrected file and run the dry run again.</li>
                  <li>Re-download the template if you need the expected columns.</li>
                </ul>
              </InfoBanner>
            )}
            {!blockingErrors && dryRunResult.ok > 0 && (
              <InfoBanner title="Dry run passed">
                <p className="text-sm">All {dryRunResult.ok} rows validated. You can now create the commitments.</p>
              </InfoBanner>
            )}

            <div className="overflow-x-auto rounded-[10px] border border-[var(--border)]">
              <table className="w-full min-w-[560px] text-left text-sm">
                <thead className="bg-[var(--muted)]/45 text-xs uppercase tracking-[0.08em] text-[var(--muted-foreground)]">
                  <tr>
                    <th scope="col" className="px-3 py-2 font-bold">Row</th>
                    <th scope="col" className="px-3 py-2 font-bold">Status</th>
                    <th scope="col" className="px-3 py-2 font-bold">Field errors</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--border)]">
                  {dryRunResult.errors.length > 0 ? (
                    dryRunResult.errors.map((error) => (
                      <tr key={`${error.row}-${fieldMessages(error).map((item) => item.field).join("-")}`}>
                        <td className="px-3 py-2 tabular-nums">{error.row}</td>
                        <td className="px-3 py-2"><StatusBadge value="ERROR" tone="danger" /></td>
                        <td className="px-3 py-2">
                          <ul className="space-y-1">
                            {fieldMessages(error).map(({ field, messages }) => (
                              <li key={field} className="flex items-start gap-2 text-xs">
                                <span className="font-mono uppercase text-[var(--muted-foreground)]">{field}</span>
                                <span className="text-[var(--foreground)]">{messages.join(", ")}</span>
                                <span className="text-[var(--muted-foreground)]">— fix this field and re-run</span>
                              </li>
                            ))}
                          </ul>
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={3} className="px-3 py-3 text-center text-xs text-[var(--muted-foreground)]">
                        No row errors — every row validated.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </section>
        )}

        {dryRunResult && commitError ? <ErrorCoach error={commitError} title="Commit was not completed" /> : null}
      </div>
    </Modal>
  )
}

export default ImportCommitmentsModal