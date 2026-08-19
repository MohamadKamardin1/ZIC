import { useCallback, useEffect, useMemo, useState } from "react"
import { BarChart3, CalendarDays, Check, FileText, Layers3, ShieldCheck, UserRound, WalletCards } from "lucide-react"
import { request } from "../lib/apiClient"
import { useAccess } from "../lib/access"
import { useToast } from "../components/ui/Toast"
import { DateInput, DecimalInput, FormGrid, InfoBanner, Modal, ReadOnlyField, SearchableSelect, SelectInput, TextInput, TextareaInput, Toggle } from "../components/ui"
import { DataTable, fetchTable, type TableResponse } from "../components/ui/DataTable"
import type { FilterDefinition, FilterOption, FilterValues, RowAction, TableMetadata, WizardStep } from "../components/ui"
import { EditableGrid } from "../components/ui/EditableGrid"
import { FilterBar } from "../components/ui/FilterBar"
import { MasterDetailPage, SimpleAreaChart, KPIStat } from "../components/ui/Patterns"
import { FormModal, Drawer } from "../components/ui/Overlays"
import { Wizard } from "../components/ui/Wizard"

type QuotationRow = Record<string, unknown> & { id?: string; quote_number?: string; quote_name?: string; prospect_name?: string; plans_summary?: string; total_premium?: string | number; currency?: string; status?: string; version?: number; quote_date?: string }
type RateRow = { id: string; description: string; rate: number; paidUpRate: number }

const quotationMetadata: TableMetadata<QuotationRow> = {
  totalLabel: "OL quotations work queue",
  pageSize: 10,
  columns: [
    { key: "quote_number", label: "Quote number", field: "quote_number", sortable: true },
    { key: "quote_name", label: "Quote name", field: "quote_name", sortable: true },
    { key: "prospect_name", label: "Prospect", field: "prospect_name" },
    { key: "plans_summary", label: "Plans", field: "plans_summary" },
    { key: "total_premium", label: "Premium", field: "total_premium", align: "right", render: (value, row) => `${row.currency ?? ""} ${Number(value ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}` },
    { key: "status", label: "Status", field: "status", sortable: true },
    { key: "version", label: "Version", field: "version", align: "center" },
    { key: "quote_date", label: "Quote date", field: "quote_date", sortable: true },
  ],
}

type QuotationSummary = Record<string, unknown>

function summaryValue(summary: QuotationSummary | null, ...keys: string[]) {
  for (const key of keys) {
    const value = summary?.[key]
    if (typeof value === "number") return value
    if (typeof value === "string" && value.trim() !== "" && Number.isFinite(Number(value))) return Number(value)
  }
  return 0
}
const searchOptions: FilterOption[] = [{ label: "Quote number", value: "quote_number" }, { label: "Prospect name", value: "prospect_name" }]

export default function UiKitSandbox() {
  const { access } = useAccess()
  const { toast } = useToast()
  const [filters, setFilters] = useState<FilterValues>({ search: "", quote_date: {} })
  const [modalOpen, setModalOpen] = useState(false)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [searchOption, setSearchOption] = useState("")
  const [activeTab, setActiveTab] = useState("overview")
  const [smoker, setSmoker] = useState(false)
  const [rates, setRates] = useState<RateRow[]>([{ id: "row-1", description: "Year 1", rate: 40, paidUpRate: 30 }, { id: "row-2", description: "Year 2", rate: 60, paidUpRate: 45 }])
  const [stepReady, setStepReady] = useState<Record<string, boolean>>({ quote: true, plans: true, members: false, installments: false, funds: false, riders: false, review: false })
  const [quotationSummary, setQuotationSummary] = useState<QuotationSummary | null>(null)

  useEffect(() => {
    let cancelled = false
    void request<QuotationSummary>("/api/v1/ol/quotations/summary/").then((summary) => {
      if (!cancelled) setQuotationSummary(summary)
    }).catch(() => {
      if (!cancelled) setQuotationSummary(null)
    })
    return () => { cancelled = true }
  }, [])

  const chartData = [
    { name: "Draft", quotations: summaryValue(quotationSummary, "total_drafts", "drafts") },
    { name: "Finalized", quotations: summaryValue(quotationSummary, "total_finalized", "finalized") },
    { name: "Converted", quotations: summaryValue(quotationSummary, "total_converted", "converted") },
    { name: "Expired", quotations: summaryValue(quotationSummary, "total_expired", "expired") },
  ]

  const fetchQuotations = useCallback((query: Parameters<typeof fetchTable<QuotationRow>>[1]) => fetchTable<QuotationRow>("/api/v1/ol/quotations/", query), [])
  const filtersForTable = useMemo(() => filters, [filters])
  const permissionStrings = access.permissions.map((permission) => `${permission.module}.${permission.action}`)
  const quotationActions: RowAction<QuotationRow>[] = [
    { key: "view", label: "View quotation", permission: "ol_quotations.view", onSelect: () => toast({ title: "View action selected", message: "The quotation detail route will consume this action contract.", tone: "info" }) },
    { key: "edit", label: "Edit quotation", permission: "ol_quotations.update", isVisible: (row) => String(row.status).toLowerCase() === "draft", onSelect: () => toast({ title: "Edit action selected", tone: "info" }) },
    { key: "delete", label: "Delete quotation", permission: "ol_quotations.delete", tone: "danger", isVisible: (row) => String(row.status).toLowerCase() === "draft", onSelect: () => toast({ title: "Delete action selected", tone: "warning" }) },
  ]
  const filterDefinitions: FilterDefinition[] = [{ key: "quote_date", label: "Quote date", type: "date-range" }]
  const wizardSteps: WizardStep[] = [
    { id: "quote", label: "Personal details", icon: UserRound, content: <InfoBanner title="Personal details">Identity, date of birth, gender, smoker status, location, and agent are supplied by the quotation wizard.</InfoBanner>, validate: () => stepReady.quote },
    { id: "plans", label: "Plan selection", icon: Layers3, content: <InfoBanner title="Plan configuration">Select active OL plans and configure term, frequency, and benefit options from parameter catalogs.</InfoBanner>, validate: () => stepReady.plans },
    { id: "members", label: "Member coverage", icon: ShieldCheck, content: <InfoBanner title="Member coverage">The principal member is derived from personal details; additional members are enabled by selected plan configuration.</InfoBanner>, validate: () => stepReady.members },
    { id: "installments", label: "Installments", icon: CalendarDays, content: <InfoBanner title="Installments">Configure payment mode, annuity period, maturity toggles, and rate rows.</InfoBanner>, validate: () => stepReady.installments },
    { id: "funds", label: "Investment funds", icon: WalletCards, content: <InfoBanner title="Investment funds">Allocate active investment funds for investment-linked plans and validate totals to 100%.</InfoBanner>, validate: () => stepReady.funds },
    { id: "riders", label: "Riders & benefits", icon: FileText, content: <InfoBanner title="Riders & benefits">Attach applicable riders and configure fixed, ratio, loaded, discounted, and capped benefits.</InfoBanner>, validate: () => stepReady.riders },
    { id: "review", label: "Review & calculate", icon: Check, content: <InfoBanner title="Review">Calculate the premium, confirm financial details, finalize, print, verify partner, and convert to proposal.</InfoBanner>, validate: () => stepReady.review },
  ]

  function updateFilter(key: string, value: FilterValues[string]) { setFilters((current) => ({ ...current, [key]: value })) }
  function setReady(id: string, value: boolean) { setStepReady((current) => ({ ...current, [id]: value })) }

  return <MasterDetailPage eyebrow="UI kit sandbox" title="Reusable screen patterns" description="A living catalog of the table, form, modal, grid, wizard, and analytics components used across ZIC modules." status={{ value: "Foundation ready", tone: "success" }} actions={<><button type="button" className="button-secondary border-white/30 bg-white/10 text-white hover:bg-white/20" onClick={() => setDrawerOpen(true)}>Open drawer</button><button type="button" className="button-secondary border-white/30 bg-white/10 text-white hover:bg-white/20" onClick={() => setModalOpen(true)}>Open modal</button></>} stats={[{ label: "Components", value: "24", helper: "Reusable contracts" }, { label: "Wizard steps", value: "7", helper: "Validation gated" }, { label: "Backend table", value: "Live", helper: "OL quotations" }, { label: "Access", value: access.permissions.length || "Fallback", helper: "IAM metadata" }]} tabs={[{ id: "overview", label: "Overview" }, { id: "forms", label: "Forms & overlays" }, { id: "workflow", label: "Wizard & grid" }]} activeTab={activeTab} onTabChange={setActiveTab}><div className="space-y-5">{activeTab === "overview" && <><FilterBar definitions={filterDefinitions} value={filters} onChange={updateFilter} onApply={() => toast({ title: "Filters applied", tone: "success" })} onReset={() => setFilters({ search: "", quote_date: {} })} /><DataTable metadata={quotationMetadata} fetcher={fetchQuotations} filters={filtersForTable} actions={quotationActions} permissions={permissionStrings} canAction={(action) => !action.permission || permissionStrings.length === 0 || permissionStrings.includes(action.permission)} caption="Live OL quotation list" /></>}{activeTab === "forms" && <div className="space-y-5"><div className="surface-card p-5"><div className="mb-4"><h2 className="text-lg font-bold">Form primitives</h2><p className="text-sm text-[var(--muted-foreground)]">Labels, validation states, searchable choices, and computed read-only values.</p></div><FormGrid columns={3}><TextInput label="Quote name" required placeholder="e.g. Family protection" /><DecimalInput label="Sum assured" required placeholder="0.00" /><DateInput label="Quote date" required /><SelectInput label="Payment frequency"><option value="">Select frequency</option><option value="annual">Provided by backend</option></SelectInput><SearchableSelect label="Agent" options={searchOptions} value={searchOption} onChange={setSearchOption} /><ReadOnlyField label="Age at quote" value="34 years" hint="Computed from date of birth" /><TextareaInput label="Address" className="md:col-span-2" placeholder="Address" /><Toggle label="Smoker status" checked={smoker} onChange={setSmoker} hint="Example boolean control" /></FormGrid></div><div className="surface-card p-5"><h2 className="text-lg font-bold">Feedback and overlays</h2><p className="mt-1 text-sm text-[var(--muted-foreground)]">Open the modal or drawer from the page header to verify keyboard and focus behavior.</p><div className="mt-4 flex flex-wrap gap-2"><button type="button" className="button-primary" onClick={() => toast({ title: "Saved successfully", message: "Toast notifications are available to every module.", tone: "success" })}>Show success toast</button><button type="button" className="button-secondary" onClick={() => toast({ title: "Validation required", message: "Resolve the highlighted fields before continuing.", tone: "warning" })}>Show warning toast</button></div></div></div>}{activeTab === "workflow" && <div className="space-y-5"><Wizard steps={wizardSteps} onCancel={() => toast({ title: "Wizard cancelled", tone: "info" })} onComplete={() => toast({ title: "Wizard complete", tone: "success" })} onAutosave={(step) => { if (step.id === "quote") return; }} /><div className="surface-card p-5"><div className="mb-4"><h2 className="text-lg font-bold">Validation gating controls</h2><p className="text-sm text-[var(--muted-foreground)]">Toggle steps off to observe the Next button blocking navigation and showing an invalid step state.</p></div><div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">{wizardSteps.map((step) => <Toggle key={step.id} label={step.label} checked={stepReady[step.id]} onChange={(value) => setReady(step.id, value)} />)}</div></div><EditableGrid rows={rates} columns={[{ key: "description", label: "Description", render: (row, _index, update) => <input value={row.description} onChange={(event) => update({ description: event.target.value })} className="h-9 w-full rounded-md border bg-[var(--card)] px-2 text-sm" aria-label="Rate description" /> }, { key: "rate", label: "Rate (%)", render: (row, _index, update) => <input type="number" step="any" value={row.rate} onChange={(event) => update({ rate: Number(event.target.value) })} className="h-9 w-full rounded-md border bg-[var(--card)] px-2 text-sm" aria-label="Rate percent" /> }, { key: "paidUpRate", label: "Paid-up rate", render: (row, _index, update) => <input type="number" step="any" value={row.paidUpRate} onChange={(event) => update({ paidUpRate: Number(event.target.value) })} className="h-9 w-full rounded-md border bg-[var(--card)] px-2 text-sm" aria-label="Paid-up rate" /> }]} getRowId={(row) => row.id} createRow={() => ({ id: `row-${Date.now()}`, description: "New row", rate: 0, paidUpRate: 0 })} onChange={setRates} validateRow={(row) => ({ ...(row.description.trim() ? {} : { description: "Description is required." }), ...(row.rate >= 0 ? {} : { rate: "Rate cannot be negative." }) })} total={{ label: "Rate total", getValue: (row) => row.rate, target: 100, format: (value) => `${value.toFixed(2)}%` }} /></div>}</div><Modal open={modalOpen} title="Form modal" description="Reusable save/cancel footer contract." onClose={() => setModalOpen(false)} footer={<><button type="button" className="button-secondary" onClick={() => setModalOpen(false)}>Cancel</button><button type="button" className="button-primary" onClick={() => { setModalOpen(false); toast({ title: "Modal saved", tone: "success" }) }}>Save changes</button></>}><InfoBanner title="Info slot">Use this slot for guidance, parameter rules, or warning context before a form action.</InfoBanner></Modal><FormModal open={false} title="Hidden form modal" onClose={() => undefined} onSave={() => undefined}>Form</FormModal><Drawer open={drawerOpen} title="Detail drawer" description="Master-detail screens can use the same accessible drawer contract." onClose={() => setDrawerOpen(false)}><div className="space-y-4"><KPIStat label="Selected record" value="Quotation" helper="Drawer content slot" /><p className="text-sm leading-6 text-[var(--muted-foreground)]">The drawer is suitable for quick inspection, action confirmation, or parameter forms without leaving the work queue.</p></div></Drawer><div className="grid gap-5 xl:grid-cols-[1fr_1.7fr]"><SimpleAreaChart data={chartData} dataKey="quotations" title="Quotation activity" /><div className="surface-card p-5"><div className="mb-4 flex items-center gap-2"><BarChart3 size={18} className="text-[var(--primary)]" aria-hidden="true" /><h2 className="text-sm font-bold">Component documentation</h2></div><div className="grid gap-3 text-sm text-[var(--muted-foreground)] md:grid-cols-2"><p><strong className="text-[var(--foreground)]">DataTable:</strong> pass backend column metadata and a fetcher that returns `{`results, count`}`.</p><p><strong className="text-[var(--foreground)]">Wizard:</strong> provide seven typed steps with async validation functions and draft autosave.</p><p><strong className="text-[var(--foreground)]">EditableGrid:</strong> supply cell renderers, a row factory, and a totals target such as 100%.</p><p><strong className="text-[var(--foreground)]">Permissions:</strong> gate row actions through IAM permission strings and state predicates.</p></div></div></div></MasterDetailPage>
}
