import { Bell, Calendar, ChevronRight, Globe, LogOut, PanelLeft, Search, Sparkles, Sun, Moon, X } from "lucide-react"
import { useEffect, useRef, useState, type ReactNode } from "react"
import { useLocation, useNavigate } from "react-router-dom"
import { useAuth } from "../../lib/auth"
import { useTheme } from "../../theme/ThemeProvider"
import { useAI } from "../ai/AIContext"
import { useLanguage, languageOptions } from "../../lib/language"
import { listCommitmentOverdueNotifications, listDashboardNotifications, markAllDashboardNotificationsRead, markDashboardNotificationRead, searchDashboard } from "../../lib/api"
import type { DashboardNotificationRecord, GlobalSearchResult } from "../../lib/types"

interface TopbarProps { onToggleSidebar: () => void }

function useClock() {
  const [now, setNow] = useState(new Date())
  useEffect(() => { const id = setInterval(() => setNow(new Date()), 1000); return () => clearInterval(id) }, [])
  return now
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

function formatRelative(value: string) {
  const minutes = Math.round((Date.now() - new Date(value).getTime()) / 60000)
  if (minutes < 1) return "Just now"
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.round(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  return `${Math.round(hours / 24)}d ago`
}

export function Topbar({ onToggleSidebar }: TopbarProps) {
  const { user, signOut } = useAuth()
  const { theme, setTheme } = useTheme()
  const { setPanelOpen } = useAI()
  const { language, setLanguage, t } = useLanguage()
  const navigate = useNavigate()
  const location = useLocation()
  const now = useClock()
  const [query, setQuery] = useState("")
  const [searchOpen, setSearchOpen] = useState(false)
  const [searchLoading, setSearchLoading] = useState(false)
  const [searchResults, setSearchResults] = useState<GlobalSearchResult[]>([])
  const [languageOpen, setLanguageOpen] = useState(false)
  const [notificationsOpen, setNotificationsOpen] = useState(false)
  const [notifications, setNotifications] = useState<DashboardNotificationRecord[]>([])
  const [commitmentNotifications, setCommitmentNotifications] = useState<DashboardNotificationRecord[]>([])
  const [notificationLoading, setNotificationLoading] = useState(false)
  const searchRef = useRef<HTMLDivElement>(null)
  const nextTheme = theme === "dark" ? "light" : "dark"
  const d = now.getDate(); const y = now.getFullYear(); const monthAbbr = MONTHS[now.getMonth()]
  const hh = String(now.getHours()).padStart(2, "0"), mm = String(now.getMinutes()).padStart(2, "0"), ss = String(now.getSeconds()).padStart(2, "0")
  const allNotifications = [...notifications, ...commitmentNotifications]
  const unreadCount = allNotifications.filter((notification) => !notification.isRead).length

  useEffect(() => {
    setSearchOpen(false); setLanguageOpen(false); setNotificationsOpen(false)
  }, [location.pathname])

  useEffect(() => {
    if (query.trim().length < 2) { setSearchResults([]); setSearchLoading(false); return }
    const controller = new AbortController(); setSearchOpen(true); setSearchLoading(true)
    const timer = window.setTimeout(async () => {
      try { setSearchResults(await searchDashboard(query.trim(), controller.signal)) }
      catch (error) { if ((error as DOMException).name !== "AbortError") setSearchResults([]) }
      finally { if (!controller.signal.aborted) setSearchLoading(false) }
    }, 260)
    return () => { window.clearTimeout(timer); controller.abort() }
  }, [query])

  async function loadNotifications() {
    setNotificationLoading(true)
    const [dashboardItems, commitmentItems] = await Promise.all([
      listDashboardNotifications().catch(() => [] as DashboardNotificationRecord[]),
      listCommitmentOverdueNotifications().catch(() => [] as DashboardNotificationRecord[]),
    ])
    setNotifications(dashboardItems)
    setCommitmentNotifications(commitmentItems)
    setNotificationLoading(false)
  }

  useEffect(() => {
    void loadNotifications()
    const interval = window.setInterval(() => void loadNotifications(), 90_000)
    return () => window.clearInterval(interval)
  }, [])

  async function openNotifications() {
    const nextOpen = !notificationsOpen
    setNotificationsOpen(nextOpen)
    if (nextOpen) void loadNotifications()
  }

  async function readNotification(notification: DashboardNotificationRecord) {
    if (notification.deepLink) {
      navigate(notification.deepLink)
      setNotificationsOpen(false)
      return
    }
    if (!notification.isRead) {
      const updated = await markDashboardNotificationRead(Number(notification.id))
      setNotifications((items) => items.map((item) => item.id === updated.id ? updated : item))
    }
    if (notification.route) navigate(notification.route)
  }

  async function markAllRead() {
    await markAllDashboardNotificationsRead()
    setNotifications((items) => items.map((item) => ({ ...item, isRead: true })))
  }

  return <header className="sticky top-0 z-30 flex min-h-16 items-center gap-3 border-b border-border bg-card/95 px-3 backdrop-blur md:px-6">
    <button onClick={onToggleSidebar} className="flex h-9 w-9 flex-none items-center justify-center rounded-lg text-muted-foreground transition hover:bg-secondary hover:text-foreground" aria-label="Toggle sidebar"><PanelLeft className="h-5 w-5" /></button>
    <div className="hidden items-center gap-2.5 lg:flex"><span className="flex h-9 w-9 items-center justify-center rounded-lg bg-accent text-accent-foreground"><Calendar className="h-[18px] w-[18px]" /></span><div className="leading-tight"><p className="text-sm font-semibold text-foreground">Account Period <span className="text-primary">{monthAbbr} {y}</span></p><p className="text-xs text-muted-foreground">{d} {monthAbbr} {y} {hh}:{mm}:{ss}</p></div></div>

    <div className="relative ml-auto flex min-w-0 items-center gap-1 sm:gap-2" ref={searchRef}>
      <div className="relative hidden min-w-0 md:block md:w-64 lg:w-80">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <input value={query} onChange={(event) => setQuery(event.target.value)} onFocus={() => query.length >= 2 && setSearchOpen(true)} placeholder={`${t("search")} partners, policies, users…`} aria-label="Search ZIC records" className="h-9 w-full rounded-xl border border-input bg-background pl-9 pr-8 text-sm outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/20" />
        {query && <button onClick={() => setQuery("")} className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-muted-foreground hover:bg-secondary" aria-label="Clear search"><X className="h-3.5 w-3.5" /></button>}
      </div>
      <IconButton label={t("search")} onClick={() => { setSearchOpen(true); document.querySelector<HTMLInputElement>('input[aria-label="Search ZIC records"]')?.focus() }}><Search className="h-[18px] w-[18px]" /></IconButton>
      <div className="relative"><IconButton label={t("language")} onClick={() => setLanguageOpen((value) => !value)}><Globe className="h-[18px] w-[18px]" /></IconButton>{languageOpen && <div className="absolute right-0 top-11 z-50 w-44 rounded-2xl border border-border bg-card p-1.5 shadow-xl"><p className="px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-muted-foreground">{t("language")}</p>{languageOptions.map((option) => <button key={option.value} onClick={() => { setLanguage(option.value); setLanguageOpen(false) }} className={`flex w-full items-center justify-between rounded-xl px-3 py-2 text-left text-sm transition hover:bg-secondary ${language === option.value ? "bg-primary/10 font-semibold text-primary" : "text-foreground"}`}><span>{option.nativeLabel}</span><span className="text-xs text-muted-foreground">{option.label}</span></button>)}</div>}</div>
      <div className="relative"><IconButton label={t("notifications")} onClick={() => void openNotifications()}><Bell className="h-[18px] w-[18px]" /></IconButton>{unreadCount > 0 && <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-destructive px-1 text-[10px] font-bold text-destructive-foreground">{unreadCount > 99 ? "99+" : unreadCount}</span>}{notificationsOpen && <div className="absolute right-0 top-11 z-50 w-[min(22rem,calc(100vw-1.5rem))] overflow-hidden rounded-2xl border border-border bg-card shadow-xl"><div className="flex items-center justify-between border-b border-border px-4 py-3"><div><p className="text-sm font-semibold">{t("notifications")}</p><p className="text-xs text-muted-foreground">{unreadCount ? `${unreadCount} unread` : t("noNotifications")}</p></div>{unreadCount > 0 && <button onClick={() => void markAllRead()} className="text-xs font-semibold text-primary hover:underline">{t("markAllRead")}</button>}</div><div className="max-h-80 overflow-y-auto">{notificationLoading ? <div className="flex items-center justify-center py-10 text-sm text-muted-foreground"><LoaderIcon /></div> : allNotifications.length === 0 ? <p className="px-4 py-10 text-center text-sm text-muted-foreground">{t("noNotifications")}</p> : allNotifications.slice(0, 6).map((notification) => <button key={notification.id} onClick={() => void readNotification(notification)} className={`flex w-full gap-3 border-b border-border px-4 py-3 text-left transition hover:bg-secondary ${notification.isRead ? "" : "bg-primary/5"}`}><span className={`mt-1 h-2 w-2 shrink-0 rounded-full ${notification.isRead ? "bg-border" : "bg-primary"}`} /><span className="min-w-0 flex-1"><span className="block truncate text-sm font-medium">{notification.title}</span><span className="mt-0.5 block line-clamp-2 text-xs text-muted-foreground">{notification.message}</span><span className="mt-1 block text-[10px] text-muted-foreground">{formatRelative(notification.createdAt)}</span></span><ChevronRight className="mt-1 h-4 w-4 shrink-0 text-muted-foreground" /></button>)}</div><button onClick={() => navigate("/notifications")} className="flex w-full items-center justify-center gap-1 px-4 py-3 text-xs font-semibold text-primary hover:bg-primary/5">{t("viewAll")} <ChevronRight className="h-3.5 w-3.5" /></button></div>}</div>
      <IconButton label={t("openAssistant")} onClick={() => setPanelOpen(true)}><Sparkles className="h-[18px] w-[18px]" /></IconButton>
      <IconButton label={`Switch to ${nextTheme} mode`} onClick={() => setTheme(nextTheme)}>{theme === "dark" ? <Sun className="h-[18px] w-[18px]" /> : <Moon className="h-[18px] w-[18px]" />}</IconButton>
      <div className="mx-1 hidden h-8 w-px bg-border sm:block" />
      <div className="flex items-center gap-2 pl-1"><div className="hidden text-right leading-tight sm:block"><p className="text-sm font-semibold text-foreground">{user?.fullName ?? user?.username ?? "User"}</p><p className="text-xs text-muted-foreground">{user?.department ?? user?.userType ?? ""}</p></div>{user?.avatar ? <img src={user.avatar} alt={user.fullName ?? "User avatar"} className="h-10 w-10 flex-none rounded-full border-2 border-card object-cover shadow-sm ring-1 ring-border" /> : <div className="flex h-10 w-10 flex-none items-center justify-center rounded-full bg-primary/10 text-sm font-bold text-primary ring-1 ring-border">{(user?.firstName?.[0] ?? user?.username?.[0] ?? "U").toUpperCase()}</div>}<IconButton label={t("signOut")} onClick={signOut}><LogOut className="h-[18px] w-[18px]" /></IconButton></div>
    </div>
    {searchOpen && query.length >= 2 && <div className="absolute left-3 right-3 top-14 z-50 overflow-hidden rounded-2xl border border-border bg-card shadow-2xl md:left-auto md:right-20 md:w-[min(32rem,calc(100vw-2rem))]">{searchLoading ? <div className="flex items-center gap-2 px-4 py-5 text-sm text-muted-foreground"><LoaderIcon /> Searching entities…</div> : searchResults.length === 0 ? <div className="px-4 py-8 text-center text-sm text-muted-foreground">No matching ZIC records found.</div> : <div className="max-h-[min(28rem,70vh)] overflow-y-auto">{searchResults.map((result) => <button key={`${result.type}-${result.id}`} onClick={() => { navigate(result.route); setQuery(""); setSearchOpen(false) }} className="flex w-full items-start gap-3 border-b border-border px-4 py-3 text-left transition last:border-0 hover:bg-secondary"><span className="mt-0.5 rounded-lg bg-primary/10 p-2 text-primary"><Search className="h-4 w-4" /></span><span className="min-w-0 flex-1"><span className="block truncate text-sm font-semibold">{result.label}</span><span className="mt-0.5 block truncate text-xs text-muted-foreground">{result.subtitle}</span></span><ChevronRight className="mt-2 h-4 w-4 shrink-0 text-muted-foreground" /></button>)}</div>}</div>}
  </header>
}

function LoaderIcon() { return <span className="inline-flex h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" /> }
function IconButton({ children, label, onClick }: { children: ReactNode; label: string; onClick?: () => void }) { return <button aria-label={label} onClick={onClick} className="flex h-9 w-9 items-center justify-center rounded-lg text-muted-foreground transition hover:bg-secondary hover:text-foreground">{children}</button> }
