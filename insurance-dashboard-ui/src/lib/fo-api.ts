import { apiFetchAuth } from "./api"

const FO_BASE = "/api/v1/front-office"

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

async function foGet(path: string): Promise<any> {
  const res = await apiFetchAuth(`${FO_BASE}${path}`)
  const json = await res.json()
  if (!res.ok) throw new Error(extractError(res, json))
  return json.data ?? json.results ?? json
}

async function foPost(path: string, data?: Record<string, unknown>): Promise<any> {
  const res = await apiFetchAuth(`${FO_BASE}${path}`, {
    method: "POST",
    body: data ? JSON.stringify(data) : undefined,
  })
  const json = await res.json()
  if (!res.ok) throw new Error(extractError(res, json))
  return json.data ?? json
}

async function foPatch(path: string, data: Record<string, unknown>): Promise<any> {
  const res = await apiFetchAuth(`${FO_BASE}${path}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  })
  const json = await res.json()
  if (!res.ok) throw new Error(extractError(res, json))
  return json.data ?? json
}

async function foDelete(path: string): Promise<void> {
  const res = await apiFetchAuth(`${FO_BASE}${path}`, { method: "DELETE" })
  if (!res.ok) {
    const json = await res.json().catch(() => null)
    throw new Error(extractError(res, json))
  }
}

async function foList(path: string, params?: Record<string, string>): Promise<any> {
  const url = params
    ? `${FO_BASE}${path}?${new URLSearchParams(params).toString()}`
    : `${FO_BASE}${path}`
  const res = await apiFetchAuth(url)
  const json = await res.json()
  if (!res.ok) throw new Error(extractError(res, json))
  return json.data ?? json.results ?? json
}

export const foCore = {
  // RECEIPTS
  listReceipts: (params?: Record<string, string>) => foList("/receipts/", params),
  getReceipt: (id: string) => foGet(`/receipts/${id}/`),
  createReceipt: (data: any) => foPost("/receipts/", data),
  updateReceipt: (id: string, data: any) => foPatch(`/receipts/${id}/`, data),
  deleteReceipt: (id: string) => foDelete(`/receipts/${id}/`),

  // COMMISSIONS
  listCommissions: (params?: Record<string, string>) => foList("/commissions/", params),
  getCommission: (id: string) => foGet(`/commissions/${id}/`),
  createCommission: (data: any) => foPost("/commissions/", data),
  updateCommission: (id: string, data: any) => foPatch(`/commissions/${id}/`, data),
  deleteCommission: (id: string) => foDelete(`/commissions/${id}/`),

  // COMMISSION STATEMENTS
  listCommissionStatements: (params?: Record<string, string>) => foList("/commission-statements/", params),
  getCommissionStatement: (id: string) => foGet(`/commission-statements/${id}/`),
  createCommissionStatement: (data: any) => foPost("/commission-statements/", data),
  updateCommissionStatement: (id: string, data: any) => foPatch(`/commission-statements/${id}/`, data),
  deleteCommissionStatement: (id: string) => foDelete(`/commission-statements/${id}/`),

  // REQUISITIONS
  listRequisitions: (params?: Record<string, string>) => foList("/requisitions/", params),
  getRequisition: (id: string) => foGet(`/requisitions/${id}/`),
  createRequisition: (data: any) => foPost("/requisitions/", data),
  updateRequisition: (id: string, data: any) => foPatch(`/requisitions/${id}/`, data),
  deleteRequisition: (id: string) => foDelete(`/requisitions/${id}/`),

  // PAYMENTS
  listPayments: (params?: Record<string, string>) => foList("/payments/", params),
  getPayment: (id: string) => foGet(`/payments/${id}/`),
  createPayment: (data: any) => foPost("/payments/", data),
  updatePayment: (id: string, data: any) => foPatch(`/payments/${id}/`, data),
  deletePayment: (id: string) => foDelete(`/payments/${id}/`),

  // PARAMETERS
  listParameters: (params?: Record<string, string>) => foList("/parameters/", params),
  getParameter: (id: string) => foGet(`/parameters/${id}/`),
  createParameter: (data: any) => foPost("/parameters/", data),
  updateParameter: (id: string, data: any) => foPatch(`/parameters/${id}/`, data),
  deleteParameter: (id: string) => foDelete(`/parameters/${id}/`),
}
