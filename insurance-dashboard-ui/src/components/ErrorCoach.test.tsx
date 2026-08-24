import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"
import { ErrorCoach } from "./ErrorCoach"

describe("shared ErrorCoach", () => {
  it("renders structured resolution steps and a deep-link action", () => {
    render(<ErrorCoach title="Receipt needs attention" message="The payment reference is required." resolutionSteps={["Choose a payment mode.", "Enter the provider reference."]} loginUrl="/front-office/parameters" actionLabel="Open payment parameters" />)
    expect(screen.getByRole("alert")).toHaveTextContent("The payment reference is required.")
    expect(screen.getByText("Choose a payment mode.")).toBeInTheDocument()
    expect(screen.getByRole("link", { name: "Open payment parameters" })).toHaveAttribute("href", "/front-office/parameters")
  })
})
