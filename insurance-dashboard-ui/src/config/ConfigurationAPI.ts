import { useState, useEffect } from "react"
import { apiFetchAuth } from "../lib/api"
import { configCache } from "./ConfigurationCache"
import type {
  ChoicesResponse,
  PartnerOnboardingConfiguration,
  WorkflowConfig,
} from "./ConfigurationTypes"

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

export async function fetchChoiceList(listCode: string): Promise<{ value: string; label: string }[]> {
  const res = await apiFetchAuth(`${CONFIG_BASE}/choices/${listCode}/`)
  if (!res.ok) return []
  return extractData<{ value: string; label: string }[]>(res)
}

export async function fetchWorkflowConfig(): Promise<WorkflowConfig> {
  const res = await apiFetchAuth(`${CONFIG_BASE}/workflows/`)
  if (!res.ok) throw new Error("Failed to load workflow config")
  return extractData<WorkflowConfig>(res)
}

export async function fetchPartnerOnboardingConfiguration(): Promise<PartnerOnboardingConfiguration> {
  const res = await apiFetchAuth(`${CONFIG_BASE}/partner-onboarding/`)
  if (!res.ok) throw new Error("Failed to load partner onboarding configuration")
  return extractData<PartnerOnboardingConfiguration>(res)
}

export function getConfiguredParameterValue(
  configuration: PartnerOnboardingConfiguration | null | undefined,
  code: string,
  fallback: unknown = undefined,
): unknown {
  if (!configuration) return fallback
  const visit = (groups: PartnerOnboardingConfiguration["groups"]): unknown => {
    for (const group of groups) {
      const match = group.parameters.find((parameter) => parameter.code === code && parameter.isActive)
      if (match) return match.value
      const nested = visit(group.children)
      if (nested !== undefined) return nested
    }
    return undefined
  }
  const value = visit(configuration.groups)
  return value === undefined || value === null ? fallback : value
}

export function clearPartnerOnboardingConfigurationCache() {
  configCache.clear("partner-onboarding")
}

export function usePartnerOnboardingConfiguration() {
  const [configuration, setConfiguration] = useState<PartnerOnboardingConfiguration | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    setLoading(true)
    const cached = configCache.get<PartnerOnboardingConfiguration>("partner-onboarding")
    if (cached) {
      setConfiguration(cached)
      setLoading(false)
      return () => { active = false }
    }

    fetchPartnerOnboardingConfiguration()
      .then((data) => {
        if (!active) return
        configCache.set("partner-onboarding", data)
        setConfiguration(data)
        setError(null)
      })
      .catch((err) => {
        if (!active) return
        setError(err instanceof Error ? err.message : "Failed to load configuration")
      })
      .finally(() => {
        if (active) setLoading(false)
      })

    return () => { active = false }
  }, [])

  return { configuration, loading, error }
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
