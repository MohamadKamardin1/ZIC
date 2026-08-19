import { useEffect, useMemo, useState } from "react"
import { request } from "../../lib/apiClient"
import type { FilterOption } from "../../components/ui/types"

export type RemoteChoiceMap = Record<string, FilterOption[]>

type UnknownRecord = Record<string, unknown>

function asRecord(value: unknown): UnknownRecord {
  return value && typeof value === "object" && !Array.isArray(value) ? value as UnknownRecord : {}
}

function unwrap(value: unknown): unknown {
  const record = asRecord(value)
  return "data" in record ? record.data : value
}

function labelize(value: string) {
  return value.replace(/_/g, " ").toLowerCase().replace(/(^|\s)\S/g, (character: string) => character.toUpperCase())
}

function parseChoiceList(value: unknown): FilterOption[] {
  if (!Array.isArray(value)) return []
  return value.flatMap((item) => {
    const record = asRecord(item)
    const optionValue = record.value ?? record.id
    if (optionValue === undefined || optionValue === null || optionValue === "") return []
    const optionLabel = record.display_name ?? record.label ?? record.name ?? optionValue
    return [{ value: String(optionValue), label: String(optionLabel) }]
  })
}

function mergeOptions(...lists: FilterOption[][]): FilterOption[] {
  const seen = new Set<string>()
  return lists.flat().filter((option) => {
    if (seen.has(option.value)) return false
    seen.add(option.value)
    return true
  })
}

function readFieldChoices(payload: unknown, field: string): FilterOption[] {
  const record = asRecord(unwrap(payload))
  const actions = asRecord(record.actions)
  const post = asRecord(actions.POST)
  const fieldMeta = asRecord(post[field])
  const choices = parseChoiceList(fieldMeta.choices)
  if (choices.length) return choices
  const topLevel = asRecord(record[field])
  return parseChoiceList(topLevel.choices)
}

export function distinctRecordOptions(rows: UnknownRecord[], field: string): FilterOption[] {
  return mergeOptions(rows.flatMap((row) => {
    const value = row[field]
    if (value === undefined || value === null || value === "") return []
    const stringValue = String(value)
    return [{ value: stringValue, label: labelize(stringValue) }]
  }))
}

export function useRemoteChoices(endpoint: string, fields: string[], rows: UnknownRecord[] = []) {
  const [remote, setRemote] = useState<RemoteChoiceMap>({})
  const [loading, setLoading] = useState(true)
  const rowSignature = useMemo(() => rows.map((row) => fields.map((field) => String(row[field] ?? "")).join(":" )).join("|"), [fields, rows])

  useEffect(() => {
    let active = true
    setLoading(true)
    request<unknown>(endpoint, { method: "OPTIONS" }).then((payload) => {
      if (!active) return
      const next: RemoteChoiceMap = {}
      fields.forEach((field) => { next[field] = readFieldChoices(payload, field) })
      setRemote(next)
    }).catch(() => {
      if (active) setRemote({})
    }).finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [endpoint, fields])

  const choices = useMemo(() => Object.fromEntries(fields.map((field) => [field, mergeOptions(remote[field] ?? [], distinctRecordOptions(rows, field))])), [fields, remote, rowSignature, rows])
  return { choices, loading }
}

export function optionLabel(value: unknown, options: FilterOption[]) {
  if (value === null || value === undefined || value === "") return "—"
  return options.find((option) => option.value === String(value))?.label ?? labelize(String(value))
}
