import { describe, expect, it, vi } from "vitest"
import { ApiClientError, request } from "./apiClient"

describe("api client", () => {
  it("normalizes envelope and field errors with correlation id", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(
      JSON.stringify({ success: false, message: "Validation failed", data: { email: ["Email is required"] } }),
      { status: 422, headers: { "Content-Type": "application/json", "X-Correlation-ID": "corr-123" } },
    )))

    await expect(request("/api/v1/example/", { method: "POST", body: JSON.stringify({}) })).rejects.toMatchObject({
      status: 422,
      code: "HTTP_422",
      message: "Validation failed",
      fieldErrors: { email: ["Email is required"] },
      correlationId: "corr-123",
    })
  })

  it("unwraps nested global error.details validation fields", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(
      JSON.stringify({
        success: false,
        status_code: 400,
        error: {
          code: "VALIDATION_ERROR",
          message: "Plan selection needs attention.",
          details: {
            term_years: ["Choose a policy term from 5 to 20 years. You entered 3 years."],
            plans: [{ base_sum_assured: ["Enter a base sum assured within the configured range."] }],
          },
        },
      }),
      { status: 400, headers: { "Content-Type": "application/json" } },
    )))

    await expect(request("/api/v1/ol-quotations/quotations/quote-1/plans/", { method: "POST", body: JSON.stringify({}) })).rejects.toMatchObject({
      status: 400,
      code: "VALIDATION_ERROR",
      message: "Plan selection needs attention.",
      fieldErrors: {
        term_years: ["Choose a policy term from 5 to 20 years. You entered 3 years."],
        "plans.0.base_sum_assured": ["Enter a base sum assured within the configured range."],
      },
    })
  })

  it("normalizes structured receipts errors with resolution steps and deep links", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(
      JSON.stringify({ errorCode: "RECEIPT_OVERALLOCATION", message: "The allocation total exceeds the unallocated receipt balance.", resolutionSteps: ["Reduce the allocation total."], deepLink: "/front-office/receipts", fieldErrors: {} }),
      { status: 422, headers: { "Content-Type": "application/json" } },
    )))

    await expect(request("/api/v1/front-office/receipts/receipt-1/allocate/", { method: "POST", body: JSON.stringify({}) })).rejects.toMatchObject({
      status: 422,
      code: "RECEIPT_OVERALLOCATION",
      resolutionSteps: ["Reduce the allocation total."],
      deepLink: "/front-office/receipts",
    })
  })

  it("preserves top-level quick-create errors when data is null", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(
      JSON.stringify({
        success: false,
        status_code: 400,
        message: "Quick-create validation failed.",
        errors: { code: ["An option with this code already exists."] },
        data: null,
      }),
      { status: 400, headers: { "Content-Type": "application/json" } },
    )))

    await expect(request("/api/v1/ol/options/payment-frequencies/quick-create/", { method: "POST", body: JSON.stringify({}) })).rejects.toMatchObject({
      status: 400,
      message: "Quick-create validation failed.",
      fieldErrors: { code: ["An option with this code already exists."] },
    })
  })
})
