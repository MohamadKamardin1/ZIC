import { fireEvent, render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"
import { OverdueProcessingButton } from "./OverdueProcessingButton"

describe("OverdueProcessingButton", () => {
  it("is hidden without the processing permission", () => {
    const { container } = render(<OverdueProcessingButton hasPermission={false} onRun={vi.fn()} />)
    expect(container.firstChild).toBeNull()
  })

  it("renders and triggers when the permission exists", () => {
    const onRun = vi.fn()
    render(<OverdueProcessingButton hasPermission onRun={onRun} />)
    const button = screen.getByRole("button", { name: "Run Overdue Processing" })
    fireEvent.click(button)
    expect(onRun).toHaveBeenCalled()
  })
})