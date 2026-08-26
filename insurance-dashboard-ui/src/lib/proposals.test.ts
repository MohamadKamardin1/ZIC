import { beforeEach, describe, expect, it, vi } from "vitest"
import { request } from "./apiClient"
import { getProposalOptions } from "./proposals"

vi.mock("./apiClient", async () => {
  const actual = await vi.importActual<typeof import("./apiClient")>("./apiClient")
  return { ...actual, request: vi.fn() }
})

const mockedRequest = vi.mocked(request)

beforeEach(() => {
  mockedRequest.mockReset()
})

describe("proposal partner option paths", () => {
  it.each(["banks", "intermediaries", "employers"])("loads %s from the canonical OL option registry", async (entity) => {
    mockedRequest.mockResolvedValue({
      entity,
      results: [{ value: "partner-1", label: "P-001 — Zanzibar Partner", meta: { partner_type: entity === "banks" ? "BANK" : "CORPORATE", active_status: "ACTIVE" } }],
      count: 1,
    } as never)

    const result = await getProposalOptions(entity)

    expect(mockedRequest).toHaveBeenCalledWith(`/api/v1/ol/options/${entity}/`)
    expect(result).toMatchObject({ count: 1, results: [{ id: "partner-1", value: "partner-1", label: "P-001 — Zanzibar Partner", reference: "partner-1" }] })
  })

  it("keeps non-partner proposal option kinds on their legacy endpoint", async () => {
    mockedRequest.mockResolvedValue({ results: [{ value: "ACTIVE", label: "Active" }], count: 1 } as never)

    await getProposalOptions("statuses")

    expect(mockedRequest).toHaveBeenCalledWith("/api/v1/ol-proposals/proposals/options/statuses/")
  })
})
