import { Navigate } from "react-router-dom"
import { useAuth } from "../lib/auth"
import type { ReactNode } from "react"

interface RequirePermissionProps {
  module: string
  action: string
  children: ReactNode
  fallback?: ReactNode
}

export function RequirePermission({ module, action, children, fallback }: RequirePermissionProps) {
  const { user, hasPermission } = useAuth()

  if (!user) {
    return <Navigate to="/login" replace />
  }

  if (!hasPermission(module, action)) {
    if (fallback) {
      return <>{fallback}</>
    }
    return <Navigate to="/unauthorized" replace />
  }

  return <>{children}</>
}

interface PermissionGuardProps {
  permissions: Array<{ module: string; action: string }>
  children: ReactNode
  fallback?: ReactNode
}

export function PermissionGuard({ permissions, children, fallback }: PermissionGuardProps) {
  const { user, hasAnyPermission } = useAuth()

  if (!user) {
    return <Navigate to="/login" replace />
  }

  if (!hasAnyPermission(permissions)) {
    if (fallback) {
      return <>{fallback}</>
    }
    return <Navigate to="/unauthorized" replace />
  }

  return <>{children}</>
}
