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

export const OPTION_CHOICE_LIST_CODES: Record<string, string> = {
  "identity-types": "IDENTIFICATION_TYPE_CHOICES",
  "payment-frequencies": "OL_PREMIUM_FREQUENCY_CHOICES",
  "quote-bases": "OL_QUOTE_BASIS_CHOICES",
  "premium-factors": "OL_PREMIUM_FACTOR_CHOICES",
  "member-relations": "OL_MEMBER_RELATION_CHOICES",
  "cover-types": "OL_COVER_TYPE_CHOICES",
  "payment-modes": "OL_PAYMENT_MODE_CHOICES",
  "benefit-types": "OL_BENEFIT_TYPE_CHOICES",
  currencies: "CURRENCY_CHOICES",
}

export const OPTION_REGISTRY_ENTITIES = [
  "identity-types", "locations", "agents", "products", "plan-types", "payment-frequencies", "quote-bases", "premium-factors",
  "member-relations", "cover-types", "payment-modes", "investment-funds", "investment-fund-types", "riders", "benefit-types", "currencies",
] as const

export const OPTION_MANAGE_HREFS: Record<string, string> = {
  "identity-types": "/ordinary-life/parameters/dropdown-configuration?entity=identity-types",
  locations: "/system-parameters/partner/locations",
  agents: "/ordinary-life/parameters/agent-management",
  products: "/ordinary-life/parameters/product-setup",
  "plan-types": "/ordinary-life/parameters/product-setup",
  "payment-frequencies": "/ordinary-life/parameters/dropdown-configuration?entity=payment-frequencies",
  "quote-bases": "/ordinary-life/parameters/dropdown-configuration?entity=quote-bases",
  "premium-factors": "/ordinary-life/parameters/dropdown-configuration?entity=premium-factors",
  "member-relations": "/ordinary-life/parameters/dropdown-configuration?entity=member-relations",
  "cover-types": "/ordinary-life/parameters/dropdown-configuration?entity=cover-types",
  "payment-modes": "/ordinary-life/parameters/dropdown-configuration?entity=payment-modes",
  "investment-funds": "/ordinary-life/parameters/product-setup",
  "investment-fund-types": "/ordinary-life/parameters/product-setup",
  riders: "/ordinary-life/parameters/rider-setup",
  "benefit-types": "/ordinary-life/parameters/dropdown-configuration?entity=benefit-types",
  currencies: "/ordinary-life/parameters/dropdown-configuration?entity=currencies",
}

export const OPTION_PARAMETER_SCREEN_LABELS: Record<string, string> = {
  "identity-types": "Drop Down Configuration",
  locations: "Location Management",
  agents: "Agent Management",
  products: "Product Setup",
  "plan-types": "Product Setup",
  "payment-frequencies": "Drop Down Configuration",
  "quote-bases": "Drop Down Configuration",
  "premium-factors": "Drop Down Configuration",
  "member-relations": "Drop Down Configuration",
  "cover-types": "Drop Down Configuration",
  "payment-modes": "Drop Down Configuration",
  "investment-funds": "Product Setup",
  "investment-fund-types": "Product Setup",
  riders: "Rider Setup",
  "benefit-types": "Drop Down Configuration",
  currencies: "Drop Down Configuration",
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
