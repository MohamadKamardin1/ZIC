import { createContext, useContext, useMemo, type ReactNode } from "react"
import { useQuery } from "@tanstack/react-query"
import { Navigate, useLocation } from "react-router-dom"
import { fetchAccessMetadata, type AccessMetadata } from "./apiClient"
import { useAuth } from "./auth"

interface AccessContextValue {
  access: AccessMetadata
  isLoading: boolean
  isError: boolean
  isSuperAdmin: boolean
  canAccess: (moduleKey: string) => boolean
  hasPermission?: (permissionCode: string) => boolean
}

const AccessContext = createContext<AccessContextValue | null>(null)

function fallbackAccess(): AccessMetadata {
  return { visibleModules: [], permissions: [], groups: [] }
}

export function AccessProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth()
  const query = useQuery({
    queryKey: ["iam", "me", "access"],
    queryFn: fetchAccessMetadata,
    enabled: Boolean(user),
    staleTime: 5 * 60 * 1000,
    retry: false,
  })

  const access = useMemo<AccessMetadata>(() => {
    const remote = query.data
    if (remote && (remote.visibleModules.length > 0 || remote.permissions.length > 0)) return remote
    return {
      visibleModules: [],
      permissions: user?.permissions ?? [],
      groups: user?.groups ?? [],
    }
  }, [query.data, user?.groups, user?.permissions])

  const isSuperAdmin = useMemo(() => {
    const normalizedUserType = user?.userType?.toUpperCase().replace(/[\s-]+/g, "_")
    return query.data?.isSuperuser === true || user?.isSuperuser === true || normalizedUserType === "SUPER_ADMIN" || user?.groups?.some(
      (group) => group.toUpperCase().replace(/[\s-]+/g, "_") === "SUPER_ADMIN",
    ) === true
  }, [query.data?.isSuperuser, user?.groups, user?.isSuperuser, user?.userType])

  const hasPermission = (permissionCode: string): boolean => {
    if (!permissionCode || isSuperAdmin) return Boolean(permissionCode)
    const normalized = permissionCode.toLowerCase().replace(/:/g, ".")
    const separator = normalized.lastIndexOf(".")
    const moduleKey = separator > 0 ? normalized.slice(0, separator) : normalized
    const action = separator > 0 ? normalized.slice(separator + 1) : ""
    return access.permissions.some((permission) => {
      const permissionModule = String(permission.module ?? "").toLowerCase().replace(/:/g, ".")
      const permissionAction = String(permission.action ?? "").toLowerCase()
      return permissionModule === moduleKey && (!action || permissionAction === action)
    })
  }

  const canAccess = (moduleKey: string): boolean => {
    if (!moduleKey || isSuperAdmin) return true
    const aliases = new Set([moduleKey.toLowerCase()])
    if (moduleKey.toLowerCase().startsWith("ol_")) aliases.add("ordinary_life")
    if (moduleKey.toLowerCase().startsWith("gl_")) aliases.add("group_life")
    if (moduleKey.toLowerCase().startsWith("gc_")) aliases.add("group_credit")
    if (access.visibleModules.length > 0) {
      return access.visibleModules.some((module) => aliases.has(module.toLowerCase()))
    }
    if (access.permissions.length === 0) return true
    return access.permissions.some((permission) => aliases.has(permission.module.toLowerCase()))
  }

  return (
    <AccessContext.Provider value={{ access, isLoading: query.isLoading, isError: query.isError, isSuperAdmin, canAccess, hasPermission }}>
      {children}
    </AccessContext.Provider>
  )
}

export function useAccess() {
  const context = useContext(AccessContext)
  if (!context) throw new Error("useAccess must be used within AccessProvider")
  return context
}

const ROUTE_MODULES: Array<[string, string]> = [
  ["/onboarding", "partner_onboarding"],
  ["/partners", "partners"],
  ["/ordinary-life/quotations", "ol_quotations"],
  ["/ordinary-life/proposals", "ol_proposals"],
  ["/ordinary-life/policies", "ol_policies"],
  ["/ordinary-life/claims", "ol_claims"],
  ["/ordinary-life/loans", "ol_loans"],
  ["/ordinary-life/withdrawals", "ol_withdrawals"],
  ["/ordinary-life/commitments", "ol_commitments"],
  ["/ordinary-life/maturity-installments", "ol_maturity_installments"],
  ["/ordinary-life/parameters", "ol_parameters"],
  ["/ordinary-life/setup", "ol_parameters"],
  ["/ordinary-life", "ordinary_life"],
  ["/group-life/quotations", "gl_quotations"],
  ["/group-life/claims", "gl_claims"],
  ["/group-life", "group_life"],
  ["/group-credit/quotations", "gc_quotations"],
  ["/group-credit/claims", "gc_claims"],
  ["/group-credit", "group_credit"],
  ["/front-office", "front_office"],
  ["/reports", "reports"],
  ["/system-parameters", "system_parameters"],
  ["/user-management", "user_management"],
  ["/approvals", "approvals"],
]

export function routeModuleKey(pathname: string): string | null {
  return ROUTE_MODULES.find(([prefix]) => pathname === prefix || pathname.startsWith(`${prefix}/`))?.[1] ?? null
}

export function AccessDenied() {
  return (
    <div className="mx-auto flex min-h-[52vh] max-w-2xl items-center justify-center px-6 py-12">
      <section className="surface-card w-full p-8 text-center">
        <div className="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-2xl bg-danger-soft text-danger">
          <span className="text-2xl font-bold">!</span>
        </div>
        <h1 className="text-xl font-semibold text-foreground">Access restricted</h1>
        <p className="mt-2 text-sm text-muted-foreground">Your current access profile does not include this workspace.</p>
        <a className="button-primary mt-6 inline-flex" href="/">Return to dashboard</a>
      </section>
    </div>
  )
}

export function AccessGate({ children }: { children: ReactNode }) {
  const location = useLocation()
  const { canAccess, isLoading } = useAccess()
  const moduleKey = routeModuleKey(location.pathname)
  if (isLoading && moduleKey) {
    return <div className="flex min-h-[52vh] items-center justify-center text-sm text-muted-foreground">Loading access profile…</div>
  }
  if (moduleKey && !canAccess(moduleKey)) return <AccessDenied />
  return <>{children}</>
}

/**
 * Gate a screen behind an exact permission code (e.g. ``ol_commitments.view``).
 * Super admins always pass; the fallback renders {@link AccessDenied}.
 */
export function RequirePermission({
  permission,
  children,
  fallback,
}: {
  permission: string
  children: ReactNode
  fallback?: ReactNode
}) {
  const { hasPermission, isSuperAdmin, isLoading } = useAccess()
  if (isLoading) {
    return <div className="flex min-h-[52vh] items-center justify-center text-sm text-muted-foreground">Loading access profile…</div>
  }
  if (isSuperAdmin || (hasPermission?.(permission) ?? false)) return <>{children}</>
  return <>{fallback ?? <AccessDenied />}</>
}

export function defaultAccess(): AccessMetadata {
  return fallbackAccess()
}
