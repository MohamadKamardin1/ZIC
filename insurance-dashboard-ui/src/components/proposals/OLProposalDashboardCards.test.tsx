import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { OLProposalDashboardCards } from "./OLProposalDashboardCards"

const { navigateMock, kpisMock, hasPermissionMock } = vi.hoisted(() => ({
  navigateMock: vi.fn(),
  kpisMock: vi.fn(),
  hasPermissionMock: vi.fn(),
}))

vi.mock("react-router-dom", () => ({ useNavigate: () => navigateMock }))

vi.mock("../../lib/proposalsHooks", () => ({
  useProposalDashboardKpis: kpisMock,
}))

vi.mock("../../lib/access", () => ({
  useAccess: () => ({ hasPermission: hasPermissionMock, isSuperAdmin: false }),
}))

beforeEach(() => {
  navigateMock.mockReset()
  kpisMock.mockReset()
  hasPermissionMock.mockReset()
  hasPermissionMock.mockReturnValue(true)
  kpisMock.mockReturnValue({
    data: {
      awaitingFirstPremium: 9,
      awaitingFirstPremiumAmount: 45000,
      expiringIn7Days: 3,
      pendingUnderwriting: 7,
    },
    isLoading: false,
  })
})

describe("OLProposalDashboardCards", () => {
  it("renders awaiting first premium count with amount and deep links to filtered lists", async () => {
    render(<OLProposalDashboardCards />)

    expect(screen.getByTestId("card-value-awaiting_first_premium")).toHaveTextContent("9")
    expect(screen.getByTestId("proposal-card-awaiting_first_premium")).toHaveTextContent("TZS 45,000")
    expect(screen.getByTestId("card-value-expiring_7_days")).toHaveTextContent("3")
    expect(screen.getByTestId("card-value-pending_underwriting")).toHaveTextContent("7")

    fireEvent.click(screen.getByTestId("card-link-awaiting_first_premium"))
    await waitFor(() =>
      expect(navigateMock).toHaveBeenCalledWith("/ordinary-life/proposals?preset=awaiting_first_premium"),
    )

    fireEvent.click(screen.getByTestId("card-link-expiring_7_days"))
    await waitFor(() =>
      expect(navigateMock).toHaveBeenCalledWith("/ordinary-life/proposals?preset=expiring_7_days"),
    )

    fireEvent.click(screen.getByTestId("card-link-pending_underwriting"))
    await waitFor(() =>
      expect(navigateMock).toHaveBeenCalledWith("/ordinary-life/proposals?preset=pending_underwriting"),
    )
  })

  it("is hidden for users without ol_proposals.view", () => {
    hasPermissionMock.mockReturnValue(false)
    const { container } = render(<OLProposalDashboardCards />)
    expect(container).toBeEmptyDOMElement()
  })
})
