export const OPTION_CREATE_PERMISSIONS: Record<string, string> = {
  "identity-types": "system_parameters.manage",
  locations: "ol_parameters.create",
  agents: "partners.create",
  products: "ol_parameters.create",
  "plan-types": "ol_parameters.create",
  "payment-frequencies": "system_parameters.manage",
  "quote-bases": "system_parameters.manage",
  "premium-factors": "system_parameters.manage",
  "member-relations": "system_parameters.manage",
  "cover-types": "system_parameters.manage",
  "payment-modes": "system_parameters.manage",
  "investment-funds": "ol_parameters.create",
  "investment-fund-types": "ol_parameters.create",
  riders: "ol_parameters.create",
  "benefit-types": "system_parameters.manage",
  currencies: "system_parameters.manage",
}

export const OPTION_MANAGE_HREFS: Record<string, string> = {
  "identity-types": "/ordinary-life/parameters",
  locations: "/ordinary-life/parameters",
  agents: "/ordinary-life/parameters/agent-management",
  products: "/ordinary-life/parameters/product-setup",
  "plan-types": "/ordinary-life/parameters/product-setup",
  "payment-frequencies": "/ordinary-life/parameters",
  "quote-bases": "/ordinary-life/parameters",
  "premium-factors": "/ordinary-life/parameters",
  "member-relations": "/ordinary-life/parameters",
  "cover-types": "/ordinary-life/parameters",
  "payment-modes": "/ordinary-life/parameters",
  "investment-funds": "/ordinary-life/parameters/product-setup",
  "investment-fund-types": "/ordinary-life/parameters/product-setup",
  riders: "/ordinary-life/parameters/rider-setup",
  "benefit-types": "/ordinary-life/parameters",
  currencies: "/ordinary-life/parameters",
}

export const OPTION_PARAMETER_SCREEN_LABELS: Record<string, string> = {
  "identity-types": "Default Setup",
  locations: "Default Setup",
  agents: "Agent Management",
  products: "Product Setup",
  "plan-types": "Product Setup",
  "payment-frequencies": "Default Setup",
  "quote-bases": "Default Setup",
  "premium-factors": "Default Setup",
  "member-relations": "Default Setup",
  "cover-types": "Default Setup",
  "payment-modes": "Default Setup",
  "investment-funds": "Product Setup",
  "investment-fund-types": "Product Setup",
  riders: "Rider Setup",
  "benefit-types": "Default Setup",
  currencies: "Default Setup",
}

export function prettifyOptionEntity(entity: string): string {
  return entity
    .replace(/[-_]/g, " ")
    .replace(/\b\w/g, (character) => character.toUpperCase())
    .replace(/Types$/, "Types")
    .replace(/s$/, "")
}

export function hasExplicitPermission(
  permissions: Array<{ module?: string; action?: string }> | undefined,
  permissionCode: string | undefined,
): boolean {
  if (!permissionCode || !permissions) return false
  const normalized = permissionCode.toLowerCase().replace(/:/g, ".")
  const separator = normalized.lastIndexOf(".")
  const moduleKey = separator > 0 ? normalized.slice(0, separator) : normalized
  const action = separator > 0 ? normalized.slice(separator + 1) : ""
  return permissions.some((permission) => {
    const permissionModule = String(permission.module ?? "").toLowerCase().replace(/:/g, ".")
    const permissionAction = String(permission.action ?? "").toLowerCase()
    return permissionModule === moduleKey && (!action || permissionAction === action)
  })
}
