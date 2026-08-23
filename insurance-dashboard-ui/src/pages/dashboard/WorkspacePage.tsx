import { useEffect, useMemo, useState } from "react"
import { Link, useNavigate } from "react-router-dom"
import {
  AlertTriangle, BellRing, Check, CheckCircle2, ChevronRight, Circle, Clock3, DollarSign,
  ExternalLink, Inbox, Loader2, Plus, RefreshCw, Search, Sparkles, Trash2, X,
} from "lucide-react"
import {
  actOnDashboardAlert, addCurrencyPair, createDashboardTask, deleteDashboardTask,
  listCurrencyPairs, listDashboardAlerts, listDashboardNotifications, listDashboardTasks,
  markAllDashboardNotificationsRead, markDashboardNotificationRead, refreshCurrencyPairs, removeCurrencyPair,
  updateDashboardTask,
} from "../../lib/api"
import type {
  CurrencyPairRecord, DashboardAlertRecord, DashboardNotificationRecord, DashboardTaskRecord,
} from "../../lib/types"
import { useAI } from "../../components/ai/AIContext"
import { useLanguage } from "../../lib/language"

type WorkspaceSection = "tasks" | "alerts" | "notifications" | "currencies" | "reports" | "approvals" | "help"

const sectionMeta: Record<WorkspaceSection, { eyebrow: string; title: string; description: string }> = {
  tasks: { eyebrow: "Execution centre", title: "My task tracker", description: "Keep every operational commitment visible, routed, and accountable." },
  alerts: { eyebrow: "Risk desk", title: "Alerts & controls", description: "Resolve operational exceptions before they become customer or compliance issues." },
  notifications: { eyebrow: "Activity stream", title: "Notifications", description: "Follow onboarding, approval, and workflow activity from one focused inbox." },
  currencies: { eyebrow: "Treasury view", title: "Currency tracker", description: "Monitor the exchange pairs that matter to ZIC’s financial and reporting workflows." },
  reports: { eyebrow: "Insights", title: "Reports workspace", description: "Use report categories and saved execution routes as your reporting launchpad." },
  approvals: { eyebrow: "Governance", title: "Approvals queue", description: "Bring pending decisions into a single review surface with clear ownership." },
  help: { eyebrow: "Enablement", title: "Help centre", description: "Find workflow guidance and jump directly to the right operational module." },
}

function formatDate(value: string | null) {
  if (!value) return "No due date"
  return new Intl.DateTimeFormat(undefined, { day: "2-digit", month: "short", year: "numeric" }).format(new Date(value))
}

function toneForPriority(priority: DashboardTaskRecord["priority"]) {
  return priority === "URGENT" ? "text-rose-600 bg-rose-50" : priority === "HIGH" ? "text-amber-700 bg-amber-50" : "text-slate-600 bg-slate-100"
}

function EmptyState({ icon: Icon, title, description, action }: { icon: typeof Inbox; title: string; description: string; action?: React.ReactNode }) {
  return <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-border bg-card/70 px-6 py-16 text-center">
    <div className="mb-4 rounded-2xl bg-primary/10 p-3 text-primary"><Icon className="h-6 w-6" /></div>
    <h3 className="text-sm font-semibold text-foreground">{title}</h3>
    <p className="mt-1 max-w-md text-sm text-muted-foreground">{description}</p>
    {action && <div className="mt-5">{action}</div>}
  </div>
}

export default function WorkspacePage({ section }: { section: WorkspaceSection }) {
  const navigate = useNavigate()
  const { setPanelOpen } = useAI()
  const { t } = useLanguage()
  const meta = sectionMeta[section]
  const [tasks, setTasks] = useState<DashboardTaskRecord[]>([])
  const [alerts, setAlerts] = useState<DashboardAlertRecord[]>([])
  const [notifications, setNotifications] = useState<DashboardNotificationRecord[]>([])
  const [pairs, setPairs] = useState<CurrencyPairRecord[]>([])
  const [loading, setLoading] = useState(section === "tasks" || section === "alerts" || section === "notifications" || section === "currencies")
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState("")
  const [taskComposerOpen, setTaskComposerOpen] = useState(false)
  const [taskTitle, setTaskTitle] = useState("")
  const [taskPriority, setTaskPriority] = useState<DashboardTaskRecord["priority"]>("MEDIUM")
  const [pairBase, setPairBase] = useState("USD")
  const [pairQuote, setPairQuote] = useState("TZS")

  async function load() {
    setLoading(true); setError("")
    try {
      if (section === "tasks") setTasks(await listDashboardTasks())
      if (section === "alerts") setAlerts(await listDashboardAlerts({ status: "OPEN" }))
      if (section === "notifications") setNotifications(await listDashboardNotifications())
      if (section === "currencies") setPairs(await listCurrencyPairs())
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load workspace data.")
    } finally { setLoading(false) }
  }

  useEffect(() => { void load() }, [section])

  const openTasks = useMemo(() => tasks.filter((task) => task.status !== "DONE" && task.status !== "ARCHIVED").length, [tasks])
  const unread = useMemo(() => notifications.filter((item) => !item.isRead).length, [notifications])

  async function toggleTask(task: DashboardTaskRecord) {
    try {
      const updated = await updateDashboardTask(task.id, { status: task.status === "DONE" ? "TODO" : "DONE" })
      setTasks((items) => items.map((item) => item.id === updated.id ? updated : item))
    } catch (err) { setError(err instanceof Error ? err.message : "Unable to update task.") }
  }

  async function submitTask(event: React.FormEvent) {
    event.preventDefault()
    if (!taskTitle.trim()) return
    setSaving(true)
    try {
      const task = await createDashboardTask({ title: taskTitle.trim(), priority: taskPriority, status: "TODO" })
      setTasks((items) => [task, ...items]); setTaskTitle(""); setTaskComposerOpen(false)
    } catch (err) { setError(err instanceof Error ? err.message : "Unable to create task.") }
    finally { setSaving(false) }
  }

  async function deleteTask(id: number) {
    try {
      await deleteDashboardTask(id)
      setTasks((items) => items.filter((item) => item.id !== id))
    } catch (err) { setError(err instanceof Error ? err.message : "Unable to delete task.") }
  }

  async function acknowledgeAlert(alert: DashboardAlertRecord, action: "acknowledge" | "dismiss") {
    try {
      const updated = await actOnDashboardAlert(alert.id, action)
      setAlerts((items) => items.filter((item) => item.id !== updated.id))
    } catch (err) { setError(err instanceof Error ? err.message : "Unable to update alert.") }
  }

  async function markRead(notification: DashboardNotificationRecord) {
    if (notification.isRead) return
    try {
      const updated = await markDashboardNotificationRead(Number(notification.id))
      setNotifications((items) => items.map((item) => item.id === updated.id ? updated : item))
    } catch (err) { setError(err instanceof Error ? err.message : "Unable to update notification.") }
  }

  async function addPair(event: React.FormEvent) {
    event.preventDefault(); setSaving(true)
    try {
      const pair = await addCurrencyPair(pairBase, pairQuote)
      setPairs((items) => items.some((item) => item.id === pair.id) ? items : [...items, pair])
    } catch (err) { setError(err instanceof Error ? err.message : "Unable to add currency pair.") }
    finally { setSaving(false) }
  }

  async function refreshRates() {
    setSaving(true)
    try { await refreshCurrencyPairs(); setPairs(await listCurrencyPairs()) }
    catch (err) { setError(err instanceof Error ? err.message : "Unable to refresh currency rates.") }
    finally { setSaving(false) }
  }

  async function removePair(id: number) {
    try { await removeCurrencyPair(id); setPairs((items) => items.filter((item) => item.id !== id)) }
    catch (err) { setError(err instanceof Error ? err.message : "Unable to remove currency pair.") }
  }

  return <main className="mx-auto w-full max-w-[1440px] space-y-6 px-4 py-5 sm:px-6 lg:px-8">
    <section className="relative overflow-hidden rounded-3xl border border-border bg-gradient-to-br from-slate-950 via-slate-900 to-primary/90 px-6 py-7 text-white shadow-xl sm:px-8">
      <div className="absolute -right-16 -top-20 h-56 w-56 rounded-full bg-primary/30 blur-3xl" />
      <div className="relative flex flex-col justify-between gap-5 lg:flex-row lg:items-end">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-primary-foreground/70">{meta.eyebrow}</p>
          <h1 className="mt-2 text-2xl font-semibold tracking-tight sm:text-3xl">{meta.title}</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-300">{meta.description}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button onClick={() => setPanelOpen(true)} className="inline-flex items-center gap-2 rounded-xl border border-white/15 bg-white/10 px-3.5 py-2 text-sm font-medium text-white transition hover:bg-white/15"><Sparkles className="h-4 w-4" /> AI workspace</button>
          {(section === "tasks" || section === "currencies") && <button onClick={() => section === "tasks" ? setTaskComposerOpen(true) : void refreshRates()} className="inline-flex items-center gap-2 rounded-xl bg-white px-3.5 py-2 text-sm font-semibold text-slate-950 transition hover:bg-slate-100"><Plus className="h-4 w-4" /> {section === "tasks" ? t("createTask") : t("refresh")}</button>}
        </div>
      </div>
    </section>

    {(section === "tasks" || section === "alerts" || section === "notifications" || section === "currencies") && <div className="grid gap-3 sm:grid-cols-3">
      <div className="rounded-2xl border border-border bg-card p-4"><p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Open items</p><p className="mt-2 text-2xl font-semibold">{section === "tasks" ? openTasks : section === "alerts" ? alerts.length : section === "notifications" ? unread : pairs.length}</p></div>
      <div className="rounded-2xl border border-border bg-card p-4"><p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Workspace status</p><p className="mt-2 text-sm font-semibold text-emerald-600">Operational</p><p className="mt-1 text-xs text-muted-foreground">Data is scoped to your account.</p></div>
      <div className="rounded-2xl border border-border bg-card p-4"><p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Last sync</p><p className="mt-2 text-sm font-semibold">{new Intl.DateTimeFormat(undefined, { hour: "2-digit", minute: "2-digit" }).format(new Date())}</p><p className="mt-1 text-xs text-muted-foreground">Live on refresh.</p></div>
    </div>}

    {error && <div className="flex items-start justify-between gap-4 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700"><span>{error}</span><button onClick={() => setError("")} aria-label="Dismiss error"><X className="h-4 w-4" /></button></div>}
    {loading ? <div className="flex items-center justify-center rounded-2xl border border-border bg-card py-20 text-muted-foreground"><Loader2 className="mr-2 h-5 w-5 animate-spin" /> Loading workspace…</div> : <>
      {section === "tasks" && <section className="space-y-3">
        {taskComposerOpen && <form onSubmit={submitTask} className="rounded-2xl border border-primary/20 bg-primary/5 p-4"><div className="flex flex-col gap-3 sm:flex-row"><input autoFocus value={taskTitle} onChange={(event) => setTaskTitle(event.target.value)} placeholder="What needs to be done?" className="min-w-0 flex-1 rounded-xl border border-input bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary/30" /><select value={taskPriority} onChange={(event) => setTaskPriority(event.target.value as DashboardTaskRecord["priority"])} className="rounded-xl border border-input bg-background px-3 py-2 text-sm"><option value="LOW">Low priority</option><option value="MEDIUM">Medium priority</option><option value="HIGH">High priority</option><option value="URGENT">Urgent</option></select><button disabled={saving} className="rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground disabled:opacity-60">{saving ? "Saving…" : "Add task"}</button><button type="button" onClick={() => setTaskComposerOpen(false)} className="rounded-xl border border-border px-3 py-2 text-sm">Cancel</button></div></form>}
        {tasks.length === 0 ? <EmptyState icon={CheckCircle2} title="Your task list is clear" description="Create a task when you need a durable reminder, owner, and route for an operational commitment." action={<button onClick={() => setTaskComposerOpen(true)} className="inline-flex items-center gap-2 rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground"><Plus className="h-4 w-4" /> {t("createTask")}</button>} /> : tasks.map((task) => <article key={task.id} className="group flex items-start gap-3 rounded-2xl border border-border bg-card p-4 transition hover:border-primary/30 hover:shadow-sm"><button onClick={() => void toggleTask(task)} aria-label={task.status === "DONE" ? "Reopen task" : "Complete task"} className="mt-0.5 text-primary">{task.status === "DONE" ? <CheckCircle2 className="h-5 w-5" /> : <Circle className="h-5 w-5" />}</button><div className="min-w-0 flex-1"><div className="flex flex-wrap items-center gap-2"><h3 className={`text-sm font-semibold ${task.status === "DONE" ? "text-muted-foreground line-through" : "text-foreground"}`}>{task.title}</h3><span className={`rounded-full px-2 py-0.5 text-[10px] font-bold uppercase ${toneForPriority(task.priority)}`}>{task.priority}</span></div><p className="mt-1 text-xs text-muted-foreground">{task.description || "No additional notes"}</p><div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-muted-foreground"><span className="inline-flex items-center gap-1"><Clock3 className="h-3.5 w-3.5" /> {formatDate(task.dueAt)}</span>{task.route && <button onClick={() => navigate(task.route)} className="inline-flex items-center gap-1 font-medium text-primary hover:underline">Open linked workflow <ChevronRight className="h-3.5 w-3.5" /></button>}</div></div><button onClick={() => void deleteTask(task.id)} aria-label="Delete task" className="rounded-lg p-2 text-muted-foreground opacity-0 transition hover:bg-rose-50 hover:text-rose-600 group-hover:opacity-100"><Trash2 className="h-4 w-4" /></button></article>)}
      </section>}

      {section === "alerts" && <section className="space-y-3">{alerts.length === 0 ? <EmptyState icon={AlertTriangle} title="No open alerts" description="Critical and warning conditions will appear here with an action route and explicit acknowledgement state." /> : alerts.map((alert) => <article key={alert.id} className="flex flex-col gap-4 rounded-2xl border border-border bg-card p-5 sm:flex-row sm:items-center"><div className={`rounded-xl p-3 ${alert.severity === "CRITICAL" ? "bg-rose-100 text-rose-700" : alert.severity === "WARNING" ? "bg-amber-100 text-amber-700" : "bg-blue-100 text-blue-700"}`}><AlertTriangle className="h-5 w-5" /></div><div className="min-w-0 flex-1"><div className="flex flex-wrap items-center gap-2"><h3 className="text-sm font-semibold">{alert.title}</h3><span className="rounded-full bg-muted px-2 py-0.5 text-[10px] font-bold uppercase text-muted-foreground">{alert.severity}</span></div><p className="mt-1 text-sm text-muted-foreground">{alert.message}</p>{alert.route && <button onClick={() => navigate(alert.route)} className="mt-2 inline-flex items-center gap-1 text-xs font-semibold text-primary hover:underline">Review related record <ExternalLink className="h-3.5 w-3.5" /></button>}</div><div className="flex shrink-0 gap-2"><button onClick={() => void acknowledgeAlert(alert, "acknowledge")} className="rounded-xl bg-primary px-3 py-2 text-xs font-semibold text-primary-foreground">Acknowledge</button><button onClick={() => void acknowledgeAlert(alert, "dismiss")} className="rounded-xl border border-border px-3 py-2 text-xs font-semibold">Dismiss</button></div></article>)}</section>}

      {section === "notifications" && <section className="space-y-3"><div className="flex justify-end"><button onClick={async () => { await markAllDashboardNotificationsRead(); setNotifications((items) => items.map((item) => ({ ...item, isRead: true }))) }} className="text-xs font-semibold text-primary hover:underline">{t("markAllRead")}</button></div>{notifications.length === 0 ? <EmptyState icon={BellRing} title={t("noNotifications")} description="Workflow events, approvals, and onboarding changes will land in this inbox." /> : notifications.map((notification) => <button key={notification.id} onClick={() => { void markRead(notification); if (notification.route) navigate(notification.route) }} className={`flex w-full items-start gap-3 rounded-2xl border p-4 text-left transition hover:border-primary/30 hover:shadow-sm ${notification.isRead ? "border-border bg-card" : "border-primary/20 bg-primary/5"}`}><div className="mt-0.5 rounded-xl bg-primary/10 p-2 text-primary"><BellRing className="h-4 w-4" /></div><div className="min-w-0 flex-1"><div className="flex items-center justify-between gap-3"><h3 className="truncate text-sm font-semibold">{notification.title}</h3><span className="shrink-0 text-xs text-muted-foreground">{formatDate(notification.createdAt)}</span></div><p className="mt-1 text-sm text-muted-foreground">{notification.message}</p><span className="mt-2 inline-flex items-center gap-1 text-xs font-semibold text-primary">Open workflow <ChevronRight className="h-3.5 w-3.5" /></span></div>{!notification.isRead && <span className="mt-2 h-2 w-2 rounded-full bg-primary" />}</button>)}</section>}

      {section === "currencies" && <section className="space-y-4"><form onSubmit={addPair} className="flex flex-col gap-3 rounded-2xl border border-border bg-card p-4 sm:flex-row sm:items-end"><label className="flex-1 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Base currency<select value={pairBase} onChange={(event) => setPairBase(event.target.value)} className="mt-1.5 w-full rounded-xl border border-input bg-background px-3 py-2.5 text-sm font-normal text-foreground"><option>USD</option><option>TZS</option><option>EUR</option><option>GBP</option><option>KES</option></select></label><label className="flex-1 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Quote currency<select value={pairQuote} onChange={(event) => setPairQuote(event.target.value)} className="mt-1.5 w-full rounded-xl border border-input bg-background px-3 py-2.5 text-sm font-normal text-foreground"><option>TZS</option><option>USD</option><option>EUR</option><option>GBP</option><option>KES</option></select></label><button disabled={saving} className="inline-flex items-center justify-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground disabled:opacity-60"><Plus className="h-4 w-4" /> Track pair</button><button type="button" onClick={() => void refreshRates()} className="inline-flex items-center justify-center gap-2 rounded-xl border border-border px-4 py-2.5 text-sm font-semibold"><RefreshCw className={`h-4 w-4 ${saving ? "animate-spin" : ""}`} /> Refresh rates</button></form>{pairs.length === 0 ? <EmptyState icon={DollarSign} title="No currency pairs tracked" description="Add a pair to start a cached, refreshable currency watchlist for the dashboard." /> : <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{pairs.map((pair) => <article key={pair.id} className="rounded-2xl border border-border bg-card p-5"><div className="flex items-center justify-between"><div className="flex items-center gap-2"><div className="rounded-xl bg-emerald-100 p-2 text-emerald-700"><DollarSign className="h-4 w-4" /></div><span className="text-sm font-semibold">{pair.baseCurrency} / {pair.quoteCurrency}</span></div><button onClick={() => void removePair(pair.id)} aria-label={`Remove ${pair.baseCurrency} ${pair.quoteCurrency}`} className="rounded-lg p-1.5 text-muted-foreground hover:bg-rose-50 hover:text-rose-600"><Trash2 className="h-4 w-4" /></button></div><p className="mt-5 text-3xl font-semibold tracking-tight">{pair.latestRate ?? "—"}</p><p className="mt-1 text-xs text-muted-foreground">{pair.latestAsOf ? `Updated ${formatDate(pair.latestAsOf)}` : "Not refreshed yet"}</p><div className="mt-4 flex items-center justify-between border-t border-border pt-3 text-xs"><span className={pair.isStale ? "text-amber-700" : "text-emerald-700"}>{pair.isStale ? "Stale — refresh recommended" : "Current observation"}</span><span className="text-muted-foreground">Provider cached</span></div></article>)}</div>}</section>}

      {section === "reports" && <EmptyState icon={Search} title="Reporting launchpad" description="Report category visibility is already available through IAM. Use the reporting module routes as they are delivered, with this workspace reserved for saved reports and execution history." action={<Link to="/" className="inline-flex items-center gap-2 rounded-xl border border-border px-4 py-2 text-sm font-semibold">Back to dashboard <ChevronRight className="h-4 w-4" /></Link>} />}
      {section === "approvals" && <EmptyState icon={Check} title="Approval queue ready" description="Approval workflows will surface here with explicit timestamps, actors, and deep links. Start with the onboarding queue for current approval work." action={<Link to="/onboarding" className="inline-flex items-center gap-2 rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground">Open onboarding queue <ChevronRight className="h-4 w-4" /></Link>} />}
      {section === "help" && <EmptyState icon={Inbox} title="ZIC help centre" description="Use the AI workspace for contextual guidance, or jump into a module to get the workflow-specific actions and documentation." action={<button onClick={() => setPanelOpen(true)} className="inline-flex items-center gap-2 rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground"><Sparkles className="h-4 w-4" /> Open AI workspace</button>} />}
    </>}
  </main>
}
