import { beforeEach, describe, expect, it, vi } from "vitest"
import { request } from "./apiClient"
import { getProposal, getProposalOptions, listProposals, normalizePaginated, normalizeProposalDetail, normalizeProposalListItem } from "./proposals"

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

describe("camelCase boundary transform", () => {
  it("normalizes a camelCase detail payload from the API into the snake view model", async () => {
    mockedRequest.mockResolvedValue({
      id: "prop-1",
      proposalNumber: "OLP-2026-000001",
      status: "ENRICHMENT",
      statusBadge: { code: "ENRICHMENT", name: "Enrichment" },
      partnerNameSnapshot: "Asha Said",
      quotation: "quote-1",
      quotationNumber: "QT-2026-000101",
      quotationVersion: 3,
      underwritingStatus: "PENDING",
      currency: "TZS",
      completeness: { missing: ["documents"], requiredMissing: ["documents"], complete: false },
      planConfigs: [
        { id: "pc-1", planNameSnapshot: "Twenty Year Endowment", baseSumAssured: "5000000.00", termYears: 20, premiumAmount: "1250.50", isSelected: true },
      ],
      members: [
        { id: "m-1", memberType: "PRINCIPAL", fullNameSnapshot: "Asha Said", dateOfBirth: "1985-04-12", ageAtQuote: 41, gender: "FEMALE", smokerStatus: "NON_SMOKER", relationship: "SELF", coverageBasis: "FIXED" },
      ],
      checklist: {
        passed: false,
        items: [
          { key: "mandatory_documents_complete", passed: false, errorCode: "PROPOSAL_DOCUMENTS_INCOMPLETE", resolutionSteps: ["Upload the missing mandatory documents."], deepLink: "/proposals/{id}/documents" },
        ],
      },
      firstPremium: { linked: true, firstPremiumPosted: false, nextActions: ["Record receipt in Front Office."] },
      allowedActions: ["view", "enrich", "convert"],
    } as never)

    const detail = normalizeProposalDetail(await getProposal("prop-1"))

    expect(detail.proposalNumber).toBe("OLP-2026-000001")
    expect(detail.statusName).toBe("Enrichment")
    expect(detail.partnerName).toBe("Asha Said")
    expect(detail.quotationVersion).toBe(3)
    expect(detail.underwritingStatus).toBe("PENDING")
    expect(detail.planConfigs[0].planName).toBe("Twenty Year Endowment")
    expect(detail.members[0].fullName).toBe("Asha Said")
    expect(detail.members[0].ageAtQuote).toBe(41)
    expect(detail.completeness?.requiredMissing).toEqual(["documents"])
    expect(detail.readiness?.items[0].errorCode).toBe("PROPOSAL_DOCUMENTS_INCOMPLETE")
    expect(detail.firstPremium?.linked).toBe(true)
    expect(detail.allowedActions).toContain("convert")
  })

  it("maps a camelCase list payload onto display names, badge, and dates", async () => {
    mockedRequest.mockResolvedValue({
      count: 1,
      results: [
        {
          id: "prop-1",
          proposalNumber: "OLP-2026-000001",
          policyholder: "CoderX Sultan (PN-2026-000002)",
          agent: "Asha Salim (ZIC-AGENT-0001)",
          employer: "-",
          product: "OL_EDUCATION_SAVINGS - ZIC Elimu Bora Education Plan",
          plan: "Elimu Bora Growth Plan",
          totalPremium: "8501.50",
          currency: "TZS",
          status: "ENRICHMENT",
          statusBadge: { code: "ENRICHMENT", name: "Enrichment" },
          paymentReady: false,
          firstPremiumPosted: false,
          expiryDate: "2026-09-26",
          createdAt: "2026-08-27T18:19:13+02:00",
          allowedActions: ["view", "enrich", "upload_documents", "mark_payment_ready", "cancel"],
        },
      ],
    } as never)

    const page = normalizePaginated(await listProposals({}), normalizeProposalListItem)
    const listRow = page.results[0]

    expect(listRow.partnerName).toBe("CoderX Sultan (PN-2026-000002)")
    expect(listRow.agentName).toBe("Asha Salim (ZIC-AGENT-0001)")
    expect(listRow.employerName).toBe("-")
    expect(listRow.planName).toBe("Elimu Bora Growth Plan")
    expect(listRow.statusName).toBe("Enrichment")
    expect(listRow.createdAt).toBe("2026-08-27T18:19:13+02:00")
    expect(listRow.allowedActions).toContain("cancel")
  })
})
