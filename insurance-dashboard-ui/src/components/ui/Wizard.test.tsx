import { fireEvent, render, screen, waitFor, within } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"
import { FileText, UserRound } from "lucide-react"
import { Modal } from "./Overlays"
import { Wizard } from "./Wizard"

describe("Wizard and overlays", () => {
  it("blocks invalid navigation and advances after validation passes", async () => {
    const validate = vi.fn().mockReturnValue(false)
    render(<Wizard steps={[{ id: "one", label: "Personal details", icon: UserRound, content: <p>First step</p>, validate }, { id: "two", label: "Review", icon: FileText, content: <p>Second step</p>, validate: () => true }]} />)
    expect(screen.getByText("First step")).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: /next/i }))
    expect(screen.getByText("First step")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /personal details/i })).toHaveAttribute("aria-current", "step")
    validate.mockReturnValue(true)
    fireEvent.click(screen.getByRole("button", { name: /next/i }))
    await waitFor(() => expect(screen.getByText("Second step")).toBeInTheDocument())
    expect(screen.getByRole("button", { name: /review/i })).toHaveAttribute("aria-current", "step")
  })

  it("exposes accessible modal semantics and close control", () => {
    const onClose = vi.fn()
    render(<Modal open title="Confirm action" onClose={onClose}>Are you sure?</Modal>)
    expect(screen.getByRole("dialog", { name: "Confirm action" })).toHaveAttribute("aria-modal", "true")
    expect(screen.getByText("Are you sure?")).toBeInTheDocument()
    fireEvent.click(within(screen.getByRole("dialog", { name: "Confirm action" })).getAllByRole("button", { name: "Close dialog" })[1])
    expect(onClose).toHaveBeenCalledTimes(1)
  })
})
