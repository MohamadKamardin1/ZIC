import { createContext, useContext, useState, useCallback, type ReactNode } from "react"

export type MessageRole = "user" | "assistant" | "system"

export interface ChatMessage {
  id: string
  role: MessageRole
  text: string
  data?: AiAnalysisResult | null
}

export interface AiAnalysisResult {
  status: "ready" | "needs_clarification"
  partnerType?: "INDIVIDUAL" | "CORPORATE"
  partnerData: Record<string, unknown>
  missingFields?: string[]
  explanation?: string
}

interface AiContextValue {
  panelOpen: boolean
  openPanel: () => void
  closePanel: () => void
  togglePanel: () => void
  messages: ChatMessage[]
  addMessage: (role: MessageRole, text: string, data?: AiAnalysisResult | null) => void
  clearMessages: () => void
  loading: boolean
  setLoading: (v: boolean) => void
  lastResult: AiAnalysisResult | null
  setLastResult: (r: AiAnalysisResult | null) => void
}

const AiContext = createContext<AiContextValue | null>(null)

let msgId = 0

export function AiProvider({ children }: { children: ReactNode }) {
  const [panelOpen, setPanelOpen] = useState(false)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [loading, setLoading] = useState(false)
  const [lastResult, setLastResult] = useState<AiAnalysisResult | null>(null)

  const addMessage = useCallback((role: MessageRole, text: string, data?: AiAnalysisResult | null) => {
    setMessages((prev) => [...prev, { id: String(++msgId), role, text, data: data ?? null }])
  }, [])

  const clearMessages = useCallback(() => {
    setMessages([])
    setLastResult(null)
  }, [])

  const openPanel = useCallback(() => setPanelOpen(true), [])
  const closePanel = useCallback(() => setPanelOpen(false), [])
  const togglePanel = useCallback(() => setPanelOpen((o) => !o), [])

  return (
    <AiContext.Provider
      value={{
        panelOpen,
        openPanel,
        closePanel,
        togglePanel,
        messages,
        addMessage,
        clearMessages,
        loading,
        setLoading,
        lastResult,
        setLastResult,
      }}
    >
      {children}
    </AiContext.Provider>
  )
}

export function useAi() {
  const ctx = useContext(AiContext)
  if (!ctx) throw new Error("useAi must be used within AiProvider")
  return ctx
}
