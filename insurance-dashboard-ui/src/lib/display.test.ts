import { describe, expect, it } from "vitest"
import { renderFk, sanitizeForDisplay } from "./display"

describe("UUID-safe display helpers", () => {
  it("prefers a human-readable backend display field over the raw relation value", () => {
    expect(renderFk("4c3f6a6b-9c2b-4ea4-bd9b-2c1f0e9c3a77", "Dar es Salaam")).toBe("Dar es Salaam")
  })

  it("never returns a UUID when no display label is available", () => {
    expect(renderFk("4c3f6a6b-9c2b-4ea4-bd9b-2c1f0e9c3a77")).toBe("—")
  })

  it("uses nested human-readable labels for relation objects", () => {
    expect(renderFk({ id: "4c3f6a6b-9c2b-4ea4-bd9b-2c1f0e9c3a77", name: "ZIC Agent" })).toBe("ZIC Agent")
  })

  it("scrubs UUIDs embedded in visible summaries and snapshots", () => {
    const safe = sanitizeForDisplay({ agent: "ZIC Agent", raw: "Agent 4c3f6a6b-9c2b-4ea4-bd9b-2c1f0e9c3a77" })
    expect(safe).toEqual({ agent: "ZIC Agent", raw: "[identifier hidden]" })
  })
})
