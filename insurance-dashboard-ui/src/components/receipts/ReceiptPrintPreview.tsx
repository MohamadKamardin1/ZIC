import { useQuery } from "@tanstack/react-query"
import { Download, ExternalLink, FileText, LoaderCircle, RefreshCw, X } from "lucide-react"
import { useEffect, useState } from "react"
import { ErrorCoach } from "../../components/ErrorCoach"
import { InfoBanner, Modal } from "../../components/ui/Overlays"
import { ApiClientError } from "../../lib/apiClient"
import { fetchAuthenticatedDocument, openAuthenticatedDocument, revokeAuthenticatedDocument, AuthenticatedDocumentError, type AuthenticatedDocumentResult } from "../../lib/documentClient"
import { receiptsApi, type ReceiptDocument, type ReceiptRecord } from "../../lib/receipts-api"

function errorProps(error: unknown) {
  if (error instanceof AuthenticatedDocumentError) return { message: error.message, loginUrl: error.requiresLogin ? error.loginUrl : undefined, actionLabel: error.requiresLogin ? "Sign in again" : undefined }
  if (error instanceof ApiClientError) {
    const settingsError = ["TEMPLATE_PENDING", "PARAMETER_MISSING", "BRANDING_NOT_CONFIGURED"].includes(error.code ?? "")
    return { message: settingsError ? `${error.message} Configure receipt document branding in System Parameters, then try again.` : error.message, resolutionSteps: error.resolutionSteps, loginUrl: settingsError ? "/system-parameters/documents/branding" : error.deepLink, actionLabel: settingsError ? "Open branding settings" : error.deepLink ? "Open resolution page" : undefined }
  }
  return { message: error instanceof Error ? error.message : "The receipt document action could not be completed." }
}

function dateLabel(value: string): string {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString()
}

function documentUrl(document: ReceiptDocument): string | null {
  return document.signed_download_url ?? document.download_url ?? document.preview_url ?? null
}

function statusWatermark(status: string): string | null {
  const normalized = status.toUpperCase()
  return normalized === "REVERSED" || normalized === "CANCELLED" ? normalized : null
}

export interface ReceiptPrintPreviewModalProps {
  open: boolean
  receipt: ReceiptRecord
  document?: ReceiptDocument | null
  onClose: () => void
  onGenerated?: () => void
}

export function ReceiptPrintPreviewModal({ open, receipt, document: initialDocument = null, onClose, onGenerated }: ReceiptPrintPreviewModalProps) {
  const [document, setDocument] = useState<ReceiptDocument | null>(initialDocument)
  const [preview, setPreview] = useState<AuthenticatedDocumentResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [downloadBusy, setDownloadBusy] = useState(false)
  const [error, setError] = useState<unknown>(null)

  useEffect(() => {
    if (!open) return
    let cancelled = false
    const load = async () => {
      setLoading(true)
      setError(null)
      revokeAuthenticatedDocument(preview)
      setPreview(null)
      try {
        const nextDocument = initialDocument ?? (await receiptsApi.print(receipt.id)).document
        if (cancelled) return
        setDocument(nextDocument)
        const url = documentUrl(nextDocument)
        if (!url) throw new Error("The server did not return a secure PDF URL for this receipt.")
        const result = await fetchAuthenticatedDocument(url, "pdf")
        if (cancelled) {
          revokeAuthenticatedDocument(result)
          return
        }
        setPreview(result)
        if (!initialDocument) onGenerated?.()
      } catch (caught) {
        if (!cancelled) setError(caught)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    void load()
    return () => { cancelled = true }
  }, [open, receipt.id, initialDocument])

  useEffect(() => () => revokeAuthenticatedDocument(preview), [preview])

  const download = async () => {
    if (!document) return
    const url = documentUrl(document)
    if (!url) return
    setDownloadBusy(true)
    setError(null)
    try {
      await openAuthenticatedDocument(url, { kind: "pdf", mode: "download", filename: `${receipt.receipt_number}.pdf` })
    } catch (caught) {
      setError(caught)
    } finally {
      setDownloadBusy(false)
    }
  }

  const openSignedTicket = () => {
    if (document?.signed_download_url) window.open(document.signed_download_url, "_blank", "noopener,noreferrer")
  }

  const close = () => {
    revokeAuthenticatedDocument(preview)
    setPreview(null)
    setDocument(null)
    setError(null)
    onClose()
  }

  const normalizedError = error ? errorProps(error) : null
  const watermark = statusWatermark(receipt.status)
  return <Modal open={open} title={`${receipt.receipt_number} · Receipt PDF`} description="Authenticated branded receipt preview. The PDF is fetched through the secure document client." onClose={close} size="xl" footer={<><button type="button" className="button-secondary inline-flex items-center gap-2" onClick={() => void download()} disabled={!document || loading || downloadBusy}>{downloadBusy ? <LoaderCircle size={15} className="animate-spin" aria-hidden="true" /> : <Download size={15} aria-hidden="true" />}{downloadBusy ? "Downloading…" : "Download"}</button><button type="button" className="button-secondary inline-flex items-center gap-2" onClick={openSignedTicket} disabled={!document?.signed_download_url || loading}><ExternalLink size={15} aria-hidden="true" />Open in New Tab</button><button type="button" className="button-primary" onClick={close}>Close</button></>}>
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-[10px] border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-950 dark:border-blue-900/60 dark:bg-blue-950/30 dark:text-blue-100"><span className="flex items-center gap-2"><FileText size={16} aria-hidden="true" />Secure preview · {document?.template_name ?? "Generating receipt document…"}{document ? ` · v${document.template_version}` : ""}</span><button type="button" aria-label="Close PDF preview" className="rounded-md p-1 hover:bg-blue-100 focus:outline-none focus:ring-2 focus:ring-blue-600" onClick={close}><X size={16} aria-hidden="true" /></button></div>
      {watermark && <div className="rounded-[10px] border border-amber-300 bg-amber-50 px-4 py-3 text-sm font-bold text-amber-950" role="status">This receipt is {watermark}. The branded PDF carries a {watermark} watermark.</div>}
      {loading && <div className="flex min-h-[60vh] items-center justify-center gap-2 rounded-[10px] border bg-[var(--muted)]/20 text-sm text-[var(--muted-foreground)]" role="status"><LoaderCircle size={18} className="animate-spin" aria-hidden="true" />Generating and loading authenticated PDF…</div>}
      {normalizedError && <ErrorCoach title="Receipt document could not be opened" message={normalizedError.message} resolutionSteps={normalizedError.resolutionSteps} loginUrl={normalizedError.loginUrl} actionLabel={normalizedError.actionLabel} />}
      {!loading && !normalizedError && preview && <div className="relative overflow-hidden rounded-[10px] border bg-slate-100"><iframe title={`${receipt.receipt_number} branded PDF`} src={preview.objectUrl} className="min-h-[65vh] w-full" />{watermark && <div className="pointer-events-none absolute inset-0 flex items-center justify-center"><span className="rotate-[-28deg] select-none text-[clamp(3rem,10vw,8rem)] font-black tracking-[0.18em] text-red-600/15">{watermark}</span></div>}</div>}
      {!loading && !normalizedError && !preview && <InfoBanner title="Preview unavailable"><p>Generate the receipt again or close this dialog and review the Documents tab.</p></InfoBanner>}
    </div>
  </Modal>
}

export interface ReceiptDocumentsPanelProps {
  receipt: ReceiptRecord
  refreshKey?: number
  canPrint: boolean
  onGenerate: () => void
  onPreview: (document: ReceiptDocument) => void
}

export function ReceiptDocumentsPanel({ receipt, refreshKey = 0, canPrint, onGenerate, onPreview }: ReceiptDocumentsPanelProps) {
  const [actionError, setActionError] = useState<unknown>(null)
  const documentsQuery = useQuery({ queryKey: ["receipts", "detail", receipt.id, "documents", refreshKey], queryFn: () => receiptsApi.documents(receipt.id), retry: false })

  const download = async (document: ReceiptDocument) => {
    const url = documentUrl(document)
    if (!url) {
      setActionError(new Error("This document has no secure PDF URL."))
      return
    }
    setActionError(null)
    try {
      await openAuthenticatedDocument(url, { kind: "pdf", mode: "download", filename: `${receipt.receipt_number}.pdf` })
    } catch (caught) {
      setActionError(caught)
    }
  }

  const normalizedError = actionError ? errorProps(actionError) : null
  return <section className="surface-card overflow-hidden" aria-labelledby="documents-heading"><div className="flex flex-wrap items-start justify-between gap-3 border-b px-5 py-4"><div><h2 id="documents-heading" className="flex items-center gap-2 font-bold"><FileText size={17} aria-hidden="true" />Documents</h2><p className="mt-1 text-sm text-[var(--muted-foreground)]">Generated receipt PDFs retain their template version and source transaction.</p></div><div className="flex flex-wrap gap-2"><button type="button" className="button-secondary inline-flex items-center gap-2" onClick={() => void documentsQuery.refetch()} disabled={documentsQuery.isFetching}><RefreshCw size={14} className={documentsQuery.isFetching ? "animate-spin" : ""} aria-hidden="true" />Refresh</button>{canPrint && <button type="button" className="button-primary inline-flex items-center gap-2" onClick={onGenerate}><FileText size={14} aria-hidden="true" />Generate receipt PDF</button>}</div></div><div className="p-5">{documentsQuery.isLoading && <div className="flex items-center gap-2 py-8 text-sm text-[var(--muted-foreground)]" role="status"><LoaderCircle size={16} className="animate-spin" aria-hidden="true" />Loading generated documents…</div>}{documentsQuery.isError && <ErrorCoach title="Receipt documents could not be loaded" {...errorProps(documentsQuery.error)} />}{normalizedError && <ErrorCoach title="Receipt download failed" message={normalizedError.message} resolutionSteps={normalizedError.resolutionSteps} loginUrl={normalizedError.loginUrl} actionLabel={normalizedError.actionLabel} />}{!documentsQuery.isLoading && !documentsQuery.isError && !documentsQuery.data?.results.length && <InfoBanner title="No generated printouts"><p>{canPrint ? "Use Generate receipt PDF to create the first branded receipt document." : "No generated receipt PDF is available. Ask for front_office.receipts.print access to generate one."}</p></InfoBanner>}{!documentsQuery.isLoading && !documentsQuery.isError && Boolean(documentsQuery.data?.results.length) && <div className="overflow-x-auto"><table className="w-full min-w-[760px] text-left text-sm"><caption className="sr-only">Generated receipt documents</caption><thead><tr className="border-b text-xs uppercase tracking-wide text-[var(--muted-foreground)]"><th className="px-3 py-3">Template</th><th className="px-3 py-3">Version</th><th className="px-3 py-3">Generated by</th><th className="px-3 py-3">Generated at</th><th className="px-3 py-3">Pages</th><th className="px-3 py-3 text-right">Actions</th></tr></thead><tbody>{documentsQuery.data?.results.map((record) => <tr key={record.id} className="border-b last:border-0 hover:bg-[var(--muted)]/35"><td className="px-3 py-3 font-semibold">{record.template_name}</td><td className="px-3 py-3">v{record.template_version}</td><td className="px-3 py-3">{record.generated_by_display}</td><td className="px-3 py-3">{dateLabel(record.generated_at)}</td><td className="px-3 py-3">{record.page_count}</td><td className="px-3 py-3"><div className="flex flex-wrap justify-end gap-2"><button type="button" className="button-secondary inline-flex items-center gap-1" onClick={() => onPreview(record)}>Preview</button><button type="button" className="button-secondary inline-flex items-center gap-1" onClick={() => void download(record)}><Download size={14} aria-hidden="true" />Download</button>{record.signed_download_url && <button type="button" className="button-secondary inline-flex items-center gap-1" onClick={() => window.open(record.signed_download_url ?? "", "_blank", "noopener,noreferrer")}><ExternalLink size={14} aria-hidden="true" />Open in new tab</button>}</div></td></tr>)}</tbody></table></div>}</div></section>
}
