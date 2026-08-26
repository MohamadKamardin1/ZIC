import { Download, ExternalLink, FileText, Loader2 } from "lucide-react"
import { useEffect, useState } from "react"
import { ErrorCoach } from "../../components/commitments/ErrorCoach"
import { Modal } from "../../components/ui/Overlays"
import { AuthenticatedDocumentError, fetchAuthenticatedDocument, openAuthenticatedDocument, revokeAuthenticatedDocument, type AuthenticatedDocumentResult } from "../../lib/documentClient"
import { usePrintProposalMutation } from "../../lib/proposalsHooks"

/**
 * Print preview modal: generates the summary printout through the unified
 * documents engine, fetches the PDF through the authenticated document client,
 * and only permits a new tab when the API issued a signed ticket URL.
 */
export function OLPrintPreviewModal({
  open,
  proposalId,
  onClose,
  onError,
}: {
  open: boolean
  proposalId: string
  onClose: () => void
  onError: (error: unknown) => void
}) {
  const print = usePrintProposalMutation()
  const [preview, setPreview] = useState<AuthenticatedDocumentResult | null>(null)
  const [previewError, setPreviewError] = useState<unknown>(null)
  const document = print.data ?? null

  useEffect(() => {
    if (!open) return
    let cancelled = false
    const load = async () => {
      setPreviewError(null)
      revokeAuthenticatedDocument(preview)
      setPreview(null)
      try {
        const nextDocument = await print.mutateAsync(proposalId)
        const url = nextDocument.signedDownloadUrl ?? nextDocument.pdfUrl
        if (!url) throw new Error("The proposal print service did not return a secure PDF URL. Generate the document again or contact System Administration.")
        const result = await fetchAuthenticatedDocument(url, "pdf")
        if (cancelled) {
          revokeAuthenticatedDocument(result)
          return
        }
        setPreview(result)
      } catch (caught) {
        if (!cancelled) {
          setPreviewError(caught)
          onError(caught)
        }
      }
    }
    void load()
    return () => {
      cancelled = true
      revokeAuthenticatedDocument(preview)
    }
  }, [open, proposalId])

  useEffect(() => () => revokeAuthenticatedDocument(preview), [preview])

  const close = () => {
    revokeAuthenticatedDocument(preview)
    setPreview(null)
    setPreviewError(null)
    print.reset()
    onClose()
  }

  const download = async () => {
    const url = document?.signedDownloadUrl ?? document?.pdfUrl
    if (!url) return
    try {
      await openAuthenticatedDocument(url, { kind: "pdf", mode: "download", filename: `proposal-${proposalId}.pdf` })
    } catch (caught) {
      setPreviewError(caught)
      onError(caught)
    }
  }

  const openSignedTicket = () => {
    if (document?.signedDownloadUrl) window.open(document.signedDownloadUrl, "_blank", "noopener,noreferrer")
  }

  const documentError = print.error ?? previewError
  return (
    <Modal
      open={open}
      title="Print preview — proposal summary"
      description="A durable PDF and HTML copy are stored against this proposal."
      onClose={close}
      size="xl"
      footer={
        <>
          <button type="button" className="button-secondary" onClick={close}>
            Close
          </button>
          <button
            type="button"
            className="button-primary inline-flex items-center gap-2 disabled:cursor-not-allowed disabled:opacity-60"
            onClick={() => void download()}
            disabled={!document || !(document.signedDownloadUrl ?? document.pdfUrl) || Boolean(print.isPending)}
            data-testid="print-download-pdf"
          >
            <Download size={15} aria-hidden="true" />
            Download PDF
          </button>
          <button
            type="button"
            className="button-secondary inline-flex items-center gap-2 disabled:cursor-not-allowed disabled:opacity-60"
            onClick={openSignedTicket}
            disabled={!document?.signedDownloadUrl || Boolean(print.isPending)}
          >
            <ExternalLink size={15} aria-hidden="true" />
            Open in New Tab
          </button>
        </>
      }
    >
      <div className="space-y-3">
        {print.isPending && <div className="flex h-72 items-center justify-center gap-2 rounded-[10px] bg-[var(--muted)] text-sm" aria-busy="true" data-testid="print-loading"><Loader2 size={16} className="animate-spin" aria-hidden="true" />Generating and loading authenticated PDF…</div>}
        {Boolean(documentError) && (
          <ErrorCoach error={documentError} title="The printout could not be generated or opened" compact onRetry={() => void print.mutateAsync(proposalId)} />
        )}
        {document && (
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-[var(--muted-foreground)]" data-testid="print-metadata">
            <span className="flex items-center gap-1 font-bold text-[var(--foreground)]">
              <FileText size={13} aria-hidden="true" />
              {document.documentType}
            </span>
            {document.templateCode && <span>Template <strong className="text-[var(--foreground)]">{document.templateCode}</strong> v{document.templateVersion ?? "?"}</span>}
            {document.sourceVersion != null && <span>Quotation version {document.sourceVersion}</span>}
            <span>Status {document.status}</span>
          </div>
        )}
        {preview ? (
          <iframe src={preview.objectUrl} title="Print preview" className="h-[65vh] w-full rounded-[10px] border border-[var(--border)] bg-white" data-testid="print-preview-frame" />
        ) : !print.isPending && !documentError ? (
          <p className="rounded-[10px] border border-dashed border-[var(--border)] px-4 py-6 text-center text-sm text-[var(--muted-foreground)]">Inline preview unavailable — generate the document again.</p>
        ) : null}
      </div>
    </Modal>
  )
}

export default OLPrintPreviewModal
