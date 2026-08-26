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
  "benefit-types": "ol_parameters.create",
  currencies: "system_parameters.manage",
}

export const OPTION_MANAGE_PERMISSIONS: Record<string, string[]> = {
  "identity-types": ["ol_parameters.configure", "system_parameters.manage"],
  locations: ["ol_parameters.configure", "partner_onboarding.configure", "partner_onboarding.manage", "system_parameters.manage"],
  branches: ["ol_parameters.configure", "partner_onboarding.configure", "partner_onboarding.manage", "system_parameters.manage"],
  branch: ["ol_parameters.configure", "partner_onboarding.configure", "partner_onboarding.manage", "system_parameters.manage"],
  agents: ["ol_parameters.configure", "partners.configure", "partners.manage", "partner_onboarding.configure", "partner_onboarding.manage"],
  intermediaries: ["ol_parameters.configure", "partners.configure", "partners.manage", "partner_onboarding.configure", "partner_onboarding.manage"],
  employers: ["ol_parameters.configure", "partners.configure", "partners.manage", "partner_onboarding.configure", "partner_onboarding.manage"],
  banks: ["ol_parameters.configure", "partners.configure", "partners.manage", "partner_onboarding.configure", "partner_onboarding.manage"],
  products: ["ol_parameters.configure"],
  product: ["ol_parameters.configure"],
  "plan-types": ["ol_parameters.configure"],
  "plan-type": ["ol_parameters.configure"],
  "payment-frequencies": ["ol_parameters.configure", "system_parameters.manage"],
  "payment-frequency": ["ol_parameters.configure", "system_parameters.manage"],
  "quote-bases": ["ol_parameters.configure", "system_parameters.manage"],
  "quote-basis": ["ol_parameters.configure", "system_parameters.manage"],
  "premium-factors": ["ol_parameters.configure", "system_parameters.manage"],
  "premium-factor": ["ol_parameters.configure", "system_parameters.manage"],
  "member-relations": ["ol_parameters.configure", "system_parameters.manage"],
  "member-relation": ["ol_parameters.configure", "system_parameters.manage"],
  "cover-types": ["ol_parameters.configure", "system_parameters.manage"],
  "cover-type": ["ol_parameters.configure", "system_parameters.manage"],
  "payment-modes": ["ol_parameters.configure", "system_parameters.manage"],
  "payment-mode": ["ol_parameters.configure", "system_parameters.manage"],
  "investment-funds": ["ol_parameters.configure"],
  "investment-fund": ["ol_parameters.configure"],
  "investment-fund-types": ["ol_parameters.configure"],
  "investment-fund-type": ["ol_parameters.configure"],
  riders: ["ol_parameters.configure"],
  rider: ["ol_parameters.configure"],
  "benefit-types": ["ol_parameters.configure"],
  "benefit-type": ["ol_parameters.configure"],
  currencies: ["ol_parameters.configure", "system_parameters.manage"],
  currency: ["ol_parameters.configure", "system_parameters.manage"],
}

export const OPTION_CHOICE_LIST_CODES: Record<string, string> = {
  "identity-types": "IDENTIFICATION_TYPE_CHOICES",
  "payment-frequencies": "OL_PREMIUM_FREQUENCY_CHOICES",
  "quote-bases": "OL_QUOTE_BASIS_CHOICES",
  "premium-factors": "OL_PREMIUM_FACTOR_CHOICES",
  "member-relations": "OL_MEMBER_RELATION_CHOICES",
  "cover-types": "OL_COVER_TYPE_CHOICES",
  "payment-modes": "OL_PAYMENT_MODE_CHOICES",
  "benefit-type-codes": "OL_BENEFIT_TYPE_CHOICES",
  currencies: "CURRENCY_CHOICES",
}

export const OPTION_REGISTRY_ENTITIES = [
  "identity-types", "locations", "agents", "products", "plan-types", "payment-frequencies", "quote-bases", "premium-factors",
  "member-relations", "cover-types", "payment-modes", "investment-funds", "investment-fund-types", "riders", "benefit-types", "currencies",
] as const

export const OPTION_MANAGE_ROUTES: Record<string, string> = {
  "identity-types": "/ordinary-life/parameters/dropdown-configuration?entity=identity-types",
  locations: "/system-parameters/partner/locations",
  branches: "/system-parameters/partner/branches",
  branch: "/system-parameters/partner/branches",
  agents: "/partners",
  intermediaries: "/partners",
  employers: "/partners",
  banks: "/partners",
  products: "/ordinary-life/parameters/product-setup?screen=products",
  product: "/ordinary-life/parameters/product-setup?screen=products",
  "plan-types": "/ordinary-life/parameters/product-setup?screen=plan-types",
  "plan-type": "/ordinary-life/parameters/product-setup?screen=plan-types",
  "payment-frequencies": "/ordinary-life/parameters/dropdown-configuration?entity=payment-frequencies",
  "payment-frequency": "/ordinary-life/parameters/dropdown-configuration?entity=payment-frequencies",
  "quote-bases": "/ordinary-life/parameters/dropdown-configuration?entity=quote-bases",
  "quote-basis": "/ordinary-life/parameters/dropdown-configuration?entity=quote-bases",
  "premium-factors": "/ordinary-life/parameters/dropdown-configuration?entity=premium-factors",
  "premium-factor": "/ordinary-life/parameters/dropdown-configuration?entity=premium-factors",
  "member-relations": "/ordinary-life/parameters/dropdown-configuration?entity=member-relations",
  "member-relation": "/ordinary-life/parameters/dropdown-configuration?entity=member-relations",
  "cover-types": "/ordinary-life/parameters/dropdown-configuration?entity=cover-types",
  "cover-type": "/ordinary-life/parameters/dropdown-configuration?entity=cover-types",
  "payment-modes": "/ordinary-life/parameters/dropdown-configuration?entity=payment-modes",
  "payment-mode": "/ordinary-life/parameters/dropdown-configuration?entity=payment-modes",
  "investment-funds": "/ordinary-life/parameters/product-setup?screen=investment-funds",
  "investment-fund": "/ordinary-life/parameters/product-setup?screen=investment-funds",
  "investment-fund-types": "/ordinary-life/parameters/product-setup?screen=investment-fund-types",
  "investment-fund-type": "/ordinary-life/parameters/product-setup?screen=investment-fund-types",
  riders: "/ordinary-life/parameters/rider-setup",
  rider: "/ordinary-life/parameters/rider-setup",
  "benefit-types": "/ordinary-life/parameters/policy-setup?screen=beneficial",
  "benefit-type": "/ordinary-life/parameters/policy-setup?screen=beneficial",
  currencies: "/ordinary-life/parameters/dropdown-configuration?entity=currencies",
  currency: "/ordinary-life/parameters/dropdown-configuration?entity=currencies",
}

// Backward-compatible export used by existing quick-create and parameter screens.
export const OPTION_MANAGE_HREFS = OPTION_MANAGE_ROUTES

export function withWizardReturnContext(route: string): string {
  if (typeof window === "undefined" || !window.location.pathname.includes("/ordinary-life/quotations")) return route
  const url = new URL(route, window.location.origin)
  const returnTo = `${window.location.pathname}${window.location.search}`
  if (returnTo) url.searchParams.set("return_to", returnTo)
  try {
    const draftId = window.sessionStorage.getItem("zic.ol-quotation.active-draft")
    if (draftId) url.searchParams.set("draft_id", draftId)
  } catch {
    // Ignore storage restrictions; the wizard also persists a local browser snapshot.
  }
  return `${url.pathname}${url.search}${url.hash}`
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
  "benefit-types": "Policy Setup · Beneficial Types",
  currencies: "Drop Down Configuration",
}

export function prettifyOptionEntity(entity: string): string {
  return entity
    .replace(/[-_]/g, " ")
    .replace(/\b\w/g, (character) => character.toUpperCase())
    .replace(/Types$/, "Types")
    .replace(/s$/, "")
}

export function hasAnyExplicitPermission(
  permissions: Array<{ module?: string; action?: string }> | undefined,
  permissionCodes: string[] | undefined,
): boolean {
  return Boolean(permissionCodes?.some((permissionCode) => hasExplicitPermission(permissions, permissionCode)))
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
