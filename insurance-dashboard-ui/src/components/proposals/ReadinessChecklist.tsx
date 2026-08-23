import { useNavigate } from "react-router-dom"
import { CheckCircle2, ExternalLink, XCircle } from "lucide-react"
import { proposalDeepLink, type ChecklistItem } from "../../lib/proposals"

/**
 * Payment readiness checklist panel.
 *
 * Renders the backend's seven-item evaluation: a pass/fail icon per item,
 * the teach-first failure message plus its first resolution step, and a
 * deep-link button that jumps straight to the screen where the item is fixed
 * (backend links like "/proposals/{id}/documents" are translated to in-app
 * routes).
 */
export function ReadinessChecklist({
  items,
  proposalId,
  onNavigateItem,
  className = "",
}: {
  items: ChecklistItem[]
  proposalId?: string | null
  onNavigateItem?: (route: string) => void
  className?: string
}) {
  const navigate = useNavigate()

  if (!items.length) {
    return (
      <p className={`text-[13px] text-[var(--muted-foreground)] ${className}`} data-readiness-checklist="empty">
        Payment readiness has not been evaluated yet. Save enrichment sections, beneficiaries,
        and documents, then evaluate again.
      </p>
    )
  }

  const goTo = (route: string) => {
    if (onNavigateItem) onNavigateItem(route)
    else void navigate(route)
  }

  return (
    <ul className={`flex flex-col gap-2 ${className}`} data-readiness-checklist="true">
      {items.map((item) => {
        const route = proposalDeepLink(item.deepLink, proposalId)
        return (
          <li
            key={item.key}
            data-checklist-item={item.key}
            data-checklist-passed={item.passed ? "true" : "false"}
            className={`flex flex-col gap-1 rounded-md border px-3 py-2 sm:flex-row sm:items-center sm:justify-between ${
              item.passed ? "border-[var(--border)]" : "border-[var(--destructive)]/50 bg-[var(--destructive)]/5"
            }`}
          >
            <div className="flex items-start gap-2">
              {item.passed ? (
                <CheckCircle2 size={16} aria-hidden="true" className="mt-0.5 text-[var(--success)]" />
              ) : (
                <XCircle size={16} aria-hidden="true" className="mt-0.5 text-[var(--destructive)]" />
              )}
              <div>
                <p className="text-[13px] font-semibold capitalize text-[var(--foreground)]">
                  {item.key.replace(/_/g, " ")}
                </p>
                {!item.passed && (
                  <>
                    {item.message && (
                      <p className="text-xs font-semibold leading-5 text-[var(--destructive)]">{item.message}</p>
                    )}
                    {item.resolutionSteps.length > 0 && (
                      <ul className="mt-0.5 list-disc pl-4 text-xs leading-5 text-[var(--muted-foreground)]">
                        {item.resolutionSteps.map((step) => (
                          <li key={step}>{step}</li>
                        ))}
                      </ul>
                    )}
                  </>
                )}
              </div>
            </div>
            {!item.passed && route && (
              <button
                type="button"
                onClick={() => goTo(route)}
                className="button-secondary inline-flex h-8 flex-none items-center gap-1.5 self-start px-2.5 text-xs font-semibold sm:self-auto"
                data-testid={`checklist-link-${item.key}`}
              >
                <ExternalLink size={13} aria-hidden="true" />
                Resolve
              </button>
            )}
          </li>
        )
      })}
    </ul>
  )
}

export default ReadinessChecklist
