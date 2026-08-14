import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { ArrowLeft, ArrowRight, Check, ClipboardList, FilePlus2, RefreshCw, X } from "lucide-react"
import { useNavigate } from "react-router-dom"
import { olWorkflow, type OrdinaryLifeResource } from "../../lib/ol-api"
import "../../lit/ordinary-life-workspace"

type WorkspaceKey =
  | "applications"
  | "quotations"
  | "proposals"
  | "policies"
  | "commitments"
  | "loans"
  | "withdrawals"
  | "claims"
  | "maturity-installments"
  | "documents"
  | "notes"
  | "approvals"
  | "audit-history"

type Row = Record<string, unknown>
type EventDetail = { row?: Row }
type FormState = Record<string, string>

type WorkspaceConfig = {
  title: string
  eyebrow: string
  description: string
  resource: OrdinaryLifeResource
  columns: { key: string; label: string; emphasis?: boolean; muted?: boolean }[]
  statusOptions: string[]
  primaryLabel: string
  primaryMode: "application" | "quotation" | "issue" | "refresh"
}

const configs: Record<WorkspaceKey, WorkspaceConfig> = {
  applications: {
    title: "Application intake",
    eyebrow: "Ordinary Life / Front office",
    description: "Capture canonical parties, declarations, and the controlled route from intake to quotation.",
    resource: "applications",
    columns: [
      { key: "application_number", label: "Application", emphasis: true },
      { key: "partner_name", label: "Partner" },
      { key: "policyholder_name", label: "Policyholder" },
      { key: "status", label: "Status" },
      { key: "created_at", label: "Created", muted: true },
    ],
    statusOptions: ["DRAFT", "SUBMITTED", "CONVERTED", "REJECTED"],
    primaryLabel: "New application",
    primaryMode: "application",
  },
  quotations: {
    title: "Quotation register",
    eyebrow: "Ordinary Life / Commercial",
    description: "Immutable, versioned quotations with transparent premium and conversion checkpoints.",
    resource: "quotations",
    columns: [
      { key: "quotation_number", label: "Quotation", emphasis: true },
      { key: "application", label: "Application" },
      { key: "sum_assured", label: "Sum assured" },
      { key: "premium_amount", label: "Premium" },
      { key: "status", label: "Status" },
    ],
    statusOptions: ["DRAFT", "SUBMITTED", "EXPIRED", "CONVERTED"],
    primaryLabel: "New quotation",
    primaryMode: "quotation",
  },
  proposals: {
    title: "Proposal & underwriting queue",
    eyebrow: "Ordinary Life / Risk",
    description: "Move proposals through underwriting, medical evidence, and controlled approval decisions.",
    resource: "proposals",
    columns: [
      { key: "proposal_number", label: "Proposal", emphasis: true },
      { key: "quotation_number", label: "Quotation" },
      { key: "underwriting_status", label: "Underwriting" },
      { key: "status", label: "Status" },
      { key: "created_at", label: "Created", muted: true },
    ],
    statusOptions: ["DRAFT", "SUBMITTED", "UNDERWRITING", "APPROVAL_PENDING", "APPROVED", "DECLINED"],
    primaryLabel: "Refresh queue",
    primaryMode: "refresh",
  },
  policies: {
    title: "Policy servicing",
    eyebrow: "Ordinary Life / In force",
    description: "Issue policies from approved proposals and operate post-issuance servicing with a complete transaction trail.",
    resource: "policies",
    columns: [
      { key: "policy_number", label: "Policy", emphasis: true },
      { key: "proposal_number", label: "Proposal" },
      { key: "status", label: "Status" },
      { key: "premium_amount", label: "Premium" },
      { key: "start_date", label: "Start date", muted: true },
    ],
    statusOptions: ["ACTIVE", "GRACE", "LAPSED", "REACTIVATED", "CANCELLED", "MATURED"],
    primaryLabel: "Issue policy",
    primaryMode: "issue",
  },
  commitments: {
    title: "Commitment control",
    eyebrow: "Ordinary Life / Finance",
    description: "Monitor commitments and obligations created by proposal and policy workflows.",
    resource: "payment-obligations",
    columns: [
      { key: "id", label: "Obligation", emphasis: true },
      { key: "proposal_number", label: "Proposal" },
      { key: "amount", label: "Amount" },
      { key: "status", label: "Status" },
      { key: "due_date", label: "Due date", muted: true },
    ],
    statusOptions: ["PENDING", "PARTIALLY_PAID", "PAID", "CANCELLED"],
    primaryLabel: "Refresh obligations",
    primaryMode: "refresh",
  },
  loans: {
    title: "Policy loans",
    eyebrow: "Ordinary Life / Servicing",
    description: "Review policy loan requests and keep servicing activity tied to the policy ledger.",
    resource: "loans",
    columns: [
      { key: "id", label: "Loan", emphasis: true },
      { key: "policy_number", label: "Policy" },
      { key: "principal_amount", label: "Principal" },
      { key: "status", label: "Status" },
      { key: "created_at", label: "Created", muted: true },
    ],
    statusOptions: ["REQUESTED", "APPROVED", "PAID", "REJECTED"],
    primaryLabel: "Refresh loans",
    primaryMode: "refresh",
  },
  withdrawals: {
    title: "Withdrawal requests",
    eyebrow: "Ordinary Life / Servicing",
    description: "Track controlled withdrawals against policy value with approval-ready context.",
    resource: "withdrawals",
    columns: [
      { key: "id", label: "Request", emphasis: true },
      { key: "policy_number", label: "Policy" },
      { key: "amount", label: "Amount" },
      { key: "status", label: "Status" },
      { key: "created_at", label: "Created", muted: true },
    ],
    statusOptions: ["REQUESTED", "APPROVED", "PAID", "REJECTED"],
    primaryLabel: "Refresh withdrawals",
    primaryMode: "refresh",
  },
  claims: {
    title: "Claims intake",
    eyebrow: "Ordinary Life / Claims",
    description: "Keep claim records visible beside the policy, evidence, and audit trail that support the decision.",
    resource: "claims",
    columns: [
      { key: "claim_number", label: "Claim", emphasis: true },
      { key: "policy_number", label: "Policy" },
      { key: "claim_type", label: "Type" },
      { key: "status", label: "Status" },
      { key: "created_at", label: "Created", muted: true },
    ],
    statusOptions: ["REPORTED", "UNDER_REVIEW", "APPROVED", "REJECTED", "PAID"],
    primaryLabel: "Refresh claims",
    primaryMode: "refresh",
  },
  "maturity-installments": {
    title: "Maturity installments",
    eyebrow: "Ordinary Life / Maturity",
    description: "Monitor maturity schedules and installment-level settlement records.",
    resource: "maturity-installments",
    columns: [
      { key: "id", label: "Installment", emphasis: true },
      { key: "policy_number", label: "Policy" },
      { key: "amount", label: "Amount" },
      { key: "status", label: "Status" },
      { key: "due_date", label: "Due date", muted: true },
    ],
    statusOptions: ["PENDING", "PAID", "OVERDUE"],
    primaryLabel: "Refresh installments",
    primaryMode: "refresh",
  },
  documents: {
    title: "Document evidence",
    eyebrow: "Ordinary Life / Operations",
    description: "Verify evidence and retain every document transition in the policy workflow history.",
    resource: "documents",
    columns: [
      { key: "document_type", label: "Document", emphasis: true },
      { key: "proposal_number", label: "Proposal" },
      { key: "status", label: "Status" },
      { key: "uploaded_at", label: "Uploaded", muted: true },
    ],
    statusOptions: ["REQUESTED", "UPLOADED", "VERIFICATION_PENDING", "VERIFIED", "REJECTED"],
    primaryLabel: "Refresh evidence",
    primaryMode: "refresh",
  },
  notes: {
    title: "File notes",
    eyebrow: "Ordinary Life / Operations",
    description: "Read the operational narrative without losing author, scope, and timestamp context.",
    resource: "notes",
    columns: [
      { key: "note_type", label: "Type", emphasis: true },
      { key: "policy_number", label: "Policy" },
      { key: "body", label: "Note" },
      { key: "created_at", label: "Created", muted: true },
    ],
    statusOptions: [],
    primaryLabel: "Refresh notes",
    primaryMode: "refresh",
  },
  approvals: {
    title: "Approval queue",
    eyebrow: "Ordinary Life / Governance",
    description: "Review pending Ordinary Life decisions with explicit status, reviewer, and comment context.",
    resource: "approvals",
    columns: [
      { key: "entity_type", label: "Entity", emphasis: true },
      { key: "entity_repr", label: "Reference" },
      { key: "action", label: "Action" },
      { key: "status", label: "Status" },
      { key: "submitted_at", label: "Submitted", muted: true },
    ],
    statusOptions: ["PENDING", "APPROVED", "REJECTED", "CANCELLED"],
    primaryLabel: "Refresh queue",
    primaryMode: "refresh",
  },
  "audit-history": {
    title: "Audit history",
    eyebrow: "Ordinary Life / Compliance",
    description: "Trace material Ordinary Life changes by object, action, actor, and correlation reference.",
    resource: "audit-history",
    columns: [
      { key: "action", label: "Action", emphasis: true },
      { key: "model_name", label: "Model" },
      { key: "object_repr", label: "Object" },
      { key: "actor_name", label: "Actor" },
      { key: "created_at", label: "Created", muted: true },
    ],
    statusOptions: [],
    primaryLabel: "Refresh history",
    primaryMode: "refresh",
  },
}

const routeByKey: Record<WorkspaceKey, string> = {
  applications: "/ordinary-life/applications",
  quotations: "/ordinary-life/quotations",
  proposals: "/ordinary-life/proposals",
  policies: "/ordinary-life/policies",
  commitments: "/ordinary-life/commitments",
  loans: "/ordinary-life/loans",
  withdrawals: "/ordinary-life/withdrawals",
  claims: "/ordinary-life/claims",
  "maturity-installments": "/ordinary-life/maturity-installments",
  documents: "/ordinary-life/documents",
  notes: "/ordinary-life/notes",
  approvals: "/ordinary-life/approvals",
  "audit-history": "/ordinary-life/audit-history",
}

const nav: { key: WorkspaceKey; label: string }[] = [
  { key: "applications", label: "Applications" },
  { key: "quotations", label: "Quotations" },
  { key: "proposals", label: "Underwriting" },
  { key: "policies", label: "Policies" },
  { key: "approvals", label: "Approvals" },
  { key: "documents", label: "Evidence" },
  { key: "audit-history", label: "Audit" },
]

function display(value: unknown) {
  if (value === null || value === undefined || value === "") return "—"
  if (typeof value === "object") return JSON.stringify(value)
  return String(value)
}

function listData(value: unknown): Row[] {
  if (Array.isArray(value)) return value as Row[]
  if (value && typeof value === "object" && Array.isArray((value as { results?: unknown }).results)) return (value as { results: Row[] }).results
  return []
}

function metricValue(rows: Row[], key: string) {
  return rows.filter((row) => String(row.status ?? "").toUpperCase() === key).length
}

export default function OrdinaryLifeWorkspacePage({ view }: { view: WorkspaceKey }) {
  const config = configs[view]
  const navigate = useNavigate()
  const workspaceRef = useRef<HTMLElement | null>(null)
  const [rows, setRows] = useState<Row[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [selected, setSelected] = useState<Row | null>(null)
  const [drawerMode, setDrawerMode] = useState<"detail" | "primary">("detail")
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState("")
  const [form, setForm] = useState<FormState>({})

  const load = useCallback(async () => {
    setLoading(true)
    setError("")
    try {
      const data = await olWorkflow.list(config.resource, { ordering: "-created_at" })
      setRows(listData(data))
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load the Ordinary Life queue.")
    } finally {
      setLoading(false)
    }
  }, [config.resource])

  useEffect(() => {
    void load()
  }, [load])

  useEffect(() => {
    const node = workspaceRef.current
    if (!node) return
    const onSelect = (event: Event) => {
      const detail = (event as CustomEvent<EventDetail>).detail
      if (detail.row) {
        setSelected(detail.row)
        setDrawerMode("detail")
        setNotice("")
      }
    }
    const onPrimary = () => {
      setSelected(null)
      setNotice("")
      if (config.primaryMode === "refresh") {
        void load()
      } else {
        setDrawerMode("primary")
        setForm({})
      }
    }
    node.addEventListener("ol-row-select", onSelect)
    node.addEventListener("ol-primary-action", onPrimary)
    return () => {
      node.removeEventListener("ol-row-select", onSelect)
      node.removeEventListener("ol-primary-action", onPrimary)
    }
  }, [config.primaryMode, load])

  useEffect(() => {
    const node = workspaceRef.current as (HTMLElement & Record<string, unknown>) | null
    if (!node) return
    Object.assign(node, {
      title: config.title,
      metrics: [
        { label: "Total records", value: String(rows.length), detail: "Visible in current scope", tone: "dark" },
        { label: "Pending", value: String(metricValue(rows, "PENDING") + metricValue(rows, "SUBMITTED") + metricValue(rows, "APPROVAL_PENDING")), detail: "Requires next action", tone: "soft" },
        { label: "Completed", value: String(metricValue(rows, "APPROVED") + metricValue(rows, "PAID") + metricValue(rows, "ACTIVE") + metricValue(rows, "VERIFIED")), detail: "Completed or in force", tone: "line" },
        { label: "Attention", value: String(metricValue(rows, "REJECTED") + metricValue(rows, "DECLINED") + metricValue(rows, "OVERDUE")), detail: "Review exceptions", tone: "line" },
      ],
      columns: config.columns,
      rows,
      loading,
      error,
      actionLabel: config.primaryLabel,
      statusOptions: config.statusOptions,
      emptyLabel: `No ${config.title.toLowerCase()} records match the current view.`,
    })
  }, [config, error, loading, rows])

  const closeDrawer = () => {
    setSelected(null)
    setDrawerMode("detail")
    setNotice("")
  }

  const setField = (key: string, value: string) => setForm((current) => ({ ...current, [key]: value }))

  const submitPrimary = async (event: React.FormEvent) => {
    event.preventDefault()
    setBusy(true)
    setError("")
    try {
      if (config.primaryMode === "application") {
        await olWorkflow.create("applications", {
          partner: form.partner,
          policyholder: form.policyholder,
          life_assured: form.life_assured,
          payer: form.payer || null,
          declarations: form.declarations ? JSON.parse(form.declarations) : {},
        })
      } else if (config.primaryMode === "quotation") {
        await olWorkflow.create("quotations", {
          application: form.application,
          product_version: form.product_version,
          plan: form.plan || null,
          sum_assured: form.sum_assured,
          term_years: Number(form.term_years),
          payment_frequency: form.payment_frequency || "ANNUAL",
          rider_codes: form.rider_codes ? form.rider_codes.split(",").map((value) => value.trim()).filter(Boolean) : [],
        })
      } else if (config.primaryMode === "issue") {
        await olWorkflow.collectionAction("policies", "issue", {
          proposal: form.proposal,
          first_payment_obligation: form.first_payment_obligation,
          allocation: {
            external_receipt_reference: form.external_receipt_reference,
            amount: form.amount,
            currency: form.currency || "TZS",
            metadata: {},
          },
          beneficiary_allocations: form.beneficiary_allocations ? JSON.parse(form.beneficiary_allocations) : [],
          reason: form.reason || "Policy issued from approved proposal.",
        })
      }
      setNotice(`${config.title} action completed successfully.`)
      setDrawerMode("detail")
      setForm({})
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : "The operation could not be completed.")
    } finally {
      setBusy(false)
    }
  }

  const action = async (actionName: string, payload: Row = {}) => {
    if (!selected?.id) return
    setBusy(true)
    setError("")
    try {
      const actionPayload = { reason: form.reason || `Ordinary Life ${actionName.replace(/-/g, " ")} requested from workspace.`, ...payload }
      await olWorkflow.action(config.resource, String(selected.id), actionName, actionPayload)
      setNotice(`${actionName.replace(/-/g, " ")} completed successfully.`)
      setSelected(null)
      setForm({})
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : "The workflow action was rejected.")
    } finally {
      setBusy(false)
    }
  }

  const detailFields = useMemo(() => {
    if (!selected) return []
    return Object.entries(selected)
      .filter(([key, value]) => !["id", "metadata", "before_snapshot", "after_snapshot"].includes(key) && value !== null && value !== "")
      .slice(0, 16)
  }, [selected])

  const actionButtons = useMemo(() => {
    if (!selected) return []
    if (view === "applications") return [{ label: "Submit application", action: "submit" }]
    if (view === "quotations") return [{ label: "Submit quotation", action: "submit" }, { label: "Convert to proposal", action: "convert-to-proposal" }]
    if (view === "proposals") return [
      { label: "Start underwriting", action: "start-underwriting" },
      { label: "Submit for approval", action: "submit-approval" },
      { label: "Approve proposal", action: "approve" },
    ]
    if (view === "policies") return [
      { label: "Grace period", action: "grace" },
      { label: "Lapse policy", action: "lapse" },
      { label: "Reactivate policy", action: "reactivate" },
      { label: "Cancel policy", action: "cancel" },
      { label: "Mature policy", action: "mature" },
      { label: "Request endorsement", action: "request-endorsement" },
      { label: "Request renewal", action: "request-renewal" },
      { label: "Request reinstatement", action: "request-reinstatement" },
    ]
    if (view === "documents") return [
      { label: "Submit verification", action: "submit-verification" },
      { label: "Verify document", action: "verify" },
      { label: "Reject document", action: "reject" },
    ]
    if (view === "approvals") return [{ label: "Complete approval", action: "complete" }, { label: "Reject approval", action: "reject" }]
    if (view === "commitments") return [{ label: "Allocate payment", action: "allocate" }]
    return []
  }, [selected, view])

  const renderField = (label: string, key: string, type = "text", placeholder = "") => (
    <label className="block space-y-1.5">
      <span className="text-[11px] font-semibold uppercase tracking-[0.12em] text-neutral-500">{label}</span>
      <input
        required={key !== "payer" && key !== "plan" && key !== "rider_codes" && key !== "declarations" && key !== "reason" && key !== "beneficiary_allocations"}
        type={type}
        value={form[key] ?? ""}
        placeholder={placeholder}
        onChange={(event) => setField(key, event.target.value)}
        className="h-10 w-full rounded-lg border border-neutral-300 bg-white px-3 text-sm text-neutral-900 outline-none transition focus:border-neutral-900 focus:ring-2 focus:ring-neutral-900/10"
      />
    </label>
  )

  const renderPrimaryForm = () => {
    if (config.primaryMode === "application") return (
      <>
        {renderField("Partner ID", "partner", "text", "UUID")}
        {renderField("Policyholder ID", "policyholder", "text", "UUID")}
        {renderField("Life assured ID", "life_assured", "text", "UUID")}
        {renderField("Payer ID (optional)", "payer", "text", "UUID")}
        {renderField("Declarations JSON (optional)", "declarations", "text", "{}")}
      </>
    )
    if (config.primaryMode === "quotation") return (
      <>
        {renderField("Application ID", "application", "text", "UUID")}
        {renderField("Product version ID", "product_version", "text", "UUID")}
        {renderField("Plan ID (optional)", "plan", "text", "UUID")}
        {renderField("Sum assured", "sum_assured", "number", "0.00")}
        {renderField("Term years", "term_years", "number", "10")}
        {renderField("Payment frequency", "payment_frequency", "text", "ANNUAL")}
        {renderField("Rider codes (comma separated)", "rider_codes", "text", "RIDER_A, RIDER_B")}
      </>
    )
    return (
      <>
        {renderField("Approved proposal ID", "proposal", "text", "UUID")}
        {renderField("First payment obligation ID", "first_payment_obligation", "text", "UUID")}
        {renderField("Receipt reference", "external_receipt_reference", "text", "Receipt number")}
        {renderField("Allocated amount", "amount", "number", "0.00")}
        {renderField("Currency", "currency", "text", "TZS")}
        {renderField("Beneficiary allocations JSON", "beneficiary_allocations", "text", "[]")}
        {renderField("Reason", "reason", "text", "Issuance reason")}
      </>
    )
  }

  return (
    <div className="min-h-full bg-[#f4f4f4] px-4 py-5 text-[#171717] sm:px-6 lg:px-8">
      <div className="mx-auto max-w-[1560px] space-y-5">
        <header className="flex flex-col gap-4 border-b border-neutral-300 pb-5 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <div className="mb-2 flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.16em] text-neutral-500">
              <span>ZIC</span><span>/</span><span>{config.eyebrow}</span>
            </div>
            <h1 className="text-2xl font-semibold tracking-[-0.04em] text-neutral-950 sm:text-3xl">{config.title}</h1>
            <p className="mt-1 max-w-2xl text-sm leading-6 text-neutral-500">{config.description}</p>
          </div>
          <div className="flex items-center gap-2">
            <button type="button" onClick={() => void load()} className="inline-flex h-9 items-center gap-2 rounded-lg border border-neutral-300 bg-white px-3 text-xs font-semibold text-neutral-700 transition hover:border-neutral-900 hover:text-neutral-950"><RefreshCw className="h-3.5 w-3.5" /> Refresh</button>
            <button type="button" onClick={() => navigate("/ordinary-life/approvals")} className="inline-flex h-9 items-center gap-2 rounded-lg bg-neutral-950 px-3 text-xs font-semibold text-white transition hover:bg-neutral-800"><ClipboardList className="h-3.5 w-3.5" /> Approval queue</button>
          </div>
        </header>

        <nav className="flex gap-1 overflow-x-auto rounded-xl border border-neutral-300 bg-white p-1" aria-label="Ordinary Life workspace">
          {nav.map((item) => (
            <button key={item.key} type="button" onClick={() => navigate(routeByKey[item.key])} className={`whitespace-nowrap rounded-lg px-3 py-2 text-xs font-semibold transition ${view === item.key ? "bg-neutral-950 text-white" : "text-neutral-500 hover:bg-neutral-100 hover:text-neutral-900"}`}>{item.label}</button>
          ))}
          <button type="button" onClick={() => navigate("/ordinary-life/setup")} className="whitespace-nowrap rounded-lg px-3 py-2 text-xs font-semibold text-neutral-500 transition hover:bg-neutral-100 hover:text-neutral-900">Setup</button>
        </nav>

        <zic-ordinary-life-workspace ref={workspaceRef} />

        {notice && <div className="flex items-center justify-between rounded-lg border border-neutral-300 bg-white px-4 py-3 text-sm text-neutral-700"><span className="flex items-center gap-2"><Check className="h-4 w-4" />{notice}</span><button type="button" onClick={() => setNotice("")} aria-label="Dismiss notification"><X className="h-4 w-4" /></button></div>}

        {(drawerMode === "primary" || selected) && (
          <div className="fixed inset-0 z-50 flex justify-end bg-neutral-950/30" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) closeDrawer() }}>
            <aside className="flex h-full w-full max-w-xl flex-col border-l border-neutral-300 bg-[#f8f8f8] shadow-2xl" aria-label={drawerMode === "primary" ? config.primaryLabel : "Record details"}>
              <div className="flex items-start justify-between border-b border-neutral-300 bg-white px-6 py-5">
                <div>
                  <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-neutral-500">{drawerMode === "primary" ? "Controlled write" : "Record workspace"}</p>
                  <h2 className="mt-1 text-lg font-semibold tracking-[-0.03em]">{drawerMode === "primary" ? config.primaryLabel : display(selected?.[config.columns[0]?.key ?? "id"])}</h2>
                </div>
                <button type="button" onClick={closeDrawer} className="rounded-lg p-2 text-neutral-500 transition hover:bg-neutral-100 hover:text-neutral-950" aria-label="Close drawer"><X className="h-5 w-5" /></button>
              </div>

              {drawerMode === "primary" ? (
                <form onSubmit={submitPrimary} className="flex min-h-0 flex-1 flex-col">
                  <div className="flex-1 space-y-4 overflow-y-auto px-6 py-6">{renderPrimaryForm()}</div>
                  <div className="flex items-center justify-end gap-2 border-t border-neutral-300 bg-white px-6 py-4"><button type="button" onClick={closeDrawer} className="rounded-lg px-4 py-2 text-xs font-semibold text-neutral-600 hover:bg-neutral-100">Cancel</button><button type="submit" disabled={busy} className="inline-flex items-center gap-2 rounded-lg bg-neutral-950 px-4 py-2 text-xs font-semibold text-white disabled:opacity-50"><FilePlus2 className="h-3.5 w-3.5" />{busy ? "Working..." : "Submit"}</button></div>
                </form>
              ) : (
                <div className="flex min-h-0 flex-1 flex-col">
                  <div className="flex-1 space-y-5 overflow-y-auto px-6 py-6">
                    <div className="grid gap-2 sm:grid-cols-2">{detailFields.map(([key, value]) => <div key={key} className="rounded-lg border border-neutral-300 bg-white px-3 py-3"><div className="text-[10px] font-bold uppercase tracking-[0.12em] text-neutral-500">{key.replace(/_/g, " ")}</div><div className="mt-1 break-words text-sm font-medium text-neutral-900">{display(value)}</div></div>)}</div>
                    {actionButtons.length > 0 && <div className="space-y-3"><div className="text-[10px] font-bold uppercase tracking-[0.12em] text-neutral-500">Available service actions</div><div className="grid gap-2 sm:grid-cols-2">{actionButtons.map((item) => <button key={item.action} type="button" disabled={busy} onClick={() => void action(item.action)} className="flex items-center justify-between rounded-lg border border-neutral-300 bg-white px-3 py-3 text-left text-xs font-semibold text-neutral-800 transition hover:border-neutral-950 disabled:opacity-50"><span>{item.label}</span><ArrowRight className="h-3.5 w-3.5" /></button>)}</div></div>}
                    {actionButtons.length > 0 && <label className="block space-y-1.5"><span className="text-[11px] font-semibold uppercase tracking-[0.12em] text-neutral-500">Reason / comment</span><textarea value={form.reason ?? ""} onChange={(event) => setField("reason", event.target.value)} rows={3} className="w-full rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm outline-none focus:border-neutral-950" placeholder="Record the business reason for the action" /></label>}
                  </div>
                  <div className="border-t border-neutral-300 bg-white px-6 py-4"><button type="button" onClick={() => { setSelected(null); navigate(routeByKey[view]) }} className="inline-flex items-center gap-2 text-xs font-semibold text-neutral-600 hover:text-neutral-950"><ArrowLeft className="h-3.5 w-3.5" /> Back to register</button></div>
                </div>
              )}
            </aside>
          </div>
        )}
      </div>
    </div>
  )
}
