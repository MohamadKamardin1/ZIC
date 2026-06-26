import { useEffect, useState } from "react"

type Handler = () => void

const listeners = new Map<string, Set<Handler>>()

export function emitDataChange(eventType: string) {
  const set = listeners.get(eventType)
  if (set) set.forEach((fn) => fn())
  const all = listeners.get("*")
  if (all) all.forEach((fn) => fn())
}

export function useDataRefresh(eventType: string, pollIntervalMs = 30_000): number {
  const [key, setKey] = useState(0)

  useEffect(() => {
    const handler = () => setKey((k) => k + 1)

    if (!listeners.has(eventType)) listeners.set(eventType, new Set())
    listeners.get(eventType)!.add(handler)

    const all = () => setKey((k) => k + 1)
    if (!listeners.has("*")) listeners.set("*", new Set())
    listeners.get("*")!.add(all)

    const interval = setInterval(handler, pollIntervalMs)

    return () => {
      listeners.get(eventType)?.delete(handler)
      listeners.get("*")?.delete(all)
      clearInterval(interval)
    }
  }, [eventType, pollIntervalMs])

  return key
}
