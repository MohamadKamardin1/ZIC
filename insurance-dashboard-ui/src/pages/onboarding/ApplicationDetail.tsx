import { useCallback, useEffect, useRef, useState } from "react"
import { useNavigate, useParams } from "react-router-dom"
import {
  ArrowLeft, Plus, Trash2, Loader2, X, Search, Eye, RefreshCw, Save,
  User, Building2, Landmark, Phone, Mail, MapPin, Send, CheckCircle2,
  XCircle, AlertTriangle, Shield, FileCheck, Pencil,
} from "lucide-react"
import {
  getApplication,
  listPartnerTypes,
  createPartnerType,
  updatePartnerType,
  deletePartnerType,
  listContacts,
  listBankAccounts,
  getChoices,
  uploadDocument,
  deleteDocument,
  verifyDocument,
  requestDocuments,
  submitApplication,
  startReview,
  sendToCompliance,
  approveApplication,
  rejectApplication,
  suspendApplication,
  resumeApplication,
  convertApplication,
  runCompliance,
} from "../../lib/api"
import type {
  PartnerApplicationDetail,
  ApplicationPartnerType,
  ApplicationContact,
  ApplicationBankAccount,
  ChoicesResponse,
} from "../../lib/types"
import { useStatusLabel, useStatusColor } from "../../config/ConfigurationHooks"
import { useLitProps } from "../../lib/useLitProps"
import FlowBanner from "../../components/shared/FlowBanner"
import ConfirmDialog from "../../components/shared/ConfirmDialog"

const LIFECYCLE: Record<string, { label: string; status: "completed" | "active" | "pending" | "rejected" }[]> = {
  ACTIVE: [
    { label: "Draft", status: "active" },
    { label: "Submitted", status: "pending" },
    { label: "Review", status: "pending" },
    { label: "Compliance", status: "pending" },
    { label: "Decision", status: "pending" },
  ],
  SUBMITTED: [
    { label: "Draft", status: "completed" },
    { label: "Submitted", status: "active" },
    { label: "Review", status: "pending" },
    { label: "Compliance", status: "pending" },
    { label: "Decision", status: "pending" },
  ],
  UNDER_REVIEW: [
    { label: "Draft", status: "completed" },
    { label: "Submitted", status: "completed" },
    { label: "Review", status: "active" },
    { label: "Compliance", status: "pending" },
    { label: "Decision", status: "pending" },
  ],
  PENDING_DOCUMENTS: [
    { label: "Draft", status: "completed" },
    { label: "Submitted", status: "completed" },
    { label: "Review", status: "active" },
    { label: "Compliance", status: "pending" },
    { label: "Decision", status: "pending" },
  ],
  COMPLIANCE_CHECK: [
    { label: "Draft", status: "completed" },
    { label: "Submitted", status: "completed" },
    { label: "Review", status: "completed" },
    { label: "Compliance", status: "active" },
    { label: "Decision", status: "pending" },
  ],
  APPROVED: [
    { label: "Draft", status: "completed" },
    { label: "Submitted", status: "completed" },
    { label: "Review", status: "completed" },
    { label: "Compliance", status: "completed" },
    { label: "Approved", status: "active" },
  ],
  REJECTED: [
    { label: "Draft", status: "completed" },
    { label: "Submitted", status: "completed" },
    { label: "Review", status: "completed" },
    { label: "Compliance", status: "completed" },
    { label: "Rejected", status: "rejected" },
  ],
  SUSPENDED: [
    { label: "Draft", status: "completed" },
    { label: "Submitted", status: "completed" },
    { label: "Review", status: "completed" },
    { label: "Suspended", status: "rejected" },
    { label: "Decision", status: "pending" },
  ],
  CONVERTED: [
    { label: "Draft", status: "completed" },
    { label: "Submitted", status: "completed" },
    { label: "Review", status: "completed" },
    { label: "Compliance", status: "completed" },
    { label: "Converted", status: "active" },
  ],
}

export default function ApplicationDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const [app, setApp] = useState<PartnerApplicationDetail | null>(null)
  const [partnerTypes, setPartnerTypes] = useState<ApplicationPartnerType[]>([])
  const [contacts, setContacts] = useState<ApplicationContact[]>([])
  const [bankAccounts, setBankAccounts] = useState<ApplicationBankAccount[]>([])
  const [documents, setDocuments] = useState<PartnerApplicationDetail["documents"]>([])
  const [choices, setChoices] = useState<ChoicesResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [workflowBusy, setWorkflowBusy] = useState(false)
  const [documentUploading, setDocumentUploading] = useState(false)
  const [error, setError] = useState("")
  const [subTab, setSubTab] = useState<"types" | "contacts" | "banks">("types")

  /* Confirm dialog state */
  const timelineRef = useLitProps<HTMLElement>({ status: app?.status ?? "DRAFT", applicationNumber: app?.applicationNumber ?? "" })
  const eventFeedRef = useLitProps<HTMLElement>({ events: app?.events ?? [], loading })
  const documentPanelRef = useLitProps<HTMLElement>({
    documents,
    documentTypes: choices?.documentTypes ?? [],
    canUpload: app?.status === "ACTIVE" || app?.status === "DRAFT" || app?.status === "PENDING_DOCUMENTS",
    canVerify: app?.status === "UNDER_REVIEW" || app?.status === "PENDING_DOCUMENTS" || app?.status === "COMPLIANCE_CHECK",
    uploading: documentUploading,
  })
  const workflowRef = useLitProps<HTMLElement>({
    status: app?.status ?? "DRAFT",
    canEdit: app?.status === "ACTIVE" || app?.status === "DRAFT",
    busy: workflowBusy,
  })

  const [confirmAction, setConfirmAction] = useState<{
    title: string
    message: string
    action: () => Promise<void>
  } | null>(null)

  const load = useCallback(async () => {
    if (!id) return
    setLoading(true)
    setError("")
    try {
      const [appData, pts, cts, bks, chs] = await Promise.all([
        getApplication(id),
        listPartnerTypes(id),
        listContacts(id),
        listBankAccounts(id),
        getChoices(),
      ])
      setApp(appData)
      setDocuments(appData.documents ?? [])
      setPartnerTypes(pts)
      setContacts(cts)
      setBankAccounts(bks)
      setChoices(chs)
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load")
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => { load() }, [load])

  useEffect(() => {
    const element = workflowRef.current
    if (!element) return
    const onWorkflowAction = (event: Event) => {
      const action = (event as CustomEvent<{ action: string }>).detail?.action
      if (!id || !action) return
      if (action === "edit") { navigate(`/onboarding/${id}/edit`); return }
      if (action === "submit") return confirmThen(() => submitApplication(id), "Submit Application", "Submit this application for review? Editing will be locked after submission.")
      if (action === "review") return confirmThen(() => startReview(id), "Start Review", "Begin reviewing this application?")
      if (action === "request_documents") {
        const requested = window.prompt("Enter requested document types, separated by commas:", choices?.documentTypes?.slice(0, 2).map((item) => item.label).join(", ") || "")
        if (requested === null) return
        const values = requested.split(",").map((value) => value.trim()).filter(Boolean)
        if (!values.length) { setError("At least one document must be requested."); return }
        return confirmThen(() => requestDocuments(id, values), "Request Documents", "Create document tasks for the selected evidence?")
      }
      if (action === "send_to_compliance") return confirmThen(() => sendToCompliance(id), "Send to Compliance", "Send this application for compliance review?")
      if (action === "run_compliance") return handleAction(async () => { await runCompliance(id) })
      if (action === "approve") return confirmThen(() => approveApplication(id), "Approve Application", "Approve this application?")
      if (action === "reject") {
        const reason = window.prompt("Rejection reason:", "Rejected during review")
        if (reason === null) return
        return confirmThen(() => rejectApplication(id, reason), "Reject Application", "Reject this application? This decision will be recorded in the event history.")
      }
      if (action === "suspend") return confirmThen(() => suspendApplication(id), "Suspend Application", "Suspend this application?")
      if (action === "resume") return confirmThen(() => resumeApplication(id), "Resume Application", "Resume this application?")
      if (action === "convert") return confirmThen(() => convertApplication(id), "Convert to Partner", "Create the partner record from this approved application?")
    }
    element.addEventListener("onboarding-workflow-action", onWorkflowAction)
    return () => element.removeEventListener("onboarding-workflow-action", onWorkflowAction)
  }, [id, navigate, choices])

  useEffect(() => {
    const element = documentPanelRef.current
    if (!element) return
    const onUpload = async (event: Event) => {
      const detail = (event as CustomEvent<{ file: File; documentType: string }>).detail
      if (!id || !detail?.file || !detail.documentType) return
      setDocumentUploading(true)
      setError("")
      try { await uploadDocument(id, detail.file, detail.documentType); await load() }
      catch (reason) { setError(reason instanceof Error ? reason.message : "Document upload failed") }
      finally { setDocumentUploading(false) }
    }
    const onDocumentAction = (event: Event) => {
      const detail = (event as CustomEvent<{ action: string; document: { id: string; documentName?: string } }>).detail
      if (!id || !detail?.document?.id) return
      if (detail.action === "verify") return handleAction(() => verifyDocument(id, detail.document.id))
      if (detail.action === "delete") return confirmThen(() => deleteDocument(id, detail.document.id), "Remove Document", `Remove ${detail.document.documentName || "this document"}?`)
    }
    const onDocumentError = (event: Event) => setError((event as CustomEvent<{ message: string }>).detail?.message || "Document action failed")
    element.addEventListener("onboarding-document-upload", onUpload)
    element.addEventListener("onboarding-document-action", onDocumentAction)
    element.addEventListener("onboarding-document-error", onDocumentError)
    return () => {
      element.removeEventListener("onboarding-document-upload", onUpload)
      element.removeEventListener("onboarding-document-action", onDocumentAction)
      element.removeEventListener("onboarding-document-error", onDocumentError)
    }
  }, [id, load])

  /* ── Hooks that must be called before early returns ── */
  const statusLabel = useStatusLabel(app?.status ?? "DRAFT")
  const lifecycleSteps = LIFECYCLE[app?.status ?? "DRAFT"] ?? LIFECYCLE.ACTIVE

  async function handleDeletePartnerType(ptId: string) {
    if (!id) return
    try {
      await deletePartnerType(id, ptId)
      setPartnerTypes((prev) => prev.filter((p) => p.id !== ptId))
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete partner type")
    }
  }

  /* ---- Action Handlers ---- */
  async function handleAction(action: () => Promise<unknown>) {
    setError("")
    setWorkflowBusy(true)
    try {
      await action()
      await load()
    } catch (e) {
      setError(e instanceof Error ? e.message : "Action failed")
    } finally {
      setWorkflowBusy(false)
      setConfirmAction(null)
    }
  }

  function confirmThen(action: () => Promise<unknown>, title: string, message: string) {
    setConfirmAction({
      title,
      message,
      action: () => handleAction(action),
    })
  }

  if (loading && !app) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (!app) {
    return (
      <div className="rounded-xl border border-destructive/30 bg-destructive/5 px-4 py-8 text-center text-sm font-medium text-destructive">
        Application not found.
      </div>
    )
  }

  /* ---- Action Buttons Config ---- */
  function getNextAction() {
    const s = app!.status
    if (s === "ACTIVE" || s === "DRAFT") {
      return {
        label: "Submit Application",
        onClick: () => confirmThen(
          () => submitApplication(id!),
          "Submit Application",
          "Are you sure you want to submit this application for review? You won't be able to edit it after submission.",
        ),
      }
    }
    if (s === "SUBMITTED") {
      return {
        label: "Start Review",
        onClick: () => confirmThen(
          () => startReview(id!),
          "Start Review",
          "Begin reviewing this application?",
        ),
      }
    }
    if (s === "UNDER_REVIEW" || s === "PENDING_DOCUMENTS") {
      return {
        label: "Send to Compliance",
        onClick: () => confirmThen(
          () => sendToCompliance(id!),
          "Send to Compliance",
          "Send this application for compliance check?",
        ),
      }
    }
    if (s === "COMPLIANCE_CHECK") {
      return {
        label: "Approve Application",
        onClick: () => confirmThen(
          () => approveApplication(id!),
          "Approve Application",
          "Are you sure you want to approve this application?",
        ),
      }
    }
    if (s === "APPROVED") {
      return {
        label: "Convert to Partner",
        onClick: () => confirmThen(
          () => convertApplication(id!),
          "Convert to Partner",
          "This will create a partner record from this application. Continue?",
        ),
      }
    }
    if (s === "SUSPENDED") {
      return {
        label: "Resume Application",
        onClick: () => confirmThen(
          () => resumeApplication(id!),
          "Resume Application",
          "Resume this application back to compliance check?",
        ),
      }
    }
    return null
  }

  function getSecondaryActions() {
    const s = app!.status
    const actions: { label: string; icon: React.ReactNode; onClick: () => void; variant: "danger" | "warning" }[] = []

    if (s === "COMPLIANCE_CHECK") {
      actions.push({
        label: "Reject",
        icon: <XCircle className="h-3.5 w-3.5" />,
        onClick: () => confirmThen(
          () => rejectApplication(id!, "Rejected during compliance"),
          "Reject Application",
          "Are you sure you want to reject this application?",
        ),
        variant: "danger",
      })
      actions.push({
        label: "Suspend",
        icon: <AlertTriangle className="h-3.5 w-3.5" />,
        onClick: () => confirmThen(
          () => suspendApplication(id!),
          "Suspend Application",
          "Are you sure you want to suspend this application?",
        ),
        variant: "warning",
      })
    }

    if (s === "UNDER_REVIEW" || s === "PENDING_DOCUMENTS") {
      actions.push({
        label: "Reject",
        icon: <XCircle className="h-3.5 w-3.5" />,
        onClick: () => confirmThen(
          () => rejectApplication(id!, "Rejected during review"),
          "Reject Application",
          "Are you sure you want to reject this application?",
        ),
        variant: "danger",
      })
    }

    return actions
  }

  const nextAction = getNextAction()
  const secondaryActions = getSecondaryActions()

  return (
    <div className="flex flex-col gap-5">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-1.5 text-sm text-muted-foreground">
        <button onClick={() => navigate("/")} className="font-medium text-primary hover:underline">Home</button>
        <span>/</span>
        <button onClick={() => navigate("/onboarding")} className="font-medium text-primary hover:underline">Partner</button>
        <span>/</span>
        <span className="text-foreground">View Partner</span>
      </nav>

      {error && (
        <div className="rounded-xl border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm font-medium text-destructive">
          {error}
        </div>
      )}

      <onboarding-status-timeline ref={timelineRef} />

      {/* Flow Banner */}
      <FlowBanner
        title={`Application ${app.applicationNumber} — ${statusLabel}`}
        steps={lifecycleSteps}
        nextAction={undefined}
      />

      <div className="rounded-xl border border-border bg-card px-4 py-3">
        <onboarding-workflow-actions ref={workflowRef} />
      </div>

      {/* ===== TABLE 1: User Info ===== */}
      <div className="rounded-xl border border-border bg-card">
        <div className="flex items-center gap-3 border-b border-border px-5 py-3">
          <button
            onClick={() => navigate("/onboarding")}
            className="rounded-lg p-1.5 text-muted-foreground transition hover:bg-secondary hover:text-foreground"
          >
            <ArrowLeft className="h-4 w-4" />
          </button>
          {app.partnerType === "INDIVIDUAL" ? (
            <User className="h-5 w-5 text-muted-foreground" />
          ) : (
            <Building2 className="h-5 w-5 text-muted-foreground" />
          )}
          <h2 className="text-base font-semibold text-foreground">Partner Information</h2>
          <StatusBadge status={app.status} />
        </div>
        <div className="p-5">
          {app.partnerType === "INDIVIDUAL" ? (
            <InfoTable
              rows={[
                { label: "Application No", value: app.applicationNumber },
                { label: "Full Name", value: `${app.title} ${app.firstName} ${app.otherName} ${app.surname}`.trim() },
                { label: "Partner Type", value: "Individual" },
                { label: "ID Type", value: app.identificationType || "—" },
                { label: "ID Number", value: app.identificationNumber || "—" },
                { label: "Gender", value: app.gender || "—" },
                { label: "Date of Birth", value: app.dateOfBirth || "—" },
                { label: "Marital Status", value: app.maritalStatus || "—" },
                { label: "Occupation", value: app.occupation || "—" },
                { label: "Nationality", value: app.nationality || "—" },
                { label: "Email", value: app.email },
                { label: "Mobile", value: app.mobileNumber },
                { label: "Telephone", value: app.telephoneNumber || "—" },
                { label: "Physical Address", value: app.physicalAddress || "—" },
                { label: "Postal Address", value: app.postalAddress || "—" },
              ]}
            />
          ) : (
            <InfoTable
              rows={[
                { label: "Application No", value: app.applicationNumber },
                { label: "Company Name", value: app.companyName || "—" },
                { label: "Partner Type", value: "Corporate" },
                { label: "TIN", value: app.tinNumber || "—" },
                { label: "Incorporation Date", value: app.incorporationDate || "—" },
                { label: "Industry", value: app.industry || "—" },
                { label: "Contact Person", value: app.contactPerson || "—" },
                { label: "Contact Phone", value: app.contactPersonPhone || "—" },
                { label: "Contact Email", value: app.contactPersonEmail || "—" },
                { label: "Email", value: app.email },
                { label: "Mobile", value: app.mobileNumber },
                { label: "Telephone", value: app.telephoneNumber || "—" },
                { label: "Physical Address", value: app.physicalAddress || "—" },
                { label: "Postal Address", value: app.postalAddress || "—" },
              ]}
            />
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-[minmax(0,1.35fr)_minmax(320px,.65fr)]">
        <onboarding-document-panel ref={documentPanelRef} />
        <onboarding-event-feed ref={eventFeedRef} />
      </div>

      {/* ===== TABLE 2: Tabbed (Partner Types / Contacts / Banks) ===== */}
      <div className="rounded-xl border border-border bg-card">
        {/* Tabs */}
        <div className="flex items-center gap-1 border-b border-border px-5 py-2">
          {[
            { key: "types" as const, label: "Partner Type", icon: <Building2 className="h-4 w-4" /> },
            { key: "contacts" as const, label: "Partner Contact", icon: <Phone className="h-4 w-4" /> },
            { key: "banks" as const, label: "Partner Banks", icon: <Landmark className="h-4 w-4" /> },
          ].map((t) => (
            <button
              key={t.key}
              onClick={() => setSubTab(t.key)}
              className={`inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition ${
                subTab === t.key
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {t.icon}
              {t.label}
            </button>
          ))}
        </div>

        <div className="p-5">
          {subTab === "types" && (
            <PartnerTypeTab
              partnerTypes={partnerTypes}
              applicationId={id!}
                            choices={choices}
              documents={documents}
              onAdd={(pts) => setPartnerTypes((prev) => [...prev, ...pts])}

              onDelete={handleDeletePartnerType}
              onRefresh={load}
            />
          )}
          {subTab === "contacts" && (
            <ContactsTab contacts={contacts} applicationId={id!} onRefresh={load} />
          )}
          {subTab === "banks" && (
            <BanksTab bankAccounts={bankAccounts} applicationId={id!} onRefresh={load} />
          )}
        </div>
      </div>

      {/* Confirm Dialog */}
      {confirmAction && (
        <ConfirmDialog
          open
          title={confirmAction.title}
          message={confirmAction.message}
          confirmLabel="Confirm"
          onConfirm={confirmAction.action}
          onCancel={() => setConfirmAction(null)}
        />
      )}
    </div>
  )
}

/* -------------------------------------------------------------------------- */
/*  InfoTable                                                                  */
/* -------------------------------------------------------------------------- */

function InfoTable({ rows }: { rows: { label: string; value: string }[] }) {
  return (
    <div className="overflow-hidden rounded-xl border border-border bg-background">
      <dl className="grid grid-cols-1 divide-y divide-border sm:grid-cols-2 sm:divide-y-0">
        {rows.map((r, index) => (
          <div
            key={r.label}
            className={`grid min-h-12 grid-cols-[minmax(7rem,38%)_1fr] items-center gap-3 px-4 py-3 text-sm ${index % 2 === 1 ? "sm:border-l sm:border-border" : ""} ${index < rows.length - 2 ? "border-b border-border" : ""}`}
          >
            <dt className="font-medium text-muted-foreground">{r.label}</dt>
            <dd className="break-words border-l border-border pl-3 font-medium text-foreground">{r.value || "—"}</dd>
          </div>
        ))}
      </dl>
    </div>
  )
}

/* -------------------------------------------------------------------------- */
/*  PartnerTypeTab                                                             */
/* -------------------------------------------------------------------------- */

function PartnerTypeTab({
  partnerTypes,
  applicationId,
  choices,
  documents,
  onAdd,
  onDelete,
  onRefresh,
}: {
  partnerTypes: ApplicationPartnerType[]
  applicationId: string
  choices: ChoicesResponse | null
  documents: PartnerApplicationDetail["documents"]
  onAdd: (pts: ApplicationPartnerType[]) => void
  onDelete: (id: string) => void
  onRefresh: () => Promise<void>
}) {
  const [showPopup, setShowPopup] = useState(false)
  const [editing, setEditing] = useState<ApplicationPartnerType | null>(null)
  const [adding, setAdding] = useState(false)

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          {partnerTypes.length} partner type{partnerTypes.length !== 1 ? "s" : ""} assigned
        </p>
        <button
          onClick={() => setShowPopup(true)}
          className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground transition hover:bg-primary/90"
        >
          <Plus className="h-4 w-4" />
          Add Partner Type
        </button>
      </div>

      {partnerTypes.length === 0 ? (
        <p className="py-6 text-center text-sm text-muted-foreground">No partner types assigned yet.</p>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-border">
          <table className="w-full border-collapse text-sm">
            <thead className="bg-secondary/40">
              <tr className="border-b border-border text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                <th className="border-r border-border px-3 py-3">Partner Type</th>
                <th className="border-r border-border px-3 py-3">Branch</th>
                <th className="border-r border-border px-3 py-3">Region</th>
                <th className="border-r border-border px-3 py-3">Location</th>
                <th className="border-r border-border px-3 py-3">Share Data</th>
                <th className="w-28 px-3 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {partnerTypes.map((pt) => (
                <tr key={pt.id} className="transition-colors hover:bg-secondary/30">
                  <td className="border-r border-border px-3 py-3 font-medium text-foreground">{pt.partnerTypeName}</td>
                  <td className="border-r border-border px-3 py-3 text-muted-foreground">{pt.branchName || "—"}</td>
                  <td className="border-r border-border px-3 py-3 text-muted-foreground">{pt.region || "—"}</td>
                  <td className="border-r border-border px-3 py-3 text-muted-foreground">{pt.locationName || "—"}</td>
                  <td className="border-r border-border px-3 py-3 text-muted-foreground">{pt.shareDataExternally ? "Yes" : "No"}</td>
                  <td className="px-3 py-3 text-right">
                    <div className="flex items-center justify-end gap-1.5">
                      <button
                        onClick={() => setEditing(pt)}
                        className="inline-flex items-center gap-1 rounded-md border border-border px-2 py-1.5 text-xs font-medium text-foreground transition hover:bg-secondary"
                        title="View and update setup"
                      >
                        <Eye className="h-3.5 w-3.5" />
                        View / Edit
                      </button>
                      <button
                        onClick={() => onDelete(pt.id)}
                        className="rounded-md border border-border p-1.5 text-muted-foreground transition hover:bg-secondary hover:text-foreground"
                        title="Remove"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <AddPartnerTypePopup
        open={showPopup}
        onClose={() => setShowPopup(false)}
        onConfirm={async (data) => {
          setAdding(true)
          try {
            const result = await createPartnerType(applicationId, data)
            onAdd(result)
            setShowPopup(false)
            await onRefresh()
          } catch (e) {
            throw e
          } finally {
            setAdding(false)
          }
        }}
        choices={choices}
        loading={adding}
      />
      {editing && (
        <PartnerTypeSetupModal
          assignment={editing}
          choices={choices}
          applicationId={applicationId}
          documents={documents}
          onClose={() => setEditing(null)}
          onRefresh={onRefresh}
          onSaved={async () => {
            setEditing(null)
            await onRefresh()
          }}
        />
      )}
    </div>
  )
}

/* -------------------------------------------------------------------------- */
/*  PartnerTypeSetupModal                                                      */
/* -------------------------------------------------------------------------- */

function PartnerTypeSetupModal({
  assignment,
  choices,
  applicationId,
  documents,
  onClose,
  onRefresh,
  onSaved,
}: {
  assignment: ApplicationPartnerType
  choices: ChoicesResponse | null
  applicationId: string
  documents: PartnerApplicationDetail["documents"]
  onClose: () => void
  onRefresh: () => Promise<void>
  onSaved: () => Promise<void>
}) {
  const [branch, setBranch] = useState(assignment.branch ?? "")
  const [region, setRegion] = useState(assignment.region ?? "")
  const [location, setLocation] = useState(assignment.location ?? "")
  const [shareData, setShareData] = useState(assignment.shareDataExternally)
  const [saving, setSaving] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState("")
  const [documentType, setDocumentType] = useState("")
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const locations = (choices?.locations ?? []).filter((item) => !branch || item.branchId === branch)
  const assignmentDocuments = documents.filter((document) => document.applicationPartnerType === assignment.id)

  async function uploadAssignmentDocument() {
    if (!selectedFile || !documentType) {
      setError("Select a document type and file before uploading.")
      return
    }
    setUploading(true)
    setError("")
    try {
      await uploadDocument(applicationId, selectedFile, documentType, selectedFile.name, assignment.id)
      await onRefresh()
      setSelectedFile(null)
      setDocumentType("")
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to upload the assigned document")
    } finally {
      setUploading(false)
    }
  }

  async function removeAssignmentDocument(documentId: string, documentName: string) {
    if (!window.confirm(`Remove ${documentName}? This action will be recorded in the event history.`)) return
    setUploading(true)
    setError("")
    try {
      await deleteDocument(applicationId, documentId)
      await onRefresh()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to remove the assigned document")
    } finally {
      setUploading(false)
    }
  }

  async function save() {
    setSaving(true)
    setError("")
    try {
      await updatePartnerType(applicationId, assignment.id, {
        branch: branch || null,
        region,
        location: location || null,
        share_data_externally: shareData,
      })
      await onSaved()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to update partner type")
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/45 p-4" role="dialog" aria-modal="true" aria-label="Partner type setup">
      <div className="flex max-h-[min(760px,calc(100vh-2rem))] w-full max-w-3xl flex-col overflow-hidden rounded-2xl border border-border bg-card shadow-2xl">
        <div className="flex items-start justify-between border-b border-border px-6 py-5">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">Assigned partner type</p>
            <h2 className="mt-1 text-xl font-semibold text-foreground">{assignment.partnerTypeName}</h2>
            <p className="mt-1 text-sm text-muted-foreground">Review and update assignment information without leaving this application.</p>
          </div>
          <button onClick={onClose} className="rounded-lg border border-border p-2 text-muted-foreground transition hover:bg-secondary hover:text-foreground" aria-label="Close">
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="grid gap-6 overflow-y-auto p-6 md:grid-cols-[1.1fr_.9fr]">
          <div className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="space-y-1.5 text-sm font-medium text-foreground">
                Branch
                <select value={branch} onChange={(event) => { setBranch(event.target.value); setLocation("") }} className="w-full rounded-lg border border-input bg-background px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-primary/30">
                  <option value="">No branch</option>
                  {(choices?.branches ?? []).map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
                </select>
              </label>
              <label className="space-y-1.5 text-sm font-medium text-foreground">
                Region
                <select value={region} onChange={(event) => setRegion(event.target.value)} className="w-full rounded-lg border border-input bg-background px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-primary/30">
                  <option value="">No region</option>
                  {(choices?.regions ?? []).map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
                </select>
              </label>
            </div>
            <label className="block space-y-1.5 text-sm font-medium text-foreground">
              Location
              <select value={location} onChange={(event) => setLocation(event.target.value)} className="w-full rounded-lg border border-input bg-background px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-primary/30">
                <option value="">No location</option>
                {locations.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
              </select>
            </label>
            <label className="flex items-start gap-3 rounded-xl border border-border p-4 text-sm">
              <input type="checkbox" checked={shareData} onChange={(event) => setShareData(event.target.checked)} className="mt-0.5 h-4 w-4 accent-black" />
              <span><span className="block font-medium text-foreground">Share data externally</span><span className="mt-1 block text-muted-foreground">Allow approved downstream processes to use this assignment data.</span></span>
            </label>
            <section className="rounded-xl border border-border bg-background p-4">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h3 className="text-sm font-semibold text-foreground">Required documents for this assignment</h3>
                  <p className="mt-1 text-xs text-muted-foreground">Upload evidence directly against {assignment.partnerTypeName}. Changes are synchronized immediately.</p>
                </div>
                <span className="rounded-full border border-border px-2 py-1 text-xs font-semibold text-foreground">{assignmentDocuments.length}</span>
              </div>
              <div className="mt-4 grid gap-2 sm:grid-cols-[1fr_1fr_auto]">
                <select value={documentType} onChange={(event) => setDocumentType(event.target.value)} className="rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary/30">
                  <option value="">Select document type</option>
                  {(choices?.documentTypes ?? []).map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
                </select>
                <input type="file" onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)} className="min-w-0 rounded-lg border border-input bg-background px-3 py-2 text-sm text-foreground file:mr-3 file:border-0 file:bg-transparent file:text-sm file:font-medium" />
                <button onClick={uploadAssignmentDocument} disabled={uploading || !selectedFile || !documentType} className="inline-flex items-center justify-center gap-2 rounded-lg bg-primary px-3 py-2 text-sm font-semibold text-primary-foreground disabled:cursor-not-allowed disabled:opacity-50">
                  {uploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />} Upload
                </button>
              </div>
              <div className="mt-4 overflow-hidden rounded-lg border border-border">
                {assignmentDocuments.length === 0 ? (
                  <p className="px-3 py-4 text-sm text-muted-foreground">No assignment-specific documents uploaded yet.</p>
                ) : assignmentDocuments.map((document) => (
                  <div key={document.id} className="flex items-center justify-between gap-3 border-b border-border px-3 py-3 last:border-b-0">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-foreground">{document.documentName}</p>
                      <p className="mt-0.5 text-xs text-muted-foreground">{document.documentType} · {document.isVerified ? "Verified" : "Pending verification"}</p>
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      <a href={document.file} target="_blank" rel="noreferrer" className="rounded-md border border-border px-2 py-1 text-xs font-medium text-foreground hover:bg-secondary">View</a>
                      <button onClick={() => removeAssignmentDocument(document.id, document.documentName)} disabled={uploading} className="rounded-md border border-border px-2 py-1 text-xs font-medium text-muted-foreground hover:bg-secondary hover:text-foreground disabled:opacity-50">Remove</button>
                    </div>
                  </div>
                ))}
              </div>
            </section>
            {error && <div className="rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">{error}</div>}
          </div>
          <div className="rounded-xl border border-border bg-secondary/30 p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">Current assignment</p>
            <dl className="mt-4 space-y-3 text-sm">
              <div className="flex justify-between gap-4 border-b border-border pb-3"><dt className="text-muted-foreground">Partner type</dt><dd className="text-right font-medium text-foreground">{assignment.partnerTypeName}</dd></div>
              <div className="flex justify-between gap-4 border-b border-border pb-3"><dt className="text-muted-foreground">Branch</dt><dd className="text-right font-medium text-foreground">{assignment.branchName || "Not assigned"}</dd></div>
              <div className="flex justify-between gap-4 border-b border-border pb-3"><dt className="text-muted-foreground">Region</dt><dd className="text-right font-medium text-foreground">{assignment.region || "Not assigned"}</dd></div>
              <div className="flex justify-between gap-4"><dt className="text-muted-foreground">Data sharing</dt><dd className="text-right font-medium text-foreground">{assignment.shareDataExternally ? "Enabled" : "Disabled"}</dd></div>
            </dl>
            <p className="mt-5 text-xs leading-5 text-muted-foreground">Every update is recorded in the application event history and central audit log with before-and-after values.</p>
          </div>
        </div>
        <div className="flex items-center justify-between border-t border-border px-6 py-4">
          <span className="text-xs text-muted-foreground">Changes are saved immediately.</span>
          <div className="flex gap-2">
            <button onClick={onClose} disabled={saving} className="rounded-lg border border-border px-4 py-2 text-sm font-medium text-foreground transition hover:bg-secondary disabled:opacity-50">Cancel</button>
            <button onClick={save} disabled={saving} className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground transition hover:bg-primary/90 disabled:opacity-50">{saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}{saving ? "Saving..." : "Save changes"}</button>
          </div>
        </div>
      </div>
    </div>
  )
}

/* -------------------------------------------------------------------------- */
/*  AddPartnerTypePopup                                                        */
/* -------------------------------------------------------------------------- */

function AddPartnerTypePopup({
  open, onClose, onConfirm, choices, loading,
}: {
  open: boolean
  onClose: () => void
  onConfirm: (data: { partner_type: string; branches?: string[]; region?: string; location?: string | null; share_data_externally?: boolean }) => Promise<void>
  choices: ChoicesResponse | null
  loading: boolean
}) {
  const [partnerType, setPartnerType] = useState("")
  const [selectedBranches, setSelectedBranches] = useState<string[]>([])
  const [branchQuery, setBranchQuery] = useState("")
  const [branchOpen, setBranchOpen] = useState(false)
  const branchRef = useRef<HTMLDivElement>(null)
  const [region, setRegion] = useState("")
  const [location, setLocation] = useState("")
  const [shareData, setShareData] = useState("no")
  const [error, setError] = useState("")

  const systemTypes = choices?.systemPartnerTypes ?? []
  const branchOptions = choices?.branches ?? []
  const regionOptions = choices?.regions ?? []
  const locationOptions = (choices?.locations ?? []).filter(
    (l) => selectedBranches.length === 0 || selectedBranches.includes(l.branchId),
  )

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (branchRef.current && !branchRef.current.contains(e.target as Node)) {
        setBranchOpen(false)
      }
    }
    document.addEventListener("mousedown", handleClick)
    return () => document.removeEventListener("mousedown", handleClick)
  }, [])

  const branchSearchResults = branchQuery
    ? branchOptions.filter((b) => !selectedBranches.includes(b.value) && b.label.toLowerCase().includes(branchQuery.toLowerCase()))
    : branchOptions.filter((b) => !selectedBranches.includes(b.value))

  function handleBranchToggle(value: string) {
    setSelectedBranches((prev) =>
      prev.includes(value) ? prev.filter((v) => v !== value) : [...prev, value],
    )
    setBranchQuery("")
    setBranchOpen(false)
  }

  if (!open) return null

  async function handleSubmit() {
    setError("")
    if (!partnerType) { setError("Please select a partner type."); return }
    try {
      await onConfirm({
        partner_type: partnerType,
        branches: selectedBranches.length > 0 ? selectedBranches : undefined,
        region: region || undefined,
        location: location || null,
        share_data_externally: shareData === "yes",
      })
      setPartnerType("")
      setSelectedBranches([])
      setRegion("")
      setLocation("")
      setShareData("no")
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to add partner type")
    }
  }

  function handleClose() {
    setPartnerType(""); setSelectedBranches([]); setRegion(""); setLocation(""); setShareData("no"); setError("")
    onClose()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ backgroundColor: "var(--color-bg-overlay)" }}>
      <div className="mx-4 w-full max-w-md rounded-xl bg-card shadow-xl">
        <div className="flex items-center justify-between border-b px-5 py-4">
          <h2 className="text-base font-semibold">Add Partner Type</h2>
          <button onClick={handleClose} className="rounded p-1 text-muted-foreground hover:bg-accent"><X className="h-5 w-5" /></button>
        </div>
        <div className="space-y-4 px-5 py-4">
          <div>
            <label className="mb-1 block text-sm font-medium">Partner Type</label>
            <select value={partnerType} onChange={(e) => setPartnerType(e.target.value)} className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary/40">
              <option value="">Select partner type</option>
              {systemTypes.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
          </div>
          <div ref={branchRef} className="relative">
            <label className="mb-1 block text-sm font-medium">Branches</label>
            {selectedBranches.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mb-1.5">
                {selectedBranches.map((id) => {
                  const b = branchOptions.find((o) => o.value === id)
                  return (
                    <span key={id} className="inline-flex items-center gap-1 rounded-full bg-primary/10 text-primary px-2.5 py-0.5 text-xs font-medium">
                      {b?.label ?? id}
                      <button onClick={() => { setSelectedBranches((prev) => prev.filter((v) => v !== id)); setLocation("") }} className="hover:text-destructive"><X className="h-3 w-3" /></button>
                    </span>
                  )
                })}
              </div>
            )}
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <input type="text" placeholder="Search branches..." value={branchQuery} onChange={(e) => { setBranchQuery(e.target.value); setBranchOpen(true) }} onFocus={() => setBranchOpen(true)} className="w-full rounded-lg border border-input bg-background text-foreground pl-9 pr-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary/40" />
            </div>
            {branchOpen && branchSearchResults.length > 0 && (
              <div className="absolute z-20 mt-1 w-full rounded-lg border border-border bg-card shadow-lg max-h-48 overflow-y-auto">
                {branchSearchResults.map((b) => (
                  <button key={b.value} onClick={() => handleBranchToggle(b.value)} className="w-full text-left px-3 py-2 text-sm hover:bg-accent transition-colors">{b.label}</button>
                ))}
              </div>
            )}
            </div>
          <div>
            <label className="mb-1 block text-sm font-medium">Region</label>
            <select value={region} onChange={(e) => setRegion(e.target.value)} className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary/40">
              <option value="">Select region</option>
              {regionOptions.map((r) => (
                <option key={r.value} value={r.value}>{r.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">Share Data Externally</label>
            <select value={shareData} onChange={(e) => setShareData(e.target.value)} className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary/40">
              <option value="no">No</option>
              <option value="yes">Yes</option>
            </select>
          </div>
          {error && <div className="rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">{error}</div>}
        </div>
        <div className="flex justify-end gap-2 border-t px-5 py-3">
          <button onClick={handleClose} disabled={loading} className="rounded-lg border border-input px-4 py-2 text-sm font-medium hover:bg-accent disabled:opacity-50">Cancel</button>
          <button onClick={handleSubmit} disabled={loading} className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground hover:bg-primary/90 disabled:opacity-50">{loading ? "Adding..." : "Add"}</button>
        </div>
      </div>
    </div>
  )
}

/* -------------------------------------------------------------------------- */
/*  ContactsTab                                                                */
/* -------------------------------------------------------------------------- */

function ContactsTab({ contacts, applicationId, onRefresh }: {
  contacts: ApplicationContact[]; applicationId: string; onRefresh: () => void
}) {
  if (contacts.length === 0) {
    return (
      <div className="flex flex-col items-center py-8 text-center">
        <Phone className="mb-2 h-8 w-8 text-muted-foreground" />
        <p className="text-sm text-muted-foreground">No contacts yet.</p>
      </div>
    )
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            <th className="px-3 py-2">Name</th>
            <th className="px-3 py-2">Type</th>
            <th className="px-3 py-2">Email</th>
            <th className="px-3 py-2">Phone</th>
            <th className="px-3 py-2">Mobile</th>
            <th className="px-3 py-2">Designation</th>
            <th className="w-14 px-2 py-2 text-right">Primary</th>
          </tr>
        </thead>
        <tbody>
          {contacts.map((c) => (
            <tr key={c.id} className="border-b border-border/50 last:border-b-0">
              <td className="px-3 py-2.5 font-medium text-foreground">{c.firstName} {c.lastName}</td>
              <td className="px-3 py-2.5 text-muted-foreground">{contactTypeLabel(c.contactType)}</td>
              <td className="px-3 py-2.5 text-muted-foreground">{c.email || "—"}</td>
              <td className="px-3 py-2.5 text-muted-foreground">{c.phone || "—"}</td>
              <td className="px-3 py-2.5 text-muted-foreground">{c.mobile || "—"}</td>
              <td className="px-3 py-2.5 text-muted-foreground">{c.designation || "—"}</td>
              <td className="px-2 py-2.5 text-center">{c.isPrimary ? <span className="text-xs font-semibold text-success">Yes</span> : "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

/* -------------------------------------------------------------------------- */
/*  BanksTab                                                                   */
/* -------------------------------------------------------------------------- */

function BanksTab({ bankAccounts, applicationId, onRefresh }: {
  bankAccounts: ApplicationBankAccount[]; applicationId: string; onRefresh: () => void
}) {
  if (bankAccounts.length === 0) {
    return (
      <div className="flex flex-col items-center py-8 text-center">
        <Landmark className="mb-2 h-8 w-8 text-muted-foreground" />
        <p className="text-sm text-muted-foreground">No bank accounts yet.</p>
      </div>
    )
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            <th className="px-3 py-2">Account Name</th>
            <th className="px-3 py-2">Bank</th>
            <th className="px-3 py-2">Branch</th>
            <th className="px-3 py-2">Account No</th>
            <th className="px-3 py-2">Currency</th>
            <th className="px-3 py-2">SWIFT</th>
            <th className="w-14 px-2 py-2 text-right">Primary</th>
          </tr>
        </thead>
        <tbody>
          {bankAccounts.map((b) => (
            <tr key={b.id} className="border-b border-border/50 last:border-b-0">
              <td className="px-3 py-2.5 font-medium text-foreground">{b.accountName}</td>
              <td className="px-3 py-2.5 text-muted-foreground">{b.bankName}</td>
              <td className="px-3 py-2.5 text-muted-foreground">{b.branchName || "—"}</td>
              <td className="px-3 py-2.5 text-muted-foreground">{b.accountNumber}</td>
              <td className="px-3 py-2.5 text-muted-foreground">{b.currency}</td>
              <td className="px-3 py-2.5 text-muted-foreground">{b.swiftCode || "—"}</td>
              <td className="px-2 py-2.5 text-center">{b.isPrimary ? <span className="text-xs font-semibold text-success">Yes</span> : "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

/* -------------------------------------------------------------------------- */
/*  StatusBadge (config-driven)                                                */
/* -------------------------------------------------------------------------- */

function StatusBadge({ status }: { status: string }) {
  const label = useStatusLabel(status)
  const bg = useStatusColor(status)
  return (
    <span
      className="ml-auto inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold"
      style={{ backgroundColor: bg, color: "inherit" }}
    >
      {label}
    </span>
  )
}

function contactTypeLabel(type: string): string {
  const labels: Record<string, string> = { PRIMARY: "Primary", SECONDARY: "Secondary", BILLING: "Billing", TECHNICAL: "Technical", OTHER: "Other" }
  return labels[type] ?? type
}
