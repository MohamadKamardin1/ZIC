import { useEffect, useState, useCallback, useMemo } from "react"
import { Plus, Pencil, Trash2, Check, X, Loader2 } from "lucide-react"
import { PageHeader } from "./SharedComponents"
import { fetchLocations, createLocationRecord, updateLocationRecord, deleteLocationRecord, fetchBranches } from "../../lib/api"
import { SkeletonTable } from "../../components/shared/Skeleton"
import { emitDataChange, useDataRefresh } from "../../lib/useDataRefresh"
import type { LocationRecord, BranchRecord } from "../../lib/types"

export default function Locations() {
  const [items, setItems] = useState<LocationRecord[]>([])
  const [branches, setBranches] = useState<BranchRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [form, setForm] = useState({ code: "", name: "", branchId: "", isActive: true })
  const [adding, setAdding] = useState(false)
  const [saving, setSaving] = useState(false)
  const [branchFilter, setBranchFilter] = useState("")
  const refreshKey = useDataRefresh("locations")

  const filtered = useMemo(
    () => (branchFilter ? items.filter((l) => l.branchId === branchFilter) : items),
    [items, branchFilter],
  )

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [locData, branchData] = await Promise.all([fetchLocations(), fetchBranches()])
      setItems(locData)
      setBranches(branchData)
    } finally {
      setLoading(false)
    }
  }, [refreshKey])

  useEffect(() => { load() }, [load])

  async function handleSave(id?: string) {
    setSaving(true)
    try {
      const payload = { ...form, branchId: form.branchId || undefined }
      if (id) {
        await updateLocationRecord(id, payload)
      } else {
        await createLocationRecord(payload)
      }
      setEditingId(null)
      setAdding(false)
      setForm({ code: "", name: "", branchId: branchFilter || branches[0]?.id || "", isActive: true })
      emitDataChange("locations")
      await load()
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete(id: string) {
    if (!window.confirm("Delete this location?")) return
    await deleteLocationRecord(id)
    emitDataChange("locations")
    await load()
  }

  function startEdit(item: LocationRecord) {
    setEditingId(item.id)
    setForm({ code: item.code, name: item.name, branchId: item.branchId, isActive: item.isActive })
    setAdding(false)
  }

  function startAdd() {
    setAdding(true)
    setEditingId(null)
    setForm({ code: "", name: "", branchId: branchFilter || branches[0]?.id || "", isActive: true })
  }

  function cancel() {
    setEditingId(null)
    setAdding(false)
  }

  const branchMap = Object.fromEntries(branches.map(b => [b.id, b.name]))

  if (loading) {
    return <SkeletonTable rows={5} cols={5} />
  }

  return (
    <div>
      <PageHeader title="Locations" description="Manage branch locations">
        <button onClick={startAdd} className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition">
          <Plus className="h-4 w-4" />
          Add Location
        </button>
      </PageHeader>

      {adding && (
        <div className="mb-4 rounded-lg border border-border bg-card p-4">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <div>
              <label className="mb-1 block text-xs font-medium text-muted-foreground">Branch *</label>
              <select
                className="w-full rounded border border-input bg-background px-2 py-1.5 text-sm"
                value={form.branchId}
                onChange={e => setForm({ ...form, branchId: e.target.value })}
              >
                <option value="">-- Select Branch --</option>
                {branches.map(b => <option key={b.id} value={b.id}>{b.code} — {b.name}</option>)}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-muted-foreground">Code *</label>
              <input className="w-full rounded border border-input bg-background px-2 py-1.5 text-sm font-mono" value={form.code} onChange={e => setForm({ ...form, code: e.target.value })} placeholder="LOC-001" />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-muted-foreground">Name *</label>
              <input className="w-full rounded border border-input bg-background px-2 py-1.5 text-sm" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} placeholder="Main Office" />
            </div>
            <div className="flex items-end gap-4">
              <label className="flex items-center gap-1.5 text-sm pb-1.5">
                <input type="checkbox" checked={form.isActive} onChange={e => setForm({ ...form, isActive: e.target.checked })} />
                Active
              </label>
            </div>
          </div>
          <div className="mt-3 flex justify-end gap-2">
            <button onClick={cancel} className="rounded-lg border border-border px-3 py-1.5 text-xs font-medium hover:bg-secondary">Cancel</button>
            <button
              onClick={() => handleSave()}
              disabled={saving || !form.code || !form.name || !form.branchId}
              className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Plus className="h-3.5 w-3.5" />}
              Save
            </button>
          </div>
        </div>
      )}

      {/* Branch filter */}
      {!adding && branches.length > 0 && (
        <div className="mb-3 flex items-center gap-3">
          <label className="text-xs font-medium text-muted-foreground">Filter by branch:</label>
          <select
            className="rounded-lg border border-input bg-card px-2.5 py-1.5 text-sm outline-none focus:ring-2 focus:ring-ring/40"
            value={branchFilter}
            onChange={e => setBranchFilter(e.target.value)}
          >
            <option value="">All Branches</option>
            {branches.map(b => <option key={b.id} value={b.id}>{b.code} — {b.name}</option>)}
          </select>
          <span className="text-xs text-muted-foreground">
            {filtered.length} of {items.length} locations
          </span>
          {branchFilter && (
            <button onClick={() => setBranchFilter("")} className="text-xs text-primary hover:underline">Clear</button>
          )}
        </div>
      )}

      <div className="overflow-hidden rounded-lg border border-border">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-muted/50 text-left">
              <th className="px-4 py-2.5 text-xs font-medium text-muted-foreground">Branch</th>
              <th className="px-4 py-2.5 text-xs font-medium text-muted-foreground">Code</th>
              <th className="px-4 py-2.5 text-xs font-medium text-muted-foreground">Name</th>
              <th className="px-4 py-2.5 text-xs font-medium text-muted-foreground">Active</th>
              <th className="w-20 px-4 py-2.5 text-right text-xs font-medium text-muted-foreground">Actions</th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-sm text-muted-foreground">
                  {branchFilter ? "No locations for this branch." : "No locations defined."}
                </td>
              </tr>
            )}
            {filtered.map(item =>
              editingId === item.id ? (
                <tr key={item.id} className="border-b border-border/50">
                  <td className="px-4 py-2">
                    <select className="rounded border border-input bg-background px-2 py-1 text-sm" value={form.branchId} onChange={e => setForm({ ...form, branchId: e.target.value })}>
                      {branches.map(b => <option key={b.id} value={b.id}>{b.code}</option>)}
                    </select>
                  </td>
                  <td className="px-4 py-2"><input className="w-24 rounded border border-input bg-background px-2 py-1 font-mono text-xs" value={form.code} onChange={e => setForm({ ...form, code: e.target.value })} /></td>
                  <td className="px-4 py-2"><input className="w-40 rounded border border-input bg-background px-2 py-1 text-sm" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} /></td>
                  <td className="px-4 py-2"><input type="checkbox" checked={form.isActive} onChange={e => setForm({ ...form, isActive: e.target.checked })} /></td>
                  <td className="px-4 py-2 text-right">
                    <button onClick={() => handleSave(item.id)} disabled={saving} className="mr-1 rounded p-1 text-success hover:bg-success/10"><Check className="h-4 w-4" /></button>
                    <button onClick={cancel} className="rounded p-1 text-muted-foreground hover:bg-secondary"><X className="h-4 w-4" /></button>
                  </td>
                </tr>
              ) : (
                <tr key={item.id} className="border-b border-border/50 hover:bg-muted/30">
                  <td className="px-4 py-2 text-xs text-muted-foreground">{branchMap[item.branchId] || "—"}</td>
                  <td className="px-4 py-2 font-mono text-xs text-muted-foreground">{item.code}</td>
                  <td className="px-4 py-2 font-medium">{item.name}</td>
                  <td className="px-4 py-2">{item.isActive ? <span className="text-success">Yes</span> : <span className="text-muted-foreground">No</span>}</td>
                  <td className="px-4 py-2 text-right">
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
