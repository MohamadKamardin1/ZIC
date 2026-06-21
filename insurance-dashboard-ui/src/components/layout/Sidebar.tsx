import { useLocation, useNavigate } from "react-router-dom"
import {
  LayoutDashboard,
  UserPlus,
  Users,
  ShieldCheck,
  CreditCard,
  Building2,
  FileText,
  Settings,
  UserCog,
  CheckSquare,
  HelpCircle,
  ChevronDown,
  PanelLeftClose,
  type LucideIcon,
} from "lucide-react"
import { ZicLogo } from "../ZicLogo"

interface NavItem {
  label: string
  icon: LucideIcon
  path?: string
  expandable?: boolean
}

const NAV: NavItem[] = [
  { label: "Dashboard", icon: LayoutDashboard, path: "/" },
  { label: "Partner On-boarding", icon: UserPlus, path: "/onboarding", expandable: true },
  { label: "Ordinary Life", icon: Users, expandable: true },
  { label: "Group Life", icon: ShieldCheck, expandable: true },
  { label: "Group Credit", icon: CreditCard, expandable: true },
  { label: "Front Office", icon: Building2, expandable: true },
  { label: "Reports", icon: FileText },
  { label: "System Parameters", icon: Settings, expandable: true },
  { label: "User Management", icon: UserCog, expandable: true },
  { label: "Approvals", icon: CheckSquare, expandable: true },
]

export function Sidebar({ open }: { open: boolean }) {
  const location = useLocation()
  const navigate = useNavigate()

  return (
    <aside
      className={`fixed inset-y-0 left-0 z-30 flex w-64 flex-col overflow-hidden border-r border-border bg-sidebar transition-transform duration-200 ease-out ${open ? "translate-x-0" : "-translate-x-full"}`}
    >
      <div className="flex h-16 items-center border-b border-border px-6">
        <ZicLogo size={26} />
      </div>

      <nav className="flex-1 overflow-y-auto px-3 py-4">
        <ul className="flex flex-col gap-1">
          {NAV.map((item) => {
            const active = item.path
              ? location.pathname === item.path || location.pathname.startsWith(item.path + "/")
              : false
            const Icon = item.icon
            return (
              <li key={item.label}>
                <button
                  onClick={() => item.path && navigate(item.path)}
                  className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition ${
                    active
                      ? "bg-sidebar-accent text-sidebar-accent-foreground"
                      : "text-sidebar-foreground hover:bg-secondary"
                  }`}
                >
                  <Icon className="h-[18px] w-[18px] flex-none" />
                  <span className="flex-1 text-left">{item.label}</span>
                  {item.expandable && <ChevronDown className="h-4 w-4 opacity-60" />}
                </button>
              </li>
            )
          })}
        </ul>
      </nav>

      <div className="border-t border-border p-3">
        <button className="flex w-full items-center gap-3 whitespace-nowrap rounded-lg border border-border bg-secondary/60 px-3 py-2.5 text-sm font-medium text-sidebar-foreground transition hover:border-primary/30 hover:bg-secondary">
          <span className="flex h-7 w-7 flex-none items-center justify-center rounded-md bg-accent text-primary">
            <HelpCircle className="h-[18px] w-[18px]" />
          </span>
          <span className="flex-1 text-left">Help &amp; Support</span>
        </button>
      </div>
    </aside>
  )
}
