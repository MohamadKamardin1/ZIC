import { useState, useEffect } from "react"
import { apiFetchAuth } from "../lib/api"
import { configCache } from "./ConfigurationCache"
import type { ChoicesResponse, WorkflowConfig } from "./ConfigurationTypes"

const CONFIG_BASE = "/api/v1/system-parameters/configuration"

async function extractData<T>(res: Response): Promise<T> {
  const json = await res.json()
  return json.data as T
}

export async function fetchAllChoices(): Promise<ChoicesResponse> {
  const res = await apiFetchAuth(`${CONFIG_BASE}/choices/`)
  if (!res.ok) throw new Error("Failed to load choices")
  return extractData<ChoicesResponse>(res)
}

export async function fetchChoiceList(code: string): Promise<{ value: string; label: string }[]> {
  const res = await apiFetchAuth(`${CONFIG_BASE}/choices/${code}/`)
  if (!res.ok) return []
  return extractData<{ value: string; label: string }[]>(res)
}

export async function fetchWorkflowConfig(): Promise<WorkflowConfig> {
  const res = await apiFetchAuth(`${CONFIG_BASE}/workflows/`)
  if (!res.ok) throw new Error("Failed to load workflow config")
  return extractData<WorkflowConfig>(res)
}

// Simple hook to fetch a single choice list
export function useChoiceList(listCode: string) {
  const [options, setOptions] = useState<{ value: string; label: string }[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    setLoading(true)
    
    fetchChoiceList(listCode)
      .then((data) => {
        if (!active) return
        setOptions(data)
        setError(null)
      })
      .catch((err) => {
        if (!active) return
        setError(err.message)
      })
      .finally(() => {
        if (!active) return
        setLoading(false)
      })
    
    return () => { active = false }
  }, [listCode])

  return { options, loading, error }
}

// Fetch all choices and cache them
export async function getCachedChoices(): Promise<ChoicesResponse | null> {
  const cached = configCache.get<ChoicesResponse>("choices")
  if (cached) return cached
  
  try {
    const choices = await fetchAllChoices()
    configCache.set("choices", choices)
    return choices
  } catch {
    return null
  }
}
