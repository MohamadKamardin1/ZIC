import { createContext, useContext, useState, useCallback, type ReactNode } from "react"

export interface AIMessage {
  id: string
  role: "user" | "assistant"
  content: string
  data?: Record<string, unknown>
  status?: "loading" | "done" | "error"
}

export interface AIPartnerResult {
  status: "ready" | "needs_clarification"
  partnerType?: string
  partnerData?: Record<string, unknown>
  missingRequired?: string[]
  missingOptional?: string[]
  explanation?: string
  partialData?: Record<string, unknown>
}

interface AIContextValue {
  panelOpen: boolean
  expanded: boolean
  setExpanded: (expanded: boolean) => void
  togglePanel: () => void
  setPanelOpen: (open: boolean) => void
  messages: AIMessage[]
  addMessage: (msg: AIMessage) => void
  clearMessages: () => void
  lastResult: AIPartnerResult | null
  setLastResult: (result: AIPartnerResult | null) => void
  awaitingClarification: boolean
  setAwaitingClarification: (v: boolean) => void
}

const AIContext = createContext<AIContextValue | null>(null)

export function AIProvider({ children }: { children: ReactNode }) {
  const [panelOpen, setPanelOpen] = useState(false)
  const [expanded, setExpanded] = useState(false)
  const [messages, setMessages] = useState<AIMessage[]>([])
  const [lastResult, setLastResult] = useState<AIPartnerResult | null>(null)
  const [awaitingClarification, setAwaitingClarification] = useState(false)

  const togglePanel = useCallback(() => setPanelOpen((o) => !o), [])
  const addMessage = useCallback((msg: AIMessage) => setMessages((prev) => [...prev, msg]), [])
  const clearMessages = useCallback(() => {
    setMessages([])
    setLastResult(null)
    setAwaitingClarification(false)
  }, [])

  return (
    <AIContext.Provider
      value={{
        panelOpen, expanded, setExpanded, togglePanel, setPanelOpen,
        messages, addMessage, clearMessages,
        lastResult, setLastResult,
        awaitingClarification, setAwaitingClarification,
      }}
    >
      {children}
    </AIContext.Provider>
  )
}

export function useAI() {
  const ctx = useContext(AIContext)
  if (!ctx) throw new Error("useAI must be used within AIProvider")
  return ctx
}
