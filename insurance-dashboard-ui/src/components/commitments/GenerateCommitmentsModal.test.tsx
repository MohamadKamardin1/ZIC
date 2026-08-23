import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import type { ComponentProps } from "react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { GenerateCommitmentsModal } from "./GenerateCommitmentsModal"
import { dateLabel } from "../../lib/commitmentsDisplay"

const { requestMock, navigateMock, toastMock } = vi.hoisted(() => ({ requestMock: vi.fn(), navigateMock: vi.fn(), toastMock: vi.fn() }))

vi.mock("../../lib/apiClient", () => ({ request: requestMock }))

vi.mock("react-router-dom", () => ({ useNavigate: () => navigateMock }))

vi.mock("../../lib/access", () => ({
  useAccess: () => ({
    access: { visibleModules: ["ol_commitments"], permissions: [], groups: [] },
    isLoading: false,
    isSuperAdmin: false,
    canAccess: (key: string) => Boolean(key) && (key.startsWith("ol_proposals") || key.startsWith("ol_policies")),
    hasPermission: () => false,
  }),
}))

vi.mock("../../components/ui/Toast", () => ({ useToast: () => ({ toast: toastMock, dismiss: vi.fn() }) }))

const PREVIEW_ROWS = {
  rows: [
    { installmentNumber: 1, dueDate: "2026-09-01", amount: "50000.00", currency: "TZS", graceDate: "2026-10-01", lapseDate: "2026-10-16", status: "PENDING" },
    { installmentNumber: 2, dueDate: "2026-10-01", amount: "60000.00", currency: "TZS", graceDate: "2026-10-31", lapseDate: "2026-11-15", status: "PENDING" },
  ],
}

const duplicateBody = {
  error_code: "COMMITMENT_DUPLICATE",
  status_code: 422,
  message: "A commitment already exists for this source and installment 1.",
  resolution_steps: ["Open the existing commitment to record the payment against it."],
  field_errors: {},
  error: { code: "COMMITMENT_DUPLICATE", message: "duplicate", details: { commitment_number: "OLC-2026-00041", commitment_id: "dup-1" } },
}

function renderModal(props: Partial<ComponentProps<typeof GenerateCommitmentsModal>> = {}) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <GenerateCommitmentsModal open onClose={vi.fn()} onOpenManual={vi.fn()} onComplete={vi.fn()} {...props} />
    </QueryClientProvider>,
  )
}

async function chooseProposalSource() {
  const button = await screen.findByLabelText(/Proposal/)
  await waitFor(() => expect(button).not.toBeDisabled())
  fireEvent.click(button)
  const option = await screen.findByRole("option", { name: /Zanzibar Trading Co/ })
  fireEvent.click(option)
}

beforeEach(() => {
  requestMock.mockReset()
  navigateMock.mockReset()
  toastMock.mockReset()
  requestMock.mockImplementation(async (path: string, init?: RequestInit) => {
    if (path.includes("/options/sources/")) return { results: [{ id: "prop-1", label: "Zanzibar Trading Co.", reference: "OLP-2026-0001" }] }
    if (path.includes("/commitments/generate-preview/")) return PREVIEW_ROWS
    if (path.includes("/commitments/generate/")) return { created: 2, events: 2 }
    return { results: [] }
  })
})

describe("GenerateCommitmentsModal", () => {
  it("renders the dry-run preview schedule after choosing a source", async () => {
    renderModal()
    await chooseProposalSource()

    expect(await screen.findByText("TZS 50,000.00", undefined, { timeout: 5000 })).toBeInTheDocument()
    expect(screen.getByText("TZS 60,000.00")).toBeInTheDocument()
    expect(screen.getAllByRole("status").map((node) => node.textContent)).toContain("Pending")
    expect(screen.getByText(dateLabel("2026-09-01"))).toBeInTheDocument()
    expect(screen.getAllByText(dateLabel("2026-10-01")).length).toBeGreaterThan(0)
    expect(screen.getByText(dateLabel("2026-10-16"))).toBeInTheDocument()
    expect(screen.getByText(dateLabel("2026-10-31"))).toBeInTheDocument()
    expect(screen.getByText(dateLabel("2026-11-15"))).toBeInTheDocument()
    expect(screen.getByText("Grace date")).toBeInTheDocument()
    expect(screen.getByText("Lapse date")).toBeInTheDocument()
    expect(screen.getByTestId("execute-generation")).toBeEnabled()
  })

  it("shows an ErrorCoach deep link when generation parameters are missing", async () => {
    requestMock.mockImplementation(async (path: string) => {
      if (path.includes("/options/sources/")) return { results: [{ id: "prop-1", label: "Zanzibar Trading Co.", reference: "OLP-2026-0001" }] }
      throw { error_code: "PARAMETER_MISSING", message: "OL Grace Period is not configured.", resolution_steps: ["Configure the OL Grace Period row."], deep_link: "/ordinary-life/parameters/policy-setup" }
    })
    renderModal()
    await chooseProposalSource()

    const deepLink = await screen.findByTestId("error-coach-deep-link", undefined, { timeout: 5000 })
    expect(screen.getByTestId("error-coach-code")).toHaveTextContent("PARAMETER_MISSING")
    fireEvent.click(deepLink)
    expect(navigateMock).toHaveBeenCalledWith("/ordinary-life/parameters/policy-setup")
  })

  it("shows the View existing link when execution hits a duplicate", async () => {
    requestMock.mockImplementation(async (path: string, init?: RequestInit) => {
      if (path.includes("/options/sources/")) return { results: [{ id: "prop-1", label: "Zanzibar Trading Co.", reference: "OLP-2026-0001" }] }
      if (path.includes("/commitments/generate-preview/")) return PREVIEW_ROWS
      if (path.includes("/commitments/generate/")) throw duplicateBody
      return { results: [] }
    })
    renderModal()
    await chooseProposalSource()
    await screen.findByText("TZS 50,000.00", undefined, { timeout: 5000 })

    fireEvent.click(screen.getByTestId("execute-generation"))
    const existing = await screen.findByTestId("error-coach-existing", undefined, { timeout: 5000 })
    expect(existing).toHaveTextContent("View existing")
    fireEvent.click(existing)
    expect(navigateMock).toHaveBeenCalledWith("/ordinary-life/commitments/dup-1")
  })

  it("navigates to the proposals module from the quick-create action", async () => {
    renderModal()
    const quickCreate = await screen.findByTestId("quick-create-source")
    fireEvent.click(quickCreate)
    expect(navigateMock).toHaveBeenCalledWith("/ordinary-life/proposals")
  })

  it("offers the manual form when the Manual source type is chosen", async () => {
    const onOpenManual = vi.fn()
    renderModal({ onOpenManual })
    fireEvent.change(screen.getByLabelText(/Source type/), { target: { value: "MANUAL" } })
    const openManual = await screen.findByTestId("open-manual-form")
    expect(openManual).toBeInTheDocument()
    fireEvent.click(openManual)
    expect(onOpenManual).toHaveBeenCalled()
  })
})