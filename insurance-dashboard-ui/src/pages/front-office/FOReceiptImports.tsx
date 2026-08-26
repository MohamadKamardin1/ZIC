import { useQuery, useQueryClient } from "@tanstack/react-query"
import { CheckCircle2, Download, FileCheck2, FileSpreadsheet, LoaderCircle, RotateCcw, Upload, XCircle } from "lucide-react"
import { useRef, useState } from "react"
import { Link } from "react-router-dom"
import { ErrorCoach } from "../../components/ErrorCoach"
import { ReceiptStatusBadge } from "../../components/receipts/ReceiptPrimitives"
import { InfoBanner } from "../../components/ui/Overlays"
import { MasterDetailPage } from "../../components/ui/Patterns"
import { useAccess } from "../../lib/access"
import { ApiClientError } from "../../lib/apiClient"
import { receiptsApi, type ReceiptImportBatch, type ReceiptImportResult, type ReceiptImportRowResult } from "../../lib/receipts-api"

const IMPORT_MODES = [
  { value: "CREATE_DRAFTS", label: "Create drafts", hint: "Create receipt records in Draft status for review." },
  { value: "POST", label: "Post", hint: "Post validated receipts without allocating them." },
  { value: "POST_AND_ALLOCATE", label: "Post and allocate", hint: "Post and allocate rows when a target commitment is provided." },
] as const

type ImportMode = typeof IMPORT_MODES[number]["value"]

function errorCoachProps(error: unknown) {
  if (error instanceof ApiClientError) return { message: error.message, resolutionSteps: error.resolutionSteps, loginUrl: error.deepLink, actionLabel: error.deepLink ? "Open resolution page" : undefined }
  return { message: error instanceof Error ? error.message : "The receipt import service could not be reached. Refresh and try again." }
}

function formatDateTime(value: string): string {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(date)
}

function resultRows(result: ReceiptImportResult | null): ReceiptImportRowResult[] {
  if (!result) return []
  if (result.rows?.length) return result.rows
  return result.errors
}

function resultSummary(result: ReceiptImportResult | null) {
  const rows = resultRows(result)
  const errors = result?.error_count ?? result?.errors.length ?? rows.filter((row) => row.status === "ERROR").length
  const total = result?.total_rows ?? rows.length
  const ok = result?.ok_count ?? Math.max(total - errors, 0)
  return { total, ok, errors }
}

function downloadBlob(blob: Blob, fileName: string) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement("a")
  link.href = url
  link.download = fileName
  link.click()
  URL.revokeObjectURL(url)
}

function FieldErrors({ row }: { row: ReceiptImportRowResult }) {
  const entries = Object.entries(row.field_errors ?? {})
  if (!entries.length && !(row.resolution_steps?.length)) return <span className="text-sm text-[var(--muted-foreground)]">No field-level message returned.</span>
  return <div className="space-y-2 text-sm"><ul className="list-disc space-y-1 pl-5">{entries.map(([field, messages]) => <li key={field}><span className="font-bold">{field}:</span> {messages.join("; ")}</li>)}</ul>{row.resolution_steps?.length ? <div className="rounded-[8px] bg-[var(--muted)]/35 px-3 py-2"><p className="font-bold">How to fix this row</p><ul className="mt-1 list-disc space-y-1 pl-5">{row.resolution_steps.map((step) => <li key={step}>{step}</li>)}</ul></div> : null}</div>
}

function SummaryCards({ result, label }: { result: ReceiptImportResult | null; label: string }) {
  const summary = resultSummary(result)
  return <div className="grid gap-3 sm:grid-cols-3" aria-label={`${label} summary`}><div className="surface-card p-4"><p className="text-xs font-bold uppercase tracking-[0.1em] text-[var(--muted-foreground)]">Rows checked</p><p className="mt-2 text-2xl font-extrabold">{summary.total.toLocaleString()}</p></div><div className="surface-card p-4"><p className="text-xs font-bold uppercase tracking-[0.1em] text-[var(--muted-foreground)]">Ready</p><p className="mt-2 flex items-center gap-2 text-2xl font-extrabold text-emerald-700"><CheckCircle2 size={20} aria-hidden="true" />{summary.ok.toLocaleString()}</p></div><div className="surface-card p-4"><p className="text-xs font-bold uppercase tracking-[0.1em] text-[var(--muted-foreground)]">Blocking errors</p><p className="mt-2 flex items-center gap-2 text-2xl font-extrabold text-[var(--destructive)]"><XCircle size={20} aria-hidden="true" />{summary.errors.toLocaleString()}</p></div></div>
}

function RowResults({ result }: { result: ReceiptImportResult | null }) {
  const rows = resultRows(result)
  if (!rows.length) return <InfoBanner title="No row results returned"><p>The service returned no row-level results. Confirm the file is a supported CSV and run the dry-run again.</p></InfoBanner>
  return <div className="overflow-x-auto rounded-[10px] border border-[var(--border)]"><table className="w-full min-w-[780px] text-left text-sm"><caption className="sr-only">Receipt CSV row validation results</caption><thead className="bg-[var(--muted)]/45 text-xs uppercase tracking-[0.08em] text-[var(--muted-foreground)]"><tr><th className="px-4 py-3">Row</th><th className="px-4 py-3">Status</th><th className="px-4 py-3">Messages and resolution hints</th></tr></thead><tbody className="divide-y divide-[var(--border)]">{rows.map((row) => <tr key={row.row} className={row.status === "ERROR" ? "bg-red-50/50" : undefined}><td className="px-4 py-4 align-top font-bold">{row.row}</td><td className="px-4 py-4 align-top"><span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-bold ${row.status === "ERROR" ? "bg-red-100 text-red-800" : "bg-emerald-100 text-emerald-800"}`}>{row.status === "ERROR" ? <XCircle size={13} aria-hidden="true" /> : <CheckCircle2 size={13} aria-hidden="true" />}{row.status}</span></td><td className="px-4 py-4 align-top">{row.status === "ERROR" ? <FieldErrors row={row} /> : <span className="text-emerald-800">Row is ready for import.</span>}</td></tr>)}</tbody></table></div>
}

export default function FOReceiptImports() {
  const { access, isSuperAdmin, hasPermission } = useAccess()
  const queryClient = useQueryClient()
  const fileRef = useRef<HTMLInputElement>(null)
  const [file, setFile] = useState<File | null>(null)
  const [dryRunResult, setDryRunResult] = useState<ReceiptImportResult | null>(null)
  const [commitResult, setCommitResult] = useState<ReceiptImportResult | null>(null)
  const [mode, setMode] = useState<ImportMode>("CREATE_DRAFTS")
  const [allowPartial, setAllowPartial] = useState(false)
  const [busy, setBusy] = useState<"dry-run" | "commit" | "template" | "reprocess" | null>(null)
  const [error, setError] = useState<unknown>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [selectedBatchId, setSelectedBatchId] = useState<string | null>(null)
  const canImport = isSuperAdmin || Boolean(hasPermission?.("front_office.receipts.import"))
  const historyQuery = useQuery({ queryKey: ["receipts", "imports"], queryFn: () => receiptsApi.imports({ page: 1, page_size: 25 }), enabled: canImport, retry: false })
  const detailQuery = useQuery({ queryKey: ["receipts", "imports", selectedBatchId], queryFn: () => receiptsApi.importDetail(selectedBatchId as string), enabled: canImport && Boolean(selectedBatchId), retry: false })

  const selectFile = (nextFile: File | undefined) => {
    if (!nextFile) return
    setFile(nextFile)
    setDryRunResult(null)
    setCommitResult(null)
    setAllowPartial(false)
    setError(null)
    setMessage(null)
  }

  const runDryRun = async () => {
    if (!file) return
    setBusy("dry-run")
    setError(null)
    setMessage(null)
    try {
      const result = await receiptsApi.importDryRun(file)
      setDryRunResult(result)
      const summary = resultSummary(result)
      setMessage(`Dry-run complete: ${summary.ok} rows ready and ${summary.errors} blocking errors.`)
    } catch (nextError) {
      setError(nextError)
    } finally {
      setBusy(null)
    }
  }

  const commitImport = async () => {
    if (!file || !dryRunResult) return
    const summary = resultSummary(dryRunResult)
    if (summary.errors > 0 && !allowPartial) return
    setBusy("commit")
    setError(null)
    setMessage(null)
    try {
      const result = await receiptsApi.importCommit(file, mode)
      setCommitResult(result)
      setMessage(`Import finished: ${result.created} records created, ${result.errors.length} row errors.`)
      void queryClient.invalidateQueries({ queryKey: ["receipts", "imports"] })
    } catch (nextError) {
      setError(nextError)
    } finally {
      setBusy(null)
    }
  }

  const downloadTemplate = async () => {
    setBusy("template")
    setError(null)
    try {
      const blob = await receiptsApi.downloadCsvTemplate()
      downloadBlob(blob, "front-office-receipts-template.csv")
      setMessage("CSV template downloaded. Keep the header names unchanged so every row can be explained safely.")
    } catch (nextError) {
      setError(nextError)
    } finally {
      setBusy(null)
    }
  }

  const reprocess = async () => {
    if (!selectedBatchId) return
    setBusy("reprocess")
    setError(null)
    try {
      const result = await receiptsApi.importReprocess(selectedBatchId)
      setMessage(`Reprocess finished: ${result.created} records created, ${result.errors.length} row errors.`)
      void queryClient.invalidateQueries({ queryKey: ["receipts", "imports"] })
      void queryClient.invalidateQueries({ queryKey: ["receipts", "imports", selectedBatchId] })
    } catch (nextError) {
      setError(nextError)
    } finally {
      setBusy(null)
    }
  }

  if (!canImport) return <div className="space-y-4 p-4 md:p-6"><Link to="/front-office/receipts" className="font-semibold text-[var(--primary)] hover:underline">Back to Receipts Work Queue</Link><ErrorCoach title="Receipt import access required" message="Your access profile does not include permission to import receipts." resolutionSteps={["Ask an administrator for front_office.receipts.import.", "Return to the Receipts Work Queue after access is granted."]} /></div>

  const dryRunSummary = resultSummary(dryRunResult)
  const canCommit = Boolean(file && dryRunResult && (dryRunSummary.errors === 0 || allowPartial))

  return <div className="space-y-5 p-4 md:p-6">
    <Link to="/front-office/receipts" className="inline-flex items-center gap-2 text-sm font-semibold text-[var(--primary)] hover:underline">Back to Receipts Work Queue</Link>
    <MasterDetailPage eyebrow="Front Office · Receipts" title="Bulk Receipt Import" description="Validate every CSV row before creating drafts, posting receipts, or allocating to supplied commitments." actions={<div className="flex flex-wrap gap-2"><button type="button" className="button-secondary" onClick={() => void downloadTemplate()} disabled={busy !== null}><Download size={16} aria-hidden="true" />{busy === "template" ? "Downloading…" : "Download CSV template"}</button><button type="button" className="button-primary" onClick={() => fileRef.current?.click()} disabled={busy !== null}><Upload size={16} aria-hidden="true" />Choose CSV file</button><input ref={fileRef} aria-label="Receipt CSV file" type="file" accept=".csv,text/csv" className="hidden" onChange={(event) => { selectFile(event.target.files?.[0]); event.target.value = "" }} /></div>}>
      <div className="space-y-6">
        <section className="surface-card p-5" aria-labelledby="import-upload-heading"><div className="flex flex-wrap items-start justify-between gap-4"><div><h2 id="import-upload-heading" className="text-lg font-bold">1. Upload and dry-run</h2><p className="mt-1 max-w-2xl text-sm text-[var(--muted-foreground)]">Dry-run is the default safety gate. It does not create, post, or allocate receipts.</p></div><FileSpreadsheet size={24} className="text-[var(--primary)]" aria-hidden="true" /></div><div className="mt-5 rounded-[10px] border border-dashed border-[var(--border)] bg-[var(--muted)]/20 p-5"><p className="font-semibold">{file ? file.name : "No CSV file selected"}</p><p className="mt-1 text-sm text-[var(--muted-foreground)]">{file ? `${(file.size / 1024).toFixed(1)} KB ready for validation.` : "Select a CSV file using the button above, then run the dry-run."}</p>{file && <button type="button" className="button-primary mt-4" onClick={() => void runDryRun()} disabled={busy !== null}>{busy === "dry-run" ? <><LoaderCircle size={16} className="animate-spin" aria-hidden="true" />Checking rows…</> : <><FileCheck2 size={16} aria-hidden="true" />Run dry-run</>}</button>}</div></section>

        {error !== null && <ErrorCoach title="Receipt import needs attention" {...errorCoachProps(error)} />}
        {message && <InfoBanner title="Import update"><p>{message}</p></InfoBanner>}

        {dryRunResult && <section className="space-y-4" aria-labelledby="dry-run-results-heading"><div><h2 id="dry-run-results-heading" className="text-lg font-bold">2. Dry-run results</h2><p className="mt-1 text-sm text-[var(--muted-foreground)]">Every row is shown with field-level messages and resolution hints. Correct the file and re-run when a row is blocked.</p></div><SummaryCards result={dryRunResult} label="Dry-run" /><RowResults result={dryRunResult} /></section>}

        {dryRunResult && <section className="surface-card space-y-4 p-5" aria-labelledby="import-commit-heading"><div><h2 id="import-commit-heading" className="text-lg font-bold">3. Commit import</h2><p className="mt-1 text-sm text-[var(--muted-foreground)]">Choose what the validated rows should do. Post-and-allocate requires a target commitment in the relevant CSV row.</p></div><div className="grid gap-4 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]"><label htmlFor="receipt-import-mode" className="space-y-1.5 text-sm font-semibold">Import mode<select id="receipt-import-mode" aria-label="Import mode" className="mt-1 w-full rounded-[10px] border border-[var(--border)] bg-[var(--card)] px-3 py-2.5 text-sm font-normal" value={mode} onChange={(event) => setMode(event.target.value as ImportMode)}>
{IMPORT_MODES.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select><span className="block text-xs font-normal text-[var(--muted-foreground)]">{IMPORT_MODES.find((option) => option.value === mode)?.hint}</span></label><div className="rounded-[10px] border border-[var(--border)] bg-[var(--muted)]/20 p-4"><p className="text-sm font-bold">Safety gate</p>{dryRunSummary.errors > 0 ? <label className="mt-2 flex items-start gap-2 text-sm"><input type="checkbox" className="mt-1" checked={allowPartial} onChange={(event) => setAllowPartial(event.target.checked)} /><span>Allow partial import and commit the {dryRunSummary.ok} valid row(s) while leaving {dryRunSummary.errors} error row(s) for correction.</span></label> : <p className="mt-2 flex items-center gap-2 text-sm text-emerald-800"><CheckCircle2 size={16} aria-hidden="true" />All rows passed the dry-run.</p>}</div></div><button type="button" className="button-primary" onClick={() => void commitImport()} disabled={!canCommit || busy !== null}>{busy === "commit" ? <><LoaderCircle size={16} className="animate-spin" aria-hidden="true" />Committing…</> : "Commit import"}</button>{dryRunSummary.errors > 0 && !allowPartial && <p className="text-sm font-semibold text-amber-800">Commit is disabled until all blocking rows are corrected or you explicitly confirm a partial import.</p>}</section>}

        {commitResult && <section className="space-y-4" aria-labelledby="import-result-heading"><div><h2 id="import-result-heading" className="text-lg font-bold">Import result</h2><p className="mt-1 text-sm text-[var(--muted-foreground)]">The server result is retained here so failed rows can be corrected and safely reprocessed.</p></div><SummaryCards result={commitResult} label="Import" /><RowResults result={commitResult} /></section>}

        <section className="space-y-4" aria-labelledby="import-history-heading"><div><h2 id="import-history-heading" className="text-lg font-bold">Import history</h2><p className="mt-1 text-sm text-[var(--muted-foreground)]">Review previous batches, drill into row errors, and reprocess a batch after correcting its source file.</p></div>{historyQuery.isLoading && <div className="surface-card p-6 text-sm text-[var(--muted-foreground)]" role="status">Loading import history…</div>}{historyQuery.isError && <ErrorCoach title="Import history could not be loaded" {...errorCoachProps(historyQuery.error)} />}{!historyQuery.isLoading && !historyQuery.isError && !historyQuery.data?.results.length && <InfoBanner title="No import batches yet"><p>After the first dry-run or commit, this area will retain a reviewable batch history.</p></InfoBanner>}{!historyQuery.isLoading && !historyQuery.isError && Boolean(historyQuery.data?.results.length) && <div className="overflow-x-auto rounded-[10px] border border-[var(--border)]"><table className="w-full min-w-[820px] text-left text-sm"><caption className="sr-only">Receipt import history</caption><thead className="bg-[var(--muted)]/45 text-xs uppercase tracking-[0.08em] text-[var(--muted-foreground)]"><tr><th className="px-4 py-3">File</th><th className="px-4 py-3">Uploaded by / date</th><th className="px-4 py-3">Rows</th><th className="px-4 py-3">Ready</th><th className="px-4 py-3">Errors</th><th className="px-4 py-3">Status</th><th className="px-4 py-3">Action</th></tr></thead><tbody className="divide-y divide-[var(--border)]">{historyQuery.data?.results.map((batch: ReceiptImportBatch) => <tr key={batch.id}><td className="px-4 py-3 font-semibold">{batch.file_name}</td><td className="px-4 py-3">{batch.uploaded_by_display} · {formatDateTime(batch.uploaded_at)}</td><td className="px-4 py-3">{batch.total_rows}</td><td className="px-4 py-3 text-emerald-800">{batch.ok_count}</td><td className="px-4 py-3 text-red-800">{batch.error_count}</td><td className="px-4 py-3"><ReceiptStatusBadge status={batch.status} /></td><td className="px-4 py-3"><button type="button" className="font-bold text-[var(--primary)] hover:underline" onClick={() => setSelectedBatchId(batch.id)}>View rows</button></td></tr>)}</tbody></table></div>}

          {selectedBatchId && <div className="surface-card space-y-4 p-5" aria-labelledby="import-batch-detail-heading"><div className="flex flex-wrap items-start justify-between gap-3"><div><h3 id="import-batch-detail-heading" className="font-bold">Batch row detail</h3><p className="mt-1 text-sm text-[var(--muted-foreground)]">{detailQuery.data?.file_name ?? "Loading selected batch…"}</p></div><div className="flex flex-wrap gap-2"><button type="button" className="button-secondary" onClick={() => setSelectedBatchId(null)}>Close</button><button type="button" className="button-primary" onClick={() => void reprocess()} disabled={busy !== null || detailQuery.isLoading}>{busy === "reprocess" ? <><LoaderCircle size={16} className="animate-spin" aria-hidden="true" />Reprocessing…</> : <><RotateCcw size={16} aria-hidden="true" />Reprocess batch</>}</button></div></div>{detailQuery.isLoading && <div className="text-sm text-[var(--muted-foreground)]" role="status">Loading row detail…</div>}{detailQuery.isError && <ErrorCoach title="Batch detail could not be loaded" {...errorCoachProps(detailQuery.error)} />}{detailQuery.data && <RowResults result={{ dry_run: false, imported: detailQuery.data.total_rows, created: 0, errors: detailQuery.data.errors, rows: detailQuery.data.errors, total_rows: detailQuery.data.total_rows, ok_count: detailQuery.data.ok_count, error_count: detailQuery.data.error_count }} />}</div>}
        </section>
      </div>
    </MasterDetailPage>
  </div>
}
