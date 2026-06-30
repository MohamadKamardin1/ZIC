import { CheckCircle2, Clock, AlertTriangle, XCircle, ArrowRight } from "lucide-react"

interface FlowStep {
  label: string
  status: "completed" | "active" | "pending" | "rejected"
}

interface FlowBannerProps {
  title: string
  steps: FlowStep[]
  nextAction?: {
    label: string
    onClick: () => void
  }
}

const statusConfig = {
  completed: {
    icon: CheckCircle2,
    bg: "bg-[var(--color-bg-success-soft)]",
    text: "text-[var(--color-text-success-soft)]",
    border: "border-[var(--color-feedback-success)]",
  },
  active: {
    icon: Clock,
    bg: "bg-[var(--color-bg-info-soft)]",
    text: "text-[var(--color-text-info-soft)]",
    border: "border-[var(--color-feedback-info)]",
  },
  pending: {
    icon: Clock,
    bg: "bg-[var(--color-bg-muted)]",
    text: "text-[var(--color-text-muted)]",
    border: "border-[var(--color-border-default)]",
  },
  rejected: {
    icon: XCircle,
    bg: "bg-[var(--color-bg-destructive-soft)]",
    text: "text-[var(--color-text-destructive-soft)]",
    border: "border-[var(--color-feedback-destructive)]",
  },
}

export default function FlowBanner({ title, steps, nextAction }: FlowBannerProps) {
  return (
    <div className="rounded-xl border border-[var(--color-border-default)] bg-[var(--color-bg-surface)] shadow-sm overflow-hidden">
      <div className="flex items-center gap-3 px-5 py-3 border-b border-[var(--color-border-default)] bg-[var(--color-bg-muted)]">
        <AlertTriangle className="h-4 w-4 text-[var(--color-text-muted)]" />
        <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">{title}</h3>
      </div>
      <div className="flex items-center gap-2 px-5 py-4 overflow-x-auto">
        {steps.map((step, index) => {
          const config = statusConfig[step.status]
          const Icon = config.icon
          const isLast = index === steps.length - 1

          return (
            <div key={index} className="flex items-center gap-2 flex-none">
              <div className={`flex items-center gap-2 rounded-lg border px-3 py-2 ${config.bg} ${config.border}`}>
                <Icon className={`h-4 w-4 ${config.text}`} />
                <span className={`text-xs font-medium whitespace-nowrap ${config.text}`}>
                  {step.label}
                </span>
              </div>
              {!isLast && (
                <ArrowRight className="h-3.5 w-3.5 text-[var(--color-text-muted)] flex-none" />
              )}
            </div>
          )
        })}

        {nextAction && (
          <>
            <div className="h-6 w-px bg-[var(--color-border-default)] mx-2 flex-none" />
            <button
              onClick={nextAction.onClick}
              className="flex items-center gap-1.5 rounded-lg bg-[var(--color-brand-primary)] px-4 py-2 text-xs font-semibold text-white hover:brightness-110 transition-all flex-none"
            >
              {nextAction.label}
              <ArrowRight className="h-3.5 w-3.5" />
            </button>
          </>
        )}
      </div>
    </div>
  )
}
