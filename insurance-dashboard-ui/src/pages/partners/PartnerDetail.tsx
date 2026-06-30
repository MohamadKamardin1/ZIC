import { useCallback, useEffect, useState, useRef } from "react"
import { useNavigate, useParams, useSearchParams } from "react-router-dom"
import {
  ArrowLeft, User, Building2, Shield, FileText, Loader2, Pencil,
  FileSpreadsheet, Contact, Landmark, CheckCircle, XCircle, Plus, Trash2, Upload,
} from "lucide-react"
import {
  getPartner,
  getAssignmentSetupSummary,
  getAssignmentDocuments,
  uploadAssignmentDocumentFile,
  updateAssignmentDocument,
  getAssignmentFieldValues,
  updateAssignmentFieldValues,
  getAssignmentContacts,
  createAssignmentContact,
  deleteAssignmentContact,
  getAssignmentBankAccounts,
  createAssignmentBankAccount,
  deleteAssignmentBankAccount,
  getAssignmentKYC,
  updateAssignmentKYC,
  fetchDocumentRequirements,
} from "../../lib/api"
import type {
  PartnerDetail as PartnerDetailType,
  PartnerTypeAssignment,
  SetupSummary,
  PartnerDocument,
  PartnerDynamicFieldValue,
  PartnerAssignmentContact,
  PartnerAssignmentBankAccount,
  PartnerKYCProfile,
  PartnerTypeDocumentRequirement,
  PartnerTypeFieldConfiguration,
  PartnerTypeContactRequirement,
  PartnerTypeBankRequirement,
} from "../../lib/types"

type SetupTab = "documents" | "fields" | "contacts" | "banks" | "kyc"

export default function PartnerDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const fromOnboarding = searchParams.get("from") === "onboarding"

  const [partner, setPartner] = useState<PartnerDetailType | null>(null)
  const [summaries, setSummaries] = useState<Record<string, SetupSummary>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [expandedAssign, setExpandedAssign] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<SetupTab>("documents")

  const load = useCallback(async () => {
    if (!id) return
    setLoading(true)
    setError("")
    try {
      const data = await getPartner(id)
      setPartner(data)

      const summaryMap: Record<string, SetupSummary> = {}
      if (data.typeAssignments?.length) {
        const results = await Promise.allSettled(
          data.typeAssignments.map((a) =>
            getAssignmentSetupSummary(a.id).then((s) => ({ id: a.id, summary: s })),
          ),
        )
        for (const r of results) {
          if (r.status === "fulfilled") summaryMap[r.value.id] = r.value.summary
        }
      }
      setSummaries(summaryMap)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load partner")
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => { load() }, [load])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-4 rounded-lg bg-[var(--color-bg-destructive-soft)] text-[var(--color-text-destructive-soft)] text-sm">
        {error}
      </div>
    )
  }

  if (!partner) return null

  function statusBadge(status: string) {
    const colors: Record<string, string> = {
      ACTIVE: "bg-[var(--color-bg-success-soft)] text-[var(--color-text-success-soft)]",
      INACTIVE: "bg-[var(--color-bg-destructive-soft)] text-[var(--color-text-destructive-soft)]",
    }
    return (
      <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium ${colors[status] ?? "bg-[var(--color-bg-warning-soft)] text-[var(--color-text-warning-soft)]"}`}>
        {status}
      </span>
    )
  }

  return (
    <div className="space-y-6">
      <button
        onClick={() => navigate(fromOnboarding ? "/onboarding" : "/partners")}
        className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
      >
        <ArrowLeft className="h-4 w-4" />
        {fromOnboarding ? "Back to Onboarding" : "Back to Partners"}
      </button>

      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">{partner.displayName}</h1>
          <p className="text-sm text-muted-foreground mt-1">{partner.partnerNumber}</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate(`/partners/${id}/edit`)}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-border text-sm text-foreground hover:bg-muted transition-colors"
          >
            <Pencil className="h-3.5 w-3.5" />
            Edit
          </button>
          {statusBadge(partner.status)}
          <span className="text-sm text-muted-foreground">{partner.partnerCategory || partner.partnerType}</span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <div className="rounded-xl border border-border bg-card p-5">
            <h2 className="text-base font-semibold text-foreground mb-4 flex items-center gap-2">
              <User className="h-4 w-4 text-muted-foreground" />
              Core Information
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Field label="Partner Type" value={partner.partnerCategory || partner.partnerType} />
              <Field label="Status" value={partner.status} />
              <Field label="Email" value={partner.email} />
              <Field label="Mobile" value={partner.mobileNumber} />
              <Field label="Telephone" value={partner.telephoneNumber} />
              <Field label="TIN" value={partner.tinNumber} />
              <Field label="Political Risk" value={partner.politicalRisk} />
              <Field label="AML Risk" value={partner.amlRisk} />
            </div>
            <div className="mt-4 space-y-2">
              <Field label="Physical Address" value={partner.physicalAddress} />
              <Field label="Postal Address" value={partner.postalAddress} />
            </div>
            <div className="mt-4 pt-4 border-t border-border grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Field label="Company" value={partner.companyName} />
              <Field label="Contact Person" value={partner.contactPerson} />
              <Field label="Contact Phone" value={partner.contactPersonPhone} />
              <Field label="Contact Email" value={partner.contactPersonEmail} />
              <Field label="Occupation" value={partner.occupation} />
              <Field label="Nationality" value={partner.nationality} />
            </div>
          </div>

          {partner.individualProfile && (
            <div className="rounded-xl border border-border bg-card p-5">
              <h2 className="text-base font-semibold text-foreground mb-4 flex items-center gap-2">
                <User className="h-4 w-4 text-muted-foreground" />
                Individual Profile
              </h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <Field label="Title" value={partner.individualProfile.title} />
                <Field label="First Name" value={partner.individualProfile.firstName} />
                <Field label="Other Name" value={partner.individualProfile.otherName} />
                <Field label="Surname" value={partner.individualProfile.surname} />
                <Field label="Gender" value={partner.individualProfile.gender} />
                <Field label="Date of Birth" value={partner.individualProfile.dateOfBirth} />
                <Field label="Marital Status" value={partner.individualProfile.maritalStatus} />
                <Field label="Occupation" value={partner.individualProfile.occupation} />
                <Field label="Nationality" value={partner.individualProfile.nationality} />
                <Field label="ID Type" value={partner.individualProfile.identificationType} />
                <Field label="ID Number" value={partner.individualProfile.identificationNumber} />
              </div>
            </div>
          )}

          {partner.corporateProfile && (
            <div className="rounded-xl border border-border bg-card p-5">
              <h2 className="text-base font-semibold text-foreground mb-4 flex items-center gap-2">
                <Building2 className="h-4 w-4 text-muted-foreground" />
                Corporate Profile
              </h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <Field label="Company Name" value={partner.corporateProfile.companyName} />
                <Field label="TIN Number" value={partner.corporateProfile.tinNumber} />
                <Field label="Incorporation Date" value={partner.corporateProfile.incorporationDate} />
                <Field label="Industry" value={partner.corporateProfile.industry} />
                <Field label="Contact Person" value={partner.corporateProfile.contactPerson} />
                <Field label="Contact Phone" value={partner.corporateProfile.contactPersonPhone} />
                <Field label="Contact Email" value={partner.corporateProfile.contactPersonEmail} />
              </div>
            </div>
          )}

          {partner.typeAssignments?.length > 0 && (
            <div className="rounded-xl border border-border bg-card p-5">
              <h2 className="text-base font-semibold text-foreground mb-4 flex items-center gap-2">
                <Shield className="h-4 w-4 text-muted-foreground" />
                Type Assignments ({partner.typeAssignments.length})
              </h2>
              <div className="space-y-3">
                {partner.typeAssignments.map((ta) => {
                  const summary = summaries[ta.id]
                  const isExpanded = expandedAssign === ta.id
                  return (
                    <div key={ta.id} className="rounded-lg border border-border">
                      <div
                        className="flex items-center justify-between p-4 hover:bg-muted/30 transition-colors cursor-pointer"
                        onClick={() => setExpandedAssign(isExpanded ? null : ta.id)}
                      >
                        <div>
                          <span className="font-medium text-foreground">{ta.partnerTypeName}</span>
                          <span className="text-sm text-muted-foreground ml-2">({ta.partnerTypeCode})</span>
                        </div>
                        <div className="flex items-center gap-3">
                          {summary && (
                            <span className="text-xs text-muted-foreground">
                              Docs {summary.documents.progressPct}% | Fields {summary.fields.progressPct}%
                            </span>
                          )}
                          {statusBadge(ta.status)}
                        </div>
                      </div>
                      {isExpanded && (
                        <SetupManager
                          assignment={ta}
                          summary={summary}
                          onRefresh={() => load()}
                        />
                      )}
                    </div>
                  )
                })}
              </div>
            </div>
          )}
        </div>

        <div className="space-y-6">
          {/* Progress Overview */}
          {partner.typeAssignments && partner.typeAssignments.length > 0 && (
            <div className="rounded-xl border border-border bg-card p-5">
              <h2 className="text-base font-semibold text-foreground mb-4 flex items-center gap-2">
                <Shield className="h-4 w-4 text-muted-foreground" />
                Progress Overview
              </h2>
              {(() => {
                const vals = Object.values(summaries)
                const total = vals.length
                if (total === 0) return <p className="text-xs text-muted-foreground">Loading...</p>
                const avgDocs = Math.round(vals.reduce((s, v) => s + v.documents.progressPct, 0) / total)
                const avgFields = Math.round(vals.reduce((s, v) => s + v.fields.progressPct, 0) / total)
                const avgContacts = Math.round(vals.reduce((s, v) => s + v.contacts.progressPct, 0) / total)
                const avgBanks = Math.round(vals.reduce((s, v) => s + v.banks.progressPct, 0) / total)
                const overall = Math.round((avgDocs + avgFields + avgContacts + avgBanks) / 4)
                return (
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-muted-foreground">Overall Completion</span>
                      <span className="text-sm font-bold text-foreground">{overall}%</span>
                    </div>
                    <div className="h-2 w-full rounded-full bg-[var(--color-bg-muted)] overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all duration-700 ease-out"
                        style={{
                          width: `${overall}%`,
                          backgroundColor: overall >= 80
                            ? "var(--color-feedback-success)"
                            : overall >= 50
                              ? "var(--color-feedback-warning)"
                              : "var(--color-feedback-info)",
                        }}
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-2 pt-1">
                      <MiniProgress label="Docs" pct={avgDocs} />
                      <MiniProgress label="Fields" pct={avgFields} />
                      <MiniProgress label="Contacts" pct={avgContacts} />
                      <MiniProgress label="Banks" pct={avgBanks} />
                    </div>
                  </div>
                )
              })()}
            </div>
          )}

          <div className="rounded-xl border border-border bg-card p-5">
            <h2 className="text-base font-semibold text-foreground mb-4 flex items-center gap-2">
              <FileText className="h-4 w-4 text-muted-foreground" />
              Timestamps
            </h2>
            <div className="space-y-3 text-sm">
              <div><span className="text-muted-foreground">Created</span><p className="text-foreground">{formatDate(partner.createdAt)}</p></div>
              <div><span className="text-muted-foreground">Updated</span><p className="text-foreground">{formatDate(partner.updatedAt)}</p></div>
              {partner.activatedAt && <div><span className="text-muted-foreground">Activated</span><p className="text-foreground">{formatDate(partner.activatedAt)}</p></div>}
              {partner.deactivatedAt && <div><span className="text-muted-foreground">Deactivated</span><p className="text-foreground">{formatDate(partner.deactivatedAt)}</p></div>}
            </div>
          </div>
          {partner.deactivationReason && (
            <div className="rounded-xl border border-border bg-card p-5">
              <h2 className="text-base font-semibold text-foreground mb-2">Deactivation Reason</h2>
              <p className="text-sm text-muted-foreground">{partner.deactivationReason}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function SetupManager({
  assignment,
  summary,
  onRefresh,
}: {
  assignment: PartnerTypeAssignment
  summary?: SetupSummary
  onRefresh: () => void
}) {
  const [tab, setTab] = useState<SetupTab>("documents")

  const tabs: { key: SetupTab; label: string; icon: React.ReactNode }[] = [
    { key: "documents", label: "Documents", icon: <FileText className="h-3.5 w-3.5" /> },
    { key: "fields", label: "Fields", icon: <FileSpreadsheet className="h-3.5 w-3.5" /> },
    { key: "contacts", label: "Contacts", icon: <Contact className="h-3.5 w-3.5" /> },
    { key: "banks", label: "Banks", icon: <Landmark className="h-3.5 w-3.5" /> },
    { key: "kyc", label: "KYC", icon: <CheckCircle className="h-3.5 w-3.5" /> },
  ]

  return (
    <div className="border-t border-border">
      <div className="flex gap-1 px-4 pt-3 border-b border-border bg-muted/20">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`flex items-center gap-1.5 px-3 py-2 text-xs font-medium border-b-2 transition-colors ${
              tab === t.key
                ? "border-primary text-foreground bg-card"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            {t.icon}
            {t.label}
          </button>
        ))}
      </div>
      <div className="p-4">
        {tab === "documents" && <DocumentsTab assignmentId={assignment.id} partnerTypeId={assignment.partnerType} onRefresh={onRefresh} />}
        {tab === "fields" && <FieldsTab assignmentId={assignment.id} onRefresh={onRefresh} />}
        {tab === "contacts" && <ContactsTab assignmentId={assignment.id} onRefresh={onRefresh} />}
        {tab === "banks" && <BanksTab assignmentId={assignment.id} onRefresh={onRefresh} />}
        {tab === "kyc" && <KYCTab assignmentId={assignment.id} onRefresh={onRefresh} />}
      </div>
    </div>
  )
}

function DocumentsTab({ assignmentId, partnerTypeId, onRefresh }: { assignmentId: string; partnerTypeId: string; onRefresh: () => void }) {
  const [requirements, setRequirements] = useState<PartnerTypeDocumentRequirement[]>([])
  const [docs, setDocs] = useState<PartnerDocument[]>([])
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState("")
  const [uploading, setUploading] = useState<string | null>(null)
  const fileRefs = useRef<Record<string, HTMLInputElement | null>>({})

  const [manualMode, setManualMode] = useState(false)
  const [manualReqId, setManualReqId] = useState("")
  const manualFileRef = useRef<HTMLInputElement | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setLoadError("")
    try {
      const [reqs, existing] = await Promise.all([
        fetchDocumentRequirements(partnerTypeId),
        getAssignmentDocuments(assignmentId),
      ])
      setRequirements(reqs.filter((r) => r.isActive))
      setDocs(existing)
    } catch (e) {
      setLoadError(e instanceof Error ? e.message : "Failed to load")
      setManualMode(true)
    }
    setLoading(false)
  }, [assignmentId, partnerTypeId])
  useEffect(() => { load() }, [load])

  function getDocForRequirement(reqId: string): PartnerDocument | undefined {
    return docs.find((d) => d.documentRequirement === reqId)
  }

  async function handleFilePick(reqId: string, file: File) {
    setUploading(reqId)
    try {
      await uploadAssignmentDocumentFile(assignmentId, reqId, file)
      load()
      onRefresh()
    } catch {}
    setUploading(null)
  }

  async function handleManualUpload() {
    if (!manualReqId || !manualFileRef.current?.files?.[0]) return
    setUploading("manual")
    try {
      await uploadAssignmentDocumentFile(assignmentId, manualReqId, manualFileRef.current.files[0])
      setManualReqId("")
      if (manualFileRef.current) manualFileRef.current.value = ""
      load()
      onRefresh()
    } catch {}
    setUploading(null)
  }

  async function handleVerify(docId: string) {
    try {
      await updateAssignmentDocument(assignmentId, docId, { status: "APPROVED" })
      load()
      onRefresh()
    } catch {}
  }

  async function handleReject(docId: string) {
    try {
      await updateAssignmentDocument(assignmentId, docId, { status: "REJECTED" })
      load()
      onRefresh()
    } catch {}
  }

  if (loading) return <Loader2 className="h-5 w-5 animate-spin text-muted-foreground mx-auto" />

  const activeReqs = requirements.filter((r) => r.isActive)

  return (
    <div className="space-y-3">
      {loadError && (
        <div className="p-2 rounded bg-[var(--color-bg-warning-soft)] text-xs text-[var(--color-text-warning-soft)]">
          {loadError}
        </div>
      )}

      {activeReqs.length > 0 ? (
        <div className="space-y-2">
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Required Documents</p>
          {activeReqs.map((req) => {
            const doc = getDocForRequirement(req.id)
            return (
              <div key={req.id} className="flex items-center justify-between rounded-lg border border-border px-4 py-3">
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-foreground">{req.description || req.code}</p>
                  <p className="text-xs text-muted-foreground mt-0.5">{req.code}{req.isMandatory ? " · Required" : " · Optional"}</p>
                </div>
                <div className="flex items-center gap-3 flex-none ml-4">
                  {doc ? (
                    <>
                      <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium ${
                        doc.status === "APPROVED" ? "bg-[var(--color-bg-success-soft)] text-[var(--color-text-success-soft)]" :
                        doc.status === "REJECTED" || doc.status === "EXPIRED" ? "bg-[var(--color-bg-destructive-soft)] text-[var(--color-text-destructive-soft)]" :
                        "bg-[var(--color-bg-warning-soft)] text-[var(--color-text-warning-soft)]"
                      }`}>{doc.status}</span>
                      {doc.status === "UPLOADED" || doc.status === "NOT_SUBMITTED" ? (
                        <>
                          <button onClick={() => handleVerify(doc.id)} className="p-1 text-[var(--color-feedback-success)] hover:bg-[var(--color-bg-success-soft)] rounded" title="Approve"><CheckCircle className="h-4 w-4" /></button>
                          <button onClick={() => handleReject(doc.id)} className="p-1 text-[var(--color-feedback-destructive)] hover:bg-[var(--color-bg-destructive-soft)] rounded" title="Reject"><XCircle className="h-4 w-4" /></button>
                        </>
                      ) : null}
                    </>
                  ) : (
                    <>
                      <input type="file" ref={(el) => { fileRefs.current[req.id] = el }} onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFilePick(req.id, f) }} className="hidden" accept=".pdf,.jpg,.jpeg,.png" />
                      <button onClick={() => fileRefs.current[req.id]?.click()} disabled={uploading === req.id} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary text-primary-foreground text-xs font-medium hover:bg-primary/90 disabled:opacity-50 transition-colors">
                        {uploading === req.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Upload className="h-3.5 w-3.5" />}
                        Upload
                      </button>
                    </>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      ) : !loadError ? (
        <p className="text-sm text-muted-foreground text-center py-4">No document requirements configured for this partner type.</p>
      ) : null}

      {manualMode && (
        <div className="border-t border-border pt-3 mt-3">
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">Upload by Document ID</p>
          <div className="flex items-center gap-2">
            <input value={manualReqId} onChange={(e) => setManualReqId(e.target.value)} placeholder="Document Requirement UUID" className="flex-1 rounded border border-input bg-card px-2 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50" />
            <input type="file" ref={manualFileRef} className="hidden" accept=".pdf,.jpg,.jpeg,.png" />
            <button onClick={() => manualFileRef.current?.click()} className="px-2 py-1.5 rounded border border-input text-xs text-foreground hover:bg-muted">Choose File</button>
            <button onClick={handleManualUpload} disabled={uploading === "manual" || !manualReqId} className="flex items-center gap-1 px-3 py-1.5 rounded bg-primary text-primary-foreground text-xs font-medium hover:bg-primary/90 disabled:opacity-50">
              {uploading === "manual" ? <Loader2 className="h-3 w-3 animate-spin" /> : <Upload className="h-3 w-3" />}
              Upload
            </button>
          </div>
        </div>
      )}

      {docs.length > 0 && (
        <div className="border-t border-border pt-3 mt-3">
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">All Uploaded Documents ({docs.length})</p>
          <div className="space-y-1">
            {docs.map((doc) => (
              <div key={doc.id} className="flex items-center justify-between rounded border border-border px-3 py-2 text-xs">
                <span className="text-foreground truncate">{doc.documentRequirementName || doc.documentRequirementCode || doc.id}</span>
                <span className={`ml-2 px-1.5 py-0.5 rounded text-[10px] font-medium flex-none ${
                  doc.status === "APPROVED" ? "bg-[var(--color-bg-success-soft)] text-[var(--color-text-success-soft)]" :
                  doc.status === "REJECTED" || doc.status === "EXPIRED" ? "bg-[var(--color-bg-destructive-soft)] text-[var(--color-text-destructive-soft)]" :
                  "bg-[var(--color-bg-warning-soft)] text-[var(--color-text-warning-soft)]"
                }`}>{doc.status}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function FieldsTab({ assignmentId, onRefresh }: { assignmentId: string; onRefresh: () => void }) {
  const [fields, setFields] = useState<PartnerDynamicFieldValue[]>([])
  const [loading, setLoading] = useState(true)
  const load = useCallback(async () => {
    setLoading(true)
    try { setFields(await getAssignmentFieldValues(assignmentId)) } catch {}
    setLoading(false)
  }, [assignmentId])
  useEffect(() => { load() }, [load])

  const [editValues, setEditValues] = useState<Record<string, string>>({})
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    const ev: Record<string, string> = {}
    for (const f of fields) {
      const v = f.valueJson
      ev[f.id] = typeof v === "object" && v !== null ? String((v as Record<string, unknown>).value ?? "") : String(v ?? "")
    }
    setEditValues(ev)
  }, [fields])

  async function handleSave() {
    setSaving(true)
    try {
      const payload = fields.map((f) => ({
        field_config: f.fieldConfig,
        value_json: { value: editValues[f.id] ?? "" },
      }))
      await updateAssignmentFieldValues(assignmentId, payload)
      load()
      onRefresh()
    } catch {}
    setSaving(false)
  }

  if (loading) return <Loader2 className="h-5 w-5 animate-spin text-muted-foreground mx-auto" />

  return (
    <div className="space-y-3">
      {fields.map((f) => (
        <div key={f.id} className="flex items-center gap-3">
          <span className="text-sm text-foreground w-40 flex-none">{f.fieldName || f.fieldCode}</span>
          <input
            type={f.fieldType === "DATE" ? "date" : "text"}
            value={editValues[f.id] ?? ""}
            onChange={(e) => setEditValues((ev) => ({ ...ev, [f.id]: e.target.value }))}
            className="flex-1 rounded border border-input bg-card px-2 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50"
          />
          <span className="text-[10px] text-muted-foreground w-16 text-right">{f.fieldType}</span>
        </div>
      ))}
      {fields.length === 0 && <p className="text-sm text-muted-foreground text-center py-4">No dynamic fields configured.</p>}
      {fields.length > 0 && (
        <div className="flex justify-end pt-2">
          <button onClick={handleSave} disabled={saving} className="flex items-center gap-1 px-3 py-1.5 rounded bg-primary text-primary-foreground text-xs font-medium hover:bg-primary/90 disabled:opacity-50">
            {saving ? <Loader2 className="h-3 w-3 animate-spin" /> : <CheckCircle className="h-3 w-3" />}
            Save Fields
          </button>
        </div>
      )}
    </div>
  )
}

function ContactsTab({ assignmentId, onRefresh }: { assignmentId: string; onRefresh: () => void }) {
  const [contacts, setContacts] = useState<PartnerAssignmentContact[]>([])
  const [loading, setLoading] = useState(true)
  const load = useCallback(async () => {
    setLoading(true)
    try { setContacts(await getAssignmentContacts(assignmentId)) } catch {}
    setLoading(false)
  }, [assignmentId])
  useEffect(() => { load() }, [load])

  const [newContact, setNewContact] = useState({ contact_requirement: "", contact_type: "OTHER", first_name: "", last_name: "", email: "", phone: "", mobile: "", designation: "", is_primary: false, notes: "" })
  const [saving, setSaving] = useState(false)
  const [showForm, setShowForm] = useState(false)

  async function handleAdd() {
    if (!newContact.first_name) return
    setSaving(true)
    try {
      await createAssignmentContact(assignmentId, newContact)
      setNewContact({ contact_requirement: "", contact_type: "OTHER", first_name: "", last_name: "", email: "", phone: "", mobile: "", designation: "", is_primary: false, notes: "" })
      setShowForm(false)
      load()
      onRefresh()
    } catch {}
    setSaving(false)
  }

  async function handleDelete(contactId: string) {
    try { await deleteAssignmentContact(assignmentId, contactId); load(); onRefresh() } catch {}
  }

  if (loading) return <Loader2 className="h-5 w-5 animate-spin text-muted-foreground mx-auto" />

  return (
    <div className="space-y-3">
      <div className="flex justify-end">
        <button onClick={() => setShowForm(!showForm)} className="flex items-center gap-1 px-3 py-1.5 rounded bg-primary text-primary-foreground text-xs font-medium hover:bg-primary/90">
          <Plus className="h-3 w-3" />
          Add Contact
        </button>
      </div>

      {showForm && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 p-3 rounded-lg border border-border bg-muted/20">
          <input placeholder="First Name *" value={newContact.first_name} onChange={(e) => setNewContact((d) => ({ ...d, first_name: e.target.value }))} className="rounded border border-input bg-card px-2 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50" />
          <input placeholder="Last Name" value={newContact.last_name} onChange={(e) => setNewContact((d) => ({ ...d, last_name: e.target.value }))} className="rounded border border-input bg-card px-2 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50" />
          <input placeholder="Email" value={newContact.email} onChange={(e) => setNewContact((d) => ({ ...d, email: e.target.value }))} className="rounded border border-input bg-card px-2 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50" />
          <input placeholder="Phone" value={newContact.phone} onChange={(e) => setNewContact((d) => ({ ...d, phone: e.target.value }))} className="rounded border border-input bg-card px-2 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50" />
          <input placeholder="Mobile" value={newContact.mobile} onChange={(e) => setNewContact((d) => ({ ...d, mobile: e.target.value }))} className="rounded border border-input bg-card px-2 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50" />
          <input placeholder="Designation" value={newContact.designation} onChange={(e) => setNewContact((d) => ({ ...d, designation: e.target.value }))} className="rounded border border-input bg-card px-2 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50" />
          <div className="flex items-center gap-2">
            <input type="checkbox" id="isPrimary" checked={newContact.is_primary} onChange={(e) => setNewContact((d) => ({ ...d, is_primary: e.target.checked }))} className="rounded border-border" />
            <label htmlFor="isPrimary" className="text-xs text-foreground">Is Primary</label>
          </div>
          <button onClick={handleAdd} disabled={saving || !newContact.first_name} className="flex items-center gap-1 px-3 py-1.5 rounded bg-primary text-primary-foreground text-xs font-medium hover:bg-primary/90 disabled:opacity-50">
            {saving ? <Loader2 className="h-3 w-3 animate-spin" /> : <Plus className="h-3 w-3" />}
            Save Contact
          </button>
        </div>
      )}

      <div className="space-y-2">
        {contacts.map((c) => (
          <div key={c.id} className="flex items-center justify-between rounded-lg border border-border px-3 py-2 text-sm">
            <div className="flex-1 min-w-0">
              <p className="font-medium text-foreground">{c.firstName} {c.lastName}</p>
              <p className="text-xs text-muted-foreground">{c.email} · {c.phone || c.mobile || "—"}{c.isPrimary ? " · PRIMARY" : ""}</p>
              <p className="text-xs text-muted-foreground">{c.contactType}{c.designation ? ` · ${c.designation}` : ""}</p>
            </div>
            <button onClick={() => handleDelete(c.id)} className="p-1 text-muted-foreground hover:text-destructive rounded flex-none ml-2" title="Delete">
              <Trash2 className="h-3.5 w-3.5" />
            </button>
          </div>
        ))}
        {contacts.length === 0 && <p className="text-sm text-muted-foreground text-center py-4">No contacts added yet.</p>}
      </div>
    </div>
  )
}

function BanksTab({ assignmentId, onRefresh }: { assignmentId: string; onRefresh: () => void }) {
  const [banks, setBanks] = useState<PartnerAssignmentBankAccount[]>([])
  const [loading, setLoading] = useState(true)
  const load = useCallback(async () => {
    setLoading(true)
    try { setBanks(await getAssignmentBankAccounts(assignmentId)) } catch {}
    setLoading(false)
  }, [assignmentId])
  useEffect(() => { load() }, [load])

  const [newBank, setNewBank] = useState({ bank_requirement: "", bank_type: "SAVINGS", bank_name: "", branch_name: "", account_name: "", account_number: "", swift_code: "", currency: "TZS", is_primary: false, notes: "" })
  const [saving, setSaving] = useState(false)
  const [showForm, setShowForm] = useState(false)

  async function handleAdd() {
    if (!newBank.bank_name || !newBank.account_name) return
    setSaving(true)
    try {
      await createAssignmentBankAccount(assignmentId, newBank)
      setNewBank({ bank_requirement: "", bank_type: "SAVINGS", bank_name: "", branch_name: "", account_name: "", account_number: "", swift_code: "", currency: "TZS", is_primary: false, notes: "" })
      setShowForm(false)
      load()
      onRefresh()
    } catch {}
    setSaving(false)
  }

  async function handleDelete(bankId: string) {
    try { await deleteAssignmentBankAccount(assignmentId, bankId); load(); onRefresh() } catch {}
  }

  if (loading) return <Loader2 className="h-5 w-5 animate-spin text-muted-foreground mx-auto" />

  return (
    <div className="space-y-3">
      <div className="flex justify-end">
        <button onClick={() => setShowForm(!showForm)} className="flex items-center gap-1 px-3 py-1.5 rounded bg-primary text-primary-foreground text-xs font-medium hover:bg-primary/90">
          <Plus className="h-3 w-3" />
          Add Bank Account
        </button>
      </div>

      {showForm && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 p-3 rounded-lg border border-border bg-muted/20">
          <input placeholder="Bank Name *" value={newBank.bank_name} onChange={(e) => setNewBank((d) => ({ ...d, bank_name: e.target.value }))} className="rounded border border-input bg-card px-2 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50" />
          <input placeholder="Branch" value={newBank.branch_name} onChange={(e) => setNewBank((d) => ({ ...d, branch_name: e.target.value }))} className="rounded border border-input bg-card px-2 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50" />
          <input placeholder="Account Name *" value={newBank.account_name} onChange={(e) => setNewBank((d) => ({ ...d, account_name: e.target.value }))} className="rounded border border-input bg-card px-2 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50" />
          <input placeholder="Account Number" value={newBank.account_number} onChange={(e) => setNewBank((d) => ({ ...d, account_number: e.target.value }))} className="rounded border border-input bg-card px-2 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50" />
          <input placeholder="SWIFT Code" value={newBank.swift_code} onChange={(e) => setNewBank((d) => ({ ...d, swift_code: e.target.value }))} className="rounded border border-input bg-card px-2 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50" />
          <input placeholder="Currency" value={newBank.currency} onChange={(e) => setNewBank((d) => ({ ...d, currency: e.target.value }))} className="rounded border border-input bg-card px-2 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50" />
          <div className="flex items-center gap-2">
            <input type="checkbox" id="isPrimaryBank" checked={newBank.is_primary} onChange={(e) => setNewBank((d) => ({ ...d, is_primary: e.target.checked }))} className="rounded border-border" />
            <label htmlFor="isPrimaryBank" className="text-xs text-foreground">Is Primary</label>
          </div>
          <button onClick={handleAdd} disabled={saving || !newBank.bank_name || !newBank.account_name} className="flex items-center gap-1 px-3 py-1.5 rounded bg-primary text-primary-foreground text-xs font-medium hover:bg-primary/90 disabled:opacity-50">
            {saving ? <Loader2 className="h-3 w-3 animate-spin" /> : <Plus className="h-3 w-3" />}
            Save Bank
          </button>
        </div>
      )}

      <div className="space-y-2">
        {banks.map((b) => (
          <div key={b.id} className="flex items-center justify-between rounded-lg border border-border px-3 py-2 text-sm">
            <div className="flex-1 min-w-0">
              <p className="font-medium text-foreground">{b.bankName} · {b.accountName}</p>
              <p className="text-xs text-muted-foreground">{b.accountNumber}{b.swiftCode ? ` · SWIFT ${b.swiftCode}` : ""} · {b.currency}{b.isPrimary ? " · PRIMARY" : ""}</p>
              {b.branchName && <p className="text-xs text-muted-foreground">{b.branchName}</p>}
            </div>
            <button onClick={() => handleDelete(b.id)} className="p-1 text-muted-foreground hover:text-destructive rounded flex-none ml-2" title="Delete">
              <Trash2 className="h-3.5 w-3.5" />
            </button>
          </div>
        ))}
        {banks.length === 0 && <p className="text-sm text-muted-foreground text-center py-4">No bank accounts added yet.</p>}
      </div>
    </div>
  )
}

function KYCTab({ assignmentId, onRefresh }: { assignmentId: string; onRefresh: () => void }) {
  const [kyc, setKYC] = useState<PartnerKYCProfile | null>(null)
  const [loading, setLoading] = useState(true)
  const load = useCallback(async () => {
    setLoading(true)
    try { setKYC(await getAssignmentKYC(assignmentId)) } catch {}
    setLoading(false)
  }, [assignmentId])
  useEffect(() => { load() }, [load])

  const [kycStatus, setKycStatus] = useState("NOT_SET")
  const [notes, setNotes] = useState("")
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (kyc) {
      setKycStatus(kyc.kycStatus)
      setNotes(kyc.notes ?? "")
    }
  }, [kyc])

  async function handleSave() {
    setSaving(true)
    try {
      await updateAssignmentKYC(assignmentId, {
        kyc_status: kycStatus,
        last_review_date: new Date().toISOString(),
        notes,
      })
      load()
      onRefresh()
    } catch {}
    setSaving(false)
  }

  if (loading) return <Loader2 className="h-5 w-5 animate-spin text-muted-foreground mx-auto" />

  return (
    <div className="space-y-4">
      {kyc && (
        <div className="grid grid-cols-3 gap-4 mb-4">
          <div className="text-center p-3 rounded-lg border border-border">
            <p className="text-2xl font-bold text-foreground">{kyc.riskScore ?? "—"}</p>
            <p className="text-xs text-muted-foreground">Risk Score</p>
          </div>
          <div className="text-center p-3 rounded-lg border border-border">
            <p className="text-2xl font-bold text-foreground">{kyc.riskLevel || "—"}</p>
            <p className="text-xs text-muted-foreground">Risk Level</p>
          </div>
          <div className="text-center p-3 rounded-lg border border-border">
            <p className="text-lg font-bold text-foreground">{kyc.lastReviewDate ? new Date(kyc.lastReviewDate).toLocaleDateString() : "—"}</p>
            <p className="text-xs text-muted-foreground">Last Review</p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label className="block text-xs font-medium text-foreground mb-1">KYC Status</label>
          <select
            value={kycStatus}
            onChange={(e) => setKycStatus(e.target.value)}
            className="w-full rounded-lg border border-input bg-card px-2.5 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50"
          >
            <option value="NOT_SET">Not Set</option>
            <option value="PENDING">Pending</option>
            <option value="CLEARED">Cleared</option>
            <option value="REJECTED">Rejected</option>
            <option value="ESCALATED">Escalated</option>
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium text-foreground mb-1">Notes</label>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={2}
            className="w-full rounded-lg border border-input bg-card px-2.5 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50"
          />
        </div>
      </div>

      <div className="flex justify-end">
        <button
          onClick={handleSave}
          disabled={saving}
          className="flex items-center gap-1 px-3 py-1.5 rounded bg-primary text-primary-foreground text-xs font-medium hover:bg-primary/90 disabled:opacity-50"
        >
          {saving ? <Loader2 className="h-3 w-3 animate-spin" /> : <CheckCircle className="h-3 w-3" />}
          Update KYC
        </button>
      </div>
    </div>
  )
}

function Field({ label, value }: { label: string; value?: string | null }) {
  return (
    <div className="text-sm">
      <span className="text-muted-foreground">{label}</span>
      <p className="text-foreground mt-0.5">{value || "-"}</p>
    </div>
  )
}

function MiniProgress({ label, pct }: { label: string; pct: number }) {
  return (
    <div className="text-center">
      <p className="text-xs font-medium text-foreground">{pct}%</p>
      <div className="mt-0.5 h-1 w-full rounded-full bg-[var(--color-bg-muted)] overflow-hidden">
        <div
          className="h-full rounded-full"
          style={{
            width: `${pct}%`,
            backgroundColor: pct >= 80
              ? "var(--color-feedback-success)"
              : pct >= 50
                ? "var(--color-feedback-warning)"
                : "var(--color-feedback-info)",
          }}
        />
      </div>
      <p className="text-[10px] text-muted-foreground mt-0.5">{label}</p>
    </div>
  )
}

function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return "-"
  return new Date(dateStr).toLocaleDateString("en-US", {
    year: "numeric", month: "short", day: "numeric",
    hour: "2-digit", minute: "2-digit",
  })
}
