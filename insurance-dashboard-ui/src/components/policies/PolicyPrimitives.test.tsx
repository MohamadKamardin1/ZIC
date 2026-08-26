import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"
import { LifeStageBadge, MoneyCell, PolicyHeader, PolicyStatusBadge } from "./PolicyPrimitives"

const policyHeader = {
  policyNumber: "ZIC-OL-2026-000001",
  policyholderDisplay: "P-000018 — Amani Salum",
  policyholderIdentity: "National ID ending 4821",
  productPlanDisplay: "OL_EDU_GROWTH — Elimu Bora Growth Plan",
  sumAssured: "25000000.00",
  premiumAmount: "120000.00",
  premiumFrequency: "MONTHLY",
  currency: "TZS",
  status: "ACTIVE",
  riskCommencementDate: "2026-01-15",
  maturityDate: "2041-01-15",
}

describe("PolicyStatusBadge", () => {
  it.each([
    ["ACTIVE", "Active", "badge-success"],
    ["LAPSED", "Lapsed", "badge-danger"],
    ["MATURED", "Matured", "badge-success"],
    ["SURRENDERED", "Surrendered", "badge-neutral"],
  ])("renders %s with the expected tone", (status, label, tone) => {
    render(<PolicyStatusBadge status={status} />)
    expect(screen.getByRole("status")).toHaveTextContent(label)
    expect(screen.getByRole("status").className).toContain(tone)
  })

  it("uses parameter metadata when a status catalog supplies a tone", () => {
    render(<PolicyStatusBadge status="CUSTOM_ACTIVE" statusOptions={[{ value: "CUSTOM_ACTIVE", label: "In force", meta: { badge_type: "POSITIVE" } }]} />)
    expect(screen.getByRole("status")).toHaveTextContent("In force")
    expect(screen.getByRole("status").className).toContain("badge-success")
  })
})

describe("LifeStageBadge", () => {
  it("shows the explicit grace stage", () => {
    render(<LifeStageBadge stage="GRACE" />)
    expect(screen.getByRole("status")).toHaveTextContent("Grace period")
    expect(screen.getByRole("status").className).toContain("badge-warning")
  })

  it("infers paid-up from policy status", () => {
    render(<LifeStageBadge status="PAID_UP" />)
    expect(screen.getByRole("status")).toHaveTextContent("Paid-up")
  })
})

describe("MoneyCell", () => {
  it("formats a policy amount with its currency", () => {
    render(<MoneyCell value="25000000.00" currency="TZS" />)
    expect(screen.getByText(/25,000,000\.00/)).toBeInTheDocument()
  })
})

describe("PolicyHeader", () => {
  it("renders contract facts and never needs a raw foreign-key value", () => {
    render(<PolicyHeader data={policyHeader} />)
    expect(screen.getByRole("heading", { name: "ZIC-OL-2026-000001" })).toBeInTheDocument()
    expect(screen.getByText("P-000018 — Amani Salum · National ID ending 4821")).toBeInTheDocument()
    expect(screen.getByText("OL_EDU_GROWTH — Elimu Bora Growth Plan")).toBeInTheDocument()
    expect(screen.getByText("Issue date")).toBeInTheDocument()
    expect(screen.getByText("15 Jan 2026")).toBeInTheDocument()
    expect(screen.getByRole("status")).toHaveTextContent("Active")
  })
})
