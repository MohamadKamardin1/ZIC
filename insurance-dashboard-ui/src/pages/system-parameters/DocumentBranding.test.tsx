import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { request } from "../../lib/apiClient"
import { ToastProvider } from "../../components/ui/Toast"
import DocumentBranding from "./DocumentBranding"

vi.mock("../../lib/apiClient", () => ({
  request: vi.fn(),
  ApiClientError: class ApiClientError extends Error {},
}))

describe("DocumentBranding", () => {
  const current = {
    code: "COMPANY_BRANDING",
    version: 2,
    company_name: "Zanzibar Insurance Corporation",
    address: "Bima House",
    phone: "+255 659 072 500",
    email: "info@zic.co.tz",
    registration_number: "ZIC-001",
    footer_legal_text: "System generated",
    accent_colors: { primary: "#183a91", accent: "#d94754", table_header: "#edf1f4" },
    is_active: true,
    history: [],
  }

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(request).mockResolvedValue(current)
  })

  it("loads the active branding version and submits a multipart version update", async () => {
    render(<ToastProvider><DocumentBranding /></ToastProvider>)
    expect(await screen.findByText("Document Branding")).toBeInTheDocument()
    expect(screen.getByText("v2")).toBeInTheDocument()
    const name = screen.getByLabelText(/Company name/)
    fireEvent.change(name, { target: { value: "ZIC New Legal Name" } })
    vi.mocked(request).mockResolvedValueOnce({ ...current, version: 3, company_name: "ZIC New Legal Name" })
    fireEvent.click(screen.getByRole("button", { name: "Create branding version" }))
    await waitFor(() => expect(request).toHaveBeenCalledWith("/api/v1/documents/branding/", expect.objectContaining({ method: "POST", body: expect.any(FormData) })))
    const call = vi.mocked(request).mock.calls.find(([, options]) => options?.method === "POST")
    const body = call?.[1]?.body as FormData
    expect(body.get("company_name")).toBe("ZIC New Legal Name")
    expect(body.get("accent_colors")).toContain("primary")
  })
})
