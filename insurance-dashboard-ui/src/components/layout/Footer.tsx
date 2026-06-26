import { ListTodo, Sparkles } from "lucide-react"
import { useAI } from "../ai/AIContext"

export function Footer() {
  const { togglePanel } = useAI()

  return (
    <footer className="mt-2 flex flex-wrap items-center gap-x-6 gap-y-2 border-t border-border bg-card px-4 py-3 text-xs md:px-6">
      <span className="inline-flex items-center gap-1.5 rounded-full border border-border px-3 py-1 font-medium text-muted-foreground">
        <ListTodo className="h-3.5 w-3.5" />
        Task
      </span>
      <span className="font-semibold text-success">129.45 TZS/USD</span>
      <span className="inline-flex items-center gap-1.5 text-muted-foreground">
        <span className="h-2 w-2 rounded-full bg-success" />
        Connection Stable
      </span>
      <button
        onClick={togglePanel}
        className="inline-flex cursor-pointer items-center gap-1.5 rounded-full border border-border px-3 py-1 font-medium text-primary transition-colors hover:bg-accent"
      >
        <Sparkles className="h-3.5 w-3.5" />
        AI
      </button>
      <span className="ml-auto text-muted-foreground">
        Powered by <span className="font-semibold text-foreground">sultan_code</span>
      </span>
    </footer>
  )
}
