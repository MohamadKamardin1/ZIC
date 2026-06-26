import { useEffect, useRef, useState } from "react"
import { useParams, useNavigate, useSearchParams } from "react-router-dom"
import {
  ArrowLeft, FileText, ListChecks, Users, Building2,
  Plus, Pencil, Trash2, X, Check, Upload, Loader2, Save,
} from "lucide-react"
import {
  fetchPartnerType,
  fetchDocumentRequirements,
  createDocumentRequirement,
  updateDocumentRequirement,
  deleteDocumentRequirement,
  listDocuments,
  uploadDocument,
  deleteDocument,
  fetchFieldConfigurations,
  fetchContactRequirements,
  fetchBankRequirements,
  listContacts,
  createContact,
  deleteContact,
  listBankAccounts,
  createBankAccount,
  deleteBankAccount,
  listFieldValues,
  batchUpdateFieldValues,
} from "../../lib/api"
import { useDataRefresh, emitDataChange } from "../../lib/useDataRefresh"
import { SkeletonTable } from "../../components/shared/Skeleton"
import type {
  PartnerTypeRecord,
  PartnerTypeDocumentRequirement,
  ApplicationDocument,
  PartnerTypeFieldConfiguration,
  ApplicationContact,
  ApplicationBankAccount,
  ApplicationFieldValue,
} from "../../lib/types"

type Tab = "documents" | "form-fields" | "contacts" | "banks"

const tabs: { key: Tab; label: string; icon: typeof FileText }[] = [
  { key: "documents", label: "Documents", icon: FileText },
  { key: "form-fields", label: "Form Fields", icon: ListChecks },
  { key: "contacts", label: "Contacts", icon: Users },
  { key: "banks", label: "Banks", icon: Building2 },
]

export default function PartnerTypeSetup() {
  const { id } = useParams<{ id: string }>()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const applicationId = searchParams.get("applicationId")
  const [partnerType, setPartnerType] = useState<PartnerTypeRecord | null>(null)
  const [activeTab, setActiveTab] = useState<Tab>("documents")
  const [loading, setLoading] = useState(true)
  useDataRefresh("partner-types")

  useEffect(() => {
    if (!id) return
    setLoading(true)
    fetchPartnerType(id)
      .then(setPartnerType)
      .finally(() => setLoading(false))
  }, [id])

  if (loading) {
    return (
      <div>
        <div className="mb-6 h-8 w-64 animate-pulse rounded bg-muted-foreground/15" />
        <SkeletonTable rows={5} cols={4} />
      </div>
    )
  }

  if (!partnerType) {
    return (
      <div className="flex flex-col items-center gap-4 py-20">
        <p className="text-lg text-muted-foreground">Partner type not found.</p>
        <button onClick={() => navigate("/system-parameters/partner/partner-types")} className="text-sm text-primary underline">
          Back to Partner Types
        </button>
      </div>
    )
  }

  return (
    <div>
      <button
        onClick={() => navigate("/system-parameters/partner/partner-types")}
        className="mb-4 flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Partner Types
      </button>

      <div className="mb-6">
        <h1 className="text-2xl font-bold">{partnerType.name}</h1>
        <p className="text-sm text-muted-foreground">{partnerType.code} — {partnerType.description || "No description"}</p>
      </div>

      <div className="mb-6 flex gap-1 border-b">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setActiveTab(t.key)}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium transition-colors ${
              activeTab === t.key
                ? "border-b-2 border-primary text-primary"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <t.icon className="h-4 w-4" />
            {t.label}
          </button>
        ))}
      </div>

      {activeTab === "documents" && <DocumentsTab partnerTypeId={partnerType.id} applicationId={applicationId} />}
      {activeTab === "form-fields" && <FieldsTab partnerTypeId={partnerType.id} applicationId={applicationId} />}
      {activeTab === "contacts" && <ContactsTab partnerTypeId={partnerType.id} applicationId={applicationId} />}
      {activeTab === "banks" && <BanksTab partnerTypeId={partnerType.id} applicationId={applicationId} />}
    </div>
  )
}

/* ========================================================================== */
/*  Documents Tab                                                              */
/* ========================================================================== */

function DocumentsTab({ partnerTypeId, applicationId }: { partnerTypeId: string; applicationId: string | null }) {
  const [items, setItems] = useState<PartnerTypeDocumentRequirement[]>([])
  const [loading, setLoading] = useState(true)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [adding, setAdding] = useState(false)
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState({ code: "", description: "", isRequired: true, isMandatory: false, sortOrder: 0 })

  const [uploadingFor, setUploadingFor] = useState<string | null>(null)
  const [uploadError, setUploadError] = useState("")
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [existingDocs, setExistingDocs] = useState<ApplicationDocument[]>([])

  useDataRefresh("partner-types")

  useEffect(() => {
    setLoading(true)
    Promise.all([
      fetchDocumentRequirements(partnerTypeId).then(async (reqs) => {
        if (reqs.length === 0) {
          await Promise.all([
            createDocumentRequirement(partnerTypeId, { code: "IDENTITY_DOC", description: "Identity Document", isRequired: true, isMandatory: false, sortOrder: 1 }),
            createDocumentRequirement(partnerTypeId, { code: "PROOF_OF_ADDRESS", description: "Proof of Address", isRequired: true, isMandatory: false, sortOrder: 2 }),
          ])
          return fetchDocumentRequirements(partnerTypeId)
        }
        return reqs
      }).then(setItems),
      applicationId ? listDocuments(applicationId).then(setExistingDocs) : Promise.resolve(),
    ]).finally(() => setLoading(false))
  }, [partnerTypeId, applicationId])

  async function handleAdd() {
    if (!form.code.trim()) return
    setSaving(true)
    try {
      const created = await createDocumentRequirement(partnerTypeId, form)
      setItems((prev) => [...prev, created])
      setForm({ code: "", description: "", isRequired: true, isMandatory: false, sortOrder: 0 })
      setAdding(false)
      emitDataChange("partner-types")
    } finally {
      setSaving(false)
    }
  }

  async function handleEdit(id: string) {
    const item = items.find((i) => i.id === id)
    if (!item) return
    setEditingId(id)
    setForm({ code: item.code, description: item.description, isRequired: item.isRequired, isMandatory: item.isMandatory, sortOrder: item.sortOrder })
  }

  async function handleSave(id: string) {
    setSaving(true)
    try {
      const updated = await updateDocumentRequirement(partnerTypeId, id, form)
      setItems((prev) => prev.map((i) => (i.id === id ? updated : i)))
      setEditingId(null)
      emitDataChange("partner-types")
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete(id: string) {
    if (!confirm("Delete this document requirement?")) return
    await deleteDocumentRequirement(partnerTypeId, id)
    setItems((prev) => prev.filter((i) => i.id !== id))
    emitDataChange("partner-types")
  }

  function resetForm() {
    setForm({ code: "", description: "", isRequired: true, isMandatory: false, sortOrder: 0 })
    setEditingId(null)
    setAdding(false)
  }

  function triggerUpload(code: string) {
    setUploadError("")
    setUploadingFor(code)
    fileInputRef.current?.click()
  }

  async function handleFileSelected(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file || !uploadingFor || !applicationId) return

    setUploadError("")
    setSaving(true)
    try {
      const doc = await uploadDocument(applicationId, file, uploadingFor)
      setExistingDocs((prev) => [...prev, doc])
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : "Upload failed")
    } finally {
      setSaving(false)
      setUploadingFor(null)
      if (fileInputRef.current) fileInputRef.current.value = ""
    }
  }

  async function handleDeleteDoc(docId: string) {
    if (!applicationId) return
    if (!confirm("Delete this uploaded document?")) return
    await deleteDocument(applicationId, docId)
    setExistingDocs((prev) => prev.filter((d) => d.id !== docId))
  }

  function getDocForCode(code: string): ApplicationDocument | undefined {
    return existingDocs.find((d) => d.documentType === code)
  }

  if (loading) return <SkeletonTable rows={5} cols={5} />

  return (
    <div>
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.jpg,.jpeg,.png,.doc,.docx"
        className="hidden"
        onChange={handleFileSelected}
      />

      <div className="mb-4 flex items-center justify-between">
        <p className="text-sm text-muted-foreground">{items.length} document requirement(s)</p>
        {!adding && (
          <button onClick={() => setAdding(true)} className="flex items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground hover:bg-primary/90">
            <Plus className="h-4 w-4" /> Add Document
          </button>
        )}
      </div>

      {adding && (
        <div className="mb-4 rounded-lg border p-4">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
            <div>
              <label className="mb-1 block text-xs font-medium text-muted-foreground">Code</label>
              <input value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value.toUpperCase().replace(/[^A-Z0-9_]/g, "") })}
                className="w-full rounded-lg border border-input bg-background px-3 py-1.5 text-sm outline-none focus:ring-2 focus:ring-primary/40" placeholder="e.g. NID" />
            </div>
            <div className="sm:col-span-2">
              <label className="mb-1 block text-xs font-medium text-muted-foreground">Description</label>
              <input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })}
                className="w-full rounded-lg border border-input bg-background px-3 py-1.5 text-sm outline-none focus:ring-2 focus:ring-primary/40" placeholder="Document description" />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-muted-foreground">Required</label>
              <select value={form.isRequired ? "yes" : "no"} onChange={(e) => setForm({ ...form, isRequired: e.target.value === "yes" })}
                className="w-full rounded-lg border border-input bg-background px-3 py-1.5 text-sm outline-none focus:ring-2 focus:ring-primary/40">
                <option value="yes">Yes</option>
                <option value="no">No</option>
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-muted-foreground">Mandatory</label>
              <select value={form.isMandatory ? "yes" : "no"} onChange={(e) => setForm({ ...form, isMandatory: e.target.value === "yes" })}
                className="w-full rounded-lg border border-input bg-background px-3 py-1.5 text-sm outline-none focus:ring-2 focus:ring-primary/40">
                <option value="yes">Yes</option>
                <option value="no">No</option>
              </select>
            </div>
          </div>
          <div className="mt-3 flex gap-2">
            <button onClick={handleAdd} disabled={saving || !form.code.trim()}
              className="rounded-lg bg-primary px-4 py-1.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50">
              {saving ? "Saving..." : "Save"}
            </button>
            <button onClick={resetForm} disabled={saving}
              className="rounded-lg border border-input px-4 py-1.5 text-sm font-medium hover:bg-accent disabled:opacity-50">
              Cancel
            </button>
          </div>
        </div>
      )}

      {uploadError && (
        <div className="mb-4 rounded-lg border px-4 py-2 text-sm" style={{ borderColor: "var(--color-bg-destructive-soft)", backgroundColor: "var(--color-bg-destructive-soft)", color: "var(--color-text-destructive-soft)" }}>
          {uploadError}
        </div>
      )}

      {items.length === 0 && !adding ? (
        <div className="rounded-lg border border-dashed p-10 text-center text-sm text-muted-foreground">
          No document requirements configured. Click "Add Document" to define one.
        </div>
      ) : (
        <div className="overflow-x-auto rounded-lg border">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-muted/50 text-left text-xs font-medium uppercase text-muted-foreground">
                <th className="px-4 py-3">Code</th>
                <th className="px-4 py-3">Description</th>
                <th className="px-4 py-3">Required</th>
                <th className="px-4 py-3">Mandatory</th>
                <th className="px-4 py-3">Order</th>
                <th className="px-4 py-3">Upload</th>
                <th className="px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => {
                const doc = getDocForCode(item.code)
                return editingId === item.id ? (
                  <tr key={item.id} className="border-b bg-accent/30">
                    <td className="px-4 py-2">
                      <input value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value.toUpperCase().replace(/[^A-Z0-9_]/g, "") })}
                        className="w-full rounded border border-input bg-background px-2 py-1 text-sm outline-none focus:ring-2 focus:ring-primary/40" />
                    </td>
                    <td className="px-4 py-2">
                      <input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })}
                        className="w-full rounded border border-input bg-background px-2 py-1 text-sm outline-none focus:ring-2 focus:ring-primary/40" />
                    </td>
                    <td className="px-4 py-2">
                      <select value={form.isRequired ? "yes" : "no"} onChange={(e) => setForm({ ...form, isRequired: e.target.value === "yes" })}
                        className="w-full rounded border border-input bg-background px-2 py-1 text-sm outline-none focus:ring-2 focus:ring-primary/40">
                        <option value="yes">Yes</option>
                        <option value="no">No</option>
                      </select>
                    </td>
                    <td className="px-4 py-2">
                      <select value={form.isMandatory ? "yes" : "no"} onChange={(e) => setForm({ ...form, isMandatory: e.target.value === "yes" })}
                        className="w-full rounded border border-input bg-background px-2 py-1 text-sm outline-none focus:ring-2 focus:ring-primary/40">
                        <option value="yes">Yes</option>
                        <option value="no">No</option>
                      </select>
                    </td>
                    <td className="px-4 py-2">
                      <input type="number" value={form.sortOrder} onChange={(e) => setForm({ ...form, sortOrder: parseInt(e.target.value) || 0 })}
                        className="w-16 rounded border border-input bg-background px-2 py-1 text-sm outline-none focus:ring-2 focus:ring-primary/40" />
                    </td>
                    <td className="px-4 py-2" />
                    <td className="px-4 py-2">
                      <div className="flex gap-1">
                        <button onClick={() => handleSave(item.id)} disabled={saving}
                          className="rounded p-1 text-success hover:bg-success/10"><Check className="h-4 w-4" /></button>
                        <button onClick={resetForm} disabled={saving}
                          className="rounded p-1 text-destructive hover:bg-destructive/10"><X className="h-4 w-4" /></button>
                      </div>
                    </td>
                  </tr>
                ) : (
                  <tr key={item.id} className="border-b last:border-0 hover:bg-muted/30">
                    <td className="px-4 py-3 font-medium">{item.code}</td>
                    <td className="px-4 py-3 text-muted-foreground">{item.description || "—"}</td>
                    <td className="px-4 py-3">{item.isRequired ? <span className="text-success">Yes</span> : <span className="text-muted-foreground">No</span>}</td>
                    <td className="px-4 py-3">{item.isMandatory ? <span className="text-warning">Yes</span> : <span className="text-muted-foreground">No</span>}</td>
                    <td className="px-4 py-3 text-muted-foreground">{item.sortOrder}</td>
                    <td className="px-4 py-3">
                      {doc ? (
                        <div className="flex items-center gap-2">
                          <a
                            href={doc.file}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 rounded px-2 py-1 text-xs font-medium" style={{ backgroundColor: "var(--color-bg-success-soft)", color: "var(--color-text-success-soft)" }}
                          >
                            <FileText className="h-3 w-3" />
                            {doc.documentName}
                          </a>
                          <button
                            onClick={() => handleDeleteDoc(doc.id)}
                            className="rounded p-0.5 text-destructive hover:bg-destructive/10"
                            title="Delete uploaded file"
                          >
                            <X className="h-3 w-3" />
                          </button>
                        </div>
                      ) : applicationId ? (
                        <button
                          onClick={() => triggerUpload(item.code)}
                          disabled={saving && uploadingFor === item.code}
                          className="inline-flex items-center gap-1 rounded bg-primary/10 px-2.5 py-1 text-xs font-medium text-primary hover:bg-primary/20 disabled:opacity-50"
                        >
                          {saving && uploadingFor === item.code ? (
                            <Loader2 className="h-3 w-3 animate-spin" />
                          ) : (
                            <Upload className="h-3 w-3" />
                          )}
                          Upload
                        </button>
                      ) : (
                        <span className="text-xs text-muted-foreground">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex gap-1">
                        <button onClick={() => handleEdit(item.id)} className="rounded p-1 text-muted-foreground hover:bg-accent"><Pencil className="h-4 w-4" /></button>
                        <button onClick={() => handleDelete(item.id)} className="rounded p-1 text-destructive hover:bg-destructive/10"><Trash2 className="h-4 w-4" /></button>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

/* ========================================================================== */
/*  Form Fields Tab — fillable inputs for each configured field                */
/* ========================================================================== */

function FieldsTab({ partnerTypeId, applicationId }: { partnerTypeId: string; applicationId: string | null }) {
  const [fields, setFields] = useState<PartnerTypeFieldConfiguration[]>([])
  const [values, setValues] = useState<Record<string, string>>({})
  const [fieldConfigMap, setFieldConfigMap] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [justSaved, setJustSaved] = useState(false)

  function setValue(fieldCode: string, value: string) {
    setValues((v) => ({ ...v, [fieldCode]: value }))
    setJustSaved(false)
  }

  useEffect(() => {
    setLoading(true)
    Promise.all([
      fetchFieldConfigurations(partnerTypeId),
      applicationId ? listFieldValues(applicationId).catch(() => [] as ApplicationFieldValue[]) : Promise.resolve([] as ApplicationFieldValue[]),
    ]).then(([flds, existing]) => {
      setFields(flds)
      const configMap: Record<string, string> = {}
      flds.forEach((f) => { configMap[f.fieldCode] = f.id })
      setFieldConfigMap(configMap)

      const init: Record<string, string> = {}
      const existingMap: Record<string, string> = {}
      existing.forEach((fv) => {
        const v = fv.valueJson
        const str = typeof v === "object" && v !== null ? String((v as Record<string, unknown>).value ?? "") : String(v ?? "")
        existingMap[fv.fieldCode] = str
      })

      flds.forEach((f) => {
        if (existingMap[f.fieldCode]) {
          init[f.fieldCode] = existingMap[f.fieldCode]
        } else if (f.validationRules && typeof f.validationRules === "object" && "default" in (f.validationRules as Record<string, unknown>)) {
          init[f.fieldCode] = (f.validationRules as Record<string, string>).default || ""
        } else {
          init[f.fieldCode] = f.defaultValue || ""
        }
      })
      setValues(init)
    }).finally(() => setLoading(false))
  }, [partnerTypeId, applicationId])

  async function handleSave() {
    if (!applicationId) return
    setSaving(true)
    try {
      const payload = fields.map((f) => ({
        field_config: fieldConfigMap[f.fieldCode],
        value_json: { value: values[f.fieldCode] ?? "" },
      })).filter((p) => p.field_config)
      await batchUpdateFieldValues(applicationId, payload)
      setJustSaved(true)
    } catch (e) {
      console.error(e)
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <SkeletonTable rows={4} cols={3} />

  if (fields.length === 0) {
    return (
      <div className="rounded-lg border border-dashed p-10 text-center text-sm text-muted-foreground">
        No form fields configured for this partner type.
      </div>
    )
  }

  return (
    <div>
      <p className="mb-4 text-sm text-muted-foreground">
        Fill in the fields for this partner type.{!applicationId && " (No application context — values are not saved.)"}
      </p>

      <div className="space-y-4">
        {fields
          .sort((a, b) => a.displayOrder - b.displayOrder)
          .map((f) => {
            const rules = f.validationRules && typeof f.validationRules === "object"
              ? (f.validationRules as Record<string, unknown>)
              : {}
            const options = rules.options as string[] | undefined

            return (
              <div key={f.id}>
                <label className="mb-1 block text-xs font-medium text-foreground">
                  {f.fieldName}
                  {f.isRequired && <span className="ml-1 text-destructive">*</span>}
                  <span className="ml-2 text-[10px] text-muted-foreground uppercase">{f.fieldType}</span>
                </label>
                {f.fieldType === "BOOLEAN" ? (
                  <select
                    value={values[f.fieldCode] || "false"}
                    onChange={(e) => setValue(f.fieldCode, e.target.value)}
                    className="w-full rounded-lg border border-input bg-background px-2.5 py-1.5 text-sm outline-none focus:ring-1 focus:ring-primary/50"
                  >
                    <option value="false">No</option>
                    <option value="true">Yes</option>
                  </select>
                ) : f.fieldType === "DATE" ? (
                  <input
                    type="date"
                    value={values[f.fieldCode] || ""}
                    onChange={(e) => setValue(f.fieldCode, e.target.value)}
                    className="w-full rounded-lg border border-input bg-background px-2.5 py-1.5 text-sm outline-none focus:ring-1 focus:ring-primary/50"
                  />
                ) : f.fieldType === "DROPDOWN" && options ? (
                  <select
                    value={values[f.fieldCode] || ""}
                    onChange={(e) => setValue(f.fieldCode, e.target.value)}
                    className="w-full rounded-lg border border-input bg-background px-2.5 py-1.5 text-sm outline-none focus:ring-1 focus:ring-primary/50"
                  >
                    <option value="">Select...</option>
                    {options.map((opt) => <option key={opt} value={opt}>{opt}</option>)}
                  </select>
                ) : f.fieldType === "MULTI_SELECT" && options ? (
                  <div className="flex flex-wrap gap-2">
                    {options.map((opt) => {
                      const selected = (values[f.fieldCode] || "").split(",").includes(opt)
                      return (
                        <label key={opt} className="flex items-center gap-1.5 rounded-lg border border-input px-2.5 py-1.5 text-sm cursor-pointer hover:bg-accent">
                          <input
                            type="checkbox"
                            checked={selected}
                            onChange={() => {
                              const current = (values[f.fieldCode] || "").split(",").filter(Boolean)
                              const next = selected ? current.filter((v) => v !== opt) : [...current, opt]
                              setValue(f.fieldCode, next.join(","))
                            }}
                          />
                          {opt}
                        </label>
                      )
                    })}
                  </div>
                ) : f.fieldType === "PERCENTAGE" ? (
                  <div className="relative">
                    <input
                      type="number"
                      step={String(rules.decimal_places ? 1 / Math.pow(10, rules.decimal_places as number) : 0.01)}
                      min={rules.min as number | undefined}
                      max={rules.max as number | undefined}
                      value={values[f.fieldCode] || ""}
                      onChange={(e) => setValue(f.fieldCode, e.target.value)}
                      className="w-full rounded-lg border border-input bg-background px-2.5 py-1.5 pr-8 text-sm outline-none focus:ring-1 focus:ring-primary/50"
                    />
                    <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-sm text-muted-foreground">%</span>
                  </div>
                ) : f.fieldType === "CURRENCY" ? (
                  <div className="relative">
                    <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-sm text-muted-foreground">$</span>
                    <input
                      type="number"
                      step="0.01"
                      value={values[f.fieldCode] || ""}
                      onChange={(e) => setValue(f.fieldCode, e.target.value)}
                      className="w-full rounded-lg border border-input bg-background pl-8 py-1.5 pr-2.5 text-sm outline-none focus:ring-1 focus:ring-primary/50"
                    />
                  </div>
                ) : (
                  <input
                    value={values[f.fieldCode] || ""}
                    onChange={(e) => setValue(f.fieldCode, e.target.value)}
                    className="w-full rounded-lg border border-input bg-background px-2.5 py-1.5 text-sm outline-none focus:ring-1 focus:ring-primary/50"
                  />
                )}
                {f.fieldType === "PERCENTAGE" && rules.min !== undefined && rules.max !== undefined && (
                  <p className="mt-0.5 text-[10px] text-muted-foreground">
                    Range: {((rules.min as number) * 100).toFixed(0)}% – {((rules.max as number) * 100).toFixed(0)}%
                  </p>
                )}
              </div>
            )
          })}
      </div>

      {applicationId && fields.length > 0 && (
        <div className="mt-6 flex items-center justify-end gap-3 border-t pt-4">
          {justSaved && (
            <span className="text-xs font-medium text-success">Field values saved successfully.</span>
          )}
          <button
            onClick={handleSave}
            disabled={saving}
            className={`flex items-center gap-1.5 rounded-lg px-5 py-2 text-sm font-medium disabled:opacity-50 ${
              justSaved
                ? "bg-success/10 text-success hover:bg-success/20"
                : "bg-primary text-primary-foreground hover:bg-primary/90"
            }`}
          >
            {saving ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : justSaved ? (
              <Check className="h-4 w-4" />
            ) : (
              <Save className="h-4 w-4" />
            )}
            {saving ? "Saving..." : justSaved ? "Saved" : "Save Field Values"}
          </button>
        </div>
      )}
    </div>
  )
}

/* ========================================================================== */
/*  Contacts Tab — add/list contacts for this application                       */
/* ========================================================================== */

interface ContactForm {
  contactType: string; firstName: string; lastName: string; email: string
  phone: string; mobile: string; designation: string; isPrimary: boolean; notes: string
}

const CONTACT_FORM_INIT: ContactForm = {
  contactType: "SECONDARY", firstName: "", lastName: "", email: "",
  phone: "", mobile: "", designation: "", isPrimary: false, notes: "",
}

function ContactsTab({ partnerTypeId, applicationId }: { partnerTypeId: string; applicationId: string | null }) {
  const [items, setItems] = useState<ApplicationContact[]>([])
  const [contactTypes, setContactTypes] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [adding, setAdding] = useState(false)
  const [form, setForm] = useState<ContactForm>(CONTACT_FORM_INIT)

  useDataRefresh("partner-types")

  useEffect(() => {
    if (!applicationId) { setLoading(false); return }
    setLoading(true)
    Promise.all([
      listContacts(applicationId),
      fetchContactRequirements(partnerTypeId).then((reqs) =>
        reqs.filter((r) => r.isActive).map((r) => r.contactType)
      ).catch(() => []),
    ]).then(([contacts, types]) => {
      setItems(contacts)
      setContactTypes(types)
    }).finally(() => setLoading(false))
  }, [applicationId, partnerTypeId])

  function resetForm() { setForm(CONTACT_FORM_INIT); setAdding(false) }

  async function handleAdd() {
    if (!form.firstName || !form.lastName || !applicationId) return
    setSaving(true)
    try {
      const created = await createContact(applicationId, form as unknown as Partial<ApplicationContact>)
      setItems((prev) => [...prev, created])
      resetForm()
      emitDataChange("partner-types")
    } catch (e) {
      console.error(e)
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete(id: string) {
    if (!applicationId) return
    if (!confirm("Delete this contact?")) return
    await deleteContact(applicationId, id)
    setItems((prev) => prev.filter((i) => i.id !== id))
    emitDataChange("partner-types")
  }

  if (!applicationId) {
    return (
      <div className="rounded-lg border border-dashed p-10 text-center text-sm text-muted-foreground">
        Contacts can be added when this page is opened from a partner application.
      </div>
    )
  }

  if (loading) return <SkeletonTable rows={3} cols={5} />

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <p className="text-sm text-muted-foreground">{items.length} contact(s)</p>
        {!adding && (
          <button onClick={() => setAdding(true)} className="flex items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground hover:bg-primary/90">
            <Plus className="h-4 w-4" /> Add Contact
          </button>
        )}
      </div>

      {adding && (
        <div className="mb-6 rounded-xl border border-border bg-card p-5">
          <h3 className="mb-4 text-sm font-semibold text-foreground">New Contact</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-4">
            <div>
              <label className="mb-1 block text-xs font-medium text-foreground">Contact Type</label>
              <select value={form.contactType} onChange={(e) => setForm((f) => ({ ...f, contactType: e.target.value }))}
                className="w-full rounded-lg border border-input bg-background px-2.5 py-1.5 text-sm outline-none focus:ring-1 focus:ring-primary/50">
                {contactTypes.length > 0 ? (
                  contactTypes.map((ct) => <option key={ct} value={ct}>{ct}</option>)
                ) : (
                  <>
                    <option value="PRIMARY">PRIMARY</option>
                    <option value="SECONDARY">SECONDARY</option>
                    <option value="BILLING">BILLING</option>
                  </>
                )}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-foreground">First Name *</label>
              <input value={form.firstName} onChange={(e) => setForm((f) => ({ ...f, firstName: e.target.value }))}
                className="w-full rounded-lg border border-input bg-background px-2.5 py-1.5 text-sm outline-none focus:ring-1 focus:ring-primary/50" />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-foreground">Last Name *</label>
              <input value={form.lastName} onChange={(e) => setForm((f) => ({ ...f, lastName: e.target.value }))}
                className="w-full rounded-lg border border-input bg-background px-2.5 py-1.5 text-sm outline-none focus:ring-1 focus:ring-primary/50" />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-foreground">Email *</label>
              <input value={form.email} onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
                className="w-full rounded-lg border border-input bg-background px-2.5 py-1.5 text-sm outline-none focus:ring-1 focus:ring-primary/50" />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-foreground">Phone</label>
              <input value={form.phone} onChange={(e) => setForm((f) => ({ ...f, phone: e.target.value }))}
                className="w-full rounded-lg border border-input bg-background px-2.5 py-1.5 text-sm outline-none focus:ring-1 focus:ring-primary/50" />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-foreground">Mobile</label>
              <input value={form.mobile} onChange={(e) => setForm((f) => ({ ...f, mobile: e.target.value }))}
                className="w-full rounded-lg border border-input bg-background px-2.5 py-1.5 text-sm outline-none focus:ring-1 focus:ring-primary/50" />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-foreground">Designation</label>
              <input value={form.designation} onChange={(e) => setForm((f) => ({ ...f, designation: e.target.value }))}
                className="w-full rounded-lg border border-input bg-background px-2.5 py-1.5 text-sm outline-none focus:ring-1 focus:ring-primary/50" />
            </div>
            <div className="flex items-end pb-1.5">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={form.isPrimary}
                  onChange={(e) => setForm((f) => ({ ...f, isPrimary: e.target.checked }))}
                  className="h-4 w-4 rounded border-input text-primary focus:ring-primary/50"
                />
                <span className="text-xs font-medium text-foreground">Primary Contact</span>
              </label>
            </div>
            <div className="sm:col-span-2 lg:col-span-3">
              <label className="mb-1 block text-xs font-medium text-foreground">Notes</label>
              <textarea value={form.notes} onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
                className="w-full rounded-lg border border-input bg-background px-2.5 py-1.5 text-sm outline-none focus:ring-1 focus:ring-primary/50" rows={2} />
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <button onClick={resetForm} className="rounded-lg border border-input px-3 py-1.5 text-xs font-medium hover:bg-accent">Cancel</button>
            <button onClick={handleAdd} disabled={saving || !form.firstName || !form.lastName || !form.email}
              className="rounded-lg bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50">
              {saving ? "Saving..." : "Save Contact"}
            </button>
          </div>
        </div>
      )}

      {items.length === 0 && !adding ? (
        <div className="rounded-lg border border-dashed p-10 text-center text-sm text-muted-foreground">
          No contacts added yet. Click "Add Contact" to add one.
        </div>
      ) : (
        <div className="overflow-x-auto rounded-lg border">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-muted/50 text-left text-xs font-medium uppercase text-muted-foreground">
                <th className="px-4 py-3">Type</th>
                <th className="px-4 py-3">Name</th>
                <th className="px-4 py-3">Email</th>
                <th className="px-4 py-3">Phone</th>
                <th className="px-4 py-3">Designation</th>
                <th className="px-4 py-3">Primary</th>
                <th className="w-16 px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {items.map((c) => (
                <tr key={c.id} className="border-b last:border-0 hover:bg-muted/30">
                  <td className="px-4 py-3"><span className="rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-medium text-primary">{c.contactType}</span></td>
                  <td className="px-4 py-3 font-medium">{c.firstName} {c.lastName}</td>
                  <td className="px-4 py-3 text-muted-foreground">{c.email}</td>
                  <td className="px-4 py-3 text-muted-foreground">{c.phone || c.mobile || "—"}</td>
                  <td className="px-4 py-3 text-muted-foreground">{c.designation || "—"}</td>
                  <td className="px-4 py-3">{c.isPrimary ? <span className="text-success">Yes</span> : "—"}</td>
                  <td className="px-4 py-3 text-right">
                    <button onClick={() => handleDelete(c.id)} className="rounded p-1 text-destructive hover:bg-destructive/10">
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

/* ========================================================================== */
/*  Banks Tab — add/list bank accounts for this application                     */
/* ========================================================================== */

interface BankForm {
  bankName: string; branchName: string; accountName: string; accountNumber: string
  swiftCode: string; iban: string; currency: string; isPrimary: boolean
}

const BANK_FORM_INIT: BankForm = {
  bankName: "", branchName: "", accountName: "", accountNumber: "",
  swiftCode: "", iban: "", currency: "TZS", isPrimary: false,
}

function BanksTab({ partnerTypeId, applicationId }: { partnerTypeId: string; applicationId: string | null }) {
  const [items, setItems] = useState<ApplicationBankAccount[]>([])
  const [bankTypes, setBankTypes] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [adding, setAdding] = useState(false)
  const [form, setForm] = useState<BankForm>(BANK_FORM_INIT)

  useDataRefresh("partner-types")

  useEffect(() => {
    if (!applicationId) { setLoading(false); return }
    setLoading(true)
    Promise.all([
      listBankAccounts(applicationId),
      fetchBankRequirements(partnerTypeId).then((reqs) =>
        reqs.filter((r) => r.isActive).map((r) => r.bankType)
      ).catch(() => []),
    ]).then(([accounts, types]) => {
      setItems(accounts)
      setBankTypes(types)
    }).finally(() => setLoading(false))
  }, [applicationId, partnerTypeId])

  function resetForm() { setForm(BANK_FORM_INIT); setAdding(false) }

  async function handleAdd() {
    if (!form.bankName || !form.accountName || !form.accountNumber || !applicationId) return
    setSaving(true)
    try {
      const created = await createBankAccount(applicationId, form)
      setItems((prev) => [...prev, created])
      resetForm()
      emitDataChange("partner-types")
    } catch (e) {
      console.error(e)
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete(id: string) {
    if (!applicationId) return
    if (!confirm("Delete this bank account?")) return
    await deleteBankAccount(applicationId, id)
    setItems((prev) => prev.filter((i) => i.id !== id))
    emitDataChange("partner-types")
  }

  if (!applicationId) {
    return (
      <div className="rounded-lg border border-dashed p-10 text-center text-sm text-muted-foreground">
        Bank accounts can be added when this page is opened from a partner application.
      </div>
    )
  }

  if (loading) return <SkeletonTable rows={3} cols={5} />

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <p className="text-sm text-muted-foreground">{items.length} bank account(s)</p>
        {!adding && (
          <button onClick={() => setAdding(true)} className="flex items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground hover:bg-primary/90">
            <Plus className="h-4 w-4" /> Add Bank Account
          </button>
        )}
      </div>

      {adding && (
        <div className="mb-6 rounded-xl border border-border bg-card p-5">
          <h3 className="mb-4 text-sm font-semibold text-foreground">New Bank Account</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-4">
            {bankTypes.length > 0 && (
              <div>
                <label className="mb-1 block text-xs font-medium text-foreground">Bank Type</label>
                <select value={form.bankName ? "custom" : ""} onChange={() => {}}
                  className="w-full rounded-lg border border-input bg-background px-2.5 py-1.5 text-sm outline-none focus:ring-1 focus:ring-primary/50">
                  {bankTypes.map((bt) => <option key={bt} value={bt}>{bt}</option>)}
                </select>
              </div>
            )}
            <div>
              <label className="mb-1 block text-xs font-medium text-foreground">Bank Name *</label>
              <input value={form.bankName} onChange={(e) => setForm((f) => ({ ...f, bankName: e.target.value }))}
                className="w-full rounded-lg border border-input bg-background px-2.5 py-1.5 text-sm outline-none focus:ring-1 focus:ring-primary/50" placeholder="e.g. CRDB Bank" />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-foreground">Branch Name</label>
              <input value={form.branchName} onChange={(e) => setForm((f) => ({ ...f, branchName: e.target.value }))}
                className="w-full rounded-lg border border-input bg-background px-2.5 py-1.5 text-sm outline-none focus:ring-1 focus:ring-primary/50" placeholder="e.g. Mlimani City" />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-foreground">Account Name *</label>
              <input value={form.accountName} onChange={(e) => setForm((f) => ({ ...f, accountName: e.target.value }))}
                className="w-full rounded-lg border border-input bg-background px-2.5 py-1.5 text-sm outline-none focus:ring-1 focus:ring-primary/50" placeholder="e.g. John Doe Trading" />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-foreground">Account Number *</label>
              <input value={form.accountNumber} onChange={(e) => setForm((f) => ({ ...f, accountNumber: e.target.value }))}
                className="w-full rounded-lg border border-input bg-background px-2.5 py-1.5 text-sm outline-none focus:ring-1 focus:ring-primary/50" placeholder="e.g. 0150123456789" />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-foreground">SWIFT Code</label>
              <input value={form.swiftCode} onChange={(e) => setForm((f) => ({ ...f, swiftCode: e.target.value }))}
                className="w-full rounded-lg border border-input bg-background px-2.5 py-1.5 text-sm outline-none focus:ring-1 focus:ring-primary/50" placeholder="e.g. CORUTZTZ" />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-foreground">IBAN</label>
              <input value={form.iban} onChange={(e) => setForm((f) => ({ ...f, iban: e.target.value }))}
                className="w-full rounded-lg border border-input bg-background px-2.5 py-1.5 text-sm outline-none focus:ring-1 focus:ring-primary/50" placeholder="e.g. TZ..." />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-foreground">Currency</label>
              <select value={form.currency} onChange={(e) => setForm((f) => ({ ...f, currency: e.target.value }))}
                className="w-full rounded-lg border border-input bg-background px-2.5 py-1.5 text-sm outline-none focus:ring-1 focus:ring-primary/50">
                <option value="TZS">TZS</option>
                <option value="USD">USD</option>
                <option value="EUR">EUR</option>
                <option value="GBP">GBP</option>
                <option value="KES">KES</option>
                <option value="UGX">UGX</option>
              </select>
            </div>
            <div className="flex items-end pb-1.5">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={form.isPrimary}
                  onChange={(e) => setForm((f) => ({ ...f, isPrimary: e.target.checked }))}
                  className="h-4 w-4 rounded border-input text-primary focus:ring-primary/50"
                />
                <span className="text-xs font-medium text-foreground">Primary Account</span>
              </label>
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <button onClick={resetForm} className="rounded-lg border border-input px-3 py-1.5 text-xs font-medium hover:bg-accent">Cancel</button>
            <button onClick={handleAdd} disabled={saving || !form.bankName || !form.accountName || !form.accountNumber}
              className="rounded-lg bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50">
              {saving ? "Saving..." : "Save Bank Account"}
            </button>
          </div>
        </div>
      )}

      {items.length === 0 && !adding ? (
        <div className="rounded-lg border border-dashed p-10 text-center text-sm text-muted-foreground">
          No bank accounts added yet. Click "Add Bank Account" to add one.
        </div>
      ) : (
        <div className="overflow-x-auto rounded-lg border">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-muted/50 text-left text-xs font-medium uppercase text-muted-foreground">
                <th className="px-4 py-3">Bank</th>
                <th className="px-4 py-3">Branch</th>
                <th className="px-4 py-3">Account Name</th>
                <th className="px-4 py-3">Account Number</th>
                <th className="px-4 py-3">Currency</th>
                <th className="px-4 py-3">SWIFT</th>
                <th className="px-4 py-3">Primary</th>
                <th className="w-16 px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {items.map((b) => (
                <tr key={b.id} className="border-b last:border-0 hover:bg-muted/30">
                  <td className="px-4 py-3 font-medium">{b.bankName}</td>
                  <td className="px-4 py-3 text-muted-foreground">{b.branchName || "—"}</td>
                  <td className="px-4 py-3">{b.accountName}</td>
                  <td className="px-4 py-3 font-mono text-muted-foreground">{b.accountNumber}</td>
                  <td className="px-4 py-3"><span className="rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-medium text-primary">{b.currency}</span></td>
                  <td className="px-4 py-3 font-mono text-muted-foreground">{b.swiftCode || "—"}</td>
                  <td className="px-4 py-3">{b.isPrimary ? <span className="text-success">Yes</span> : "—"}</td>
                  <td className="px-4 py-3 text-right">
                    <button onClick={() => handleDelete(b.id)} className="rounded p-1 text-destructive hover:bg-destructive/10">
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
