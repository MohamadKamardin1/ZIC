import { useEffect, useMemo, useState } from "react"
import { Check, Edit2, ExternalLink, ListFilter, Loader2, Plus, Search, ToggleLeft, ToggleRight, Trash2, X } from "lucide-react"
import { useSearchParams } from "react-router-dom"
import { createChoiceList, createChoiceOption, deleteChoiceList, deleteChoiceOption, listChoiceLists, listChoiceOptions, updateChoiceList, updateChoiceOption } from "../../lib/api"
import type { ChoiceList, ChoiceOption } from "../../lib/types"
import { useAccess } from "../../lib/access"
import { hasExplicitPermission, OPTION_CHOICE_LIST_CODES, OPTION_MANAGE_HREFS, OPTION_PARAMETER_SCREEN_LABELS, OPTION_REGISTRY_ENTITIES, prettifyOptionEntity } from "../../lib/optionMetadata"
import { useToast } from "../../components/ui/Toast"
import { ConfirmModal, InfoBanner, Modal } from "../../components/ui/Overlays"
import { TextInput, TextareaInput, Toggle } from "../../components/ui/FormControls"

const MANAGE_PERMISSION = "system_parameters.manage"

type ListForm = { code: string; name: string; description: string; isActive: boolean }
type OptionForm = { code: string; label: string; sortOrder: string; isDefault: boolean; isActive: boolean }

function unwrapError(error: unknown): string {
  return error instanceof Error ? error.message : "Unable to save dropdown configuration."
}

function listForm(item?: ChoiceList | null): ListForm {
  return { code: item?.code ?? "", name: item?.name ?? "", description: item?.description ?? "", isActive: item?.isActive ?? true }
}

function optionForm(item?: ChoiceOption | null): OptionForm {
  return { code: item?.code ?? "", label: item?.label ?? "", sortOrder: String(item?.sortOrder ?? 1), isDefault: item?.isDefault ?? false, isActive: item?.isActive ?? true }
}

export default function OLDropdownConfiguration() {
  const [searchParams] = useSearchParams()
  const requestedEntity = searchParams.get("entity") ?? ""
  const { access } = useAccess()
  const { toast } = useToast()
  const canManage = hasExplicitPermission(access.permissions, MANAGE_PERMISSION)
  const [lists, setLists] = useState<ChoiceList[]>([])
  const [options, setOptions] = useState<ChoiceOption[]>([])
  const [selectedListId, setSelectedListId] = useState("")
  const [search, setSearch] = useState("")
  const [loading, setLoading] = useState(true)
  const [optionsLoading, setOptionsLoading] = useState(false)
  const [error, setError] = useState("")
  const [listModal, setListModal] = useState(false)
  const [optionModal, setOptionModal] = useState(false)
  const [editingList, setEditingList] = useState<ChoiceList | null>(null)
  const [editingOption, setEditingOption] = useState<ChoiceOption | null>(null)
  const [listValues, setListValues] = useState<ListForm>(listForm())
  const [optionValues, setOptionValues] = useState<OptionForm>(optionForm())
  const [saving, setSaving] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<{ kind: "list" | "option"; id: string; label: string } | null>(null)

  const selectedList = useMemo(() => lists.find((item) => item.id === selectedListId) ?? null, [lists, selectedListId])
  const filteredLists = useMemo(() => {
    const needle = search.trim().toLowerCase()
    if (!needle) return lists
    return lists.filter((item) => `${item.code} ${item.name} ${item.description}`.toLowerCase().includes(needle))
  }, [lists, search])
  const filteredOptions = useMemo(() => {
    const needle = search.trim().toLowerCase()
    if (!needle) return options
    return options.filter((item) => `${item.code} ${item.label}`.toLowerCase().includes(needle))
  }, [options, search])

  const loadLists = async () => {
    setLoading(true)
    setError("")
    try {
      const next = await listChoiceLists()
      setLists(next)
      setSelectedListId((current) => current && next.some((item) => item.id === current) ? current : next[0]?.id ?? "")
    } catch (loadError) {
      setError(unwrapError(loadError))
    } finally {
      setLoading(false)
    }
  }

  const loadOptions = async (listId: string) => {
    if (!listId) { setOptions([]); return }
    setOptionsLoading(true)
    try { setOptions(await listChoiceOptions(listId)) } catch (loadError) { setError(unwrapError(loadError)) } finally { setOptionsLoading(false) }
  }

  useEffect(() => { void loadLists() }, [])
  useEffect(() => {
    if (!requestedEntity || lists.length === 0 || selectedListId) return
    const targetHref = OPTION_MANAGE_HREFS[requestedEntity]
    if (!targetHref?.startsWith("/ordinary-life/parameters/dropdown-configuration")) return
    const targetCode = OPTION_CHOICE_LIST_CODES[requestedEntity] ?? ""
    const match = targetCode ? lists.find((item) => item.code.toUpperCase() === targetCode) : undefined
    if (match) setSelectedListId(match.id)
  }, [lists, requestedEntity, selectedListId])
  useEffect(() => { void loadOptions(selectedListId) }, [selectedListId])

  const saveList = async () => {
    if (!listValues.code.trim() || !listValues.name.trim()) { setError("Code and name are required."); return }
    setSaving(true); setError("")
    try {
      const payload = { code: listValues.code.trim().toUpperCase(), name: listValues.name.trim(), description: listValues.description.trim(), is_active: listValues.isActive }
      const saved = editingList ? await updateChoiceList(editingList.id, payload) : await createChoiceList(payload)
      setLists((current) => editingList ? current.map((item) => item.id === saved.id ? saved : item) : [...current, saved])
      setSelectedListId(saved.id)
      setListModal(false)
      toast({ tone: "success", title: editingList ? "Dropdown catalog updated" : "Dropdown catalog created", message: saved.name })
    } catch (saveError) { setError(unwrapError(saveError)) } finally { setSaving(false) }
  }

  const saveOption = async () => {
    if (!selectedListId) { setError("Select a dropdown catalog first."); return }
    if (!optionValues.code.trim() || !optionValues.label.trim()) { setError("Code and label are required."); return }
    setSaving(true); setError("")
    try {
      const payload = { choice_list: selectedListId, code: optionValues.code.trim().toUpperCase(), label: optionValues.label.trim(), sort_order: Number(optionValues.sortOrder) || 1, is_default: optionValues.isDefault, is_active: optionValues.isActive }
      const saved = editingOption ? await updateChoiceOption(editingOption.id, payload) : await createChoiceOption(payload)
      setOptions((current) => editingOption ? current.map((item) => item.id === saved.id ? saved : item) : [...current, saved])
      setOptionModal(false)
      toast({ tone: "success", title: editingOption ? "Dropdown option updated" : "Dropdown option created", message: saved.label })
    } catch (saveError) { setError(unwrapError(saveError)) } finally { setSaving(false) }
  }

  const confirmDelete = async () => {
    if (!deleteTarget) return
    setSaving(true)
    try {
      if (deleteTarget.kind === "list") {
        await deleteChoiceList(deleteTarget.id)
        setLists((current) => current.filter((item) => item.id !== deleteTarget.id))
        setSelectedListId((current) => current === deleteTarget.id ? "" : current)
        setOptions([])
      } else {
        await deleteChoiceOption(deleteTarget.id)
        setOptions((current) => current.filter((item) => item.id !== deleteTarget.id))
      }
      toast({ tone: "success", title: "Configuration deleted", message: deleteTarget.label })
      setDeleteTarget(null)
    } catch (deleteError) { setError(unwrapError(deleteError)) } finally { setSaving(false) }
  }

  const toggleList = async (item: ChoiceList) => {
    if (!canManage) return
    try { const saved = await updateChoiceList(item.id, { is_active: !item.isActive }); setLists((current) => current.map((row) => row.id === saved.id ? saved : row)); toast({ tone: "success", title: saved.isActive ? "Catalog activated" : "Catalog deactivated", message: saved.name }) } catch (toggleError) { setError(unwrapError(toggleError)) }
  }
  const toggleOption = async (item: ChoiceOption) => {
    if (!canManage) return
    try { const saved = await updateChoiceOption(item.id, { is_active: !item.isActive }); setOptions((current) => current.map((row) => row.id === saved.id ? saved : row)); toast({ tone: "success", title: saved.isActive ? "Option activated" : "Option deactivated", message: saved.label }) } catch (toggleError) { setError(unwrapError(toggleError)) }
  }

  return <div className="space-y-5 p-5 lg:p-7">
    <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
      <div><p className="text-xs font-bold uppercase tracking-[0.16em] text-[var(--muted-foreground)]">Ordinary Life / Parameters</p><h1 className="mt-1 text-2xl font-bold tracking-tight">Drop Down Configuration</h1><p className="mt-1 max-w-3xl text-sm text-[var(--muted-foreground)]">Manage every choice-backed OL dropdown from one registry. Changes are immediately available to quotation forms and are audited through System Parameters.</p></div>
      <div className="flex flex-wrap gap-2">{canManage && <button type="button" className="button-primary" onClick={() => { setEditingList(null); setListValues(listForm()); setListModal(true) }}><Plus size={16} /> Add dropdown catalog</button>}<button type="button" className="button-secondary" onClick={() => void loadLists()}><Loader2 size={16} className={loading ? "animate-spin" : ""} /> Refresh</button></div>
    </div>
    <InfoBanner title="Registry-backed configuration">Catalogs are the source of truth for fixed OL choices such as payment frequencies, payment modes, quote bases, identity types, member relations, benefit types, and currencies. IDs remain internal; quotation screens submit values and display labels.</InfoBanner>
    <section className="surface-card p-4"><div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between"><div><h2 className="font-bold">All OL dropdown sources</h2><p className="text-sm text-[var(--muted-foreground)]">Choice catalogs are edited here; relational dropdowns open their authoritative parameter screen in a new authenticated tab.</p></div><span className="rounded-full bg-[var(--muted)] px-2.5 py-1 text-xs font-bold text-[var(--muted-foreground)]">{OPTION_REGISTRY_ENTITIES.length} registered entities</span></div><div className="mt-4 grid gap-2 sm:grid-cols-2 xl:grid-cols-4">{OPTION_REGISTRY_ENTITIES.map((entity) => { const href = OPTION_MANAGE_HREFS[entity]; const isChoice = href.includes("dropdown-configuration"); return <a key={entity} href={href} target="_blank" rel="noreferrer" className="group flex min-w-0 items-center justify-between gap-3 rounded-[10px] border px-3 py-3 transition hover:border-[var(--primary)] hover:bg-[var(--secondary)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]"><span className="min-w-0"><span className="block truncate text-sm font-bold">{prettifyOptionEntity(entity)}</span><span className="mt-0.5 block truncate text-xs text-[var(--muted-foreground)]">{OPTION_PARAMETER_SCREEN_LABELS[entity]}</span></span><span className="flex shrink-0 items-center gap-1 text-[var(--muted-foreground)]"><span className="text-[10px] font-bold uppercase">{isChoice ? "Catalog" : "Master"}</span><ExternalLink size={14} aria-hidden="true" className="transition group-hover:text-[var(--primary)]" /></span></a> })}</div></section>
    {error && <div className="flex items-center justify-between rounded-[10px] border border-[var(--destructive)]/30 bg-[var(--destructive)]/10 px-4 py-3 text-sm text-[var(--destructive)]" role="alert"><span>{error}</span><button type="button" aria-label="Dismiss error" onClick={() => setError("")}><X size={16} /></button></div>}
    <div className="grid gap-5 xl:grid-cols-[minmax(280px,0.38fr)_minmax(0,1fr)]">
      <section className="surface-card overflow-hidden"><div className="flex items-center justify-between border-b px-4 py-3"><div><h2 className="font-bold">Dropdown catalogs</h2><p className="text-xs text-[var(--muted-foreground)]">{filteredLists.length} catalogs</p></div><ListFilter size={17} className="text-[var(--muted-foreground)]" /></div><div className="border-b p-3"><label className="relative block"><Search size={15} className="absolute left-3 top-3 text-[var(--muted-foreground)]" aria-hidden="true" /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search catalogs and options…" className="h-10 w-full rounded-[10px] border bg-[var(--card)] pl-9 pr-3 text-sm outline-none focus:border-[var(--ring)] focus:ring-2 focus:ring-[color-mix(in_srgb,var(--ring)_18%,transparent)]" aria-label="Search dropdown configuration" /></label></div><div className="max-h-[62vh] overflow-auto p-2">{loading && <div className="flex items-center justify-center gap-2 p-8 text-sm text-[var(--muted-foreground)]"><Loader2 size={16} className="animate-spin" /> Loading catalogs…</div>}{!loading && filteredLists.length === 0 && <p className="p-8 text-center text-sm text-[var(--muted-foreground)]">No dropdown catalogs found.</p>}{filteredLists.map((item) => <button type="button" key={item.id} onClick={() => setSelectedListId(item.id)} className={`mb-1 flex w-full items-start justify-between gap-3 rounded-[10px] border px-3 py-3 text-left transition hover:bg-[var(--secondary)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)] ${item.id === selectedListId ? "border-[var(--primary)] bg-[var(--primary)]/5" : "border-transparent"}`}><span className="min-w-0"><span className="block truncate text-sm font-bold">{item.name}</span><span className="mt-0.5 block truncate font-mono text-[11px] text-[var(--muted-foreground)]">{item.code}</span><span className="mt-1 block text-xs text-[var(--muted-foreground)]">{item.options?.length ?? 0} loaded options</span></span><span className={`mt-1 h-2.5 w-2.5 shrink-0 rounded-full ${item.isActive ? "bg-emerald-500" : "bg-slate-400"}`} title={item.isActive ? "Active" : "Inactive"} /></button>)}</div></section>
      <section className="surface-card overflow-hidden"><div className="flex flex-col gap-3 border-b px-4 py-3 sm:flex-row sm:items-center sm:justify-between"><div><h2 className="font-bold">{selectedList?.name ?? "Select a dropdown catalog"}</h2><p className="font-mono text-xs text-[var(--muted-foreground)]">{selectedList?.code ?? "Choose a catalog from the left"}</p></div><div className="flex flex-wrap gap-2">{selectedList && canManage && <><button type="button" className="button-secondary !min-h-9 !px-3" onClick={() => { setEditingList(selectedList); setListValues(listForm(selectedList)); setListModal(true) }}><Edit2 size={14} /> Edit catalog</button><button type="button" aria-label={`Delete catalog ${selectedList.name}`} className="button-secondary !min-h-9 !px-3" onClick={() => setDeleteTarget({ kind: "list", id: selectedList.id, label: selectedList.name })}><Trash2 size={14} /></button><button type="button" aria-label={`${selectedList.isActive ? "Deactivate" : "Activate"} catalog ${selectedList.name}`} className="button-secondary !min-h-9 !px-3" onClick={() => void toggleList(selectedList)}>{selectedList.isActive ? <ToggleRight size={15} /> : <ToggleLeft size={15} />} {selectedList.isActive ? "Deactivate" : "Activate"}</button></>}{selectedList && canManage && <button type="button" className="button-primary !min-h-9 !px-3" onClick={() => { setEditingOption(null); setOptionValues(optionForm()); setOptionModal(true) }}><Plus size={14} /> Add option</button>}</div></div>{selectedList?.description && <p className="border-b px-4 py-3 text-sm text-[var(--muted-foreground)]">{selectedList.description}</p>}<div className="overflow-x-auto"><table className="w-full min-w-[700px] text-left text-sm"><thead className="bg-[var(--muted)]/40 text-xs uppercase tracking-wide text-[var(--muted-foreground)]"><tr><th className="px-4 py-3">Code</th><th className="px-4 py-3">Display label</th><th className="px-4 py-3">Order</th><th className="px-4 py-3">Default</th><th className="px-4 py-3">Status</th><th className="px-4 py-3 text-right">Actions</th></tr></thead><tbody className="divide-y">{optionsLoading && <tr><td colSpan={6} className="px-4 py-10 text-center text-[var(--muted-foreground)]"><Loader2 size={16} className="mx-auto mb-2 animate-spin" />Loading options…</td></tr>}{!optionsLoading && !selectedList && <tr><td colSpan={6} className="px-4 py-10 text-center text-[var(--muted-foreground)]">Select a catalog to manage its options.</td></tr>}{!optionsLoading && selectedList && filteredOptions.length === 0 && <tr><td colSpan={6} className="px-4 py-10 text-center text-[var(--muted-foreground)]">No options found.</td></tr>}{!optionsLoading && filteredOptions.map((item) => <tr key={item.id} className="hover:bg-[var(--secondary)]/50"><td className="px-4 py-3 font-mono text-xs">{item.code}</td><td className="px-4 py-3 font-semibold">{item.label}</td><td className="px-4 py-3">{item.sortOrder}</td><td className="px-4 py-3">{item.isDefault ? <Check size={16} className="text-emerald-600" aria-label="Default" /> : "—"}</td><td className="px-4 py-3"><span className={`rounded-full px-2 py-1 text-xs font-bold ${item.isActive ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-200" : "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300"}`}>{item.isActive ? "Active" : "Inactive"}</span></td><td className="px-4 py-3"><div className="flex justify-end gap-1">{canManage && <><button type="button" className="icon-button" aria-label={`Edit ${item.label}`} onClick={() => { setEditingOption(item); setOptionValues(optionForm(item)); setOptionModal(true) }}><Edit2 size={15} /></button><button type="button" className="icon-button" aria-label={`${item.isActive ? "Deactivate" : "Activate"} ${item.label}`} onClick={() => void toggleOption(item)}>{item.isActive ? <ToggleRight size={15} /> : <ToggleLeft size={15} />}</button><button type="button" className="icon-button text-[var(--destructive)]" aria-label={`Delete ${item.label}`} onClick={() => setDeleteTarget({ kind: "option", id: item.id, label: item.label })}><Trash2 size={15} /></button></>}</div></td></tr>)}</tbody></table></div></section>
    </div>
    <Modal open={listModal} title={editingList ? "Edit dropdown catalog" : "Add dropdown catalog"} description="Catalog metadata is used by the option registry and SmartSelect components." onClose={() => setListModal(false)} footer={<><button type="button" className="button-secondary" onClick={() => setListModal(false)} disabled={saving}>Cancel</button><button type="button" className="button-primary" onClick={() => void saveList()} disabled={saving}>{saving ? "Saving…" : "Save catalog"}</button></>}><div className="grid gap-4"><TextInput label="Code" required value={listValues.code} onChange={(event) => setListValues((current) => ({ ...current, code: event.target.value }))} hint="Stable uppercase registry key, for example OL_PAYMENT_MODE_CHOICES." /><TextInput label="Name" required value={listValues.name} onChange={(event) => setListValues((current) => ({ ...current, name: event.target.value }))} /><TextareaInput label="Description" value={listValues.description} onChange={(event) => setListValues((current) => ({ ...current, description: event.target.value }))} /><Toggle label="Active" checked={listValues.isActive} onChange={(checked) => setListValues((current) => ({ ...current, isActive: checked }))} /></div></Modal>
    <Modal open={optionModal} title={editingOption ? "Edit dropdown option" : "Add dropdown option"} description={selectedList ? `Option in ${selectedList.name}` : "Select a catalog first."} onClose={() => setOptionModal(false)} footer={<><button type="button" className="button-secondary" onClick={() => setOptionModal(false)} disabled={saving}>Cancel</button><button type="button" className="button-primary" onClick={() => void saveOption()} disabled={saving || !selectedListId}>{saving ? "Saving…" : "Save option"}</button></>}><div className="grid gap-4 sm:grid-cols-2"><TextInput label="Code" required value={optionValues.code} onChange={(event) => setOptionValues((current) => ({ ...current, code: event.target.value }))} /><TextInput label="Display label" required value={optionValues.label} onChange={(event) => setOptionValues((current) => ({ ...current, label: event.target.value }))} /><TextInput label="Sort order" type="number" value={optionValues.sortOrder} onChange={(event) => setOptionValues((current) => ({ ...current, sortOrder: event.target.value }))} /><div className="flex items-center gap-6 pt-7"><Toggle label="Default" checked={optionValues.isDefault} onChange={(checked) => setOptionValues((current) => ({ ...current, isDefault: checked }))} /><Toggle label="Active" checked={optionValues.isActive} onChange={(checked) => setOptionValues((current) => ({ ...current, isActive: checked }))} /></div></div></Modal>
    <ConfirmModal open={Boolean(deleteTarget)} title="Delete configuration" description={`Delete ${deleteTarget?.label ?? "this configuration"}? This action is audited and cannot be undone.`} confirmLabel={saving ? "Deleting…" : "Delete"} onClose={() => setDeleteTarget(null)} onConfirm={() => void confirmDelete()} />
  </div>
}
