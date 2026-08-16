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
  getApplicationPartnerTypeFieldValues,
  updateApplicationPartnerTypeFieldValues,
  getApplicationPartnerTypeContacts,
  createApplicationPartnerTypeContact,
  updateApplicationPartnerTypeContact,
  deleteApplicationPartnerTypeContact,
  getApplicationPartnerTypeBankAccounts,
  createApplicationPartnerTypeBankAccount,
  updateApplicationPartnerTypeBankAccount,
  deleteApplicationPartnerTypeBankAccount,
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
  ApplicationFieldValue,
  PartnerTypeDocumentRequirement,
  PartnerTypeFieldConfiguration,
  PartnerTypeContactRequirement,
  PartnerTypeBankRequirement,
  ChoicesResponse,
} from "../../lib/types"
import { useStatusLabel, useStatusColor } from "../../config/ConfigurationHooks"
import { fetchPartnerOnboardingConfiguration, getConfiguredParameterValue, usePartnerOnboardingConfiguration } from "../../config/ConfigurationAPI"
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
  type SetupSection = "documents" | "attributes" | "contacts" | "banks"
  const steps: { key: SetupSection; label: string; shortLabel: string; icon: React.ReactNode }[] = [
    { key: "documents", label: "Partner Type Documents", shortLabel: "Documents", icon: <FileCheck className="h-4 w-4" /> },
    { key: "attributes", label: "Partner Type Attributes Form", shortLabel: "Attributes Form", icon: <Pencil className="h-4 w-4" /> },
    { key: "contacts", label: "Partner Type Contacts", shortLabel: "Contacts", icon: <Phone className="h-4 w-4" /> },
    { key: "banks", label: "Partner Type Banks", shortLabel: "Banks", icon: <Landmark className="h-4 w-4" /> },
  ]

  const [branch, setBranch] = useState(assignment.branch ?? "")
  const [region, setRegion] = useState(assignment.region ?? "")
  const [location, setLocation] = useState(assignment.location ?? "")
  const [shareData, setShareData] = useState(assignment.shareDataExternally)
  const [activeSection, setActiveSection] = useState<SetupSection>("documents")
  const [saving, setSaving] = useState(false)
  const [setupLoading, setSetupLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState("")
  const [notice, setNotice] = useState("")
  const [documentType, setDocumentType] = useState("")
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [documentRequirements, setDocumentRequirements] = useState<PartnerTypeDocumentRequirement[]>([])
  const [fieldConfigurations, setFieldConfigurations] = useState<PartnerTypeFieldConfiguration[]>([])
  const [contactRequirements, setContactRequirements] = useState<PartnerTypeContactRequirement[]>([])
  const [bankRequirements, setBankRequirements] = useState<PartnerTypeBankRequirement[]>([])
  const [fieldValues, setFieldValues] = useState<Record<string, unknown>>({})
  const [assignmentContacts, setAssignmentContacts] = useState<ApplicationContact[]>([])
  const [assignmentBanks, setAssignmentBanks] = useState<ApplicationBankAccount[]>([])
  const [editingContactId, setEditingContactId] = useState<string | null>(null)
  const [editingBankId, setEditingBankId] = useState<string | null>(null)
  const [contactDraft, setContactDraft] = useState({ requirement: "", firstName: "", lastName: "", email: "", phone: "", mobile: "", designation: "", isPrimary: false, notes: "" })
  const [bankDraft, setBankDraft] = useState({ requirement: "", bankName: "", branchName: "", accountName: "", accountNumber: "", swiftCode: "", currency: "", isPrimary: false, notes: "" })
  const { configuration: onboardingConfiguration } = usePartnerOnboardingConfiguration()
  const configuredCurrency = String(getConfiguredParameterValue(onboardingConfiguration, "DEFAULT_CURRENCY", "TZS"))

  const locations = (choices?.locations ?? []).filter((item) => !branch || item.branchId === branch)
  const assignmentDocuments = documents.filter((document) => document.applicationPartnerType === assignment.id)
  const activeStepIndex = steps.findIndex((step) => step.key === activeSection)
  const completedDocuments = documentRequirements.filter((requirement) => assignmentDocuments.some((document) => document.documentType === requirement.code || document.documentName === requirement.code)).length
  const completedFields = fieldConfigurations.filter((config) => {
    const value = fieldValues[config.id]
    return value !== undefined && value !== null && (Array.isArray(value) ? value.length > 0 : String(value).trim() !== "")
  }).length
  const completedContacts = contactRequirements.filter((requirement) => assignmentContacts.some((contact) => contact.contactRequirement === requirement.id)).length
  const completedBanks = bankRequirements.filter((requirement) => assignmentBanks.some((bank) => bank.bankRequirement === requirement.id)).length

  const loadAssignmentSetup = useCallback(async () => {
    setSetupLoading(true)
    setError("")
    try {
      const [configuration, values, savedContacts, savedBanks] = await Promise.all([
        // This is the same authoritative projection used by Partner Parameters.
        // It is intentionally fetched fresh here so changes made in Settings are
        // visible immediately when the setup popup is opened or refreshed.
        fetchPartnerOnboardingConfiguration(),
        getApplicationPartnerTypeFieldValues(applicationId, assignment.id),
        getApplicationPartnerTypeContacts(applicationId, assignment.id),
        getApplicationPartnerTypeBankAccounts(applicationId, assignment.id),
      ])
      const configuredType = configuration.partnerTypes.find((item) =>
        item.id === assignment.partnerType || item.code === assignment.partnerType,
      )
      if (!configuredType) {
        throw new Error(`No active Partner Parameters configuration was found for ${assignment.partnerTypeName}. Configure this partner type under Partner Parameters first.`)
      }

      const docs: PartnerTypeDocumentRequirement[] = configuredType.documents
        .filter((item) => item.isActive)
        .sort((a, b) => a.sortOrder - b.sortOrder)
        .map((item) => ({
          id: item.id,
          partnerType: configuredType.id,
          partnerTypeName: configuredType.name,
          code: item.code,
          description: item.description,
          isRequired: item.isRequired,
          isMandatory: item.isMandatory,
          sortOrder: item.sortOrder,
          isActive: item.isActive,
          createdBy: null,
          createdByName: null,
          updatedBy: null,
          updatedByName: null,
          createdAt: "",
          updatedAt: "",
        }))
      const fields: PartnerTypeFieldConfiguration[] = configuredType.attributes
        .filter((item) => item.isActive)
        .sort((a, b) => a.displayOrder - b.displayOrder)
        .map((item) => ({
          id: item.id,
          partnerType: configuredType.id,
          partnerTypeName: configuredType.name,
          fieldName: item.fieldName,
          fieldCode: item.fieldCode,
          fieldType: item.fieldType as PartnerTypeFieldConfiguration["fieldType"],
          defaultValue: item.defaultValue ?? "",
          isRequired: item.isRequired,
          validationRules: item.validationRules ?? {},
          displayOrder: item.displayOrder,
          visibilityRules: item.visibilityRules ?? {},
          isActive: item.isActive,
          createdAt: "",
          updatedAt: "",
        }))
      const contactsReqs: PartnerTypeContactRequirement[] = configuredType.contacts
        .filter((item) => item.isActive)
        .sort((a, b) => a.displayOrder - b.displayOrder)
        .map((item) => ({
          id: item.id,
          partnerType: configuredType.id,
          partnerTypeName: configuredType.name,
          contactType: item.contactType,
          isRequired: item.isRequired,
          multipleAllowed: item.multipleAllowed,
          displayOrder: item.displayOrder,
          isActive: item.isActive,
          createdAt: "",
          updatedAt: "",
        }))
      const banksReqs: PartnerTypeBankRequirement[] = configuredType.banks
        .filter((item) => item.isActive)
        .sort((a, b) => a.displayOrder - b.displayOrder)
        .map((item) => ({
          id: item.id,
          partnerType: configuredType.id,
          partnerTypeName: configuredType.name,
          bankType: item.bankType,
          isRequired: item.isRequired,
          multipleAllowed: item.multipleAllowed,
          validationRules: item.validationRules ?? {},
          displayOrder: item.displayOrder,
          isActive: item.isActive,
          createdAt: "",
          updatedAt: "",
        }))

      setDocumentRequirements(docs)
      setFieldConfigurations(fields)
      setContactRequirements(contactsReqs)
      setBankRequirements(banksReqs)
      setFieldValues(Object.fromEntries(values.map((item) => [item.fieldConfig, item.valueJson])))
      setAssignmentContacts(savedContacts)
      setAssignmentBanks(savedBanks)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to load configured partner-type requirements")
      setDocumentRequirements([])
      setFieldConfigurations([])
      setContactRequirements([])
      setBankRequirements([])
    } finally {
      setSetupLoading(false)
    }
  }, [applicationId, assignment.id, assignment.partnerType, assignment.partnerTypeName])

  useEffect(() => { void loadAssignmentSetup() }, [loadAssignmentSetup])

  useEffect(() => {
    setBankDraft((current) => current.currency ? current : { ...current, currency: configuredCurrency })
  }, [configuredCurrency])

  function clearFeedback() {
    setError("")
    setNotice("")
  }

  function isBlankValue(value: unknown) {
    return value === undefined || value === null || (Array.isArray(value) ? value.length === 0 : String(value).trim() === "")
  }

  function fieldOptions(config: PartnerTypeFieldConfiguration): { value: string; label: string }[] {
    const raw = config.validationRules?.options
    if (!Array.isArray(raw)) return []
    return raw.map((option) => {
      if (typeof option === "object" && option !== null) {
        const item = option as Record<string, unknown>
        return { value: String(item.value ?? item.code ?? item.label ?? ""), label: String(item.label ?? item.name ?? item.value ?? "") }
      }
      return { value: String(option), label: String(option) }
    }).filter((option) => option.value)
  }

  function validateField(config: PartnerTypeFieldConfiguration, value: unknown): string | null {
    if (config.isRequired && isBlankValue(value)) return `${config.fieldName} is required.`
    if (isBlankValue(value)) return null
    const rules = config.validationRules ?? {}
    const textValue = Array.isArray(value) ? value.join(",") : String(value)
    if (typeof rules.minLength === "number" && textValue.length < rules.minLength) return `${config.fieldName} must be at least ${rules.minLength} characters.`
    if (typeof rules.maxLength === "number" && textValue.length > rules.maxLength) return `${config.fieldName} must not exceed ${rules.maxLength} characters.`
    if (typeof rules.pattern === "string") {
      try {
        if (!new RegExp(rules.pattern).test(textValue)) return `${config.fieldName} has an invalid format.`
      } catch {
        // Invalid configuration should not make the entire workspace unusable.
      }
    }
    return null
  }

  function coerceFieldValue(config: PartnerTypeFieldConfiguration, value: string) {
    if (["NUMBER", "CURRENCY", "PERCENTAGE"].includes(config.fieldType)) return value === "" ? "" : Number(value)
    return value
  }

  async function saveConfiguredFields(): Promise<boolean> {
    clearFeedback()
    const invalid = fieldConfigurations.map((config) => validateField(config, fieldValues[config.id])).find(Boolean)
    if (invalid) {
      setError(invalid)
      setActiveSection("attributes")
      return false
    }
    try {
      await updateApplicationPartnerTypeFieldValues(applicationId, assignment.id, fieldConfigurations.map((config) => ({
        field_config: config.id,
        value_json: fieldValues[config.id] ?? null,
      })))
      await loadAssignmentSetup()
      await onRefresh()
      setNotice("Attributes saved and synchronized.")
      return true
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to save configured attributes")
      return false
    }
  }

  function resetContactDraft() {
    setEditingContactId(null)
    setContactDraft({ requirement: "", firstName: "", lastName: "", email: "", phone: "", mobile: "", designation: "", isPrimary: false, notes: "" })
  }

  function resetBankDraft() {
    setEditingBankId(null)
    setBankDraft({ requirement: "", bankName: "", branchName: "", accountName: "", accountNumber: "", swiftCode: "", currency: configuredCurrency, isPrimary: false, notes: "" })
  }

  async function saveContact() {
    clearFeedback()
    if (!contactDraft.requirement || !contactDraft.firstName.trim() || !contactDraft.lastName.trim()) {
      setError("Select the configured contact requirement and provide the contact name.")
      return
    }
    const requirement = contactRequirements.find((item) => item.id === contactDraft.requirement)
    const payload = {
      contact_requirement: contactDraft.requirement,
      contact_type: requirement?.contactType ?? "OTHER",
      first_name: contactDraft.firstName.trim(),
      last_name: contactDraft.lastName.trim(),
      email: contactDraft.email.trim(),
      phone: contactDraft.phone.trim(),
      mobile: contactDraft.mobile.trim(),
      designation: contactDraft.designation.trim(),
      is_primary: contactDraft.isPrimary,
      notes: contactDraft.notes.trim(),
    }
    try {
      if (editingContactId) await updateApplicationPartnerTypeContact(applicationId, assignment.id, editingContactId, payload)
      else await createApplicationPartnerTypeContact(applicationId, assignment.id, payload)
      resetContactDraft()
      await loadAssignmentSetup()
      await onRefresh()
      setNotice(editingContactId ? "Contact updated and synchronized." : "Contact added and synchronized.")
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to save contact")
    }
  }

  async function saveBank() {
    clearFeedback()
    if (!bankDraft.requirement || !bankDraft.bankName.trim() || !bankDraft.accountName.trim() || !bankDraft.accountNumber.trim()) {
      setError("Select the configured bank requirement and provide bank, account name, and account number.")
      return
    }
    const requirement = bankRequirements.find((item) => item.id === bankDraft.requirement)
    const payload = {
      bank_requirement: bankDraft.requirement,
      bank_type: requirement?.bankType ?? "OTHER",
      bank_name: bankDraft.bankName.trim(),
      branch_name: bankDraft.branchName.trim(),
      account_name: bankDraft.accountName.trim(),
      account_number: bankDraft.accountNumber.trim(),
      swift_code: bankDraft.swiftCode.trim(),
      currency: bankDraft.currency.trim() || configuredCurrency,
      is_primary: bankDraft.isPrimary,
      notes: bankDraft.notes.trim(),
    }
    try {
      if (editingBankId) await updateApplicationPartnerTypeBankAccount(applicationId, assignment.id, editingBankId, payload)
      else await createApplicationPartnerTypeBankAccount(applicationId, assignment.id, payload)
      resetBankDraft()
      await loadAssignmentSetup()
      await onRefresh()
      setNotice(editingBankId ? "Bank account updated and synchronized." : "Bank account added and synchronized.")
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to save bank account")
    }
  }

  function editContact(contact: ApplicationContact) {
    clearFeedback()
    setEditingContactId(contact.id)
    setContactDraft({ requirement: contact.contactRequirement ?? "", firstName: contact.firstName, lastName: contact.lastName, email: contact.email, phone: contact.phone, mobile: contact.mobile, designation: contact.designation, isPrimary: contact.isPrimary, notes: contact.notes })
    setActiveSection("contacts")
  }

  function editBank(bank: ApplicationBankAccount) {
    clearFeedback()
    setEditingBankId(bank.id)
    setBankDraft({ requirement: bank.bankRequirement ?? "", bankName: bank.bankName, branchName: bank.branchName, accountName: bank.accountName, accountNumber: bank.accountNumber, swiftCode: bank.swiftCode, currency: bank.currency, isPrimary: bank.isPrimary, notes: bank.notes })
    setActiveSection("banks")
  }

  async function removeContact(contact: ApplicationContact) {
    clearFeedback()
    try {
      await deleteApplicationPartnerTypeContact(applicationId, assignment.id, contact.id)
      await loadAssignmentSetup()
      await onRefresh()
      setNotice("Contact removed and synchronized.")
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to remove contact")
    }
  }

  async function removeBank(bank: ApplicationBankAccount) {
    clearFeedback()
    try {
      await deleteApplicationPartnerTypeBankAccount(applicationId, assignment.id, bank.id)
      await loadAssignmentSetup()
      await onRefresh()
      setNotice("Bank account removed and synchronized.")
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to remove bank account")
    }
  }

  async function uploadAssignmentDocument() {
    clearFeedback()
    if (!selectedFile || !documentType) {
      setError("Select a configured document requirement and file before uploading.")
      return
    }
    setUploading(true)
    try {
      await uploadDocument(applicationId, selectedFile, documentType, selectedFile.name, assignment.id)
      await onRefresh()
      await loadAssignmentSetup()
      setSelectedFile(null)
      setDocumentType("")
      setNotice("Document uploaded and synchronized.")
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to upload the assigned document")
    } finally {
      setUploading(false)
    }
  }

  async function removeAssignmentDocument(documentId: string, documentName: string) {
    if (!window.confirm(`Remove ${documentName}? This action will be recorded in the event history.`)) return
    clearFeedback()
    setUploading(true)
    try {
      await deleteDocument(applicationId, documentId)
      await onRefresh()
      await loadAssignmentSetup()
      setNotice("Document removed and synchronized.")
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to remove the assigned document")
    } finally {
      setUploading(false)
    }
  }

  async function saveAssignment() {
    clearFeedback()
    setSaving(true)
    try {
      await updatePartnerType(applicationId, assignment.id, {
        branch: branch || null,
        region,
        location: location || null,
        share_data_externally: shareData,
      })
      await onSaved()
      setNotice("Assignment settings saved and synchronized.")
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to update partner type")
    } finally {
      setSaving(false)
    }
  }

  async function moveToStep(nextIndex: number) {
    if (nextIndex < 0 || nextIndex >= steps.length) return
    if (activeSection === "attributes") {
      const saved = await saveConfiguredFields()
      if (!saved) return
    }
    clearFeedback()
    setActiveSection(steps[nextIndex].key)
  }

  function renderDynamicField(config: PartnerTypeFieldConfiguration) {
    const value = fieldValues[config.id] ?? config.defaultValue ?? ""
    const options = fieldOptions(config)
    const rules = config.validationRules ?? {}
    const common = {
      className: "w-full rounded-lg border border-input bg-background px-3 py-2.5 text-sm outline-none transition focus:border-foreground focus:ring-2 focus:ring-foreground/15",
      required: config.isRequired,
    }
    if (config.fieldType === "BOOLEAN") {
      return <label className="flex min-h-11 items-center gap-3 rounded-lg border border-input bg-background px-3 py-2.5 text-sm font-normal"><input type="checkbox" checked={Boolean(value)} onChange={(event) => setFieldValues((prev) => ({ ...prev, [config.id]: event.target.checked }))} className="h-4 w-4 accent-black" /> Yes</label>
    }
    if (config.fieldType === "DROPDOWN") {
      return <select {...common} value={String(value)} onChange={(event) => setFieldValues((prev) => ({ ...prev, [config.id]: event.target.value }))}><option value="">Select {config.fieldName}</option>{options.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select>
    }
    if (config.fieldType === "MULTI_SELECT" && options.length > 0) {
      const selected = Array.isArray(value) ? value.map(String) : []
      return <div className="grid gap-2 rounded-lg border border-input bg-background p-3 sm:grid-cols-2">{options.map((option) => <label key={option.value} className="flex items-center gap-2 text-sm font-normal"><input type="checkbox" checked={selected.includes(option.value)} onChange={(event) => setFieldValues((prev) => ({ ...prev, [config.id]: event.target.checked ? [...selected, option.value] : selected.filter((item) => item !== option.value) }))} className="h-4 w-4 accent-black" />{option.label}</label>)}</div>
    }
    if (config.fieldType === "MULTI_SELECT") {
      return <input {...common} value={Array.isArray(value) ? value.join(", ") : String(value)} onChange={(event) => setFieldValues((prev) => ({ ...prev, [config.id]: event.target.value.split(",").map((item) => item.trim()).filter(Boolean) }))} placeholder="Enter values separated by commas" />
    }
    if (config.fieldType === "FILE") {
      return <div className="space-y-2"><input type="file" {...common} onChange={(event) => setFieldValues((prev) => ({ ...prev, [config.id]: event.target.files?.[0]?.name ?? "" }))} /><p className="text-[11px] font-normal text-muted-foreground">File evidence is uploaded from the Documents step; this configured value stores the reference.</p></div>
    }
    const inputType = config.fieldType === "NUMBER" || config.fieldType === "CURRENCY" || config.fieldType === "PERCENTAGE" ? "number" : config.fieldType === "DATE" ? "date" : "text"
    return <input {...common} type={inputType} value={String(value)} min={typeof rules.min === "number" ? rules.min : undefined} max={typeof rules.max === "number" ? rules.max : undefined} maxLength={typeof rules.maxLength === "number" ? rules.maxLength : undefined} onChange={(event) => setFieldValues((prev) => ({ ...prev, [config.id]: coerceFieldValue(config, event.target.value) }))} />
  }

  return (
    <div className="partner-type-setup fixed inset-0 z-[60] flex items-center justify-center bg-black/55 p-0 sm:p-4" role="dialog" aria-modal="true" aria-label="Partner type setup">
      <style>{`\n        .partner-type-setup input:not([type="checkbox"]):not([type="radio"]),\n        .partner-type-setup select,\n        .partner-type-setup button,\n        .partner-type-setup a {\n          min-height: 40px;\n        }\n        .partner-type-setup input:not([type="checkbox"]):not([type="radio"]),\n        .partner-type-setup select {\n          height: 40px;\n        }\n        .partner-type-setup input[type="file"] {\n          height: 40px;\n          padding-top: 8px;\n          padding-bottom: 8px;\n        }\n        .partner-type-setup textarea {\n          min-height: 88px;\n        }\n        .partner-type-setup button,\n        .partner-type-setup a {\n          line-height: 1.15;\n        }\n      `}</style>
      <div className="flex h-full max-h-[100vh] w-full flex-col overflow-hidden border border-border bg-card shadow-2xl sm:h-auto sm:max-h-[calc(100vh-2rem)] sm:rounded-2xl 2xl:max-w-[1800px]">
        <div className="flex flex-col gap-4 border-b border-border px-4 py-4 sm:px-6 sm:py-5 lg:flex-row lg:items-center lg:justify-between">
          <div className="min-w-0">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground"><span>Partner</span><span>/</span><span>Partner Type Setup</span></div>
            <h2 className="mt-1 truncate text-xl font-semibold text-foreground sm:text-2xl">{assignment.partnerTypeName}</h2>
            <p className="mt-1 text-sm text-muted-foreground">Complete the parameterized setup steps for this assigned partner type.</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center gap-2 rounded-lg border border-border bg-background px-3 py-2 text-xs font-semibold text-muted-foreground"><Shield className="h-3.5 w-3.5" /> KYC: Not Set</span>
            <button type="button" onClick={onClose} className="inline-flex items-center gap-2 rounded-lg border border-border bg-background px-3 py-2 text-sm font-semibold text-foreground transition hover:bg-secondary"><ArrowLeft className="h-4 w-4" /> Back to Partner View</button>
          </div>
        </div>

        <div className="border-b border-border bg-secondary/20 px-4 py-3 sm:px-6">
          <div className="flex gap-2 overflow-x-auto" role="tablist" aria-label="Partner type setup steps">
            {steps.map((step, index) => {
              const count = step.key === "documents" ? `${completedDocuments}/${documentRequirements.length}` : step.key === "attributes" ? `${completedFields}/${fieldConfigurations.length}` : step.key === "contacts" ? `${completedContacts}/${contactRequirements.length}` : `${completedBanks}/${bankRequirements.length}`
              return <button key={step.key} type="button" onClick={() => { clearFeedback(); setActiveSection(step.key) }} className={`flex min-w-max items-center gap-2 rounded-lg border px-3 py-2.5 text-left transition sm:px-4 ${activeSection === step.key ? "border-foreground bg-foreground text-background" : "border-border bg-background text-muted-foreground hover:bg-secondary hover:text-foreground"}`} role="tab" aria-selected={activeSection === step.key}><span className="flex h-6 w-6 items-center justify-center rounded-full border border-current text-xs font-bold">{index + 1}</span><span><span className="block text-xs font-semibold sm:text-sm">{step.label}</span><span className="block text-[10px] font-normal uppercase tracking-wide opacity-70">{count} configured</span></span>{step.icon}</button>
            })}
          </div>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto bg-background p-4 sm:p-6">
          <div className="mx-auto grid max-w-[1640px] gap-5 xl:grid-cols-[minmax(0,1fr)_300px]">
            <div className="space-y-5">
              <section className="rounded-xl border border-border bg-card p-4 sm:p-5">
                <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
                  <div><p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">Assignment context</p><p className="mt-1 text-sm text-muted-foreground">These values are also controlled by the partner and branch parameter configuration.</p></div>
                  <div className="flex items-center gap-2 text-xs font-semibold text-muted-foreground"><span className="h-2 w-2 rounded-full bg-foreground" /> Assignment active</div>
                </div>
                <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                  <label className="space-y-1.5 text-sm font-medium text-foreground">Branch<select value={branch} onChange={(event) => { setBranch(event.target.value); setLocation("") }} className="w-full rounded-lg border border-input bg-background px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-foreground/15"><option value="">No branch</option>{(choices?.branches ?? []).map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label>
                  <label className="space-y-1.5 text-sm font-medium text-foreground">Region<select value={region} onChange={(event) => setRegion(event.target.value)} className="w-full rounded-lg border border-input bg-background px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-foreground/15"><option value="">No region</option>{(choices?.regions ?? []).map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label>
                  <label className="space-y-1.5 text-sm font-medium text-foreground">Location<select value={location} onChange={(event) => setLocation(event.target.value)} className="w-full rounded-lg border border-input bg-background px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-foreground/15"><option value="">No location</option>{locations.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label>
                  <label className="flex items-center gap-3 rounded-lg border border-input bg-background px-3 py-2.5 text-sm"><input type="checkbox" checked={shareData} onChange={(event) => setShareData(event.target.checked)} className="h-4 w-4 accent-black" /><span><span className="block font-medium text-foreground">Share data externally</span><span className="block text-[11px] font-normal text-muted-foreground">Approved downstream use</span></span></label>
                </div>
              </section>

              {setupLoading && <div className="flex items-center gap-3 rounded-xl border border-dashed border-border bg-card px-4 py-5 text-sm text-muted-foreground"><Loader2 className="h-4 w-4 animate-spin" /> Loading requirements from parameter settings...</div>}

              {!setupLoading && activeSection === "documents" && <section className="rounded-xl border border-border bg-card">
                <div className="flex flex-col gap-3 border-b border-border px-4 py-4 sm:flex-row sm:items-start sm:justify-between sm:px-5"><div><h3 className="text-base font-semibold text-foreground">Partner Type Documents</h3><p className="mt-1 text-sm text-muted-foreground">Every row below comes from the document requirements configured for this partner type.</p></div><span className="rounded-full border border-border px-3 py-1 text-xs font-semibold text-foreground">{completedDocuments}/{documentRequirements.length} uploaded</span></div>
                <div className="border-b border-border bg-secondary/20 p-4 sm:p-5"><div className="grid gap-3 lg:grid-cols-[minmax(220px,.8fr)_minmax(260px,1fr)_auto]"><label className="space-y-1.5 text-sm font-medium text-foreground">Configured document<select value={documentType} onChange={(event) => setDocumentType(event.target.value)} className="w-full rounded-lg border border-input bg-background px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-foreground/15"><option value="">Select document requirement</option>{documentRequirements.map((item) => <option key={item.id} value={item.code}>{item.code} · {item.description || "Document"}{item.isRequired || item.isMandatory ? " · Required" : ""}</option>)}</select></label><label className="space-y-1.5 text-sm font-medium text-foreground">Evidence file<input id={`partner-document-file-${assignment.id}`} type="file" onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)} className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm text-foreground file:mr-3 file:border-0 file:bg-transparent file:font-medium" /></label><button onClick={uploadAssignmentDocument} disabled={uploading || !selectedFile || !documentType} className="inline-flex items-end justify-center gap-2 rounded-lg bg-foreground px-4 py-2.5 text-sm font-semibold text-background disabled:cursor-not-allowed disabled:opacity-50"><Plus className="h-4 w-4" />{uploading ? "Uploading..." : "Upload"}</button></div></div>
                <div className="overflow-x-auto"><table className="w-full min-w-[980px] border-collapse text-sm"><thead className="bg-secondary/30"><tr className="border-b border-border text-left text-[11px] font-semibold uppercase tracking-wide text-muted-foreground"><th className="border-r border-border px-3 py-3">No.</th><th className="border-r border-border px-3 py-3">Code</th><th className="border-r border-border px-3 py-3">Description</th><th className="border-r border-border px-3 py-3">Required</th><th className="border-r border-border px-3 py-3">Mandatory</th><th className="border-r border-border px-3 py-3">Uploaded by</th><th className="border-r border-border px-3 py-3">Uploaded</th><th className="px-3 py-3 text-right">Actions</th></tr></thead><tbody className="divide-y divide-border">{documentRequirements.length === 0 ? <tr><td colSpan={8} className="px-4 py-8 text-center text-sm text-muted-foreground">No active document requirements are configured for this partner type.</td></tr> : documentRequirements.map((requirement, index) => { const matches = assignmentDocuments.filter((document) => document.documentType === requirement.code || document.documentName === requirement.code); const latest = matches[0]; return <tr key={requirement.id} className="transition hover:bg-secondary/20"><td className="border-r border-border px-3 py-3 text-muted-foreground">{index + 1}</td><td className="border-r border-border px-3 py-3 font-semibold text-foreground">{requirement.code}</td><td className="border-r border-border px-3 py-3 text-foreground">{requirement.description || "—"}</td><td className="border-r border-border px-3 py-3">{requirement.isRequired ? <span className="font-semibold text-foreground">Yes</span> : "No"}</td><td className="border-r border-border px-3 py-3">{requirement.isMandatory ? <span className="font-semibold text-foreground">Yes</span> : "No"}</td><td className="border-r border-border px-3 py-3 text-muted-foreground">{latest?.uploadedBy || "—"}</td><td className="border-r border-border px-3 py-3">{latest ? <span className="font-semibold text-foreground">Yes</span> : <span className="font-semibold text-muted-foreground">No</span>}</td><td className="px-3 py-3 text-right">{latest ? <div className="flex justify-end gap-2"><a href={latest.file} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 rounded-md border border-border px-2 py-1.5 text-xs font-semibold hover:bg-secondary"><Eye className="h-3.5 w-3.5" />View</a><button onClick={() => removeAssignmentDocument(latest.id, latest.documentName)} disabled={uploading} className="rounded-md border border-border px-2 py-1.5 text-xs font-semibold text-muted-foreground hover:bg-secondary hover:text-foreground disabled:opacity-50">Remove</button></div> : <button onClick={() => { setDocumentType(requirement.code); document.getElementById(`partner-document-file-${assignment.id}`)?.focus() }} className="inline-flex items-center gap-1 rounded-md border border-border px-2 py-1.5 text-xs font-semibold hover:bg-secondary"><Plus className="h-3.5 w-3.5" />Upload</button>}</td></tr> })}</tbody></table></div>
              </section>}

              {!setupLoading && activeSection === "attributes" && <section className="rounded-xl border border-border bg-card">
                <div className="flex flex-col gap-3 border-b border-border px-4 py-4 sm:flex-row sm:items-start sm:justify-between sm:px-5"><div><h3 className="text-base font-semibold text-foreground">Partner Type Attributes Form</h3><p className="mt-1 text-sm text-muted-foreground">All fields are rendered from the active field configurations under system parameters.</p></div><button type="button" onClick={() => void saveConfiguredFields()} disabled={fieldConfigurations.length === 0} className="inline-flex items-center justify-center gap-2 rounded-lg bg-foreground px-3 py-2 text-sm font-semibold text-background disabled:cursor-not-allowed disabled:opacity-50"><Save className="h-4 w-4" />Save attributes</button></div>
                <div className="p-4 sm:p-5">{fieldConfigurations.length === 0 ? <p className="rounded-lg border border-dashed border-border px-4 py-8 text-center text-sm text-muted-foreground">No active attribute fields are configured for this partner type.</p> : <div className="grid gap-5 md:grid-cols-2">{fieldConfigurations.map((config) => <label key={config.id} className="space-y-2 text-sm font-medium text-foreground"><span className="flex items-center justify-between gap-3"><span>{config.fieldName}{config.isRequired ? <span className="ml-1 text-foreground">*</span> : null}</span><span className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">{config.fieldCode} · {config.fieldType}</span></span>{renderDynamicField(config)}{config.visibilityRules && Object.keys(config.visibilityRules).length > 0 ? <span className="block text-[11px] font-normal text-muted-foreground">Visibility is controlled by the configured parameter rules.</span> : null}</label>)}</div>}</div>
              </section>}

              {!setupLoading && activeSection === "contacts" && <section className="rounded-xl border border-border bg-card">
                <div className="flex flex-col gap-3 border-b border-border px-4 py-4 sm:flex-row sm:items-start sm:justify-between sm:px-5"><div><h3 className="text-base font-semibold text-foreground">Partner Type Contacts</h3><p className="mt-1 text-sm text-muted-foreground">Contact roles, requiredness, ordering, and multiplicity come from parameter settings.</p></div><span className="rounded-full border border-border px-3 py-1 text-xs font-semibold text-foreground">{completedContacts}/{contactRequirements.length} requirements covered</span></div>
                <div className="border-b border-border bg-secondary/20 p-4 sm:p-5"><div className="mb-3 flex items-center justify-between gap-3"><p className="text-sm font-semibold text-foreground">{editingContactId ? "Update contact" : "Add contact"}</p>{editingContactId ? <button type="button" onClick={resetContactDraft} className="text-xs font-semibold text-muted-foreground underline">Cancel edit</button> : null}</div><div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4"><label className="space-y-1.5 text-xs font-semibold text-muted-foreground">Configured role<select value={contactDraft.requirement} onChange={(event) => setContactDraft((prev) => ({ ...prev, requirement: event.target.value }))} className="w-full rounded-lg border border-input bg-background px-3 py-2.5 text-sm font-normal text-foreground"><option value="">Select role</option>{contactRequirements.filter((item) => item.multipleAllowed || editingContactId || !assignmentContacts.some((contact) => contact.contactRequirement === item.id)).map((item) => <option key={item.id} value={item.id}>{item.contactType}{item.isRequired ? " · Required" : ""}{item.multipleAllowed ? " · Multiple" : ""}</option>)}</select></label><label className="space-y-1.5 text-xs font-semibold text-muted-foreground">First name<input value={contactDraft.firstName} onChange={(event) => setContactDraft((prev) => ({ ...prev, firstName: event.target.value }))} className="w-full rounded-lg border border-input bg-background px-3 py-2.5 text-sm font-normal text-foreground" /></label><label className="space-y-1.5 text-xs font-semibold text-muted-foreground">Last name<input value={contactDraft.lastName} onChange={(event) => setContactDraft((prev) => ({ ...prev, lastName: event.target.value }))} className="w-full rounded-lg border border-input bg-background px-3 py-2.5 text-sm font-normal text-foreground" /></label><label className="space-y-1.5 text-xs font-semibold text-muted-foreground">Designation<input value={contactDraft.designation} onChange={(event) => setContactDraft((prev) => ({ ...prev, designation: event.target.value }))} className="w-full rounded-lg border border-input bg-background px-3 py-2.5 text-sm font-normal text-foreground" /></label><label className="space-y-1.5 text-xs font-semibold text-muted-foreground">Email<input value={contactDraft.email} onChange={(event) => setContactDraft((prev) => ({ ...prev, email: event.target.value }))} type="email" className="w-full rounded-lg border border-input bg-background px-3 py-2.5 text-sm font-normal text-foreground" /></label><label className="space-y-1.5 text-xs font-semibold text-muted-foreground">Telephone<input value={contactDraft.phone} onChange={(event) => setContactDraft((prev) => ({ ...prev, phone: event.target.value }))} className="w-full rounded-lg border border-input bg-background px-3 py-2.5 text-sm font-normal text-foreground" /></label><label className="space-y-1.5 text-xs font-semibold text-muted-foreground">Mobile<input value={contactDraft.mobile} onChange={(event) => setContactDraft((prev) => ({ ...prev, mobile: event.target.value }))} className="w-full rounded-lg border border-input bg-background px-3 py-2.5 text-sm font-normal text-foreground" /></label><label className="flex items-center gap-2 rounded-lg border border-input bg-background px-3 py-2.5 text-sm font-normal"><input type="checkbox" checked={contactDraft.isPrimary} onChange={(event) => setContactDraft((prev) => ({ ...prev, isPrimary: event.target.checked }))} className="h-4 w-4 accent-black" /> Primary contact</label></div><div className="mt-3 flex justify-end"><button type="button" onClick={() => void saveContact()} className="inline-flex items-center gap-2 rounded-lg bg-foreground px-4 py-2.5 text-sm font-semibold text-background"><Plus className="h-4 w-4" />{editingContactId ? "Update contact" : "Add contact"}</button></div></div>
                <div className="overflow-x-auto"><table className="w-full min-w-[820px] border-collapse text-sm"><thead className="bg-secondary/30"><tr className="border-b border-border text-left text-[11px] font-semibold uppercase tracking-wide text-muted-foreground"><th className="border-r border-border px-3 py-3">Configured role</th><th className="border-r border-border px-3 py-3">Contact</th><th className="border-r border-border px-3 py-3">Designation</th><th className="border-r border-border px-3 py-3">Email / Mobile</th><th className="px-3 py-3 text-right">Actions</th></tr></thead><tbody className="divide-y divide-border">{assignmentContacts.length === 0 ? <tr><td colSpan={5} className="px-4 py-8 text-center text-sm text-muted-foreground">No contacts captured for this partner type yet.</td></tr> : assignmentContacts.map((contact) => <tr key={contact.id} className="transition hover:bg-secondary/20"><td className="border-r border-border px-3 py-3 font-medium">{contactRequirements.find((item) => item.id === contact.contactRequirement)?.contactType ?? contact.contactType}</td><td className="border-r border-border px-3 py-3">{contact.firstName} {contact.lastName}{contact.isPrimary ? <span className="ml-2 rounded-full border border-border px-2 py-0.5 text-[10px] font-semibold">Primary</span> : null}</td><td className="border-r border-border px-3 py-3 text-muted-foreground">{contact.designation || "—"}</td><td className="border-r border-border px-3 py-3 text-muted-foreground">{contact.email || contact.mobile || contact.phone || "—"}</td><td className="px-3 py-3 text-right"><button type="button" onClick={() => editContact(contact)} className="mr-3 inline-flex items-center gap-1 text-xs font-semibold underline"><Pencil className="h-3.5 w-3.5" />Edit</button><button type="button" onClick={() => void removeContact(contact)} className="inline-flex items-center gap-1 text-xs font-semibold text-muted-foreground underline"><Trash2 className="h-3.5 w-3.5" />Remove</button></td></tr>)}</tbody></table></div>
              </section>}

              {!setupLoading && activeSection === "banks" && <section className="rounded-xl border border-border bg-card">
                <div className="flex flex-col gap-3 border-b border-border px-4 py-4 sm:flex-row sm:items-start sm:justify-between sm:px-5"><div><h3 className="text-base font-semibold text-foreground">Partner Type Banks</h3><p className="mt-1 text-sm text-muted-foreground">Bank roles and validation rules are loaded from the partner type parameter configuration.</p></div><span className="rounded-full border border-border px-3 py-1 text-xs font-semibold text-foreground">{completedBanks}/{bankRequirements.length} requirements covered</span></div>
                <div className="border-b border-border bg-secondary/20 p-4 sm:p-5"><div className="mb-3 flex items-center justify-between gap-3"><p className="text-sm font-semibold text-foreground">{editingBankId ? "Update bank account" : "Add bank account"}</p>{editingBankId ? <button type="button" onClick={resetBankDraft} className="text-xs font-semibold text-muted-foreground underline">Cancel edit</button> : null}</div><div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4"><label className="space-y-1.5 text-xs font-semibold text-muted-foreground">Configured bank role<select value={bankDraft.requirement} onChange={(event) => setBankDraft((prev) => ({ ...prev, requirement: event.target.value }))} className="w-full rounded-lg border border-input bg-background px-3 py-2.5 text-sm font-normal text-foreground"><option value="">Select role</option>{bankRequirements.filter((item) => item.multipleAllowed || editingBankId || !assignmentBanks.some((bank) => bank.bankRequirement === item.id)).map((item) => <option key={item.id} value={item.id}>{item.bankType}{item.isRequired ? " · Required" : ""}{item.multipleAllowed ? " · Multiple" : ""}</option>)}</select></label><label className="space-y-1.5 text-xs font-semibold text-muted-foreground">Bank name<input value={bankDraft.bankName} onChange={(event) => setBankDraft((prev) => ({ ...prev, bankName: event.target.value }))} className="w-full rounded-lg border border-input bg-background px-3 py-2.5 text-sm font-normal text-foreground" /></label><label className="space-y-1.5 text-xs font-semibold text-muted-foreground">Branch<input value={bankDraft.branchName} onChange={(event) => setBankDraft((prev) => ({ ...prev, branchName: event.target.value }))} className="w-full rounded-lg border border-input bg-background px-3 py-2.5 text-sm font-normal text-foreground" /></label><label className="space-y-1.5 text-xs font-semibold text-muted-foreground">Account name<input value={bankDraft.accountName} onChange={(event) => setBankDraft((prev) => ({ ...prev, accountName: event.target.value }))} className="w-full rounded-lg border border-input bg-background px-3 py-2.5 text-sm font-normal text-foreground" /></label><label className="space-y-1.5 text-xs font-semibold text-muted-foreground">Account number<input value={bankDraft.accountNumber} onChange={(event) => setBankDraft((prev) => ({ ...prev, accountNumber: event.target.value }))} className="w-full rounded-lg border border-input bg-background px-3 py-2.5 text-sm font-normal text-foreground" /></label><label className="space-y-1.5 text-xs font-semibold text-muted-foreground">SWIFT code<input value={bankDraft.swiftCode} onChange={(event) => setBankDraft((prev) => ({ ...prev, swiftCode: event.target.value }))} className="w-full rounded-lg border border-input bg-background px-3 py-2.5 text-sm font-normal text-foreground" /></label><label className="space-y-1.5 text-xs font-semibold text-muted-foreground">Currency<input value={bankDraft.currency} onChange={(event) => setBankDraft((prev) => ({ ...prev, currency: event.target.value }))} className="w-full rounded-lg border border-input bg-background px-3 py-2.5 text-sm font-normal text-foreground" /></label><label className="flex items-center gap-2 rounded-lg border border-input bg-background px-3 py-2.5 text-sm font-normal"><input type="checkbox" checked={bankDraft.isPrimary} onChange={(event) => setBankDraft((prev) => ({ ...prev, isPrimary: event.target.checked }))} className="h-4 w-4 accent-black" /> Primary account</label></div><div className="mt-3 flex justify-end"><button type="button" onClick={() => void saveBank()} className="inline-flex items-center gap-2 rounded-lg bg-foreground px-4 py-2.5 text-sm font-semibold text-background"><Plus className="h-4 w-4" />{editingBankId ? "Update bank account" : "Add bank account"}</button></div></div>
                <div className="overflow-x-auto"><table className="w-full min-w-[900px] border-collapse text-sm"><thead className="bg-secondary/30"><tr className="border-b border-border text-left text-[11px] font-semibold uppercase tracking-wide text-muted-foreground"><th className="border-r border-border px-3 py-3">Configured role</th><th className="border-r border-border px-3 py-3">Bank</th><th className="border-r border-border px-3 py-3">Account</th><th className="border-r border-border px-3 py-3">Currency</th><th className="px-3 py-3 text-right">Actions</th></tr></thead><tbody className="divide-y divide-border">{assignmentBanks.length === 0 ? <tr><td colSpan={5} className="px-4 py-8 text-center text-sm text-muted-foreground">No bank accounts captured for this partner type yet.</td></tr> : assignmentBanks.map((bank) => <tr key={bank.id} className="transition hover:bg-secondary/20"><td className="border-r border-border px-3 py-3 font-medium">{bankRequirements.find((item) => item.id === bank.bankRequirement)?.bankType ?? bank.bankRequirement ?? "Configured bank"}</td><td className="border-r border-border px-3 py-3">{bank.bankName}<span className="block text-xs text-muted-foreground">{bank.branchName || "No branch"}</span></td><td className="border-r border-border px-3 py-3">{bank.accountName}<span className="block text-xs text-muted-foreground">{bank.accountNumber}{bank.isPrimary ? " · Primary" : ""}</span></td><td className="border-r border-border px-3 py-3 text-muted-foreground">{bank.currency || "—"}</td><td className="px-3 py-3 text-right"><button type="button" onClick={() => editBank(bank)} className="mr-3 inline-flex items-center gap-1 text-xs font-semibold underline"><Pencil className="h-3.5 w-3.5" />Edit</button><button type="button" onClick={() => void removeBank(bank)} className="inline-flex items-center gap-1 text-xs font-semibold text-muted-foreground underline"><Trash2 className="h-3.5 w-3.5" />Remove</button></td></tr>)}</tbody></table></div>
              </section>}

              {(error || notice) && <div className={`rounded-lg border px-3 py-2.5 text-sm ${error ? "border-destructive/30 bg-destructive/5 text-destructive" : "border-border bg-secondary/30 text-foreground"}`}>{error || notice}</div>}
            </div>

            <aside className="h-fit rounded-xl border border-border bg-card p-4 sm:p-5 xl:sticky xl:top-0"><p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">Setup progress</p><h3 className="mt-1 text-base font-semibold text-foreground">{assignment.partnerTypeName}</h3><div className="mt-5 space-y-3">{steps.map((step) => { const current = step.key === activeSection; const count = step.key === "documents" ? `${completedDocuments}/${documentRequirements.length}` : step.key === "attributes" ? `${completedFields}/${fieldConfigurations.length}` : step.key === "contacts" ? `${completedContacts}/${contactRequirements.length}` : `${completedBanks}/${bankRequirements.length}`; return <button key={step.key} type="button" onClick={() => setActiveSection(step.key)} className={`flex w-full items-center justify-between gap-3 rounded-lg border px-3 py-3 text-left transition ${current ? "border-foreground bg-foreground text-background" : "border-border hover:bg-secondary"}`}><span className="flex items-center gap-2">{step.icon}<span className="text-sm font-semibold">{step.shortLabel}</span></span><span className="text-xs font-semibold opacity-75">{count}</span></button> })}</div><div className="mt-5 border-t border-border pt-4"><dl className="space-y-3 text-sm"><div className="flex justify-between gap-3"><dt className="text-muted-foreground">Branch</dt><dd className="text-right font-medium text-foreground">{assignment.branchName || "Not assigned"}</dd></div><div className="flex justify-between gap-3"><dt className="text-muted-foreground">Region</dt><dd className="text-right font-medium text-foreground">{assignment.region || "Not assigned"}</dd></div><div className="flex justify-between gap-3"><dt className="text-muted-foreground">Data sharing</dt><dd className="text-right font-medium text-foreground">{shareData ? "Enabled" : "Disabled"}</dd></div></dl></div><p className="mt-5 text-xs leading-5 text-muted-foreground">Configuration is read from system parameters. Every nested update is synchronized with the assignment and recorded in the audit/event history.</p></aside>
          </div>
        </div>

        <div className="flex flex-col gap-3 border-t border-border bg-card px-4 py-3 sm:flex-row sm:items-center sm:justify-between sm:px-6"><div className="flex items-center gap-2"><button type="button" onClick={() => void moveToStep(activeStepIndex - 1)} disabled={activeStepIndex <= 0 || setupLoading} className="inline-flex items-center gap-1 rounded-lg border border-border px-3 py-2 text-xs font-semibold text-foreground transition hover:bg-secondary disabled:cursor-not-allowed disabled:opacity-40"><ArrowLeft className="h-3.5 w-3.5" />Previous</button><button type="button" onClick={() => void moveToStep(activeStepIndex + 1)} disabled={activeStepIndex >= steps.length - 1 || setupLoading} className="inline-flex items-center gap-1 rounded-lg border border-border px-3 py-2 text-xs font-semibold text-foreground transition hover:bg-secondary disabled:cursor-not-allowed disabled:opacity-40">Next</button><span className="hidden text-xs text-muted-foreground sm:inline">Step {activeStepIndex + 1} of {steps.length}</span></div><div className="flex items-center justify-end gap-2"><button type="button" onClick={onClose} disabled={saving} className="rounded-lg border border-border px-4 py-2 text-sm font-medium text-foreground transition hover:bg-secondary disabled:opacity-50">Close</button><button type="button" onClick={() => void saveAssignment()} disabled={saving} className="inline-flex items-center gap-2 rounded-lg bg-foreground px-4 py-2 text-sm font-semibold text-background transition hover:opacity-90 disabled:opacity-50">{saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}{saving ? "Saving..." : "Save assignment"}</button></div></div>
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
