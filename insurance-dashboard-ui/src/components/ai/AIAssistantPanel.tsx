import { useState, useRef, useEffect, type ChangeEvent, type KeyboardEvent } from "react"
import { Sparkles, X, Send, CheckCircle, AlertCircle, Loader2, Bot, User, ArrowRight } from "lucide-react"
import { useAI, type AIMessage, type AIPartnerResult } from "./AIContext"
import { emitDataChange } from "../../lib/useDataRefresh"

interface Props {
  onAnalyze: (prompt: string) => Promise<{ success: boolean; message: string; data: AIPartnerResult }>
  onCreate: (partnerType: string, partnerData: Record<string, unknown>) => Promise<Record<string, unknown>>
  onClarify: (prompt: string, missingFields: string[], partialData: Record<string, unknown>) => Promise<{ success: boolean; data: AIPartnerResult }>
}

export function AIAssistantPanel({ onAnalyze, onCreate, onClarify }: Props) {
  const {
    panelOpen, setPanelOpen, messages, addMessage, clearMessages,
    lastResult, setLastResult, awaitingClarification, setAwaitingClarification,
  } = useAI()
  const [input, setInput] = useState("")
  const [loading, setLoading] = useState(false)
  const [confirming, setConfirming] = useState(false)
  const [done, setDone] = useState(false)
  const [error, setError] = useState("")
  const bottomRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const autoResize = () => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = "auto"
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`
  }

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, loading])

  useEffect(() => {
    if (!panelOpen) {
      setConfirming(false)
      setDone(false)
      setError("")
      setAwaitingClarification(false)
    }
  }, [panelOpen, setAwaitingClarification])

  if (!panelOpen) return null

  // -------------------------------------------------------------------
  // Sends initial prompt to analyze endpoint
  // -------------------------------------------------------------------
  const handleSend = async () => {
    const text = input.trim()
    if (!text || loading) return
    setInput("")
    setError("")
    if (textareaRef.current) textareaRef.current.style.height = "auto"

    addMessage({ id: String(Date.now()), role: "user", content: text, status: "done" })
    setLoading(true)
    setLastResult(null)
    setConfirming(false)
    setDone(false)
    setAwaitingClarification(false)

    try {
      const result = await onAnalyze(text)
      const data = result.data

      if (data.status === "needs_clarification") {
        setLastResult(data)
        setAwaitingClarification(true)
        addMessage({
          id: String(Date.now() + 1),
          role: "assistant",
          content: data.explanation ?? "Some information is missing.",
          data: data as unknown as Record<string, unknown>,
          status: "done",
        })
      } else {
        setLastResult(data)
        addMessage({
          id: String(Date.now() + 1),
          role: "assistant",
          content: "I've analyzed your prompt. Here's the structured data. Please review and confirm.",
          data: data as unknown as Record<string, unknown>,
          status: "done",
        })
        setConfirming(true)
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : "AI service unavailable"
      setError(msg)
      addMessage({ id: String(Date.now() + 1), role: "assistant", content: `Error: ${msg}`, status: "error" })
    } finally {
      setLoading(false)
    }
  }

  // -------------------------------------------------------------------
  // Sends follow-up clarification response
  // -------------------------------------------------------------------
  const handleClarifySend = async () => {
    const text = input.trim()
    if (!text || loading || !lastResult) return
    setInput("")
    setError("")
    if (textareaRef.current) textareaRef.current.style.height = "auto"

    addMessage({ id: String(Date.now()), role: "user", content: text, status: "done" })
    setLoading(true)

    try {
      const allMissing = [
        ...(lastResult.missingRequired ?? []),
        ...(lastResult.missingOptional ?? []),
      ]
      const result = await onClarify(text, allMissing, lastResult.partnerData ?? {})
      const data = result.data

      if (data.status === "needs_clarification") {
        setLastResult(data)
        setAwaitingClarification(true)
        addMessage({
          id: String(Date.now() + 1),
          role: "assistant",
          content: data.explanation ?? "Still missing some fields.",
          data: data as unknown as Record<string, unknown>,
          status: "done",
        })
      } else {
        setLastResult(data)
        setAwaitingClarification(false)
        addMessage({
          id: String(Date.now() + 1),
          role: "assistant",
          content: "Great, all required fields are filled! Please review and confirm.",
          data: data as unknown as Record<string, unknown>,
          status: "done",
        })
        setConfirming(true)
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : "AI service unavailable"
      setError(msg)
      addMessage({ id: String(Date.now() + 1), role: "assistant", content: `Error: ${msg}`, status: "error" })
    } finally {
      setLoading(false)
    }
  }

  // -------------------------------------------------------------------
  // Executes partner creation via API
  // -------------------------------------------------------------------
  const handleConfirm = async () => {
    if (!lastResult || lastResult.status !== "ready") return
    setLoading(true)
    setError("")

    try {
      const created = await onCreate(
        lastResult.partnerType ?? "INDIVIDUAL",
        lastResult.partnerData ?? {},
      )
      const appNumber = (created as Record<string, unknown>).applicationNumber ?? ""
      const name = lastResult.partnerType === "CORPORATE"
        ? (created as Record<string, unknown>).companyName ?? ""
        : `${(created as Record<string, unknown>).firstName ?? ""} ${(created as Record<string, unknown>).surname ?? ""}`.trim()

      addMessage({
        id: String(Date.now()),
        role: "assistant",
        content: `${name || "Partner"} has been onboarded successfully! Application #${appNumber} is now ACTIVE. You can attach partner types, branches, and documents, or onboard another partner.`,
        status: "done",
      })
      setDone(true)
      setConfirming(false)
      setLastResult(null)
      emitDataChange("partners")
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Creation failed"
      setError(msg)
      addMessage({ id: String(Date.now()), role: "assistant", content: `Error: ${msg}`, status: "error" })
    } finally {
      setLoading(false)
    }
  }

  // -------------------------------------------------------------------
  // Creates partner with available data (skips missing optional fields)
  // -------------------------------------------------------------------
  const handleCreateWithAvailable = async () => {
    if (!lastResult) return
    setLoading(true)
    setError("")

    try {
      const partnerData = { ...(lastResult.partnerData ?? {}) }
      // Strip nulls so the serializer doesn't reject them
      const clean = Object.fromEntries(Object.entries(partnerData).filter(([, v]) => v !== null))

      const created = await onCreate(lastResult.partnerType ?? "INDIVIDUAL", clean)
      const appNumber = (created as Record<string, unknown>).applicationNumber ?? ""
      const name = lastResult.partnerType === "CORPORATE"
        ? (created as Record<string, unknown>).companyName ?? ""
        : `${(created as Record<string, unknown>).firstName ?? ""} ${(created as Record<string, unknown>).surname ?? ""}`.trim()

      addMessage({
        id: String(Date.now()),
        role: "assistant",
        content: `${name || "Partner"} has been onboarded successfully! Application #${appNumber} is now ACTIVE. You can update the remaining details later.`,
        status: "done",
      })
      setDone(true)
      setConfirming(false)
      setAwaitingClarification(false)
      setLastResult(null)
      emitDataChange("partners")
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Creation failed"
      setError(msg)
      addMessage({ id: String(Date.now()), role: "assistant", content: `Error: ${msg}`, status: "error" })
    } finally {
      setLoading(false)
    }
  }

  const handleNewChat = () => {
    clearMessages()
    setConfirming(false)
    setDone(false)
    setError("")
  }

  // -------------------------------------------------------------------
  // Render helpers
  // -------------------------------------------------------------------
  const renderMessageIcon = (msg: AIMessage) => {
    if (msg.role === "user") {
      return (
        <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary">
          <User className="h-4 w-4 text-primary-foreground" />
        </div>
      )
    }
    return (
      <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary/10">
        {msg.status === "error" ? (
          <AlertCircle className="h-4 w-4 text-destructive" />
        ) : (
          <Bot className="h-4 w-4 text-primary" />
        )}
      </div>
    )
  }

  const renderConfirmationCard = (data: AIPartnerResult) => {
    if (data.status !== "ready" || !data.partnerData) return null
    return (
      <div className="mt-2 rounded-lg border border-border bg-card p-3">
        <p className="mb-2 text-xs font-semibold uppercase text-muted-foreground">
          {data.partnerType ?? "Partner"} Details
        </p>
        <div className="space-y-1 text-xs">
          {Object.entries(data.partnerData).map(([key, value]) => (
            <div key={key} className="flex justify-between">
              <span className="text-muted-foreground">{key.replace(/([A-Z])/g, " $1").replace(/^ /, "")}</span>
              <span className="font-medium">{value !== null && value !== "" ? String(value) : "-"}</span>
            </div>
          ))}
        </div>
      </div>
    )
  }

  const renderMissingFields = (data: AIPartnerResult) => {
    if (!data.missingRequired?.length && !data.missingOptional?.length) return null
    return (
      <div className="mt-2 space-y-1.5">
        {data.missingRequired?.map((f) => (
          <div key={f} className="flex items-center gap-2 rounded-md bg-destructive/10 px-2.5 py-1.5 text-xs text-destructive">
            <span className="h-1.5 w-1.5 rounded-full bg-destructive" />
            {f.replace(/([A-Z])/g, " $1").replace(/^ /, "")}
            <span className="ml-auto text-[10px] font-medium">Required</span>
          </div>
        ))}
        {data.missingOptional?.map((f) => (
          <div key={f} className="flex items-center gap-2 rounded-md bg-muted px-2.5 py-1.5 text-xs text-muted-foreground">
            <span className="h-1.5 w-1.5 rounded-full bg-muted-foreground/40" />
            {f.replace(/([A-Z])/g, " $1").replace(/^ /, "")}
            <span className="ml-auto text-[10px]">Optional</span>
          </div>
        ))}
      </div>
    )
  }

  // -------------------------------------------------------------------
  // Determine which input placeholder and action to show
  // -------------------------------------------------------------------
  const isClarifying = awaitingClarification && lastResult?.status === "needs_clarification"
  const inputPlaceholder = isClarifying
    ? "Provide the missing information..."
    : "Describe the partner to onboard..."

  const handleSubmit = isClarifying ? handleClarifySend : handleSend

  return (
    <div className="fixed inset-y-0 right-0 z-50 flex w-full max-w-md flex-col border-l border-border bg-background shadow-2xl">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <div className="flex items-center gap-2">
          <div className="rounded-lg bg-primary/10 p-1.5">
            <Sparkles className="h-5 w-5 text-primary" />
          </div>
          <div>
            <h2 className="text-sm font-semibold">AI Assistant</h2>
            <p className="text-xs text-muted-foreground">Powered by DeepSeek</p>
          </div>
        </div>
        <div className="flex items-center gap-1">
          {messages.length > 0 && (
            <button onClick={handleNewChat} className="rounded-md px-2 py-1 text-xs font-medium text-muted-foreground hover:bg-accent hover:text-foreground">
              New Chat
            </button>
          )}
          <button onClick={() => setPanelOpen(false)} className="rounded-md p-1.5 text-muted-foreground hover:bg-accent hover:text-foreground">
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4">
        {messages.length === 0 && (
          <div className="flex h-full flex-col items-center justify-center text-center">
            <div className="mb-4 rounded-full bg-primary/10 p-4">
              <Bot className="h-8 w-8 text-primary" />
            </div>
            <h3 className="mb-1 text-sm font-semibold">How can I help?</h3>
            <p className="max-w-xs text-xs text-muted-foreground">
              Describe the partner you want to onboard and I'll extract the data, create the draft, and handle the setup.
            </p>
            <div className="mt-4 space-y-2 text-left">
              {[
                "Onboard a new individual partner named John Doe",
                "Create a corporate partner for ABC Corp Ltd",
                "Add a new partner: Sarah Johnson, female, born 1990-05-15",
              ].map((suggestion, i) => (
                <button
                  key={i}
                  onClick={() => {
                    setInput(suggestion)
                    setTimeout(() => {
                      handleSend()
                      if (textareaRef.current) textareaRef.current.style.height = "auto"
                    }, 100)
                  }}
                  className="block w-full rounded-lg border border-border px-3 py-2 text-left text-xs text-muted-foreground hover:bg-accent hover:text-foreground"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="space-y-4">
          {messages.map((msg) => (
            <div key={msg.id} className={`flex gap-3 ${msg.role === "user" ? "justify-end" : ""}`}>
              {renderMessageIcon(msg)}

              <div className={`max-w-[85%] ${msg.role === "user" ? "order-first" : ""}`}>
                <div
                  className={`rounded-lg px-3 py-2 text-sm ${
                    msg.role === "user"
                      ? "bg-primary text-primary-foreground"
                      : msg.status === "error"
                        ? "bg-destructive/10 text-destructive"
                        : "bg-accent text-accent-foreground"
                  }`}
                >
                  <p className="whitespace-pre-wrap">{msg.content}</p>
                </div>

                {/* Confirmation card */}
                {msg.data && (msg.data as unknown as AIPartnerResult).status === "ready" && (
                  renderConfirmationCard(msg.data as unknown as AIPartnerResult)
                )}

                {/* Missing fields card */}
                {msg.data && (msg.data as unknown as AIPartnerResult).missingRequired?.length ? (
                  renderMissingFields(msg.data as unknown as AIPartnerResult)
                ) : null}
              </div>
            </div>
          ))}

          {loading && (
            <div className="flex gap-3">
              <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary/10">
                <Bot className="h-4 w-4 text-primary" />
              </div>
              <div className="flex items-center gap-2 rounded-lg bg-accent px-3 py-2 text-sm text-muted-foreground">
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                {isClarifying ? "Processing..." : "Analyzing..."}
              </div>
            </div>
          )}

          {error && !loading && (
            <div className="flex items-center gap-2 rounded-lg bg-destructive/10 px-3 py-2 text-xs text-destructive">
              <AlertCircle className="h-3.5 w-3.5 shrink-0" />
              {error}
            </div>
          )}

          <div ref={bottomRef} />
        </div>
      </div>

      {/* Footer actions */}
      <div className="border-t border-border px-4 py-3">
        {confirming && !done && (
          <div className="mb-3 flex gap-2">
            <button onClick={handleConfirm} disabled={loading}
              className="flex flex-1 items-center justify-center gap-1.5 rounded-lg bg-primary px-3 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle className="h-4 w-4" />}
              Confirm & Create
            </button>
            <button onClick={() => { setConfirming(false); setLastResult(null) }}
              className="rounded-lg border border-border px-3 py-2 text-sm text-muted-foreground hover:bg-accent"
            >
              Cancel
            </button>
          </div>
        )}

        {/* Create with available data (shown during clarification) */}
        {isClarifying && lastResult && (
          <div className="mb-3">
            <button onClick={handleCreateWithAvailable} disabled={loading}
              className="flex w-full items-center justify-center gap-1.5 rounded-lg border border-primary/30 bg-primary/5 px-3 py-2 text-sm font-medium text-primary hover:bg-primary/10 disabled:opacity-50"
            >
              <ArrowRight className="h-4 w-4" />
              Create with available data (skip optional fields)
            </button>
            <p className="mt-1 text-center text-[10px] text-muted-foreground">
              Missing optional fields will be left empty. You can edit them later.
            </p>
          </div>
        )}

        {done && (
          <div className="mb-3 flex gap-2">
            <button onClick={handleNewChat}
              className="flex flex-1 items-center justify-center gap-1.5 rounded-lg bg-primary px-3 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
            >
              <Sparkles className="h-4 w-4" />
              New Partner
            </button>
            <button onClick={() => setPanelOpen(false)}
              className="flex-1 rounded-lg border border-border px-3 py-2 text-sm text-muted-foreground hover:bg-accent"
            >
              Close
            </button>
          </div>
        )}

        {!confirming && !done && (
          <div className="flex gap-2">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e: ChangeEvent<HTMLTextAreaElement>) => { setInput(e.target.value); autoResize() }}
              onKeyDown={(e: KeyboardEvent<HTMLTextAreaElement>) => {
                if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSubmit() }
              }}
              placeholder={inputPlaceholder}
              rows={1}
              className="min-w-0 flex-1 resize-none rounded-lg border border-input bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
              disabled={loading}
            />
            <button onClick={handleSubmit} disabled={!input.trim() || loading}
              className="self-end rounded-lg bg-primary p-2 text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              <Send className="h-4 w-4" />
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
