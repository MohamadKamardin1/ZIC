import { useCallback, useEffect, useState } from "react"
import { useNavigate, useParams } from "react-router-dom"
import { ArrowLeft, Loader2, Save, Send, Upload, Trash2, FileText, CheckCircle2 } from "lucide-react"
import {
  createApplication,
  updateApplication,
  getApplication,
  submitApplication,
  uploadDocument,
  deleteDocument,
  listDocuments,
  getChoices,
} from "../../lib/api"
import type { PartnerApplicationDetail, ApplicationDocument, ChoicesResponse } from "../../lib/types"
import { useChoices } from "../../config/ConfigurationHooks"

interface FormState {
  partnerType: "INDIVIDUAL" | "CORPORATE" | ""
  identificationType: string
  identificationNumber: string
  title: string
  firstName: string
  otherName: string
  surname: string
  gender: string
  dateOfBirth: string
  maritalStatus: string
  occupation: string
  nationality: string
  companyName: string
  tinNumber: string
  incorporationDate: string
  industry: string
  contactPerson: string
  contactPersonPhone: string
  contactPersonEmail: string
  email: string
  telephoneNumber: string
  mobileNumber: string
  physicalAddress: string
  postalAddress: string
  politicalRisk: string
  amlRisk: string
}

const INITIAL: FormState = {
  partnerType: "",
  identificationType: "", identificationNumber: "", title: "Mr",
  firstName: "", otherName: "", surname: "", gender: "",
  dateOfBirth: "", maritalStatus: "", occupation: "", nationality: "",
  companyName: "", tinNumber: "", incorporationDate: "", industry: "",
  contactPerson: "", contactPersonPhone: "", contactPersonEmail: "",
  email: "", telephoneNumber: "", mobileNumber: "",
  physicalAddress: "", postalAddress: "",
  politicalRisk: "LOW", amlRisk: "LOW",
}

function toPayload(f: FormState): Record<string, unknown> {
  return {
    partner_type: f.partnerType,
    ...(f.partnerType === "INDIVIDUAL" ? {
      identification_type: f.identificationType, identification_number: f.identificationNumber,
      title: f.title, first_name: f.firstName, other_name: f.otherName, surname: f.surname,
      gender: f.gender, date_of_birth: f.dateOfBirth || null,
      marital_status: f.maritalStatus, occupation: f.occupation, nationality: f.nationality,
    } : {
      company_name: f.companyName, tin_number: f.tinNumber,
      incorporation_date: f.incorporationDate || null, industry: f.industry,
      contact_person: f.contactPerson, contact_person_phone: f.contactPersonPhone,
      contact_person_email: f.contactPersonEmail,
    }),
    email: f.email, telephone_number: f.telephoneNumber, mobile_number: f.mobileNumber,
    physical_address: f.physicalAddress, postal_address: f.postalAddress,
    political_risk: f.politicalRisk, aml_risk: f.amlRisk,
  }
}

export default function ApplicationForm() {
  const { id } = useParams<{ id: string }>()
  const isEdit = !!id
  const navigate = useNavigate()

  const [form, setForm] = useState<FormState>(INITIAL)
  const [saving, setSaving] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState("")
  const [docs, setDocs] = useState<ApplicationDocument[]>([])
  const choices = useChoices()

  // Load choices from API (legacy path — hook handles config endpoint)
  useEffect(() => {
    getChoices().catch(() => {})
  }, [])

  // Edit mode: load application
  useEffect(() => {
    if (!isEdit) return
    let active = true
    getApplication(id!).then((d) => {
      if (!active) return
      setForm({
        partnerType: d.partnerType,
        identificationType: d.identificationType || "", identificationNumber: d.identificationNumber || "",
        title: d.title || "Mr", firstName: d.firstName || "", otherName: d.otherName || "",
        surname: d.surname || "", gender: d.gender || "", dateOfBirth: d.dateOfBirth || "",
        maritalStatus: d.maritalStatus || "", occupation: d.occupation || "", nationality: d.nationality || "",
        companyName: d.companyName || "", tinNumber: d.tinNumber || "", incorporationDate: d.incorporationDate || "",
        industry: d.industry || "", contactPerson: d.contactPerson || "",
        contactPersonPhone: d.contactPersonPhone || "", contactPersonEmail: d.contactPersonEmail || "",
        email: d.email || "", telephoneNumber: d.telephoneNumber || "", mobileNumber: d.mobileNumber || "",
        physicalAddress: d.physicalAddress || "", postalAddress: d.postalAddress || "",
        politicalRisk: d.politicalRisk || "LOW", amlRisk: d.amlRisk || "LOW",
      })
      setDocs(d.documents || [])
    }).catch((e) => {
      if (active) setError(e instanceof Error ? e.message : "Failed to load")
    })
    return () => { active = false }
  }, [id, isEdit])

  // Load documents in edit mode
  useEffect(() => {
    if (!isEdit || !id) return
    let active = true
    listDocuments(id).then((d) => { if (active) setDocs(d) }).catch(() => {})
    return () => { active = false }
  }, [id, isEdit])

  const update = useCallback(
    <K extends keyof FormState>(k: K, v: FormState[K]) => setForm((f) => ({ ...f, [k]: v })),
    [],
  )

  function validate(submit = false): string | null {
    if (!form.partnerType) return "Select a partner type"
    if (form.partnerType === "INDIVIDUAL") {
      if (!form.firstName) return "First name is required"
      if (!form.surname) return "Surname is required"
      if (submit) {
        if (!form.identificationType) return "ID type is required for submission"
        if (!form.identificationNumber) return "ID number is required for submission"
        if (!form.dateOfBirth) return "Date of birth is required for submission"
        if (!form.nationality) return "Nationality is required for submission"
        if (!form.gender) return "Gender is required for submission"
      }
    } else {
      if (!form.companyName) return "Company name is required"
      if (!form.tinNumber) return "TIN number is required"
      if (!form.contactPerson) return "Contact person is required"
      if (submit) {
        if (!form.incorporationDate) return "Incorporation date is required for submission"
        if (!form.industry) return "Industry is required for submission"
        if (!form.contactPersonPhone) return "Contact person phone is required for submission"
        if (!form.contactPersonEmail) return "Contact person email is required for submission"
        if (!form.physicalAddress) return "Physical address is required for submission"
      }
    }
    if (!form.email) return "Email is required"
    if (!form.mobileNumber) return "Mobile number is required"
    if (submit && isEdit && docs.length === 0) return "At least one document must be uploaded before submitting"
    return null
  }

  async function handleSave() {
    const err = validate(false)
    if (err) { setError(err); return }
    setError("")
    setSaving(true)
    try {
      if (isEdit) {
        await updateApplication(id!, toPayload(form))
      } else {
        const result = await createApplication(toPayload(form))
        navigate(`/onboarding/${(result as PartnerApplicationDetail).id}`)
        return
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save")
    } finally {
      setSaving(false)
    }
  }

  async function handleSaveAndSubmit() {
    const err = validate(true)
    if (err) { setError(err); return }
    setError("")
    setSubmitting(true)
    try {
      const appId = isEdit ? id! : ((await createApplication(toPayload(form))) as PartnerApplicationDetail).id
      if (isEdit) await updateApplication(appId, toPayload(form))
      await submitApplication(appId)
      navigate(`/onboarding/${appId}`)
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to submit")
    } finally {
      setSubmitting(false)
    }
  }

  async function handleUpload(file: File, docType: string) {
    if (!isEdit) return
    try {
      const doc = await uploadDocument(id!, file, docType)
      setDocs((d) => [...d, doc])
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed")
    }
  }

  async function handleDeleteDoc(docId: string) {
    if (!isEdit) return
    try {
      await deleteDocument(id!, docId)
      setDocs((d) => d.filter((x) => x.id !== docId))
    } catch (e) {
      setError(e instanceof Error ? e.message : "Delete failed")
    }
  }

  const isCorporate = form.partnerType === "CORPORATE"
  const busy = saving || submitting

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-5">
      {/* Header */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => navigate(isEdit ? `/onboarding/${id}` : "/onboarding")}
          className="rounded-lg p-2 text-muted-foreground transition hover:bg-secondary hover:text-foreground"
        >
          <ArrowLeft className="h-5 w-5" />
        </button>
        <h1 className="text-xl font-bold text-foreground">
          {isEdit ? "Edit Application" : "Add Partner"}
        </h1>
      </div>

      {error && (
        <div className="rounded-xl border px-4 py-3 text-sm font-medium" style={{ borderColor: "var(--color-bg-destructive-soft)", backgroundColor: "var(--color-bg-destructive-soft)", color: "var(--color-text-destructive-soft)" }}>
          {error}
        </div>
      )}

      {/* Type selector */}
      <div className="flex gap-3">
        {(choices?.partnerTypes ?? []).length > 0
          ? (choices!.partnerTypes).map((t) => (
              <button
                key={t.value}
                type="button"
                disabled={isEdit}
                onClick={() => setForm((f) => ({ ...f, partnerType: t.value as "INDIVIDUAL" | "CORPORATE" }))}
                className={`flex-1 rounded-xl border-2 py-4 text-center text-sm font-semibold transition ${
                  form.partnerType === t.value
                    ? "border-primary bg-accent text-accent-foreground"
                    : "border-border bg-card text-muted-foreground hover:border-primary/50"
                } ${isEdit ? "cursor-not-allowed opacity-60" : ""}`}
              >
                {t.label}
              </button>
            ))
          : (["INDIVIDUAL", "CORPORATE"] as const).map((t) => (
              <button
                key={t}
                type="button"
                disabled={isEdit}
                onClick={() => setForm((f) => ({ ...f, partnerType: t }))}
                className={`flex-1 rounded-xl border-2 py-4 text-center text-sm font-semibold transition ${
                  form.partnerType === t
                    ? "border-primary bg-accent text-accent-foreground"
                    : "border-border bg-card text-muted-foreground hover:border-primary/50"
                } ${isEdit ? "cursor-not-allowed opacity-60" : ""}`}
              >
                {t === "INDIVIDUAL" ? "Individual" : "Corporate"}
              </button>
            ))}
      </div>

      {/* Form */}
      <div className="rounded-xl border border-border bg-card p-6 shadow-sm">
        <div className="grid grid-cols-1 gap-x-5 gap-y-4 sm:grid-cols-2">
          {isCorporate ? (
            <>
              <SelectField label="Industry" value={form.industry} onChange={(v) => update("industry", v)}
                options={choices?.industries ?? []} placeholder="Select industry" colSpan={2} />
              <InputField label="Company Name *" value={form.companyName} onChange={(v) => update("companyName", v)} colSpan={2} />
              <InputField label="TIN Number *" value={form.tinNumber} onChange={(v) => update("tinNumber", v)} />
              <InputField type="date" label="Incorporation Date" value={form.incorporationDate} onChange={(v) => update("incorporationDate", v)} />
              <InputField label="Contact Person *" value={form.contactPerson} onChange={(v) => update("contactPerson", v)} />
              <InputField label="Contact Phone" value={form.contactPersonPhone} onChange={(v) => update("contactPersonPhone", v)} />
              <InputField label="Contact Email" value={form.contactPersonEmail} onChange={(v) => update("contactPersonEmail", v)} />
            </>
          ) : (
            <>
              <SelectField label="Title" value={form.title} onChange={(v) => update("title", v)} options={choices?.titles ?? []} />
              <InputField label="First Name *" value={form.firstName} onChange={(v) => update("firstName", v)} />
              <InputField label="Other Name" value={form.otherName} onChange={(v) => update("otherName", v)} />
              <InputField label="Surname *" value={form.surname} onChange={(v) => update("surname", v)} />
              <SelectField label="ID Type" value={form.identificationType} onChange={(v) => update("identificationType", v)}
                options={choices?.identificationTypes ?? []} placeholder="Select ID type" />
              <InputField label="ID Number" value={form.identificationNumber} onChange={(v) => update("identificationNumber", v)} />
              <SelectField label="Gender" value={form.gender} onChange={(v) => update("gender", v)}
                options={choices?.genders ?? []} placeholder="Select gender" />
              <InputField type="date" label="Date of Birth" value={form.dateOfBirth} onChange={(v) => update("dateOfBirth", v)} />
              <SelectField label="Marital Status" value={form.maritalStatus} onChange={(v) => update("maritalStatus", v)}
                options={choices?.maritalStatuses ?? []} placeholder="Select" />
              <InputField label="Occupation" value={form.occupation} onChange={(v) => update("occupation", v)} />
              <SelectField label="Nationality" value={form.nationality} onChange={(v) => update("nationality", v)}
                options={choices?.nationalities ?? []} placeholder="Select nationality" />
            </>
          )}

          {/* --- Common fields --- */}
          <InputField label="Email *" type="email" value={form.email} onChange={(v) => update("email", v)} />
          <InputField label="Mobile Number *" value={form.mobileNumber} onChange={(v) => update("mobileNumber", v)} />
          <InputField label="Telephone" value={form.telephoneNumber} onChange={(v) => update("telephoneNumber", v)} />
          <SelectField label="Political Risk" value={form.politicalRisk} onChange={(v) => update("politicalRisk", v)}
            options={choices?.politicalRisks ?? []} />
          <SelectField label="AML Risk" value={form.amlRisk} onChange={(v) => update("amlRisk", v)}
            options={choices?.amlRisks ?? []} />
          <TextAreaField label="Physical Address" value={form.physicalAddress} onChange={(v) => update("physicalAddress", v)} />
          <TextAreaField label="Postal Address" value={form.postalAddress} onChange={(v) => update("postalAddress", v)} />
        </div>
      </div>

      {/* Documents (edit mode only) */}
      {isEdit && (
      <div className="rounded-xl border border-border bg-card p-6 shadow-sm">
          <h2 className="mb-3 text-base font-semibold text-foreground">Documents</h2>
          <div className="mb-4 flex gap-3">
            <select
              id="docType"
              className="rounded-lg border border-input bg-card px-3 py-2 text-sm text-foreground"
            >
              {(choices?.documentTypes ?? []).map((d) => (
                <option key={d.value} value={d.value}>{d.label}</option>
              ))}
            </select>
            <label className="inline-flex cursor-pointer items-center gap-2 rounded-lg border border-input bg-card px-4 py-2 text-sm font-medium text-foreground transition hover:bg-secondary">
              <Upload className="h-4 w-4" />
              Upload
              <input
                type="file"
                accept=".pdf,.jpg,.jpeg,.png,.doc,.docx"
                className="hidden"
                onChange={(e) => {
                  const file = e.target.files?.[0]
                  const sel = document.getElementById("docType") as HTMLSelectElement | null
                  if (file && sel) { handleUpload(file, sel.value); e.target.value = "" }
                }}
              />
            </label>
          </div>
          {docs.length > 0 && (
            <ul className="divide-y divide-border">
              {docs.map((d) => (
                <li key={d.id} className="flex items-center gap-3 py-3">
                  <FileText className="h-4 w-4 shrink-0 text-muted-foreground" />
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-sm font-medium text-foreground">{d.documentName}</div>
                    <div className="text-xs text-muted-foreground">
                      {(choices?.documentTypes ?? []).find((t) => t.value === d.documentType)?.label ?? d.documentType}
                      {d.fileSize ? ` · ${(d.fileSize / 1024).toFixed(0)} KB` : ""}
                    </div>
                  </div>
                  {d.isVerified && <CheckCircle2 className="h-4 w-4 shrink-0" style={{ color: "var(--color-feedback-success)" }} />}
                  <button onClick={() => handleDeleteDoc(d.id)}
                    className="rounded p-1 text-muted-foreground hover:text-destructive">
                    <Trash2 className="h-4 w-4" />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center justify-end gap-3">
        <button
          onClick={handleSave}
          disabled={busy}
          className="inline-flex items-center gap-2 rounded-lg border border-border px-5 py-2.5 text-sm font-semibold text-foreground transition hover:bg-secondary disabled:opacity-50"
        >
          {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
          Save as Draft
        </button>
        <button
          onClick={handleSaveAndSubmit}
          disabled={busy}
          className="inline-flex items-center gap-2 rounded-lg bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground transition hover:brightness-110 disabled:opacity-50"
        >
          {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
          Save & Submit
        </button>
      </div>
    </div>
  )
}

/* -------------------------------------------------------------------------- */
/*  Field helpers                                                              */
/* -------------------------------------------------------------------------- */

function InputField({ label, value, onChange, type = "text", colSpan }: {
  label: string; value: string; onChange: (v: string) => void; type?: string; colSpan?: number
}) {
  return (
    <div className={colSpan === 2 ? "sm:col-span-2" : ""}>
      <label className="mb-1 block text-sm font-medium text-foreground">{label}</label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-lg border border-input bg-card px-3 py-2.5 text-sm text-foreground outline-none transition placeholder:text-muted-foreground focus:border-ring focus:ring-2 focus:ring-ring/40"
      />
    </div>
  )
}

function SelectField({ label, value, onChange, options, placeholder, colSpan }: {
  label: string; value: string; onChange: (v: string) => void
  options: { value: string; label: string }[]; placeholder?: string; colSpan?: number
}) {
  return (
    <div className={colSpan === 2 ? "sm:col-span-2" : ""}>
      <label className="mb-1 block text-sm font-medium text-foreground">{label}</label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-lg border border-input bg-card px-3 py-2.5 text-sm text-foreground outline-none transition focus:border-ring focus:ring-2 focus:ring-ring/40"
      >
        {placeholder && <option value="">{placeholder}</option>}
        {options.map((o) => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </select>
    </div>
  )
}

function TextAreaField({ label, value, onChange }: {
  label: string; value: string; onChange: (v: string) => void
}) {
  return (
    <div className="sm:col-span-2">
      <label className="mb-1 block text-sm font-medium text-foreground">{label}</label>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        rows={2}
        className="w-full rounded-lg border border-input bg-card px-3 py-2.5 text-sm text-foreground outline-none transition placeholder:text-muted-foreground focus:border-ring focus:ring-2 focus:ring-ring/40"
      />
    </div>
  )
}
