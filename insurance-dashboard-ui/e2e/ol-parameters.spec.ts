import { expect, test, type Page } from "@playwright/test"
import { mockAccessApi, mockParameterApi, seedSuperuserSession } from "./fixtures"

const UUID_RE = /\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b/i

async function expectNoVisibleUuid(page: Page) {
  await expect(page.locator("body")).not.toContainText(UUID_RE)
}

test("OL default parameter setup supports create and refresh", async ({ page }) => {
  await seedSuperuserSession(page)
  await mockAccessApi(page, ["ol_parameters", "ordinary_life"])
  await mockParameterApi(page)

  await page.goto("/ordinary-life/parameters/default-setup")
  await expect(page.getByRole("heading", { name: "Default System Parameters" })).toBeVisible()
  await page.getByRole("button", { name: "New setup" }).click()
  await expect(page.getByRole("heading", { name: "Create Default System Parameters" })).toBeVisible()
  await page.getByLabel("Code").fill("E2E_PARAMETER")
  await page.getByLabel("Name").fill("E2E Parameter")
  await page.getByLabel("Parameter key").fill("E2E_PARAMETER")
  await page.getByLabel("Category").fill("E2E")
  await page.getByLabel("Typed value").fill("10")
  await page.getByRole("button", { name: "Create setup" }).click()

  await expect(page.getByRole("heading", { name: "Create Default System Parameters" })).toBeHidden()
  await expectNoVisibleUuid(page)
})
