import { StatusBadge, type StatusTone } from "../ui/StatusBadge"
import type { CommitmentStatusOption } from "../../lib/commitments"

export interface CommitmentStatusMeta {
  code: string
  label: string
  tone: StatusTone
}

/** Parameter-driven tone inference for OL commitment status codes. */
export function commitmentStatusTone(status: string): StatusTone {
  const normalized = (status || "").toUpperCase()
  if (/CANCELLED|LAPSED|OVERDUE|FAILED|REJECTED/.test(normalized)) return "danger"
  if (/SUSPENDED|WAIVED|PARTIAL/.test(normalized)) return "warning"
  if (/COMPLETED|PAID|FULLY|FINAL/.test(normalized)) return "success"
  if (/REVIEW|APPROVAL|PROCESSING/.test(normalized)) return "info"
  if (/PENDING|ACTIVE|GRACE/.test(normalized)) return "warning"
  return "neutral"
}

export function commitmentStatusLabel(status: string): string {
  const code = (status || "").trim()
  if (!code) return "—"
  return code
    .split(/_+/)
    .filter(Boolean)
    .map((word) => `${word.charAt(0)}${word.slice(1).toLowerCase()}`)
    .join(" ")
}

export function commitmentStatusMeta(
  status: string,
  config?: CommitmentStatusOption[] | null,
): CommitmentStatusMeta {
  const code = (status || "").toUpperCase()
  const configured = config?.find((option) => (option.code || "").toUpperCase() === code)
  if (configured) {
    return {
      code: configured.code,
      label: configured.name || commitmentStatusLabel(code),
      tone: configured.tone ?? commitmentStatusTone(code),
    }
  }
  return { code, label: commitmentStatusLabel(code), tone: commitmentStatusTone(code) }
}

export function CommitmentStatusBadge({
  value,
  config,
  className = "",
}: {
  value: string
  config?: CommitmentStatusOption[] | null
  className?: string
}) {
  const meta = commitmentStatusMeta(value, config)
  return <StatusBadge value={meta.label} tone={meta.tone} className={className} />
}

export default CommitmentStatusBadge