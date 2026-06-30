import { useState, useEffect } from "react"
import {
  Settings, Package, Shield, Activity, Heart, FileText,
  Plus, Edit3, Trash2, ChevronRight, Search, X, Check,
  Loader2, AlertCircle
} from "lucide-react"
import { glSetup } from "../../lib/gl-api"

interface SetupCategory {
  key: string
  label: string
  icon: typeof Settings
  color: string
  gradient: string
  fetchFn: (params?: Record<string, string>) => Promise<any>
  createFn?: (data: Record<string, unknown>) => Promise<any>
  updateFn?: (id: string, data: Record<string, unknown>) => Promise<any>
  deleteFn?: (id: string) => Promise<void>
  fields: { key: string; label: string; type?: string; required?: boolean }[]
}

const SETUP_CATEGORIES: SetupCategory[] = [
  {
    key: "products", label: "Products", icon: Package,
    color: "var(--color-primary)", gradient: "linear-gradient(135deg, #6366f1, #8b5cf6)",
    fetchFn: glSetup.listProducts, createFn: (d) => glSetup.createProduct(d),
    updateFn: (id, d) => glSetup.updateProduct(id, d), deleteFn: (id) => glSetup.deleteProduct(id),
    fields: [
      { key: "code", label: "Code", required: true },
      { key: "name", label: "Name", required: true },
      { key: "minMembers", label: "Min Members", type: "number" },
      { key: "maxMembers", label: "Max Members", type: "number" },
      { key: "freeCoverLimit", label: "FCL", type: "number" },
      { key: "currency", label: "Currency" },
    ],
  },
  {
    key: "riders", label: "Riders", icon: Shield,
    color: "#10b981", gradient: "linear-gradient(135deg, #10b981, #34d399)",
    fetchFn: glSetup.listRiders, createFn: (d) => glSetup.createRider(d),
    updateFn: (id, d) => glSetup.updateRider(id, d),
    fields: [
      { key: "code", label: "Code", required: true },
      { key: "name", label: "Name", required: true },
      { key: "riderType", label: "Type" },
      { key: "isMandatory", label: "Mandatory", type: "boolean" },
    ],
  },
  {
    key: "schemeTypes", label: "Scheme Types", icon: FileText,
    color: "#f59e0b", gradient: "linear-gradient(135deg, #f59e0b, #fbbf24)",
    fetchFn: glSetup.listSchemeTypes, createFn: (d) => glSetup.createSchemeType(d),
    updateFn: (id, d) => glSetup.updateSchemeType(id, d), deleteFn: (id) => glSetup.deleteSchemeType(id),
    fields: [
      { key: "code", label: "Code", required: true },
      { key: "name", label: "Name", required: true },
      { key: "description", label: "Description" },
    ],
  },
  {
    key: "schemeStatuses", label: "Scheme Statuses", icon: Activity,
    color: "#ec4899", gradient: "linear-gradient(135deg, #ec4899, #f472b6)",
    fetchFn: glSetup.listSchemeStatuses, createFn: (d) => glSetup.createSchemeStatus(d),
    updateFn: (id, d) => glSetup.updateSchemeStatus(id, d), deleteFn: (id) => glSetup.deleteSchemeStatus(id),
    fields: [
      { key: "code", label: "Code", required: true },
      { key: "name", label: "Name", required: true },
      { key: "sortOrder", label: "Sort Order", type: "number" },
      { key: "isTerminal", label: "Terminal", type: "boolean" },
    ],
  },
  {
    key: "claimTypes", label: "Claim Types", icon: AlertCircle,
    color: "#ef4444", gradient: "linear-gradient(135deg, #ef4444, #f87171)",
    fetchFn: glSetup.listClaimTypes, createFn: (d) => glSetup.createClaimType(d),
    updateFn: (id, d) => glSetup.updateClaimType(id, d),
    fields: [
      { key: "code", label: "Code", required: true },
      { key: "name", label: "Name", required: true },
      { key: "requiresMedicalReport", label: "Req. Medical", type: "boolean" },
    ],
  },
  {
    key: "medicalFacilities", label: "Medical Facilities", icon: Heart,
    color: "#06b6d4", gradient: "linear-gradient(135deg, #06b6d4, #22d3ee)",
    fetchFn: glSetup.listMedicalFacilities, createFn: (d) => glSetup.createMedicalFacility(d),
    updateFn: (id, d) => glSetup.updateMedicalFacility(id, d),
    fields: [
      { key: "code", label: "Code", required: true },
      { key: "name", label: "Name", required: true },
      { key: "facilityType", label: "Type" },
      { key: "city", label: "City" },
      { key: "region", label: "Region" },
      { key: "phone", label: "Phone" },
    ],
  },
]

export default function GLSetup() {
  const [activeCat, setActiveCat] = useState<SetupCategory | null>(null)
  const [items, setItems] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState("")
  const [showForm, setShowForm] = useState(false)
  const [editItem, setEditItem] = useState<any>(null)
  const [formData, setFormData] = useState<Record<string, any>>({})
  const [saving, setSaving] = useState(false)
  const [counts, setCounts] = useState<Record<string, number>>({})

  useEffect(() => {
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

  function openCreate() {
    setEditItem(null)
    setFormData({})
    setShowForm(true)
  }

  function openEdit(item: any) {
    setEditItem(item)
    setFormData({ ...item })
    setShowForm(true)
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

  async function handleDelete(id: string) {
    if (!activeCat?.deleteFn) return
    if (!confirm("Are you sure you want to delete this item?")) return
    try {
      await activeCat.deleteFn(id)
      await loadCategory(activeCat)
    } catch (err: any) {
      alert(err.message)
    }
  }

  const filtered = items.filter((item) => {
    if (!search) return true
    const s = search.toLowerCase()
    return (
      item.name?.toLowerCase().includes(s) ||
      item.code?.toLowerCase().includes(s) ||
      item.description?.toLowerCase().includes(s)
    )
  })

  // Category grid view
  if (!activeCat) {
    return (
      <div className="p-6 max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-3">
            <div className="p-2 rounded-xl" style={{ background: "linear-gradient(135deg, #6366f1, #8b5cf6)" }}>
              <Settings className="h-6 w-6 text-white" />
            </div>
            Group Life Setup
          </h1>
          <p className="text-muted-foreground mt-1">Configure parameters, products, and lookup tables for Group Life insurance.</p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {SETUP_CATEGORIES.map((cat) => {
            const Icon = cat.icon
            return (
              <button
                key={cat.key}
                onClick={() => loadCategory(cat)}
                className="group relative overflow-hidden rounded-2xl border border-border bg-card p-6 text-left transition-all duration-300 hover:shadow-xl hover:shadow-primary/5 hover:-translate-y-1 hover:border-primary/30"
              >
                <div className="absolute inset-0 opacity-0 transition-opacity group-hover:opacity-5" style={{ background: cat.gradient }} />
                <div className="flex items-start justify-between">
                  <div className="rounded-xl p-3 shadow-lg" style={{ background: cat.gradient }}>
                    <Icon className="h-6 w-6 text-white" />
                  </div>
                  <ChevronRight className="h-5 w-5 text-muted-foreground transition-transform group-hover:translate-x-1" />
                </div>
                <h3 className="mt-4 text-lg font-semibold text-foreground">{cat.label}</h3>
                <p className="mt-1 text-sm text-muted-foreground">
                  {counts[cat.key] !== undefined ? `${counts[cat.key]} items configured` : "Loading..."}
                </p>
              </button>
            )
          })}
        </div>
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
            <p className="text-sm text-muted-foreground">{filtered.length} items</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
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
                  {activeCat.fields.slice(0, 5).map((f) => (
                    <td key={f.key} className="px-4 py-3.5 text-sm text-foreground">
                      {f.type === "boolean" ? (
                        item[f.key] ? <Check className="h-4 w-4 text-emerald-500" /> : <X className="h-4 w-4 text-muted-foreground/40" />
                      ) : (
                        String(item[f.key] ?? "—")
                      )}
                    </td>
                  ))}
                  <td className="px-4 py-3.5">
                    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
                      item.isActive !== false
                        ? "bg-emerald-500/10 text-emerald-500"
                        : "bg-red-500/10 text-red-500"
                    }`}>
                      {item.isActive !== false ? "Active" : "Inactive"}
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
                        <button onClick={() => handleDelete(item.id)} className="p-1.5 rounded-lg hover:bg-red-500/10 text-muted-foreground hover:text-red-500 transition">
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
            <div className="space-y-4">
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
                  ) : (
                    <input
                      type={f.type === "number" ? "number" : "text"}
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
    </div>
  )
}
