import { Check } from "lucide-react"

export interface Step {
  title: string
  description?: string
}

interface StepperProps {
  steps: Step[]
  currentStep: number
  className?: string
}

export default function Stepper({ steps, currentStep, className = "" }: StepperProps) {
  return (
    <div className={`w-full ${className}`}>
      <div className="flex items-start">
        {steps.map((step, index) => {
          const isCompleted = index < currentStep
          const isActive = index === currentStep
          const isLast = index === steps.length - 1

          return (
            <div key={index} className="flex items-center flex-1 last:flex-none">
              <div className="flex flex-col items-center">
                <div
                  className={`flex h-9 w-9 items-center justify-center rounded-full border-2 text-sm font-bold transition-all duration-300 ${
                    isCompleted
                      ? "border-[var(--color-feedback-success)] bg-[var(--color-feedback-success)] text-white shadow-sm"
                      : isActive
                        ? "border-[var(--color-brand-primary)] bg-[var(--color-brand-primary)] text-white shadow-md scale-110"
                        : "border-[var(--color-border-default)] bg-[var(--color-bg-surface)] text-[var(--color-text-muted)]"
                  }`}
                >
                  {isCompleted ? (
                    <Check className="h-4 w-4" />
                  ) : (
                    <span>{index + 1}</span>
                  )}
                </div>
                <div className="mt-2 text-center">
                  <p
                    className={`text-xs font-semibold leading-tight ${
                      isActive
                        ? "text-[var(--color-brand-primary)]"
                        : isCompleted
                          ? "text-[var(--color-text-primary)]"
                          : "text-[var(--color-text-muted)]"
                    }`}
                  >
                    {step.title}
                  </p>
                  {step.description && (
                    <p className="mt-0.5 text-[10px] leading-tight text-[var(--color-text-muted)] max-w-24">
                      {step.description}
                    </p>
                  )}
                </div>
              </div>

              {!isLast && (
                <div className="flex-1 mx-2 mb-6">
                  <div
                    className={`h-0.5 rounded-full transition-all duration-500 ${
                      isCompleted
                        ? "bg-[var(--color-feedback-success)]"
                        : "bg-[var(--color-border-default)]"
                    }`}
                  />
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
