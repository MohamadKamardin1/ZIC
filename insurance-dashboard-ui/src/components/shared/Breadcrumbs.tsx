import { ChevronRight, Home } from "lucide-react"
import { useNavigate } from "react-router-dom"

interface Crumb {
  label: string
  path?: string
}

export function Breadcrumbs({ items }: { items: Crumb[] }) {
  const navigate = useNavigate()

  if (!items.length) return null

  return (
    <nav className="mb-4 flex items-center gap-1.5 text-sm text-muted-foreground">
      <button
        onClick={() => navigate("/")}
        className="flex items-center gap-1 rounded-md px-1.5 py-0.5 transition hover:bg-accent hover:text-foreground"
      >
        <Home className="h-3.5 w-3.5" />
        <span>Home</span>
      </button>
      {items.map((crumb, i) => (
        <span key={i} className="flex items-center gap-1.5">
          <ChevronRight className="h-3.5 w-3.5" />
          {crumb.path ? (
            <button
              onClick={() => navigate(crumb.path!)}
              className="rounded-md px-1.5 py-0.5 transition hover:bg-accent hover:text-foreground"
            >
              {crumb.label}
            </button>
          ) : (
            <span className="font-medium text-foreground">{crumb.label}</span>
          )}
        </span>
      ))}
    </nav>
  )
}
