import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { useAccess } from "../../lib/access"
import { request } from "../../lib/apiClient"
import { useToast } from "../../components/ui/Toast"
import OLMOrbClaimSetup from "./OLMedicalClaimSetup"

vi.mock("../../lib/apiClient", async () => {
  const actual = await vi.importActual<typeof import("../../lib/apiClient")>("../../lib/apiClient")
  return { ...actual, request: vi.fn() }
})
vi.mock("../../lib/access", () => ({ useAccess: vi.fn() }))
vi.mock("../../components/ui/Toast", () => ({ useToast: vi.fn() }))

const requestMock = vi.mocked(request)
const accessMock = vi.mocked(useAccess)
const toastMock = vi.fn()
const permissions = [
  { module: "ol_parameters", action: "view" },
  { module: "ol_parameters", action: "create" },
  { module: "ol_parameters", action: "update" },
  { module: "ol_parameters", action: "deactivate" },
]

const medicalCode = { id: "mc-1", code: "ECG", name: "ECG", is_active: true, medical_category: "CARDIAC", effective_from: "2026-01-01", effective_to: null }
const facility = { id: "facility-1", code: "FAC-1", name: "ZIC Medical Centre", is_active: true, facility_code: "FAC-1", facility_type: "HOSPITAL", registration_number: "REG-1", city: "Zanzibar", country: "TZ", approval_status: "APPROVED", partner_name: "ZIC Provider Partner" }
const practitioner = { id: "practitioner-1", code: "DOC-1", name: "Asha Suleiman", is_active: true, practitioner_code: "DOC-1", first_name: "Asha", last_name: "Suleiman", specialty: "CARDIOLOGY", license_number: "LIC-1", medical_facility: "FAC-1", approval_status: "APPROVED", partner_number: "PART-1" }
const claimStatus = { id: "status-1", code: "REGISTERED", name: "Registered", is_active: true, badge_type: "INFO", display_order: 1, is_terminal: false, is_payable: false, allowed_transitions: ["APPROVED"], effective_from: "2026-01-01", effective_to: null }
const nextStatus = { id: "status-2", code: "APPROVED", name: "Approved", is_active: true, badge_type: "SUCCESS", display_order: 2, is_terminal: false, is_payable: true, allowed_transitions: [], effective_from: "2026-01-01", effective_to: null }

function accessValue() {
  return { access: { visibleModules: ["ol_parameters"], permissions, groups: [] }, isLoading: false, isError: false, canAccess: vi.fn(() => true) }
}

function optionsPayload() {
  return { actions: { POST: {
    limit_type: { choices: [{ value: "AMOUNT", display_name: "Amount" }] },
    required_frequency: { choices: [{ value: "ANNUAL", display_name: "Annual" }] },
    habit_category: { choices: [{ value: "SMOKING", display_name: "Smoking" }] },
    underwriting_impact: { choices: [{ value: "LOADING", display_name: "Loading" }] },
    approval_status: { choices: [{ value: "APPROVED", display_name: "Approved" }] },
    claim_category: { choices: [{ value: "DEATH", display_name: "Death" }] },
    calculation_basis: { choices: [{ value: "BENEFIT", display_name: "Benefit" }] },
    duplicate_check_rule: { choices: [{ value: "POLICY", display_name: "Policy" }] },
    reason_category: { choices: [{ value: "NATURAL", display_name: "Natural" }] },
    badge_type: { choices: [{ value: "INFO", display_name: "Info" }, { value: "SUCCESS", display_name: "Success" }] },
    discharge_category: { choices: [{ value: "FULL", display_name: "Full" }] },
    correspondence_category: { choices: [{ value: "CLAIM", display_name: "Claim" }] },
    communication_channel: { choices: [{ value: "EMAIL", display_name: "Email" }] },
  } } }
}

function setupApi() {
  requestMock.mockImplementation(async (path, options) => {
    if (options?.method === "OPTIONS") return optionsPayload() as never
    if (options?.method === "POST" || options?.method === "PATCH") return {} as never
    if (String(path).includes("claim-statuses")) return { results: [claimStatus, nextStatus], count: 2, page: 1, page_size: 100 } as never
    if (String(path).includes("medical-facilities")) return { results: [facility], count: 1, page: 1, page_size: 20 } as never
    if (String(path).includes("medical-practitioners")) return { results: [practitioner], count: 1, page: 1, page_size: 20 } as never
    return { results: [medicalCode], count: 1, page: 1, page_size: 20 } as never
  })
}

describe("OLMedicalClaimSetup", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    accessMock.mockReturnValue(accessValue())
    vi.mocked(useToast).mockReturnValue({ toast: toastMock, dismiss: vi.fn() })
    setupApi()
  })

  it("renders all six Medical U/W screens and exposes partner linkage", async () => {
    render(<OLMOrbClaimSetup section="medical" />)
    expect(await screen.findByRole("columnheader", { name: "Category" })).toBeInTheDocument()
    const tabs: [string, string][] = [
      ["OL Medical Limit", "Medical code"],
      ["OL Personal Habit", "Category"],
      ["OL Medical History", "Severity"],
      ["OL Medical Facility", "Partner linkage"],
      ["OL Medical Practitioners", "Partner linkage"],
    ]
    for (const [label, column] of tabs) {
      fireEvent.click(screen.getByRole("tab", { name: label }))
      expect(await screen.findByRole("columnheader", { name: column })).toBeInTheDocument()
    }
    fireEvent.click(screen.getByRole("tab", { name: "OL Medical Facility" }))
    expect(await screen.findByText("ZIC Provider Partner")).toBeInTheDocument()
    fireEvent.click(screen.getByRole("tab", { name: "OL Medical Practitioners" }))
    expect(await screen.findByText("PART-1")).toBeInTheDocument()
  })

  it("saves a medical code through the API-backed modal", async () => {
    render(<OLMOrbClaimSetup section="medical" />)
    await screen.findByRole("columnheader", { name: "Category" })
    fireEvent.click(screen.getByRole("button", { name: "New setup" }))
    fireEvent.change(screen.getByRole("textbox", { name: /^Coderequired$/ }), { target: { value: "MRI" } })
    fireEvent.change(screen.getByRole("textbox", { name: /^Namerequired$/ }), { target: { value: "MRI" } })
    fireEvent.change(screen.getByRole("textbox", { name: /^Medical categoryrequired$/ }), { target: { value: "IMAGING" } })
    fireEvent.click(screen.getByRole("button", { name: "Save setup" }))
    await waitFor(() => expect(requestMock).toHaveBeenCalledWith("/api/v1/ol-parameters/medical-codes/", expect.objectContaining({ method: "POST", body: expect.stringContaining('"code":"MRI"') })))
  })

  it("edits claim status transitions from the transition editor", async () => {
    render(<OLMOrbClaimSetup section="claims" />)
    fireEvent.click(await screen.findByRole("tab", { name: "OL Claim Status" }))
    expect(await screen.findByText("REGISTERED")).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: /Actions for row 1/ }))
    fireEvent.click(screen.getByRole("button", { name: "Edit" }))
    const transition = await screen.findByRole("checkbox", { name: /APPROVED/ })
    expect(transition).toBeChecked()
    fireEvent.click(transition)
    fireEvent.click(screen.getByRole("button", { name: "Save setup" }))
    await waitFor(() => expect(requestMock).toHaveBeenCalledWith(expect.stringMatching(/claim-statuses\/status-1\//), expect.objectContaining({ method: "PATCH", body: expect.stringContaining('"allowed_transitions":[]') })))
  })
})
