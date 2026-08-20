export const UUID_RE = /\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b/i
const UUID_GLOBAL_RE = new RegExp(UUID_RE.source, "gi")

export function isUuid(value: unknown): value is string {
  return typeof value === "string" && UUID_RE.test(value.trim())
}

export function scrubUuids(value: unknown): string {
  return String(value).replace(UUID_GLOBAL_RE, "[identifier hidden]")
}

function candidateLabel(value: unknown): string | undefined {
  if (!value || typeof value !== "object" || Array.isArray(value)) return undefined
  const record = value as Record<string, unknown>
  for (const key of ["display", "display_name", "displayName", "label", "name", "code", "username", "legal_name", "description"]) {
    const candidate = record[key]
    if (candidate !== null && candidate !== undefined && candidate !== "" && !isUuid(candidate)) return scrubUuids(candidate)
  }
  return undefined
}

/**
 * Render a foreign-key-backed value without ever exposing a UUID to users.
 * Prefer the backend's *_display field, then a human-readable nested object label.
 */
export function renderFk(value: unknown, display?: unknown, fallback = "—"): string {
  const displayText = candidateLabel(display) ?? (display !== null && display !== undefined && display !== "" && !isUuid(display) ? scrubUuids(display) : undefined)
  if (displayText) return displayText
  const nestedText = candidateLabel(value)
  if (nestedText) return nestedText
  if (value === null || value === undefined || value === "") return fallback
  const raw = String(value)
  return isUuid(raw) ? fallback : scrubUuids(raw)
}

/** Replace identifier-like UUID strings in a user-visible object such as a version snapshot. */
export function sanitizeForDisplay(value: unknown): unknown {
  if (isUuid(value)) return "[identifier hidden]"
  if (typeof value === "string") return scrubUuids(value)
  if (Array.isArray(value)) return value.map(sanitizeForDisplay)
  if (!value || typeof value !== "object") return value
  return Object.fromEntries(Object.entries(value as Record<string, unknown>).map(([key, nested]) => [key, sanitizeForDisplay(nested)]))
}
