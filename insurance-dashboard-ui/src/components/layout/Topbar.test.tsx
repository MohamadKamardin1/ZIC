import { fireEvent, render, screen, waitFor, within } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { Topbar } from "./Topbar"

const { listDashboardMock, listOverdueMock, listProposalNoticeMock, listReceiptNoticeMock, markReadMock, markAllMock, searchMock, navigateMock } = vi.hoisted(() => ({
  listDashboardMock: vi.fn(),
  listOverdueMock: vi.fn(),
  listProposalNoticeMock: vi.fn(),
  listReceiptNoticeMock: vi.fn(),
  markReadMock: vi.fn(),
  markAllMock: vi.fn(),
  searchMock: vi.fn(),
  navigateMock: vi.fn(),
}))

vi.mock("react-router-dom", async (importOriginal) => {
  const actual = await importOriginal<typeof import("react-router-dom")>()
  return { ...actual, useNavigate: () => navigateMock }
})

vi.mock("../../lib/api", () => ({
  listDashboardNotifications: listDashboardMock,
  listCommitmentOverdueNotifications: listOverdueMock,
  listProposalNotifications: listProposalNoticeMock,
  listReceiptNotifications: listReceiptNoticeMock,
  markDashboardNotificationRead: markReadMock,
  markAllDashboardNotificationsRead: markAllMock,
  searchDashboard: searchMock,
}))

vi.mock("../../lib/auth", () => ({ useAuth: () => ({ user: { fullName: "Test User", username: "tester" }, signOut: vi.fn() }) }))

vi.mock("../../theme/ThemeProvider", () => ({ useTheme: () => ({ theme: "light", setTheme: vi.fn() }) }))

vi.mock("../ai/AIContext", () => ({ useAI: () => ({ setPanelOpen: vi.fn() }) }))

vi.mock("../../lib/language", () => ({ useLanguage: () => ({ language: "en", setLanguage: vi.fn(), t: (key: string) => key, languageOptions: [] }) }))

const DASH_NOTICE = {
  id: 1, kind: "system", title: "Partner approved", message: "Approved", status: "UNREAD", route: "/partners", entityType: "Partner", entityId: "1", isRead: false, createdAt: new Date().toISOString(),
}

const OVERDUE_NOTICE = {
  id: "evt-9", kind: "ol-commitments", title: "Commitment OLC-2026-00009 is overdue", message: "Past its grace date.", status: "UNREAD", route: "/ordinary-life/commitments/9", entityType: "OLCommitment", entityId: "evt-9", isRead: false, createdAt: new Date().toISOString(), deepLink: "/ordinary-life/commitments/9",
}

function renderTopbar() {
  return render(
    <MemoryRouter>
      <Topbar onToggleSidebar={vi.fn()} />
    </MemoryRouter>,
  )
}

beforeEach(() => {
  listDashboardMock.mockReset()
  listOverdueMock.mockReset()
  listProposalNoticeMock.mockReset()
  listReceiptNoticeMock.mockReset()
  markReadMock.mockReset()
  markAllMock.mockReset()
  searchMock.mockReset()
  navigateMock.mockReset()
  listDashboardMock.mockResolvedValue([DASH_NOTICE])
  listOverdueMock.mockResolvedValue([OVERDUE_NOTICE])
  listProposalNoticeMock.mockResolvedValue([])
  listReceiptNoticeMock.mockResolvedValue([])
  searchMock.mockResolvedValue([])
})

describe("Topbar bell notification center integration", () => {
  it("surfaces CommitmentOverdue notifications with a deep link that navigates", async () => {
    renderTopbar()

    const bell = await screen.findByRole("button", { name: "notifications" })
    fireEvent.click(bell)

    const item = await screen.findByText("Commitment OLC-2026-00009 is overdue")
    expect(item).toBeInTheDocument()

    fireEvent.click(item)
    await waitFor(() => expect(navigateMock).toHaveBeenCalledWith("/ordinary-life/commitments/9"))
  })

  it("surfaces receipt lifecycle notifications with deep links that navigate", async () => {
    listReceiptNoticeMock.mockResolvedValue([
      {
        id: "receipt-event-1",
        kind: "front-office-receipts",
        title: "Receipt RCT-2026-000001 posted",
        message: "The receipt is ready for allocation.",
        status: "UNREAD",
        route: "/front-office/receipts/receipt-1",
        entityType: "Receipt",
        entityId: "receipt-1",
        isRead: false,
        createdAt: new Date().toISOString(),
        deepLink: "/front-office/receipts/receipt-1",
      },
    ])

    renderTopbar()

    fireEvent.click(await screen.findByRole("button", { name: "notifications" }))

    const item = await screen.findByText("Receipt RCT-2026-000001 posted")
    fireEvent.click(item)
    await waitFor(() => expect(navigateMock).toHaveBeenCalledWith("/front-office/receipts/receipt-1"))
  })

  it("surfaces proposal lifecycle notifications with deep links that navigate", async () => {
    listProposalNoticeMock.mockResolvedValue([
      {
        id: "prop-evt-7",
        kind: "ol-proposals",
        title: "Proposal OLP-2026-000042 converted to policy",
        message: "The proposal was converted to a policy; the first premium is fully posted.",
        status: "UNREAD",
        route: "/ordinary-life/proposals/prop-uuid-0001",
        entityType: "OLProposal",
        entityId: "prop-evt-7",
        isRead: false,
        createdAt: new Date().toISOString(),
        deepLink: "/ordinary-life/proposals/prop-uuid-0001",
      },
    ])

    renderTopbar()

    fireEvent.click(await screen.findByRole("button", { name: "notifications" }))

    const item = await screen.findByText("Proposal OLP-2026-000042 converted to policy")
    fireEvent.click(item)
    await waitFor(() => expect(navigateMock).toHaveBeenCalledWith("/ordinary-life/proposals/prop-uuid-0001"))
  })
})