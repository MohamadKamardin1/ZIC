import { useCallback, useEffect, useMemo, useState, type ChangeEvent, type ReactNode } from "react"
import { Plus, RefreshCw, Save, Upload, X } from "lucide-react"
import { request, type TableQuery } from "../../lib/apiClient"
import { useAccess } from "../../lib/access"
import { DataTable, fetchTable, normalizeTableResponse } from "../../components/ui/DataTable"
import { FilterBar, type FilterValues } from "../../components/ui/FilterBar"
import { ConfirmModal, FormModal, InfoBanner } from "../../components/ui/Overlays"
import { DateInput, DecimalInput, EditableGrid, SelectInput, TextInput, TextareaInput, Toggle } from "../../components/ui"
import type { EditableGridColumn } from "../../components/ui/EditableGrid"
import type { FilterDefinition, RowAction, TableColumn, TableMetadata } from "../../components/ui/types"
import { MasterDetailPage } from "../../components/ui/Patterns"
import { StatusBadge, type StatusTone } from "../../components/ui/StatusBadge"
import { useToast } from "../../components/ui/Toast"

const API_PREFIX = "/api/v1/ol-parameters"

type RatingTab = "premium" | "mortality" | "joint" | "reinstatement" | "bonus" | "mortgage" | "installment" | "cash-surrender" | "reserve"

type RatingRecord = Record<string, unknown> & {
  id?: string
  code?: string
  name?: string
  description?: string | null
  is_active?: boolean
  effective_from?: string | null
  effective_to?: string | null
  table_code?: string
  version?: string
  rating_basis?: string
  currency?: string
  product?: string | null
  plan?: string | null
  gender?: string
  smoker_status?: string
  age_from?: number | string
  age_to?: number | string
  term_from?: number | string
  term_to?: number | string
  frequency?: string
  sum_assured_band_from?: number | string | null
  sum_assured_band_to?: number | string | null
  rate?: number | string | null
  rate_unit?: string
  age?: number | string
  policy_year?: number | string
  mortality_rate?: number | string
  joint_life_type?: string
  age_basis?: string
  survivor_benefit_rule?: string
  premium_adjustment_factor?: number | string
  underwriting_rule?: string
  calculation_basis?: string
  bonus_type?: string
  valuation_year?: number | string | null
  declaration_frequency?: string
  factor?: number | string
  charge_type?: string
  rate_value?: number | string
  apply_on?: string
  policy_year_from?: number | string
  policy_year_to?: number | string
  surrender_value_factor?: number | string | null
  loading_type?: string
  loading_basis?: string
}

type PremiumRow = {
  id?: string
  code: string
  name: string
  gender: string
  smoker_status: string
  age_from: string
  age_to: string
  term_from: string
  term_to: string
  frequency: string
  sum_assured_band_from: string
  sum_assured_band_to: string
  rate: string
  rate_unit: string
}

type MortalityRow = {
  id?: string
  code: string
  name: string
  age: string
  gender: string
  smoker_status: string
  policy_year: string
  mortality_rate: string
}

type EditorValue = string | number | boolean | null | undefined
type EditorState = Record<string, EditorValue>
type CsvError = { row: number; message: string }

type ScreenConfig = {
  title: string
  description: string
  endpoint: string
  columns: TableColumn<RatingRecord>[]
  filters: FilterDefinition[]
}

const tabs: Array<{ id: RatingTab; label: string }> = [
  { id: "premium", label: "OL Premium Rates" },
  { id: "mortality", label: "OL Mortality Rate" },
  { id: "joint", label: "OL Joint Life Setup" },
  { id: "reinstatement", label: "Reinstatement Interest Rate" },
  { id: "bonus", label: "OL Bonus Rate" },
  { id: "mortgage", label: "OL Mortgage Interest Factor" },
  { id: "installment", label: "Installment Charge Rate" },
  { id: "cash-surrender", label: "OL Cash Surrender Value" },
  { id: "reserve", label: "OL Reserve Loadings" },
]

const statusTone = (value: unknown): StatusTone => {
  const normalized = String(value ?? "").toLowerCase()
  if (["active", "current", "true"].includes(normalized)) return "success"
  if (["expired", "superseded", "false"].includes(normalized)) return "neutral"
  return "warning"
}

const effectiveState = (row: RatingRecord): string => {
  if (!row.is_active) return "Inactive"
  if (row.effective_to && row.effective_to < new Date().toISOString().slice(0, 10)) return "Expired"
  if (row.effective_from && row.effective_from > new Date().toISOString().slice(0, 10)) return "Scheduled"
  return "Active"
}

const formatRate = (value: unknown) => {
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric.toFixed(8).replace(/0+$/, "").replace(/\.$/, "") : "—"
}

const premiumMetadata: TableMetadata<RatingRecord> = {
  totalLabel: "Premium rate tables",
  defaultOrdering: "table_code",
  columns: [
    { key: "table_code", label: "Table", field: "table_code", sortable: true },
    { key: "name", label: "Name", field: "name", sortable: true },
    { key: "version", label: "Version", field: "version", sortable: true, render: (value) => <span className="font-bold">v{String(value ?? "—")}</span> },
    { key: "rating_basis", label: "Basis", field: "rating_basis" },
    { key: "currency", label: "Currency", field: "currency" },
    { key: "effective_from", label: "Effective from", field: "effective_from", sortable: true },
    { key: "effective_to", label: "Effective to", field: "effective_to" },
    { key: "status", label: "Status", render: (_value, row) => <StatusBadge value={effectiveState(row)} tone={statusTone(effectiveState(row))} /> },
  ],
}

const mortalityMetadata: TableMetadata<RatingRecord> = {
  totalLabel: "Mortality rate tables",
  defaultOrdering: "table_code",
  columns: [
    { key: "table_code", label: "Table", field: "table_code", sortable: true },
    { key: "name", label: "Name", field: "name", sortable: true },
    { key: "version", label: "Version", field: "version", sortable: true, render: (value) => <span className="font-bold">v{String(value ?? "—")}</span> },
    { key: "effective_from", label: "Effective from", field: "effective_from", sortable: true },
    { key: "effective_to", label: "Effective to", field: "effective_to" },
    { key: "status", label: "Status", render: (_value, row) => <StatusBadge value={effectiveState(row)} tone={statusTone(effectiveState(row))} /> },
  ],
}

const jointMetadata: TableMetadata<RatingRecord> = {
  totalLabel: "Joint-life setups",
  defaultOrdering: "joint_life_type",
  columns: [
    { key: "code", label: "Code", field: "code", sortable: true },
    { key: "name", label: "Name", field: "name", sortable: true },
    { key: "joint_life_type", label: "Type", field: "joint_life_type", sortable: true },
    { key: "age_basis", label: "Age basis", field: "age_basis" },
    { key: "survivor_benefit_rule", label: "Survivor rule", field: "survivor_benefit_rule" },
    { key: "premium_adjustment_factor", label: "Adjustment", field: "premium_adjustment_factor", align: "right", render: (value) => formatRate(value) },
    { key: "status", label: "Status", render: (_value, row) => <StatusBadge value={effectiveState(row)} tone={statusTone(effectiveState(row))} /> },
  ],
}

const configs: Record<RatingTab, ScreenConfig> = {
  premium: {
    title: "OL Premium Rates",
    description: "Versioned premium rating tables with multi-dimensional rate rows.",
    endpoint: `${API_PREFIX}/premium-rate-tables/`,
    columns: premiumMetadata.columns,
    filters: [
      { key: "product", label: "Product", type: "text", placeholder: "Product ID" },
      { key: "plan", label: "Plan", type: "text", placeholder: "Plan ID" },
      { key: "version", label: "Version", type: "text" },
      { key: "effective_from", label: "Effective date", type: "date-range" },
      { key: "is_active", label: "Status", type: "select", options: [{ label: "Active", value: "true" }, { label: "Inactive", value: "false" }] },
    ],
  },
  mortality: {
    title: "OL Mortality Rate",
    description: "Mortality bases by age, gender, smoker status, and policy year.",
    endpoint: `${API_PREFIX}/mortality-rate-tables/`,
    columns: mortalityMetadata.columns,
    filters: [
      { key: "version", label: "Version", type: "text" },
      { key: "effective_from", label: "Effective date", type: "date-range" },
      { key: "is_active", label: "Status", type: "select", options: [{ label: "Active", value: "true" }, { label: "Inactive", value: "false" }] },
    ],
  },
  joint: {
    title: "OL Joint Life Setup",
    description: "Effective-dated joint-life survivor and premium adjustment configuration.",
    endpoint: `${API_PREFIX}/joint-life-setups/`,
    columns: jointMetadata.columns,
    filters: [
      { key: "joint_life_type", label: "Joint-life type", type: "select", options: [{ label: "First death", value: "FIRST_DEATH" }, { label: "Last survivor", value: "LAST_SURVIVOR" }, { label: "Joint and survivor", value: "JOINT_AND_SURVIVOR" }] },
      { key: "age_basis", label: "Age basis", type: "select", options: [{ label: "Younger life", value: "YOUNGER_LIFE" }, { label: "Older life", value: "OLDER_LIFE" }, { label: "Average age", value: "AVERAGE_AGE" }, { label: "Joint age", value: "JOINT_AGE" }] },
      { key: "is_active", label: "Status", type: "select", options: [{ label: "Active", value: "true" }, { label: "Inactive", value: "false" }] },
    ],
  },
  reinstatement: {
    title: "Reinstatement Interest Rate",
    description: "Effective-dated interest assumptions applied during policy reinstatement.",
    endpoint: `${API_PREFIX}/reinstatement-interest-rates/`,
    columns: [
      { key: "code", label: "Code", field: "code", sortable: true },
      { key: "product", label: "Product", field: "product", sortable: true },
      { key: "plan", label: "Plan", field: "plan", sortable: true },
      { key: "calculation_basis", label: "Basis", field: "calculation_basis" },
      { key: "rate", label: "Rate", field: "rate", align: "right", render: (value) => formatRate(value) },
      { key: "effective_from", label: "Effective from", field: "effective_from", sortable: true },
      { key: "effective_to", label: "Effective to", field: "effective_to" },
      { key: "status", label: "Status", render: (_value, row) => <StatusBadge value={effectiveState(row)} tone={statusTone(effectiveState(row))} /> },
    ],
    filters: [
      { key: "product", label: "Product", type: "text", placeholder: "Product ID" },
      { key: "plan", label: "Plan", type: "text", placeholder: "Plan ID" },
      { key: "calculation_basis", label: "Basis", type: "text" },
      { key: "effective_from", label: "Effective date", type: "date-range" },
    ],
  },
  bonus: {
    title: "OL Bonus Rate",
    description: "Effective-dated bonus declarations by product, plan, type, and valuation year.",
    endpoint: `${API_PREFIX}/bonus-rates/`,
    columns: [
      { key: "code", label: "Code", field: "code", sortable: true },
      { key: "product", label: "Product", field: "product", sortable: true },
      { key: "plan", label: "Plan", field: "plan", sortable: true },
      { key: "bonus_type", label: "Bonus type", field: "bonus_type" },
      { key: "valuation_year", label: "Valuation year", field: "valuation_year", sortable: true },
      { key: "rate", label: "Rate", field: "rate", align: "right", render: (value) => formatRate(value) },
      { key: "effective_from", label: "Effective from", field: "effective_from", sortable: true },
      { key: "effective_to", label: "Effective to", field: "effective_to" },
      { key: "status", label: "Status", render: (_value, row) => <StatusBadge value={effectiveState(row)} tone={statusTone(effectiveState(row))} /> },
    ],
    filters: [
      { key: "product", label: "Product", type: "text", placeholder: "Product ID" },
      { key: "plan", label: "Plan", type: "text", placeholder: "Plan ID" },
      { key: "bonus_type", label: "Bonus type", type: "text" },
      { key: "effective_from", label: "Effective date", type: "date-range" },
    ],
  },
  mortgage: {
    title: "OL Mortgage Interest Factor",
    description: "Product and plan interest factors for loan-linked calculations.",
    endpoint: `${API_PREFIX}/mortgage-interest-factors/`,
    columns: [
      { key: "code", label: "Code", field: "code", sortable: true },
      { key: "product", label: "Product", field: "product", sortable: true },
      { key: "plan", label: "Plan", field: "plan", sortable: true },
      { key: "calculation_basis", label: "Basis", field: "calculation_basis" },
      { key: "factor", label: "Factor", field: "factor", align: "right", render: (value) => formatRate(value) },
      { key: "effective_from", label: "Effective from", field: "effective_from", sortable: true },
      { key: "effective_to", label: "Effective to", field: "effective_to" },
      { key: "status", label: "Status", render: (_value, row) => <StatusBadge value={effectiveState(row)} tone={statusTone(effectiveState(row))} /> },
    ],
    filters: [
      { key: "product", label: "Product", type: "text", placeholder: "Product ID" },
      { key: "plan", label: "Plan", type: "text", placeholder: "Plan ID" },
      { key: "calculation_basis", label: "Basis", type: "text" },
      { key: "effective_from", label: "Effective date", type: "date-range" },
    ],
  },
  installment: {
    title: "Installment Charge Rate",
    description: "Effective-dated installment charge values by frequency, type, and application basis.",
    endpoint: `${API_PREFIX}/installment-charge-rates/`,
    columns: [
      { key: "code", label: "Code", field: "code", sortable: true },
      { key: "product", label: "Product", field: "product", sortable: true },
      { key: "plan", label: "Plan", field: "plan", sortable: true },
      { key: "frequency", label: "Frequency", field: "frequency" },
      { key: "charge_type", label: "Charge type", field: "charge_type" },
      { key: "apply_on", label: "Apply on", field: "apply_on" },
      { key: "rate_value", label: "Value", field: "rate_value", align: "right", render: (value) => formatRate(value) },
      { key: "effective_from", label: "Effective from", field: "effective_from", sortable: true },
      { key: "effective_to", label: "Effective to", field: "effective_to" },
      { key: "status", label: "Status", render: (_value, row) => <StatusBadge value={effectiveState(row)} tone={statusTone(effectiveState(row))} /> },
    ],
    filters: [
      { key: "product", label: "Product", type: "text", placeholder: "Product ID" },
      { key: "plan", label: "Plan", type: "text", placeholder: "Plan ID" },
      { key: "frequency", label: "Frequency", type: "text" },
      { key: "effective_from", label: "Effective date", type: "date-range" },
    ],
  },
  "cash-surrender": {
    title: "OL Cash Surrender Value",
    description: "Policy-year, age, term, and demographic surrender value factors or rates.",
    endpoint: `${API_PREFIX}/cash-surrender-values/`,
    columns: [
      { key: "code", label: "Code", field: "code", sortable: true },
      { key: "product", label: "Product", field: "product", sortable: true },
      { key: "plan", label: "Plan", field: "plan", sortable: true },
      { key: "policy_year_from", label: "Policy year", field: "policy_year_from", render: (_value, row) => `${row.policy_year_from ?? "—"}–${row.policy_year_to ?? "—"}` },
      { key: "age_from", label: "Age band", field: "age_from", render: (_value, row) => `${row.age_from ?? "—"}–${row.age_to ?? "—"}` },
      { key: "term_from", label: "Term band", field: "term_from", render: (_value, row) => `${row.term_from ?? "—"}–${row.term_to ?? "—"}` },
      { key: "gender", label: "Gender", field: "gender" },
      { key: "smoker_status", label: "Smoker", field: "smoker_status" },
      { key: "surrender_value_factor", label: "Factor / rate", field: "surrender_value_factor", render: (_value, row) => formatRate(row.surrender_value_factor ?? row.rate) },
      { key: "effective_from", label: "Effective from", field: "effective_from", sortable: true },
      { key: "effective_to", label: "Effective to", field: "effective_to" },
      { key: "status", label: "Status", render: (_value, row) => <StatusBadge value={effectiveState(row)} tone={statusTone(effectiveState(row))} /> },
    ],
    filters: [
      { key: "product", label: "Product", type: "text", placeholder: "Product ID" },
      { key: "plan", label: "Plan", type: "text", placeholder: "Plan ID" },
      { key: "gender", label: "Gender", type: "text" },
      { key: "smoker_status", label: "Smoker", type: "text" },
      { key: "effective_from", label: "Effective date", type: "date-range" },
    ],
  },
  reserve: {
    title: "OL Reserve Loadings",
    description: "Effective-dated reserve, risk, expense, contingency, and capital loading assumptions.",
    endpoint: `${API_PREFIX}/reserve-loadings/`,
    columns: [
      { key: "code", label: "Code", field: "code", sortable: true },
      { key: "product", label: "Product", field: "product", sortable: true },
      { key: "plan", label: "Plan", field: "plan", sortable: true },
      { key: "loading_type", label: "Loading type", field: "loading_type" },
      { key: "loading_basis", label: "Basis", field: "loading_basis" },
      { key: "rate_value", label: "Rate", field: "rate_value", align: "right", render: (value) => formatRate(value) },
      { key: "effective_from", label: "Effective from", field: "effective_from", sortable: true },
      { key: "effective_to", label: "Effective to", field: "effective_to" },
      { key: "status", label: "Status", render: (_value, row) => <StatusBadge value={effectiveState(row)} tone={statusTone(effectiveState(row))} /> },
    ],
    filters: [
      { key: "product", label: "Product", type: "text", placeholder: "Product ID" },
      { key: "plan", label: "Plan", type: "text", placeholder: "Plan ID" },
      { key: "loading_type", label: "Loading type", type: "text" },
      { key: "effective_from", label: "Effective date", type: "date-range" },
    ],
  },
}

const defaultPremiumRow = (): PremiumRow => ({ code: `PREM-ROW-${Date.now()}`, name: "", gender: "MALE", smoker_status: "NON_SMOKER", age_from: "18", age_to: "65", term_from: "1", term_to: "30", frequency: "ANNUAL", sum_assured_band_from: "", sum_assured_band_to: "", rate: "0", rate_unit: "PER_THOUSAND_SUM_ASSURED" })
const defaultMortalityRow = (): MortalityRow => ({ code: `MORT-ROW-${Date.now()}`, name: "", age: "18", gender: "MALE", smoker_status: "NON_SMOKER", policy_year: "1", mortality_rate: "0" })
const tableId = (row: RatingRecord) => String(row.id ?? "")

function parseCsv(text: string): Array<Record<string, string>> {
  const lines = text.split(/\r?\n/).map((line) => line.trim()).filter(Boolean)
  if (lines.length < 2) return []
  const headers = lines[0].split(",").map((header) => header.trim().replace(/^"|"$/g, ""))
  return lines.slice(1).map((line) => {
    const values = line.split(",").map((value) => value.trim().replace(/^"|"$/g, ""))
    return Object.fromEntries(headers.map((header, index) => [header, values[index] ?? ""]))
  })
}

function errorsFromResponse(error: unknown): string {
  if (error && typeof error === "object" && "fieldErrors" in error) {
    const fields = Object.entries((error as { fieldErrors: Record<string, string[]> }).fieldErrors)
    if (fields.length) return fields.map(([field, messages]) => `${field}: ${messages.join(", ")}`).join("; ")
  }
  return error instanceof Error ? error.message : "The request could not be completed."
}

function PremiumGrid({ rows, onChange }: { rows: PremiumRow[]; onChange: (rows: PremiumRow[]) => void }) {
  const columns: Array<EditableGridColumn<PremiumRow>> = [
    { key: "gender", label: "Gender", render: (row, _index, update) => <SelectInput label="Gender" name="gender" value={row.gender} onChange={(event: ChangeEvent<HTMLSelectElement>) => update({ gender: event.target.value })}><option value="MALE">Male</option><option value="FEMALE">Female</option><option value="UNISEX">Unisex</option></SelectInput> },
    { key: "smoker_status", label: "Smoker", render: (row, _index, update) => <SelectInput label="Smoker" name="smoker_status" value={row.smoker_status} onChange={(event: ChangeEvent<HTMLSelectElement>) => update({ smoker_status: event.target.value })}><option value="NON_SMOKER">Non-smoker</option><option value="SMOKER">Smoker</option></SelectInput> },
    { key: "age_from", label: "Age from", render: (row, _index, update) => <DecimalInput label="Age from" name="age_from" value={row.age_from} onChange={(event: ChangeEvent<HTMLInputElement>) => update({ age_from: event.target.value })} /> },
    { key: "age_to", label: "Age to", render: (row, _index, update) => <DecimalInput label="Age to" name="age_to" value={row.age_to} onChange={(event: ChangeEvent<HTMLInputElement>) => update({ age_to: event.target.value })} /> },
    { key: "term_from", label: "Term from", render: (row, _index, update) => <DecimalInput label="Term from" name="term_from" value={row.term_from} onChange={(event: ChangeEvent<HTMLInputElement>) => update({ term_from: event.target.value })} /> },
    { key: "term_to", label: "Term to", render: (row, _index, update) => <DecimalInput label="Term to" name="term_to" value={row.term_to} onChange={(event: ChangeEvent<HTMLInputElement>) => update({ term_to: event.target.value })} /> },
    { key: "frequency", label: "Frequency", render: (row, _index, update) => <TextInput label="Frequency" name="frequency" value={row.frequency} onChange={(event: ChangeEvent<HTMLInputElement>) => update({ frequency: event.target.value.toUpperCase() })} /> },
    { key: "rate", label: "Rate", render: (row, _index, update) => <DecimalInput label="Rate" name="rate" value={row.rate} onChange={(event: ChangeEvent<HTMLInputElement>) => update({ rate: event.target.value })} /> },
  ]
  return <EditableGrid rows={rows} columns={columns} getRowId={(row, index) => row.id ?? `${row.code}-${index}`} createRow={defaultPremiumRow} onChange={onChange} validateRow={(row) => { const errors: Record<string, string> = {}; if (!row.code.trim()) errors.code = "Code is required."; if (Number(row.age_to) < Number(row.age_from)) errors.age_to = "Age-to must be at least age-from."; if (Number(row.term_to) < Number(row.term_from)) errors.term_to = "Term-to must be at least term-from."; if (Number(row.rate) < 0) errors.rate = "Rate cannot be negative."; return errors }} />
}

function MortalityGrid({ rows, onChange }: { rows: MortalityRow[]; onChange: (rows: MortalityRow[]) => void }) {
  const columns: Array<EditableGridColumn<MortalityRow>> = [
    { key: "age", label: "Age", render: (row, _index, update) => <DecimalInput label="Age" name="age" value={row.age} onChange={(event: ChangeEvent<HTMLInputElement>) => update({ age: event.target.value })} /> },
    { key: "gender", label: "Gender", render: (row, _index, update) => <SelectInput label="Gender" name="gender" value={row.gender} onChange={(event: ChangeEvent<HTMLSelectElement>) => update({ gender: event.target.value })}><option value="MALE">Male</option><option value="FEMALE">Female</option><option value="UNISEX">Unisex</option></SelectInput> },
    { key: "smoker_status", label: "Smoker", render: (row, _index, update) => <SelectInput label="Smoker" name="smoker_status" value={row.smoker_status} onChange={(event: ChangeEvent<HTMLSelectElement>) => update({ smoker_status: event.target.value })}><option value="NON_SMOKER">Non-smoker</option><option value="SMOKER">Smoker</option></SelectInput> },
    { key: "policy_year", label: "Policy year", render: (row, _index, update) => <DecimalInput label="Policy year" name="policy_year" value={row.policy_year} onChange={(event: ChangeEvent<HTMLInputElement>) => update({ policy_year: event.target.value })} /> },
    { key: "mortality_rate", label: "Mortality rate", render: (row, _index, update) => <DecimalInput label="Mortality rate" name="mortality_rate" value={row.mortality_rate} onChange={(event: ChangeEvent<HTMLInputElement>) => update({ mortality_rate: event.target.value })} /> },
  ]
  return <EditableGrid rows={rows} columns={columns} getRowId={(row, index) => row.id ?? `${row.code}-${index}`} createRow={defaultMortalityRow} onChange={onChange} validateRow={(row) => { const errors: Record<string, string> = {}; if (Number(row.age) < 0 || Number(row.age) > 150) errors.age = "Age must be between 0 and 150."; if (Number(row.policy_year) < 1) errors.policy_year = "Policy year must be positive."; if (Number(row.mortality_rate) < 0) errors.mortality_rate = "Mortality rate cannot be negative."; return errors }} />
}

function Part2Editor({ tab, record, onChange }: { tab: Exclude<RatingTab, "premium" | "mortality" | "joint">; record: RatingRecord; onChange: (key: string, value: EditorValue) => void }) {
  const field = (key: string) => String(record[key] ?? "")
  const valueMode = record.rate != null && String(record.rate).trim() !== "" ? "rate" : "factor"
  const set = (key: string) => (event: ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => onChange(key, event.target.value || null)
  return <div className="space-y-5">
    <section className="surface-card space-y-4 p-4"><h3 className="text-sm font-extrabold uppercase tracking-[0.12em]">Scope and effective dates</h3><div className="grid gap-4 md:grid-cols-2"><TextInput label="Code" name="code" required value={field("code")} onChange={set("code") as (event: ChangeEvent<HTMLInputElement>) => void} /><TextInput label="Product ID" name="product" value={field("product")} onChange={set("product") as (event: ChangeEvent<HTMLInputElement>) => void} /><TextInput label="Plan ID" name="plan" value={field("plan")} onChange={set("plan") as (event: ChangeEvent<HTMLInputElement>) => void} /><DateInput label="Effective from" name="effective_from" required value={field("effective_from")} onChange={set("effective_from") as (event: ChangeEvent<HTMLInputElement>) => void} /><DateInput label="Effective to" name="effective_to" value={field("effective_to")} onChange={set("effective_to") as (event: ChangeEvent<HTMLInputElement>) => void} /><Toggle label="Active" checked={Boolean(record.is_active ?? true)} onChange={(checked) => onChange("is_active", checked)} /></div></section>
    {tab === "reinstatement" && <section className="surface-card space-y-4 p-4"><h3 className="text-sm font-extrabold uppercase tracking-[0.12em]">Reinstatement interest</h3><div className="grid gap-4 md:grid-cols-2"><SelectInput label="Calculation basis" name="calculation_basis" required value={field("calculation_basis")} onChange={set("calculation_basis") as (event: ChangeEvent<HTMLSelectElement>) => void}><option value="OUTSTANDING_PREMIUM">Outstanding premium</option><option value="POLICY_VALUE">Policy value</option><option value="LOAN_BALANCE">Loan balance</option></SelectInput><DecimalInput label="Rate (%)" name="rate" required value={field("rate")} onChange={set("rate") as (event: ChangeEvent<HTMLInputElement>) => void} /></div></section>}
    {tab === "bonus" && <section className="surface-card space-y-4 p-4"><h3 className="text-sm font-extrabold uppercase tracking-[0.12em]">Bonus declaration</h3><div className="grid gap-4 md:grid-cols-2"><SelectInput label="Bonus type" name="bonus_type" required value={field("bonus_type")} onChange={set("bonus_type") as (event: ChangeEvent<HTMLSelectElement>) => void}><option value="REVERSIONARY">Reversionary</option><option value="TERMINAL">Terminal</option><option value="LOYALTY">Loyalty</option><option value="SPECIAL">Special</option><option value="GUARANTEED">Guaranteed</option></SelectInput><DecimalInput label="Rate" name="rate" required value={field("rate")} onChange={set("rate") as (event: ChangeEvent<HTMLInputElement>) => void} /><DecimalInput label="Valuation year" name="valuation_year" value={field("valuation_year")} onChange={set("valuation_year") as (event: ChangeEvent<HTMLInputElement>) => void} /><SelectInput label="Declaration frequency" name="declaration_frequency" value={field("declaration_frequency")} onChange={set("declaration_frequency") as (event: ChangeEvent<HTMLSelectElement>) => void}><option value="ANNUAL">Annual</option><option value="QUARTERLY">Quarterly</option><option value="MONTHLY">Monthly</option><option value="ON_MATURITY">On maturity</option><option value="AD_HOC">Ad hoc</option></SelectInput></div></section>}
    {tab === "mortgage" && <section className="surface-card space-y-4 p-4"><h3 className="text-sm font-extrabold uppercase tracking-[0.12em]">Mortgage interest factor</h3><div className="grid gap-4 md:grid-cols-2"><SelectInput label="Calculation basis" name="calculation_basis" required value={field("calculation_basis")} onChange={set("calculation_basis") as (event: ChangeEvent<HTMLSelectElement>) => void}><option value="CASH_VALUE">Cash value</option><option value="PREMIUM">Premium</option><option value="LOAN_BALANCE">Loan balance</option></SelectInput><DecimalInput label="Factor" name="factor" required value={field("factor")} onChange={set("factor") as (event: ChangeEvent<HTMLInputElement>) => void} /></div></section>}
    {tab === "installment" && <section className="surface-card space-y-4 p-4"><h3 className="text-sm font-extrabold uppercase tracking-[0.12em]">Installment charge</h3><div className="grid gap-4 md:grid-cols-2"><SelectInput label="Frequency" name="frequency" required value={field("frequency")} onChange={set("frequency") as (event: ChangeEvent<HTMLSelectElement>) => void}><option value="SINGLE">Single</option><option value="MONTHLY">Monthly</option><option value="QUARTERLY">Quarterly</option><option value="HALF_YEARLY">Half yearly</option><option value="ANNUAL">Annual</option></SelectInput><SelectInput label="Charge type" name="charge_type" required value={field("charge_type")} onChange={set("charge_type") as (event: ChangeEvent<HTMLSelectElement>) => void}><option value="FIXED">Fixed amount</option><option value="PERCENTAGE">Percentage</option><option value="FACTOR">Factor</option></SelectInput><SelectInput label="Apply on" name="apply_on" required value={field("apply_on")} onChange={set("apply_on") as (event: ChangeEvent<HTMLSelectElement>) => void}><option value="PREMIUM">Premium</option><option value="INSTALLMENT">Installment</option><option value="SUM_ASSURED">Sum assured</option><option value="POLICY_VALUE">Policy value</option><option value="DUE_AMOUNT">Due amount</option></SelectInput><DecimalInput label="Charge value" name="rate_value" required value={field("rate_value")} onChange={set("rate_value") as (event: ChangeEvent<HTMLInputElement>) => void} /></div></section>}
    {tab === "cash-surrender" && <section className="surface-card space-y-4 p-4"><h3 className="text-sm font-extrabold uppercase tracking-[0.12em]">Surrender-value dimensions</h3><div className="grid gap-4 md:grid-cols-3">{([["policy_year_from","Policy year from"],["policy_year_to","Policy year to"],["age_from","Age from"],["age_to","Age to"],["term_from","Term from"],["term_to","Term to"]] as const).map(([key, label]) => <DecimalInput key={key} label={label} name={key} required value={field(key)} onChange={set(key) as (event: ChangeEvent<HTMLInputElement>) => void} />)}<SelectInput label="Gender" name="gender" value={field("gender")} onChange={set("gender") as (event: ChangeEvent<HTMLSelectElement>) => void}><option value="M">Male</option><option value="F">Female</option></SelectInput><SelectInput label="Smoker status" name="smoker_status" value={field("smoker_status")} onChange={set("smoker_status") as (event: ChangeEvent<HTMLSelectElement>) => void}><option value="NS">Non-smoker</option><option value="S">Smoker</option></SelectInput><SelectInput label="Value type" name="cash_value_type" value={valueMode} onChange={(event: ChangeEvent<HTMLSelectElement>) => { if (event.target.value === "rate") { onChange("rate", record.rate ?? "0"); onChange("surrender_value_factor", null) } else { onChange("surrender_value_factor", record.surrender_value_factor ?? "0"); onChange("rate", null) } }}><option value="factor">Surrender factor (0–1)</option><option value="rate">Surrender rate (%)</option></SelectInput>{valueMode === "factor" ? <DecimalInput label="Surrender value factor (0–1)" name="surrender_value_factor" required value={field("surrender_value_factor")} onChange={set("surrender_value_factor") as (event: ChangeEvent<HTMLInputElement>) => void} /> : <DecimalInput label="Surrender value rate (%)" name="rate" required value={field("rate")} onChange={set("rate") as (event: ChangeEvent<HTMLInputElement>) => void} />}</div></section>}
    {tab === "reserve" && <section className="surface-card space-y-4 p-4"><h3 className="text-sm font-extrabold uppercase tracking-[0.12em]">Reserve loading</h3><div className="grid gap-4 md:grid-cols-2"><SelectInput label="Loading type" name="loading_type" required value={field("loading_type")} onChange={set("loading_type") as (event: ChangeEvent<HTMLSelectElement>) => void}><option value="EXPENSE">Expense</option><option value="RISK">Risk</option><option value="CONTINGENCY">Contingency</option><option value="PROFIT">Profit</option><option value="CAPITAL">Capital</option><option value="OTHER">Other</option></SelectInput><SelectInput label="Loading basis" name="loading_basis" required value={field("loading_basis")} onChange={set("loading_basis") as (event: ChangeEvent<HTMLSelectElement>) => void}><option value="RESERVE">Reserve</option><option value="PREMIUM">Premium</option><option value="SUM_ASSURED">Sum assured</option><option value="POLICY_VALUE">Policy value</option><option value="CUSTOM">Custom</option></SelectInput><DecimalInput label="Rate value (%)" name="rate_value" required value={field("rate_value")} onChange={set("rate_value") as (event: ChangeEvent<HTMLInputElement>) => void} /></div></section>}
    <TextareaInput label="Description" name="description" value={field("description")} onChange={set("description") as (event: ChangeEvent<HTMLTextAreaElement>) => void} />
  </div>
}

export default function OLProductRating() {
  const { access, canAccess, isSuperAdmin } = useAccess()
  const { toast } = useToast()
  const [activeTab, setActiveTab] = useState<RatingTab>("premium")
  const [filters, setFilters] = useState<FilterValues>({})
  const [refreshKey, setRefreshKey] = useState(0)
  const [editor, setEditor] = useState<{ mode: "create" | "edit"; tab: RatingTab; record: RatingRecord } | null>(null)
  const [confirm, setConfirm] = useState<RatingRecord | null>(null)
  const [saving, setSaving] = useState(false)
  const [rowTable, setRowTable] = useState<RatingRecord | null>(null)
  const [premiumRows, setPremiumRows] = useState<PremiumRow[]>([])
  const [mortalityRows, setMortalityRows] = useState<MortalityRow[]>([])
  const [importErrors, setImportErrors] = useState<CsvError[]>([])
  const [overlapWarning, setOverlapWarning] = useState<string | null>(null)

  const permissions = useMemo(() => isSuperAdmin ? ["ol_parameters.view", "ol_parameters.create", "ol_parameters.update", "ol_parameters.deactivate"] : access.permissions.filter((permission) => permission.module === "ol_parameters").map((permission) => `${permission.module}.${permission.action}`), [access.permissions, isSuperAdmin])
  const canCreate = isSuperAdmin || canAccess("ol_parameters")
  const canUpdate = isSuperAdmin || canAccess("ol_parameters")
  const canDeactivate = isSuperAdmin || canAccess("ol_parameters")
  const config = configs[activeTab]
  const metadata: TableMetadata<RatingRecord> = activeTab === "premium" ? premiumMetadata : activeTab === "mortality" ? mortalityMetadata : activeTab === "joint" ? jointMetadata : { totalLabel: config.title, defaultOrdering: "effective_from", columns: config.columns }

  const fetcher = useCallback((query: TableQuery) => fetchTable<RatingRecord>(config.endpoint, query), [config.endpoint])

  const loadRows = useCallback(async (table: RatingRecord, tab: "premium" | "mortality") => {
    const endpoint = tab === "premium" ? `${API_PREFIX}/premium-rate-rows/` : `${API_PREFIX}/mortality-rate-rows/`
    const response = normalizeTableResponse<RatingRecord>(await request<unknown>(`${endpoint}?table=${encodeURIComponent(tableId(table))}&page_size=500`))
    if (tab === "premium") setPremiumRows(response.results.map((row) => ({ id: row.id, code: String(row.code ?? ""), name: String(row.name ?? ""), gender: String(row.gender ?? "MALE"), smoker_status: String(row.smoker_status ?? "NON_SMOKER"), age_from: String(row.age_from ?? ""), age_to: String(row.age_to ?? ""), term_from: String(row.term_from ?? ""), term_to: String(row.term_to ?? ""), frequency: String(row.frequency ?? "ANNUAL"), sum_assured_band_from: String(row.sum_assured_band_from ?? ""), sum_assured_band_to: String(row.sum_assured_band_to ?? ""), rate: String(row.rate ?? "0"), rate_unit: String(row.rate_unit ?? "PER_THOUSAND_SUM_ASSURED") })))
    else setMortalityRows(response.results.map((row) => ({ id: row.id, code: String(row.code ?? ""), name: String(row.name ?? ""), age: String(row.age ?? ""), gender: String(row.gender ?? "MALE"), smoker_status: String(row.smoker_status ?? "NON_SMOKER"), policy_year: String(row.policy_year ?? "1"), mortality_rate: String(row.mortality_rate ?? "0") })))
    setRowTable(table)
    setImportErrors([])
  }, [])

  const openEditor = (tab: RatingTab, mode: "create" | "edit", record?: RatingRecord) => {
    const today = new Date().toISOString().slice(0, 10)
    const defaults: RatingRecord = tab === "joint" ? { code: "", name: "", joint_life_type: "FIRST_DEATH", age_basis: "YOUNGER_LIFE", survivor_benefit_rule: "", premium_adjustment_factor: "1", underwriting_rule: "", product: null, plan: null, effective_from: today, effective_to: null, is_active: true } : tab === "premium" ? { table_code: "", name: "", description: "", rating_basis: "SUM_ASSURED", currency: "TZS", version: "1.0", effective_from: today, effective_to: null, is_active: true } : tab === "mortality" ? { table_code: "", name: "", description: "", version: "1.0", effective_from: today, effective_to: null, is_active: true } : { code: "", name: "", product: null, plan: null, effective_from: today, effective_to: null, is_active: true, factor: "1", rate_value: "0", policy_year_from: "1", policy_year_to: "30", age_from: "18", age_to: "65", term_from: "5", term_to: "30", gender: "M", smoker_status: "NS", surrender_value_factor: "0.5", rate: null, calculation_basis: "POLICY_VALUE", bonus_type: "REVERSIONARY", valuation_year: "1", declaration_frequency: "ANNUAL", frequency: "ANNUAL", charge_type: "PERCENTAGE", apply_on: "PREMIUM", loading_type: "EXPENSE", loading_basis: "RESERVE" }
    setEditor({ tab, mode, record: { ...defaults, ...(record ?? {}) } })
    setOverlapWarning(null)
  }

  const saveTable = async () => {
    if (!editor) return
    const record = editor.record
    const errors: Record<string, string> = {}
    if (editor.tab === "joint") {
      if (!String(record.code ?? "").trim()) errors.code = "Code is required."
      if (!String(record.survivor_benefit_rule ?? "").trim()) errors.survivor_benefit_rule = "Survivor benefit rule is required."
      if (!String(record.underwriting_rule ?? "").trim()) errors.underwriting_rule = "Underwriting rule is required."
      if (Number(record.premium_adjustment_factor) <= 0) errors.premium_adjustment_factor = "Adjustment factor must be greater than zero."
      if (!record.product && !record.plan) errors.product = "Select a product or plan scope."
    } else if (editor.tab === "premium" || editor.tab === "mortality") {
      if (!String(record.table_code ?? "").trim()) errors.table_code = "Table code is required."
      if (!String(record.name ?? "").trim()) errors.name = "Name is required."
      if (!String(record.version ?? "").trim()) errors.version = "Version is required."
    } else {
      if (!String(record.code ?? "").trim()) errors.code = "Code is required."
      if (!record.product && !record.plan) errors.product = "Select a product or plan scope."
      if (editor.tab === "reinstatement" && (Number(record.rate) < 0 || Number(record.rate) > 100)) errors.rate = "Rate must be between 0 and 100."
      if (editor.tab === "bonus" && (!String(record.bonus_type ?? "").trim() || Number(record.valuation_year) < 1 || Number(record.rate) < 0)) errors.bonus_type = "Bonus type, positive valuation year, and non-negative rate are required."
      if (editor.tab === "mortgage" && Number(record.factor) <= 0) errors.factor = "Mortgage factor must be greater than zero."
      if (editor.tab === "installment" && (Number(record.rate_value) < 0 || Number(record.rate_value) > 100)) errors.rate_value = "Installment charge must be between 0 and 100."
      if (editor.tab === "cash-surrender") {
        if (Number(record.policy_year_to) < Number(record.policy_year_from) || Number(record.age_to) < Number(record.age_from) || Number(record.term_to) < Number(record.term_from)) errors.policy_year_to = "All dimension upper bounds must be at least their lower bounds."
        const hasFactor = record.surrender_value_factor != null && String(record.surrender_value_factor).trim() !== ""
        const hasRate = record.rate != null && String(record.rate).trim() !== ""
        if (hasFactor === hasRate) errors.surrender_value_factor = "Provide exactly one of surrender value factor or rate."
        if (hasFactor && (Number(record.surrender_value_factor) < 0 || Number(record.surrender_value_factor) > 1)) errors.surrender_value_factor = "Surrender value factor must be between 0 and 1."
        if (hasRate && (Number(record.rate) < 0 || Number(record.rate) > 100)) errors.rate = "Surrender value rate must be between 0 and 100."
      }
      if (editor.tab === "reserve" && (Number(record.rate_value) < 0 || Number(record.rate_value) > 100)) errors.rate_value = "Reserve loading must be between 0 and 100."
    }
    if (record.effective_from && record.effective_to && String(record.effective_to) < String(record.effective_from)) errors.effective_to = "Effective-to cannot precede effective-from."
    if (Object.keys(errors).length) {
      setOverlapWarning(Object.values(errors).join(" "))
      return
    }
    setSaving(true)
    try {
      const endpoint = configs[editor.tab].endpoint
      const body = { ...record }
      const saved = await request<RatingRecord>(editor.mode === "create" ? endpoint : `${endpoint}${tableId(record)}/`, { method: editor.mode === "create" ? "POST" : "PATCH", body: JSON.stringify(body) })
      setEditor(null)
      setRefreshKey((value) => value + 1)
      toast({ tone: "success", title: editor.mode === "create" ? "Rating setup created" : "Rating setup updated", message: String(saved.code ?? saved.table_code ?? "The record was saved.") })
    } catch (error) {
      const message = errorsFromResponse(error)
      setOverlapWarning(message)
      toast({ tone: "danger", title: "Unable to save rating setup", message })
    } finally {
      setSaving(false)
    }
  }

  const saveRows = async () => {
    if (!rowTable) return
    const tab = activeTab === "premium" ? "premium" : "mortality"
    const endpoint = tab === "premium" ? `${API_PREFIX}/premium-rate-rows/` : `${API_PREFIX}/mortality-rate-rows/`
    const rows = tab === "premium" ? premiumRows : mortalityRows
    if (tab === "premium") {
      const invalid = premiumRows.some((row) => !row.code || Number(row.age_to) < Number(row.age_from) || Number(row.term_to) < Number(row.term_from) || Number(row.rate) < 0)
      if (invalid) {
        setOverlapWarning("Correct the highlighted premium rate rows before saving.")
        return
      }
    } else {
      const invalid = mortalityRows.some((row) => !row.code || Number(row.age) < 0 || Number(row.age) > 150 || Number(row.policy_year) < 1 || Number(row.mortality_rate) < 0)
      if (invalid) {
        setOverlapWarning("Correct the highlighted mortality rows before saving.")
        return
      }
    }
    setSaving(true)
    setOverlapWarning(null)
    try {
      if (tab === "mortality" && mortalityRows.length) {
        await request(`${endpoint}bulk-import/`, { method: "POST", body: JSON.stringify({ rows: mortalityRows.map((row) => ({ ...row, table: tableId(rowTable!), age: Number(row.age), policy_year: Number(row.policy_year), mortality_rate: row.mortality_rate })) }) })
      } else {
        for (const row of premiumRows) {
          await request(row.id ? `${endpoint}${row.id}/` : endpoint, { method: row.id ? "PATCH" : "POST", body: JSON.stringify({ ...row, table: tableId(rowTable!) }) })
        }
      }
      toast({ tone: "success", title: "Rate rows saved", message: `${rows.length} rows persisted.` })
      setRowTable(null)
      setRefreshKey((value) => value + 1)
    } catch (error) {
      const message = errorsFromResponse(error)
      setOverlapWarning(message)
      toast({ tone: "danger", title: "Rate rows rejected", message })
    } finally {
      setSaving(false)
    }
  }

  const importCsv = async (file: File) => {
    if (!rowTable && activeTab !== "cash-surrender") {
      toast({ tone: "warning", title: "Select a rate table first", message: "Open a table row before importing CSV data." })
      return
    }
    const text = await file.text()
    const parsed = parseCsv(text)
    const errors: CsvError[] = []
    const validRows: Record<string, string>[] = []
    parsed.forEach((row, index) => {
      const line = index + 2
      if (!row.code) errors.push({ row: line, message: "code is required" })
      if (activeTab === "premium" && (Number(row.age_to) < Number(row.age_from) || Number(row.term_to) < Number(row.term_from))) errors.push({ row: line, message: "age and term bands must be ordered" })
      if (activeTab === "mortality" && (Number(row.age) < 0 || Number(row.age) > 150 || Number(row.mortality_rate) < 0)) errors.push({ row: line, message: "age or mortality rate is invalid" })
      if (activeTab === "cash-surrender") {
        const hasFactor = row.surrender_value_factor !== ""
        const hasRate = row.rate !== ""
        if (!row.product) errors.push({ row: line, message: "product is required" })
        if (Number(row.policy_year_from) < 1 || Number(row.policy_year_to) < Number(row.policy_year_from)) errors.push({ row: line, message: "policy-year band is invalid" })
        if (row.age_from !== "" && (Number(row.age_from) < 0 || Number(row.age_from) > 150)) errors.push({ row: line, message: "age-from is invalid" })
        if (row.age_to !== "" && (Number(row.age_to) < 0 || Number(row.age_to) > 150 || (row.age_from !== "" && Number(row.age_to) < Number(row.age_from)))) errors.push({ row: line, message: "age band is invalid" })
        if (row.term_from !== "" && Number(row.term_from) < 1) errors.push({ row: line, message: "term-from must be positive" })
        if (row.term_to !== "" && (Number(row.term_to) < 1 || (row.term_from !== "" && Number(row.term_to) < Number(row.term_from)))) errors.push({ row: line, message: "term band is invalid" })
        if (hasFactor === hasRate) errors.push({ row: line, message: "provide exactly one factor or rate" })
        if (hasFactor && (Number(row.surrender_value_factor) < 0 || Number(row.surrender_value_factor) > 1)) errors.push({ row: line, message: "surrender value factor must be between 0 and 1" })
        if (hasRate && (Number(row.rate) < 0 || Number(row.rate) > 100)) errors.push({ row: line, message: "surrender value rate must be between 0 and 100" })
      }
      if (!errors.some((error) => error.row === line)) validRows.push(row)
    })
    setImportErrors(errors)
    if (!validRows.length) return
    try {
      if (activeTab === "cash-surrender") {
        for (const row of validRows) await request(`${API_PREFIX}/cash-surrender-values/`, { method: "POST", body: JSON.stringify({ ...row, policy_year_from: Number(row.policy_year_from), policy_year_to: Number(row.policy_year_to), age_from: row.age_from === "" ? null : Number(row.age_from), age_to: row.age_to === "" ? null : Number(row.age_to), term_from: row.term_from === "" ? null : Number(row.term_from), term_to: row.term_to === "" ? null : Number(row.term_to), surrender_value_factor: row.surrender_value_factor === "" ? null : row.surrender_value_factor, rate: row.rate === "" ? null : row.rate }) })
      } else if (activeTab === "mortality") await request(`${API_PREFIX}/mortality-rate-rows/bulk-import/`, { method: "POST", body: JSON.stringify({ rows: validRows.map((row) => ({ ...row, table: tableId(rowTable!) })) }) })
      else for (const row of validRows) await request(`${API_PREFIX}/premium-rate-rows/`, { method: "POST", body: JSON.stringify({ ...row, table: tableId(rowTable!) }) })
      toast({ tone: errors.length ? "warning" : "success", title: "CSV import processed", message: `${validRows.length} rows imported; ${errors.length} rejected.` })
      if (activeTab === "cash-surrender") setRefreshKey((value) => value + 1)
      else if (rowTable) await loadRows(rowTable, activeTab as "premium" | "mortality")
    } catch (error) {
      setOverlapWarning(errorsFromResponse(error))
      toast({ tone: "danger", title: "CSV import failed", message: errorsFromResponse(error) })
    }
  }

  const createVersion = async (table: RatingRecord) => {
    const endpoint = activeTab === "premium" ? `${API_PREFIX}/premium-rate-tables/` : `${API_PREFIX}/mortality-rate-tables/`
    const currentVersion = Number(String(table.version ?? "0").replace(/[^0-9.]/g, ""))
    const version = Number.isFinite(currentVersion) ? (currentVersion + 1).toFixed(1) : "1.0"
    try {
      const copy = { ...table, id: undefined, version, table_code: `${String(table.table_code ?? "TABLE")}-${version.replace(".", "")}`, is_active: true }
      const created = await request<RatingRecord>(endpoint, { method: "POST", body: JSON.stringify(copy) })
      toast({ tone: "success", title: "New rating version created", message: `Version ${version} is ready for rows.` })
      if (table.id && created.id) {
        const oldEndpoint = activeTab === "premium" ? `${API_PREFIX}/premium-rate-rows/` : `${API_PREFIX}/mortality-rate-rows/`
        const rows = normalizeTableResponse<RatingRecord>(await request<unknown>(`${oldEndpoint}?table=${encodeURIComponent(tableId(table))}&page_size=500`)).results
        for (const row of rows) {
          const { id: _id, ...payload } = row
          await request(oldEndpoint, { method: "POST", body: JSON.stringify({ ...payload, table: created.id, code: `${String(payload.code ?? "ROW")}-${version.replace(".", "")}` }) })
        }
      }
      setRefreshKey((value) => value + 1)
    } catch (error) {
      toast({ tone: "danger", title: "Unable to create version", message: errorsFromResponse(error) })
    }
  }

  const deactivate = async () => {
    if (!confirm) return
    const endpoint = configs[activeTab].endpoint
    try {
      await request(`${endpoint}${tableId(confirm)}/deactivate/`, { method: "POST" })
      setConfirm(null)
      setRefreshKey((value) => value + 1)
      toast({ tone: "success", title: "Rating setup deactivated" })
    } catch (error) {
      toast({ tone: "danger", title: "Unable to deactivate", message: errorsFromResponse(error) })
    }
  }

  const actions: RowAction<RatingRecord>[] = [
    ...(activeTab === "premium" || activeTab === "mortality" ? [{ key: "rows", label: "Open rate rows", permission: "ol_parameters.view", onSelect: (row: RatingRecord) => void loadRows(row, activeTab) } satisfies RowAction<RatingRecord>] : []),
    { key: "edit", label: "Edit", permission: "ol_parameters.update", onSelect: (row) => openEditor(activeTab, "edit", row) },
    ...(activeTab === "premium" || activeTab === "mortality" ? [{ key: "version", label: "Create new version", permission: "ol_parameters.create", onSelect: (row: RatingRecord) => void createVersion(row) } satisfies RowAction<RatingRecord>] : []),
    { key: "deactivate", label: "Deactivate", permission: "ol_parameters.deactivate", tone: "danger", isVisible: (row) => Boolean(row.is_active), onSelect: (row) => setConfirm(row) },
  ]

  const stats = useMemo(() => [{ label: "Current workspace", value: config.title, helper: "Backend-driven Product Rating" }, { label: "Dimension model", value: activeTab === "joint" ? "Scoped setup" : activeTab === "premium" ? "8 dimensions" : activeTab === "mortality" ? "5 dimensions" : activeTab === "cash-surrender" ? "10 dimensions" : "Scoped setup", helper: "Validated before persistence" }], [activeTab, config.title])

  return <MasterDetailPage eyebrow="Ordinary Life / Product Rating" title="OL Product Rating" description="Configure effective-dated premium and mortality rating bases with auditable version and row workflows." stats={stats} tabs={tabs} activeTab={activeTab} onTabChange={(id) => { setActiveTab(id as RatingTab); setFilters({}); setRowTable(null); setImportErrors([]); setOverlapWarning(null) }} actions={<>{activeTab !== "joint" && canCreate && <button type="button" className="button-primary" onClick={() => openEditor(activeTab, "create")}><Plus size={16} aria-hidden="true" />New version</button>}{activeTab === "joint" && canCreate && <button type="button" className="button-primary" onClick={() => openEditor("joint", "create")}><Plus size={16} aria-hidden="true" />Add setup</button>}</>}>
    <div className="space-y-4">
      <FilterBar definitions={config.filters} value={filters} onChange={(key, value) => setFilters((current) => ({ ...current, [key]: value }))} onReset={() => setFilters({})} />
      {overlapWarning && <InfoBanner title="Validation or overlap warning"><div className="flex items-start justify-between gap-4"><span>{overlapWarning}</span><button type="button" aria-label="Dismiss warning" className="rounded-md p-1 hover:bg-blue-100" onClick={() => setOverlapWarning(null)}><X size={15} /></button></div></InfoBanner>}
      {importErrors.length > 0 && <InfoBanner title="CSV rows rejected"><ul className="mt-1 list-disc pl-5">{importErrors.map((error) => <li key={`${error.row}-${error.message}`}>Row {error.row}: {error.message}</li>)}</ul></InfoBanner>}
      {rowTable && (activeTab === "premium" || activeTab === "mortality") ? <section className="surface-card space-y-4 p-4"><div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-xs font-bold uppercase tracking-[0.12em] text-[var(--muted-foreground)]">Rate row editor</p><h2 className="mt-1 text-lg font-extrabold">{String(rowTable.table_code ?? rowTable.name ?? "Selected table")} · v{String(rowTable.version ?? "—")}</h2><p className="mt-1 text-sm text-[var(--muted-foreground)]">Dimension filters are applied through the table selection. Rate values use backend decimal precision.</p></div><div className="flex flex-wrap gap-2"><button type="button" className="button-secondary" onClick={() => setRowTable(null)}>Back to versions</button><label className="button-secondary cursor-pointer"><Upload size={15} aria-hidden="true" />Import CSV<input aria-label="Import rate rows CSV" type="file" accept=".csv,text/csv" className="sr-only" onChange={(event) => { const file = event.target.files?.[0]; if (file) void importCsv(file); event.target.value = "" }} /></label>{canUpdate && <button type="button" className="button-primary" onClick={() => void saveRows()} disabled={saving}><Save size={15} aria-hidden="true" />{saving ? "Saving…" : "Save rows"}</button>}</div></div>{activeTab === "premium" ? <PremiumGrid rows={premiumRows} onChange={setPremiumRows} /> : <MortalityGrid rows={mortalityRows} onChange={setMortalityRows} />}</section> : <DataTable metadata={metadata} fetcher={fetcher} filters={filters} refreshKey={refreshKey} actions={actions} permissions={permissions} onImportCsv={activeTab === "premium" || activeTab === "mortality" || activeTab === "cash-surrender" ? importCsv : undefined} exportFileName={`ol-${activeTab}-rating.csv`} caption={config.title} />}
    </div>
    <FormModal open={Boolean(editor)} title={editor ? `${editor.mode === "create" ? "Create" : "Edit"} ${config.title}` : "Rating editor"} description="All values are validated by the backend before becoming effective." onClose={() => setEditor(null)} onSave={() => void saveTable()} saving={saving} saveLabel="Save setup" size="lg">{editor ? (editor.tab === "joint" ? <div className="space-y-4"><div className="grid gap-4 md:grid-cols-2"><TextInput label="Code" name="code" required value={String(editor.record.code ?? "")} onChange={(event: ChangeEvent<HTMLInputElement>) => setEditor((current) => current ? { ...current, record: { ...current.record, code: event.target.value } } : current)} /><TextInput label="Name" name="name" value={String(editor.record.name ?? "")} onChange={(event: ChangeEvent<HTMLInputElement>) => setEditor((current) => current ? { ...current, record: { ...current.record, name: event.target.value } } : current)} /><SelectInput label="Joint-life type" name="joint_life_type" required value={String(editor.record.joint_life_type ?? "FIRST_DEATH")} onChange={(event: ChangeEvent<HTMLSelectElement>) => setEditor((current) => current ? { ...current, record: { ...current.record, joint_life_type: event.target.value } } : current)}><option value="FIRST_DEATH">First death</option><option value="LAST_SURVIVOR">Last survivor</option><option value="JOINT_AND_SURVIVOR">Joint and survivor</option></SelectInput><SelectInput label="Age basis" name="age_basis" required value={String(editor.record.age_basis ?? "YOUNGER_LIFE")} onChange={(event: ChangeEvent<HTMLSelectElement>) => setEditor((current) => current ? { ...current, record: { ...current.record, age_basis: event.target.value } } : current)}><option value="YOUNGER_LIFE">Younger life</option><option value="OLDER_LIFE">Older life</option><option value="AVERAGE_AGE">Average age</option><option value="JOINT_AGE">Joint age</option></SelectInput><TextInput label="Product ID" name="product" value={String(editor.record.product ?? "")} onChange={(event: ChangeEvent<HTMLInputElement>) => setEditor((current) => current ? { ...current, record: { ...current.record, product: event.target.value || null } } : current)} /><TextInput label="Plan ID" name="plan" value={String(editor.record.plan ?? "")} onChange={(event: ChangeEvent<HTMLInputElement>) => setEditor((current) => current ? { ...current, record: { ...current.record, plan: event.target.value || null } } : current)} /><DecimalInput label="Premium adjustment factor" name="premium_adjustment_factor" required value={String(editor.record.premium_adjustment_factor ?? "1")} onChange={(event: ChangeEvent<HTMLInputElement>) => setEditor((current) => current ? { ...current, record: { ...current.record, premium_adjustment_factor: event.target.value } } : current)} /><DateInput label="Effective from" name="effective_from" required value={String(editor.record.effective_from ?? "")} onChange={(event: ChangeEvent<HTMLInputElement>) => setEditor((current) => current ? { ...current, record: { ...current.record, effective_from: event.target.value } } : current)} /><DateInput label="Effective to" name="effective_to" value={String(editor.record.effective_to ?? "")} onChange={(event: ChangeEvent<HTMLInputElement>) => setEditor((current) => current ? { ...current, record: { ...current.record, effective_to: event.target.value || null } } : current)} /></div><TextareaInput label="Survivor benefit rule" name="survivor_benefit_rule" required value={String(editor.record.survivor_benefit_rule ?? "")} onChange={(event: ChangeEvent<HTMLTextAreaElement>) => setEditor((current) => current ? { ...current, record: { ...current.record, survivor_benefit_rule: event.target.value } } : current)} /><TextareaInput label="Underwriting rule" name="underwriting_rule" required value={String(editor.record.underwriting_rule ?? "")} onChange={(event: ChangeEvent<HTMLTextAreaElement>) => setEditor((current) => current ? { ...current, record: { ...current.record, underwriting_rule: event.target.value } } : current)} /></div> : (editor.tab === "premium" || editor.tab === "mortality") ? <div className="space-y-4"><div className="grid gap-4 md:grid-cols-2"><TextInput label="Table code" name="table_code" required value={String(editor.record.table_code ?? "")} onChange={(event: ChangeEvent<HTMLInputElement>) => setEditor((current) => current ? { ...current, record: { ...current.record, table_code: event.target.value } } : current)} /><TextInput label="Name" name="name" required value={String(editor.record.name ?? "")} onChange={(event: ChangeEvent<HTMLInputElement>) => setEditor((current) => current ? { ...current, record: { ...current.record, name: event.target.value } } : current)} /><TextInput label="Version" name="version" required value={String(editor.record.version ?? "1.0")} onChange={(event: ChangeEvent<HTMLInputElement>) => setEditor((current) => current ? { ...current, record: { ...current.record, version: event.target.value } } : current)} /><TextInput label="Rating basis" name="rating_basis" value={String(editor.record.rating_basis ?? "SUM_ASSURED")} onChange={(event: ChangeEvent<HTMLInputElement>) => setEditor((current) => current ? { ...current, record: { ...current.record, rating_basis: event.target.value } } : current)} /><TextInput label="Currency" name="currency" value={String(editor.record.currency ?? "TZS")} onChange={(event: ChangeEvent<HTMLInputElement>) => setEditor((current) => current ? { ...current, record: { ...current.record, currency: event.target.value } } : current)} /><DateInput label="Effective from" name="effective_from" required value={String(editor.record.effective_from ?? "")} onChange={(event: ChangeEvent<HTMLInputElement>) => setEditor((current) => current ? { ...current, record: { ...current.record, effective_from: event.target.value } } : current)} /><DateInput label="Effective to" name="effective_to" value={String(editor.record.effective_to ?? "")} onChange={(event: ChangeEvent<HTMLInputElement>) => setEditor((current) => current ? { ...current, record: { ...current.record, effective_to: event.target.value || null } } : current)} /></div><TextareaInput label="Description" name="description" value={String(editor.record.description ?? "")} onChange={(event: ChangeEvent<HTMLTextAreaElement>) => setEditor((current) => current ? { ...current, record: { ...current.record, description: event.target.value } } : current)} /></div> : <Part2Editor tab={editor.tab as Exclude<RatingTab, "premium" | "mortality" | "joint">} record={editor.record} onChange={(key, value) => setEditor((current) => current ? { ...current, record: { ...current.record, [key]: value } } : current)} />): null}
    </FormModal>
    <ConfirmModal open={Boolean(confirm)} title="Deactivate rating setup" description={`Deactivate ${String(confirm?.table_code ?? confirm?.code ?? "this setup")}? Existing quotation calculations retain their source version.`} onClose={() => setConfirm(null)} onConfirm={() => void deactivate()} />
  </MasterDetailPage>
}
