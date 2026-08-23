import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { CheckCircle2, Circle, Loader2 } from "lucide-react"
import { Modal } from "../../components/ui/Overlays"
import { ErrorCoach } from "./ErrorCoach"
import { StatusBadge } from "../ui/StatusBadge"
import { useToast } from "../ui/Toast"
import { processOverdueCommitments, type OverdueRunResult } from "../../lib/commitments"
import { notifyCommitmentSuccess } from "../../lib/commitmentsNotify"

export interface OverdueProcessingModalProps {
  open: boolean
  onClose: () => void
  onComplete: () => void
}

export const OVERDUE_STAGES = ["validate", "update", "notify", "summarize"] as const
export type OverdueStage = (typeof OVERDUE_STAGES)[number]

export function OverdueProcessingModal({ open, onClose, onComplete }: OverdueProcessingModalProps) {
  const navigate = useNavigate()
  const { toast } = useToast()
  const [running, setRunning] = useState(false)
  const [stage, setStage] = useState<number>(-1)
  const [result, setResult] = useState<OverdueRunResult | null>(null)
  const [error, setError] = useState<unknown>(null)

  const step = (index: number) => (): Promise<void> => new Promise((resolve) => window.setTimeout(() => { setStage(index); resolve() }, 0))

  const run = async () => {
    setError(null)
    setResult(null)
    setRunning(true)
    try {
      const next = await processOverdueCommitments()
      await step(0)()
      await step(1)()
      await step(2)()
      setStage(3)
      setResult(next)
      notifyCommitmentSuccess(toast, "Overdue processing complete", `${next.overdue} commitment(s) marked overdue. Review the lapse queue for policy actions.`)
      onComplete()
    } catch (reason) {
      setError(reason)
    } finally {
      setRunning(false)
    }
  }

  const stageLabel: Record<OverdueStage, string> = {
    validate: "Validate due commitments",
    update: "Update statuses to overdue",
    notify: "Create grace notifications",
    summarize: "Summarize results",
  }

  const footer = (
    <>
      <button type="button" className="button-secondary" onClick={onClose}>Close</button>
      {!result && (
        <button type="button" className="button-primary" data-testid="run-overdue" disabled={running} onClick={() => void run()}>
          {running ? "Processing…" : "Run Overdue Processing"}
        </button>
      )}
    </>
  )

  return (
    <Modal open={open} title="Overdue Processing" description="Safe, idempotent batch: marks past-grace commitments overdue, writes grace notifications, and flags lapse reviews." onClose={onClose} footer={footer} size="lg">
      <div className="space-y-4">
        <ol className="flex flex-col gap-2">
          {OVERDUE_STAGES.map((key, index) => {
            const isDone = result !== null || stage > index
            const isActive = running && stage === index
            return (
              <li key={key} className="flex items-center gap-2 text-sm" data-testid={`overdue-stage-${key}`}>
                {isDone ? (
                  <CheckCircle2 size={16} className="text-[var(--success)]" aria-hidden="true" />
                ) : isActive ? (
                  <Loader2 size={16} className="animate-spin text-[var(--primary)]" aria-hidden="true" />
                ) : (
                  <Circle size={16} className="text-[var(--muted-foreground)]/40" aria-hidden="true" />
                )}
                <span className={isDone || isActive ? "font-semibold text-[var(--foreground)]" : "text-[var(--muted-foreground)]"}>{stageLabel[key]}</span>
              </li>
            )
          })}
        </ol>

        {result && (
          <section className="rounded-[10px] border border-[var(--border)] bg-[var(--muted)]/20 px-4 py-3" aria-label="Overdue processing summary" data-testid="overdue-summary">
            <div className="mb-2"><h3 className="text-sm font-bold text-[var(--foreground)]">Overdue processing summary</h3><p className="text-xs text-[var(--muted-foreground)]">Every status change and notification is recorded in audit and the outbox.</p></div>
            <dl className="grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-4">
              <div><dt className="text-xs text-[var(--muted-foreground)]">Processed</dt><dd className="tabular-nums font-semibold text-[var(--foreground)]">{result.processed.toLocaleString()}</dd></div>
              <div><dt className="text-xs text-[var(--muted-foreground)]">Marked overdue</dt><dd className="tabular-nums font-semibold text-[var(--destructive)]">{result.overdue.toLocaleString()}</dd></div>
              <div><dt className="text-xs text-[var(--muted-foreground)]">Notifications created</dt><dd className="tabular-nums font-semibold text-[var(--foreground)]">{result.notified.toLocaleString()}</dd></div>
              <div><dt className="text-xs text-[var(--muted-foreground)]">Lapse reviews flagged</dt><dd className="tabular-nums font-semibold text-[var(--warning)]">{result.lapseReviews.toLocaleString()}</dd></div>
            </dl>
            <div className="mt-3 flex flex-wrap gap-2">
              <button type="button" className="button-secondary" onClick={() => navigate("/ordinary-life/commitments?overdue_only=true")} data-testid="overdue-link">
                View overdue commitments
              </button>
              <button type="button" className="button-primary" onClick={() => navigate("/ordinary-life/commitments")} data-testid="lapse-link">
                Open lapse review queue
              </button>
            </div>
          </section>
        )}

        {result && <StatusBadge value="Audited batch · source BATCH" tone="info" />}

        {error ? <ErrorCoach error={error} title="Overdue processing could not be completed" /> : null}
      </div>
    </Modal>
  )
}

export default OverdueProcessingModal