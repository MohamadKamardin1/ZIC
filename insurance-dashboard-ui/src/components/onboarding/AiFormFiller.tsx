import { useState, useRef, useEffect } from "react"
import { Sparkles, Send, Loader2, Bot, User, CheckCircle, AlertCircle, ArrowRight } from "lucide-react"
import { analyzePrompt, clarifyPrompt } from "../../lib/ai-api"
import type { AiAnalyzeResult } from "../../lib/ai-api"

interface FormFields {
  partnerType: string
  title: string
  firstName: string
  otherName: string
  surname: string
  gender: string
  dateOfBirth: string
  maritalStatus: string
  occupation: string
  nationality: string
  identificationType: string
  identificationNumber: string
  companyName: string
  tinNumber: string
  incorporationDate: string
  industry: string
  contactPerson: string
  contactPersonPhone: string
  contactPersonEmail: string
  email: string
  telephoneNumber: string
  mobileNumber: string
  physicalAddress: string
  postalAddress: string
  politicalRisk: string
  amlRisk: string
}

interface Props {
  onFill: (fields: Partial<FormFields>) => void
  disabled?: boolean
}

type Step = "idle" | "loading" | "ready" | "clarify"

export default function AiFormFiller({ onFill, disabled }: Props) {
  const [input, setInput] = useState("")
  const [step, setStep] = useState<Step>("idle")
  const [result, setResult] = useState<AiAnalyzeResult | null>(null)
  const [error, setError] = useState("")
  const [conversation, setConversation] = useState<{ role: "user" | "assistant"; text: string }[]>([])
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [conversation, step])

  const handleSend = async () => {
    const text = input.trim()
    if (!text || step === "loading") return
    setInput("")
    setError("")

    const isClarify = step === "clarify"
    setConversation((prev) => [...prev, { role: "user", text }])
    setStep("loading")

    try {
      let data: AiAnalyzeResult
      if (isClarify && result) {
        const allMissing = [...(result.missingRequired ?? []), ...(result.missingOptional ?? [])]
        data = await clarifyPrompt(text, allMissing, result.partnerData)
      } else {
        data = await analyzePrompt(text)
      }

      setResult(data)
      setConversation((prev) => [...prev, { role: "assistant", text: data.explanation || "Data extracted successfully." }])

      if (data.status === "ready") {
        setStep("ready")
      } else {
        setStep("clarify")
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : "AI service unavailable"
      setError(msg)
      setConversation((prev) => [...prev, { role: "assistant", text: `Error: ${msg}` }])
      setStep("idle")
    }
  }

  const handleApply = () => {
    if (!result || result.status !== "ready" || !result.partnerData) return

    const raw = result.partnerData as Record<string, string>
    const fields: Partial<FormFields> = {
      partnerType: result.partnerType ?? "",
      title: raw.title ?? "",
      firstName: raw.firstName ?? "",
      otherName: raw.otherName ?? "",
      surname: raw.surname ?? "",
      gender: raw.gender ?? "",
      dateOfBirth: raw.dateOfBirth ?? "",
      maritalStatus: raw.maritalStatus ?? "",
      occupation: raw.occupation ?? "",
      nationality: raw.nationality ?? "",
      identificationType: raw.identificationType ?? "",
      identificationNumber: raw.identificationNumber ?? "",
      companyName: raw.companyName ?? "",
      tinNumber: raw.tinNumber ?? "",
      incorporationDate: raw.incorporationDate ?? "",
      industry: raw.industry ?? "",
      contactPerson: raw.contactPerson ?? "",
      contactPersonPhone: raw.contactPersonPhone ?? "",
      contactPersonEmail: raw.contactPersonEmail ?? "",
      email: raw.email ?? "",
      telephoneNumber: raw.telephoneNumber ?? "",
      mobileNumber: raw.mobileNumber ?? "",
      physicalAddress: raw.physicalAddress ?? "",
      postalAddress: raw.postalAddress ?? "",
      politicalRisk: raw.politicalRisk ?? "",
      amlRisk: raw.amlRisk ?? "",
    }

    onFill(fields)
    setConversation((prev) => [...prev, { role: "assistant", text: "Form fields have been filled. Please review and save." }])
  }

  const handleReset = () => {
    setStep("idle")
    setResult(null)
    setError("")
    setConversation([])
    setInput("")
  }

  const renderFieldCard = () => {
    if (!result || result.status !== "ready" || !result.partnerData) return null
    const data = result.partnerData
    const type = result.partnerType

    return (
      <div className="rounded-lg border border-border bg-card p-3 text-xs">
        <p className="mb-2 font-semibold text-foreground">
          {type === "CORPORATE" ? "Corporate Partner" : "Individual Partner"}
        </p>
        <div className="space-y-1">
          {Object.entries(data).map(([key, value]) => {
            if (value === null || value === "") return null
            return (
              <div key={key} className="flex justify-between gap-2">
                <span className="shrink-0 capitalize text-muted-foreground">
                  {key.replace(/([A-Z])/g, " $1").trim()}
                </span>
                <span className="truncate font-medium text-foreground">{String(value)}</span>
              </div>
            )
          })}
        </div>
        {result.missingOptional && result.missingOptional.length > 0 && (
          <div className="mt-2 border-t border-border pt-2">
            <p className="mb-1 text-[10px] font-medium text-muted-foreground">Optional fields not provided:</p>
            <div className="flex flex-wrap gap-1">
              {result.missingOptional.map((f) => (
                <span key={f} className="rounded bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">
                  {f.replace(/([A-Z])/g, " $1").trim()}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    )
  }

  const renderMissingFields = () => {
    if (!result || !result.missingRequired?.length) return null
    return (
      <div className="space-y-1">
        {result.missingRequired.map((f) => (
          <div key={f} className="flex items-center gap-1.5 rounded bg-destructive/10 px-2 py-1 text-xs text-destructive">
            <AlertCircle className="h-3 w-3 shrink-0" />
            {f.replace(/([A-Z])/g, " $1").trim()}
          </div>
        ))}
      </div>
    )
  }

  return (
    <div className="flex h-full flex-col rounded-xl border border-border bg-card shadow-sm">
      {/* Header */}
      <div className="flex items-center gap-2 border-b border-border px-4 py-3">
        <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary/10">
          <Sparkles className="h-4 w-4 text-primary" />
        </div>
        <div className="flex-1">
          <h3 className="text-sm font-semibold text-foreground">AI Assistant</h3>
          <p className="text-[10px] text-muted-foreground">Describe the partner — I'll fill the form</p>
        </div>
        {conversation.length > 0 && (
          <button onClick={handleReset} className="text-[11px] text-muted-foreground hover:text-foreground">
            Reset
          </button>
        )}
      </div>

      {/* Body */}
      <div className="flex-1 space-y-3 overflow-y-auto px-4 py-3">
        {conversation.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center text-center">
            <div className="mb-3 rounded-full bg-primary/10 p-3">
              <Bot className="h-6 w-6 text-primary" />
            </div>
            <p className="mb-3 text-sm text-muted-foreground">
              Type a description and I'll extract partner data into the form.
            </p>
            <div className="w-full space-y-1.5">
              {[
                "John Doe, male, 1990-05-15, single, American, software engineer, john@email.com, +255712345678",
                "ABC Corp Ltd, TIN 12345-67890, technology industry, contact Peter, peter@abccorp.com",
              ].map((s, i) => (
                <button
                  key={i}
                  onClick={() => { setInput(s); setTimeout(handleSend, 50) }}
                  className="w-full rounded-lg border border-border px-3 py-2 text-left text-xs text-muted-foreground hover:bg-accent hover:text-foreground"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <>
            {conversation.map((msg, i) => (
              <div key={i} className={`flex gap-2 ${msg.role === "user" ? "justify-end" : ""}`}>
                {msg.role === "assistant" && (
                  <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary/10">
                    <Bot className="h-3.5 w-3.5 text-primary" />
                  </div>
                )}
                <div
                  className={`max-w-[85%] rounded-lg px-3 py-2 text-xs ${
                    msg.role === "user"
                      ? "bg-primary text-primary-foreground"
                      : "bg-accent text-accent-foreground"
                  }`}
                >
                  {msg.text}
                </div>
                {msg.role === "user" && (
                  <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary">
                    <User className="h-3.5 w-3.5 text-primary-foreground" />
                  </div>
                )}
              </div>
            ))}

            {step === "ready" && result && renderFieldCard()}
            {step === "clarify" && result && renderMissingFields()}

            {step === "loading" && (
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <Loader2 className="h-3 w-3 animate-spin" />
                Analyzing...
              </div>
            )}

            {error && (
              <div className="flex items-center gap-1.5 rounded bg-destructive/10 px-2.5 py-1.5 text-xs text-destructive">
                <AlertCircle className="h-3 w-3 shrink-0" />
                {error}
              </div>
            )}
          </>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Footer */}
      <div className="border-t border-border px-4 py-3">
        {step === "ready" && (
          <button
            onClick={handleApply}
            disabled={disabled}
            className="mb-2 flex w-full items-center justify-center gap-1.5 rounded-lg bg-primary py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
          >
            <CheckCircle className="h-4 w-4" />
            Apply to Form
          </button>
        )}

        {step !== "ready" && step !== "loading" && (
          <div className="flex gap-2">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend() }}}
              placeholder={step === "clarify" ? "Provide missing information..." : "Describe the partner..."}
              rows={1}
              className="min-w-0 flex-1 resize-none rounded-lg border border-input bg-background px-3 py-2 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
              disabled={disabled}
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || disabled}
              className="self-end rounded-lg bg-primary p-2 text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              <Send className="h-4 w-4" />
            </button>
          </div>
        )}

        {step === "clarify" && (
          <button
            onClick={handleReset}
            className="mt-1 text-center text-[10px] text-muted-foreground hover:text-foreground"
          >
            Start over
          </button>
        )}
      </div>
    </div>
  )
}
