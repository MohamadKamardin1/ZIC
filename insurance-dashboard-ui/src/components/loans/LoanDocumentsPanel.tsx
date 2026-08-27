import { Download, ExternalLink, FileText, LoaderCircle, RefreshCw, X } from "lucide-react"
import { useCallback, useEffect, useState } from "react"
import { ApiClientError, request } from "../../lib/apiClient"
import { fetchAuthenticatedDocument, openAuthenticatedDocument, revokeAuthenticatedDocument, type AuthenticatedDocumentResult } from "../../lib/documentClient"
import { printLoanDocument, type LoanDetail } from "../../lib/loans"
import { ErrorCoach } from "../ErrorCoach"
import { InfoBanner, Modal } from "../ui/Overlays"

interface LoanDocumentRecord {
  id: string
  documentType: string
  templateName: string
  templateVersion: number | string
  generatedByDisplay: string
  generatedAt: string
  pageCount: number | string
  previewUrl?: string | null
  downloadUrl?: string | null
  signedDownloadUrl?: string | null
}

interface LoanDocumentsPayload {
  count?: number
  results?: unknown[]
}

type PrintType = "agreement" | "schedule"

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value)
}

function stringValue(row: Record<string, unknown>, ...keys: string[]): string {
  for (const key of keys) if (row[key] !== undefined && row[key] !== null) return String(row[key])
  return ""
}

function nullableString(row: Record<string, unknown>, ...keys: string[]): string | null {
  const value = stringValue(row, ...keys)
  return value || null
}

function scalarValue(value: unknown, fallback: string | number): string | number {
  return typeof value === "string" || typeof value === "number" ? value : fallback
}

function normalizeRecord(value: unknown): LoanDocumentRecord {
  const row = isRecord(value) ? value : {}
  return {
    id: stringValue(row, "id", "uuid"),
    documentType: stringValue(row, "documentType", "document_type"),
    templateName: stringValue(row, "templateName", "template_name") || "Loan document",
    templateVersion: scalarValue(row.templateVersion ?? row.template_version, "—"),
    generatedByDisplay: stringValue(row, "generatedByDisplay", "generated_by_display", "generatedBy", "generated_by") || "System",
    generatedAt: stringValue(row, "generatedAt", "generated_at"),
    pageCount: scalarValue(row.pageCount ?? row.page_count, "—"),
    previewUrl: nullableString(row, "previewUrl", "preview_url"),
    downloadUrl: nullableString(row, "downloadUrl", "download_url"),
    signedDownloadUrl: nullableString(row, "signedDownloadUrl", "signed_download_url"),
  }
}

function formatDate(value: string): string {
  if (!value) return "—"
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString()
}

function documentLabel(documentType: string): string {
  return documentType === "OL_LOAN_SCHEDULE" ? "Repayment Schedule" : "Loan Agreement"
}

function watermarkFor(status: string): "DEFAULTED" | "SETTLED" | null {
  const normalized = status.toUpperCase()
  return normalized === "DEFAULTED" || normalized === "SETTLED" ? normalized : null
}

function errorProps(error: unknown): { message: string; resolutionSteps?: string[]; loginUrl?: string; actionLabel?: string } {
  if (error instanceof ApiClientError) {
    if (["TEMPLATE_PENDING", "PARAMETER_MISSING", "BRANDING_NOT_CONFIGURED"].includes(error.code)) {
      return {
        message: `${error.message} Configure the loan document template and branding in System Parameters, then try again.`,
        resolutionSteps: error.resolutionSteps,
        loginUrl: "/system-parameters/documents/branding",
        actionLabel: "Open document settings",
      }
    }
    return { message: error.message, resolutionSteps: error.resolutionSteps }
  }
  return { message: error instanceof Error ? error.message : "The loan document action could not be completed." }
}

function documentUrl(document: LoanDocumentRecord): string | null {
  return document.signedDownloadUrl ?? document.previewUrl ?? document.downloadUrl ?? null
}

function PreviewModal({ preview, title, watermark, onClose, onDownload, onOpenSigned, downloading }: { preview: AuthenticatedDocumentResult | null; title: string; watermark: "DEFAULTED" | "SETTLED" | null; onClose: () => void; onDownload: () => void; onOpenSigned: () => void; downloading: boolean }) {
  return <Modal open={Boolean(preview)} title={`${title} · PDF`} onClose={onClose} size="xl" footer={<><button type="button" className="button-secondary inline-flex items-center gap-2" onClick={onDownload} disabled={!preview || downloading}>{downloading ? <LoaderCircle size={15} className="animate-spin" aria-hidden="true" /> : <Download size={15} aria-hidden="true" />}{downloading ? "Downloading…" : "Download"}</button><button type="button" className="button-secondary inline-flex items-center gap-2" onClick={onOpenSigned} disabled={!preview}><ExternalLink size={15} aria-hidden="true" />Open in New Tab</button><button type="button" className="button-primary" onClick={onClose}>Close</button></>}><div className="space-y-3"><div className="flex items-center justify-between rounded-[10px] border border-blue-200 bg-blue-50 px-3 py-2 text-sm text-blue-900 dark:border-blue-900/60 dark:bg-blue-950/30 dark:text-blue-100"><span className="flex items-center gap-2"><FileText size={16} aria-hidden="true" />Authenticated branded PDF preview</span><button type="button" aria-label="Close PDF preview" className="rounded-md p-1 hover:bg-blue-100 focus:outline-none focus:ring-2 focus:ring-blue-600" onClick={onClose}><X size={16} aria-hidden="true" /></button></div>{watermark && <div className="rounded-[10px] border border-amber-300 bg-amber-50 px-4 py-3 text-sm font-bold text-amber-950" role="status">This loan is {watermark}. The PDF carries a {watermark} watermark.</div>}{preview && <div className="relative overflow-hidden rounded-[10px] border bg-slate-100"><iframe title={`${title} PDF`} src={preview.objectUrl} className="min-h-[65vh] w-full" />{watermark && <div className="pointer-events-none absolute inset-0 flex items-center justify-center"><span className="rotate-[-28deg] select-none text-[clamp(3rem,10vw,8rem)] font-black tracking-[0.18em] text-red-600/15">{watermark}</span></div>}</div>}</div></Modal>
}

export function LoanDocumentsPanel({ loan, canPrint }: { loan: LoanDetail; canPrint: boolean }) {
  const [records, setRecords] = useState<LoanDocumentRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [rendering, setRendering] = useState<PrintType | null>(null)
  const [downloading, setDownloading] = useState(false)
  const [error, setError] = useState<unknown>(null)
  const [previewError, setPreviewError] = useState<unknown>(null)
  const [preview, setPreview] = useState<AuthenticatedDocumentResult | null>(null)
  const [previewRecord, setPreviewRecord] = useState<LoanDocumentRecord | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const query = new URLSearchParams({ source_type: "ol_loans.olloan", object_id: loan.id, page_size: "50" })
      const payload = await request<LoanDocumentsPayload>(`/api/v1/documents/instances/?${query.toString()}`)
      setRecords((payload.results ?? []).filter(isRecord).map(normalizeRecord))
    } catch (caught) {
      setError(caught)
    } finally {
      setLoading(false)
    }
  }, [loan.id])

  useEffect(() => { void load() }, [load])
  useEffect(() => () => revokeAuthenticatedDocument(preview), [preview])

  const openPreview = async (record: LoanDocumentRecord) => {
    const url = documentUrl(record)
    if (!url) {
      setPreviewError(new Error("This loan document has no secure PDF URL. Generate it again or contact ZIC Finance."))
      return
    }
    setPreviewError(null)
    revokeAuthenticatedDocument(preview)
    try {
      const result = await fetchAuthenticatedDocument(url, "pdf")
      setPreview(result)
      setPreviewRecord(record)
    } catch (caught) {
      setPreviewError(caught)
    }
  }

  const generate = async (printType: PrintType) => {
    setRendering(printType)
    setError(null)
    try {
      const result = await printLoanDocument(loan.id, printType)
      const generated = normalizeRecord(result.instance)
      const url = result.signedDownloadUrl ?? result.previewUrl ?? result.previewBlobBase64OrUrl ?? documentUrl(generated)
      if (!url) throw new Error("The server did not return a secure PDF URL for this loan document.")
      const nextPreview = await fetchAuthenticatedDocument(url, "pdf")
      revokeAuthenticatedDocument(preview)
      setPreview(nextPreview)
      setPreviewRecord({ ...generated, documentType: generated.documentType || (printType === "agreement" ? "OL_LOAN_AGREEMENT" : "OL_LOAN_SCHEDULE"), signedDownloadUrl: result.signedDownloadUrl ?? generated.signedDownloadUrl, previewUrl: result.previewUrl ?? generated.previewUrl })
      await load()
    } catch (caught) {
      setError(caught)
    } finally {
      setRendering(null)
    }
  }

  const download = async () => {
    if (!previewRecord) return
    const url = documentUrl(previewRecord)
    if (!url) {
      setPreviewError(new Error("This loan document has no secure PDF URL."))
      return
    }
    setDownloading(true)
    setPreviewError(null)
    try {
      await openAuthenticatedDocument(url, { kind: "pdf", mode: "download", filename: `${loan.loanNumber}-${previewRecord.documentType.toLowerCase()}.pdf` })
    } catch (caught) {
      setPreviewError(caught)
    } finally {
      setDownloading(false)
    }
  }

  const openSigned = () => {
    if (previewRecord?.signedDownloadUrl) window.open(previewRecord.signedDownloadUrl, "_blank", "noopener,noreferrer")
    else setPreviewError(new Error("Open in New Tab is available only after the server issues a signed download ticket."))
  }

  const closePreview = () => {
    revokeAuthenticatedDocument(preview)
    setPreview(null)
    setPreviewRecord(null)
    setPreviewError(null)
  }

  const normalizedError = error ? errorProps(error) : null
  const normalizedPreviewError = previewError ? errorProps(previewError) : null
  const watermark = watermarkFor(String(loan.statusDisplay || loan.status))
  return <section className="surface-card overflow-hidden" aria-labelledby="loan-documents-heading" data-testid="loan-documents-panel"><header className="flex flex-wrap items-start justify-between gap-3 border-b px-5 py-4"><div><h2 id="loan-documents-heading" className="flex items-center gap-2 text-base font-bold"><FileText size={18} aria-hidden="true" />Documents</h2><p className="mt-1 text-sm text-[var(--muted-foreground)]">Loan agreements and repayment schedules retain their source loan and approved template version.</p></div><div className="flex flex-wrap gap-2"><button type="button" className="button-secondary inline-flex items-center gap-2" onClick={() => void load()} disabled={loading || Boolean(rendering)}><RefreshCw size={15} className={loading ? "animate-spin" : ""} aria-hidden="true" />Refresh</button>{canPrint && <><button type="button" className="button-primary inline-flex items-center gap-2" onClick={() => void generate("agreement")} disabled={Boolean(rendering)}><FileText size={15} aria-hidden="true" />{rendering === "agreement" ? "Generating…" : "Print Agreement"}</button><button type="button" className="button-primary inline-flex items-center gap-2" onClick={() => void generate("schedule")} disabled={Boolean(rendering)}><FileText size={15} aria-hidden="true" />{rendering === "schedule" ? "Generating…" : "Print Schedule"}</button></>}</div></header><div className="p-5">{normalizedError && <ErrorCoach title={normalizedError.message.includes("template") ? "Loan document template pending" : "Loan document could not be generated"} message={normalizedError.message} resolutionSteps={normalizedError.resolutionSteps} loginUrl={normalizedError.loginUrl} actionLabel={normalizedError.actionLabel} />}{watermark && <InfoBanner title={`${watermark} loan document watermark`}><p>The generated agreement and schedule carry a visible <strong>{watermark}</strong> status watermark.</p></InfoBanner>}{loading ? <div className="flex items-center gap-2 py-8 text-sm text-[var(--muted-foreground)]" role="status"><LoaderCircle size={16} className="animate-spin" aria-hidden="true" />Loading generated loan documents…</div> : records.length === 0 ? <p className="py-8 text-sm text-[var(--muted-foreground)]">No generated loan documents yet. Use Print Agreement or Print Schedule to create one.</p> : <div className="overflow-x-auto"><table className="w-full min-w-[900px] text-left text-sm"><caption className="sr-only">Generated loan documents</caption><thead><tr className="border-b text-xs uppercase tracking-wide text-[var(--muted-foreground)]"><th className="px-3 py-3">Document</th><th className="px-3 py-3">Template</th><th className="px-3 py-3">Version</th><th className="px-3 py-3">Generated by</th><th className="px-3 py-3">Generated at</th><th className="px-3 py-3">Pages</th><th className="px-3 py-3 text-right">Actions</th></tr></thead><tbody>{records.map((record) => <tr key={record.id || `${record.documentType}-${record.generatedAt}`} className="border-b last:border-0 hover:bg-[var(--muted)]/35"><td className="px-3 py-3 font-semibold">{documentLabel(record.documentType)}</td><td className="px-3 py-3">{record.templateName}</td><td className="px-3 py-3">v{record.templateVersion}</td><td className="px-3 py-3">{record.generatedByDisplay}</td><td className="px-3 py-3">{formatDate(record.generatedAt)}</td><td className="px-3 py-3">{record.pageCount}</td><td className="px-3 py-3"><div className="flex flex-wrap justify-end gap-2"><button type="button" className="button-secondary inline-flex items-center gap-1" onClick={() => void openPreview(record)}>Preview</button><button type="button" className="button-secondary inline-flex items-center gap-1" onClick={() => { setPreviewRecord(record); void openPreview(record) }}><Download size={14} aria-hidden="true" />Download</button>{record.signedDownloadUrl && <button type="button" className="button-secondary inline-flex items-center gap-1" onClick={() => { setPreviewRecord(record); openSigned() }}><ExternalLink size={14} aria-hidden="true" />Open in New Tab</button>}</div></td></tr>)}</tbody></table></div>}{normalizedPreviewError && <div className="mt-4"><ErrorCoach title="Loan document preview unavailable" message={normalizedPreviewError.message} resolutionSteps={normalizedPreviewError.resolutionSteps} loginUrl={normalizedPreviewError.loginUrl} actionLabel={normalizedPreviewError.actionLabel} /></div>}</div><PreviewModal preview={preview} title={previewRecord ? documentLabel(previewRecord.documentType) : "Loan document"} watermark={watermark} onClose={closePreview} onDownload={() => void download()} onOpenSigned={openSigned} downloading={downloading} /></section>
}
