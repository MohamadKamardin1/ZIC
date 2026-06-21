import { useLitProps } from "../../lib/useLitProps"
import type {
  DebitedAmount,
  LeadItem,
  NotificationsData,
  PartnersOnboarded,
  PoliciesIssued,
  Quotations,
  ClaimGauge,
  TodoItem,
} from "../../lib/types"

const fill = { display: "block", height: "100%" } as const

export function PoliciesCard({ data }: { data: PoliciesIssued }) {
  const ref = useLitProps({ data })
  return <zic-policies-card ref={ref} style={fill} />
}

export function ClaimsCard({ data }: { data: ClaimGauge[] }) {
  const ref = useLitProps({ data })
  return <zic-claims-card ref={ref} style={fill} />
}

export function PartnersCard({ data }: { data: PartnersOnboarded }) {
  const ref = useLitProps({ data })
  return <zic-partners-card ref={ref} style={fill} />
}

export function DebitedGauge({ data }: { data: DebitedAmount }) {
  const ref = useLitProps({ data })
  return <zic-debited-gauge ref={ref} style={fill} />
}

export function QuotationsChart({ data }: { data: Quotations }) {
  const ref = useLitProps({ data })
  return <zic-quotations-chart ref={ref} style={fill} />
}

export function NotificationsPanel({ data }: { data: NotificationsData }) {
  const ref = useLitProps({ data })
  return <zic-notifications-panel ref={ref} style={fill} />
}

export function TodoLeads({ todos, leads }: { todos: TodoItem[]; leads: LeadItem[] }) {
  const ref = useLitProps({ todos, leads })
  return <zic-todo-leads ref={ref} style={fill} />
}

export function TodoWidget({ todos }: { todos: TodoItem[] }) {
  const ref = useLitProps({ todos })
  return <zic-todo ref={ref} style={fill} />
}

export function LeadsWidget({ leads }: { leads: LeadItem[] }) {
  const ref = useLitProps({ leads })
  return <zic-leads ref={ref} style={fill} />
}
