import { fireEvent, render, screen } from "@testing-library/react"
import type { ComponentProps } from "react"
import { describe, expect, it, vi } from "vitest"
import { reasonError, ReasonField, DEFAULT_REASON_MIN_LENGTH } from "./ReasonField"

function renderField(overrides: Partial<ComponentProps<typeof ReasonField>> = {}) {
  const onChange = overrides.onChange ?? vi.fn()
  const utils = render(<ReasonField value={overrides.value ?? ""} onChange={onChange} label="Reason" {...overrides} />)
  return { ...utils, onChange: onChange as ReturnType<typeof vi.fn> }
}

describe("reasonError", () => {
  it("requires a reason", () => {
    expect(reasonError("")).toContain("required")
    expect(reasonError("   ")).toContain("required")
  })

  it("enforces the minimum length", () => {
    expect(reasonError("short")).toContain("at least 8")
  })

  it("accepts a valid reason", () => {
    expect(reasonError("Duplicate receipt collected")).toBeNull()
  })
})

describe("ReasonField", () => {
  it("shows an inline error after blurring an empty field", () => {
    renderField()
    const textarea = screen.getByLabelText(/Reason/)
    fireEvent.blur(textarea)
    expect(screen.getByRole("alert")).toHaveTextContent("A reason is required.")
  })

  it("shows a minimum-length error after blurring a short reason", () => {
    renderField({ value: "short" })
    const textarea = screen.getByLabelText(/Reason/)
    fireEvent.blur(textarea)
    expect(screen.getByRole("alert")).toHaveTextContent(`Provide at least ${DEFAULT_REASON_MIN_LENGTH} characters.`)
  })

  it("clears the error once the reason passes the minimum length", () => {
    renderField({ value: "Duplicate receipt collected" })
    const textarea = screen.getByLabelText(/Reason/)
    fireEvent.blur(textarea)
    expect(screen.queryByRole("alert")).not.toBeInTheDocument()
  })

  it("marks the textarea invalid with aria-invalid when errored", () => {
    renderField()
    const textarea = screen.getByLabelText(/Reason/)
    fireEvent.blur(textarea)
    expect(textarea).toHaveAttribute("aria-invalid", "true")
  })

  it("reveals the error via showError without needing a blur (submit attempt)", () => {
    const first = renderField({ value: "x" })
    expect(screen.queryByRole("alert")).not.toBeInTheDocument()
    first.unmount()
    renderField({ value: "x", showError: true })
    expect(screen.getByRole("alert")).toHaveTextContent("at least")
  })
})