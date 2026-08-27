import { useCallback, useEffect, useState } from "react"
import { Download, ExternalLink, FileText, LoaderCircle, RefreshCw, X } from "lucide-react"
import { ApiClientError, request } from "../../lib/apiClient"
import { fetchAuthenticatedDocument, openAuthenticatedDocument, revokeAuthenticatedDocument, type AuthenticatedDocumentResult } from "../../lib/documentClient"
import { printWithdrawalStatement, type WithdrawalDetail, type WithdrawalPrintResult } from "../../lib/withdrawals"
import { ErrorCoach } from "../ErrorCoach"
import { InfoBanner, Modal } from "../ui/Overlays"

interface WithdrawalDocumentRecord {
  id: string
  documentType: string
  templateName: string
  templateVersion: string | number
  generatedByDisplay: string
  generatedAt: string
  pageCount: string | number
  previewUrl?: string | null
  downloadUrl?: string | null
  signedDownloadUrl?: string | null
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value)
}

function stringValue(row: Record<string, unknown>, ...keys: string[]): string {
  for (const key of keys) if (row[key] !== undefined && row[key] !== null) return String(row[key])
  return ""
}

function scalarValue(value: unknown, fallback: string | number): string | number {
  return typeof value === "string" || typeof value === "number" ? value : fallback
}

function normalizeRecord(value: unknown): WithdrawalDocumentRecord {
  const row = isRecord(value) ? value : {}
  return {
    id: stringValue(row, "id", "document_id"),
    documentType: stringValue(row, "documentType", "document_type") || "OL_WITHDRAWAL_STATEMENT",
    templateName: stringValue(row, "templateName", "template_name", "template_display") || "Withdrawal Statement",
    templateVersion: scalarValue(row.templateVersion ?? row.template_version ?? row.version, "—"),
    generatedByDisplay: stringValue(row, "generatedByDisplay", "generated_by_display", "generatedByName", "generated_by_name", "generated_by") || "System",
    generatedAt: stringValue(row, "generatedAt", "generated_at", "created_at"),
    pageCount: scalarValue(row.pageCount ?? row.page_count ?? row.pages, "—"),
    previewUrl: typeof row.previewUrl === "string" ? row.previewUrl : typeof row.preview_url === "string" ? row.preview_url : null,
    downloadUrl: typeof row.downloadUrl === "string" ? row.downloadUrl : typeof row.download_url === "string" ? row.download_url : typeof row.pdf_url === "string" ? row.pdf_url : null,
    signedDownloadUrl: typeof row.signedDownloadUrl === "string" ? row.signedDownloadUrl : typeof row.signed_download_url === "string" ? row.signed_download_url : null,
  }
}

function normalizeRows(value: unknown): WithdrawalDocumentRecord[] {
  const record = isRecord(value) ? value : {}
  const rows = Array.isArray(value) ? value : Array.isArray(record.results) ? record.results : Array.isArray(record.documents) ? record.documents : []
  return rows.map(normalizeRecord).filter((row) => Boolean(row.id))
}

function labelForType(documentType: string): string {
  return documentType === "OL_WITHDRAWAL_PAYMENT_CONFIRMATION" ? "Payment Confirmation" : "Withdrawal Statement"
}

function formatDate(value: string): string {
  if (!value) return "—"
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString()
}

function watermarkFor(status: string): "CANCELLED" | "REVERSED" | null {
  const value = status.toUpperCase()
  return value === "CANCELLED" || value === "REVERSED" ? value : null
}

function errorProps(error: unknown): { title: string; message: string; steps?: string[]; settingsUrl?: string } {
  if (error instanceof ApiClientError && error.code === "TEMPLATE_PENDING") return { title: "Withdrawal document template pending", message: error.message, steps: error.resolutionSteps, settingsUrl: "/system-parameters/documents/branding" }
  if (error instanceof ApiClientError) return { title: "Withdrawal document could not be generated", message: error.message, steps: error.resolutionSteps }
  return { title: "Withdrawal document action failed", message: error instanceof Error ? error.message : "The withdrawal document action could not be completed." }
}

function documentUrl(record: WithdrawalDocumentRecord): string | null {
  return record.signedDownloadUrl ?? record.previewUrl ?? record.downloadUrl ?? null
}

function PreviewModal({ preview, record, watermark, onClose, onDownload, onOpenSigned, downloading }: { preview: AuthenticatedDocumentResult | null; record: WithdrawalDocumentRecord | null; watermark: "CANCELLED" | "REVERSED" | null; onClose: () => void; onDownload: () => void; onOpenSigned: () => void; downloading: boolean }) {
  const title = record ? labelForType(record.documentType) : "Withdrawal document"
  return <Modal open={Boolean(preview)} title={`${title} · PDF`} onClose={onClose} size="xl" footer={<><button type="button" className="button-secondary inline-flex items-center gap-2" onClick={onDownload} disabled={!preview || downloading}>{downloading ? <LoaderCircle size={15} className="animate-spin" aria-hidden="true" /> : <Download size={15} aria-hidden="true" />}{downloading ? "Downloading…" : "Download"}</button><button type="button" className="button-secondary inline-flex items-center gap-2" onClick={onOpenSigned} disabled={!preview}><ExternalLink size={15} aria-hidden="true" />Open in New Tab</button><button type="button" className="button-primary" onClick={onClose}>Close</button></>}><div className="space-y-3"><div className="flex items-center justify-between rounded-[10px] border border-blue-200 bg-blue-50 px-3 py-2 text-sm text-blue-900 dark:border-blue-900/60 dark:bg-blue-950/30 dark:text-blue-100"><span className="flex items-center gap-2"><FileText size={16} aria-hidden="true" />Authenticated branded PDF preview</span><button type="button" aria-label="Close PDF preview" className="rounded-md p-1 hover:bg-blue-100 focus:outline-none focus:ring-2 focus:ring-blue-600" onClick={onClose}><X size={16} aria-hidden="true" /></button></div>{watermark && <div className="rounded-[10px] border border-amber-300 bg-amber-50 px-4 py-3 text-sm font-bold text-amber-950" role="status">This withdrawal is {watermark}. The PDF carries a {watermark} watermark.</div>}{preview && <div className="relative overflow-hidden rounded-[10px] border bg-slate-100"><iframe title={`${title} PDF`} src={preview.objectUrl} className="min-h-[65vh] w-full" />{watermark && <div className="pointer-events-none absolute inset-0 flex items-center justify-center"><span className="rotate-[-28deg] select-none text-[clamp(3rem,10vw,8rem)] font-black tracking-[0.18em] text-red-600/15">{watermark}</span></div>}</div>}</div></Modal>
}

export function WithdrawalDocumentsPanel({ withdrawal, canPrint }: { withdrawal: WithdrawalDetail; canPrint: boolean }) {
  const [records, setRecords] = useState<WithdrawalDocumentRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [rendering, setRendering] = useState(false)
  const [downloading, setDownloading] = useState(false)
  const [error, setError] = useState<unknown>(null)
  const [previewError, setPreviewError] = useState<unknown>(null)
  const [preview, setPreview] = useState<AuthenticatedDocumentResult | null>(null)
  const [previewRecord, setPreviewRecord] = useState<WithdrawalDocumentRecord | null>(null)
  const watermark = watermarkFor(String(withdrawal.statusDisplay || withdrawal.status))

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const query = new URLSearchParams({ source_type: "ol_policies.withdrawalrequest", object_id: withdrawal.id, page_size: "50" })
      const payload = await request<unknown>(`/api/v1/documents/instances/?${query.toString()}`)
      setRecords(normalizeRows(payload))
    } catch (caught) {
      setError(caught)
    } finally {
      setLoading(false)
    }
  }, [withdrawal.id])

  useEffect(() => { void load() }, [load])
  useEffect(() => () => revokeAuthenticatedDocument(preview), [preview])

  const openPreview = async (record: WithdrawalDocumentRecord) => {
    const url = documentUrl(record)
    if (!url) { setPreviewError(new Error("This withdrawal document has no secure PDF URL. Generate it again or contact ZIC Finance.")); return }
    setPreviewError(null)
    revokeAuthenticatedDocument(preview)
    try {
      const result = await fetchAuthenticatedDocument(url, "pdf")
      setPreview(result)
      setPreviewRecord(record)
    } catch (caught) { setPreviewError(caught) }
  }

  const generate = async () => {
    setRendering(true)
    setError(null)
    try {
      const result: WithdrawalPrintResult = await printWithdrawalStatement(withdrawal.id)
      const generated = normalizeRecord(result.instance)
      const url = result.signedDownloadUrl ?? result.previewUrl ?? result.previewBlobBase64OrUrl ?? documentUrl(generated)
      if (!url) throw new Error("The server did not return a secure PDF URL for this withdrawal statement.")
      const nextPreview = await fetchAuthenticatedDocument(url, "pdf")
      revokeAuthenticatedDocument(preview)
      const record = { ...generated, documentType: generated.documentType || "OL_WITHDRAWAL_STATEMENT", signedDownloadUrl: result.signedDownloadUrl ?? generated.signedDownloadUrl, previewUrl: result.previewUrl ?? generated.previewUrl }
      setPreview(nextPreview)
      setPreviewRecord(record)
      await load()
    } catch (caught) { setError(caught) }
    finally { setRendering(false) }
  }

  const download = async () => {
    if (!previewRecord) return
    const url = documentUrl(previewRecord)
    if (!url) { setPreviewError(new Error("This withdrawal document has no secure PDF URL.")); return }
    setDownloading(true)
    setPreviewError(null)
    try { await openAuthenticatedDocument(url, { kind: "pdf", mode: "download", filename: `${withdrawal.withdrawalNumber}-statement.pdf` }) }
    catch (caught) { setPreviewError(caught) }
    finally { setDownloading(false) }
  }

  const downloadDocument = async (record: WithdrawalDocumentRecord) => {
    const url = documentUrl(record)
    if (!url) { setError(new Error("This withdrawal document has no secure PDF URL. Generate it again or contact ZIC Finance.")); return }
    setDownloading(true)
    setError(null)
    try { await openAuthenticatedDocument(url, { kind: "pdf", mode: "download", filename: `${withdrawal.withdrawalNumber}-${record.documentType.toLowerCase()}.pdf` }) }
    catch (caught) { setError(caught) }
    finally { setDownloading(false) }
  }

  const openSigned = () => {
    if (previewRecord?.signedDownloadUrl) window.open(previewRecord.signedDownloadUrl, "_blank", "noopener,noreferrer")
    else setPreviewError(new Error("Open in New Tab is available only after the server issues a signed download ticket."))
  }

  const closePreview = () => { revokeAuthenticatedDocument(preview); setPreview(null); setPreviewRecord(null); setPreviewError(null) }
  const normalizedError = error ? errorProps(error) : null
  const normalizedPreviewError = previewError ? errorProps(previewError) : null
  return <section className="surface-card overflow-hidden" aria-labelledby="withdrawal-documents-heading" data-testid="withdrawal-documents-panel"><header className="flex flex-wrap items-start justify-between gap-3 border-b px-5 py-4"><div><h2 id="withdrawal-documents-heading" className="flex items-center gap-2 text-base font-bold"><FileText size={18} aria-hidden="true" />Documents</h2><p className="mt-1 text-sm text-[var(--muted-foreground)]">Withdrawal statements and payment confirmations retain their source transaction and approved template version.</p></div><div className="flex flex-wrap gap-2"><button type="button" className="button-secondary inline-flex items-center gap-2" onClick={() => void load()} disabled={loading || rendering}><RefreshCw size={15} className={loading ? "animate-spin" : ""} aria-hidden="true" />Refresh</button>{canPrint && <button type="button" className="button-primary inline-flex items-center gap-2" onClick={() => void generate()} disabled={rendering}><FileText size={15} aria-hidden="true" />{rendering ? "Generating…" : "Print Statement"}</button>}</div></header><div className="p-5">{normalizedError && <ErrorCoach title={normalizedError.title} message={normalizedError.message} resolutionSteps={normalizedError.steps} loginUrl={normalizedError.settingsUrl} actionLabel={normalizedError.settingsUrl ? "Open document settings" : undefined} />}{watermark && <InfoBanner title={`${watermark} withdrawal document watermark`}><p>The generated statement carries a visible <strong>{watermark}</strong> status watermark.</p></InfoBanner>}{loading ? <div className="flex items-center gap-2 py-8 text-sm text-[var(--muted-foreground)]" role="status"><LoaderCircle size={16} className="animate-spin" aria-hidden="true" />Loading generated withdrawal documents…</div> : records.length === 0 ? <p className="py-8 text-sm text-[var(--muted-foreground)]">No generated documents yet. Use Print Statement to create the first version.</p> : <div className="overflow-x-auto"><table className="w-full min-w-[930px] text-left text-sm"><caption className="sr-only">Generated withdrawal documents</caption><thead><tr className="border-b text-xs uppercase tracking-wide text-[var(--muted-foreground)]"><th className="px-3 py-3">Document</th><th className="px-3 py-3">Template</th><th className="px-3 py-3">Version</th><th className="px-3 py-3">Generated by</th><th className="px-3 py-3">Generated at</th><th className="px-3 py-3">Pages</th><th className="px-3 py-3 text-right">Actions</th></tr></thead><tbody>{records.map((record) => <tr key={record.id || `${record.documentType}-${record.generatedAt}`} className="border-b last:border-0 hover:bg-[var(--muted)]/35"><td className="px-3 py-3 font-semibold">{labelForType(record.documentType)}</td><td className="px-3 py-3">{record.templateName}</td><td className="px-3 py-3">v{record.templateVersion}</td><td className="px-3 py-3">{record.generatedByDisplay}</td><td className="px-3 py-3">{formatDate(record.generatedAt)}</td><td className="px-3 py-3">{record.pageCount}</td><td className="px-3 py-3"><div className="flex flex-wrap justify-end gap-2"><button type="button" className="button-secondary inline-flex items-center gap-1" onClick={() => void openPreview(record)}>Preview</button><button type="button" className="button-secondary inline-flex items-center gap-1" onClick={() => void downloadDocument(record)} disabled={downloading}><Download size={14} aria-hidden="true" />Download</button>{record.signedDownloadUrl && <button type="button" className="button-secondary inline-flex items-center gap-1" onClick={() => { setPreviewRecord(record); openSigned() }}><ExternalLink size={14} aria-hidden="true" />Open in New Tab</button>}</div></td></tr>)}</tbody></table></div>}{normalizedPreviewError && <div className="mt-4"><ErrorCoach title="Withdrawal document preview unavailable" message={normalizedPreviewError.message} resolutionSteps={normalizedPreviewError.steps} loginUrl={normalizedPreviewError.settingsUrl} actionLabel={normalizedPreviewError.settingsUrl ? "Open document settings" : undefined} /></div>}</div><PreviewModal preview={preview} record={previewRecord} watermark={watermark} onClose={closePreview} onDownload={() => void download()} onOpenSigned={openSigned} downloading={downloading} /></section>
}
