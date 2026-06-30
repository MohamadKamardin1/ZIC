// Permission constants for the entire application
export const PERMISSIONS = {
  SYSTEM_PARAMETERS: {
    READ: { module: 'system_parameters', action: 'READ' },
    CREATE: { module: 'system_parameters', action: 'CREATE' },
    UPDATE: { module: 'system_parameters', action: 'UPDATE' },
    DELETE: { module: 'system_parameters', action: 'DELETE' },
    MANAGE: { module: 'system_parameters', action: 'MANAGE' },
  },
  USERS: {
    READ: { module: 'users', action: 'READ' },
    CREATE: { module: 'users', action: 'CREATE' },
    UPDATE: { module: 'users', action: 'UPDATE' },
    DELETE: { module: 'users', action: 'DELETE' },
    MANAGE: { module: 'users', action: 'MANAGE' },
  },
  PARTNER_ONBOARDING: {
    READ: { module: 'partner_onboarding', action: 'READ' },
    CREATE: { module: 'partner_onboarding', action: 'CREATE' },
    UPDATE: { module: 'partner_onboarding', action: 'UPDATE' },
    DELETE: { module: 'partner_onboarding', action: 'DELETE' },
    REVIEW: { module: 'partner_onboarding', action: 'REVIEW' },
    APPROVE: { module: 'partner_onboarding', action: 'APPROVE' },
    COMPLIANCE: { module: 'partner_onboarding', action: 'COMPLIANCE' },
    CONVERT: { module: 'partner_onboarding', action: 'CONVERT' },
    BULK_IMPORT: { module: 'partner_onboarding', action: 'BULK_IMPORT' },
  },
  PARTNERS: {
    READ: { module: 'partners', action: 'READ' },
    CREATE: { module: 'partners', action: 'CREATE' },
    UPDATE: { module: 'partners', action: 'UPDATE' },
    DELETE: { module: 'partners', action: 'DELETE' },
    SUSPEND: { module: 'partners', action: 'SUSPEND' },
    MANAGE: { module: 'partners', action: 'MANAGE' },
  },
  PARTNER_CONFIG: {
    READ: { module: 'partner_config', action: 'READ' },
    CREATE: { module: 'partner_config', action: 'CREATE' },
    UPDATE: { module: 'partner_config', action: 'UPDATE' },
    DELETE: { module: 'partner_config', action: 'DELETE' },
    MANAGE: { module: 'partner_config', action: 'MANAGE' },
  },
  GOVERNANCE: {
    READ: { module: 'governance', action: 'READ' },
    APPROVE: { module: 'governance', action: 'APPROVE' },
    MANAGE: { module: 'governance', action: 'MANAGE' },
  },
  FINANCE: {
    READ: { module: 'finance', action: 'READ' },
    UPDATE: { module: 'finance', action: 'UPDATE' },
    ASSESS: { module: 'finance', action: 'ASSESS' },
    MANAGE: { module: 'finance', action: 'MANAGE' },
  },
  REPORTS: {
    READ: { module: 'reports', action: 'READ' },
    EXPORT: { module: 'reports', action: 'EXPORT' },
  },
  AUDIT: {
    READ: { module: 'audit', action: 'READ' },
    EXPORT: { module: 'audit', action: 'EXPORT' },
  },
} as const

export function permissionString(perm: { module: string; action: string }): string {
  return `${perm.module}:${perm.action}`
}

export function hasPermission(
  userPermissions: Array<{ module: string; action: string }>,
  module: string,
  action: string
): boolean {
  return userPermissions.some((p) => p.module === module && p.action === action)
}
