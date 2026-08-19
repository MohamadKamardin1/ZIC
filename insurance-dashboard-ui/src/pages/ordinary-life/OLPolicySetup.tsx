import { useCallback, useEffect, useMemo, useState, type ChangeEvent } from "react"
import { Plus } from "lucide-react"
import { request } from "../../lib/apiClient"
import { useAccess } from "../../lib/access"
import { DataTable, normalizeTableResponse } from "../../components/ui/DataTable"
import { FilterBar } from "../../components/ui/FilterBar"
import { FormModal, ConfirmModal, InfoBanner } from "../../components/ui/Overlays"
import { DateInput, DecimalInput, EditableGrid, TextInput, TextareaInput, Toggle } from "../../components/ui"
import { MasterDetailPage } from "../../components/ui/Patterns"
import { StatusBadge, type StatusTone } from "../../components/ui/StatusBadge"
import type { FilterValues } from "../../components/ui/FilterBar"
import type { EditableGridColumn } from "../../components/ui/EditableGrid"
import type { FilterDefinition, RowAction, TableColumn } from "../../components/ui/types"
import { useToast } from "../../components/ui/Toast"

const API_PREFIX = "/api/v1/ol-parameters"

type ScreenKey =
  | "rates"
  | "grace"
  | "status"
  | "renewal"
  | "beneficial"
  | "member"
  | "surrender"
  | "paidup"
  | "surrenderValueRate"
  | "paidupRate"
  | "commitment"
  | "healthQuestions"
  | "questionnaires"
  | "questionnaireBuilder"
  | "notificationSchedule"
  | "reinstatement"

type PolicyRecord = {
  id: string
  code: string
  name: string
  description?: string | null
  is_active: boolean
  effective_from: string
  effective_to?: string | null
  product?: string | null
  plan?: string | null
  installment_type?: string
  frequency?: string
  age_from?: number | null
  age_to?: number | null
  term_from?: number | null
  term_to?: number | null
  policy_year_from?: number | null
  policy_year_to?: number | null
  rate_factor?: string | number
  currency?: string
  premium_frequency?: string
  grace_days?: number
  warning_days?: number
  pre_lapse_days?: number
  lapse_days?: number
  minimum_due_amount?: string | number | null
  display_order?: number
  badge_type?: string
  is_terminal?: boolean
  allowed_transitions?: string[]
  renewal_action?: string
  category?: string
  calculation_basis?: string
  default_ratio?: string | number
  allows_multiple?: boolean
  cover_type?: string
  member_relation?: string
  min_age?: number | null
  max_age?: number | null
  waiting_period_days?: number
  benefit_limit?: string | number | null
  premium_basis?: string
  coverage_basis?: string
  minimum_premiums_paid?: number
  minimum_policy_months?: number
  minimum_premium_paid_ratio?: string | number
  surrender_charge_type?: string
  surrender_charge_value?: string | number
  partial_surrender_allowed?: boolean
  surrender_payout_days?: number
  require_approval?: boolean
  paidup_conversion_basis?: string
  allow_paidup?: boolean
  paidup_effective_rule?: string
  table_code?: string
  rate_table_version?: string
  gender?: string
  smoker_status?: string
  row_order?: number
  applies_to?: string
  question_text?: string
  answer_type?: string
  underwriting_impact?: string
  requires_medical_followup?: boolean
  applies_to_scope?: string
  scheme_code?: string
  version?: string
  sum_assured_threshold?: string | number | null
  age_threshold?: number | null
  questionnaire?: string
  health_question?: string
  sequence?: number
  mandatory?: boolean
  trigger_medical_requirement?: boolean
  score?: string | number | null
  event_type?: string
  days_offset?: number
  notification_channel?: string
  recipient_type?: string
  template_code?: string
  days_after_lapse?: number
  maximum_reinstatements?: number | null
  require_medical_underwriting?: boolean
  require_outstanding_premium_payment?: boolean
  interest_rate?: string | number | null
  penalty_rate?: string | number | null
}

type BuilderItem = PolicyRecord & { localId: string }

type EditorValue = string | number | boolean | string[] | null | undefined
type EditorState = Record<string, EditorValue>
type RateEditorRow = {
  age_from: string
  age_to: string
  term_from: string
  term_to: string
  policy_year_from: string
  policy_year_to: string
  rate_factor: string
  row_order: string
}

type CsvImportError = { row: number; message: string }

type ScreenConfig = {
  key: ScreenKey
  title: string
  description: string
  endpoint: string
  columns: TableColumn<PolicyRecord>[]
  filters: FilterDefinition[]
}

const today = () => new Date().toISOString().slice(0, 10)
const valueLabel = (value: unknown) => value === null || value === undefined || value === "" ? "—" : String(value)
const dateLabel = (value?: string | null) => value ? new Intl.DateTimeFormat("en-GB", { dateStyle: "medium" }).format(new Date(`${value}T00:00:00`)) : "Open ended"

function dateState(value?: string | null): { label: string; className: string } {
  if (!value) return { label: "Open ended", className: "text-[var(--muted-foreground)]" }
  if (value < today()) return { label: dateLabel(value), className: "font-semibold text-[var(--destructive)]" }
  if (value > today()) return { label: dateLabel(value), className: "font-semibold text-[var(--info)]" }
  return { label: dateLabel(value), className: "font-semibold text-[var(--success)]" }
}

function DateState({ value }: { value?: string | null }) {
  const state = dateState(value)
  return <span className={state.className}>{state.label}</span>
}

function badgeTone(value?: string): StatusTone {
  const normalized = String(value ?? "").toUpperCase()
  if (["POSITIVE", "SUCCESS", "GOOD", "APPROVED", "ACTIVE"].includes(normalized)) return "success"
  if (["WARNING", "PENDING", "ATTENTION", "SCHEDULED"].includes(normalized)) return "warning"
  if (["NEGATIVE", "DANGER", "ERROR", "REJECTED", "EXPIRED"].includes(normalized)) return "danger"
  if (["INFO", "INFORMATION"].includes(normalized)) return "info"
  return "neutral"
}

function activeTone(row: PolicyRecord): StatusTone {
  if (!row.is_active) return "danger"
  if (row.effective_to && row.effective_to < today()) return "danger"
  if (row.effective_from > today()) return "info"
  return "success"
}

const commonColumns = (extra: TableColumn<PolicyRecord>[]): TableColumn<PolicyRecord>[] => [
  { key: "code", label: "Code", field: "code", sortable: true },
  { key: "name", label: "Name", field: "name", sortable: true },
  ...extra,
  { key: "effective_from", label: "Effective from", field: "effective_from", sortable: true, render: (value) => <DateState value={value as string} /> },
  { key: "effective_to", label: "Effective to", field: "effective_to", sortable: true, render: (value) => <DateState value={value as string | null} /> },
  { key: "status", label: "Status", render: (_value, row) => <StatusBadge value={!row.is_active ? "Inactive" : row.effective_to && row.effective_to < today() ? "Expired" : row.effective_from > today() ? "Scheduled" : "Active"} tone={activeTone(row)} /> },
]

const rateColumns = (label: string): TableColumn<PolicyRecord>[] => commonColumns([
  { key: "table_code", label: "Table code", field: "table_code", sortable: true },
  { key: "rate_table_version", label: "Version", field: "rate_table_version", sortable: true },
  { key: "product", label: "Product", field: "product", sortable: true, render: (value) => valueLabel(value) },
  { key: "plan", label: "Plan", field: "plan", sortable: true, render: (value) => valueLabel(value) },
  { key: "gender", label: "Gender", field: "gender", sortable: true },
  { key: "smoker_status", label: "Smoker", field: "smoker_status", sortable: true },
  { key: "age", label: "Age range", render: (_value, row) => `${valueLabel(row.age_from)} – ${valueLabel(row.age_to)}` },
  { key: "term", label: "Term range", render: (_value, row) => `${valueLabel(row.term_from)} – ${valueLabel(row.term_to)}` },
  { key: "policy_year", label: "Policy year", render: (_value, row) => `${valueLabel(row.policy_year_from)} – ${valueLabel(row.policy_year_to)}` },
  { key: "rate_factor", label, field: "rate_factor", sortable: true, align: "right" },
])

const screens: Record<ScreenKey, ScreenConfig> = {
  rates: {
    key: "rates", title: "Anticipated Endowment Installment Rate", description: "Effective-dated rate factors by product, plan, frequency, age, term, policy year, and currency.", endpoint: `${API_PREFIX}/anticipated-endowment-rates/`,
    columns: commonColumns([
      { key: "product", label: "Product", field: "product", sortable: true, render: (value) => valueLabel(value) },
      { key: "plan", label: "Plan", field: "plan", sortable: true, render: (value) => valueLabel(value) },
      { key: "frequency", label: "Frequency", field: "frequency", sortable: true },
      { key: "age", label: "Age range", render: (_value, row) => `${valueLabel(row.age_from)} – ${valueLabel(row.age_to)}` },
      { key: "term", label: "Term range", render: (_value, row) => `${valueLabel(row.term_from)} – ${valueLabel(row.term_to)}` },
      { key: "policy_year", label: "Policy year", render: (_value, row) => `${valueLabel(row.policy_year_from)} – ${valueLabel(row.policy_year_to)}` },
      { key: "rate_factor", label: "Rate factor", field: "rate_factor", sortable: true, align: "right" },
    ]),
    filters: [
      { key: "product", label: "Product ID", type: "text", placeholder: "Product identifier" }, { key: "plan", label: "Plan ID", type: "text", placeholder: "Plan identifier" }, { key: "frequency", label: "Frequency", type: "text", placeholder: "Configured frequency" }, { key: "currency", label: "Currency", type: "text", placeholder: "ISO currency" }, { key: "is_active", label: "Active status", type: "text", placeholder: "true or false" },
    ],
  },
  grace: {
    key: "grace", title: "OL Grace Period", description: "Premium warning, grace, pre-lapse, and lapse timing by optional product scope.", endpoint: `${API_PREFIX}/grace-periods/`,
    columns: commonColumns([
      { key: "product", label: "Product", field: "product", sortable: true, render: (value) => valueLabel(value) }, { key: "plan", label: "Plan", field: "plan", sortable: true, render: (value) => valueLabel(value) }, { key: "premium_frequency", label: "Premium frequency", field: "premium_frequency", sortable: true }, { key: "grace_days", label: "Grace days", field: "grace_days", sortable: true, align: "right" }, { key: "warning_days", label: "Warning days", field: "warning_days", sortable: true, align: "right" }, { key: "pre_lapse_days", label: "Pre-lapse", field: "pre_lapse_days", sortable: true, align: "right" }, { key: "lapse_days", label: "Lapse days", field: "lapse_days", sortable: true, align: "right" },
    ]),
    filters: [{ key: "product", label: "Product ID", type: "text", placeholder: "Product identifier" }, { key: "plan", label: "Plan ID", type: "text", placeholder: "Plan identifier" }, { key: "premium_frequency", label: "Premium frequency", type: "text", placeholder: "Configured frequency" }, { key: "is_active", label: "Active status", type: "text", placeholder: "true or false" }],
  },
  status: {
    key: "status", title: "OL Policy Status", description: "Policy lifecycle status catalog with configured visual badges, terminal flags, and outgoing transitions.", endpoint: `${API_PREFIX}/policy-statuses/`,
    columns: commonColumns([{ key: "display_order", label: "Order", field: "display_order", sortable: true, align: "right" }, { key: "badge_type", label: "Configured badge", field: "badge_type", sortable: true, render: (value) => <StatusBadge value={valueLabel(value)} tone={badgeTone(String(value))} /> }, { key: "is_terminal", label: "Terminal", field: "is_terminal", render: (value) => <StatusBadge value={value ? "Terminal" : "Non-terminal"} tone={value ? "danger" : "neutral"} /> }, { key: "allowed_transitions", label: "Transitions", field: "allowed_transitions", render: (value) => valueLabel(Array.isArray(value) ? value.join(", ") : value) }]),
    filters: [{ key: "badge_type", label: "Badge type", type: "text", placeholder: "Configured badge" }, { key: "is_terminal", label: "Terminal", type: "text", placeholder: "true or false" }, { key: "is_active", label: "Active status", type: "text", placeholder: "true or false" }],
  },
  renewal: {
    key: "renewal", title: "OL Policy Renewal Status", description: "Renewal status catalog with ordered workflow states and parameter-driven actions.", endpoint: `${API_PREFIX}/policy-renewal-statuses/`, columns: commonColumns([{ key: "display_order", label: "Order", field: "display_order", sortable: true, align: "right" }, { key: "renewal_action", label: "Renewal action", field: "renewal_action", sortable: true }]), filters: [{ key: "renewal_action", label: "Renewal action", type: "text", placeholder: "Configured action" }, { key: "is_active", label: "Active status", type: "text", placeholder: "true or false" }],
  },
  beneficial: {
    key: "beneficial", title: "OL Beneficial Type", description: "Beneficiary and benefit type catalog with calculation basis, ratio defaults, and multiplicity rules.", endpoint: `${API_PREFIX}/beneficial-types/`, columns: commonColumns([{ key: "category", label: "Category", field: "category", sortable: true }, { key: "calculation_basis", label: "Calculation basis", field: "calculation_basis", sortable: true }, { key: "default_ratio", label: "Default ratio", field: "default_ratio", sortable: true, align: "right", render: (value) => `${valueLabel(value)}%` }, { key: "allows_multiple", label: "Multiple", field: "allows_multiple", render: (value) => <StatusBadge value={value ? "Allowed" : "Single"} tone={value ? "success" : "neutral"} /> }]), filters: [{ key: "category", label: "Category", type: "text", placeholder: "Configured category" }, { key: "calculation_basis", label: "Calculation basis", type: "text", placeholder: "Configured basis" }, { key: "is_active", label: "Active status", type: "text", placeholder: "true or false" }],
  },
  member: {
    key: "member", title: "OL Member Cover Configuration", description: "Effective-dated member and dependent eligibility, waiting period, premium basis, and benefit limits.", endpoint: `${API_PREFIX}/member-cover-configurations/`, columns: commonColumns([{ key: "product", label: "Product", field: "product", sortable: true, render: (value) => valueLabel(value) }, { key: "plan", label: "Plan", field: "plan", sortable: true, render: (value) => valueLabel(value) }, { key: "cover_type", label: "Cover type", field: "cover_type", sortable: true }, { key: "member_relation", label: "Relation", field: "member_relation", sortable: true }, { key: "age_range", label: "Age range", render: (_value, row) => `${valueLabel(row.min_age)} – ${valueLabel(row.max_age)}` }, { key: "waiting_period_days", label: "Waiting days", field: "waiting_period_days", sortable: true, align: "right" }, { key: "benefit_limit", label: "Benefit limit", field: "benefit_limit", sortable: true, align: "right" }]), filters: [{ key: "product", label: "Product ID", type: "text", placeholder: "Product identifier" }, { key: "plan", label: "Plan ID", type: "text", placeholder: "Plan identifier" }, { key: "cover_type", label: "Cover type", type: "text", placeholder: "Configured cover" }, { key: "member_relation", label: "Member relation", type: "text", placeholder: "Configured relation" }, { key: "is_active", label: "Active status", type: "text", placeholder: "true or false" }],
  },
  surrender: {
    key: "surrender", title: "OL Surrender Setup", description: "Surrender eligibility, charges, payout timing, partial surrender, and approval behavior.", endpoint: `${API_PREFIX}/surrender-setups/`, columns: commonColumns([{ key: "product", label: "Product", field: "product", sortable: true, render: (value) => valueLabel(value) }, { key: "plan", label: "Plan", field: "plan", sortable: true, render: (value) => valueLabel(value) }, { key: "minimum_policy_months", label: "Min months", field: "minimum_policy_months", sortable: true, align: "right" }, { key: "minimum_premiums_paid", label: "Min premiums", field: "minimum_premiums_paid", sortable: true, align: "right" }, { key: "minimum_premium_paid_ratio", label: "Min ratio", field: "minimum_premium_paid_ratio", sortable: true, align: "right", render: (value) => `${valueLabel(value)}%` }, { key: "surrender_charge_type", label: "Charge type", field: "surrender_charge_type", sortable: true }, { key: "surrender_charge_value", label: "Charge value", field: "surrender_charge_value", sortable: true, align: "right" }, { key: "partial_surrender_allowed", label: "Partial", field: "partial_surrender_allowed", render: (value) => <StatusBadge value={value ? "Allowed" : "Not allowed"} tone={value ? "success" : "neutral"} /> }, { key: "require_approval", label: "Approval", field: "require_approval", render: (value) => <StatusBadge value={value ? "Required" : "Not required"} tone={value ? "warning" : "neutral"} /> }]), filters: [{ key: "product", label: "Product ID", type: "text", placeholder: "Product identifier" }, { key: "plan", label: "Plan ID", type: "text", placeholder: "Plan identifier" }, { key: "surrender_charge_type", label: "Charge type", type: "text", placeholder: "Configured charge type" }, { key: "partial_surrender_allowed", label: "Partial surrender", type: "text", placeholder: "true or false" }, { key: "is_active", label: "Active status", type: "text", placeholder: "true or false" }],
  },
  paidup: {
    key: "paidup", title: "OL Paid-Up Setup", description: "Paid-up eligibility thresholds, conversion basis, and effective timing rules.", endpoint: `${API_PREFIX}/paid-up-setups/`, columns: commonColumns([{ key: "product", label: "Product", field: "product", sortable: true, render: (value) => valueLabel(value) }, { key: "plan", label: "Plan", field: "plan", sortable: true, render: (value) => valueLabel(value) }, { key: "minimum_policy_months", label: "Min months", field: "minimum_policy_months", sortable: true, align: "right" }, { key: "minimum_premiums_paid", label: "Min premiums", field: "minimum_premiums_paid", sortable: true, align: "right" }, { key: "paidup_conversion_basis", label: "Conversion basis", field: "paidup_conversion_basis", sortable: true }, { key: "paidup_effective_rule", label: "Effective rule", field: "paidup_effective_rule", sortable: true }, { key: "allow_paidup", label: "Allowed", field: "allow_paidup", render: (value) => <StatusBadge value={value ? "Allowed" : "Disabled"} tone={value ? "success" : "neutral"} /> }]), filters: [{ key: "product", label: "Product ID", type: "text", placeholder: "Product identifier" }, { key: "plan", label: "Plan ID", type: "text", placeholder: "Plan identifier" }, { key: "allow_paidup", label: "Allowed", type: "text", placeholder: "true or false" }, { key: "paidup_conversion_basis", label: "Conversion basis", type: "text", placeholder: "Configured basis" }, { key: "is_active", label: "Active status", type: "text", placeholder: "true or false" }],
  },
  surrenderValueRate: {
    key: "surrenderValueRate", title: "OL Surrender Value Rate", description: "Versioned, multi-dimensional surrender value factors with product, gender, smoker, age, term, and policy-year ranges.", endpoint: `${API_PREFIX}/surrender-value-rates/`, columns: rateColumns("Surrender factor"), filters: [{ key: "table_code", label: "Table code", type: "text", placeholder: "Rate table code" }, { key: "rate_table_version", label: "Version", type: "text", placeholder: "Version number" }, { key: "product", label: "Product ID", type: "text", placeholder: "Product identifier" }, { key: "plan", label: "Plan ID", type: "text", placeholder: "Plan identifier" }, { key: "gender", label: "Gender", type: "text", placeholder: "Configured gender" }, { key: "smoker_status", label: "Smoker", type: "text", placeholder: "Configured smoker status" }, { key: "is_active", label: "Active status", type: "text", placeholder: "true or false" }],
  },
  paidupRate: {
    key: "paidupRate", title: "OL Paid-Up Rate", description: "Versioned, multi-dimensional paid-up value factors with product, gender, smoker, age, term, and policy-year ranges.", endpoint: `${API_PREFIX}/paid-up-rates/`, columns: rateColumns("Paid-up factor"), filters: [{ key: "table_code", label: "Table code", type: "text", placeholder: "Rate table code" }, { key: "rate_table_version", label: "Version", type: "text", placeholder: "Version number" }, { key: "product", label: "Product ID", type: "text", placeholder: "Product identifier" }, { key: "plan", label: "Plan ID", type: "text", placeholder: "Plan identifier" }, { key: "gender", label: "Gender", type: "text", placeholder: "Configured gender" }, { key: "smoker_status", label: "Smoker", type: "text", placeholder: "Configured smoker status" }, { key: "is_active", label: "Active status", type: "text", placeholder: "true or false" }],
  },
  commitment: {
    key: "commitment", title: "OL Commitment Status", description: "Commitment status catalog with applicability, ordering, terminal-state behavior, and lifecycle badges.", endpoint: `${API_PREFIX}/commitment-statuses/`, columns: [{ key: "code", label: "Code", field: "code", sortable: true }, { key: "name", label: "Name", field: "name", sortable: true }, { key: "applies_to", label: "Applies to", field: "applies_to", sortable: true }, { key: "display_order", label: "Order", field: "display_order", sortable: true, align: "right" }, { key: "is_terminal", label: "Terminal", field: "is_terminal", render: (value) => <StatusBadge value={value ? "Terminal" : "Non-terminal"} tone={value ? "danger" : "neutral"} /> }, { key: "is_active", label: "Status", field: "is_active", render: (value) => <StatusBadge value={value ? "Active" : "Inactive"} tone={value ? "success" : "danger"} /> }], filters: [{ key: "applies_to", label: "Applies to", type: "text", placeholder: "Configured scope" }, { key: "is_terminal", label: "Terminal", type: "text", placeholder: "true or false" }, { key: "is_active", label: "Active status", type: "text", placeholder: "true or false" }],
  },
  healthQuestions: {
    key: "healthQuestions", title: "OL Health Questions", description: "Reusable underwriting health-question catalog with answer types and underwriting impact.", endpoint: `${API_PREFIX}/health-questions/`, columns: commonColumns([{ key: "question_text", label: "Question", field: "question_text", sortable: true }, { key: "category", label: "Category", field: "category", sortable: true }, { key: "answer_type", label: "Answer type", field: "answer_type", sortable: true }, { key: "underwriting_impact", label: "Underwriting impact", field: "underwriting_impact", sortable: true, render: (value) => <StatusBadge value={valueLabel(value)} tone={badgeTone(String(value))} /> }, { key: "requires_medical_followup", label: "Medical follow-up", field: "requires_medical_followup", render: (value) => <StatusBadge value={value ? "Required" : "Not required"} tone={value ? "warning" : "neutral"} /> }]), filters: [{ key: "category", label: "Category", type: "text", placeholder: "Question category" }, { key: "answer_type", label: "Answer type", type: "text", placeholder: "Configured answer type" }, { key: "underwriting_impact", label: "Underwriting impact", type: "text", placeholder: "Configured impact" }, { key: "is_active", label: "Active status", type: "text", placeholder: "true or false" }],
  },
  questionnaires: {
    key: "questionnaires", title: "OL Health Questionnaires", description: "Effective-dated, scoped questionnaire versions built from the active health-question catalog.", endpoint: `${API_PREFIX}/health-questionnaires/`, columns: commonColumns([{ key: "version", label: "Version", field: "version", sortable: true }, { key: "applies_to_scope", label: "Scope", field: "applies_to_scope", sortable: true, render: (value) => <StatusBadge value={valueLabel(value)} tone="info" /> }, { key: "product", label: "Product", field: "product", sortable: true, render: (value) => valueLabel(value) }, { key: "plan", label: "Plan", field: "plan", sortable: true, render: (value) => valueLabel(value) }, { key: "sum_assured_threshold", label: "Sum threshold", field: "sum_assured_threshold", sortable: true }, { key: "age_threshold", label: "Age threshold", field: "age_threshold", sortable: true }, { key: "version_state", label: "Version state", render: (_value, row) => <StatusBadge value={row.is_active && (!row.effective_to || row.effective_to >= today()) ? "Current" : "Superseded"} tone={row.is_active && (!row.effective_to || row.effective_to >= today()) ? "success" : "neutral"} /> }]), filters: [{ key: "applies_to_scope", label: "Scope", type: "text", placeholder: "GLOBAL, PRODUCT, PLAN, or SCHEME" }, { key: "version", label: "Version", type: "text", placeholder: "Version" }, { key: "product", label: "Product ID", type: "text", placeholder: "Product identifier" }, { key: "plan", label: "Plan ID", type: "text", placeholder: "Plan identifier" }, { key: "is_active", label: "Active status", type: "text", placeholder: "true or false" }],
  },
  questionnaireBuilder: {
    key: "questionnaireBuilder", title: "OL Health Questionnaire Builder", description: "Compose, order, version, and preview health-questionnaire items from the active catalog.", endpoint: `${API_PREFIX}/health-questionnaires/`, columns: [], filters: [],
  },
  notificationSchedule: {
    key: "notificationSchedule", title: "Grace Period Notification Schedule", description: "Effective-dated grace and lapse notification events, channels, and recipients.", endpoint: `${API_PREFIX}/grace-period-notification-schedules/`, columns: commonColumns([{ key: "event_type", label: "Event", field: "event_type", sortable: true }, { key: "days_offset", label: "Days offset", field: "days_offset", sortable: true, align: "right" }, { key: "notification_channel", label: "Channel", field: "notification_channel", sortable: true }, { key: "recipient_type", label: "Recipient", field: "recipient_type", sortable: true }, { key: "template_code", label: "Template", field: "template_code", sortable: true }]), filters: [{ key: "event_type", label: "Event type", type: "text", placeholder: "Configured event" }, { key: "notification_channel", label: "Channel", type: "text", placeholder: "Configured channel" }, { key: "recipient_type", label: "Recipient", type: "text", placeholder: "Configured recipient" }, { key: "is_active", label: "Active status", type: "text", placeholder: "true or false" }],
  },
  reinstatement: {
    key: "reinstatement", title: "Reinstallment / Reinstatement Window", description: "Lapse reinstatement eligibility, medical underwriting, repayment requirements, and interest or penalty rates.", endpoint: `${API_PREFIX}/reinstatement-windows/`, columns: commonColumns([{ key: "product", label: "Product", field: "product", sortable: true, render: (value) => valueLabel(value) }, { key: "plan", label: "Plan", field: "plan", sortable: true, render: (value) => valueLabel(value) }, { key: "days_after_lapse", label: "Days after lapse", field: "days_after_lapse", sortable: true, align: "right" }, { key: "maximum_reinstatements", label: "Max reinstatements", field: "maximum_reinstatements", sortable: true, align: "right" }, { key: "require_medical_underwriting", label: "Medical U/W", field: "require_medical_underwriting", render: (value) => <StatusBadge value={value ? "Required" : "Not required"} tone={value ? "warning" : "neutral"} /> }, { key: "interest_rate", label: "Interest %", field: "interest_rate", sortable: true, align: "right" }, { key: "penalty_rate", label: "Penalty %", field: "penalty_rate", sortable: true, align: "right" }]), filters: [{ key: "product", label: "Product ID", type: "text", placeholder: "Product identifier" }, { key: "plan", label: "Plan ID", type: "text", placeholder: "Plan identifier" }, { key: "require_medical_underwriting", label: "Medical U/W", type: "text", placeholder: "true or false" }, { key: "is_active", label: "Active status", type: "text", placeholder: "true or false" }],
  },
}

const emptyEditor = (screen: ScreenKey): EditorState => ({
  code: "", name: "", description: "", effective_from: today(), effective_to: "", is_active: true,
  ...(screen === "rates" ? { product: "", plan: "", installment_type: "ANTICIPATED_ENDOWMENT", frequency: "ANNUAL", currency: "" } : {}),
  ...(screen === "grace" ? { product: "", plan: "", premium_frequency: "", grace_days: 0, warning_days: 0, pre_lapse_days: 0, lapse_days: 0, minimum_due_amount: "" } : {}),
  ...(screen === "status" ? { display_order: 0, badge_type: "NEUTRAL", is_terminal: false } : {}),
  ...(screen === "renewal" ? { display_order: 0, renewal_action: "NONE" } : {}),
  ...(screen === "beneficial" ? { category: "", calculation_basis: "PERCENTAGE", default_ratio: "0", allows_multiple: true } : {}),
  ...(screen === "member" ? { product: "", plan: "", cover_type: "INDIVIDUAL", member_relation: "MEMBER", min_age: "", max_age: "", waiting_period_days: 0, benefit_limit: "", premium_basis: "MEMBER_PREMIUM", coverage_basis: "SUM_ASSURED" } : {}),
  ...(screen === "surrender" ? { product: "", plan: "", minimum_premiums_paid: 0, minimum_policy_months: 0, minimum_premium_paid_ratio: "0", surrender_charge_type: "NONE", surrender_charge_value: "0", partial_surrender_allowed: false, surrender_payout_days: 0, require_approval: true } : {}),
  ...(screen === "paidup" ? { product: "", plan: "", minimum_premiums_paid: 0, minimum_policy_months: 0, paidup_conversion_basis: "PROPORTIONAL", allow_paidup: true, paidup_effective_rule: "NEXT_ANNIVERSARY" } : {}),
  ...(screen === "surrenderValueRate" || screen === "paidupRate" ? { table_code: "", rate_table_version: "", product: "", plan: "", gender: "", smoker_status: "" } : {}),
  ...(screen === "commitment" ? { display_order: 0, applies_to: "COMMITMENT", is_terminal: false } : {}),
  ...(screen === "healthQuestions" ? { question_text: "", category: "", answer_type: "", underwriting_impact: "", requires_medical_followup: false } : {}),
  ...(screen === "questionnaires" || screen === "questionnaireBuilder" ? { applies_to_scope: "", product: "", plan: "", scheme_code: "", sum_assured_threshold: "", age_threshold: "", version: "1.0" } : {}),
  ...(screen === "notificationSchedule" ? { event_type: "", days_offset: 0, notification_channel: "", recipient_type: "", template_code: "" } : {}),
  ...(screen === "reinstatement" ? { product: "", plan: "", days_after_lapse: 1, maximum_reinstatements: "", require_medical_underwriting: false, require_outstanding_premium_payment: true, interest_rate: "", penalty_rate: "" } : {}),
})

const emptyRateRow = (): RateEditorRow => ({ age_from: "", age_to: "", term_from: "", term_to: "", policy_year_from: "", policy_year_to: "", rate_factor: "", row_order: "" })
const isRateScreen = (screen: ScreenKey) => ["rates", "surrenderValueRate", "paidupRate"].includes(screen)
const isVersionRateScreen = (screen: ScreenKey) => ["surrenderValueRate", "paidupRate"].includes(screen)

function toEditor(screen: ScreenKey, row: PolicyRecord): EditorState { return { ...emptyEditor(screen), ...row } }
function numberValue(value: string): number | null { if (value.trim() === "") return null; const parsed = Number(value); return Number.isFinite(parsed) ? parsed : null }
function cleanPayload(payload: Record<string, unknown>) { ;["product", "plan", "effective_to", "currency", "premium_frequency", "minimum_due_amount", "benefit_limit", "min_age", "max_age"].forEach((key) => { if (payload[key] === "") payload[key] = null }); return payload }

function validateRateRow(row: RateEditorRow): Record<string, string> {
  const errors: Record<string, string> = {}
  const ranges: Array<[keyof RateEditorRow, keyof RateEditorRow, string]> = [["age_from", "age_to", "Age"], ["term_from", "term_to", "Term"], ["policy_year_from", "policy_year_to", "Policy year"]]
  ranges.forEach(([from, to, label]) => { const lower = numberValue(row[from]); const upper = numberValue(row[to]); if (row[from] !== "" && lower === null) errors[from] = `${label} from must be numeric.`; if (row[to] !== "" && upper === null) errors[to] = `${label} to must be numeric.`; if (lower !== null && upper !== null && upper < lower) errors[to] = `${label} to cannot be less than ${label.toLowerCase()} from.`; if (label !== "Age" && lower !== null && lower < 1) errors[from] = `${label} from must be at least 1.` })
  if (row.rate_factor.trim() === "") errors.rate_factor = "Rate factor is required."; else if (Number.isNaN(Number(row.rate_factor)) || Number(row.rate_factor) < 0) errors.rate_factor = "Rate factor must be non-negative."
  if (row.row_order !== "" && (!Number.isInteger(Number(row.row_order)) || Number(row.row_order) < 0)) errors.row_order = "Row order must be a non-negative whole number."
  return errors
}

function EditorField({ label, name, value, onChange, error, required, type = "text", decimal = false }: { label: string; name: string; value: unknown; onChange: (event: ChangeEvent<HTMLInputElement>) => void; error?: string; required?: boolean; type?: string; decimal?: boolean }) {
  const Component = decimal ? DecimalInput : TextInput
  return <Component label={label} name={name} value={String(value ?? "")} onChange={onChange} error={error} required={required} type={type} />
}

function CommonEditorFields({ value, onChange, error }: { value: EditorState; onChange: (key: string, next: string | number | boolean | null) => void; error: (key: string) => string | undefined }) {
  const text = (key: string, label: string, required = false) => <EditorField label={label} name={key} value={value[key]} required={required} error={error(key)} onChange={(event) => onChange(key, event.target.value)} />
  return <>
    <div className="grid gap-4 sm:grid-cols-2">{text("code", "Code", true)}{text("name", "Name", true)}</div>
    <TextareaInput label="Description" name="description" value={String(value.description ?? "")} onChange={(event) => onChange("description", event.target.value)} />
    <div className="grid gap-4 sm:grid-cols-3"><DateInput label="Effective from" name="effective_from" required value={String(value.effective_from ?? "")} onChange={(event) => onChange("effective_from", event.target.value)} error={error("effective_from")} /><DateInput label="Effective to" name="effective_to" value={String(value.effective_to ?? "")} onChange={(event) => onChange("effective_to", event.target.value)} /><Toggle label="Active" checked={Boolean(value.is_active)} onChange={(checked) => onChange("is_active", checked)} /></div>
  </>
}

function RateEditor({ value, onChange, rateRows, setRateRows, error, versioned }: { value: EditorState; onChange: (key: string, next: string | number | boolean | null) => void; rateRows: RateEditorRow[]; setRateRows: (rows: RateEditorRow[]) => void; error: (key: string) => string | undefined; versioned: boolean }) {
  const rateColumns = useMemo<EditableGridColumn<RateEditorRow>[]>(() => {
    const input = (key: keyof RateEditorRow, label: string, decimal = false) => (row: RateEditorRow, _index: number, update: (patch: Partial<RateEditorRow>) => void) => <EditorField label={label} name={String(key)} value={row[key]} decimal={decimal} onChange={(event) => update({ [key]: event.target.value })} />
    return [{ key: "age_from", label: "Age from", width: "110px", render: input("age_from", "Age from") }, { key: "age_to", label: "Age to", width: "110px", render: input("age_to", "Age to") }, { key: "term_from", label: "Term from", width: "110px", render: input("term_from", "Term from") }, { key: "term_to", label: "Term to", width: "110px", render: input("term_to", "Term to") }, { key: "policy_year_from", label: "Year from", width: "110px", render: input("policy_year_from", "Year from") }, { key: "policy_year_to", label: "Year to", width: "110px", render: input("policy_year_to", "Year to") }, { key: "rate_factor", label: "Rate factor", width: "130px", render: input("rate_factor", "Rate factor", true) }, ...(versioned ? [{ key: "row_order", label: "Row order", width: "110px", render: input("row_order", "Row order") }] : [])]
  }, [versioned])
  const text = (key: string, label: string, required = false) => <EditorField label={label} name={key} value={value[key]} required={required} error={error(key)} onChange={(event) => onChange(key, event.target.value)} />
  return <div className="space-y-4">
    <CommonEditorFields value={value} onChange={onChange} error={error} />
    <div className="grid gap-4 sm:grid-cols-2">{versioned ? <>{text("table_code", "Table code", false)}{text("rate_table_version", "Rate table version", false)}{text("product", "Product ID", true)}{text("plan", "Plan ID")}{text("gender", "Gender")}{text("smoker_status", "Smoker status")}</> : <>{text("product", "Product ID", true)}{text("plan", "Plan ID")}{text("installment_type", "Installment type", true)}{text("frequency", "Frequency", true)}{text("currency", "Currency")}</>}</div>
    {versioned && <InfoBanner title="Version and overlap validation">Use the same table code and version for a coherent rate version. The backend rejects overlapping dimensions in an active version and returns any conflict as an inline save or import error.</InfoBanner>}
    {!versioned && <InfoBanner title="Rate row editor">Add one or more parameter-driven rows. The backend validates product/plan scope, range ordering, effective-date overlap, and decimal precision.</InfoBanner>}
    <EditableGrid rows={rateRows} columns={rateColumns} getRowId={(_row, index) => `rate-row-${index}`} createRow={emptyRateRow} onChange={setRateRows} validateRow={validateRateRow} />
  </div>
}

function PolicyStatusEditor({ value, onChange, allowedTransitions, setAllowedTransitions, transitionOptions, error }: { value: EditorState; onChange: (key: string, next: string | number | boolean | null) => void; allowedTransitions: string[]; setAllowedTransitions: (values: string[]) => void; transitionOptions: PolicyRecord[]; error: (key: string) => string | undefined }) {
  const toggleTransition = (code: string) => setAllowedTransitions(allowedTransitions.includes(code) ? allowedTransitions.filter((item) => item !== code) : [...allowedTransitions, code])
  return <div className="space-y-4"><CommonEditorFields value={value} onChange={onChange} error={error} /><div className="grid gap-4 sm:grid-cols-2"><EditorField label="Display order" name="display_order" value={value.display_order} type="number" onChange={(event) => onChange("display_order", Number(event.target.value))} /><EditorField label="Configured badge type" name="badge_type" value={value.badge_type} required error={error("badge_type")} onChange={(event) => onChange("badge_type", event.target.value)} /></div><Toggle label="Terminal status" checked={Boolean(value.is_terminal)} onChange={(checked) => onChange("is_terminal", checked)} /><div className="rounded-[10px] border p-4"><div className="mb-3"><p className="text-sm font-bold">Allowed transitions</p><p className="text-xs text-[var(--muted-foreground)]">Targets are loaded from the active Policy Status catalog. Terminal statuses must have no outgoing transitions.</p></div>{transitionOptions.length === 0 ? <p className="text-sm text-[var(--muted-foreground)]">No active policy statuses are available yet.</p> : <div className="grid gap-2 sm:grid-cols-2">{transitionOptions.filter((option) => option.code !== value.code).map((option) => <label key={option.id} className="flex items-center gap-3 rounded-md border px-3 py-2 text-sm"><input type="checkbox" checked={allowedTransitions.includes(option.code)} onChange={() => toggleTransition(option.code)} /> <span>{option.code}</span><span className="ml-auto text-xs text-[var(--muted-foreground)]">{option.name}</span></label>)}</div>}{error("allowed_transitions") && <p className="mt-2 text-xs font-medium text-[var(--destructive)]" role="alert">{error("allowed_transitions")}</p>}</div></div>
}

function PolicyEditor({ screen, value, onChange, rateRows, setRateRows, allowedTransitions, setAllowedTransitions, transitionOptions, error }: { screen: ScreenKey; value: EditorState; onChange: (key: string, next: string | number | boolean | null) => void; rateRows: RateEditorRow[]; setRateRows: (rows: RateEditorRow[]) => void; allowedTransitions: string[]; setAllowedTransitions: (values: string[]) => void; transitionOptions: PolicyRecord[]; error: (key: string) => string | undefined }) {
  if (screen === "rates") return <RateEditor value={value} onChange={onChange} rateRows={rateRows} setRateRows={setRateRows} error={error} versioned={false} />
  if (screen === "surrenderValueRate" || screen === "paidupRate") return <RateEditor value={value} onChange={onChange} rateRows={rateRows} setRateRows={setRateRows} error={error} versioned />
  if (screen === "status") return <PolicyStatusEditor value={value} onChange={onChange} allowedTransitions={allowedTransitions} setAllowedTransitions={setAllowedTransitions} transitionOptions={transitionOptions} error={error} />
  const text = (key: string, label: string, required = false) => <EditorField label={label} name={key} value={value[key]} required={required} error={error(key)} onChange={(event) => onChange(key, event.target.value)} />
  const numeric = (key: string, label: string, decimal = false) => <EditorField label={label} name={key} value={value[key]} decimal={decimal} type="number" error={error(key)} onChange={(event) => onChange(key, decimal ? event.target.value : Number(event.target.value))} />
  if (screen === "grace") return <div className="space-y-4"><CommonEditorFields value={value} onChange={onChange} error={error} /><div className="grid gap-4 sm:grid-cols-2">{text("product", "Product ID")}{text("plan", "Plan ID")}{text("premium_frequency", "Premium frequency")}{numeric("grace_days", "Grace days")}{numeric("warning_days", "Warning days")}{numeric("pre_lapse_days", "Pre-lapse days")}{numeric("lapse_days", "Lapse days")}{numeric("minimum_due_amount", "Minimum due amount", true)}</div><InfoBanner title="Timing validation">Grace, warning, and pre-lapse days cannot exceed the configured lapse days.</InfoBanner></div>
  if (screen === "renewal") return <div className="space-y-4"><CommonEditorFields value={value} onChange={onChange} error={error} /><div className="grid gap-4 sm:grid-cols-2">{numeric("display_order", "Display order")}{text("renewal_action", "Renewal action", true)}</div></div>
  if (screen === "beneficial") return <div className="space-y-4"><CommonEditorFields value={value} onChange={onChange} error={error} /><div className="grid gap-4 sm:grid-cols-2">{text("category", "Category", true)}{text("calculation_basis", "Calculation basis", true)}{numeric("default_ratio", "Default ratio (%)", true)}<Toggle label="Allows multiple" checked={Boolean(value.allows_multiple)} onChange={(checked) => onChange("allows_multiple", checked)} /></div><InfoBanner title="Ratio validation">Default ratio must be between 0 and 100 percent.</InfoBanner></div>
  if (screen === "member") return <div className="space-y-4"><CommonEditorFields value={value} onChange={onChange} error={error} /><div className="grid gap-4 sm:grid-cols-2">{text("product", "Product ID")}{text("plan", "Plan ID")}{text("cover_type", "Cover type", true)}{text("member_relation", "Member relation", true)}{numeric("min_age", "Minimum age")}{numeric("max_age", "Maximum age")}{numeric("waiting_period_days", "Waiting period days")}{numeric("benefit_limit", "Benefit limit", true)}{text("premium_basis", "Premium basis")}{text("coverage_basis", "Coverage basis")}</div><InfoBanner title="Eligibility validation">Maximum age cannot be less than minimum age, and benefit limits cannot be negative.</InfoBanner></div>
  if (screen === "healthQuestions") return <div className="space-y-4"><CommonEditorFields value={value} onChange={onChange} error={error} /><TextareaInput label="Question text" name="question_text" required value={String(value.question_text ?? "")} error={error("question_text")} onChange={(event) => onChange("question_text", event.target.value)} /><div className="grid gap-4 sm:grid-cols-2">{text("category", "Category")}{text("answer_type", "Answer type", true)}{text("underwriting_impact", "Underwriting impact", true)}</div><Toggle label="Requires medical follow-up" checked={Boolean(value.requires_medical_followup)} onChange={(checked) => onChange("requires_medical_followup", checked)} /></div>
  if (screen === "notificationSchedule") return <div className="space-y-4"><CommonEditorFields value={value} onChange={onChange} error={error} /><div className="grid gap-4 sm:grid-cols-2">{text("event_type", "Event type", true)}{numeric("days_offset", "Days offset")}{text("notification_channel", "Notification channel", true)}{text("recipient_type", "Recipient type", true)}{text("template_code", "Template code")}</div><InfoBanner title="Schedule validation">Days offset is relative to the configured event and must remain within the server-supported range.</InfoBanner></div>
  if (screen === "reinstatement") return <div className="space-y-4"><CommonEditorFields value={value} onChange={onChange} error={error} /><div className="grid gap-4 sm:grid-cols-2">{text("product", "Product ID")}{text("plan", "Plan ID")}{numeric("days_after_lapse", "Days after lapse", false)}{numeric("maximum_reinstatements", "Maximum reinstatements")}{numeric("interest_rate", "Interest rate (%)", true)}{numeric("penalty_rate", "Penalty rate (%)", true)}</div><div className="grid gap-4 sm:grid-cols-2"><Toggle label="Require medical underwriting" checked={Boolean(value.require_medical_underwriting)} onChange={(checked) => onChange("require_medical_underwriting", checked)} /><Toggle label="Require outstanding premium payment" checked={Boolean(value.require_outstanding_premium_payment)} onChange={(checked) => onChange("require_outstanding_premium_payment", checked)} /></div><InfoBanner title="Reinstatement validation">Days after lapse must be positive. Interest and penalty rates must remain between 0 and 100 percent.</InfoBanner></div>
  if (screen === "surrender") return <div className="space-y-4"><CommonEditorFields value={value} onChange={onChange} error={error} /><div className="grid gap-4 sm:grid-cols-2">{text("product", "Product ID")}{text("plan", "Plan ID")}{numeric("minimum_premiums_paid", "Minimum premiums paid")}{numeric("minimum_policy_months", "Minimum policy months")}{numeric("minimum_premium_paid_ratio", "Minimum premium ratio (%)", true)}{text("surrender_charge_type", "Surrender charge type")}{numeric("surrender_charge_value", "Surrender charge value", true)}{numeric("surrender_payout_days", "Surrender payout days")}</div><div className="grid gap-4 sm:grid-cols-2"><Toggle label="Partial surrender allowed" checked={Boolean(value.partial_surrender_allowed)} onChange={(checked) => onChange("partial_surrender_allowed", checked)} /><Toggle label="Require approval" checked={Boolean(value.require_approval)} onChange={(checked) => onChange("require_approval", checked)} /></div><InfoBanner title="Overlap warning">Active surrender setups with the same product and plan scope cannot overlap effective dates.</InfoBanner></div>
  if (screen === "paidup") return <div className="space-y-4"><CommonEditorFields value={value} onChange={onChange} error={error} /><div className="grid gap-4 sm:grid-cols-2">{text("product", "Product ID")}{text("plan", "Plan ID")}{numeric("minimum_premiums_paid", "Minimum premiums paid")}{numeric("minimum_policy_months", "Minimum policy months")}{text("paidup_conversion_basis", "Paid-up conversion basis")}{text("paidup_effective_rule", "Paid-up effective rule")}</div><Toggle label="Paid-up conversion allowed" checked={Boolean(value.allow_paidup)} onChange={(checked) => onChange("allow_paidup", checked)} /><InfoBanner title="Eligibility validation">When paid-up conversion is allowed, at least one premium or policy-month threshold is required.</InfoBanner></div>
  return <div className="space-y-4"><CommonEditorFields value={value} onChange={onChange} error={error} /><div className="grid gap-4 sm:grid-cols-2">{text("applies_to", "Applies to", true)}{numeric("display_order", "Display order")}</div><Toggle label="Terminal commitment status" checked={Boolean(value.is_terminal)} onChange={(checked) => onChange("is_terminal", checked)} /></div>
}

function validateEditor(screen: ScreenKey, value: EditorState, rateRows: RateEditorRow[], allowedTransitions: string[]): string | null {
  const required = ["code", "name", "effective_from"]
  if (screen === "rates") required.push("product", "installment_type", "frequency")
  if (screen === "surrenderValueRate" || screen === "paidupRate") required.push("product")
  if (screen === "status") required.push("badge_type")
  if (screen === "renewal") required.push("renewal_action")
  if (screen === "beneficial") required.push("category", "calculation_basis")
  if (screen === "member") required.push("cover_type", "member_relation")
  if (screen === "surrender" || screen === "paidup") required.push("product")
  if (screen === "commitment") required.push("applies_to")
  for (const key of required) if (!String(value[key] ?? "").trim()) return `${key.replace(/_/g, " ")} is required.`
  if ((screen === "surrenderValueRate" || screen === "paidupRate") && !String(value.table_code ?? "").trim() && !String(value.rate_table_version ?? "").trim()) return "Table code or rate table version is required."
  if (value.effective_to && String(value.effective_to) < String(value.effective_from)) return "effective to must be on or after effective from."
  if (isRateScreen(screen)) { if (!rateRows.length) return "At least one rate row is required."; const rowError = rateRows.map(validateRateRow).find((errors) => Object.keys(errors).length > 0); if (rowError) return Object.values(rowError)[0] }
  if (screen === "grace") { const lapse = Number(value.lapse_days); if (["grace_days", "warning_days", "pre_lapse_days"].some((key) => Number(value[key]) > lapse)) return "Grace, warning, and pre-lapse days cannot exceed lapse days."; if (Number(value.minimum_due_amount) < 0) return "Minimum due amount cannot be negative." }
  if (screen === "status" && Boolean(value.is_terminal) && allowedTransitions.length) return "Terminal policy statuses cannot have outgoing transitions."
  if (screen === "status" && allowedTransitions.some((code) => code.toUpperCase() === String(value.code).toUpperCase())) return "A policy status cannot transition to itself."
  if (screen === "beneficial" && (Number(value.default_ratio) < 0 || Number(value.default_ratio) > 100 || Number.isNaN(Number(value.default_ratio)))) return "Default ratio must be between 0 and 100."
  if (screen === "member" && value.min_age !== "" && value.max_age !== "" && Number(value.max_age) < Number(value.min_age)) return "Maximum age cannot be less than minimum age."
  if (screen === "member" && value.benefit_limit !== "" && Number(value.benefit_limit) < 0) return "Benefit limit cannot be negative."
  if (screen === "surrender" && (Number(value.minimum_premium_paid_ratio) < 0 || Number(value.minimum_premium_paid_ratio) > 100)) return "Minimum premium paid ratio must be between 0 and 100."
  if (screen === "surrender" && Number(value.surrender_charge_value) < 0) return "Surrender charge value cannot be negative."
  if (screen === "surrender" && String(value.surrender_charge_type).toUpperCase() === "NONE" && Number(value.surrender_charge_value) !== 0) return "A surrender charge value is not allowed when charge type is NONE."
  if (screen === "paidup" && Boolean(value.allow_paidup) && Number(value.minimum_premiums_paid) === 0 && Number(value.minimum_policy_months) === 0) return "At least one paid-up eligibility threshold is required when paid-up conversion is allowed."
  return null
}

function serializeEditor(value: EditorState, allowedTransitions: string[], rateRow?: RateEditorRow): Record<string, unknown> {
  const payload: Record<string, unknown> = { ...value }
  if (rateRow) { ;["age_from", "age_to", "term_from", "term_to", "policy_year_from", "policy_year_to"].forEach((key) => { payload[key] = numberValue(rateRow[key as keyof RateEditorRow]) }); payload.rate_factor = rateRow.rate_factor; payload.row_order = rateRow.row_order === "" ? 0 : Number(rateRow.row_order) }
  if (allowedTransitions) payload.allowed_transitions = allowedTransitions
  return cleanPayload(payload)
}

function parseCsvLine(line: string): string[] { const result: string[] = []; let current = ""; let quoted = false; for (let index = 0; index < line.length; index += 1) { const character = line[index]; if (character === '"' && line[index + 1] === '"' && quoted) { current += '"'; index += 1 } else if (character === '"') quoted = !quoted; else if (character === "," && !quoted) { result.push(current.trim()); current = "" } else current += character } result.push(current.trim()); return result }
function parseCsv(text: string): Record<string, string>[] { const lines = text.split(/\r?\n/).filter((line) => line.trim()); if (lines.length < 2) return []; const headers = parseCsvLine(lines[0]).map((header) => header.toLowerCase()); return lines.slice(1).map((line) => Object.fromEntries(parseCsvLine(line).map((value, index) => [headers[index], value]))) }

const rateImportFields = ["code", "name", "description", "effective_from", "effective_to", "is_active", "table_code", "rate_table_version", "product", "plan", "gender", "smoker_status", "age_from", "age_to", "term_from", "term_to", "policy_year_from", "policy_year_to", "rate_factor", "row_order"]

type QuestionnaireBuilderProps = {
  value: EditorState
  onChange: (key: string, next: EditorValue) => void
  items: BuilderItem[]
  catalog: PolicyRecord[]
  onItemsChange: (items: BuilderItem[]) => void
  error: (key: string) => string | undefined
  dirty: boolean
  saving: boolean
  isVersionCopy: boolean
  onCreateVersion: () => void
  onSave: () => void
}

function nextQuestionnaireVersion(version: string): string {
  const match = version.trim().match(/^(.*?)(\\d+(?:\\.\\d+)?)$/)
  if (!match) return `${version.trim() || "1"}.1`
  const prefix = match[1]
  const current = Number(match[2])
  return `${prefix}${(current + 0.1).toFixed(1)}`
}

function QuestionnaireBuilderPanel({ value, onChange, items, catalog, onItemsChange, error, dirty, saving, isVersionCopy, onCreateVersion, onSave }: QuestionnaireBuilderProps) {
  const available = catalog.filter((question) => !items.some((item) => item.health_question === question.id))
  const addQuestion = (question: PolicyRecord) => onItemsChange([...items, { ...question, localId: `new-${question.id}-${Date.now()}`, health_question: question.id, sequence: items.length + 1, mandatory: false, trigger_medical_requirement: false, score: "" }])
  const move = (index: number, direction: -1 | 1) => {
    const target = index + direction
    if (target < 0 || target >= items.length) return
    const next = [...items]
    const [moved] = next.splice(index, 1)
    next.splice(target, 0, moved)
    onItemsChange(next.map((item, itemIndex) => ({ ...item, sequence: itemIndex + 1 })))
  }
  const remove = (localId: string) => onItemsChange(items.filter((item) => item.localId !== localId).map((item, index) => ({ ...item, sequence: index + 1 })))
  const updateItem = (localId: string, patch: Partial<BuilderItem>) => onItemsChange(items.map((item) => item.localId === localId ? { ...item, ...patch } : item))
  return <div className="space-y-5">
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-[10px] border border-[var(--border)] bg-[var(--muted)]/30 p-4">
      <div><p className="text-sm font-bold">Questionnaire builder</p><p className="text-xs text-[var(--muted-foreground)]">Changes are held locally until you save the questionnaire header and its ordered items.</p></div>
      <div className="flex items-center gap-2">{dirty && <StatusBadge value="Unsaved changes" tone="warning" />}{isVersionCopy && <StatusBadge value="New version" tone="info" />}{value.is_active ? <StatusBadge value="Current" tone="success" /> : <StatusBadge value="Superseded" tone="neutral" />}</div>
    </div>
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1.1fr)_minmax(300px,0.9fr)]">
      <div className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-2"> <EditorField label="Code" name="questionnaire_code" value={value.code} required error={error("code")} onChange={(event) => onChange("code", event.target.value)} /> <EditorField label="Version" name="questionnaire_version" value={value.version} required error={error("version")} onChange={(event) => onChange("version", event.target.value)} /> </div>
        <TextareaInput label="Description" name="questionnaire_description" value={String(value.description ?? "")} onChange={(event) => onChange("description", event.target.value)} />
        <div className="grid gap-4 sm:grid-cols-2"><EditorField label="Scope" name="questionnaire_scope" value={value.applies_to_scope} required error={error("applies_to_scope")} onChange={(event) => onChange("applies_to_scope", event.target.value.toUpperCase())} /><EditorField label="Scheme code" name="questionnaire_scheme" value={value.scheme_code} error={error("scheme_code")} onChange={(event) => onChange("scheme_code", event.target.value)} /><EditorField label="Product ID" name="questionnaire_product" value={value.product} error={error("product")} onChange={(event) => onChange("product", event.target.value)} /><EditorField label="Plan ID" name="questionnaire_plan" value={value.plan} error={error("plan")} onChange={(event) => onChange("plan", event.target.value)} /></div>
        <div className="grid gap-4 sm:grid-cols-3"><EditorField label="Sum assured threshold" name="sum_assured_threshold" value={value.sum_assured_threshold} decimal error={error("sum_assured_threshold")} onChange={(event) => onChange("sum_assured_threshold", event.target.value)} /><EditorField label="Age threshold" name="age_threshold" value={value.age_threshold} type="number" error={error("age_threshold")} onChange={(event) => onChange("age_threshold", Number(event.target.value))} /><DateInput label="Effective from" name="questionnaire_effective_from" required value={String(value.effective_from ?? "")} error={error("effective_from")} onChange={(event) => onChange("effective_from", event.target.value)} /></div>
        <div className="grid gap-4 sm:grid-cols-2"><DateInput label="Effective to" name="questionnaire_effective_to" value={String(value.effective_to ?? "")} error={error("effective_to")} onChange={(event) => onChange("effective_to", event.target.value)} /><Toggle label="Current / active version" checked={Boolean(value.is_active)} onChange={(checked) => onChange("is_active", checked)} /></div>
        <div className="rounded-[10px] border border-[var(--border)] p-4"><div className="mb-3 flex items-center justify-between"><div><p className="text-sm font-bold">Add questions from catalog</p><p className="text-xs text-[var(--muted-foreground)]">Only active, unselected catalog questions are available.</p></div><span className="text-xs text-[var(--muted-foreground)]">{items.length} selected</span></div>{available.length === 0 ? <p className="text-sm text-[var(--muted-foreground)]">All available health questions are already included.</p> : <div className="grid gap-2 sm:grid-cols-2">{available.map((question) => <button key={question.id} type="button" className="rounded-md border border-[var(--border)] p-3 text-left transition hover:border-[var(--foreground)]" onClick={() => addQuestion(question)}><span className="block text-sm font-semibold">{question.code} · {question.question_text}</span><span className="mt-1 block text-xs text-[var(--muted-foreground)]">{valueLabel(question.category)} · {valueLabel(question.answer_type)}</span></button>)}</div>}</div>
        <div className="space-y-2">{items.length === 0 ? <InfoBanner title="No questions selected">Add at least one active health question to build this questionnaire.</InfoBanner> : items.map((item, index) => <div key={item.localId} className="rounded-[10px] border border-[var(--border)] p-3"><div className="flex flex-wrap items-start gap-3"><div className="flex h-8 w-8 items-center justify-center rounded-full bg-[var(--muted)] text-sm font-bold">{index + 1}</div><div className="min-w-0 flex-1"><p className="text-sm font-semibold">{item.code} · {item.question_text}</p><p className="text-xs text-[var(--muted-foreground)]">{valueLabel(item.category)} · {valueLabel(item.answer_type)} · impact {valueLabel(item.underwriting_impact)}</p></div><div className="flex items-center gap-1"><button type="button" className="button-secondary px-2 py-1 text-xs" disabled={index === 0} onClick={() => move(index, -1)} aria-label={`Move ${item.code} up`}>Up</button><button type="button" className="button-secondary px-2 py-1 text-xs" disabled={index === items.length - 1} onClick={() => move(index, 1)} aria-label={`Move ${item.code} down`}>Down</button><button type="button" className="button-secondary px-2 py-1 text-xs" onClick={() => remove(item.localId)} aria-label={`Remove ${item.code}`}>Remove</button></div></div><div className="mt-3 flex flex-wrap gap-4"><Toggle label="Mandatory" checked={Boolean(item.mandatory)} onChange={(checked) => updateItem(item.localId, { mandatory: checked })} /><Toggle label="Trigger medical" checked={Boolean(item.trigger_medical_requirement)} onChange={(checked) => updateItem(item.localId, { trigger_medical_requirement: checked })} /><EditorField label="Score" name={`score-${item.localId}`} value={item.score} decimal onChange={(event) => updateItem(item.localId, { score: event.target.value })} /></div></div>)}</div>
      </div>
      <aside className="rounded-[10px] border border-[var(--border)] bg-[var(--muted)]/20 p-4"><div className="mb-4 flex items-center justify-between"><div><p className="text-sm font-bold">Live questionnaire preview</p><p className="text-xs text-[var(--muted-foreground)]">Preview follows the current sequence and flags.</p></div><StatusBadge value={`${items.length} questions`} tone="info" /></div><div className="space-y-3">{items.length === 0 ? <p className="text-sm text-[var(--muted-foreground)]">Your preview will appear here as questions are added.</p> : items.map((item, index) => <div key={`preview-${item.localId}`} className="rounded-md bg-[var(--background)] p-3"><div className="flex gap-3"><span className="text-xs font-bold text-[var(--muted-foreground)]">{index + 1}.</span><div><p className="text-sm font-semibold">{item.question_text}</p><p className="mt-1 text-xs text-[var(--muted-foreground)]">{valueLabel(item.answer_type)}{item.mandatory ? " · Mandatory" : " · Optional"}{item.trigger_medical_requirement ? " · Medical review trigger" : ""}</p></div></div></div>)}</div><div className="mt-5 flex flex-wrap justify-end gap-2"><button type="button" className="button-primary" onClick={onSave} disabled={saving}>Save questionnaire</button>{!isVersionCopy && <button type="button" className="button-secondary" onClick={onCreateVersion} disabled={!value.id}>Create new version</button>}</div></aside>
    </div>
    {saving && <InfoBanner title="Saving questionnaire">The questionnaire header and ordered items are being persisted.</InfoBanner>}
  </div>
}

export default function OLPolicySetup() {
  const { access, canAccess } = useAccess()
  const { toast } = useToast()
  const [active, setActive] = useState<ScreenKey>("rates")
  const [filters, setFilters] = useState<FilterValues>({})
  const [refreshKey, setRefreshKey] = useState(0)
  const [saving, setSaving] = useState(false)
  const [editor, setEditor] = useState<{ open: boolean; row?: PolicyRecord; value: EditorState }>({ open: false, value: emptyEditor("rates") })
  const [rateRows, setRateRows] = useState<RateEditorRow[]>([emptyRateRow()])
  const [allowedTransitions, setAllowedTransitions] = useState<string[]>([])
  const [transitionOptions, setTransitionOptions] = useState<PolicyRecord[]>([])
  const [deactivateRow, setDeactivateRow] = useState<PolicyRecord | null>(null)
  const [csvImporting, setCsvImporting] = useState(false)
  const [importErrors, setImportErrors] = useState<CsvImportError[]>([])
  const [questionCatalog, setQuestionCatalog] = useState<PolicyRecord[]>([])
  const [questionnaireItems, setQuestionnaireItems] = useState<BuilderItem[]>([])
  const [questionnaireDirty, setQuestionnaireDirty] = useState(false)
  const [questionnaireVersionCopy, setQuestionnaireVersionCopy] = useState(false)
  const [questionnaireLoading, setQuestionnaireLoading] = useState(false)
  const screen = screens[active]

  const hasPermission = useCallback((permission: string) => { const [module, action] = permission.split("."); if (!access.permissions.length) return canAccess(module); return access.permissions.some((item) => item.module.toLowerCase() === module.toLowerCase() && item.action.toLowerCase() === action.toLowerCase()) }, [access.permissions, canAccess])
  const canManage = hasPermission("ol_parameters.create") || hasPermission("ol_parameters.update")
  const canDeactivate = hasPermission("ol_parameters.deactivate") || canManage
  const permissionKeys = access.permissions.map((item) => `${item.module}.${item.action}`)

  useEffect(() => { if (!editor.open || active !== "status") return; let mounted = true; request<unknown>(`${screens.status.endpoint}?is_active=true&page_size=100&ordering=display_order`).then((payload) => { if (mounted) setTransitionOptions(normalizeTableResponse<PolicyRecord>(payload).results) }).catch(() => { if (mounted) setTransitionOptions([]) }); return () => { mounted = false } }, [active, editor.open, refreshKey])

  useEffect(() => { if (active !== "questionnaireBuilder") return; let mounted = true; request<unknown>(`${screens.healthQuestions.endpoint}?is_active=true&page_size=200&ordering=category,code`).then((payload) => { if (mounted) setQuestionCatalog(normalizeTableResponse<PolicyRecord>(payload).results) }).catch(() => { if (mounted) setQuestionCatalog([]) }); return () => { mounted = false } }, [active, refreshKey])

  useEffect(() => { if (!questionnaireDirty) return; const handleBeforeUnload = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = "" }; window.addEventListener("beforeunload", handleBeforeUnload); return () => window.removeEventListener("beforeunload", handleBeforeUnload) }, [questionnaireDirty])

  const fetcher = useCallback(async (query: { page?: number; pageSize?: number; search?: string; ordering?: string; filters?: Record<string, string | number | boolean | null | undefined> }) => { const params = new URLSearchParams(); if (query.page) params.set("page", String(query.page)); if (query.pageSize) params.set("page_size", String(query.pageSize)); if (query.search) params.set("search", query.search); if (query.ordering) params.set("ordering", query.ordering); Object.entries(query.filters ?? {}).forEach(([key, value]) => { if (value !== undefined && value !== null && value !== "") params.set(key, String(value)) }); return normalizeTableResponse<PolicyRecord>(await request<unknown>(`${screen.endpoint}?${params.toString()}`)) }, [screen.endpoint])

  const openQuestionnaireBuilder = async (row?: PolicyRecord, clone = false) => {
    setActive("questionnaireBuilder")
    setQuestionnaireVersionCopy(clone)
    setQuestionnaireDirty(false)
    setQuestionnaireItems([])
    if (!row) {
      setEditor({ open: false, value: emptyEditor("questionnaireBuilder") })
      return
    }
    setQuestionnaireLoading(true)
    try {
      const [itemsPayload] = await Promise.all([request<unknown>(`${API_PREFIX}/health-questionnaire-items/?questionnaire=${row.id}&is_active=true&page_size=200&ordering=sequence`), request<unknown>(`${screens.healthQuestions.endpoint}?is_active=true&page_size=200&ordering=category,code`).then((payload) => setQuestionCatalog(normalizeTableResponse<PolicyRecord>(payload).results))])
      const items = normalizeTableResponse<PolicyRecord>(itemsPayload).results.map((item) => ({ ...item, localId: `item-${item.id}` }))
      const value = toEditor("questionnaireBuilder", row)
      if (clone) {
        value.id = undefined
        value.version = nextQuestionnaireVersion(String(row.version ?? "1.0"))
        value.effective_from = today()
        value.effective_to = ""
        value.is_active = true
      }
      setEditor({ open: false, row: clone ? undefined : row, value })
      setQuestionnaireItems(clone ? items.map((item, index) => ({ ...item, localId: `copy-${item.id ?? index}-${Date.now()}`, sequence: index + 1 })) : items)
    } catch (error) {
      toast({ tone: "danger", title: "Questionnaire load failed", message: error instanceof Error ? error.message : "The questionnaire could not be loaded." })
    } finally {
      setQuestionnaireLoading(false)
    }
  }

  const openCreate = () => {
    if (active === "questionnaires" || active === "questionnaireBuilder") {
      void openQuestionnaireBuilder()
      return
    }
    setEditor({ open: true, value: emptyEditor(active) }); setRateRows([emptyRateRow()]); setAllowedTransitions([]); setImportErrors([])
  }
  const rowToRate = (row: PolicyRecord): RateEditorRow => ({ age_from: row.age_from === null || row.age_from === undefined ? "" : String(row.age_from), age_to: row.age_to === null || row.age_to === undefined ? "" : String(row.age_to), term_from: row.term_from === null || row.term_from === undefined ? "" : String(row.term_from), term_to: row.term_to === null || row.term_to === undefined ? "" : String(row.term_to), policy_year_from: row.policy_year_from === null || row.policy_year_from === undefined ? "" : String(row.policy_year_from), policy_year_to: row.policy_year_to === null || row.policy_year_to === undefined ? "" : String(row.policy_year_to), rate_factor: row.rate_factor === null || row.rate_factor === undefined ? "" : String(row.rate_factor), row_order: row.row_order === null || row.row_order === undefined ? "" : String(row.row_order) })
  const openEdit = (row: PolicyRecord) => { if (active === "questionnaires") { void openQuestionnaireBuilder(row); return } setEditor({ open: true, row, value: toEditor(active, row) }); setRateRows(isRateScreen(active) ? [rowToRate(row)] : [emptyRateRow()]); setAllowedTransitions(active === "status" ? row.allowed_transitions ?? [] : []); setImportErrors([]) }
  const updateQuestionnaireItems = (items: BuilderItem[]) => { setQuestionnaireItems(items); setQuestionnaireDirty(true) }
  const updateQuestionnaire = (key: string, next: EditorValue) => { setEditor((current) => ({ ...current, value: { ...current.value, [key]: next } })); setQuestionnaireDirty(true) }
  const saveQuestionnaire = async () => {
    const validationMessage = validateEditor("questionnaireBuilder", editor.value, [], [])
    if (validationMessage) { toast({ tone: "danger", title: "Check the questionnaire", message: validationMessage }); return }
    if (!questionnaireItems.length) { toast({ tone: "danger", title: "Add questions", message: "At least one health question is required." }); return }
    setQuestionnaireLoading(true)
    try {
      const headerPayload = cleanPayload({ code: editor.value.code, name: editor.value.name || editor.value.code, description: editor.value.description, effective_from: editor.value.effective_from, effective_to: editor.value.effective_to, is_active: editor.value.is_active, applies_to_scope: editor.value.applies_to_scope, product: editor.value.product, plan: editor.value.plan, scheme_code: editor.value.scheme_code, sum_assured_threshold: editor.value.sum_assured_threshold, age_threshold: editor.value.age_threshold, version: editor.value.version })
      const headerPath = editor.row ? `${screens.questionnaires.endpoint}${editor.row.id}/` : screens.questionnaires.endpoint
      const saved = await request<PolicyRecord>(headerPath, { method: editor.row ? "PATCH" : "POST", body: JSON.stringify(headerPayload) })
      const questionnaireId = saved.id ?? editor.row?.id
      if (!questionnaireId) throw new Error("The saved questionnaire did not return an identifier.")
      for (const [index, item] of questionnaireItems.entries()) {
        const itemPayload = cleanPayload({ code: item.code || `${editor.value.code}-${index + 1}`, name: item.name || item.question_text || `Question ${index + 1}`, description: item.question_text, questionnaire: questionnaireId, health_question: item.health_question || item.id, sequence: index + 1, mandatory: Boolean(item.mandatory), trigger_medical_requirement: Boolean(item.trigger_medical_requirement), score: item.score })
        const path = item.id && !questionnaireVersionCopy ? `${API_PREFIX}/health-questionnaire-items/${item.id}/` : `${API_PREFIX}/health-questionnaire-items/`
        await request(path, { method: item.id && !questionnaireVersionCopy ? "PATCH" : "POST", body: JSON.stringify(itemPayload) })
      }
      toast({ tone: "success", title: "Questionnaire saved", message: `${editor.value.code} version ${editor.value.version} is ready.` })
      setQuestionnaireDirty(false); setQuestionnaireVersionCopy(false); setRefreshKey((current) => current + 1); setActive("questionnaires")
    } catch (error) {
      toast({ tone: "danger", title: "Questionnaire save failed", message: error instanceof Error ? error.message : "The questionnaire could not be saved." })
    } finally { setQuestionnaireLoading(false) }
  }
  const closeEditor = () => { if (!saving) setEditor({ open: false, value: emptyEditor(active) }) }
  const updateEditor = (key: string, next: string | number | boolean | null) => setEditor((current) => ({ ...current, value: { ...current.value, [key]: next } }))
  const editorError = (key: string) => { const value = editor.value[key]; if (["code", "name", "effective_from"].includes(key) && !String(value ?? "").trim()) return "This field is required."; if (["product", "installment_type", "frequency", "badge_type", "renewal_action", "category", "calculation_basis", "cover_type", "member_relation", "applies_to"].includes(key) && !String(value ?? "").trim()) return "This field is required."; if ((active === "surrenderValueRate" || active === "paidupRate") && key === "table_code" && !String(value ?? "").trim() && !String(editor.value.rate_table_version ?? "").trim()) return "Table code or version is required."; if (key === "effective_to" && value && String(value) < String(editor.value.effective_from)) return "Effective to must be on or after effective from."; if (active === "beneficial" && key === "default_ratio" && (Number(value) < 0 || Number(value) > 100)) return "Enter a value between 0 and 100."; if (active === "surrender" && key === "minimum_premium_paid_ratio" && (Number(value) < 0 || Number(value) > 100)) return "Enter a value between 0 and 100."; if (active === "member" && key === "max_age" && editor.value.min_age !== "" && value !== "" && Number(value) < Number(editor.value.min_age)) return "Maximum age cannot be less than minimum age."; return undefined }

  const saveEditor = async () => {
    const validationMessage = validateEditor(active, editor.value, rateRows, allowedTransitions)
    if (validationMessage) {
      toast({ tone: "danger", title: "Check the form", message: validationMessage })
      return
    }
    try {
      setSaving(true)
      if (isRateScreen(active)) {
        if (editor.row) {
          await request(`${screen.endpoint}${editor.row.id}/`, {
            method: "PATCH",
            body: JSON.stringify(serializeEditor(editor.value, [], rateRows[0])),
          })
          for (const extraRow of rateRows.slice(1)) {
            await request(screen.endpoint, {
              method: "POST",
              body: JSON.stringify(serializeEditor(editor.value, [], extraRow)),
            })
          }
        } else {
          for (const rateRow of rateRows) {
            await request(screen.endpoint, {
              method: "POST",
              body: JSON.stringify(serializeEditor(editor.value, [], rateRow)),
            })
          }
        }
      } else {
        const payload = serializeEditor(editor.value, active === "status" ? allowedTransitions : [])
        const path = editor.row ? `${screen.endpoint}${editor.row.id}/` : screen.endpoint
        await request(path, {
          method: editor.row ? "PATCH" : "POST",
          body: JSON.stringify(payload),
        })
      }
      toast({ tone: "success", title: editor.row ? "Setup updated" : "Setup created", message: `${screen.title} saved successfully.` })
      closeEditor()
      setRefreshKey((current) => current + 1)
    } catch (error) {
      toast({ tone: "danger", title: "Save failed", message: error instanceof Error ? error.message : "The setup could not be saved." })
    } finally {
      setSaving(false)
    }
  }

  const importCsv = async (file: File) => {
    if (!isVersionRateScreen(active)) return
    setCsvImporting(true); setImportErrors([])
    try { const records = parseCsv(await file.text()); if (!records.length) { setImportErrors([{ row: 1, message: "The CSV must contain a header row and at least one data row." }]); return }; const errors: CsvImportError[] = []; for (const [index, record] of records.entries()) { const payload: Record<string, unknown> = {}; rateImportFields.forEach((field) => { if (record[field] !== undefined) payload[field] = record[field] }); ["age_from", "age_to", "term_from", "term_to", "policy_year_from", "policy_year_to", "row_order"].forEach((field) => { if (payload[field] === "") payload[field] = null }); if (payload.is_active !== undefined) payload.is_active = String(payload.is_active).toLowerCase() !== "false"; try { await request(screen.endpoint, { method: "POST", body: JSON.stringify(cleanPayload(payload)) }) } catch (error) { errors.push({ row: index + 2, message: error instanceof Error ? error.message : "The backend rejected this row." }) } } setImportErrors(errors); setRefreshKey((current) => current + 1); toast({ tone: errors.length ? "warning" : "success", title: errors.length ? "CSV imported with errors" : "CSV imported", message: errors.length ? `${records.length - errors.length} row(s) imported; ${errors.length} row(s) require attention.` : `${records.length} rate row(s) imported successfully.` }) } catch (error) { setImportErrors([{ row: 1, message: error instanceof Error ? error.message : "The CSV could not be read." }]) } finally { setCsvImporting(false) }
  }

  const deactivate = async () => { if (!deactivateRow) return; try { await request(`${screen.endpoint}${deactivateRow.id}/deactivate/`, { method: "POST" }); toast({ tone: "success", title: "Setup deactivated", message: `${deactivateRow.code} is now inactive.` }); setDeactivateRow(null); setRefreshKey((current) => current + 1) } catch (error) { toast({ tone: "danger", title: "Deactivation failed", message: error instanceof Error ? error.message : "The setup could not be deactivated." }) } }
  const actions = useMemo<RowAction<PolicyRecord>[]>(() => {
    const base: RowAction<PolicyRecord>[] = [{ key: "edit", label: "Edit", permission: "ol_parameters.update", onSelect: openEdit }, { key: "deactivate", label: "Deactivate", permission: "ol_parameters.deactivate", tone: "danger", isVisible: (row) => row.is_active, onSelect: setDeactivateRow }]
    if (active === "questionnaires") base.unshift({ key: "builder", label: "Open builder", permission: "ol_parameters.update", onSelect: openEdit }, { key: "version", label: "Create new version", permission: "ol_parameters.create", isVisible: (row) => Boolean(row.id), onSelect: (row) => void openQuestionnaireBuilder(row, true) })
    return base
  }, [active])
  const changeTab = (id: string) => {
    if (questionnaireDirty && id !== "questionnaireBuilder" && !window.confirm("You have unsaved questionnaire changes. Leave without saving?")) return
    setActive(id as ScreenKey); setFilters({}); setImportErrors([]); if (id !== "questionnaireBuilder") { setQuestionnaireDirty(false); setQuestionnaireItems([]) }
  }
  const stats = [{ label: "Workspace", value: screen.title, helper: "Backend parameter registry" }, { label: "Access", value: canManage ? "Configure" : "Read only", helper: canDeactivate ? "Deactivation available" : "No mutation permission" }]

  return <MasterDetailPage eyebrow="Ordinary Life Parameters / Policy Setup" title={screen.title} description={screen.description} stats={stats} tabs={Object.values(screens).map((item) => ({ id: item.key, label: item.title }))} activeTab={active} onTabChange={changeTab} actions={canManage && active !== "questionnaireBuilder" ? <button type="button" className="button-primary" onClick={openCreate}><Plus size={16} aria-hidden="true" /> New setup</button> : active === "questionnaireBuilder" && canManage ? <button type="button" className="button-secondary" onClick={() => changeTab("questionnaires")}>Back to questionnaires</button> : undefined}>
    <div className="space-y-4">
      {!hasPermission("ol_parameters.view") && <InfoBanner title="Read access required">Your current IAM access metadata does not include the OL parameter view permission.</InfoBanner>}
      {active === "questionnaireBuilder" ? <QuestionnaireBuilderPanel value={editor.value} onChange={updateQuestionnaire} items={questionnaireItems} catalog={questionCatalog} onItemsChange={updateQuestionnaireItems} error={editorError} dirty={questionnaireDirty} saving={questionnaireLoading} isVersionCopy={questionnaireVersionCopy} onCreateVersion={() => { if (editor.row) void openQuestionnaireBuilder(editor.row, true) }} onSave={() => void saveQuestionnaire()} /> : <>
        {csvImporting && <InfoBanner title="CSV import in progress">Rows are being validated and submitted one at a time so rejected rows can be reported precisely.</InfoBanner>}
        {importErrors.length > 0 && <div className="rounded-[10px] border border-[var(--destructive)]/40 bg-[var(--destructive)]/5 p-4" role="alert"><p className="text-sm font-bold text-[var(--destructive)]">CSV row errors</p><ul className="mt-2 space-y-1 text-sm">{importErrors.map((item) => <li key={`${item.row}-${item.message}`}><span className="font-semibold">Row {item.row}:</span> {item.message}</li>)}</ul></div>}
        <FilterBar definitions={screen.filters} value={filters} onChange={(key, next) => setFilters((current) => ({ ...current, [key]: next }))} onApply={() => undefined} onReset={() => setFilters({})} />
        <DataTable<PolicyRecord> key={screen.key} metadata={{ columns: screen.columns, defaultOrdering: active === "commitment" ? "display_order" : "-effective_from", pageSize: 20, totalLabel: "policy setups" }} fetcher={fetcher} filters={filters} refreshKey={refreshKey} actions={hasPermission("ol_parameters.view") && (canManage || canDeactivate) ? actions : []} permissions={permissionKeys} onImportCsv={isVersionRateScreen(active) ? importCsv : undefined} exportFileName={`${screen.key}-policy-setup.csv`} caption={screen.title} />
      </>}
    </div>
    <FormModal open={editor.open} title={`${editor.row ? "Edit" : "Create"} ${screen.title}`} description="Save changes through the OL Parameters API. Effective dates and business validation remain server-authoritative." onClose={closeEditor} onSave={saveEditor} saving={saving} saveLabel={editor.row ? "Save changes" : "Create setup"}><PolicyEditor screen={active} value={editor.value} onChange={updateEditor} rateRows={rateRows} setRateRows={setRateRows} allowedTransitions={allowedTransitions} setAllowedTransitions={setAllowedTransitions} transitionOptions={transitionOptions} error={editorError} /></FormModal>
    <ConfirmModal open={Boolean(deactivateRow)} title="Deactivate policy setup" description={`Deactivate ${deactivateRow?.code ?? "this setup"}? It will remain available for audit history but will no longer be active.`} confirmLabel="Deactivate" onClose={() => setDeactivateRow(null)} onConfirm={deactivate} />
  </MasterDetailPage>
}

export { screens as olPolicySetupScreens }
