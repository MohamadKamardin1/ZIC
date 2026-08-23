import { useRef, useState } from "react"
import { AlertTriangle, CheckCircle2, CircleDashed, FileText, UploadCloud } from "lucide-react"
import { ErrorCoach } from "../../components/commitments/ErrorCoach"
import { SmartSelect } from "../../components/ui/SmartSelect"
import { Modal } from "../../components/ui/Overlays"
import { TextInput } from "../../components/ui/FormControls"
import { useToast } from "../../components/ui/Toast"
import { useProposalDocuments, useUploadDocumentMutation } from "../../lib/proposalsHooks"
import type { ProposalDetail, ProposalDocumentRecord, ProposalDocumentRequirement } from "../../lib/proposals"

const DOCUMENT_TYPES_OPTIONS_URL = "/api/v1/ol-proposals/options/document-types/"
const SATISFIED_STATUSES = new Set(["UPLOADED", "VERIFIED"])

function formatFileSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

/** Blocking banner listing each missing mandatory document (BR-12). */
function MissingMandatoryBanner({
  missing,
  onPick,
}: {
  missing: ProposalDocumentRequirement[]
  onPick: (requirement: ProposalDocumentRequirement) => void
}) {
  return (
    <div
      className="flex flex-col gap-3 rounded-[10px] border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-900 dark:border-red-900/60 dark:bg-red-950/35 dark:text-red-100"
      role="alert"
      data-testid="mandatory-documents-banner"
    >
      <div className="flex items-center gap-2 font-bold">
        <AlertTriangle size={16} aria-hidden="true" />
        Mandatory documents missing — payment readiness is blocked until these are uploaded.
      </div>
      <ul className="flex flex-wrap gap-2">
        {missing.map((requirement) => (
          <li key={requirement.code}>
            <button
              type="button"
              data-testid={`missing-document-${requirement.documentType}`}
              className="rounded-full border border-red-300 bg-white px-3 py-1 text-xs font-bold text-red-800 hover:bg-red-100 dark:border-red-800 dark:bg-transparent dark:text-red-100 dark:hover:bg-red-900/40"
              onClick={() => onPick(requirement)}
            >
              {requirement.name} · Upload
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}

/** Requirement checklist resolved for this proposal's product/plan scope. */
function RequirementsChecklist({
  requirements,
  uploads,
}: {
  requirements: ProposalDocumentRequirement[]
  uploads: ProposalDocumentRecord[]
}) {
  const uploadedByType = new Map<string, ProposalDocumentRecord>()
  for (const row of uploads) {
    if (SATISFIED_STATUSES.has(row.status.toUpperCase())) uploadedByType.set(row.documentType, row)
  }
  if (requirements.length === 0) return null

  const mandatoryMissing = requirements.filter((row) => row.mandatory && !uploadedByType.has(row.documentType)).length

  return (
    <section className="surface-card p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h2 className="font-bold">Required documents</h2>
        <span className="text-xs font-bold uppercase tracking-[0.08em] text-[var(--muted-foreground)]">
          {requirements.length - mandatoryMissing}/{requirements.length} satisfied
        </span>
      </div>
      <ul className="divide-y">
        {requirements.map((requirement) => {
          const uploaded = uploadedByType.get(requirement.documentType)
          return (
            <li key={requirement.code} className="flex items-center justify-between gap-3 py-2 text-sm" data-testid={`requirement-row-${requirement.documentType}`}>
              <span className="min-w-0 truncate font-semibold">
                {uploaded ? (
                  <CheckCircle2 size={15} className="mr-1.5 inline align-text-bottom text-green-600" aria-hidden="true" />
                ) : (
                  <CircleDashed size={15} className="mr-1.5 inline align-text-bottom text-[var(--muted-foreground)]" aria-hidden="true" />
                )}
                {requirement.name}
                <span
                  className={`ml-2 rounded-full px-1.5 py-0.5 text-[10px] font-bold ${
                    requirement.mandatory ? "bg-[var(--secondary)]" : "border border-[var(--border)] text-[var(--muted-foreground)]"
                  }`}
                >
                  {requirement.mandatory ? "Mandatory" : "Optional"}
                </span>
              </span>
              <span className="flex-none text-xs font-bold uppercase tracking-wide text-[var(--muted-foreground)]">
                {uploaded ? uploaded.status : "Not uploaded"}
              </span>
            </li>
          )
        })}
      </ul>
    </section>
  )
}

/** Upload modal with drag-and-drop, preview-before-save, and DMS reference fallback. */
export function OLDocumentUploadModal({
  open,
  proposalId,
  initialType,
  onClose,
  onError,
}: {
  open: boolean
  proposalId: string
  initialType?: string
  onClose: () => void
  onError: (error: unknown) => void
}) {
  const { toast } = useToast()
  const [documentType, setDocumentType] = useState(initialType ?? "")
  const [fileReference, setFileReference] = useState("")
  const [file, setFile] = useState<File | null>(null)
  const [dragActive, setDragActive] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const upload = useUploadDocumentMutation()

  const reset = () => {
    setFile(null)
    setFileReference("")
    setDragActive(false)
    if (inputRef.current) inputRef.current.value = ""
  }

  const close = () => {
    reset()
    onClose()
  }

  const takeFiles = (files: FileList | null) => {
    const picked = files?.[0]
    if (!picked) return
    setFile(picked)
    if (!fileReference.trim()) setFileReference(picked.name)
  }

  const submitUpload = () => {
    if (!documentType || !fileReference.trim()) return
    onError(null)
    upload.mutate(
      { id: proposalId, data: { document_type: documentType, file_reference: fileReference.trim() } },
      {
        onSuccess: () => {
          toast({ title: "Document uploaded", message: `${documentType} was attached to this proposal.`, tone: "success" })
          reset()
          onClose()
        },
        onError: (error) => onError(error),
      },
    )
  }

  return (
    <Modal
      open={open}
      title="Upload document"
      description="Attach a document to this proposal. Review the file details before saving."
      onClose={close}
      footer={
        <>
          <button type="button" className="button-secondary" onClick={close}>
            Cancel
          </button>
          <button
            type="button"
            className="button-primary"
            data-testid="upload-document"
            disabled={!documentType || !fileReference.trim() || upload.isPending}
            onClick={submitUpload}
          >
            {upload.isPending ? "Uploading…" : "Save document"}
          </button>
        </>
      }
    >
      <div className="space-y-4">
        <SmartSelect
          entity="document-types"
          label="Document type"
          name="upload_document_type"
          optionsUrl={DOCUMENT_TYPES_OPTIONS_URL}
          rememberLastUsed={false}
          value={documentType}
          onChange={setDocumentType}
          placeholder="Select document type"
        />

        <div
          data-testid="document-drop-zone"
          role="button"
          tabIndex={0}
          aria-label="Choose or drop a file"
          className={`flex cursor-pointer flex-col items-center gap-1 rounded-[10px] border border-dashed px-4 py-6 text-center text-sm transition-colors ${
            dragActive ? "border-blue-500 bg-blue-50 dark:bg-blue-950/30" : "border-[var(--border)] hover:border-blue-400"
          }`}
          onClick={() => inputRef.current?.click()}
          onKeyDown={(event) => {
            if (event.key === "Enter" || event.key === " ") {
              event.preventDefault()
              inputRef.current?.click()
            }
          }}
          onDragOver={(event) => {
            event.preventDefault()
            setDragActive(true)
          }}
          onDragLeave={() => setDragActive(false)}
          onDrop={(event) => {
            event.preventDefault()
            setDragActive(false)
            takeFiles(event.dataTransfer.files)
          }}
        >
          <UploadCloud size={22} className="text-[var(--muted-foreground)]" aria-hidden="true" />
          <span className="font-semibold">Drag a file here, or click to browse</span>
          <span className="text-xs text-[var(--muted-foreground)]">The file stays in your browser — only its reference is sent to the DMS.</span>
          <input
            ref={inputRef}
            type="file"
            className="hidden"
            data-testid="document-file-input"
            onChange={(event) => takeFiles(event.target.files)}
          />
        </div>

        {file ? (
          <div className="flex items-center justify-between gap-3 rounded-[10px] border border-[var(--border)] bg-[var(--muted)] px-3 py-2 text-sm" data-testid="document-preview">
            <span className="flex min-w-0 items-center gap-2">
              <FileText size={16} aria-hidden="true" />
              <span className="min-w-0 truncate font-semibold">{file.name}</span>
            </span>
            <span className="flex-none text-xs text-[var(--muted-foreground)]">{formatFileSize(file.size)}</span>
          </div>
        ) : null}

        <TextInput
          label="File reference (DMS reference or URL)"
          name="upload_file_reference"
          value={fileReference}
          onChange={(event) => setFileReference(event.target.value)}
          placeholder="DMS reference or URL"
          hint="Pre-filled from the selected file — adjust it if your DMS assigns a different reference."
        />
      </div>
    </Modal>
  )
}

/** Documents tab: requirement checklist, blocking banner, uploaded files. */
export function OLProposalDocuments({ detail, onActionError }: { detail: ProposalDetail; onActionError: (error: unknown) => void }) {
  const documentsQuery = useProposalDocuments(detail.id)
  const rows = documentsQuery.data?.rows?.length ? documentsQuery.data.rows : detail.documents
  const requirements = documentsQuery.data?.requirements ?? []
  const [uploadModalOpen, setUploadModalOpen] = useState(false)
  const [preselectedType, setPreselectedType] = useState<string | undefined>(undefined)

  const uploadedByType = new Set(
    rows.filter((row) => SATISFIED_STATUSES.has(row.status.toUpperCase())).map((row) => row.documentType),
  )
  const missingMandatory = requirements.filter((row) => row.mandatory && !uploadedByType.has(row.documentType))

  const openUploadModal = (requirement?: ProposalDocumentRequirement) => {
    setPreselectedType(requirement?.documentType)
    onActionError(null)
    setUploadModalOpen(true)
  }

  return (
    <div className="space-y-4" data-testid="tab-documents">
      {documentsQuery.isError ? (
        <ErrorCoach error={documentsQuery.error} title="The document list could not be loaded" compact onRetry={() => void documentsQuery.refetch()} />
      ) : (
        <>
          {missingMandatory.length > 0 && (
            <MissingMandatoryBanner missing={missingMandatory} onPick={(requirement) => openUploadModal(requirement)} />
          )}

          <RequirementsChecklist requirements={requirements} uploads={rows} />

          <section className="surface-card p-4">
            <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
              <h2 className="flex items-center gap-2 font-bold">
                <FileText size={16} aria-hidden="true" />
                Uploaded documents
              </h2>
              <button type="button" className="button-primary" data-testid="open-upload-modal" onClick={() => openUploadModal()}>
                Upload document
              </button>
            </div>
            {rows.length > 0 ? (
              <ul className="divide-y">
                {rows.map((row) => (
                  <li key={row.id || row.documentType} className="flex items-center justify-between gap-3 py-2 text-sm" data-document-type={row.documentType}>
                    <span className="min-w-0 truncate font-semibold">
                      {row.documentTypeDisplay || row.documentType}
                      {row.mandatory ? <span className="ml-2 rounded-full bg-[var(--secondary)] px-1.5 py-0.5 text-[10px] font-bold">Mandatory</span> : null}
                    </span>
                    <span className="flex flex-none items-center gap-3">
                      {row.fileReference && /^https?:\/\//.test(row.fileReference) && (
                        <a href={row.fileReference} target="_blank" rel="noreferrer" className="text-xs font-bold underline-offset-2 hover:underline">
                          Open
                        </a>
                      )}
                      <span className="text-xs font-bold uppercase tracking-wide text-[var(--muted-foreground)]">{row.status}</span>
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-[var(--muted-foreground)]">No documents have been uploaded for this proposal yet.</p>
            )}
          </section>

          <OLDocumentUploadModal
            key={preselectedType ?? "none"}
            open={uploadModalOpen}
            proposalId={String(detail.id)}
            initialType={preselectedType}
            onClose={() => {
              setUploadModalOpen(false)
              setPreselectedType(undefined)
            }}
            onError={(error) => onActionError(error)}
          />
        </>
      )}
    </div>
  )
}
