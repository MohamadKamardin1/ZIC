import { CheckCircle2, CircleAlert, CircleDot, Info, XCircle } from "lucide-react"

export type StatusTone = "success" | "info" | "warning" | "danger" | "neutral"

const toneMap: Record<StatusTone, { className: string; Icon: typeof CircleDot }> = {
  success: { className: "badge-success", Icon: CheckCircle2 },
  info: { className: "badge-info", Icon: Info },
  warning: { className: "badge-warning", Icon: CircleAlert },
  danger: { className: "badge-danger", Icon: XCircle },
  neutral: { className: "badge-neutral", Icon: CircleDot },
}

function inferTone(value: string): StatusTone {
  const normalized = value.toLowerCase()
  if (/active|approved|completed|converted|paid|success|ready|configured|finalized/.test(normalized)) return "success"
  if (/pending|review|warning|attention|draft/.test(normalized)) return "warning"
  if (/rejected|failed|expired|blocked|inactive|danger/.test(normalized)) return "danger"
  if (/info|processing|in progress|selected/.test(normalized)) return "info"
  return "neutral"
}

export function StatusBadge({ value, tone, className = "" }: { value: string; tone?: StatusTone; className?: string }) {
  const resolved = toneMap[tone ?? inferTone(value)]
  const Icon = resolved.Icon
  return (
    <span className={`${resolved.className} ${className}`} role="status">
      <Icon size={13} aria-hidden="true" />
      {value}
    </span>
  )
}
