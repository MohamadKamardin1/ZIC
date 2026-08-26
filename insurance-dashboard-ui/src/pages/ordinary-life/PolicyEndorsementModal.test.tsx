import { fireEvent, render, screen } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import PolicyEndorsementModal from "./PolicyEndorsementModal"
import type { PolicyDetail } from "../../lib/policies"

const { mutateMock, resetMock, toastMock, closeMock, optionsMock } = vi.hoisted(() => ({
  mutateMock: vi.fn(),
  resetMock: vi.fn(),
  toastMock: vi.fn(),
  closeMock: vi.fn(),
  optionsMock: vi.fn(),
}))

vi.mock("../../lib/policiesHooks", () => ({
  usePolicyOptions: optionsMock,
  useCreatePolicyEndorsementMutation: () => ({ mutate: mutateMock, reset: resetMock, isPending: false, error: null }),
}))
vi.mock("../../components/ui/Toast", () => ({ useToast: () => ({ toast: toastMock }) }))

const policy = {
  id: "policy-1",
  policyNumber: "ZIC-OL-2026-000001",
  policyholderDisplay: "P-000018 — Amani Salum",
  policyholderName: "Amani Salum",
  productPlanDisplay: "OL_EDU_GROWTH — Elimu Bora Growth Plan",
  agentDisplay: "AG-0004 — Faraja Intermediaries",
  currency: "TZS",
  sumAssured: "25000000.00",
  premiumAmount: "120000.00",
  premiumFrequency: "MONTHLY",
  status: "ACTIVE",
  statusDisplay: "Active",
  allowedActions: ["endorse"],
  contractSnapshot: {},
  members: [],
  riders: [],
  benefits: [],
  endorsements: [],
  auditLogs: [],
} as PolicyDetail

beforeEach(() => {
  mutateMock.mockReset()
  resetMock.mockReset()
  toastMock.mockReset()
  closeMock.mockReset()
  optionsMock.mockReturnValue({
    data: [
      { value: "ADDRESS_CHANGE", label: "Address change", meta: {} },
      { value: "PREMIUM_CHANGE", label: "Premium change", meta: { max_premium_change_percent: 10 } },
      { value: "MEMBER_ADD", label: "Add member", meta: {} },
    ],
    isError: false,
    isPending: false,
    error: null,
    refetch: vi.fn(),
  })
})

describe("PolicyEndorsementModal", () => {
  it("loads configured endorsement types and reveals a type-specific premium field", () => {
    render(<PolicyEndorsementModal open policy={policy} onClose={closeMock} />)
    const select = screen.getByRole("combobox", { name: /Endorsement type/ })
    expect(screen.getByRole("option", { name: "Address change" })).toBeInTheDocument()
    fireEvent.change(select, { target: { value: "PREMIUM_CHANGE" } })
    expect(screen.getByRole("spinbutton", { name: /New premium amount/ })).toBeInTheDocument()
    expect(screen.getByText("Configured maximum change: 10%")).toBeInTheDocument()
  })

  it("shows teachable inline validation before submitting an incomplete request", () => {
    render(<PolicyEndorsementModal open policy={policy} onClose={closeMock} />)
    fireEvent.click(screen.getByRole("button", { name: "Submit endorsement" }))
    expect(screen.getByText("Choose the type of policy change to apply.")).toBeInTheDocument()
    expect(screen.getByText("Explain why this endorsement is being requested.")).toBeInTheDocument()
    expect(mutateMock).not.toHaveBeenCalled()
  })

  it("submits a pending append-only endorsement and closes on success", () => {
    mutateMock.mockImplementation((_variables, callbacks) => callbacks.onSuccess())
    render(<PolicyEndorsementModal open policy={policy} onClose={closeMock} />)
    fireEvent.change(screen.getByRole("combobox", { name: /Endorsement type/ }), { target: { value: "ADDRESS_CHANGE" } })
    fireEvent.change(screen.getByRole("textbox", { name: /Reason \/ description/ }), { target: { value: "Customer requested a postal address update" } })
    fireEvent.click(screen.getByRole("button", { name: "Submit endorsement" }))
    expect(mutateMock).toHaveBeenCalledWith(expect.objectContaining({ id: "policy-1", payload: expect.objectContaining({ endorsement_type: "ADDRESS_CHANGE", description: "Customer requested a postal address update", changes: {} }) }), expect.any(Object))
    expect(toastMock).toHaveBeenCalledWith(expect.objectContaining({ title: "Endorsement submitted" }))
    expect(closeMock).toHaveBeenCalled()
  })
})
