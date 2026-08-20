import { expect, test, type Page } from "@playwright/test"
import { mockAccessApi, mockQuotationApi, quotation, seedSuperuserSession } from "./fixtures"

const UUID_RE = /\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b/i

async function expectNoVisibleUuid(page: Page) {
  await expect(page.locator("body")).not.toContainText(UUID_RE)
}

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

  test("never renders UUIDs on quotation list or detail pages", async ({ page }) => {
    const uuid = "550e8400-e29b-41d4-a716-446655440000"
    await mockQuotationApi(page, {
      ...quotation,
      id: uuid,
      agent_id: uuid,
      agent_display: "E2E Agent",
      partner_id: uuid,
      partner_display: "E2E Partner",
      branch_id: uuid,
      branch_display: "Dar es Salaam Branch",
      currency_id: uuid,
      currency_display: "TZS — Tanzanian Shilling",
      plan_configurations: [{ ...quotation.plan_configurations[0], id: uuid, plan_id: uuid, plan_display: "Twenty Year Term", product_id: uuid, product_display: "ZIC Term Assurance" }],
    } as Partial<typeof quotation>)

    await page.goto("/ordinary-life/quotations")
    await expect(page.getByText("Q-E2E-0001")).toBeVisible()
    await expectNoVisibleUuid(page)

    await page.goto("/ordinary-life/quotations/quote-1")
    await expect(page.getByText("Q-E2E-0001")).toBeVisible()
    await expectNoVisibleUuid(page)
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
