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
      message: "Email is required",
      fieldErrors: { email: ["Email is required"] },
      correlationId: "corr-123",
    })
  })
})
