import { useEffect, useState, useCallback } from "react"
import { Plus, Pencil, Trash2, Check, X, Loader2, Settings } from "lucide-react"
import { useNavigate } from "react-router-dom"
import { PageHeader } from "./SharedComponents"
import {
  fetchPartnerTypes,
  createPartnerTypeRecord,
  updatePartnerTypeRecord,
  deletePartnerTypeRecord,
  fetchBranches,
  fetchLocations,
} from "../../lib/api"
import { SkeletonTable } from "../../components/shared/Skeleton"
import { useDataRefresh, emitDataChange } from "../../lib/useDataRefresh"
import type { PartnerTypeRecord, BranchRecord, LocationRecord } from "../../lib/types"

interface PartnerTypeForm {
  code: string
  name: string
  description: string
  branchId: string
  locationId: string
  isActive: boolean
}

const EMPTY_FORM: PartnerTypeForm = {
  code: "", name: "", description: "", branchId: "", locationId: "", isActive: true,
}

export default function PartnerTypeList() {
  const navigate = useNavigate()
  const [items, setItems] = useState<PartnerTypeRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [form, setForm] = useState<PartnerTypeForm>(EMPTY_FORM)
  const [adding, setAdding] = useState(false)
  const [saving, setSaving] = useState(false)
  const [branches, setBranches] = useState<BranchRecord[]>([])
  const [locations, setLocations] = useState<LocationRecord[]>([])
  const [locationsLoading, setLocationsLoading] = useState(false)
  const refreshKey = useDataRefresh("partner-types")

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [types, branchData] = await Promise.all([
        fetchPartnerTypes(),
        fetchBranches(),
      ])
      setItems(types)
      setBranches(branchData)
    } finally {
      setLoading(false)
    }
  }, [refreshKey])

  useEffect(() => { load() }, [load])

  const loadLocations = useCallback(async (branchId: string) => {
    if (!branchId) { setLocations([]); return }
    setLocationsLoading(true)
    try {
      setLocations(await fetchLocations(branchId))
    } finally {
      setLocationsLoading(false)
    }
  }, [])

  const handleBranchChange = (branchId: string) => {
    setForm((prev) => ({ ...prev, branchId, locationId: "" }))
    loadLocations(branchId)
  }

  async function handleSave(id?: string) {
    setSaving(true)
    try {
      const payload: Record<string, unknown> = {
        code: form.code,
        name: form.name,
        description: form.description,
        isActive: form.isActive,
      }
      if (form.branchId) payload.branchId = form.branchId
      if (form.locationId) payload.locationId = form.locationId

      if (id) {
        await updatePartnerTypeRecord(id, payload)
        setEditingId(null)
        setAdding(false)
        setForm(EMPTY_FORM)
        setLocations([])
        emitDataChange("partner-types")
        await load()
      } else {
        const created = await createPartnerTypeRecord(payload)
        console.log("[PartnerTypeList] created:", created)
        setEditingId(null)
        setAdding(false)
        setForm(EMPTY_FORM)
        setLocations([])
        emitDataChange("partner-types")
        await load()
        if (created?.id) {
          navigate(`/system-parameters/partner/partner-types/${created.id}/setup`)
        } else {
          console.error("[PartnerTypeList] created has no id:", created)
        }
      }
    } catch (e) {
      console.error("[PartnerTypeList] handleSave error:", e)
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete(id: string) {
    if (!window.confirm("Delete this partner type?")) return
    await deletePartnerTypeRecord(id)
    emitDataChange("partner-types")
    await load()
  }

  function startEdit(item: PartnerTypeRecord) {
    setEditingId(item.id)
    setForm({
      code: item.code,
      name: item.name,
      description: item.description,
      branchId: item.branchId ?? "",
      locationId: item.locationId ?? "",
      isActive: item.isActive,
    })
    setAdding(false)
    if (item.branchId) loadLocations(item.branchId)
  }

  function startAdd() {
    setAdding(true)
    setEditingId(null)
    setForm(EMPTY_FORM)
    setLocations([])
  }

  function cancel() {
    setEditingId(null)
    setAdding(false)
    setLocations([])
  }

  if (loading) {
    return <SkeletonTable rows={5} cols={7} />
  }

  return (
    <div>
      <PageHeader title="Partner Types" description="Manage partner type definitions (Client, Broker, Intermediary, Service Provider, Medical Practitioner)">
        <button onClick={startAdd} className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition">
          <Plus className="h-4 w-4" />
          Add Type
        </button>
      </PageHeader>

      {adding && (
        <div className="mb-4 rounded-lg border border-border bg-card p-4">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <div>
              <label className="mb-1 block text-xs font-medium text-muted-foreground">Code *</label>
              <input className="w-full rounded border border-input bg-background px-2 py-1.5 text-sm font-mono" value={form.code} onChange={e => setForm({ ...form, code: e.target.value.toUpperCase() })} placeholder="CLIENT" />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-muted-foreground">Name *</label>
              <input className="w-full rounded border border-input bg-background px-2 py-1.5 text-sm" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} placeholder="Client" />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-muted-foreground">Branch</label>
              <select className="w-full rounded border border-input bg-background px-2 py-1.5 text-sm" value={form.branchId} onChange={e => handleBranchChange(e.target.value)}>
                <option value="">-- Select Branch --</option>
                {branches.map(b => <option key={b.id} value={b.id}>{b.code} — {b.name}</option>)}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-muted-foreground">Location</label>
              {locationsLoading ? (
                <div className="flex h-9 items-center gap-2 text-xs text-muted-foreground">
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  Loading...
                </div>
              ) : (
                <select className="w-full rounded border border-input bg-background px-2 py-1.5 text-sm" value={form.locationId} onChange={e => setForm({ ...form, locationId: e.target.value })} disabled={!form.branchId}>
                  <option value="">-- Select Location --</option>
                  {locations.map(l => <option key={l.id} value={l.id}>{l.code} — {l.name}</option>)}
                </select>
              )}
            </div>
          </div>
          <div className="mt-3 flex items-center justify-between">
            <label className="flex items-center gap-1.5 text-sm">
              <input type="checkbox" checked={form.isActive} onChange={e => setForm({ ...form, isActive: e.target.checked })} />
              Active
            </label>
            <div className="flex gap-2">
              <button onClick={cancel} className="rounded-lg border border-border px-3 py-1.5 text-xs font-medium hover:bg-secondary">Cancel</button>
              <button onClick={() => handleSave()} disabled={saving || !form.code || !form.name} className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50">
                {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Plus className="h-3.5 w-3.5" />}
                Save
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="overflow-hidden rounded-lg border border-border">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-muted/50">
              <th className="px-4 py-2.5 text-left text-xs font-medium text-muted-foreground">Code</th>
              <th className="px-4 py-2.5 text-left text-xs font-medium text-muted-foreground">Name</th>
              <th className="px-4 py-2.5 text-left text-xs font-medium text-muted-foreground">Branch</th>
              <th className="px-4 py-2.5 text-left text-xs font-medium text-muted-foreground">Location</th>
              <th className="px-4 py-2.5 text-left text-xs font-medium text-muted-foreground">Active</th>
              <th className="w-20 px-4 py-2.5 text-right text-xs font-medium text-muted-foreground">Actions</th>
            </tr>
          </thead>
          <tbody>
            {items.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-sm text-muted-foreground">
                  No partner types defined.
                </td>
              </tr>
            )}
            {items.map(item =>
              editingId === item.id ? (
                <tr key={item.id} className="border-b border-border/50">
                  <td className="px-4 py-2"><input className="w-24 rounded border border-input bg-background px-2 py-1 font-mono text-xs" value={form.code} onChange={e => setForm({ ...form, code: e.target.value })} /></td>
                  <td className="px-4 py-2"><input className="w-36 rounded border border-input bg-background px-2 py-1 text-sm" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} /></td>
                  <td className="px-4 py-2">
                    <select className="w-36 rounded border border-input bg-background px-2 py-1 text-xs" value={form.branchId} onChange={e => handleBranchChange(e.target.value)}>
                      <option value="">None</option>
                      {branches.map(b => <option key={b.id} value={b.id}>{b.code}</option>)}
                    </select>
                  </td>
                  <td className="px-4 py-2">
                    {locationsLoading ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin text-muted-foreground" />
                    ) : (
                      <select className="w-36 rounded border border-input bg-background px-2 py-1 text-xs" value={form.locationId} onChange={e => setForm({ ...form, locationId: e.target.value })} disabled={!form.branchId}>
                        <option value="">None</option>
                        {locations.map(l => <option key={l.id} value={l.id}>{l.code}</option>)}
                      </select>
                    )}
                  </td>
                  <td className="px-4 py-2"><input type="checkbox" checked={form.isActive} onChange={e => setForm({ ...form, isActive: e.target.checked })} /></td>
                  <td className="px-4 py-2 text-right">
                    <button onClick={() => handleSave(item.id)} disabled={saving} className="mr-1 rounded p-1 text-success hover:bg-success/10"><Check className="h-4 w-4" /></button>
                    <button onClick={cancel} className="rounded p-1 text-muted-foreground hover:bg-secondary"><X className="h-4 w-4" /></button>
                  </td>
                </tr>
              ) : (
                <tr key={item.id} className="border-b border-border/50 hover:bg-muted/30">
                  <td className="px-4 py-2 font-mono text-xs text-muted-foreground">{item.code}</td>
                  <td className="px-4 py-2 font-medium">{item.name}</td>
                  <td className="px-4 py-2 text-xs text-muted-foreground">{item.branchName || "—"}</td>
                  <td className="px-4 py-2 text-xs text-muted-foreground">{item.locationName || "—"}</td>
                  <td className="px-4 py-2">{item.isActive ? <span className="text-success">Yes</span> : <span className="text-muted-foreground">No</span>}</td>
                  <td className="px-4 py-2 text-right">
                    <button onClick={() => navigate(`/system-parameters/partner/partner-types/${item.id}/setup`)} className="mr-1 rounded p-1 text-primary hover:bg-accent" title="Setup"><Settings className="h-4 w-4" /></button>
                    <button onClick={() => startEdit(item)} className="mr-1 rounded p-1 text-muted-foreground hover:bg-secondary"><Pencil className="h-4 w-4" /></button>
                    <button onClick={() => handleDelete(item.id)} className="rounded p-1 text-destructive hover:bg-destructive/10"><Trash2 className="h-4 w-4" /></button>
                  </td>
                </tr>
              )
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
