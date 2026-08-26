import { Check, ChevronLeft, ChevronRight, CircleAlert, X } from "lucide-react"
import { useEffect, useState, type ReactNode } from "react"
import type { LucideIcon } from "lucide-react"

export type WizardStep = { id: string; label: string; icon: LucideIcon; content: ReactNode; validate?: () => boolean | Promise<boolean> }

export function Wizard({ steps, initialStep = 0, onCancel, onComplete, onAutosave, completeLabel = "Complete", completeDisabled = false, className = "" }: { steps: WizardStep[]; initialStep?: number; onCancel?: () => void; onComplete?: () => void; onAutosave?: (step: WizardStep, index: number) => void | Promise<void>; completeLabel?: string; completeDisabled?: boolean; className?: string }) {
  const [activeIndex, setActiveIndex] = useState(Math.min(initialStep, Math.max(0, steps.length - 1)))
  const [completed, setCompleted] = useState<Set<string>>(new Set())
  const [invalid, setInvalid] = useState<Set<string>>(new Set())
  const activeStep = steps[activeIndex]

  useEffect(() => { if (activeStep) void onAutosave?.(activeStep, activeIndex) }, [activeIndex, activeStep, onAutosave])

  async function validateCurrent() {
    if (!activeStep?.validate) return true
    const valid = await activeStep.validate()
    setInvalid((current) => { const next = new Set(current); if (valid) next.delete(activeStep.id); else next.add(activeStep.id); return next })
    if (valid) setCompleted((current) => new Set(current).add(activeStep.id))
    return valid
  }

  async function next() {
    if (!(await validateCurrent())) return
    if (activeIndex === steps.length - 1) { onComplete?.(); return }
    setActiveIndex((current) => current + 1)
  }

  async function selectStep(index: number) {
    if (index > activeIndex && !(await validateCurrent())) return
    setActiveIndex(index)
  }

  if (!steps.length) return null
  return <section className={`surface-card overflow-hidden ${className}`} aria-label="Wizard"><nav className="overflow-x-auto border-b bg-[var(--muted)]/35 px-4 py-3" aria-label="Wizard steps"><ol className="flex min-w-max items-center justify-between gap-2"><>{steps.map((step, index) => { const StepIcon = step.icon; const isActive = index === activeIndex; const isComplete = completed.has(step.id); const isInvalid = invalid.has(step.id); return <li key={step.id} className="flex items-center gap-2"><button type="button" onClick={() => void selectStep(index)} className={`group flex items-center gap-2 rounded-[10px] px-3 py-2 text-left text-sm transition ${isActive ? "bg-[var(--primary)] text-[var(--primary-foreground)] shadow-sm" : isInvalid ? "text-[var(--destructive)] hover:bg-[var(--secondary)]" : "text-[var(--muted-foreground)] hover:bg-[var(--secondary)]"}`} aria-current={isActive ? "step" : undefined}><span className={`flex h-7 w-7 items-center justify-center rounded-full border ${isActive ? "border-white/40 bg-white/15" : isComplete ? "border-[var(--success)] bg-[var(--success)]/10 text-[var(--success)]" : isInvalid ? "border-[var(--destructive)] bg-[var(--destructive)]/10" : "border-current/25"}`}>{isComplete && !isActive ? <Check size={14} aria-hidden="true" /> : isInvalid ? <CircleAlert size={14} aria-hidden="true" /> : <StepIcon size={14} aria-hidden="true" />}</span><span className="font-semibold">{step.label}</span></button>{index < steps.length - 1 && <span className="hidden h-px w-6 bg-[var(--border)] xl:block" aria-hidden="true" />}</li> })}</></ol></nav><div className="p-5">{activeStep.content}</div><footer className="flex flex-wrap items-center justify-between gap-3 border-t bg-[var(--muted)]/25 px-5 py-4"><button type="button" className="button-secondary" onClick={onCancel}><X size={15} aria-hidden="true" />Cancel</button><div className="flex gap-2"><button type="button" className="button-secondary" disabled={activeIndex === 0} onClick={() => setActiveIndex((current) => Math.max(0, current - 1))}><ChevronLeft size={15} aria-hidden="true" />Previous</button><button type="button" className="button-primary" disabled={activeIndex === steps.length - 1 && completeDisabled} onClick={() => void next()}>{activeIndex === steps.length - 1 ? completeLabel : "Next"}<ChevronRight size={15} aria-hidden="true" /></button></div></footer></section>
}
