import { Link, useLocation } from "react-router-dom"
import { ArrowLeft, Settings } from "lucide-react"

interface PageHeaderProps {
  title: string
  description?: string
  children?: React.ReactNode
}

export function PageHeader({ title, description, children }: PageHeaderProps) {
  return (
    <div className="mb-6">
      <Link
        to="/system-parameters/general"
        className="mb-3 inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to System Parameters
      </Link>
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
            <Settings className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-xl font-bold">{title}</h1>
            {description && <p className="text-sm text-muted-foreground">{description}</p>}
          </div>
        </div>
        {children && <div className="flex-none">{children}</div>}
      </div>
    </div>
  )
}

interface InfoCardProps {
  title: string
  children: React.ReactNode
  className?: string
}

export function InfoCard({ title, children, className = "" }: InfoCardProps) {
  return (
    <div className={`rounded-lg border border-border bg-card p-5 ${className}`}>
      <h3 className="mb-3 text-sm font-semibold text-foreground">{title}</h3>
      {children}
    </div>
  )
}
