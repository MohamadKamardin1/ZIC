import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import PolicyIssuanceWizard from "./PolicyIssuanceWizard"

const { navigateMock, toastMock, useIssuableProposalsMock, useIssuePolicyMutationMock, mutateMock } = vi.hoisted(() => ({
  navigateMock: vi.fn(),
  toastMock: vi.fn(),
  useIssuableProposalsMock: vi.fn(),
  useIssuePolicyMutationMock: vi.fn(),
  mutateMock: vi.fn(),
}))

vi.mock("react-router-dom", () => ({ useNavigate: () => navigateMock }))
vi.mock("../../components/ui/Toast", () => ({ useToast: () => ({ toast: toastMock, dismiss: vi.fn() }) }))
vi.mock("../../lib/policiesHooks", () => ({
  useIssuableProposals: useIssuableProposalsMock,
  useIssuePolicyMutation: useIssuePolicyMutationMock,
}))

const readyProposal = {
  id: "proposal-ready-1",
  proposalNumber: "OLP-2026-000001",
  status: "PAYMENT_READY",
  partnerName: "P-000018 — Amani Salum",
  productName: "Elimu Bora Growth Plan",
  planName: "Education savings",
  totalPremium: 120000,
  currency: "TZS",
  paymentReady: true,
  firstPremiumPosted: true,
  allowedActions: ["view"],
}

const waitingProposal = {
  id: "proposal-waiting-1",
  proposalNumber: "OLP-2026-000002",
  status: "AWAITING_FIRST_PREMIUM",
  partnerName: "P-000019 — Halima Juma",
  productName: "ZIC Term Assurance Family",
  planName: "Family protection",
  totalPremium: 85000,
  currency: "TZS",
  paymentReady: false,
  firstPremiumPosted: false,
  allowedActions: ["view"],
}

beforeEach(() => {
  navigateMock.mockReset()
  toastMock.mockReset()
  mutateMock.mockReset()
  useIssuableProposalsMock.mockReset().mockReturnValue({ data: [readyProposal, waitingProposal], isPending: false, isError: false, error: null, refetch: vi.fn() })
  useIssuePolicyMutationMock.mockReset().mockReturnValue({ isPending: false, mutate: mutateMock })
})

describe("PolicyIssuanceWizard", () => {
  it("does not advance until a proposal is selected", async () => {
    render(<PolicyIssuanceWizard />)
    fireEvent.click(screen.getByRole("button", { name: "Next" }))
    expect(screen.getByTestId("issuance-select-step")).toBeInTheDocument()
    expect(screen.getByText("Select one proposal to continue.")).toBeInTheDocument()

    fireEvent.click(screen.getByRole("button", { name: /OLP-2026-000001/ }))
    fireEvent.click(screen.getByRole("button", { name: "Next" }))
    await waitFor(() => expect(screen.getByTestId("issuance-confirm-step")).toBeInTheDocument())
  })

  it("shows first-premium safety messaging for an unposted proposal", () => {
    render(<PolicyIssuanceWizard />)
    expect(screen.getByText("First premium not fully paid")).toBeInTheDocument()
    expect(screen.getByText("First premium ready")).toBeInTheDocument()
  })

  it("issues a ready proposal, shows the required toast, and redirects to policy detail", async () => {
    mutateMock.mockImplementation((_id: string, options: { onSuccess: (payload: unknown) => void }) => options.onSuccess({ id: "policy-issued-1", policy_number: "ZIC-OL-2026-000004" }))
    render(<PolicyIssuanceWizard />)
    fireEvent.click(screen.getByRole("button", { name: /OLP-2026-000001/ }))
    fireEvent.click(screen.getByRole("button", { name: "Next" }))
    await screen.findByTestId("issuance-confirm-step")
    const issueButton = screen.getByRole("button", { name: "Issue Policy" })
    expect(issueButton).not.toBeDisabled()
    fireEvent.click(issueButton)

    await waitFor(() => expect(mutateMock).toHaveBeenCalledWith("proposal-ready-1", expect.any(Object)))
    expect(toastMock).toHaveBeenCalledWith(expect.objectContaining({ title: "Policy ZIC-OL-2026-000004 Issued Successfully.", tone: "success" }))
    expect(navigateMock).toHaveBeenCalledWith("/ordinary-life/policies/policy-issued-1")
  })

  it("renders ErrorCoach when the backend rejects an otherwise ready proposal", async () => {
    mutateMock.mockImplementation((_id: string, options: { onError: (error: unknown) => void }) => options.onError({ status: 422, code: "POLICY_FIRST_PREMIUM_NOT_POSTED", message: "The proposal is not eligible for issuance because its first premium is not fully posted.", fieldErrors: {}, resolutionSteps: ["Complete and post the first premium, then retry."] }))
    render(<PolicyIssuanceWizard />)
    fireEvent.click(screen.getByRole("button", { name: /OLP-2026-000001/ }))
    fireEvent.click(screen.getByRole("button", { name: "Next" }))
    await screen.findByTestId("issuance-confirm-step")
    fireEvent.click(screen.getByRole("button", { name: "Issue Policy" }))

    expect(await screen.findByText("Proposal not eligible for issuance")).toBeInTheDocument()
    expect(screen.getByText("The proposal is not eligible for issuance because its first premium is not fully posted.")).toBeInTheDocument()
    expect(screen.getByText("Complete and post the first premium, then retry.")).toBeInTheDocument()
  })
})
