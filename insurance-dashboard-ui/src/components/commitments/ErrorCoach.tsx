import { CircleAlert, ExternalLink, RefreshCw, Settings } from "lucide-react"
import { useMemo } from "react"
import { useNavigate } from "react-router-dom"
import { fieldErrorPairs, toStructuredError } from "../../lib/structuredError"

export interface ErrorCoachProps {
  error?: unknown
  onRetry?: () => void
  title?: string
  compact?: boolean
  className?: string
}

/**
 * ErrorCoach renders the backend structured error shape
 * ``{ error_code, message, resolution_steps[], field_errors, doc_ref }`` as a
 * teach-first notice: code chip, plain-language message, numbered resolution
 * steps, inline field errors, a deep-link action for parameter fixes, a
 * "View existing" link for duplicates, and a safe retry button.
 *
 * Accessible, dark-theme parity via design tokens.
 */
export function ErrorCoach({ error, onRetry, title = "Something went wrong", compact = false, className = "" }: ErrorCoachProps) {
  const navigate = useNavigate()
  const structured = useMemo(() => (error ? toStructuredError(error) : null), [error])
  if (!structured) return null
  const fieldErrors = fieldErrorPairs(structured)
  const showRetry = Boolean(onRetry) && structured.retryable

  return (
    <div
      role="alert"
      aria-live="assertive"
      data-error-coach=""
      data-error-code={structured.code}
      className={`surface-card flex flex-col gap-3 border-l-4 border-l-[var(--destructive)] px-4 py-4 ${compact ? "" : "sm:px-5"} ${className}`}
    >
      <div className="flex flex-wrap items-center gap-2">
        <span className="badge-danger font-mono text-[11px] uppercase tracking-wide" data-testid="error-coach-code">
          {structured.code}
        </span>
        <h3 className="text-sm font-bold text-[var(--foreground)]">{title}</h3>
      </div>

      <p className="text-sm leading-5 text-[var(--foreground)]" data-testid="error-coach-message">
        {structured.message}
      </p>

      {structured.resolutionSteps.length > 0 && (
        <ol className="flex flex-col gap-1" data-testid="error-coach-steps">
          {structured.resolutionSteps.map((step, index) => (
            <li key={`${index}-${step}`} className="flex items-start gap-2 text-[13px] leading-5 text-[var(--muted-foreground)]">
              <span className="mt-0.5 flex h-4 w-4 flex-none items-center justify-center rounded-full bg-[var(--secondary)] text-[10px] font-bold text-[var(--foreground)]" aria-hidden="true">
                {index + 1}
              </span>
              <span>{step}</span>
            </li>
          ))}
        </ol>
      )}

      {fieldErrors.length > 0 && (
        <ul className="flex flex-col gap-1 border-t border-[var(--border)] pt-2" data-testid="error-coach-fields">
          {fieldErrors.map(({ field, messages }) => (
            <li key={field} className="flex items-start gap-2 text-[13px] leading-5">
              <span className="font-mono text-[11px] uppercase text-[var(--muted-foreground)]">{field}</span>
              <span className="text-[var(--foreground)]">{messages.join(", ")}</span>
            </li>
          ))}
        </ul>
      )}

      {!compact && (
        <div className="flex flex-wrap items-center gap-2 border-t border-[var(--border)] pt-3">
          {structured.deepLink && (
            <button
              type="button"
              onClick={() => void navigate(structured.deepLink as string)}
              className="button-primary inline-flex h-9 items-center gap-2 px-3 text-xs font-semibold"
              data-testid="error-coach-deep-link"
            >
              <Settings size={14} aria-hidden="true" />
              {structured.deepLinkLabel ?? "Open configuration"}
            </button>
          )}
          {structured.existing?.href && (
            <button
              type="button"
              onClick={() => void navigate(structured.existing?.href as string)}
              className="button-secondary inline-flex h-9 items-center gap-2 px-3 text-xs font-semibold"
              data-testid="error-coach-existing"
            >
              <ExternalLink size={14} aria-hidden="true" />
              {structured.existing.label}
            </button>
          )}
          {showRetry && (
            <button
              type="button"
              onClick={onRetry}
              className="button-secondary inline-flex h-9 items-center gap-2 px-3 text-xs font-semibold"
              data-testid="error-coach-retry"
            >
              <RefreshCw size={14} aria-hidden="true" />
              Try again
            </button>
          )}
          {structured.docRef && (
            <span className="ml-auto flex items-center gap-1 text-[11px] text-[var(--muted-foreground)]">
              <CircleAlert size={12} aria-hidden="true" />
              {structured.docRef}
            </span>
          )}
        </div>
      )}
    </div>
  )
}

export default ErrorCoach