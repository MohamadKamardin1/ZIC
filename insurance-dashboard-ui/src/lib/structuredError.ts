/**
 * Structured error model for the ZIC Commitments UI (Error Coach).
 *
 * The backend renders every API fault into the flat shape
 * ``{ error_code, message, resolution_steps[], field_errors, doc_ref, error, meta }``
 * (see ``docs/OL_COMMITMENTS_DESIGN.md`` §9). This module normalizes any thrown
 * value — including ``ApiClientError`` and the legacy error envelope — into a
 * single structured object the UI can teach from. Prompt 6 of the backend series
 * owns the full error taxonomy; this registry carries the code families the
 * Error Coach already understands so the app never shows a bare message.
 */

import type { ApiClientError } from "./apiClient"

export const ERROR_COACH_DOC_REF = "docs/OL_COMMITMENTS_USER_GUIDE.md"

export interface ExistingReference {
  label: string
  href?: string
  number?: string
}

export interface StructuredError {
  code: string
  message: string
  resolutionSteps: string[]
  fieldErrors: Record<string, string[]>
  docRef?: string
  deepLink?: string
  deepLinkLabel?: string
  existing?: ExistingReference
  retryable: boolean
  status?: number
  raw?: unknown
}

export interface FieldErrorPair {
  field: string
  messages: string[]
}

const NOT_RETRYABLE = new Set([
  "PARAMETER_MISSING",
  "PERMISSION_DENIED",
  "UNAUTHORIZED",
  "FORBIDDEN",
  "COMMITMENT_NOT_FOUND",
])

/** Teach-first resolution instructions by code family. */
const RESOLUTION_REGISTRY: Record<string, string[]> = {
  PARAMETER_MISSING: [
    "Open Ordinary Life > Ordinary Life Parameters > Policy Setup.",
    "Enable the missing parameter row and make sure it is Active and effective as of today.",
    "Return to Commitments and retry the operation.",
  ],
  COMMITMENT_DUPLICATE: [
    "This commitment already exists — the system never creates a second one.",
    "Open the existing commitment to record or review payments against it.",
  ],
  COMMITMENT_OVERPAYMENT: [
    "Adjust the payment amount so it is equal to or below the outstanding balance.",
    "If you intentionally collected more, record the surplus as a credit per the documented assumption.",
  ],
  COMMITMENT_INVALID_TRANSITION: [
    "Review the allowed actions shown on the commitment.",
    "Choose an action that is enabled for the current commitment status.",
  ],
  COMMITMENT_ALREADY_COMPLETED: [
    "This commitment is already fully settled — no further payment is due.",
    "Open the commitment to review its allocation history.",
  ],
  COMMITMENT_NOT_FOUND: [
    "Verify the commitment number you entered.",
    "Check the list filters for source type, status, and due date range.",
    "Contact operations if the commitment was cancelled.",
  ],
  CURRENCY_MISMATCH: [
    "Choose the commitment currency, or",
    "Provide an exchange rate between the receipt currency and the commitment currency.",
  ],
  RECEIPT_REFERENCE_INVALID: [
    "Enter a receipt reference that matches a front office receipt, or",
    "Use the manual reference format documented for the receipts seam.",
  ],
  GRACE_EXPIRED_REVERSAL_BLOCKED: [
    "The payment was allocated beyond the grace window.",
    "Raise a finance review instead of reversing this allocation.",
  ],
  PERMISSION_DENIED: [
    "Request the required OL Commitments permission from an administrator.",
    "The administrator can assign a role group under User Management.",
  ],
  VALIDATION_ERROR: [
    "Fix the highlighted fields, then submit again.",
  ],
  DEFAULT: ["Review your input and try again.", "If the problem persists, contact your system administrator."],
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value)
}

function pick(details: Record<string, unknown>, ...keys: string[]): unknown {
  for (const key of keys) {
    if (details[key] !== undefined && details[key] !== null) return details[key]
  }
  return undefined
}

function stringArray(value: unknown): string[] | undefined {
  if (Array.isArray(value)) return value.map((item) => String(item))
  if (typeof value === "string") return [value]
  return undefined
}

function toFieldMap(value: unknown): Record<string, string[]> {
  if (!isRecord(value)) return {}
  const result: Record<string, string[]> = {}
  for (const [field, raw] of Object.entries(value)) {
    result[field] = stringArray(raw) ?? [String(raw)]
  }
  return result
}

/** Expand a nested error envelope into the flat field → messages map. */
function extractFieldErrors(raw: unknown, inherited: Record<string, string[]>): Record<string, string[]> {
  if (!isRecord(raw)) return inherited
  const nested = isRecord(raw.error) ? raw.error : {}
  return (
    toFieldMap(pick(raw, "field_errors", "fieldErrors")) ??
    toFieldMap(pick(nested, "field_errors", "fieldErrors")) ??
    toFieldMap(pick(raw, "errors")) ??
    inherited
  )
}

function extractResolutionSteps(raw: unknown): string[] | undefined {
  if (!isRecord(raw)) return undefined
  const nested = isRecord(raw.error) ? raw.error : {}
  return (
    stringArray(pick(raw, "resolution_steps", "resolutionSteps")) ??
    stringArray(pick(nested, "resolution_steps", "resolutionSteps")) ??
    undefined
  )
}

function extractDocRef(raw: unknown): string | undefined {
  if (!isRecord(raw)) return undefined
  const nested = isRecord(raw.error) ? raw.error : {}
  const docRef = pick(raw, "doc_ref", "docRef") ?? pick(nested, "doc_ref", "docRef")
  return typeof docRef === "string" && docRef.trim() ? docRef : undefined
}

function extractDeepLink(raw: unknown): string | undefined {
  if (!isRecord(raw)) return undefined
  const nested = isRecord(raw.error) ? raw.error : {}
  const details = isRecord(raw.details) ? raw.details : isRecord(nested.details) ? nested.details : undefined
  const link =
    pick(raw, "deep_link", "deepLink") ??
    pick(nested, "deep_link", "deepLink") ??
    pick(details ?? {}, "deep_link", "deepLink", "navigation_path", "navigationPath")
  return typeof link === "string" && link.trim() ? link.trim() : undefined
}

function extractExisting(raw: unknown, code: string): ExistingReference | undefined {
  if (code !== "COMMITMENT_DUPLICATE" && !isRecord(raw)) return undefined
  if (!isRecord(raw)) return undefined
  const nested = isRecord(raw.error) ? raw.error : undefined
  const details = isRecord(raw.details) ? raw.details : isRecord(nested?.details) ? nested.details : undefined
  const number = String(
    pick(details ?? {}, "commitment_number", "commitmentNumber", "existing_commitment", "existingCommitment", "existing_reference") ?? "",
  )
  const id = String(pick(details ?? {}, "commitment_id", "commitmentId") ?? pick(raw, "commitment_id", "commitmentId") ?? "")
  if (!number && !id) return undefined
  const href =
    id && id !== "None"
      ? `/ordinary-life/commitments/${id}`
      : number
        ? `/ordinary-life/commitments?commitment_number=${encodeURIComponent(number)}`
        : undefined
  return { label: "View existing", href, number: number || undefined }
}

function statusOf(raw: unknown): number | undefined {
  if (!isRecord(raw)) return undefined
  const statusCode = pick(raw, "status_code", "statusCode")
  return typeof statusCode === "number" ? statusCode : undefined
}

export function toStructuredError(input: unknown, fallbackMessage?: string): StructuredError {
  let code = "UNKNOWN"
  let message = fallbackMessage ?? "The request could not be completed."
  let fieldErrors: Record<string, string[]> = {}
  let status: number | undefined
  let raw: unknown = input

  if (input instanceof Error && "code" in input && typeof (input as ApiClientError).code === "string") {
    const apiError = input as ApiClientError
    code = String(apiError.code ?? "UNKNOWN").toUpperCase()
    message = apiError.message || message
    fieldErrors = apiError.fieldErrors ?? {}
    status = apiError.status
    raw = apiError.details ?? input
  } else if (input instanceof Error) {
    message = input.message || message
  } else if (isRecord(input) && typeof input.code === "string" && typeof input.message === "string" && Array.isArray(input.resolutionSteps ?? input.resolution_steps)) {
    // Already-structured error object (idempotent passthrough).
    const structuredOnly = input as unknown as Record<string, unknown>
    const resolvedCode = String(input.code ?? "UNKNOWN").toUpperCase()
    return {
      code: resolvedCode,
      message: String(input.message ?? message),
      resolutionSteps: ((input.resolutionSteps as unknown[]) ?? []).map(String) ?? [],
      fieldErrors: toFieldMap(structuredOnly.fieldErrors ?? structuredOnly.field_errors) ?? fieldErrors,
      docRef: typeof structuredOnly.docRef === "string" ? structuredOnly.docRef : ERROR_COACH_DOC_REF,
      deepLink: typeof structuredOnly.deepLink === "string" ? structuredOnly.deepLink : undefined,
      deepLinkLabel: typeof structuredOnly.deepLinkLabel === "string" ? structuredOnly.deepLinkLabel : undefined,
      existing: isRecord(structuredOnly.existing) ? (structuredOnly.existing as unknown as ExistingReference) : undefined,
      retryable:
        typeof structuredOnly.retryable === "boolean" ? structuredOnly.retryable : !NOT_RETRYABLE.has(resolvedCode),
      status: typeof structuredOnly.status === "number" ? structuredOnly.status : undefined,
      raw: input,
    }
  } else if (isRecord(input)) {
    const nested = isRecord(input.error) ? input.error : {}
    code = String(pick(input, "error_code", "errorCode") ?? pick(nested, "code") ?? "UNKNOWN").toUpperCase()
    message = String(pick(input, "message") ?? pick(nested, "message") ?? fallbackMessage ?? message)
    status = statusOf(input)
    raw = input
  }

  const details = isRecord(raw) ? raw : {}
  const resolutionSteps =
    extractResolutionSteps(details) ?? RESOLUTION_REGISTRY[code] ?? RESOLUTION_REGISTRY.DEFAULT
  const normalizedFieldErrors = extractFieldErrors(details, fieldErrors)

  return {
    code,
    message,
    resolutionSteps,
    fieldErrors: normalizedFieldErrors,
    docRef: extractDocRef(details) ?? ERROR_COACH_DOC_REF,
    deepLink: code === "PARAMETER_MISSING" ? extractDeepLink(details) ?? "/ordinary-life/parameters/policy-setup" : undefined,
    deepLinkLabel: "Open configuration",
    existing: extractExisting(details, code),
    retryable: !NOT_RETRYABLE.has(code),
    status,
    raw: input,
  }
}

export function fieldErrorPairs(error: StructuredError): FieldErrorPair[] {
  return Object.entries(error.fieldErrors ?? {}).map(([field, messages]) => ({ field, messages }))
}