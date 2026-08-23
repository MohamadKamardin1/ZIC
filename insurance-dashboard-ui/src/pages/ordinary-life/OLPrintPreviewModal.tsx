import { useEffect, useState } from "react"
import { Download, FileText } from "lucide-react"
import { ErrorCoach } from "../../components/commitments/ErrorCoach"
import { Modal } from "../../components/ui/Overlays"
import { usePrintProposalMutation } from "../../lib/proposalsHooks"

/**
 * Print preview modal: generates the summary printout (HTML + PDF), previews
 * the PDF inline and offers a download. Generation is durable — every run is
 * listed in the Generated Documents tab with template version and actor.
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
  const [pdfUrl, setPdfUrl] = useState<string | null>(null)

  const document = print.data ?? null

  const mutate = print.mutate
  useEffect(() => {
    if (open) mutate(proposalId)
  }, [open, proposalId, mutate])

  useEffect(() => {
    if (!open || !document?.pdfUrl) {
      setPdfUrl(null)
      return
    }
    let revoked = false
    let objectUrl: string | null = null
    const load = async () => {
      try {
        const response = await fetch(document.pdfUrl as string)
        if (!response.ok) throw new Error("The printout could not be downloaded.")
        const blob = await response.blob()
        objectUrl = URL.createObjectURL(blob)
        if (!revoked) setPdfUrl(objectUrl)
      } catch {
        if (!revoked) setPdfUrl(null)
      }
    }
    void load()
    return () => {
      revoked = true
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [open, document?.pdfUrl])

  const close = () => {
    print.reset()
    onClose()
  }

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
          <a
            href={pdfUrl ?? document?.pdfUrl ?? "#"}
            download={`proposal-${proposalId}.pdf`}
            data-testid="print-download-pdf"
            className={`button-primary ${!document ? "pointer-events-none opacity-60" : ""}`}
          >
            <Download size={15} aria-hidden="true" />
            Download PDF
          </a>
        </>
      }
    >
      <div className="space-y-3">
        {print.isPending && <div className="h-72 animate-pulse rounded-[10px] bg-[var(--muted)]" aria-busy="true" data-testid="print-loading" />}
        {print.isError && (
          <ErrorCoach error={print.error} title="The printout could not be generated" compact onRetry={() => print.mutate(proposalId)} />
        )}
        {document && (
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-[var(--muted-foreground)]" data-testid="print-metadata">
            <span className="flex items-center gap-1 font-bold text-[var(--foreground)]">
              <FileText size={13} aria-hidden="true" />
              {document.documentType}
            </span>
            {document.templateCode && (
              <span>
                Template <strong className="text-[var(--foreground)]">{document.templateCode}</strong> v{document.templateVersion ?? "?"}
              </span>
            )}
            {document.sourceVersion != null && <span>Quotation version {document.sourceVersion}</span>}
            <span>Status {document.status}</span>
          </div>
        )}
        {pdfUrl ? (
          <iframe
            src={pdfUrl}
            title="Print preview"
            className="h-72 w-full rounded-[10px] border border-[var(--border)] bg-white"
            data-testid="print-preview-frame"
          />
        ) : document ? (
          <p className="rounded-[10px] border border-dashed border-[var(--border)] px-4 py-6 text-center text-sm text-[var(--muted-foreground)]">
            Inline preview unavailable — use “Download PDF” to view the stored printout.
          </p>
        ) : null}
      </div>
    </Modal>
  )
}

export default OLPrintPreviewModal
