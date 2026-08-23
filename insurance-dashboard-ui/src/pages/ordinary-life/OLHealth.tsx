import { useMemo, useState } from "react"
import { AlertTriangle, ClipboardCheck, Stethoscope } from "lucide-react"
import { ErrorCoach } from "../../components/commitments/ErrorCoach"
import { DateInput, SelectInput, TextInput } from "../../components/ui/FormControls"
import { Modal } from "../../components/ui/Overlays"
import { useToast } from "../../components/ui/Toast"
import { useHealthQuestions, useSubmitHealthAnswersMutation, useUnderwritingDecisionMutation } from "../../lib/proposalsHooks"
import type { OLHealthQuestion, ProposalDetail } from "../../lib/proposals"

const IMPACT_LABELS: Record<string, string> = {
  NONE: "No impact",
  LOW: "Low impact",
  MEDIUM: "Medium impact",
  HIGH: "High impact",
  CRITICAL: "Critical",
}

function QuestionAnswerInput({
  question,
  value,
  onChange,
}: {
  question: OLHealthQuestion
  value: string
  onChange: (value: string) => void
}) {
  const name = `health-answer-${question.questionId}`
  if (question.answerType === "BOOLEAN") {
    return (
      <SelectInput label="Answer" name={name} required={question.mandatory} value={value} onChange={(event) => onChange(event.target.value)}>
        <option value="">Select…</option>
        <option value="Yes">Yes</option>
        <option value="No">No</option>
      </SelectInput>
    )
  }
  if (question.answerType === "DATE") {
    return <DateInput label="Answer" name={name} required={question.mandatory} value={value} onChange={(event) => onChange(event.target.value)} />
  }
  if (question.answerType === "NUMBER") {
    return (
      <TextInput
        label="Answer"
        name={name}
        type="number"
        step="any"
        required={question.mandatory}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    )
  }
  return (
    <TextInput
      label={question.answerType === "CHOICE" ? "Answer (describe choice)" : "Answer"}
      name={name}
      required={question.mandatory}
      value={value}
      onChange={(event) => onChange(event.target.value)}
    />
  )
}

/** Health questionnaire + underwriting workspace (BR-13). */
export function OLHealth({ detail, canEnrich, onActionError }: { detail: ProposalDetail; canEnrich: boolean; onActionError: (error: unknown) => void }) {
  const questionsQuery = useHealthQuestions(detail.id)
  const questions = questionsQuery.data?.questions ?? []
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const [decisionOpen, setDecisionOpen] = useState(false)
  const { toast } = useToast()
  const submitAnswers = useSubmitHealthAnswersMutation()

  const pendingUnderwriting = detail.status.toUpperCase() === "PENDING_UNDERWRITING"
  const declined = detail.underwritingStatus?.toUpperCase() === "DECLINED"
  const answeredCount = Object.values(answers).filter((value) => value.trim() !== "").length

  const saveAnswers = () => {
    const payload = questions
      .filter((question) => (answers[question.questionId] ?? "").trim() !== "")
      .map((question) => ({ health_question: question.questionId, answer: answers[question.questionId].trim() }))
    if (payload.length === 0) return
    onActionError(null)
    submitAnswers.mutate(
      { id: String(detail.id), answers: payload },
      {
        onSuccess: (data) => {
          const record = (data ?? {}) as { health_result?: { triggered?: boolean; medical_required?: boolean } }
          const result = record.health_result
          if (result?.triggered || result?.medical_required) {
            toast({
              title: "Medical requirement raised",
              message: "Your answers triggered a medical follow-up. The proposal is now pending underwriting review.",
              tone: "warning" as const,
            })
          } else {
            toast({ title: "Answers saved", message: `${payload.length} health ${payload.length === 1 ? "answer" : "answers"} recorded.`, tone: "success" })
          }
        },
        onError: (error) => onActionError(error),
      },
    )
  }

  return (
    <div className="space-y-4" data-testid="tab-health">
      {declined && (
        <div
          className="rounded-[10px] border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-900 dark:border-red-900/60 dark:bg-red-950/35 dark:text-red-100"
          role="alert"
          data-testid="underwriting-declined-banner"
        >
          <p className="flex items-center gap-2 font-bold">
            <AlertTriangle size={16} aria-hidden="true" />
            Underwriting declined this proposal — it is cancelled and read-only.
          </p>
          {detail.reasonText && <p className="mt-1">Reason: {detail.reasonText}</p>}
        </div>
      )}

      {pendingUnderwriting && !declined && (
        <>
          <div
            className="rounded-[10px] border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900 dark:border-amber-800 dark:bg-amber-950/30 dark:text-amber-100"
            role="status"
            data-testid="underwriting-pending-banner"
          >
            <p className="font-bold">Pending underwriting review.</p>
            <p>Health answers have been submitted. An underwriter decision is required before payment readiness.</p>
          </div>
          {detail.medicalRequired && (
            <div className="surface-card p-4" data-testid="medical-requirement-card">
              <h2 className="mb-2 flex items-center gap-2 font-bold">
                <Stethoscope size={16} aria-hidden="true" />
                Medical requirement raised
              </h2>
              <p className="text-sm text-[var(--muted-foreground)]">
                One or more of your answers requires a medical follow-up. The ZIC underwriting team will review the case and may request
                additional medical evidence before issuing a decision.
              </p>
            </div>
          )}
        </>
      )}

      <section className="surface-card p-4">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <h2 className="flex items-center gap-2 font-bold">
            <ClipboardCheck size={16} aria-hidden="true" />
            Health questionnaire
            {questionsQuery.data?.questionnaire ? (
              <span className="text-xs font-bold uppercase tracking-wide text-[var(--muted-foreground)]">{questionsQuery.data.questionnaire}</span>
            ) : null}
          </h2>
          <span className="text-xs font-bold uppercase tracking-[0.08em] text-[var(--muted-foreground)]" data-testid="health-answered-count">
            {answeredCount}/{questions.length} answered
          </span>
        </div>

        {questionsQuery.isLoading ? (
          <div className="space-y-3" aria-busy="true">
            <div className="h-16 animate-pulse rounded-[10px] bg-[var(--muted)]" />
            <div className="h-16 animate-pulse rounded-[10px] bg-[var(--muted)]" />
          </div>
        ) : questions.length === 0 ? (
          <p className="text-sm text-[var(--muted-foreground)]">
            No health questionnaire applies to this proposal — proceed to documents and enrichment.
          </p>
        ) : (
          <>
            <ul className="space-y-3">
              {questions.map((question) => (
                <li key={question.questionId} className="rounded-[10px] border border-[var(--border)] p-3" data-testid={`health-question-${question.questionId}`}>
                  <div className="mb-2 flex flex-wrap items-start justify-between gap-2">
                    <p className="max-w-xl text-sm font-semibold">
                      {question.sequence}. {question.questionText}
                      {question.mandatory ? <span className="ml-1 text-red-600">*</span> : null}
                    </p>
                    <span className="flex flex-none gap-1.5">
                      {question.category ? (
                        <span className="rounded-full bg-[var(--secondary)] px-2 py-0.5 text-[10px] font-bold">{question.category}</span>
                      ) : null}
                      {question.triggerMedicalRequirement ? (
                        <span className="rounded-full border border-amber-400 px-2 py-0.5 text-[10px] font-bold text-amber-700 dark:text-amber-300">
                          Triggers medical
                        </span>
                      ) : null}
                      {question.underwritingImpact && question.underwritingImpact !== "NONE" ? (
                        <span className="rounded-full border border-[var(--border)] px-2 py-0.5 text-[10px] font-bold text-[var(--muted-foreground)]">
                          {IMPACT_LABELS[question.underwritingImpact] ?? question.underwritingImpact}
                        </span>
                      ) : null}
                    </span>
                  </div>
                  <div className="max-w-md">
                    <QuestionAnswerInput
                      question={question}
                      value={answers[question.questionId] ?? ""}
                      onChange={(value) => setAnswers((current) => ({ ...current, [question.questionId]: value }))}
                    />
                  </div>
                </li>
              ))}
            </ul>
            {!pendingUnderwriting && (
              <div className="mt-4 flex justify-end">
                <button
                  type="button"
                  className="button-primary"
                  data-testid="save-health-answers"
                  disabled={answeredCount === 0 || submitAnswers.isPending}
                  onClick={saveAnswers}
                >
                  {submitAnswers.isPending ? "Saving…" : "Save health answers"}
                </button>
              </div>
            )}
          </>
        )}
        {questionsQuery.isError && (
          <ErrorCoach error={questionsQuery.error} title="The health questionnaire could not be loaded" compact onRetry={() => void questionsQuery.refetch()} />
        )}
      </section>

      {canEnrich && pendingUnderwriting && !declined && (
        <section className="surface-card p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="font-bold">Underwriting decision</h2>
              <p className="text-sm text-[var(--muted-foreground)]">Clear, load, or decline this proposal based on the health answers above.</p>
            </div>
            <button type="button" className="button-primary" data-testid="open-underwriting-decision" onClick={() => setDecisionOpen(true)}>
              Record decision
            </button>
          </div>
        </section>
      )}

      <OLUnderwritingDecisionModal
        open={decisionOpen}
        proposalId={String(detail.id)}
        onClose={() => setDecisionOpen(false)}
        onError={(error) => onActionError(error)}
      />
    </div>
  )
}

const DECISION_OPTIONS = [
  { value: "clear", label: "Clear — no loading" },
  { value: "load", label: "Load — apply premium loading" },
  { value: "decline", label: "Decline — cancel proposal" },
]

/** Decision modal gated on permission + allowed action; notes mandatory for Load/Decline. */
function OLUnderwritingDecisionModal({
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
  const { toast } = useToast()
  const decide = useUnderwritingDecisionMutation()
  const [decision, setDecision] = useState<"clear" | "load" | "decline" | "">("")
  const [loadingPercent, setLoadingPercent] = useState("")
  const [notes, setNotes] = useState("")
  const [notesError, setNotesError] = useState<string | null>(null)

  const needsNotes = decision === "load" || decision === "decline"

  const close = () => {
    setDecision("")
    setLoadingPercent("")
    setNotes("")
    setNotesError(null)
    onClose()
  }

  const submitDecision = () => {
    if (!decision) return
    if (needsNotes && !notes.trim()) {
      setNotesError("Notes are mandatory when loading or declining a proposal.")
      return
    }
    setNotesError(null)
    const reasonParts = [notes.trim()]
    if (decision === "load" && loadingPercent.trim()) reasonParts.push(`+${loadingPercent.trim()}% premium loading`)
    onError(null)
    decide.mutate(
      { id: proposalId, decision, reason: reasonParts.filter(Boolean).join(" — ") },
      {
        onSuccess: () => {
          toast({
            title:
              decision === "clear"
                ? "Proposal cleared"
                : decision === "load"
                  ? "Loading applied"
                  : "Proposal declined",
            message:
              decision === "decline"
                ? "The proposal has been cancelled following the underwriting decline."
                : "The proposal returned to enrichment for finalisation.",
            tone: decision === "decline" ? ("warning" as const) : ("success" as const),
          })
          close()
        },
        onError: (error) => onError(error),
      },
    )
  }

  return (
    <Modal
      open={open}
      title="Record underwriting decision"
      description="This decision changes the proposal lifecycle immediately."
      onClose={close}
      footer={
        <>
          <button type="button" className="button-secondary" onClick={close}>
            Cancel
          </button>
          <button
            type="button"
            className="button-primary"
            data-testid="submit-underwriting-decision"
            disabled={!decision || decide.isPending}
            onClick={submitDecision}
          >
            {decide.isPending ? "Submitting…" : "Submit decision"}
          </button>
        </>
      }
    >
      <div className="space-y-4">
        <SelectInput
          label="Decision"
          name="underwriting_decision"
          value={decision}
          onChange={(event) => setDecision(event.target.value as "clear" | "load" | "decline" | "")}
          data-testid="decision-select"
        >
          <option value="">Select decision…</option>
          {DECISION_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </SelectInput>

        {decision === "load" && (
          <TextInput
            label="Premium loading (%)"
            name="underwriting_loading_percent"
            type="number"
            min="0"
            max="500"
            data-testid="loading-percent-input"
            value={loadingPercent}
            onChange={(event) => setLoadingPercent(event.target.value)}
            placeholder="e.g. 25"
            hint="Recorded with the decision notes as a percentage premium loading."
          />
        )}

        <TextInput
          label={needsNotes ? "Decision notes *" : "Decision notes"}
          name="underwriting_decision_notes"
          data-testid="decision-notes"
          value={notes}
          error={notesError ?? undefined}
          onChange={(event) => setNotes(event.target.value)}
          placeholder={needsNotes ? "Explain the medical basis for this decision" : "Optional context for the record"}
        />
      </div>
    </Modal>
  )
}
