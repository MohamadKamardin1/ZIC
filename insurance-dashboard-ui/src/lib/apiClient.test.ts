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
