import { CircleAlert, LogIn, X } from "lucide-react"

export interface ErrorCoachProps {
  title?: string
  message: string
  loginUrl?: string
  actionLabel?: string
  resolutionSteps?: string[]
  onDismiss?: () => void
}

export function ErrorCoach({ title = "Document action needs attention", message, loginUrl, actionLabel = "Sign in again", resolutionSteps = [], onDismiss }: ErrorCoachProps) {
  return (
    <div className="rounded-[10px] border border-red-200 bg-red-50 p-4 text-sm text-red-950 shadow-sm" role="alert">
      <div className="flex items-start gap-3">
        <CircleAlert className="mt-0.5 shrink-0 text-red-600" size={18} aria-hidden="true" />
        <div className="min-w-0 flex-1">
          <p className="font-bold">{title}</p>
          <p className="mt-1 leading-6">{message}</p>
          {resolutionSteps.length > 0 && <ul className="mt-2 list-disc space-y-1 pl-5 leading-5">{resolutionSteps.map((step) => <li key={step}>{step}</li>)}</ul>}
          {loginUrl && (
            <a className="mt-3 inline-flex items-center gap-2 font-bold text-red-800 underline underline-offset-2 focus:outline-none focus:ring-2 focus:ring-red-600 focus:ring-offset-2" href={loginUrl}>
              <LogIn size={15} aria-hidden="true" />
              {actionLabel}
            </a>
          )}
        </div>
        {onDismiss && <button type="button" className="rounded-md p-1 text-red-700 hover:bg-red-100 focus:outline-none focus:ring-2 focus:ring-red-600" aria-label="Dismiss error" onClick={onDismiss}><X size={16} aria-hidden="true" /></button>}
      </div>
    </div>
  )
}
