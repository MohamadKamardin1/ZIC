import { useEffect, useState } from "react"
import { Download, ExternalLink, FileText, Loader2 } from "lucide-react"
import { ErrorCoach } from "../../components/commitments/ErrorCoach"
import { Modal } from "../../components/ui/Overlays"
import { AuthenticatedDocumentError, fetchAuthenticatedDocument, openAuthenticatedDocument, revokeAuthenticatedDocument, type AuthenticatedDocumentResult } from "../../lib/documentClient"
import { usePrintPolicyContractMutation } from "../../lib/policiesHooks"
import type { PolicyDetail } from "../../lib/policies"

function recordValue(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {}
}

export default function PolicyPrintPreviewModal({ open, policy, onClose }: { open: boolean; policy: PolicyDetail; onClose: () => void }) {
  const print = usePrintPolicyContractMutation()
  const [preview, setPreview] = useState<AuthenticatedDocumentResult | null>(null)
  const [previewError, setPreviewError] = useState<unknown>(null)
  const document = print.data ?? null
  const cancelled = policy.status.toUpperCase() === "CANCELLED"

  useEffect(() => {
    if (!open) return undefined
    let disposed = false
    const load = async () => {
      setPreviewError(null)
      revokeAuthenticatedDocument(preview)
      setPreview(null)
      try {
        const generated = await print.mutateAsync(policy.id)
        const generatedRecord = recordValue(generated)
        const url = generated.signedDownloadUrl ?? generated.previewUrl ?? String(generatedRecord.signed_download_url ?? generatedRecord.preview_url ?? "")
        if (!url) throw new AuthenticatedDocumentError("The policy print service did not return a secure PDF URL. Generate the document again or contact System Administration.")
        const result = await fetchAuthenticatedDocument(url, "pdf")
        if (disposed) {
          revokeAuthenticatedDocument(result)
          return
        }
        setPreview(result)
      } catch (caught) {
        if (!disposed) setPreviewError(caught)
      }
    }
    void load()
    return () => {
      disposed = true
      revokeAuthenticatedDocument(preview)
    }
  }, [open, policy.id])

  useEffect(() => () => revokeAuthenticatedDocument(preview), [preview])

  const close = () => {
    revokeAuthenticatedDocument(preview)
    setPreview(null)
    setPreviewError(null)
    print.reset()
    onClose()
  }

  const documentUrl = document?.signedDownloadUrl ?? document?.previewUrl
  const download = async () => {
    if (!documentUrl) return
    try {
      await openAuthenticatedDocument(documentUrl, { kind: "pdf", mode: "download", filename: `${policy.policyNumber}-contract.pdf` })
    } catch (caught) {
      setPreviewError(caught)
    }
  }

  const openSignedTicket = () => {
    if (document?.signedDownloadUrl) window.open(document.signedDownloadUrl, "_blank", "noopener,noreferrer")
  }

  const documentRecord = recordValue(document?.instance)
  const documentType = String(documentRecord.document_type ?? documentRecord.documentType ?? "POLICY_CONTRACT")
  const templateName = String(documentRecord.template_name ?? documentRecord.templateName ?? "Policy Contract")
  const templateVersion = documentRecord.template_version ?? documentRecord.templateVersion
  const documentError = print.error ?? previewError

  return <Modal open={open} title="Print preview — policy contract" description="The contract is generated through the authenticated policy print pipeline and stored against this policy." onClose={close} size="xl" footer={<><button type="button" className="button-secondary" onClick={close}>Close</button><button type="button" className="button-primary inline-flex items-center gap-2 disabled:cursor-not-allowed disabled:opacity-60" onClick={() => void download()} disabled={!documentUrl || print.isPending} data-testid="policy-print-download"><Download size={15} aria-hidden="true" />Download PDF</button><button type="button" className="button-secondary inline-flex items-center gap-2 disabled:cursor-not-allowed disabled:opacity-60" onClick={openSignedTicket} disabled={!document?.signedDownloadUrl || print.isPending}><ExternalLink size={15} aria-hidden="true" />Open in New Tab</button></>}>
    <div className="space-y-3">
      {print.isPending && <div className="flex h-72 items-center justify-center gap-2 rounded-[10px] bg-[var(--muted)] text-sm" aria-busy="true" data-testid="policy-print-loading"><Loader2 size={16} className="animate-spin" aria-hidden="true" />Generating and loading authenticated PDF…</div>}
      {Boolean(documentError) && <ErrorCoach error={documentError} title="The policy contract could not be generated or opened" compact onRetry={() => void print.mutateAsync(policy.id)} />}
      {document && <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-[var(--muted-foreground)]" data-testid="policy-print-metadata"><span className="flex items-center gap-1 font-bold text-[var(--foreground)]"><FileText size={13} aria-hidden="true" />{documentType}</span><span>Template <strong className="text-[var(--foreground)]">{templateName}</strong>{templateVersion == null ? "" : ` v${String(templateVersion)}`}</span><span>Policy <strong className="text-[var(--foreground)]">{policy.policyNumber}</strong></span></div>}
      {preview ? <div className="relative"><iframe src={preview.objectUrl} title="Policy contract PDF preview" className="h-[65vh] w-full rounded-[10px] border border-[var(--border)] bg-white" data-testid="policy-print-preview-frame" />{cancelled && <div className="pointer-events-none absolute inset-0 flex items-center justify-center overflow-hidden" aria-label="Cancelled policy watermark"><span className="rotate-[-24deg] text-[clamp(3rem,12vw,9rem)] font-black tracking-[0.25em] text-red-600/25">CANCELLED</span></div>}</div> : !print.isPending && !documentError ? <p className="rounded-[10px] border border-dashed border-[var(--border)] px-4 py-6 text-center text-sm text-[var(--muted-foreground)]">Inline preview unavailable — generate the policy contract again.</p> : null}
    </div>
  </Modal>
}
