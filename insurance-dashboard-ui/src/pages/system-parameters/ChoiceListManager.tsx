import { useEffect, useState, useCallback } from "react"
import {
  Plus,
  Pencil,
  Trash2,
  X,
  AlertCircle,
  Loader2,
} from "lucide-react"
import {
  listChoiceLists,
  createChoiceList,
  updateChoiceList,
  deleteChoiceList,
  listChoiceOptions,
  createChoiceOption,
  updateChoiceOption,
  deleteChoiceOption,
  clearGroupCache,
} from "../../lib/api"
import { SkeletonTable } from "../../components/shared/Skeleton"
import ConfirmDialog from "../../components/shared/ConfirmDialog"
import Modal from "../../components/shared/Modal"
import { useDataRefresh } from "../../lib/useDataRefresh"
import type { ChoiceList, ChoiceOption } from "../../lib/types"

interface ChoiceListManagerProps {
  title?: string
  description?: string
}

export default function ChoiceListManager({ title, description }: ChoiceListManagerProps) {
  const [lists, setLists] = useState<ChoiceList[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [selectedListId, setSelectedListId] = useState<string | null>(null)
  const [options, setOptions] = useState<ChoiceOption[]>([])
  const [optionsLoading, setOptionsLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  
  const refreshKey = useDataRefresh("choice-lists")

  // Modals state
  const [listModal, setListModal] = useState<{ open: boolean; mode: "create" | "edit"; id?: string; code: string; name: string }>({ open: false, mode: "create", code: "", name: "" })
  const [optionModal, setOptionModal] = useState<{ open: boolean; mode: "create" | "edit"; id?: string; code: string; label: string }>({ open: false, mode: "create", code: "", label: "" })
  const [deleteDialog, setDeleteDialog] = useState<{ open: boolean; type: "list" | "option"; id: string; name: string }>({ open: false, type: "list", id: "", name: "" })

  const loadLists = useCallback(async () => {
    setLoading(true)
    setError("")
    try {
      const data = await listChoiceLists()
      setLists(data)
      if (!selectedListId && data.length > 0) {
        setSelectedListId(data[0].id)
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load choice lists")
    } finally {
      setLoading(false)
    }
  }, [selectedListId, refreshKey])

  useEffect(() => {
    loadLists()
  }, [loadLists])

  const loadOptions = useCallback(async (listId: string) => {
    setOptionsLoading(true)
    try {
      const data = await listChoiceOptions(listId)
      setOptions(data)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load options")
    } finally {
      setOptionsLoading(false)
    }
  }, [])

  useEffect(() => {
    if (selectedListId) {
      loadOptions(selectedListId)
    }
  }, [selectedListId, loadOptions])

  const selectedList = lists.find((l) => l.id === selectedListId)

  // --- List Handlers ---
  async function handleSaveList() {
    if (!listModal.code) { setError("Code is required"); return }
    setSaving(true)
    setError("")
    try {
      if (listModal.mode === "create") {
        await createChoiceList({ code: listModal.code, name: listModal.name || listModal.code } as Record<string, unknown>)
      } else {
        await updateChoiceList(listModal.id!, { code: listModal.code, name: listModal.name } as Record<string, unknown>)
      }
      setListModal((prev) => ({ ...prev, open: false }))
      clearGroupCache()
      await loadLists()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : `Failed to ${listModal.mode} list`)
    } finally {
      setSaving(false)
    }
  }

  async function handleSaveOption() {
    if (!optionModal.code || !selectedListId) { setError("Code is required"); return }
    setSaving(true)
    setError("")
    try {
      if (optionModal.mode === "create") {
        await createChoiceOption({
          choice_list: selectedListId,
          code: optionModal.code,
          label: optionModal.label || optionModal.code,
          sort_order: (options.length + 1) * 10,
        } as Record<string, unknown>)
      } else {
        await updateChoiceOption(optionModal.id!, { code: optionModal.code, label: optionModal.label } as Record<string, unknown>)
      }
      setOptionModal((prev) => ({ ...prev, open: false }))
      await loadOptions(selectedListId)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : `Failed to ${optionModal.mode} option`)
    } finally {
      setSaving(false)
    }
  }

  async function confirmDelete() {
    setSaving(true)
    setError("")
    try {
      if (deleteDialog.type === "list") {
        await deleteChoiceList(deleteDialog.id)
        if (selectedListId === deleteDialog.id) {
          setSelectedListId(null)
          setOptions([])
        }
        clearGroupCache()
        await loadLists()
      } else {
        await deleteChoiceOption(deleteDialog.id)
        if (selectedListId) await loadOptions(selectedListId)
      }
      setDeleteDialog((prev) => ({ ...prev, open: false }))
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to delete")
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="grid gap-5 lg:grid-cols-[280px_1fr]">
        <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
          <div className="mb-3 flex items-center justify-between">
            <div className="h-3 w-16 animate-pulse rounded bg-muted-foreground/15" />
            <div className="h-7 w-14 animate-pulse rounded-lg bg-muted-foreground/15" />
          </div>
          <div className="space-y-1">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="h-9 animate-pulse rounded-md bg-muted-foreground/15" />
            ))}
          </div>
        </div>
        <SkeletonTable rows={5} cols={3} />
      </div>
    )
  }

  return (
    <div>
      {title && <h2 className="mb-1 text-base font-semibold">{title}</h2>}
      {description && <p className="mb-4 text-xs text-muted-foreground">{description}</p>}

      {error && (
        <div className="mb-4 flex items-center gap-2 rounded-lg bg-destructive/10 px-4 py-2 text-sm text-destructive">
          <AlertCircle className="h-4 w-4 flex-none" />
          {error}
          <button onClick={() => setError("")} className="ml-auto"><X className="h-4 w-4" /></button>
        </div>
      )}

      <div className="grid gap-5 lg:grid-cols-[280px_1fr]">
        {/* Left panel: list of choice lists */}
        <div>
          <div className="mb-3 flex items-center justify-between">
            <span className="text-xs font-medium text-muted-foreground">{lists.length} lists</span>
            <button
              onClick={() => setListModal({ open: true, mode: "create", code: "", name: "" })}
              className="inline-flex items-center gap-1 rounded-lg bg-primary px-2.5 py-1 text-xs font-medium text-primary-foreground hover:bg-primary/90"
            >
              <Plus className="h-3 w-3" /> New
            </button>
          </div>

          <div className="space-y-1">
            {lists.map((list) => (
              <button
                key={list.id}
                onClick={() => setSelectedListId(list.id)}
                className={`w-full rounded-lg px-3 py-2 text-left text-sm transition ${
                  selectedListId === list.id
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-secondary"
                }`}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-sm font-medium truncate">{list.code}</div>
                    <div className={`text-xs ${selectedListId === list.id ? "text-primary-foreground/70" : "text-muted-foreground"}`}>
                      {list.options?.length ?? "—"} options
                    </div>
                  </div>
                  <div className="flex gap-0.5" onClick={(e) => e.stopPropagation()}>
                    <button
                      onClick={() => setListModal({ open: true, mode: "edit", id: list.id, code: list.code, name: list.name || "" })}
                      className={`rounded p-0.5 transition ${selectedListId === list.id ? "hover:bg-primary-foreground/20 text-primary-foreground" : "hover:bg-secondary text-muted-foreground"}`}
                    >
                      <Pencil className="h-3.5 w-3.5" />
                    </button>
                    <button
                      onClick={() => setDeleteDialog({ open: true, type: "list", id: list.id, name: list.code })}
                      className={`rounded p-0.5 transition ${selectedListId === list.id ? "hover:bg-primary-foreground/20 text-primary-foreground" : "hover:bg-secondary hover:text-destructive text-muted-foreground"}`}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
              </button>
            ))}
            {lists.length === 0 && (
              <p className="py-4 text-center text-xs text-muted-foreground">No choice lists yet.</p>
            )}
          </div>
        </div>

        {/* Right panel: options for selected list */}
        <div>
          {selectedList ? (
            <div>
              <div className="mb-3 flex items-center justify-between">
                <h3 className="text-base font-semibold">{selectedList.code} — Options</h3>
                <button
                  onClick={() => setOptionModal({ open: true, mode: "create", code: "", label: "" })}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground hover:bg-primary/90"
                >
                  <Plus className="h-3.5 w-3.5" />
                  Add Option
                </button>
              </div>

              {optionsLoading ? (
                <SkeletonTable rows={4} cols={3} />
              ) : (
                <div className="overflow-hidden rounded-lg border border-border bg-card shadow-sm">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-border bg-muted/50">
                        <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">Code</th>
                        <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">Label</th>
                        <th className="w-20 px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-muted-foreground">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {options.length === 0 && (
                        <tr>
                          <td colSpan={3} className="px-4 py-8 text-center text-sm text-muted-foreground">
                            No options yet. Click "Add Option".
                          </td>
                        </tr>
                      )}
                      {options.map((opt) => (
                        <tr key={opt.id} className="border-b border-border/50 last:border-0 hover:bg-secondary/40 transition">
                          <td className="px-4 py-3 font-mono text-xs text-foreground/80">{opt.code}</td>
                          <td className="px-4 py-3 font-medium text-foreground">{opt.label}</td>
                          <td className="px-4 py-3 text-right">
                            <div className="inline-flex justify-end gap-1">
                              <button
                                onClick={() => setOptionModal({ open: true, mode: "edit", id: opt.id, code: opt.code, label: opt.label || "" })}
                                className="rounded p-1.5 text-muted-foreground transition hover:bg-secondary hover:text-foreground"
                              >
                                <Pencil className="h-4 w-4" />
                              </button>
                              <button
                                onClick={() => setDeleteDialog({ open: true, type: "option", id: opt.id, name: opt.label || opt.code })}
                                className="rounded p-1.5 text-muted-foreground transition hover:bg-destructive/10 hover:text-destructive"
                              >
                                <Trash2 className="h-4 w-4" />
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          ) : (
            <div className="flex h-40 items-center justify-center rounded-xl border border-dashed border-border text-sm text-muted-foreground">
              Select a choice list to manage its options
            </div>
          )}
        </div>
      </div>

      {/* Modals */}
      <Modal 
        open={listModal.open} 
        title={listModal.mode === "create" ? "Create Choice List" : "Edit Choice List"} 
        onClose={() => setListModal((prev) => ({ ...prev, open: false }))}
      >
        <div className="space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-foreground">Code</label>
            <input
              type="text"
              value={listModal.code}
              onChange={(e) => setListModal((prev) => ({ ...prev, code: e.target.value }))}
              placeholder="e.g. COUNTRY_LIST"
              className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm font-mono focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-foreground">Name (Optional)</label>
            <input
              type="text"
              value={listModal.name}
              onChange={(e) => setListModal((prev) => ({ ...prev, name: e.target.value }))}
              placeholder="e.g. Countries"
              className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button
              onClick={() => setListModal((prev) => ({ ...prev, open: false }))}
              className="rounded-lg border border-border px-4 py-2 text-sm font-medium text-foreground transition hover:bg-secondary"
            >
              Cancel
            </button>
            <button
              onClick={handleSaveList}
              disabled={saving || !listModal.code}
              className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground transition hover:bg-primary/90 disabled:opacity-50"
            >
              {saving && <Loader2 className="h-4 w-4 animate-spin" />}
              {listModal.mode === "create" ? "Create" : "Save Changes"}
            </button>
          </div>
        </div>
      </Modal>

      <Modal 
        open={optionModal.open} 
        title={optionModal.mode === "create" ? "Add Option" : "Edit Option"} 
        onClose={() => setOptionModal((prev) => ({ ...prev, open: false }))}
      >
        <div className="space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-foreground">Code / Value</label>
            <input
              type="text"
              value={optionModal.code}
              onChange={(e) => setOptionModal((prev) => ({ ...prev, code: e.target.value }))}
              placeholder="e.g. US"
              className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm font-mono focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-foreground">Display Label</label>
            <input
              type="text"
              value={optionModal.label}
              onChange={(e) => setOptionModal((prev) => ({ ...prev, label: e.target.value }))}
              placeholder="e.g. United States"
              className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button
              onClick={() => setOptionModal((prev) => ({ ...prev, open: false }))}
              className="rounded-lg border border-border px-4 py-2 text-sm font-medium text-foreground transition hover:bg-secondary"
            >
              Cancel
            </button>
            <button
              onClick={handleSaveOption}
              disabled={saving || !optionModal.code}
              className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground transition hover:bg-primary/90 disabled:opacity-50"
            >
              {saving && <Loader2 className="h-4 w-4 animate-spin" />}
              {optionModal.mode === "create" ? "Add Option" : "Save Changes"}
            </button>
          </div>
        </div>
      </Modal>

      <ConfirmDialog
        open={deleteDialog.open}
        title={`Delete ${deleteDialog.type === "list" ? "Choice List" : "Option"}`}
        message={`Are you sure you want to delete "${deleteDialog.name}"? ${deleteDialog.type === "list" ? "All options inside this list will also be permanently deleted." : "This action cannot be undone."}`}
        confirmLabel="Delete"
        loading={saving}
        onConfirm={confirmDelete}
        onCancel={() => setDeleteDialog((prev) => ({ ...prev, open: false }))}
      />
    </div>
  )
}
