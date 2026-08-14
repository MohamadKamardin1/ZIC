import { useState, useEffect } from "react"
import {
  Settings, Package, Shield, Activity, Heart, FileText,
  Plus, Edit3, Trash2, ChevronRight, Search, X, Check, CheckCircle,
  Loader2, AlertCircle, CreditCard, UserCheck, Star, BookOpen,
  Stethoscope, Clipboard, Database, Award, ListChecks
} from "lucide-react"
import { gcSetup } from "../../lib/gc-api"

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
  // ── GC Scheme Setup ──────────────────────────────────────────────
  {
    key: "lookupValues", label: "Dropdown Configuration", group: "System Setup", icon: Database,
    color: "#64748b", gradient: "linear-gradient(135deg, #64748b, #94a3b8)",
    fetchFn: () => gcSetup.listLookupValues(), createFn: (d) => gcSetup.createLookupValue(d),
    updateFn: (id, d) => gcSetup.updateLookupValue(id, d), deleteFn: (id) => gcSetup.deleteLookupValue(id),
    fields: [
      { key: "category", label: "Category Key", required: true, type: "select", choices: [
        { value: "RATE_TYPE", label: "RATE_TYPE" },
        { value: "GENDER", label: "GENDER" },
        { value: "QUESTION_TYPE", label: "QUESTION_TYPE" },
        { value: "HEALTH_QUESTION_CATEGORY", label: "HEALTH_QUESTION_CATEGORY" },
        { value: "RIDER_TYPE", label: "RIDER_TYPE" },
        { value: "STATUS", label: "STATUS" },
        { value: "UW_STATUS", label: "UW_STATUS" },
        { value: "RELATIONSHIP", label: "RELATIONSHIP" },
        { value: "PERSONAL_HABIT_CATEGORY", label: "PERSONAL_HABIT_CATEGORY" },
        { value: "RISK_LEVEL", label: "RISK_LEVEL" },
        { value: "MEDICAL_HISTORY_CATEGORY", label: "MEDICAL_HISTORY_CATEGORY" },
        { value: "RISK_IMPACT", label: "RISK_IMPACT" },
        { value: "FACILITY_TYPE", label: "FACILITY_TYPE" },
      ] },
      { key: "value", label: "Stored Value", required: true },
      { key: "label", label: "Display Label", required: true },
      { key: "sort_order", label: "Sort Order", type: "number" },
    ],
  },
  {
    key: "schemeTypes", label: "GC Scheme Types", group: "GC Scheme Setup", icon: FileText,
    color: "#f59e0b", gradient: "linear-gradient(135deg, #f59e0b, #fbbf24)",
    fetchFn: gcSetup.listSchemeTypes, createFn: (d) => gcSetup.createSchemeType(d),
    updateFn: (id, d) => gcSetup.updateSchemeType(id, d), deleteFn: (id) => gcSetup.deleteSchemeType(id),
    fields: [
      { key: "code", label: "Code", required: true },
      { key: "name", label: "Name", required: true },
      { key: "description", label: "Description" },
    ],
  },
  {
    key: "premiumRates", label: "GC Scheme Premium Rates", group: "GC Scheme Setup", icon: CreditCard,
    color: "#8b5cf6", gradient: "linear-gradient(135deg, #8b5cf6, #a78bfa)",
    fetchFn: gcSetup.listPremiumRates, createFn: (d) => gcSetup.createPremiumRate(d),
    updateFn: (id, d) => gcSetup.updatePremiumRate(id, d), deleteFn: (id) => gcSetup.deletePremiumRate(id),
    fields: [
      { key: "name", label: "Name", required: true },
      { key: "rate_type", label: "Rate Type", required: true, type: "select", lookupCategory: "RATE_TYPE"},
      { key: "age_band_start", label: "Age From", type: "number" },
      { key: "age_band_end", label: "Age To", type: "number" },
      { key: "gender", label: "Gender", type: "select", lookupCategory: "GENDER"},
      { key: "rate_per_mille", label: "Rate ‰", type: "number" },
    ],
  },
  {
    key: "memberStatuses", label: "GC Scheme Member Status", group: "GC Scheme Setup", icon: UserCheck,
    color: "#06b6d4", gradient: "linear-gradient(135deg, #06b6d4, #22d3ee)",
    fetchFn: gcSetup.listMemberStatuses, createFn: (d) => gcSetup.createMemberStatus(d),
    updateFn: (id, d) => gcSetup.updateMemberStatus(id, d), deleteFn: (id) => gcSetup.deleteMemberStatus(id),
    fields: [
      { key: "code", label: "Code", required: true },
      { key: "name", label: "Name", required: true },
      { key: "description", label: "Description" },
    ],
  },
  {
    key: "schemeStatuses", label: "GC Scheme Status", group: "GC Scheme Setup", icon: Activity,
    color: "#ec4899", gradient: "linear-gradient(135deg, #ec4899, #f472b6)",
    fetchFn: gcSetup.listSchemeStatuses, createFn: (d) => gcSetup.createSchemeStatus(d),
    updateFn: (id, d) => gcSetup.updateSchemeStatus(id, d), deleteFn: (id) => gcSetup.deleteSchemeStatus(id),
    fields: [
      { key: "code", label: "Code", required: true },
      { key: "name", label: "Name", required: true },
      { key: "sort_order", label: "Sort Order", type: "number" },
      { key: "is_terminal", label: "Terminal", type: "boolean" },
    ],
  },
  {
    key: "renewalStatuses", label: "GC Scheme Renewal Status", group: "GC Scheme Setup", icon: Star,
    color: "#14b8a6", gradient: "linear-gradient(135deg, #14b8a6, #2dd4bf)",
    fetchFn: gcSetup.listRenewalStatuses, createFn: (d) => gcSetup.createRenewalStatus(d),
    updateFn: (id, d) => gcSetup.updateRenewalStatus(id, d), deleteFn: (id) => gcSetup.deleteRenewalStatus(id),
    fields: [
      { key: "code", label: "Code", required: true },
      { key: "name", label: "Name", required: true },
      { key: "description", label: "Description" },
    ],
  },
  {
    key: "healthQuestions", label: "Health Questions", group: "GC Scheme Setup", icon: BookOpen,
    color: "#6366f1", gradient: "linear-gradient(135deg, #6366f1, #818cf8)",
    fetchFn: gcSetup.listHealthQuestions, createFn: (d) => gcSetup.createHealthQuestion(d),
    updateFn: (id, d) => gcSetup.updateHealthQuestion(id, d), deleteFn: (id) => gcSetup.deleteHealthQuestion(id),
    fields: [
      { key: "code", label: "Code", required: true },
      { key: "question_text", label: "Question", required: true, type: "textarea" },
      { key: "question_type", label: "Type", type: "select", lookupCategory: "QUESTION_TYPE"},
      { key: "category", label: "Category", type: "select", lookupCategory: "HEALTH_QUESTION_CATEGORY"},
      { key: "is_required", label: "Required", type: "boolean" },
    ],
  },
  {
    key: "healthQuestionnaires", label: "Health Questionnaire", group: "GC Scheme Setup", icon: Clipboard,
    color: "#7c3aed", gradient: "linear-gradient(135deg, #7c3aed, #a78bfa)",
    fetchFn: gcSetup.listHealthQuestionnaires, createFn: (d) => gcSetup.createHealthQuestionnaire(d),
    updateFn: (id, d) => gcSetup.updateHealthQuestionnaire(id, d), deleteFn: (id) => gcSetup.deleteHealthQuestionnaire(id),
    fields: [
      { key: "code", label: "Code", required: true },
      { key: "name", label: "Name", required: true },
      { key: "version", label: "Version" },
      { key: "effective_date", label: "Effective Date", type: "date" },
    ],
  },

  // ── GC Product Setup ──────────────────────────────────────────────
  {
    key: "subProducts", label: "GC SubProducts", group: "GC Product Setup", icon: Database,
    color: "#0ea5e9", gradient: "linear-gradient(135deg, #0ea5e9, #38bdf8)",
    fetchFn: gcSetup.listSubProducts, createFn: (d) => gcSetup.createSubProduct(d),
    updateFn: (id, d) => gcSetup.updateSubProduct(id, d),
    fields: [
      { key: "code", label: "Code", required: true },
      { key: "name", label: "Name", required: true },
      { key: "description", label: "Description" },
    ],
  },
  {
    key: "products", label: "GC Products", group: "GC Product Setup", icon: Package,
    color: "#6366f1", gradient: "linear-gradient(135deg, #6366f1, #8b5cf6)",
    fetchFn: gcSetup.listProducts, createFn: (d) => gcSetup.createProduct(d),
    updateFn: (id, d) => gcSetup.updateProduct(id, d), deleteFn: (id) => gcSetup.deleteProduct(id),
    fields: [
      { key: "sub_product", label: "Sub Product", required: true, type: "select",
        optionsFn: () => gcSetup.listSubProducts(), optionLabel: "name", displayKey: "sub_product_name" },
      { key: "code", label: "Code", required: true },
      { key: "name", label: "Name", required: true },
      { key: "min_members", label: "Min Members", type: "number" },
      { key: "max_members", label: "Max Members", type: "number" },
      { key: "free_cover_limit", label: "FCL", type: "number" },
      { key: "currency", label: "Currency" },
    ],
  },

  // ── GC Rider Setup ────────────────────────────────────────────────
  {
    key: "riders", label: "GC Riders", group: "GC Rider Setup", icon: Shield,
    color: "#10b981", gradient: "linear-gradient(135deg, #10b981, #34d399)",
    fetchFn: gcSetup.listRiders, createFn: (d) => gcSetup.createRider(d),
    updateFn: (id, d) => gcSetup.updateRider(id, d), deleteFn: (id) => gcSetup.deleteRider(id),
    fields: [
      { key: "code", label: "Code", required: true },
      { key: "name", label: "Name", required: true },
      { key: "rider_type", label: "Type", type: "select", lookupCategory: "RIDER_TYPE"},
      { key: "is_mandatory", label: "Mandatory", type: "boolean" },
    ],
  },
  {
    key: "riderRates", label: "GC Rider Rates", group: "GC Rider Setup", icon: Award,
    color: "#059669", gradient: "linear-gradient(135deg, #059669, #34d399)",
    fetchFn: gcSetup.listRiderRates, createFn: (d) => gcSetup.createRiderRate(d),
    updateFn: (id, d) => gcSetup.updateRiderRate(id, d), deleteFn: (id) => gcSetup.deleteRiderRate(id),
    fields: [
      { key: "rider", label: "Rider", required: true, type: "select",
        optionsFn: () => gcSetup.listRiders(), optionLabel: "name", displayKey: "rider_name" },
      { key: "age_band_start", label: "Age From", type: "number" },
      { key: "age_band_end", label: "Age To", type: "number" },
      { key: "gender", label: "Gender", type: "select", lookupCategory: "GENDER"},
      { key: "rate_per_mille", label: "Rate ‰", type: "number" },
      { key: "flat_amount", label: "Flat Amount", type: "number" },
    ],
  },

  // ── GC Medical U/w ────────────────────────────────────────────────
  {
    key: "medicalCodes", label: "GC Medical Codes", group: "GC Medical U/w", icon: Stethoscope,
    color: "#ef4444", gradient: "linear-gradient(135deg, #ef4444, #f87171)",
    fetchFn: gcSetup.listMedicalCodes, createFn: (d) => gcSetup.createMedicalCode(d),
    fields: [
      { key: "code", label: "Code", required: true },
      { key: "name", label: "Name", required: true },
      { key: "icd10_code", label: "ICD-10" },
      { key: "category", label: "Category" },
    ],
  },
  {
    key: "medicalLimits", label: "GC Medical Limits", group: "GC Medical U/w", icon: ListChecks,
    color: "#dc2626", gradient: "linear-gradient(135deg, #dc2626, #ef4444)",
    fetchFn: gcSetup.listMedicalLimits, createFn: (d) => gcSetup.createMedicalLimit(d),
    updateFn: (id, d) => gcSetup.updateMedicalLimit(id, d), deleteFn: (id) => gcSetup.deleteMedicalLimit(id),
    fields: [
      { key: "product", label: "Product", required: true, type: "select",
        optionsFn: () => gcSetup.listProducts(), optionLabel: "name", displayKey: "product_name" },
      { key: "age_from", label: "Age From", type: "number" },
      { key: "age_to", label: "Age To", type: "number" },
      { key: "sum_assured_from", label: "SA From", type: "number" },
      { key: "sum_assured_to", label: "SA To", type: "number" },
      { key: "required_tests", label: "Required Tests" },
    ],
  },
  {
    key: "uwDecisions", label: "GC Underwriting Decision", group: "GC Medical U/w", icon: CheckCircle,
    color: "#f97316", gradient: "linear-gradient(135deg, #f97316, #fb923c)",
    fetchFn: gcSetup.listUWDecisions, createFn: (d) => gcSetup.createUWDecision(d),
    updateFn: (id, d) => gcSetup.updateUWDecision(id, d), deleteFn: (id) => gcSetup.deleteUWDecision(id),
    fields: [
      { key: "code", label: "Code", required: true },
      { key: "name", label: "Name", required: true },
      { key: "sort_order", label: "Sort Order", type: "number" },
    ],
  },
  {
    key: "personalHabits", label: "GC Personal Habits", group: "GC Medical U/w", icon: Heart,
    color: "#e11d48", gradient: "linear-gradient(135deg, #e11d48, #fb7185)",
    fetchFn: gcSetup.listPersonalHabits, createFn: (d) => gcSetup.createPersonalHabit(d),
    updateFn: (id, d) => gcSetup.updatePersonalHabit(id, d), deleteFn: (id) => gcSetup.deletePersonalHabit(id),
    fields: [
      { key: "code", label: "Code", required: true },
      { key: "name", label: "Name", required: true },
      { key: "category", label: "Category", type: "select", lookupCategory: "PERSONAL_HABIT_CATEGORY"},
      { key: "risk_level", label: "Risk Level", type: "select", lookupCategory: "RISK_LEVEL"},
    ],
  },
  {
    key: "medicalHistory", label: "GC Medical History", group: "GC Medical U/w", icon: FileText,
    color: "#9333ea", gradient: "linear-gradient(135deg, #9333ea, #a855f7)",
    fetchFn: gcSetup.listMedicalHistory, createFn: (d) => gcSetup.createMedicalHistory(d),
    updateFn: (id, d) => gcSetup.updateMedicalHistory(id, d), deleteFn: (id) => gcSetup.deleteMedicalHistory(id),
    fields: [
      { key: "code", label: "Code", required: true },
      { key: "name", label: "Name", required: true },
      { key: "category", label: "Category", type: "select", lookupCategory: "MEDICAL_HISTORY_CATEGORY"},
      { key: "risk_impact", label: "Risk Impact", type: "select", lookupCategory: "RISK_IMPACT"},
    ],
  },
  {
    key: "medicalFacilities", label: "GC Medical Facilities", group: "GC Medical U/w", icon: Heart,
    color: "#06b6d4", gradient: "linear-gradient(135deg, #06b6d4, #22d3ee)",
    fetchFn: gcSetup.listMedicalFacilities, createFn: (d) => gcSetup.createMedicalFacility(d),
    updateFn: (id, d) => gcSetup.updateMedicalFacility(id, d),
    fields: [
      { key: "code", label: "Code", required: true },
      { key: "name", label: "Name", required: true },
      { key: "facility_type", label: "Type", type: "select", lookupCategory: "FACILITY_TYPE"},
      { key: "city", label: "City" },
      { key: "region", label: "Region" },
      { key: "phone", label: "Phone" },
    ],
  },
  {
    key: "medicalPractitioners", label: "GC Medical Practitioners", group: "GC Medical U/w", icon: Stethoscope,
    color: "#0891b2", gradient: "linear-gradient(135deg, #0891b2, #06b6d4)",
    fetchFn: gcSetup.listMedicalPractitioners, createFn: (d) => gcSetup.createMedicalPractitioner(d),
    updateFn: (id, d) => gcSetup.updateMedicalPractitioner(id, d), deleteFn: (id) => gcSetup.deleteMedicalPractitioner(id),
    fields: [
      { key: "facility", label: "Facility", required: true, type: "select",
        optionsFn: () => gcSetup.listMedicalFacilities(), optionLabel: "name", displayKey: "facility_name" },
      { key: "code", label: "Code", required: true },
      { key: "name", label: "Name", required: true },
      { key: "specialization", label: "Specialization" },
      { key: "license_number", label: "License #" },
    ],
  },

  // ── GC Claim Setup ────────────────────────────────────────────────
  {
    key: "claimTypes", label: "GC Claim Types", group: "GC Claim Setup", icon: AlertCircle,
    color: "#ef4444", gradient: "linear-gradient(135deg, #ef4444, #f87171)",
    fetchFn: gcSetup.listClaimTypes, createFn: (d) => gcSetup.createClaimType(d),
    updateFn: (id, d) => gcSetup.updateClaimType(id, d),
    fields: [
      { key: "code", label: "Code", required: true },
      { key: "name", label: "Name", required: true },
      { key: "requires_medical_report", label: "Req. Medical", type: "boolean" },
    ],
  },
  {
    key: "claimReasons", label: "GC Claim Reasons", group: "GC Claim Setup", icon: FileText,
    color: "#d946ef", gradient: "linear-gradient(135deg, #d946ef, #e879f9)",
    fetchFn: gcSetup.listClaimReasons, createFn: (d) => gcSetup.createClaimReason(d),
    updateFn: (id, d) => gcSetup.updateClaimReason(id, d), deleteFn: (id) => gcSetup.deleteClaimReason(id),
    fields: [
      { key: "claim_type", label: "Claim Type", required: true, type: "select",
        optionsFn: () => gcSetup.listClaimTypes(), optionLabel: "name", displayKey: "claim_type_name" },
      { key: "code", label: "Code", required: true },
      { key: "name", label: "Name", required: true },
      { key: "description", label: "Description" },
    ],
  },
  {
    key: "claimStatuses", label: "GC Claim Statuses", group: "GC Claim Setup", icon: Activity,
    color: "#f43f5e", gradient: "linear-gradient(135deg, #f43f5e, #fb7185)",
    fetchFn: gcSetup.listClaimStatuses, createFn: (d) => gcSetup.createClaimStatus(d),
    updateFn: (id, d) => gcSetup.updateClaimStatus(id, d),
    fields: [
      { key: "code", label: "Code", required: true },
      { key: "name", label: "Name", required: true },
      { key: "sort_order", label: "Sort Order", type: "number" },
      { key: "is_terminal", label: "Terminal", type: "boolean" },
    ],
  },
  {
    key: "dischargeTypes", label: "GC Discharge Types", group: "GC Claim Setup", icon: Settings,
    color: "#a855f7", gradient: "linear-gradient(135deg, #a855f7, #c084fc)",
    fetchFn: gcSetup.listDischargeTypes, createFn: (d) => gcSetup.createDischargeType(d),
    updateFn: (id, d) => gcSetup.updateDischargeType(id, d), deleteFn: (id) => gcSetup.deleteDischargeType(id),
    fields: [
      { key: "code", label: "Code", required: true },
      { key: "name", label: "Name", required: true },
      { key: "description", label: "Description" },
    ],
  },
  {
    key: "correspondentTypes", label: "GC Correspondent Types", group: "GC Claim Setup", icon: Settings,
    color: "#78716c", gradient: "linear-gradient(135deg, #78716c, #a8a29e)",
    fetchFn: gcSetup.listCorrespondentTypes, createFn: (d) => gcSetup.createCorrespondentType(d),
    updateFn: (id, d) => gcSetup.updateCorrespondentType(id, d), deleteFn: (id) => gcSetup.deleteCorrespondentType(id),
    fields: [
      { key: "code", label: "Code", required: true },
      { key: "name", label: "Name", required: true },
      { key: "description", label: "Description" },
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
    gcSetup.listLookupValues().then((res) => {
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
            Group Credit Parameters
          </h1>
          <p className="text-muted-foreground mt-1">Configure all parameters, products, and lookup tables for Group Credit insurance.</p>
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
