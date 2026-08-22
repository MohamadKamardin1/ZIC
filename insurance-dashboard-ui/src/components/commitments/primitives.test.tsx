import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"
import { CommitmentStatusBadge, commitmentStatusMeta, commitmentStatusTone } from "./CommitmentStatusBadge"
import { DueDateWarning, dueDateWarning } from "./DueDateWarning"

const TODAY = new Date(2026, 8, 10) // 2026-09-10

describe("commitmentStatusTone / commitmentStatusMeta", () => {
  it("maps terminal, pending, and lifecycle status families to tones", () => {
    expect(commitmentStatusTone("COMPLETED")).toBe("success")
    expect(commitmentStatusTone("paid")).toBe("success")
    expect(commitmentStatusTone("CANCELLED")).toBe("danger")
    expect(commitmentStatusTone("OVERDUE")).toBe("danger")
    expect(commitmentStatusTone("PARTIALLY_PAID")).toBe("warning")
    expect(commitmentStatusTone("SUSPENDED")).toBe("warning")
    expect(commitmentStatusTone("UNDERWRITING_REVIEW")).toBe("info")
    expect(commitmentStatusTone("UNKNOWN_THING")).toBe("neutral")
  })

  it("prefers parameter-driven config when provided", () => {
    const config = [{ code: "PENDING", name: "Due for payment", tone: "info" as const }]
    const meta = commitmentStatusMeta("PENDING", config)
    expect(meta.label).toBe("Due for payment")
    expect(meta.tone).toBe("info")
  })
})

describe("CommitmentStatusBadge", () => {
  it("renders the human label, never the UUID", () => {
    render(<CommitmentStatusBadge value="COMPLETED" />)
    expect(screen.getByRole("status")).toHaveTextContent("Completed")
  })
})

describe("dueDateWarning", () => {
  it("returns on-time before the due date", () => {
    const result = dueDateWarning("2026-09-20", "2026-10-01", "2026-11-01", TODAY)
    expect(result.level).toBe("on-time")
    expect(result.tone).toBe("neutral")
    expect(result.label).toBe("On time")
  })

  it("marks in-grace (amber) between due and grace date", () => {
    const result = dueDateWarning("2026-09-05", "2026-10-01", "2026-11-01", TODAY)
    expect(result.level).toBe("in-grace")
    expect(result.tone).toBe("warning")
    expect(result.label).toBe("In grace")
  })

  it("marks overdue (red) after grace and before lapse", () => {
    const result = dueDateWarning("2026-08-01", "2026-08-25", "2026-11-01", TODAY)
    expect(result.level).toBe("overdue")
    expect(result.tone).toBe("danger")
    expect(result.label).toBe("Overdue")
  })

  it("marks lapsed (red) after the lapse date", () => {
    const result = dueDateWarning("2026-08-01", "2026-08-25", "2026-09-01", TODAY)
    expect(result.level).toBe("lapsed")
    expect(result.tone).toBe("danger")
    expect(result.label).toBe("Lapsed")
  })
})

describe("DueDateWarning component", () => {
  it("renders level label and detail", () => {
    render(<DueDateWarning dueDate="2026-09-05" graceDate="2026-10-01" lapseDate="2026-11-01" today={TODAY} />)
    expect(screen.getByText("In grace")).toBeInTheDocument()
    expect(screen.getByText("5 days past due")).toBeInTheDocument()
  })
})