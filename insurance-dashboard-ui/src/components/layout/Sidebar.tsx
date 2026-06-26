import { useState } from "react"
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
  ChevronRight,
  Sliders,
  FileCheck,
  BookOpen,
  Scale,
  Hash,
  Clock,
  Grip,
  Columns,
  User,
  Lock,
  Type,
  MapPin,
  Banknote,
  FileSpreadsheet,
  Contact,
  Landmark,
  type LucideIcon,
} from "lucide-react"
import { ZicLogo } from "../ZicLogo"

interface SubNavItem {
  label: string
  icon: LucideIcon
  path?: string
  children?: SubNavItem[]
}

interface NavItem {
  label: string
  icon: LucideIcon
  path?: string
  expandable?: boolean
  children?: SubNavItem[]
}

const PARTNER_TYPE_CHILDREN: SubNavItem[] = [
  { label: "Partner Types", icon: Type, path: "/system-parameters/partner/partner-types" },
  { label: "Branches", icon: Building2, path: "/system-parameters/partner/branches" },
  { label: "Locations", icon: MapPin, path: "/system-parameters/partner/locations" },
  { label: "Partner Type Setup", icon: Settings, path: "/system-parameters/partner/partner-types/:id/setup" },
]

const PARTNER_PARAMS_CHILDREN: SubNavItem[] = [
  { label: "Workflow & Statuses", icon: Scale, path: "/system-parameters/partner/workflow" },
  { label: "Dropdown Choices", icon: Grip, path: "/system-parameters/partner/choices" },
  { label: "Numbering Formats", icon: Hash, path: "/system-parameters/partner/numbering" },
  { label: "Doc Config per Type", icon: FileCheck, path: "/system-parameters/partner/documents" },
  { label: "Field Config per Type", icon: Columns, path: "/system-parameters/partner/fields" },
  { label: "Contact Config per Type", icon: Users, path: "/system-parameters/partner/contact-types" },
  { label: "Bank Config per Type", icon: Landmark, path: "/system-parameters/partner/bank-types" },
  { label: "Compliance Rules", icon: ShieldCheck, path: "/system-parameters/partner/compliance" },
  { label: "Field Validation", icon: BookOpen, path: "/system-parameters/partner/validation" },
  { label: "Scheduled Tasks", icon: Clock, path: "/system-parameters/partner/schedules" },
  { label: "Partner Type Config", icon: UserCog, children: PARTNER_TYPE_CHILDREN },
]

const NAV: NavItem[] = [
  { label: "Dashboard", icon: LayoutDashboard, path: "/" },
  { label: "Partner On-boarding", icon: UserPlus, children: [
    { label: "Partner", icon: UserPlus, path: "/onboarding" },
  ] },
  { label: "Ordinary Life", icon: Users, expandable: true },
  { label: "Group Life", icon: ShieldCheck, expandable: true },
  { label: "Group Credit", icon: CreditCard, expandable: true },
  { label: "Front Office", icon: Building2, expandable: true },
  { label: "Reports", icon: FileText },
  {
    label: "System Parameters",
    icon: Settings,
    expandable: true,
    children: [
      { label: "General Parameters", icon: Sliders, path: "/system-parameters/general" },
      { label: "Partner Parameters", icon: Users, children: PARTNER_PARAMS_CHILDREN },
      {
        label: "User Parameters",
        icon: UserCog,
        children: [
          { label: "General Settings", icon: Sliders, path: "/system-parameters/users" },
          { label: "Password Policy", icon: Lock, path: "/system-parameters/users/password-policy" },
        ],
      },
      { label: "Reinsurance Parameters", icon: ShieldCheck, path: "/system-parameters/reinsurance" },
    ],
  },
  { label: "User Management", icon: UserCog, expandable: true },
  { label: "Approvals", icon: CheckSquare, expandable: true },
]

function isActivePath(path: string | undefined, current: string): boolean {
  if (!path) return false
  return current === path || current.startsWith(path + "/")
}

function isParentOfAny(paths: (string | undefined)[], current: string): boolean {
  return paths.some((p) => p && p !== "/" && current.startsWith(p))
}

function SubMenuItem({ item, depth }: { item: SubNavItem; depth: number }) {
  const location = useLocation()
  const navigate = useNavigate()
  const [open, setOpen] = useState(isParentOfAny((item.children ?? []).map((c) => c.path), location.pathname))
  const active = isActivePath(item.path, location.pathname)
  const Icon = item.icon
  const hasChildren = item.children && item.children.length > 0

  return (
    <li>
      <button
        onClick={() => {
          if (hasChildren) {
            setOpen((o) => !o)
          } else if (item.path) {
            navigate(item.path)
          }
        }}
        className={`flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition ${
          active
            ? "bg-sidebar-accent text-sidebar-accent-foreground"
            : "text-sidebar-foreground hover:bg-secondary"
        }`}
        style={{ paddingLeft: `${12 + depth * 12}px` }}
      >
        <Icon className="h-[15px] w-[15px] flex-none" />
        <span className="flex-1 text-left truncate">{item.label}</span>
        {hasChildren && (
          <ChevronRight
            className={`h-3.5 w-3.5 flex-none transition-transform duration-200 ${open ? "rotate-90" : ""}`}
          />
        )}
      </button>
      {hasChildren && open && (
        <ul className="flex flex-col gap-0.5 pt-0.5">
          {item.children!.map((child) => (
            <SubMenuItem key={child.label} item={child} depth={depth + 1} />
          ))}
        </ul>
      )}
    </li>
  )
}

export function Sidebar({ open }: { open: boolean }) {
  const location = useLocation()
  const navigate = useNavigate()
  const [expanded, setExpanded] = useState<string[]>(() => {
    const items: string[] = []
    for (const item of NAV) {
      if (item.children) {
        const childPaths = collectPaths(item.children)
        if (isParentOfAny(childPaths, location.pathname)) {
          items.push(item.label)
        }
      }
    }
    return items
  })

  function toggleExpand(label: string) {
    setExpanded((prev) =>
      prev.includes(label) ? prev.filter((l) => l !== label) : [...prev, label],
    )
  }

  function collectPaths(items: SubNavItem[]): string[] {
    const paths: string[] = []
    for (const item of items) {
      if (item.path) paths.push(item.path)
      if (item.children) paths.push(...collectPaths(item.children))
    }
    return paths
  }

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
            const isExpanded = expanded.includes(item.label)

            return (
              <li key={item.label}>
                <button
                  onClick={() => {
                    if (item.children) {
                      toggleExpand(item.label)
                    } else if (item.path) {
                      navigate(item.path)
                    }
                  }}
                  className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition ${
                    active
                      ? "bg-sidebar-accent text-sidebar-accent-foreground"
                      : "text-sidebar-foreground hover:bg-secondary"
                  }`}
                >
                  <Icon className="h-[18px] w-[18px] flex-none" />
                  <span className="flex-1 text-left truncate">{item.label}</span>
                  {item.children && (
                    <ChevronDown
                      className={`h-4 w-4 flex-none transition-transform duration-200 ${isExpanded ? "" : "-rotate-90"}`}
                    />
                  )}
                  {item.expandable && !item.children && <ChevronDown className="h-4 w-4 opacity-60" />}
                </button>

                {item.children && isExpanded && (
                  <ul className="flex flex-col gap-0.5 pt-0.5">
                    {item.children.map((child) => (
                      <SubMenuItem key={child.label} item={child} depth={1} />
                    ))}
                  </ul>
                )}
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
