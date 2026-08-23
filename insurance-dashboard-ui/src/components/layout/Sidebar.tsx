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
  ListTodo,
  BellRing,
  CircleDollarSign,
  BarChart3,
  type LucideIcon,
} from "lucide-react"
import { ZicLogo } from "../ZicLogo"
import { useAuth } from "../../lib/auth"
import { useLanguage } from "../../lib/language"
import { routeModuleKey, useAccess } from "../../lib/access"

interface SubNavItem {
  label: string
  icon: LucideIcon
  path?: string
  children?: SubNavItem[]
  permission?: { module: string; action: string }
}

interface NavItem {
  label: string
  icon: LucideIcon
  path?: string
  expandable?: boolean
  children?: SubNavItem[]
  permission?: { module: string; action: string }
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

const OL_PARAMETER_CHILDREN: SubNavItem[] = [
  { label: "Default Setup", icon: Settings, path: "/ordinary-life/parameters" },
  { label: "Drop Down Configuration", icon: Grip, path: "/ordinary-life/parameters/dropdown-configuration" },
  { label: "Policy Setup", icon: FileText, path: "/ordinary-life/parameters/policy-setup" },
  { label: "Product Setup", icon: ShieldCheck, path: "/ordinary-life/parameters/product-setup" },
  { label: "Product Rating", icon: BarChart3, path: "/ordinary-life/parameters/product-rating" },
  { label: "Rider Setup", icon: FileCheck, path: "/ordinary-life/parameters/rider-setup" },
  { label: "Agent Management", icon: UserCog, path: "/ordinary-life/parameters/agent-management" },
  { label: "Loan Setup", icon: Banknote, path: "/ordinary-life/parameters/loan-setup" },
  { label: "Medical U/W", icon: Users, path: "/ordinary-life/parameters/medical-uw" },
  { label: "Claim Setup", icon: FileSpreadsheet, path: "/ordinary-life/parameters/claim-setup" },
]

const NAV: NavItem[] = [
  { label: "Dashboard", icon: LayoutDashboard, path: "/" },
  { label: "Partner On-boarding", icon: UserPlus, children: [
    { label: "Partner", icon: UserPlus, path: "/onboarding" },
  ] },
  { label: "Ordinary Life", icon: Users, expandable: true, children: [
    { label: "Quotations", icon: FileText, path: "/ordinary-life/quotations" },
    { label: "Commitments", icon: FileText, path: "/ordinary-life/commitments", permission: { module: "ol_commitments", action: "view" } },
    { label: "Proposals", icon: FileText, path: "/ordinary-life/proposals", permission: { module: "ol_proposals", action: "view" } },
    { label: "Policies", icon: ShieldCheck, path: "/ordinary-life/policies" },
    { label: "Loans", icon: FileText, path: "/ordinary-life/loans" },
    { label: "Withdrawals", icon: FileText, path: "/ordinary-life/withdrawals" },
    { label: "Claims", icon: FileText, path: "/ordinary-life/claims" },
    { label: "Maturity Installments", icon: FileText, path: "/ordinary-life/maturity-installments" },
    { label: "Ordinary Life Parameters", icon: Settings, children: OL_PARAMETER_CHILDREN },
  ] },
  { label: "Group Life", icon: ShieldCheck, expandable: true, children: [
    { label: "Quotations", icon: FileText, path: "/group-life/quotations" },
    { label: "Schemes", icon: ShieldCheck, path: "/group-life/schemes" },
    { label: "Members", icon: Users, path: "/group-life/members" },
    { label: "Claims", icon: FileText, path: "/group-life/claims" },
    { label: "Medical U/W", icon: Users, path: "/group-life/medical-uw" },
    { label: "Setup", icon: Settings, path: "/group-life/setup" },
  ] },
  { label: "Group Credit", icon: CreditCard, expandable: true, children: [
    { label: "Quotations", icon: FileText, path: "/group-credit/quotations" },
    { label: "Schemes", icon: ShieldCheck, path: "/group-credit/schemes" },
    { label: "Renewals", icon: Clock, path: "/group-credit/renewals" },
    { label: "Borrowers", icon: Users, path: "/group-credit/borrowers" },
    { label: "Claims", icon: FileText, path: "/group-credit/claims" },
    { label: "Medical U/W", icon: Users, path: "/group-credit/medical-uw" },
    { label: "Setup", icon: Settings, path: "/group-credit/setup" },
  ] },
  { label: "Front Office", icon: Building2, expandable: true, children: [
    { label: "Receipts", icon: Banknote, path: "/front-office/receipts" },
    { label: "Commissions", icon: FileSpreadsheet, path: "/front-office/commissions" },
    { label: "Commission Statement", icon: FileText, path: "/front-office/commission-statements" },
    { label: "Requisitions", icon: FileText, path: "/front-office/requisitions" },
    { label: "Payments", icon: Banknote, path: "/front-office/payments" },
    { label: "Front Office Parameters", icon: Settings, path: "/front-office/parameters" },
  ] },
  { label: "Workspace", icon: LayoutDashboard, expandable: true, children: [
    { label: "Tasks", icon: ListTodo, path: "/tasks" },
    { label: "Alerts", icon: BellRing, path: "/alerts" },
    { label: "Notifications", icon: BellRing, path: "/notifications" },
    { label: "Currencies", icon: CircleDollarSign, path: "/currencies" },
  ] },
  { label: "Reports", icon: BarChart3, path: "/reports" },
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
  {
    label: "User Management",
    icon: UserCog,
    expandable: true,
    children: [
      { label: "Permission Groups", icon: Grip, path: "/user-management/permission-groups" },
      { label: "Permissions", icon: ShieldCheck, path: "/user-management/permissions" },
      { label: "User Groups", icon: Users, path: "/user-management/user-groups" },
      { label: "Users", icon: User, path: "/user-management/users" },
    ],
  },
  { label: "Approvals", icon: CheckSquare, path: "/approvals" },
  { label: "Help & Support", icon: HelpCircle, path: "/help" },
]

function isActivePath(path: string | undefined, current: string): boolean {
  if (!path) return false
  // The OL Default Setup route is the parent landing page, not an active
  // wildcard for its sibling parameter screens.
  if (path === "/ordinary-life/parameters") return current === path
  return current === path || current.startsWith(path + "/")
}

function isParentOfAny(paths: (string | undefined)[], current: string): boolean {
  return paths.some((p) => p && p !== "/" && current.startsWith(p))
}

function isNavItemVisible(
  item: SubNavItem | NavItem,
  canAccess: (moduleKey: string) => boolean,
  hasPermission: (permissionCode: string) => boolean,
): boolean {
  if (item.permission) {
    const code = `${item.permission.module}.${item.permission.action}`
    if (!hasPermission(code)) return false
  }
  const key = item.path ? routeModuleKey(item.path) : null
  if (key && !canAccess(key)) return false
  if (!item.children?.length) return true
  return item.children.some((child) => isNavItemVisible(child, canAccess, hasPermission))
}

function SubMenuItem({ item, depth, canAccess, hasPermission }: { item: SubNavItem; depth: number; canAccess: (moduleKey: string) => boolean; hasPermission: (permissionCode: string) => boolean }) {
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
          {item.children!.filter((child) => isNavItemVisible(child, canAccess, hasPermission)).map((child) => (
            <SubMenuItem key={child.label} item={child} depth={depth + 1} canAccess={canAccess} hasPermission={hasPermission} />
          ))}
        </ul>
      )}
    </li>
  )
}

export function Sidebar({ open }: { open: boolean }) {
  const location = useLocation()
  const navigate = useNavigate()
  const { user } = useAuth()
  const { t } = useLanguage()
  const { canAccess, hasPermission: hasExactPermission } = useAccess()
  const hasPermission = (permissionCode: string) => hasExactPermission?.(permissionCode) ?? false
  const [expanded, setExpanded] = useState<string[]>(() => {
    const items: string[] = []
    for (const item of NAV) {
      if (item.children) {
        // Always expand items that have children (like Partner On-boarding)
        items.push(item.label)
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

  const visibleNav = NAV.filter((item) => isNavItemVisible(item, canAccess, hasPermission))

  return (
    <aside
      className={`fixed inset-y-0 left-0 z-30 flex w-64 flex-col overflow-hidden border-r border-border bg-sidebar transition-transform duration-200 ease-out ${open ? "translate-x-0" : "-translate-x-full"}`}
    >
      <div className="flex h-16 items-center border-b border-border px-6">
        <ZicLogo size={26} />
      </div>

      <nav className="flex-1 overflow-y-auto px-3 py-4">
        <ul className="flex flex-col gap-1">
          {visibleNav.map((item) => {
            const active = isActivePath(item.path, location.pathname)
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
                    {item.children.filter((child) => isNavItemVisible(child, canAccess, hasPermission)).map((child) => (
                      <SubMenuItem key={child.label} item={child} depth={1} canAccess={canAccess} hasPermission={hasPermission} />
                    ))}
                  </ul>
                )}
              </li>
            )
          })}
        </ul>
      </nav>

      <div className="border-t border-border p-3">
        <button onClick={() => navigate("/help")} className="flex w-full items-center gap-3 whitespace-nowrap rounded-lg border border-border bg-secondary/60 px-3 py-2.5 text-sm font-medium text-sidebar-foreground transition hover:border-primary/30 hover:bg-secondary">
          <span className="flex h-7 w-7 flex-none items-center justify-center rounded-md bg-accent text-primary">
            <HelpCircle className="h-[18px] w-[18px]" />
          </span>
          <span className="flex-1 text-left">{t("help")}</span>
        </button>
      </div>
    </aside>
  )
}
