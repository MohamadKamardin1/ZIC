import { expect, test } from "@playwright/test"
import { mockAccessApi, mockQuotationApi, seedSuperuserSession } from "./fixtures"

test.describe("OL quotation lifecycle", () => {
  test.beforeEach(async ({ page }) => {
    await seedSuperuserSession(page)
    await mockAccessApi(page)
    await mockQuotationApi(page)
  })

  test("opens print preview from generated documents", async ({ page }) => {
    await page.goto("/ordinary-life/quotations/quote-1")
    await expect(page.getByText("Q-E2E-0001")).toBeVisible()
    await page.getByRole("button", { name: "Documents" }).click()
    await page.getByRole("button", { name: "Preview" }).click()
    await expect(page.getByRole("heading", { name: "Print preview" })).toBeVisible()
    await expect(page.getByRole("dialog", { name: "Quotation print preview" }).getByText("OL_QUOTATION")).toBeVisible()
  })

  test("requires partner verification before conversion", async ({ page }) => {
    await page.goto("/ordinary-life/quotations/quote-1")
    await page.getByRole("button", { name: "Finalize quotation" }).click()
    await page.getByRole("button", { name: "Finalize", exact: true }).click()
    await expect(page.getByText("Q-E2E-0001")).toBeVisible()

    await page.getByRole("button", { name: "Convert to Proposal" }).first().click()
    await expect(page.getByText("Conversion is blocked")).toBeVisible()
    await expect(page.getByText(/Partner verification must be completed and compliant/)).toBeVisible()
  })

  test("completes partner verification and converts an eligible finalized quote", async ({ page }) => {
    await mockQuotationApi(page, { status: "FINALIZED", partner_verified: true })
    await page.goto("/ordinary-life/quotations/quote-1")
    await expect(page.getByText("Q-E2E-0001")).toBeVisible()

    await page.getByRole("button", { name: "Convert to Proposal" }).first().click()
    await expect(page.getByRole("heading", { name: "Convert to Proposal" })).toBeVisible()
    await Promise.all([
      page.waitForURL("**/ordinary-life/proposals?quotation=quote-1"),
      page.getByRole("dialog", { name: "Convert to Proposal" }).getByRole("button", { name: "Convert to Proposal", exact: true }).click(),
    ])
  })
})
