import { Bell, Calendar, Globe, LogOut, PanelLeft, Search, Sun, Moon } from "lucide-react"
import { useAuth } from "../../lib/auth"
import { useEffect, useState } from "react"
import { useTheme } from "../../theme/ThemeProvider"

interface TopbarProps {
  onToggleSidebar: () => void
}

function useClock() {
  const [now, setNow] = useState(new Date())
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000)
    return () => clearInterval(id)
  }, [])
  return now
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

export function Topbar({ onToggleSidebar }: TopbarProps) {
  const { user, signOut } = useAuth()
  const { theme, setTheme } = useTheme()
  const now = useClock()
  const nextTheme = theme === "dark" ? "light" : "dark"
  const d = now.getDate()
  const m = now.getMonth()
  const y = now.getFullYear()
  const hh = String(now.getHours()).padStart(2, "0")
  const mm = String(now.getMinutes()).padStart(2, "0")
  const ss = String(now.getSeconds()).padStart(2, "0")
  const monthAbbr = MONTHS[m]

  return (
    <header className="sticky top-0 z-20 flex h-16 items-center gap-4 border-b border-border bg-card/95 px-4 backdrop-blur md:px-6">
      <button
        onClick={onToggleSidebar}
        className="flex h-9 w-9 flex-none items-center justify-center rounded-lg text-muted-foreground transition hover:bg-secondary hover:text-foreground"
        aria-label="Toggle sidebar"
      >
        <PanelLeft className="h-5 w-5" />
      </button>

      <div className="flex items-center gap-2.5">
        <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-accent text-accent-foreground">
          <Calendar className="h-[18px] w-[18px]" />
        </span>
        <div className="leading-tight">
          <p className="text-sm font-semibold text-foreground">
            Account Period <span className="text-primary">{monthAbbr} {y}</span>
          </p>
          <p className="text-xs text-muted-foreground">{d} {monthAbbr} {y} {hh}:{mm}:{ss}</p>
        </div>
      </div>

      <div className="ml-auto flex items-center gap-1 sm:gap-2">
        <IconButton label="Search">
          <Search className="h-[18px] w-[18px]" />
        </IconButton>
        <IconButton label="Language">
          <Globe className="h-[18px] w-[18px]" />
        </IconButton>
        <div className="relative">
          <IconButton label="Notifications">
            <Bell className="h-[18px] w-[18px]" />
          </IconButton>
          <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-destructive px-1 text-[10px] font-bold text-destructive-foreground">
            13
          </span>
        </div>
        <IconButton label={`Switch to ${nextTheme} mode`} onClick={() => setTheme(nextTheme)}>
          {theme === "dark" ? <Sun className="h-[18px] w-[18px]" /> : <Moon className="h-[18px] w-[18px]" />}
        </IconButton>

        <div className="mx-1 hidden h-8 w-px bg-border sm:block" />

        <div className="flex items-center gap-3 pl-1">
          <div className="hidden text-right leading-tight sm:block">
            <p className="text-sm font-semibold text-foreground">{user?.fullName ?? user?.username ?? "User"}</p>
            <p className="text-xs text-muted-foreground">{user?.department ?? user?.userType ?? ""}</p>
          </div>
          {user?.avatar ? (
            <img
              src={user.avatar}
              alt={user.fullName ?? "User avatar"}
              className="h-10 w-10 flex-none rounded-full border-2 border-card object-cover shadow-sm ring-1 ring-border"
            />
          ) : (
            <div className="flex h-10 w-10 flex-none items-center justify-center rounded-full bg-primary/10 text-sm font-bold text-primary ring-1 ring-border">
              {(user?.firstName?.[0] ?? user?.username?.[0] ?? "U").toUpperCase()}
            </div>
          )}
          <IconButton label="Sign out" onClick={signOut}>
            <LogOut className="h-[18px] w-[18px]" />
          </IconButton>
        </div>
      </div>
    </header>
  )
}

function IconButton({ children, label, onClick }: { children: React.ReactNode; label: string; onClick?: () => void }) {
  return (
    <button
      aria-label={label}
      onClick={onClick}
      className="flex h-9 w-9 items-center justify-center rounded-lg text-muted-foreground transition hover:bg-secondary hover:text-foreground"
    >
      {children}
    </button>
  )
}
