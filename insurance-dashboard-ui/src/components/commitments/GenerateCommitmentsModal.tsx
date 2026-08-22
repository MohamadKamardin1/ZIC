import { useEffect, useMemo, useState } from "react"
import { useNavigate } from "react-router-dom"
import { ExternalLink, Plus, Sparkles } from "lucide-react"
import { Modal, InfoBanner } from "../../components/ui/Overlays"
import { FormGrid, SelectInput, SearchableSelect } from "../../components/ui/FormControls"
import { ErrorCoach } from "./ErrorCoach"
import { CommitmentStatusBadge } from "./CommitmentStatusBadge"
import { useAccess } from "../../lib/access"
import { useToast } from "../../components/ui/Toast"
import {
  useCommitmentSources,
  useGenerateCommitmentsMutation,
  useGenerateCommitmentsPreviewMutation,
} from "../../lib/commitmentsHooks"
import { normalizeGenerateResult, normalizePreviewRows, type CommitmentPreviewRow, type CommitmentSourceType } from "../../lib/commitments"
import { formatMoney, dateLabel, sourceLabel } from "../../lib/commitmentsDisplay"
import { notifyCommitmentSuccess } from "../../lib/commitmentsNotify"

export interface GenerateCommitmentsModalProps {
  open: boolean
  defaultSourceType?: CommitmentSourceType
  onClose: () => void
  onOpenManual: () => void
  onComplete: () => void
}

const SOURCE_TYPES: Array<{ value: CommitmentSourceType; label: string }> = [
  { value: "PROPOSAL", label: "Proposal (payment-ready)" },
  { value: "POLICY", label: "Policy" },
  { value: "MANUAL", label: "Manual" },
]

function mapOption(option: { id: string; label: string; reference?: string }) {
  return { value: option.id, label: option.reference && !option.label.includes(option.reference) ? `${option.label} — ${option.reference}` : option.label }
}

function PreviewTable({ rows, loading }: { rows: CommitmentPreviewRow[]; loading: boolean }) {
  if (loading) {
    return (
      <div className="space-y-2" role="status" aria-label="Loading preview">
        {["w-11/12", "w-9/12", "w-10/12"].map((width) => (
          <span key={width} className={`block h-6 ${width} animate-pulse rounded bg-[var(--muted)]`} aria-hidden="true" />
        ))}
      </div>
    )
  }
  if (rows.length === 0) {
    return <p className="py-4 text-center text-sm text-[var(--muted-foreground)]">Select a source to preview the generated schedule.</p>
  }
  return (
    <div className="overflow-x-auto rounded-[10px] border border-[var(--border)]">
      <table className="w-full min-w-[640px] text-left text-sm">
        <thead className="bg-[var(--muted)]/45 text-xs uppercase tracking-[0.08em] text-[var(--muted-foreground)]">
          <tr>
            {["Installment", "Due date", "Amount", "Grace date", "Lapse date", "Initial status"].map((heading) => (
              <th key={heading} scope="col" className="px-3 py-2 font-bold">{heading}</th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-[var(--border)]">
          {rows.map((row) => (
            <tr key={row.installmentNumber}>
              <td className="px-3 py-2 tabular-nums">{row.installmentNumber}</td>
              <td className="px-3 py-2">{dateLabel(row.dueDate)}</td>
              <td className="px-3 py-2 tabular-nums">{formatMoney(row.amount, row.currency)}</td>
              <td className="px-3 py-2">{dateLabel(row.graceDate)}</td>
              <td className="px-3 py-2">{dateLabel(row.lapseDate)}</td>
              <td className="px-3 py-2"><CommitmentStatusBadge value={row.status} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function GenerateCommitmentsModal({
  open,
  defaultSourceType = "PROPOSAL",
  onClose,
  onOpenManual,
  onComplete,
}: GenerateCommitmentsModalProps) {
  const navigate = useNavigate()
  const { toast } = useToast()
  const { canAccess } = useAccess()
  const [sourceType, setSourceType] = useState<CommitmentSourceType>(defaultSourceType)
  const [sourceId, setSourceId] = useState("")
  const [executeError, setExecuteError] = useState<unknown>(null)
  const [duplicates, setDuplicates] = useState<Array<{ id?: string; commitment_number?: string }>>([])

  const preview = useGenerateCommitmentsPreviewMutation()
  const execute = useGenerateCommitmentsMutation()
  const sourcesQuery = useCommitmentSources(sourceType === "MANUAL" ? null : sourceType)

  useEffect(() => {
    setExecuteError(null)
    setDuplicates([])
  }, [sourceType, sourceId])

  useEffect(() => {
    if (sourceType === "MANUAL" || !sourceId) return
    preview.mutate({ sourceType, sourceId })
  }, [preview, sourceId, sourceType])

  const sourceOptions = useMemo(
    () => (sourcesQuery.data?.results ?? []).map(mapOption),
    [sourcesQuery.data],
  )

  const rows = useMemo(() => (preview.data ? normalizePreviewRows(preview.data) : []), [preview.data])
  const generationReady = Boolean(sourceId) && rows.length > 0 && !preview.error && !preview.isPending

  const openCreate = (moduleKey: "proposals" | "policies") => {
    if (!canAccess(moduleKey === "proposals" ? "ol_proposals" : "ol_policies")) return
    navigate(`/ordinary-life/${moduleKey}`)
  }

  const runExecution = () => {
    if (!sourceId) return
    execute.mutate(
      { sourceType, sourceId },
      {
        onSuccess: (data) => {
          const result = normalizeGenerateResult(data)
          setExecuteError(null)
          if (result.created > 0) {
            notifyCommitmentSuccess(
              toast,
              "Commitments generated",
              `Created ${result.created} commitment(s). Open the first commitment from the register to record its first payment.`,
            )
            onComplete()
          } else if (result.existing?.length) {
            setDuplicates(result.existing.map((entry) => ({ id: entry.id, commitment_number: entry.commitment_number })))
          }
        },
        onError: (error) => {
          setExecuteError(error)
        },
      },
    )
  }

  const navigateExisting = (duplicate: { id?: string; commitment_number?: string }) => {
    if (duplicate.id) {
      navigate(`/ordinary-life/commitments/${duplicate.id}`)
    } else if (duplicate.commitment_number) {
      navigate(`/ordinary-life/commitments?commitment_number=${encodeURIComponent(duplicate.commitment_number)}`)
    }
  }

  const footer = (
    <>
      {duplicates.length === 0 && preview.error === null && (
        <button type="button" className="button-primary" disabled={!generationReady || execute.isPending} onClick={runExecution} data-testid="execute-generation">
          <Sparkles size={16} aria-hidden="true" />
          {execute.isPending ? "Creating…" : "Execute"}
        </button>
      )}
    </>
  )

  return (
    <Modal open={open} title="Generate Commitments" description="Preview the schedule from a quotation source, then execute idempotently." onClose={onClose} footer={footer} size="lg">
      <div className="space-y-4">
        <FormGrid columns={2}>
          <SelectInput
            label="Source type"
            name="source-type"
            value={sourceType}
            onChange={(event) => {
              setSourceType(event.target.value as CommitmentSourceType)
              setSourceId("")
            }}
            required
          >
            {SOURCE_TYPES.map((option) => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </SelectInput>

          {sourceType !== "MANUAL" && (
            <div className="space-y-0">
              <SearchableSelect
                label={sourceLabel(sourceType)}
                name="source"
                required
                hint={sourceType === "PROPOSAL" ? "Payment-ready proposals" : "Issued policies"}
                options={sourceOptions}
                value={sourceId}
                onChange={setSourceId}
                placeholder={`Search ${sourceLabel(sourceType).toLowerCase()}s`}
                disabled={sourcesQuery.isLoading}
              />
              <button
                type="button"
                className="mt-1 inline-flex items-center gap-1 rounded-md text-xs font-semibold text-[var(--primary)] outline-none transition hover:underline focus-visible:ring-2 focus-visible:ring-[var(--ring)]"
                onClick={() => openCreate(sourceType === "PROPOSAL" ? "proposals" : "policies")}
                data-testid="quick-create-source"
              >
                <Plus size={13} aria-hidden="true" />
                Add {sourceLabel(sourceType).toLowerCase()}
                <ExternalLink size={11} aria-hidden="true" />
              </button>
            </div>
          )}
        </FormGrid>

        {sourceType === "MANUAL" && (
          <InfoBanner title="Manual commitments are created here">
            <p className="text-sm">
              The parameter-driven wizard creates schedules from a proposal or policy. Use the manual form to create a single commitment with full control of dates and amounts.
            </p>
            <button type="button" className="button-primary mt-3" onClick={onOpenManual} data-testid="open-manual-form">
              Open manual form
            </button>
          </InfoBanner>
        )}

        <section aria-label="Preview schedule">
          <div className="mb-2 flex items-center justify-between">
            <h3 className="text-sm font-bold text-[var(--foreground)]">Preview schedule (dry-run)</h3>
            {preview.isPending && <span className="text-xs text-[var(--muted-foreground)]">Thinking…</span>}
          </div>
          <PreviewTable rows={rows} loading={preview.isPending} />
        </section>

        {preview.error ? (
          <ErrorCoach error={preview.error} title="Parameters are missing for generation" onRetry={() => (sourceId ? preview.mutate({ sourceType, sourceId }) : undefined)} />
        ) : null}

        {executeError ? (
          <ErrorCoach error={executeError} title="Generation could not be completed" onRetry={generationReady ? runExecution : undefined} />
        ) : null}

        {duplicates.length > 0 && !executeError && (
          <InfoBanner title="Commitments already exist">
            <ul className="mt-1 list-disc pl-5 text-sm">
              {duplicates.map((duplicate, index) => (
                <li key={`${duplicate.commitment_number ?? duplicate.id ?? index}`}>
                  <button type="button" className="underline underline-offset-2" onClick={() => navigateExisting(duplicate)} data-testid="view-existing">
                    View existing {duplicate.commitment_number ?? "commitment"}
                  </button>
                </li>
              ))}
            </ul>
          </InfoBanner>
        )}
      </div>
    </Modal>
  )
}

export default GenerateCommitmentsModal