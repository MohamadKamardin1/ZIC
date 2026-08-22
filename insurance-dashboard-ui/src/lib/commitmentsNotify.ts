import type { StatusTone } from "../components/ui/StatusBadge"
import { toStructuredError } from "./structuredError"

export interface CommitmentsToast {
  toast: (input: { title: string; message?: string; tone: StatusTone }) => void
}

/** Success toast with an explicit next-step hint (teach-forward, not just cheer). */
export function notifyCommitmentSuccess(toast: CommitmentsToast["toast"], title: string, nextStepHint?: string) {
  toast({ tone: "success", title, ...(nextStepHint ? { message: nextStepHint } : {}) })
}

/** Failure toast derived from the structured error so the user knows the next move. */
export function notifyCommitmentFailure(toast: CommitmentsToast["toast"], error: unknown, title: string) {
  const structured = toStructuredError(error)
  const firstStep = structured.resolutionSteps[0]
  const message = firstStep ? `${structured.message} ${firstStep}` : structured.message
  toast({ tone: "danger", title, message })
}