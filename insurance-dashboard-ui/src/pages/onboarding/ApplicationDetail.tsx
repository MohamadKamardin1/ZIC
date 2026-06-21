import { useCallback, useEffect, useState } from "react"
import { useNavigate, useParams } from "react-router-dom"
import {
  ArrowLeft,
  Edit3,
  Send,
  Eye,
  CheckCircle,
  XCircle,
  PauseCircle,
  PlayCircle,
  FileUp,
  CheckSquare,
  Plus,
  Loader2,
  Shield,
  FileText,
  ClipboardList,
  AlertTriangle,
  Download,
} from "lucide-react"
import {
  getApplication,
  submitApplication,
  startReview,
  sendToCompliance,
  approveApplication,
  rejectApplication,
  suspendApplication,
  resumeApplication,
  convertApplication,
  runCompliance,
  requestDocuments,
  verifyDocument,
  completeTask,
  createTask,
  uploadDocument,
  deleteDocument,
  listDocuments,
  listTasks,
} from "../../lib/api"
import type {
  PartnerApplicationDetail,
  ApplicationDocument,
  ApplicationTask,
  ApplicationStatus,
} from "../../lib/types"
import { STATUS_LABELS, STATUS_COLORS } from "../../lib/types"

const STATUS_FLOW: ApplicationStatus[] = [
  "DRAFT",
  "SUBMITTED",
  "UNDER_REVIEW",
  "PENDING_DOCUMENTS",
  "COMPLIANCE_CHECK",
  "APPROVED",
  "CONVERTED",
]

const TERMINAL_STATUSES: ApplicationStatus[] = ["CONVERTED", "REJECTED"]

export default function ApplicationDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const [app, setApp] = useState<PartnerApplicationDetail | null>(null)
  const [docs, setDocs] = useState<ApplicationDocument[]>([])
  const [tasks, setTasks] = useState<ApplicationTask[]>([])
  const [loading, setLoading] = useState(false)
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [error, setError] = useState("")
  const [tab, setTab] = useState<"details" | "documents" | "tasks">("details")
  const [showRejectModal, setShowRejectModal] = useState(false)
  const [rejectReason, setRejectReason] = useState("")
  const [complianceResult, setComplianceResult] = useState<{
    riskScore: number
    threshold: number
    isHighRisk: boolean
  } | null>(null)

  const load = useCallback(async () => {
    if (!id) return
    setLoading(true)
    setError("")
    try {
      const [appData, docsData, tasksData] = await Promise.all([
        getApplication(id),
        listDocuments(id),
        listTasks(id),
      ])
      setApp(appData)
      setDocs(docsData)
      setTasks(tasksData)
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load")
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    load()
  }, [load])

  async function doAction(action: string, fn: () => Promise<unknown>) {
    setActionLoading(action)
    setError("")
    try {
      await fn()
      load()
    } catch (e) {
      setError(e instanceof Error ? e.message : "Action failed")
    } finally {
      setActionLoading(null)
    }
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

  const statusIdx = STATUS_FLOW.indexOf(app.status)
  const isTerminal = TERMINAL_STATUSES.includes(app.status)

  /* ---- Action buttons per status ---- */
  const actions: { label: string; icon: React.ReactNode; fn: () => void; variant?: string }[] = []

  if (app.status === "DRAFT") {
    actions.push({
      label: "Submit",
      icon: <Send className="h-4 w-4" />,
      fn: () => doAction("submit", () => submitApplication(app.id)),
      variant: "bg-green-600 hover:bg-green-700 text-white",
    })
    actions.push({
      label: "Edit",
      icon: <Edit3 className="h-4 w-4" />,
      fn: () => navigate(`/onboarding/${app.id}/edit`),
    })
  }
  if (app.status === "SUBMITTED") {
    actions.push({
      label: "Start Review",
      icon: <Eye className="h-4 w-4" />,
      fn: () => doAction("start-review", () => startReview(app.id)),
      variant: "bg-primary hover:bg-primary/90 text-white",
    })
  }
  if (app.status === "UNDER_REVIEW") {
    actions.push({
      label: "Request Docs",
      icon: <FileUp className="h-4 w-4" />,
      fn: () => doAction("request-docs", () => requestDocuments(app.id, ["NID"])),
    })
    actions.push({
      label: "Send to Compliance",
      icon: <Shield className="h-4 w-4" />,
      fn: () => doAction("compliance", () => sendToCompliance(app.id)),
      variant: "bg-orange-500 hover:bg-orange-600 text-white",
    })
  }
  if (app.status === "PENDING_DOCUMENTS") {
    actions.push({
      label: "Re-review",
      icon: <Eye className="h-4 w-4" />,
      fn: () => doAction("re-review", () => startReview(app.id)),
    })
  }
  if (app.status === "COMPLIANCE_CHECK") {
    actions.push({
      label: "Approve",
      icon: <CheckCircle className="h-4 w-4" />,
      fn: () => doAction("approve", () => approveApplication(app.id)),
      variant: "bg-green-600 hover:bg-green-700 text-white",
    })
    actions.push({
      label: "Reject",
      icon: <XCircle className="h-4 w-4" />,
      fn: () => setShowRejectModal(true),
      variant: "bg-destructive hover:bg-destructive/90 text-white",
    })
    actions.push({
      label: "Suspend",
      icon: <PauseCircle className="h-4 w-4" />,
      fn: () => doAction("suspend", () => suspendApplication(app.id)),
    })
    actions.push({
      label: "Run Compliance",
      icon: <Shield className="h-4 w-4" />,
      fn: () =>
        doAction("compliance-check", () =>
          runCompliance(app.id).then((r) => setComplianceResult(r)),
        ),
    })
  }
  if (app.status === "SUSPENDED") {
    actions.push({
      label: "Resume",
      icon: <PlayCircle className="h-4 w-4" />,
      fn: () => doAction("resume", () => resumeApplication(app.id)),
      variant: "bg-primary hover:bg-primary/90 text-white",
    })
    actions.push({
      label: "Reject",
      icon: <XCircle className="h-4 w-4" />,
      fn: () => setShowRejectModal(true),
      variant: "bg-destructive hover:bg-destructive/90 text-white",
    })
  }
  if (app.status === "APPROVED") {
    actions.push({
      label: "Convert to Partner",
      icon: <CheckSquare className="h-4 w-4" />,
      fn: () => doAction("convert", () => convertApplication(app.id)),
      variant: "bg-emerald-600 hover:bg-emerald-700 text-white",
    })
  }

  return (
    <div className="flex flex-col gap-5">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate("/onboarding")}
            className="rounded-lg p-2 text-muted-foreground transition hover:bg-secondary hover:text-foreground"
          >
            <ArrowLeft className="h-5 w-5" />
          </button>
          <div>
            <h1 className="text-xl font-bold text-foreground">{app.displayName}</h1>
            <p className="text-sm text-muted-foreground">
              {app.applicationNumber} · {app.partnerType === "INDIVIDUAL" ? "Individual" : "Corporate"}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span
            className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${STATUS_COLORS[app.status]}`}
          >
            {STATUS_LABELS[app.status]}
          </span>
          {actions.map((a) => (
            <button
              key={a.label}
              onClick={a.fn}
              disabled={!!actionLoading}
              className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium transition disabled:opacity-50 ${
                a.variant ?? "border border-input bg-card text-foreground hover:bg-secondary"
              }`}
            >
              {actionLoading === a.label.toLowerCase().replace(/\s/g, "-") ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                a.icon
              )}
              {a.label}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm font-medium text-destructive">
          {error}
        </div>
      )}

      {/* Compliance result */}
      {complianceResult && (
        <div
          className={`rounded-xl border px-4 py-3 text-sm font-medium ${
            complianceResult.isHighRisk
              ? "border-red-300 bg-red-50 text-red-700"
              : "border-green-300 bg-green-50 text-green-700"
          }`}
        >
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4" />
            Risk Score: {complianceResult.riskScore} / {complianceResult.threshold} —{" "}
            {complianceResult.isHighRisk ? "HIGH RISK" : "OK"}
          </div>
        </div>
      )}

      {/* Status timeline */}
      <div className="rounded-xl border border-border bg-card p-4">
        <div className="flex items-center gap-1 overflow-x-auto">
          {STATUS_FLOW.map((s, i) => {
            const done = i < statusIdx
            const current = s === app.status
            return (
              <div key={s} className="flex items-center">
                <div
                  className={`flex h-8 min-w-24 items-center justify-center rounded-full px-3 text-xs font-semibold ${
                    current
                      ? "bg-primary text-primary-foreground"
                      : done
                        ? "bg-green-100 text-green-700"
                        : "bg-muted text-muted-foreground"
                  }`}
                >
                  {STATUS_LABELS[s]}
                </div>
                {i < STATUS_FLOW.length - 1 && (
                  <div
                    className={`mx-1 h-0.5 w-6 flex-none ${done ? "bg-green-300" : "bg-border"}`}
                  />
                )}
              </div>
            )
          })}
          {isTerminal && app.status === "REJECTED" && (
            <>
              <div className="mx-1 h-0.5 w-6 flex-none bg-red-300" />
              <div className="flex h-8 min-w-24 items-center justify-center rounded-full bg-red-100 px-3 text-xs font-semibold text-red-700">
                Rejected
              </div>
            </>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 rounded-lg bg-muted p-1 w-fit">
        {[
          { key: "details" as const, label: "Details", icon: <FileText className="h-4 w-4" /> },
          { key: "documents" as const, label: `Docs (${docs.length})`, icon: <ClipboardList className="h-4 w-4" /> },
          { key: "tasks" as const, label: `Tasks (${tasks.length})`, icon: <Plus className="h-4 w-4" /> },
        ].map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition ${
              tab === t.key ? "bg-card text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"
            }`}
          >
            {t.icon}
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {tab === "details" && <DetailsTab app={app} />}
      {tab === "documents" && <DocumentsTab docs={docs} applicationId={app.id} status={app.status} onRefresh={() => load()} />}
      {tab === "tasks" && <TasksTab tasks={tasks} applicationId={app.id} onRefresh={() => load()} />}

      {/* Reject modal */}
      {showRejectModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="w-full max-w-md rounded-xl bg-card p-6 shadow-xl">
            <h3 className="text-lg font-semibold text-foreground">Reject Application</h3>
            <p className="mt-1 text-sm text-muted-foreground">
              Provide a reason for rejection.
            </p>
            <textarea
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              rows={4}
              className="mt-4 w-full rounded-lg border border-input bg-secondary/60 px-3 py-2.5 text-sm text-foreground outline-none focus:ring-2 focus:ring-ring/40"
              placeholder="Rejection reason..."
              autoFocus
            />
            <div className="mt-4 flex gap-3">
              <button
                onClick={() => {
                  setShowRejectModal(false)
                  setRejectReason("")
                }}
                className="flex-1 rounded-lg border border-input py-2.5 text-sm font-medium text-foreground transition hover:bg-secondary"
              >
                Cancel
              </button>
              <button
                disabled={!rejectReason.trim() || !!actionLoading}
                onClick={() => {
                  setShowRejectModal(false)
                  doAction("reject", () => rejectApplication(app.id, rejectReason))
                  setRejectReason("")
                }}
                className="flex-1 rounded-lg bg-destructive py-2.5 text-sm font-semibold text-white transition hover:bg-destructive/90 disabled:opacity-50"
              >
                Reject
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

/* -------------------------------------------------------------------------- */
/*  DetailsTab                                                                 */
/* -------------------------------------------------------------------------- */

function DetailsTab({ app }: { app: PartnerApplicationDetail }) {
  const rows: { label: string; value: string }[] = [
    { label: "Application Number", value: app.applicationNumber },
    { label: "Partner Type", value: app.partnerType === "INDIVIDUAL" ? "Individual" : "Corporate" },
    { label: "Status", value: STATUS_LABELS[app.status] },
  ]

  if (app.partnerType === "INDIVIDUAL") {
    rows.push(
      { label: "Name", value: `${app.title} ${app.firstName} ${app.otherName} ${app.surname}`.trim() },
      { label: "ID Type", value: app.identificationType || "—" },
      { label: "ID Number", value: app.identificationNumber || "—" },
      { label: "Gender", value: app.gender || "—" },
      { label: "Date of Birth", value: app.dateOfBirth || "—" },
      { label: "Marital Status", value: app.maritalStatus || "—" },
      { label: "Occupation", value: app.occupation || "—" },
      { label: "Nationality", value: app.nationality || "—" },
    )
  } else {
    rows.push(
      { label: "Company", value: app.companyName || "—" },
      { label: "TIN", value: app.tinNumber || "—" },
      { label: "Incorporation Date", value: app.incorporationDate || "—" },
      { label: "Industry", value: app.industry || "—" },
      { label: "Contact Person", value: app.contactPerson || "—" },
      { label: "Contact Phone", value: app.contactPersonPhone || "—" },
      { label: "Contact Email", value: app.contactPersonEmail || "—" },
    )
  }

  rows.push(
    { label: "Email", value: app.email },
    { label: "Mobile", value: app.mobileNumber },
    { label: "Telephone", value: app.telephoneNumber || "—" },
    { label: "Physical Address", value: app.physicalAddress || "—" },
    { label: "Postal Address", value: app.postalAddress || "—" },
    { label: "Political Risk", value: app.politicalRisk },
    { label: "AML Risk", value: app.amlRisk },
  )

  if (app.rejectionReason) rows.push({ label: "Rejection Reason", value: app.rejectionReason })
  if (app.complianceNotes) rows.push({ label: "Compliance Notes", value: app.complianceNotes })

  return (
    <div className="max-w-3xl rounded-xl border border-border bg-card p-6">
      <dl className="space-y-3 text-sm">
        {rows.map((r) => (
          <div key={r.label} className="flex justify-between border-b border-border/50 pb-2">
            <dt className="text-muted-foreground">{r.label}</dt>
            <dd className="font-medium text-foreground">{r.value}</dd>
          </div>
        ))}
      </dl>
    </div>
  )
}

/* -------------------------------------------------------------------------- */
/*  DocumentsTab                                                               */
/* -------------------------------------------------------------------------- */

function DocumentsTab({
  docs,
  applicationId,
  status,
  onRefresh,
}: {
  docs: ApplicationDocument[]
  applicationId: string
  status: ApplicationStatus
  onRefresh: () => void
}) {
  const [uploading, setUploading] = useState(false)
  const [docType, setDocType] = useState("NID")
  const [verifying, setVerifying] = useState<string | null>(null)

  const DOC_TYPES = [
    { value: "NID", label: "National ID" },
    { value: "PASSPORT", label: "Passport" },
    { value: "TIN_CERTIFICATE", label: "TIN Certificate" },
    { value: "INCORPORATION_CERT", label: "Incorporation Cert" },
    { value: "MEMORANDUM", label: "Memorandum" },
    { value: "BOARD_RESOLUTION", label: "Board Resolution" },
    { value: "DRIVING_LICENSE", label: "Driving License" },
    { value: "OTHER", label: "Other" },
  ]

  async function handleUpload(file: File) {
    setUploading(true)
    try {
      await uploadDocument(applicationId, file, docType)
      onRefresh()
    } catch {}
    finally {
      setUploading(false)
    }
  }

  async function handleVerify(docId: string) {
    setVerifying(docId)
    try {
      await verifyDocument(applicationId, docId)
      onRefresh()
    } catch {}
    finally {
      setVerifying(null)
    }
  }

  async function handleDelete(docId: string) {
    if (!confirm("Delete this document?")) return
    try {
      await deleteDocument(applicationId, docId)
      onRefresh()
    } catch {}
  }

  return (
    <div className="rounded-xl border border-border bg-card p-6">
      {/* Upload row */}
      <div className="flex flex-wrap items-center gap-3">
        <select
          value={docType}
          onChange={(e) => setDocType(e.target.value)}
          className="rounded-lg border border-input bg-card px-3 py-2 text-sm text-foreground"
        >
          {DOC_TYPES.map((d) => (
            <option key={d.value} value={d.value}>
              {d.label}
            </option>
          ))}
        </select>
        <label className="inline-flex cursor-pointer items-center gap-2 rounded-lg border border-input bg-card px-4 py-2 text-sm font-medium text-foreground transition hover:bg-secondary">
          <FileUp className="h-4 w-4" />
          Upload
          <input
            type="file"
            accept=".pdf,.jpg,.jpeg,.png,.doc,.docx"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0]
              if (file) handleUpload(file)
            }}
            disabled={uploading}
          />
        </label>
        {uploading && <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />}
      </div>

      {docs.length === 0 ? (
        <p className="mt-6 text-center text-sm text-muted-foreground">No documents uploaded.</p>
      ) : (
        <ul className="mt-4 divide-y divide-border">
          {docs.map((d) => (
            <li key={d.id} className="flex items-center gap-3 py-3">
              <FileText className="h-4 w-4 text-muted-foreground" />
              <div className="min-w-0 flex-1">
                <div className="truncate text-sm font-medium text-foreground">{d.documentName}</div>
                <div className="text-xs text-muted-foreground">
                  {DOC_TYPES.find((t) => t.value === d.documentType)?.label ?? d.documentType}
                  {d.fileSize ? ` · ${(d.fileSize / 1024).toFixed(0)} KB` : ""}
                </div>
              </div>
              {d.isVerified ? (
                <span className="text-xs font-semibold text-green-600">Verified</span>
              ) : (
                <button
                  onClick={() => handleVerify(d.id)}
                  disabled={verifying === d.id}
                  className="rounded px-2 py-1 text-xs font-medium text-primary hover:bg-primary/10 disabled:opacity-50"
                >
                  {verifying === d.id ? <Loader2 className="h-3 w-3 animate-spin" /> : "Verify"}
                </button>
              )}
              {status === "DRAFT" && (
                <button
                  onClick={() => handleDelete(d.id)}
                  className="rounded p-1 text-muted-foreground hover:text-destructive"
                >
                  <FileText className="h-3.5 w-3.5" />
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

/* -------------------------------------------------------------------------- */
/*  TasksTab                                                                   */
/* -------------------------------------------------------------------------- */

function TasksTab({
  tasks,
  applicationId,
  onRefresh,
}: {
  tasks: ApplicationTask[]
  applicationId: string
  onRefresh: () => void
}) {
  const [showNew, setShowNew] = useState(false)
  const [newTitle, setNewTitle] = useState("")
  const [newType, setNewType] = useState("REVIEW")
  const [newPriority, setNewPriority] = useState("MEDIUM")
  const [newDue, setNewDue] = useState("")

  const PRIORITY_COLORS: Record<string, string> = {
    URGENT: "text-red-600",
    HIGH: "text-orange-600",
    MEDIUM: "text-amber-600",
    LOW: "text-muted-foreground",
  }

  async function handleCreate() {
    if (!newTitle.trim()) return
    try {
      await createTask(applicationId, {
        taskType: newType,
        title: newTitle,
        priority: newPriority,
        dueDate: newDue || undefined,
      })
      setShowNew(false)
      setNewTitle("")
      onRefresh()
    } catch {}
  }

  async function handleComplete(taskId: string) {
    try {
      await completeTask(applicationId, taskId)
      onRefresh()
    } catch {}
  }

  return (
    <div className="rounded-xl border border-border bg-card p-6">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-foreground">Tasks</h3>
        <button
          onClick={() => setShowNew((s) => !s)}
          className="inline-flex items-center gap-1 rounded-lg border border-input px-3 py-1.5 text-xs font-medium text-foreground transition hover:bg-secondary"
        >
          <Plus className="h-3 w-3" />
          New Task
        </button>
      </div>

      {showNew && (
        <div className="mt-4 flex flex-wrap gap-2 rounded-lg bg-secondary/40 p-3">
          <input
            value={newTitle}
            onChange={(e) => setNewTitle(e.target.value)}
            placeholder="Task title..."
            className="flex-1 rounded-lg border border-input bg-card px-3 py-1.5 text-sm text-foreground"
          />
          <select
            value={newType}
            onChange={(e) => setNewType(e.target.value)}
            className="rounded-lg border border-input bg-card px-2 py-1.5 text-sm text-foreground"
          >
            <option value="REVIEW">Review</option>
            <option value="DOCUMENT_REQUEST">Doc Request</option>
            <option value="COMPLIANCE_CHECK">Compliance</option>
            <option value="APPROVAL">Approval</option>
            <option value="OTHER">Other</option>
          </select>
          <select
            value={newPriority}
            onChange={(e) => setNewPriority(e.target.value)}
            className="rounded-lg border border-input bg-card px-2 py-1.5 text-sm text-foreground"
          >
            <option value="LOW">Low</option>
            <option value="MEDIUM">Medium</option>
            <option value="HIGH">High</option>
            <option value="URGENT">Urgent</option>
          </select>
          <input
            type="date"
            value={newDue}
            onChange={(e) => setNewDue(e.target.value)}
            className="rounded-lg border border-input bg-card px-2 py-1.5 text-sm text-foreground"
          />
          <button
            onClick={handleCreate}
            className="rounded-lg bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground"
          >
            Create
          </button>
        </div>
      )}

      {tasks.length === 0 ? (
        <p className="mt-4 text-center text-sm text-muted-foreground">No tasks yet.</p>
      ) : (
        <ul className="mt-4 divide-y divide-border">
          {tasks.map((t) => (
            <li key={t.id} className="flex items-center gap-3 py-3">
              <div className="flex-1">
                <div className="text-sm font-medium text-foreground">{t.title}</div>
                <div className="text-xs text-muted-foreground">
                  {t.taskType} · {PRIORITY_COLORS[t.priority]} {t.priority}
                  {t.dueDate ? ` · Due ${t.dueDate}` : ""}
                </div>
              </div>
              <span
                className={`rounded-full px-2 py-0.5 text-xs font-semibold ${
                  t.status === "COMPLETED"
                    ? "bg-green-100 text-green-700"
                    : t.status === "IN_PROGRESS"
                      ? "bg-blue-100 text-blue-700"
                      : t.status === "CANCELLED"
                        ? "bg-gray-100 text-gray-600"
                        : "bg-amber-100 text-amber-700"
                }`}
              >
                {t.status.replace("_", " ")}
              </span>
              {t.status !== "COMPLETED" && t.status !== "CANCELLED" && (
                <button
                  onClick={() => handleComplete(t.id)}
                  className="rounded px-2 py-1 text-xs font-medium text-green-600 hover:bg-green-50"
                >
                  Complete
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
