/** Shared formatting helpers for the Commitments UI (list, wizard, modals, detail). */

export function formatMoney(value: string | number | null | undefined, currency = "TZS"): string {
  if (value === null || value === undefined || value === "") return "—"
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) return String(value)
  try {
    return new Intl.NumberFormat("en-US", { style: "currency", currency, maximumFractionDigits: 2 }).format(numeric)
  } catch {
    return `${currency} ${numeric.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
  }
}

export function dateLabel(value?: string | null): string {
  if (!value) return "—"
  const parsed = new Date(`${String(value).slice(0, 10)}T00:00:00`)
  return Number.isNaN(parsed.getTime()) ? String(value) : new Intl.DateTimeFormat("en-GB", { dateStyle: "medium" }).format(parsed)
}

export function sourceLabel(sourceType?: string): string {
  switch (String(sourceType ?? "").toUpperCase()) {
    case "PROPOSAL": return "Proposal"
    case "POLICY": return "Policy"
    case "MANUAL": return "Manual"
    default: return String(sourceType ?? "—")
  }
}