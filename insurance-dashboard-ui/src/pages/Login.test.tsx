import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import { describe, expect, it, vi } from "vitest"
import Login from "./Login"

const signIn = vi.fn()

vi.mock("../lib/auth", () => ({
  useAuth: () => ({
    signIn,
    complete2FA: vi.fn(),
    cancel2FA: vi.fn(),
    requires2FA: false,
    pendingEmail: null,
  }),
}))

describe("Login", () => {
  it("validates credentials and redirects after successful sign-in", async () => {
    signIn.mockResolvedValue(false)
    render(<MemoryRouter initialEntries={["/login"]}><Login /></MemoryRouter>)

    fireEvent.click(screen.getByRole("button", { name: "Login" }))
    expect(await screen.findByText("Enter a valid email address.")).toBeInTheDocument()
    expect(signIn).not.toHaveBeenCalled()

    fireEvent.change(screen.getByPlaceholderText("Email"), { target: { value: "user@example.com" } })
    fireEvent.change(screen.getByPlaceholderText("Password"), { target: { value: "secret" } })
    fireEvent.click(screen.getByRole("button", { name: "Login" }))

    await waitFor(() => expect(signIn).toHaveBeenCalledWith("user@example.com", "secret"))
  })
})
