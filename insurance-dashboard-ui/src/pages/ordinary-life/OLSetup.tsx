import { useState, useEffect } from "react";
import { Bell, Undo2, FileText, Wallet, Banknote, RefreshCw, HandCoins, Percent, Users, Settings, TrendingDown, TrendingUp, Calculator, Sliders, Shield, Clock, CheckSquare, HeartPulse, CheckCircle, Activity, Plus, Edit2, Trash2, X, Search, ChevronRight, AlertCircle, Filter, Loader2, PlayCircle, Package, Check, Edit3 } from 'lucide-react'
import { olSetup } from "../../lib/ol-api"

interface FieldDef {
  key: string
  label: string
  type?: "text" | "number" | "boolean" | "date" | "select" | "textarea"
  required?: boolean
  /** Static choices for select fields: [{value, label}] */
  choices?: { value: string; label: string }[]
  /** Async options loader for FK select fields — returns list of {id, name|code} */
  optionsFn?: () => Promise<any>
  /** Which field to use as the option label (default: "name") */
  optionLabel?: string
  /** Which field to display in the table for FK fields */
  displayKey?: string
  /** Lookup category for dynamic choices (e.g. "GENDER") */
  lookupCategory?: string
}

interface SetupCategory {
  key: string
  label: string
  group: string
  icon: typeof Settings
  color: string
  gradient: string
  fetchFn: (params?: Record<string, string>) => Promise<any>
  createFn?: (data: Record<string, unknown>) => Promise<any>
  updateFn?: (id: string, data: Record<string, unknown>) => Promise<any>
  deleteFn?: (id: string) => Promise<void>
  fields: FieldDef[]
}

const SETUP_CATEGORIES: SetupCategory[] = [
  // ── OL Lookup Values ──────────────────────────────────────────────
  {
    key: "lookupValues", label: "Dropdown Configuration", group: "General Configuration", icon: Settings,
    color: "#a855f7", gradient: "linear-gradient(135deg, #a855f7, #d946ef)",
    fetchFn: olSetup.listLookupValues, createFn: (d) => olSetup.createLookupValue(d),
    updateFn: (id, d) => olSetup.updateLookupValue(id, d), deleteFn: (id) => olSetup.deleteLookupValue(id),
    fields: [
      { key: "category", label: "Category Key (e.g. POLICY_STATUS)", type: "text", required: true },
      { key: "value", label: "Stored Value", type: "text", required: true },
      { key: "label", label: "Display Label", type: "text", required: true },
      { key: "sort_order", label: "Sort Order", type: "number", required: false },
      { key: "is_active", label: "Is Active", type: "boolean", required: false },
    ],
  },
  
  // ── OL Default Setups ──────────────────────────────────────────────
  {
    key: "defaultSystemParameters", label: "Default System Parameters", group: "OL Default Setups", icon: Sliders,
    color: "#3b82f6", gradient: "linear-gradient(135deg, #3b82f6, #60a5fa)",
    fetchFn: olSetup.listDefaultSystemParameters, createFn: (d) => olSetup.createDefaultSystemParameter(d),
    updateFn: (id, d) => olSetup.updateDefaultSystemParameter(id, d), deleteFn: (id) => olSetup.deleteDefaultSystemParameter(id),
    fields: [
      { key: "code", label: "Parameter Code", type: "text", required: true },
      { key: "name", label: "Parameter Name", type: "text", required: true },
      { key: "value", label: "Parameter Value", type: "text", required: true },
      { key: "description", label: "Description", type: "text", required: false },
      { key: "is_active", label: "Is Active", type: "boolean", required: false },
    ],
  },
  {
    key: "overrideCommissionSetup", label: "Override Commission Setup", group: "OL Default Setups", icon: Percent,
    color: "#f59e0b", gradient: "linear-gradient(135deg, #f59e0b, #fbbf24)",
    fetchFn: olSetup.listOverrideCommissionSetups, createFn: (d) => olSetup.createOverrideCommissionSetup(d),
    updateFn: (id, d) => olSetup.updateOverrideCommissionSetup(id, d), deleteFn: (id) => olSetup.deleteOverrideCommissionSetup(id),
    fields: [
      { key: "role_name", label: "Role Name", type: "text", required: true },
      { key: "override_percentage", label: "Override %", type: "number", required: true },
      { key: "effective_date", label: "Effective Date", type: "date", required: true },
      { key: "is_active", label: "Is Active", type: "boolean", required: false },
    ],
  },
  {
    key: "computationApproaches", label: "Computation Approach", group: "OL Default Setups", icon: Calculator,
    color: "#10b981", gradient: "linear-gradient(135deg, #10b981, #34d399)",
    fetchFn: olSetup.listComputationApproaches, createFn: (d) => olSetup.createComputationApproach(d),
    updateFn: (id, d) => olSetup.updateComputationApproach(id, d), deleteFn: (id) => olSetup.deleteComputationApproach(id),
    fields: [
      { key: "code", label: "Code", type: "text", required: true },
      { key: "name", label: "Name", type: "text", required: true },
      { key: "description", label: "Description", type: "text", required: false },
      { key: "is_active", label: "Is Active", type: "boolean", required: false },
    ],
  },
  {
    key: "maturityClaimSetup", label: "Maturity Claims Setup", group: "OL Default Setups", icon: CheckSquare,
    color: "#6366f1", gradient: "linear-gradient(135deg, #6366f1, #818cf8)",
    fetchFn: olSetup.listMaturityClaimSetups, createFn: (d) => olSetup.createMaturityClaimSetup(d),
    updateFn: (id, d) => olSetup.updateMaturityClaimSetup(id, d), deleteFn: (id) => olSetup.deleteMaturityClaimSetup(id),
    fields: [
      { key: "code", label: "Code", type: "text", required: true },
      { key: "name", label: "Name", type: "text", required: true },
      { key: "notification_days_prior", label: "Notification Days Prior", type: "number", required: true },
      { key: "requires_discharge_voucher", label: "Requires Discharge Voucher", type: "boolean", required: false },
      { key: "is_active", label: "Is Active", type: "boolean", required: false },
    ],
  },

  // ── OL Policy Setup ──────────────────────────────────────────────
  {
    key: "anticipatedEndowmentRates", label: "Anticipated Endowment Rates", group: "OL Policy Setup", icon: TrendingUp,
    color: "#ec4899", gradient: "linear-gradient(135deg, #ec4899, #f472b6)",
    fetchFn: olSetup.listAnticipatedEndowmentInstallmentRates, createFn: (d) => olSetup.createAnticipatedEndowmentInstallmentRate(d),
    updateFn: (id, d) => olSetup.updateAnticipatedEndowmentInstallmentRate(id, d), deleteFn: (id) => olSetup.deleteAnticipatedEndowmentInstallmentRate(id),
    fields: [
      { key: "policy_year", label: "Policy Year", type: "number", required: true },
      { key: "percentage_payout", label: "Percentage Payout", type: "number", required: true },
      { key: "is_active", label: "Is Active", type: "boolean", required: false },
    ],
  },
  {
    key: "gracePeriods", label: "Grace Period", group: "OL Policy Setup", icon: Clock,
    color: "#8b5cf6", gradient: "linear-gradient(135deg, #8b5cf6, #a78bfa)",
    fetchFn: olSetup.listGracePeriods, createFn: (d) => olSetup.createGracePeriod(d),
    updateFn: (id, d) => olSetup.updateGracePeriod(id, d), deleteFn: (id) => olSetup.deleteGracePeriod(id),
    fields: [
      { key: "code", label: "Code", type: "text", required: true },
      { key: "days", label: "Days", type: "number", required: true },
      { key: "description", label: "Description", type: "text", required: false },
      { key: "is_active", label: "Is Active", type: "boolean", required: false },
    ],
  },
  {
    key: "policyStatuses", label: "Policy Statuses", group: "OL Policy Setup", icon: Activity,
    color: "#14b8a6", gradient: "linear-gradient(135deg, #14b8a6, #2dd4bf)",
    fetchFn: olSetup.listPolicyStatuses, createFn: (d) => olSetup.createPolicyStatus(d),
    updateFn: (id, d) => olSetup.updatePolicyStatus(id, d), deleteFn: (id) => olSetup.deletePolicyStatus(id),
    fields: [
      { key: "code", label: "Code", type: "text", required: true },
      { key: "name", label: "Name", type: "text", required: true },
      { key: "is_terminal", label: "Is Terminal", type: "boolean", required: false },
      { key: "is_active", label: "Is Active", type: "boolean", required: false },
    ],
  },
  {
    key: "policyRenewalStatuses", label: "Policy Renewal Status", group: "OL Policy Setup", icon: RefreshCw,
    color: "#0ea5e9", gradient: "linear-gradient(135deg, #0ea5e9, #38bdf8)",
    fetchFn: olSetup.listPolicyRenewalStatuses, createFn: (d) => olSetup.createPolicyRenewalStatus(d),
    updateFn: (id, d) => olSetup.updatePolicyRenewalStatus(id, d), deleteFn: (id) => olSetup.deletePolicyRenewalStatus(id),
    fields: [
      { key: "code", label: "Code", type: "text", required: true },
      { key: "name", label: "Name", type: "text", required: true },
      { key: "is_active", label: "Is Active", type: "boolean", required: false },
    ],
  },
  {
    key: "beneficiaryTypes", label: "Beneficiary Types", group: "OL Policy Setup", icon: Users,
    color: "#ef4444", gradient: "linear-gradient(135deg, #ef4444, #f87171)",
    fetchFn: olSetup.listBeneficiaryTypes, createFn: (d) => olSetup.createBeneficiaryType(d),
    updateFn: (id, d) => olSetup.updateBeneficiaryType(id, d), deleteFn: (id) => olSetup.deleteBeneficiaryType(id),
    fields: [
      { key: "code", label: "Code", type: "text", required: true },
      { key: "name", label: "Name", type: "text", required: true },
      { key: "is_active", label: "Is Active", type: "boolean", required: false },
    ],
  },
  {
    key: "memberCoverConfigurations", label: "Member Cover Configuration", group: "OL Policy Setup", icon: Shield,
    color: "#eab308", gradient: "linear-gradient(135deg, #eab308, #facc15)",
    fetchFn: olSetup.listMemberCoverConfigurations, createFn: (d) => olSetup.createMemberCoverConfiguration(d),
    updateFn: (id, d) => olSetup.updateMemberCoverConfiguration(id, d), deleteFn: (id) => olSetup.deleteMemberCoverConfiguration(id),
    fields: [
      { key: "code", label: "Code", type: "text", required: true },
      { key: "name", label: "Name", type: "text", required: true },
      { key: "max_dependents", label: "Max Dependents", type: "number", required: false },
      { key: "is_active", label: "Is Active", type: "boolean", required: false },
    ],
  },
  {
    key: "surrenderSetup", label: "Surrender Setup", group: "OL Policy Setup", icon: HandCoins,
    color: "#f43f5e", gradient: "linear-gradient(135deg, #f43f5e, #fb7185)",
    fetchFn: olSetup.listSurrenderSetups, createFn: (d) => olSetup.createSurrenderSetup(d),
    updateFn: (id, d) => olSetup.updateSurrenderSetup(id, d), deleteFn: (id) => olSetup.deleteSurrenderSetup(id),
    fields: [
      { key: "code", label: "Code", type: "text", required: true },
      { key: "min_years_in_force", label: "Min Years in Force", type: "number", required: true },
      { key: "penalty_percentage", label: "Penalty %", type: "number", required: true },
      { key: "is_active", label: "Is Active", type: "boolean", required: false },
    ],
  },
  {
    key: "paidUpSetup", label: "Paid Up Setup", group: "OL Policy Setup", icon: Wallet,
    color: "#22c55e", gradient: "linear-gradient(135deg, #22c55e, #4ade80)",
    fetchFn: olSetup.listPaidUpSetups, createFn: (d) => olSetup.createPaidUpSetup(d),
    updateFn: (id, d) => olSetup.updatePaidUpSetup(id, d), deleteFn: (id) => olSetup.deletePaidUpSetup(id),
    fields: [
      { key: "code", label: "Code", type: "text", required: true },
      { key: "min_years_in_force", label: "Min Years in Force", type: "number", required: true },
      { key: "is_active", label: "Is Active", type: "boolean", required: false },
    ],
  },
  {
    key: "surrenderValueRates", label: "Surrender Value Rates", group: "OL Policy Setup", icon: TrendingDown,
    color: "#d946ef", gradient: "linear-gradient(135deg, #d946ef, #e879f9)",
    fetchFn: olSetup.listSurrenderValueRates, createFn: (d) => olSetup.createSurrenderValueRate(d),
    updateFn: (id, d) => olSetup.updateSurrenderValueRate(id, d), deleteFn: (id) => olSetup.deleteSurrenderValueRate(id),
    fields: [
      { key: "policy_year", label: "Policy Year", type: "number", required: true },
      { key: "rate_factor", label: "Rate Factor", type: "number", required: true },
      { key: "is_active", label: "Is Active", type: "boolean", required: false },
    ],
  },
  {
    key: "paidUpRates", label: "Paid Up Rates", group: "OL Policy Setup", icon: Banknote,
    color: "#64748b", gradient: "linear-gradient(135deg, #64748b, #94a3b8)",
    fetchFn: olSetup.listPaidUpRates, createFn: (d) => olSetup.createPaidUpRate(d),
    updateFn: (id, d) => olSetup.updatePaidUpRate(id, d), deleteFn: (id) => olSetup.deletePaidUpRate(id),
    fields: [
      { key: "policy_year", label: "Policy Year", type: "number", required: true },
      { key: "rate_factor", label: "Rate Factor", type: "number", required: true },
      { key: "is_active", label: "Is Active", type: "boolean", required: false },
    ],
  },
  {
    key: "commitmentStatuses", label: "Commitment Statuses", group: "OL Policy Setup", icon: CheckCircle,
    color: "#0284c7", gradient: "linear-gradient(135deg, #0284c7, #38bdf8)",
    fetchFn: olSetup.listCommitmentStatuses, createFn: (d) => olSetup.createCommitmentStatus(d),
    updateFn: (id, d) => olSetup.updateCommitmentStatus(id, d), deleteFn: (id) => olSetup.deleteCommitmentStatus(id),
    fields: [
      { key: "code", label: "Code", type: "text", required: true },
      { key: "name", label: "Name", type: "text", required: true },
      { key: "is_active", label: "Is Active", type: "boolean", required: false },
    ],
  },
  {
    key: "healthQuestions", label: "Health Questions", group: "OL Policy Setup", icon: HeartPulse,
    color: "#f43f5e", gradient: "linear-gradient(135deg, #f43f5e, #fb7185)",
    fetchFn: olSetup.listHealthQuestions, createFn: (d) => olSetup.createHealthQuestion(d),
    updateFn: (id, d) => olSetup.updateHealthQuestion(id, d), deleteFn: (id) => olSetup.deleteHealthQuestion(id),
    fields: [
      { key: "code", label: "Question Code", type: "text", required: true },
      { key: "question_text", label: "Question Text", type: "text", required: true },
      { key: "category", label: "Category", type: "text", required: false },
      { key: "is_active", label: "Is Active", type: "boolean", required: false },
    ],
  },
  {
    key: "healthQuestionnaires", label: "Health Questionnaires", group: "OL Policy Setup", icon: FileText,
    color: "#3b82f6", gradient: "linear-gradient(135deg, #3b82f6, #60a5fa)",
    fetchFn: olSetup.listHealthQuestionnaires, createFn: (d) => olSetup.createHealthQuestionnaire(d),
    updateFn: (id, d) => olSetup.updateHealthQuestionnaire(id, d), deleteFn: (id) => olSetup.deleteHealthQuestionnaire(id),
    fields: [
      { key: "code", label: "Questionnaire Code", type: "text", required: true },
      { key: "name", label: "Name", type: "text", required: true },
      { key: "version", label: "Version", type: "text", required: false },
      { key: "effective_date", label: "Effective Date", type: "date", required: true },
      { key: "is_active", label: "Is Active", type: "boolean", required: false },
    ],
  },
  {
    key: "gracePeriodNotificationSchedules", label: "Grace Period Notification Schedule", group: "OL Policy Setup", icon: Bell,
    color: "#f59e0b", gradient: "linear-gradient(135deg, #f59e0b, #fbbf24)",
    fetchFn: olSetup.listGracePeriodNotificationSchedules, createFn: (d) => olSetup.createGracePeriodNotificationSchedule(d),
    updateFn: (id, d) => olSetup.updateGracePeriodNotificationSchedule(id, d), deleteFn: (id) => olSetup.deleteGracePeriodNotificationSchedule(id),
    fields: [
      { key: "days_past_due", label: "Days Past Due", type: "number", required: true },
      { key: "notification_type", label: "Notification Type", type: "text", required: true },
      { key: "is_active", label: "Is Active", type: "boolean", required: false },
    ],
  },
  {
    key: "reinstatementWindows", label: "Reinstatement Window", group: "OL Policy Setup", icon: Undo2,
    color: "#10b981", gradient: "linear-gradient(135deg, #10b981, #34d399)",
    fetchFn: olSetup.listReinstatementWindows, createFn: (d) => olSetup.createReinstatementWindow(d),
    updateFn: (id, d) => olSetup.updateReinstatementWindow(id, d), deleteFn: (id) => olSetup.deleteReinstatementWindow(id),
    fields: [
      { key: "max_months", label: "Max Months", type: "number", required: true },
      { key: "requires_medical", label: "Requires Medical", type: "boolean", required: false },
      { key: "is_active", label: "Is Active", type: "boolean", required: false },
    ],
  },
]


// Group setup categories by their group name
function groupByGroup(categories: SetupCategory[]) {
  const groups: { name: string; items: SetupCategory[] }[] = []
  const map = new Map<string, SetupCategory[]>()
  for (const cat of categories) {
    const existing = map.get(cat.group)
    if (existing) {
      existing.push(cat)
    } else {
      const arr = [cat]
      map.set(cat.group, arr)
      groups.push({ name: cat.group, items: arr })
    }
  }
  return groups
}

const SETUP_GROUPS = groupByGroup(SETUP_CATEGORIES)


export default function GCSetup() {
  const [activeCat, setActiveCat] = useState<SetupCategory | null>(null)
  const [items, setItems] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState("")
  const [showForm, setShowForm] = useState(false)
  const [editItem, setEditItem] = useState<any>(null)
  const [formData, setFormData] = useState<Record<string, any>>({})
  const [saving, setSaving] = useState(false)
  const [deleteItem, setDeleteItem] = useState<any>(null)
  const [counts, setCounts] = useState<Record<string, number>>({})
  // FK dropdown options: { [fieldKey]: [{id, name, ...}] }
  const [fkOptions, setFkOptions] = useState<Record<string, any[]>>({})
  // Global cache of lookup values: { [category]: [{value, label, ...}] }
  const [globalLookups, setGlobalLookups] = useState<Record<string, any[]>>({})
  const [lookupFilter, setLookupFilter] = useState("All")

  useEffect(() => {
    // Load all lookup values for table display
    olSetup.listLookupValues().then((res) => {
      const list = res?.results ?? res?.data ?? res ?? []
      const map: Record<string, any[]> = {}
      list.forEach((item: any) => {
        if (!map[item.category]) map[item.category] = []
        map[item.category].push(item)
      })
      setGlobalLookups(map)
    }).catch(console.error)

    SETUP_CATEGORIES.forEach(async (cat) => {
      try {
        const res = await cat.fetchFn()
        const list = res?.results ?? res?.data ?? res ?? []
        setCounts((prev) => ({ ...prev, [cat.key]: Array.isArray(list) ? list.length : 0 }))
      } catch { /* ignore */ }
    })
  }, [])

  async function loadCategory(cat: SetupCategory) {
    setActiveCat(cat)
    setLoading(true)
    setSearch("")
    try {
      const res = await cat.fetchFn()
      setItems(res?.results ?? res?.data ?? res ?? [])
    } catch (err: any) {
      console.error(err)
      setItems([])
    } finally {
      setLoading(false)
    }
  }

  async function loadFkOptions(cat: SetupCategory) {
    const opts: Record<string, any[]> = {}
    for (const f of cat.fields) {
      if (f.type === "select" && f.optionsFn) {
        try {
          const res = await f.optionsFn()
          const list = res?.results ?? res?.data ?? res ?? []
          opts[f.key] = Array.isArray(list) ? list : []
        } catch {
          opts[f.key] = []
        }
      }
    }
    setFkOptions(opts)
  }

  function openCreate() {
    setEditItem(null)
    setFormData({})
    setShowForm(true)
    if (activeCat) loadFkOptions(activeCat)
  }

  function openEdit(item: any) {
    setEditItem(item)
    setFormData({ ...item })
    setShowForm(true)
    if (activeCat) loadFkOptions(activeCat)
  }

  async function handleSave() {
    if (!activeCat) return
    setSaving(true)
    try {
      if (editItem && activeCat.updateFn) {
        await activeCat.updateFn(editItem.id, formData)
      } else if (activeCat.createFn) {
        await activeCat.createFn(formData)
      }
      setShowForm(false)
      await loadCategory(activeCat)
    } catch (err: any) {
      alert(err.message)
    } finally {
      setSaving(false)
    }
  }

  function handleDeleteClick(item: any) {
    setDeleteItem(item)
  }

  async function confirmDelete() {
    if (!activeCat?.deleteFn || !deleteItem) return
    setSaving(true)
    try {
      await activeCat.deleteFn(deleteItem.id)
      await loadCategory(activeCat)
      setDeleteItem(null)
    } catch (err: any) {
      alert(err.message)
    } finally {
      setSaving(false)
    }
  }

  const uniqueLookupCategories = activeCat?.key === "lookupValues" ? Array.from(new Set(items.map((i: any) => i.category))).sort() : []

  const filtered = items.filter((item) => {
    if (activeCat?.key === "lookupValues" && lookupFilter !== "All" && item.category !== lookupFilter) return false
    
    if (!search) return true
    const s = search.toLowerCase()
    return (
      item.name?.toLowerCase().includes(s) ||
      item.code?.toLowerCase().includes(s) ||
      item.description?.toLowerCase().includes(s) ||
      item.question_text?.toLowerCase().includes(s)
    )
  })

  // Category grid view — grouped by section
  if (!activeCat) {
    return (
      <div className="p-6 max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-3">
            <div className="p-2 rounded-xl" style={{ background: "linear-gradient(135deg, #6366f1, #8b5cf6)" }}>
              <Settings className="h-6 w-6 text-white" />
            </div>
            Ordinary Life Parameters
          </h1>
          <p className="text-muted-foreground mt-1">Configure all parameters, products, and lookup tables for Group Life insurance.</p>
        </div>

        {SETUP_GROUPS.map((group) => (
          <div key={group.name} className="mb-8">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground mb-3 flex items-center gap-2">
              <div className="h-px flex-1 bg-border" />
              <span className="px-2">{group.name}</span>
              <div className="h-px flex-1 bg-border" />
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {group.items.map((cat) => {
                const Icon = cat.icon
                return (
                  <button
                    key={cat.key}
                    onClick={() => loadCategory(cat)}
                    className="group relative overflow-hidden rounded-2xl border border-border bg-card p-5 text-left transition-all duration-300 hover:shadow-xl hover:shadow-primary/5 hover:-translate-y-1 hover:border-primary/30"
                  >
                    <div className="absolute inset-0 opacity-0 transition-opacity group-hover:opacity-5" style={{ background: cat.gradient }} />
                    <div className="flex items-start justify-between">
                      <div className="rounded-xl p-2.5 shadow-lg" style={{ background: cat.gradient }}>
                        <Icon className="h-5 w-5 text-white" />
                      </div>
                      <ChevronRight className="h-4 w-4 text-muted-foreground transition-transform group-hover:translate-x-1" />
                    </div>
                    <h3 className="mt-3 text-sm font-semibold text-foreground">{cat.label}</h3>
                    <p className="mt-0.5 text-xs text-muted-foreground">
                      {counts[cat.key] !== undefined ? `${counts[cat.key]} items` : "Loading..."}
                    </p>
                  </button>
                )
              })}
            </div>
          </div>
        ))}
      </div>
    )
  }

  // Detail list view
  const Icon = activeCat.icon
  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between flex-wrap gap-4">
        <div className="flex items-center gap-3">
          <button onClick={() => setActiveCat(null)} className="p-2 rounded-lg border border-border bg-card hover:bg-secondary transition">
            <ChevronRight className="h-4 w-4 rotate-180 text-foreground" />
          </button>
          <div className="p-2 rounded-xl shadow-lg" style={{ background: activeCat.gradient }}>
            <Icon className="h-5 w-5 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-foreground">{activeCat.label}</h1>
            <p className="text-xs text-muted-foreground">{activeCat.group} • {filtered.length} items</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {activeCat.key === "lookupValues" && (
            <select
              value={lookupFilter}
              onChange={(e) => setLookupFilter(e.target.value)}
              className="h-10 rounded-xl border border-border bg-card px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40 appearance-none min-w-[160px]"
            >
              <option value="All">All Categories</option>
              {uniqueLookupCategories.map((c: any) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          )}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search..."
              className="h-10 rounded-xl border border-border bg-card pl-10 pr-4 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40 w-56"
            />
          </div>
          {activeCat.createFn && (
            <button
              onClick={openCreate}
              className="flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-medium text-white shadow-lg transition hover:opacity-90"
              style={{ background: activeCat.gradient }}
            >
              <Plus className="h-4 w-4" /> Add
            </button>
          )}
        </div>
      </div>

      {/* Table */}
      <div className="overflow-hidden rounded-2xl border border-border bg-card shadow-sm">
        {loading ? (
          <div className="flex items-center justify-center p-16">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center p-16 text-muted-foreground">
            <Package className="h-12 w-12 mb-3 opacity-40" />
            <p className="text-lg font-medium">No items found</p>
            <p className="text-sm">Create your first {activeCat.label.toLowerCase()} to get started.</p>
          </div>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="border-b border-border bg-secondary/30">
                {activeCat.fields.slice(0, 5).map((f) => (
                  <th key={f.key} className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">{f.label}</th>
                ))}
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">Status</th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-muted-foreground">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {filtered.map((item: any) => (
                <tr key={item.id} className="group transition hover:bg-secondary/20">
                  {activeCat.fields.slice(0, 5).map((f) => {
                    let cellValue: any
                    if (f.type === "boolean") {
                      cellValue = item[f.key] ? <Check className="h-4 w-4 text-emerald-500" /> : <X className="h-4 w-4 text-muted-foreground/40" />
                    } else if (f.type === "select" && f.displayKey && item[f.displayKey]) {
                      // FK field — show the display name from serializer (e.g. sub_product_name)
                      cellValue = item[f.displayKey]
                    } else if (f.type === "select" && f.lookupCategory) {
                      // Lookup field — get label from globalLookups
                      const options = globalLookups[f.lookupCategory] || []
                      const match = options.find((o) => o.value === item[f.key])
                      cellValue = match ? match.label : (item[f.key] ?? "—")
                    } else if (f.type === "select" && f.choices) {
                      // Choice field — show the human label
                      const match = f.choices.find((c) => c.value === item[f.key])
                      cellValue = match ? match.label : (item[f.key] ?? "—")
                    } else {
                      cellValue = String(item[f.key] ?? "—")
                    }
                    return (
                      <td key={f.key} className="px-4 py-3.5 text-sm text-foreground">
                        {cellValue}
                      </td>
                    )
                  })}
                  <td className="px-4 py-3.5">
                    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
                      item.is_active !== false
                        ? "bg-emerald-500/10 text-emerald-500"
                        : "bg-red-500/10 text-red-500"
                    }`}>
                      {item.is_active !== false ? "Active" : "Inactive"}
                    </span>
                  </td>
                  <td className="px-4 py-3.5 text-right">
                    <div className="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transition">
                      {activeCat.updateFn && (
                        <button onClick={() => openEdit(item)} className="p-1.5 rounded-lg hover:bg-secondary text-muted-foreground hover:text-foreground transition">
                          <Edit3 className="h-4 w-4" />
                        </button>
                      )}
                      {activeCat.deleteFn && (
                        <button onClick={() => handleDeleteClick(item)} className="p-1.5 rounded-lg hover:bg-red-500/10 text-muted-foreground hover:text-red-500 transition">
                          <Trash2 className="h-4 w-4" />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Create / Edit Modal */}
      {showForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={() => setShowForm(false)}>
          <div className="w-full max-w-lg rounded-2xl border border-border bg-card p-6 shadow-2xl" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-lg font-bold text-foreground">{editItem ? "Edit" : "Create"} {activeCat.label.replace(/s$/, "")}</h2>
              <button onClick={() => setShowForm(false)} className="p-1.5 rounded-lg hover:bg-secondary text-muted-foreground"><X className="h-5 w-5" /></button>
            </div>
            <div className="space-y-4 max-h-[60vh] overflow-y-auto pr-1">
              {activeCat.fields.map((f) => (
                <div key={f.key}>
                  <label className="mb-1.5 block text-sm font-medium text-foreground">{f.label}{f.required && <span className="text-red-400 ml-1">*</span>}</label>
                  {f.type === "boolean" ? (
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={formData[f.key] ?? false}
                        onChange={(e) => setFormData({ ...formData, [f.key]: e.target.checked })}
                        className="h-4 w-4 rounded border-border text-primary"
                      />
                      <span className="text-sm text-muted-foreground">Enabled</span>
                    </label>
                  ) : f.type === "select" && f.optionsFn ? (
                    /* FK dropdown — options loaded from API */
                    <select
                      value={formData[f.key] ?? ""}
                      onChange={(e) => setFormData({ ...formData, [f.key]: e.target.value })}
                      className="h-10 w-full rounded-xl border border-border bg-secondary/30 px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40 appearance-none"
                      required={f.required}
                    >
                      <option value="">— Select {f.label} —</option>
                      {(fkOptions[f.key] ?? []).map((opt: any) => (
                        <option key={opt.id} value={opt.id}>
                          {opt[f.optionLabel ?? "name"] ?? opt.code ?? opt.id}
                        </option>
                      ))}
                    </select>
                  ) : f.type === "select" && f.lookupCategory ? (
                    /* Dynamic choice dropdown from GCLookupValue */
                    <select
                      value={formData[f.key] ?? ""}
                      onChange={(e) => setFormData({ ...formData, [f.key]: e.target.value })}
                      className="h-10 w-full rounded-xl border border-border bg-secondary/30 px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40 appearance-none"
                      required={f.required}
                    >
                      <option value="">— Select {f.label} —</option>
                      {(globalLookups[f.lookupCategory] || []).map((c: any) => (
                        <option key={c.value} value={c.value}>{c.label}</option>
                      ))}
                    </select>
                  ) : f.type === "select" && f.choices ? (
                    /* Static choice dropdown */
                    <select
                      value={formData[f.key] ?? ""}
                      onChange={(e) => setFormData({ ...formData, [f.key]: e.target.value })}
                      className="h-10 w-full rounded-xl border border-border bg-secondary/30 px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40 appearance-none"
                      required={f.required}
                    >
                      <option value="">— Select {f.label} —</option>
                      {f.choices.map((c) => (
                        <option key={c.value} value={c.value}>{c.label}</option>
                      ))}
                    </select>
                  ) : f.type === "textarea" ? (
                    <textarea
                      value={formData[f.key] ?? ""}
                      onChange={(e) => setFormData({ ...formData, [f.key]: e.target.value })}
                      rows={3}
                      className="w-full rounded-xl border border-border bg-secondary/30 px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40 resize-y"
                      required={f.required}
                    />
                  ) : (
                    <input
                      type={f.type === "number" ? "number" : f.type === "date" ? "date" : "text"}
                      value={formData[f.key] ?? ""}
                      onChange={(e) => setFormData({ ...formData, [f.key]: f.type === "number" ? Number(e.target.value) : e.target.value })}
                      className="h-10 w-full rounded-xl border border-border bg-secondary/30 px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
                      required={f.required}
                    />
                  )}
                </div>
              ))}
            </div>
            <div className="mt-6 flex items-center justify-end gap-3">
              <button onClick={() => setShowForm(false)} className="rounded-xl border border-border px-4 py-2 text-sm font-medium text-foreground hover:bg-secondary transition">Cancel</button>
              <button
                onClick={handleSave}
                disabled={saving}
                className="flex items-center gap-2 rounded-xl px-5 py-2 text-sm font-medium text-white shadow-lg transition hover:opacity-90 disabled:opacity-50"
                style={{ background: activeCat.gradient }}
              >
                {saving && <Loader2 className="h-4 w-4 animate-spin" />}
                {editItem ? "Save Changes" : "Create"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* DELETE CONFIRMATION MODAL */}
      {deleteItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={() => setDeleteItem(null)}>
          <div className="w-full max-w-sm rounded-2xl border border-border bg-card p-6 shadow-2xl" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center gap-4 mb-4 text-red-500">
              <div className="p-3 bg-red-500/10 rounded-full">
                <AlertCircle className="h-6 w-6" />
              </div>
              <h2 className="text-lg font-bold text-foreground">Confirm Delete</h2>
            </div>
            <p className="text-sm text-muted-foreground mb-6">
              Are you sure you want to delete this item? This action cannot be undone.
            </p>
            <div className="flex items-center justify-end gap-3 pt-4 border-t border-border">
              <button
                type="button"
                onClick={() => setDeleteItem(null)}
                className="px-4 py-2 text-sm font-medium text-foreground bg-secondary hover:bg-secondary/80 rounded-xl transition"
                disabled={saving}
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={confirmDelete}
                disabled={saving}
                className="px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded-xl transition flex items-center gap-2 disabled:opacity-50"
              >
                {saving && <Loader2 className="h-4 w-4 animate-spin" />}
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
