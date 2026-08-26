import { useCallback, useEffect, useState } from "react"
import { Download, ExternalLink, FileText, Loader2, RefreshCw, X } from "lucide-react"
import { request, ApiClientError } from "../../lib/apiClient"
import {
  AuthenticatedDocumentError,
  fetchAuthenticatedDocument,
  openAuthenticatedDocument,
  revokeAuthenticatedDocument,
  type AuthenticatedDocumentResult,
} from "../../lib/documentClient"
import { ErrorCoach } from "../ErrorCoach"
import { Modal } from "../ui/Overlays"

export interface DocumentInstanceRecord {
  id: string
  document_type: string
  template_name: string
  template_version: number
  generated_by_display: string
  generated_at: string
  page_count: number
  preview_url?: string | null
  download_url?: string | null
  signed_download_url?: string | null
  source_display?: string
}

interface DocumentInstancesPayload {
  count: number
  page: number
  page_size: number
  results: DocumentInstanceRecord[]
}

interface DocumentPreviewModalProps {
  result: AuthenticatedDocumentResult | null
  title: string
  onClose: () => void
}

export function DocumentPreviewModal({ result, title, onClose }: DocumentPreviewModalProps) {
  return (
    <Modal open={Boolean(result)} title={title} onClose={onClose} size="xl">
      <div className="flex min-h-[65vh] flex-col gap-3">
        <div className="flex items-center justify-between rounded-[10px] border border-blue-200 bg-blue-50 px-3 py-2 text-sm text-blue-900 dark:border-blue-900/60 dark:bg-blue-950/30 dark:text-blue-100">
          <span>Authenticated PDF preview. The document is loaded through the secure document client.</span>
          <button type="button" aria-label="Close PDF preview" className="rounded-md p-1 hover:bg-blue-100 focus:outline-none focus:ring-2 focus:ring-blue-600" onClick={onClose}>
            <X size={16} aria-hidden="true" />
          </button>
        </div>
        {result && <iframe title={`${title} PDF`} src={result.objectUrl} className="min-h-[60vh] w-full flex-1 rounded-[10px] border bg-slate-100" />}
      </div>
    </Modal>
  )
}

export interface DocumentInstancesPanelProps {
  sourceType: string
  objectId: string
  documentType: string
  title?: string
  description?: string
  renderLabel?: string
  className?: string
}

function asErrorMessage(error: unknown): { message: string; code?: string; loginUrl?: string; settingsUrl?: string } {
  if (error instanceof AuthenticatedDocumentError) {
    return { message: error.message, loginUrl: error.requiresLogin ? error.loginUrl : undefined }
  }
  if (error instanceof ApiClientError) {
    if (error.code === "TEMPLATE_PENDING" || error.code === "PARAMETER_MISSING" || error.code === "BRANDING_NOT_CONFIGURED") {
      return {
        message: `${error.message} Configure document branding in System Parameters, then try again.`,
        code: error.code,
        settingsUrl: "/system-parameters/documents/branding",
      }
    }
    return { message: error.message, code: error.code }
  }
  return { message: error instanceof Error ? error.message : "The document action could not be completed." }
}

function messageForError(error: unknown): string {
  return asErrorMessage(error).message
}

function dateLabel(value: string): string {
  if (!value) return "—"
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString()
}

export function DocumentInstancesPanel({
  sourceType,
  objectId,
  documentType,
  title = "Documents",
  description = "Generated documents retain their source transaction and approved template version.",
  renderLabel = "Generate document",
  className = "",
}: DocumentInstancesPanelProps) {
  const [records, setRecords] = useState<DocumentInstanceRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [rendering, setRendering] = useState(false)
  const [error, setError] = useState<unknown>(null)
  const [previewError, setPreviewError] = useState<unknown>(null)
  const [preview, setPreview] = useState<AuthenticatedDocumentResult | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const query = new URLSearchParams({ source_type: sourceType, object_id: objectId, page_size: "50" })
      const payload = await request<DocumentInstancesPayload>(`/api/v1/documents/instances/?${query.toString()}`)
      setRecords(payload.results ?? [])
    } catch (caught) {
      setError(caught)
    } finally {
      setLoading(false)
    }
  }, [objectId, sourceType])

  useEffect(() => {
    void load()
  }, [load])

  useEffect(() => () => revokeAuthenticatedDocument(preview), [preview])

  const renderDocument = async () => {
    setRendering(true)
    setError(null)
    try {
      await request<DocumentInstanceRecord>(`/api/v1/documents/render/${encodeURIComponent(documentType)}/${encodeURIComponent(objectId)}/`, { method: "POST", body: JSON.stringify({}) })
      await load()
    } catch (caught) {
      setError(caught)
    } finally {
      setRendering(false)
    }
  }

  const previewDocument = async (record: DocumentInstanceRecord) => {
    const url = record.signed_download_url ?? record.download_url
    if (!url) {
      setPreviewError(new Error("This document has no secure PDF download URL."))
      return
    }
    setPreviewError(null)
    revokeAuthenticatedDocument(preview)
    try {
      const result = await fetchAuthenticatedDocument(url, "pdf")
      setPreview(result)
    } catch (caught) {
      setPreviewError(caught)
    }
  }

  const downloadDocument = async (record: DocumentInstanceRecord) => {
    const url = record.signed_download_url ?? record.download_url
    if (!url) {
      setError(new Error("This document has no secure PDF download URL."))
      return
    }
    try {
      await openAuthenticatedDocument(url, { kind: "pdf", mode: "download", filename: `${record.document_type.toLowerCase()}-${record.id}.pdf` })
    } catch (caught) {
      setError(caught)
    }
  }

  const openSignedTicket = (record: DocumentInstanceRecord) => {
    if (record.signed_download_url) {
      // This is intentionally the only direct new-tab navigation. The URL is a
      // short-lived, single-purpose signed ticket returned by the API.
      window.open(record.signed_download_url, "_blank", "noopener,noreferrer")
    } else {
      setError(new Error("Open in new tab is unavailable until the server issues a signed ticket."))
    }
  }

  const normalizedError = error ? asErrorMessage(error) : null
  const normalizedPreviewError = previewError ? asErrorMessage(previewError) : null

  return (
    <section className={`rounded-[12px] border bg-[var(--card)] shadow-sm ${className}`} aria-labelledby="document-panel-title">
      <header className="flex flex-wrap items-start justify-between gap-3 border-b px-5 py-4">
        <div>
          <h2 id="document-panel-title" className="flex items-center gap-2 text-base font-bold"><FileText size={18} aria-hidden="true" />{title}</h2>
          <p className="mt-1 text-sm text-[var(--muted-foreground)]">{description}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button type="button" className="button-secondary inline-flex items-center gap-2" onClick={() => void load()} disabled={loading || rendering}><RefreshCw size={15} aria-hidden="true" />Refresh</button>
          <button type="button" className="button-primary inline-flex items-center gap-2" onClick={() => void renderDocument()} disabled={rendering}><FileText size={15} aria-hidden="true" />{rendering ? "Generating…" : renderLabel}</button>
        </div>
      </header>
      <div className="p-5">
        {normalizedError && <ErrorCoach title={normalizedError.code === "TEMPLATE_PENDING" ? "Document template pending" : undefined} message={normalizedError.message} loginUrl={normalizedError.loginUrl ?? normalizedError.settingsUrl} actionLabel={normalizedError.settingsUrl ? "Open branding settings" : undefined} />}
        {loading ? <div className="flex items-center gap-2 py-8 text-sm text-[var(--muted-foreground)]" role="status"><Loader2 size={16} className="animate-spin" aria-hidden="true" />Loading generated documents…</div> : records.length === 0 ? <p className="py-8 text-sm text-[var(--muted-foreground)]">No generated documents yet. Use “{renderLabel}” to create the first version.</p> : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px] text-left text-sm">
              <thead><tr className="border-b text-xs uppercase tracking-wide text-[var(--muted-foreground)]"><th className="px-3 py-3">Template</th><th className="px-3 py-3">Version</th><th className="px-3 py-3">Generated by</th><th className="px-3 py-3">Generated at</th><th className="px-3 py-3">Pages</th><th className="px-3 py-3 text-right">Actions</th></tr></thead>
              <tbody>{records.map((record) => <tr key={record.id} className="border-b last:border-0 hover:bg-[var(--muted)]/35"><td className="px-3 py-3 font-semibold">{record.template_name || "Document"}</td><td className="px-3 py-3">v{record.template_version}</td><td className="px-3 py-3">{record.generated_by_display || "System"}</td><td className="px-3 py-3">{dateLabel(record.generated_at)}</td><td className="px-3 py-3">{record.page_count}</td><td className="px-3 py-3"><div className="flex flex-wrap justify-end gap-2"><button type="button" className="button-secondary inline-flex items-center gap-1" onClick={() => void previewDocument(record)}>Preview</button><button type="button" className="button-secondary inline-flex items-center gap-1" onClick={() => void downloadDocument(record)}><Download size={14} aria-hidden="true" />Download</button>{record.signed_download_url && <button type="button" className="button-secondary inline-flex items-center gap-1" onClick={() => openSignedTicket(record)}><ExternalLink size={14} aria-hidden="true" />Open in new tab</button>}</div></td></tr>)}</tbody>
            </table>
          </div>
        )}
        {normalizedPreviewError && <div className="mt-4"><ErrorCoach message={normalizedPreviewError.message} loginUrl={normalizedPreviewError.loginUrl ?? normalizedPreviewError.settingsUrl} actionLabel={normalizedPreviewError.settingsUrl ? "Open branding settings" : undefined} /></div>}
      </div>
      <DocumentPreviewModal result={preview} title={title} onClose={() => { revokeAuthenticatedDocument(preview); setPreview(null) }} />
    </section>
  )
}
