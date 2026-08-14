import os

models = [
    ("lookup-values", "LookupValue", "/setup"),
    ("default-system-parameters", "DefaultSystemParameter", "/setup"),
    ("override-commission-setup", "OverrideCommissionSetup", "/setup"),
    ("computation-approaches", "ComputationApproach", "/setup"),
    ("maturity-claim-setup", "MaturityClaimSetup", "/setup"),
    ("anticipated-endowment-rates", "AnticipatedEndowmentInstallmentRate", "/setup"),
    ("grace-periods", "GracePeriod", "/setup"),
    ("policy-statuses", "PolicyStatus", "/setup"),
    ("policy-renewal-statuses", "PolicyRenewalStatus", "/setup"),
    ("beneficiary-types", "BeneficiaryType", "/setup"),
    ("member-cover-configurations", "MemberCoverConfiguration", "/setup"),
    ("surrender-setup", "SurrenderSetup", "/setup"),
    ("paid-up-setup", "PaidUpSetup", "/setup"),
    ("surrender-value-rates", "SurrenderValueRate", "/setup"),
    ("paid-up-rates", "PaidUpRate", "/setup"),
    ("commitment-statuses", "CommitmentStatus", "/setup"),
    ("health-questions", "HealthQuestion", "/setup"),
    ("health-questionnaires", "HealthQuestionnaire", "/setup"),
    ("grace-period-notification-schedules", "GracePeriodNotificationSchedule", "/setup"),
    ("reinstatement-windows", "ReinstatementWindow", "/setup"),
]

ts_content = """/**
 * Ordinary Life — API Client
 *
 * Dedicated API functions for all Ordinary Life endpoints.
 */

import { apiFetchAuth } from "./api"

const OL_BASE = "/api/v1/ordinary-life"

// ---------------------------------------------------------------------------
// Generic helpers
// ---------------------------------------------------------------------------

function extractError(res: Response, body: unknown): string {
  if (typeof body === "object" && body !== null) {
    const b = body as Record<string, unknown>
    if (typeof b.message === "string") return b.message
    if (typeof b.detail === "string") return b.detail
    if (Array.isArray(b.non_field_errors)) return (b.non_field_errors[0] as string) ?? "Request failed."
    for (const key in b) {
      const val = b[key]
      if (Array.isArray(val) && val.length > 0) return `${key}: ${val[0] as string}`
    }
  }
  return `Request failed (${res.status}).`
}

async function olGet(path: string): Promise<any> {
  const res = await apiFetchAuth(`${OL_BASE}${path}`)
  const json = await res.json()
  if (!res.ok) throw new Error(extractError(res, json))
  return json.data ?? json.results ?? json
}

async function olPost(path: string, data?: Record<string, unknown>): Promise<any> {
  const res = await apiFetchAuth(`${OL_BASE}${path}`, {
    method: "POST",
    body: data ? JSON.stringify(data) : undefined,
  })
  const json = await res.json()
  if (!res.ok) throw new Error(extractError(res, json))
  return json.data ?? json
}

async function olPatch(path: string, data: Record<string, unknown>): Promise<any> {
  const res = await apiFetchAuth(`${OL_BASE}${path}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  })
  const json = await res.json()
  if (!res.ok) throw new Error(extractError(res, json))
  return json.data ?? json
}

async function olDelete(path: string): Promise<void> {
  const res = await apiFetchAuth(`${OL_BASE}${path}`, { method: "DELETE" })
  if (!res.ok) {
    const json = await res.json().catch(() => null)
    throw new Error(extractError(res, json))
  }
}

async function olList(path: string, params?: Record<string, string>): Promise<any> {
  const url = params
    ? `${OL_BASE}${path}?${new URLSearchParams(params).toString()}`
    : `${OL_BASE}${path}`
  const res = await apiFetchAuth(url)
  const json = await res.json()
  if (!res.ok) throw new Error(extractError(res, json))
  return json.data ?? json.results ?? json
}

// ---------------------------------------------------------------------------
// Setup API
// ---------------------------------------------------------------------------

export const olSetup = {
"""

for ep, name, prefix in models:
    # special pluralizations
    list_name = f"list{name}s"
    if name.endswith("Status"):
        list_name = f"list{name}es"
    if name == "GracePeriodNotificationSchedule":
        list_name = "listGracePeriodNotificationSchedules"
        
    ts_content += f'  {list_name}: (params?: Record<string, string>) => olList("{prefix}/{ep}/", params),\n'
    ts_content += f'  get{name}: (id: string) => olGet("{prefix}/{ep}/${{id}}/"),\n'
    ts_content += f'  create{name}: (data: any) => olPost("{prefix}/{ep}/", data),\n'
    ts_content += f'  update{name}: (id: string, data: any) => olPatch("{prefix}/{ep}/${{id}}/", data),\n'
    ts_content += f'  delete{name}: (id: string) => olDelete("{prefix}/{ep}/${{id}}/"),\n'

ts_content += "}\n"

with open("src/lib/ol-api.ts", "w") as f:
    f.write(ts_content)
