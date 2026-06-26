import { apiFetchAuth } from "./api"

const AI_BASE = "/api/v1/ai"

export interface AiAnalyzeResult {
  status: "ready" | "needs_clarification"
  partnerType?: "INDIVIDUAL" | "CORPORATE"
  partnerData: Record<string, unknown>
  missingRequired: string[]
  missingOptional: string[]
  explanation: string
}

export async function analyzePrompt(prompt: string): Promise<AiAnalyzeResult> {
  const res = await apiFetchAuth(`${AI_BASE}/analyze-prompt/`, {
    method: "POST",
    body: JSON.stringify({ prompt }),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(body?.message ?? "AI service unavailable")
  }
  const json = await res.json()
  return json.data as AiAnalyzeResult
}

export async function clarifyPrompt(
  prompt: string,
  missingFields: string[],
  partialData: Record<string, unknown>,
): Promise<AiAnalyzeResult> {
  const res = await apiFetchAuth(`${AI_BASE}/clarify/`, {
    method: "POST",
    body: JSON.stringify({ prompt, missing_fields: missingFields, partial_data: partialData }),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(body?.message ?? "AI service unavailable")
  }
  const json = await res.json()
  return json.data as AiAnalyzeResult
}

export async function executePartnerCreation(
  partnerType: string,
  partnerData: Record<string, unknown>,
): Promise<unknown> {
  const res = await apiFetchAuth(`${AI_BASE}/execute/`, {
    method: "POST",
    body: JSON.stringify({ partner_type: partnerType, partner_data: partnerData }),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(body?.message ?? "Failed to create partner")
  }
  const json = await res.json()
  return json.data
}
