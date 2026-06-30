import { useQuery } from "@tanstack/react-query"
import { apiFetchAuth } from "../lib/api"

export interface ChoiceOption {
  value: string
  label: string
  description?: string
}

export function useChoices(listCode: string) {
  return useQuery<ChoiceOption[]>({
    queryKey: ["choices", listCode],
    queryFn: async () => {
      const response = await apiFetchAuth(`/api/v1/system-parameters/configuration/choices/${listCode}/`)
      if (!response.ok) throw new Error("Failed to load choices")
      const body = await response.json()
      console.log(`[useChoices] Debug response for ${listCode}:`, body)
      
      // The backend wraps responses in a standard structure { success, data, message, meta }
      // where `data` is the array of options directly.
      const optionsArray = Array.isArray(body.data) ? body.data : (body.options || [])
      console.log(`[useChoices] Extracted options array:`, optionsArray)
      
      return optionsArray.map((opt: any) => ({
        value: opt.code || opt.value,
        label: opt.label,
        description: opt.description,
      })) as ChoiceOption[]
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}

export function useMultipleChoices(listCodes: string[]) {
  return useQuery<Record<string, ChoiceOption[]>>({
    queryKey: ["choices", "multiple", listCodes],
    queryFn: async () => {
      const promises = listCodes.map((code) =>
        apiFetchAuth(`/api/v1/system-parameters/configuration/choices/${code}/`)
      )
      const responses = await Promise.all(promises)

      const result: Record<string, ChoiceOption[]> = {}
      for (let index = 0; index < responses.length; index++) {
        const response = responses[index]
        if (!response.ok) continue
        const body = await response.json()
        const optionsArray = Array.isArray(body.data) ? body.data : (body.options || [])
        result[listCodes[index]] = optionsArray.map((opt: any) => ({
          value: opt.code || opt.value,
          label: opt.label,
          description: opt.description,
        }))
      }

      return result
    },
    staleTime: 5 * 60 * 1000,
  })
}
