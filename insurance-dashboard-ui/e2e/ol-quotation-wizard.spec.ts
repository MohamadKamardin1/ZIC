import { expect, test } from "@playwright/test"
import { mockAccessApi, mockQuotationApi, seedSuperuserSession } from "./fixtures"

test("full OL quotation wizard reaches finalize review", async ({ page }) => {
  await seedSuperuserSession(page)
  await mockAccessApi(page)
  await mockQuotationApi(page)

  await page.goto("/ordinary-life/quotations/new")
  await expect(page.getByRole("heading", { name: "Personal Details" })).toBeVisible()

  await page.getByLabel(/Quote Name/).fill("E2E Family Protection")
  await page.getByLabel(/Quote Date/).fill("2026-08-19")
  await page.getByLabel(/Identity Type/).selectOption("NIN")
  await page.getByLabel(/Identity Number/).fill("NIN-E2E-001")
  await page.getByLabel(/Date of Birth/).fill("1990-01-01")
  await page.getByLabel(/Gender/).selectOption("MALE")
  await page.getByLabel(/Smoker/).selectOption("NON_SMOKER")
  await page.getByLabel(/Address/).fill("Kinondoni")
  await page.getByRole("button", { name: /Location/ }).click()
  await page.getByRole("option", { name: "Dar es Salaam" }).click()
  await page.getByRole("button", { name: /Agent/ }).click()
  await page.getByRole("option", { name: "E2E Agent" }).click()
  await page.getByRole("button", { name: "Next" }).click()

  await expect(page.getByRole("button", { name: "Plan & Sub-Products" })).toHaveAttribute("aria-current", "step")
  await page.getByRole("button", { name: /TERM-20/ }).click()
  await page.getByRole("button", { name: "Next" }).click()
  await expect(page.getByRole("button", { name: "Member Coverage" })).toHaveAttribute("aria-current", "step")

  await page.getByRole("button", { name: "Installments", exact: true }).click()
  await expect(page.getByRole("heading", { name: "Installments" })).toBeVisible()
  await page.getByRole("button", { name: "Configure" }).click()
  await expect(page.getByRole("heading", { name: "Configure Installments" })).toBeVisible()
  await page.getByLabel("Installment 1 rate").fill("100")
  await page.getByRole("button", { name: "Save configuration" }).click()
  await expect(page.getByRole("heading", { name: "Configure Installments" })).toBeHidden()

  await page.getByRole("button", { name: "Investment Funds", exact: true }).click()
  await page.getByRole("button", { name: "Riders & Benefits", exact: true }).click()
  await page.getByRole("button", { name: "Financial Details", exact: true }).click()
  await expect(page.getByRole("heading", { name: "Financial Details" })).toBeVisible()
  await page.getByRole("button", { name: "Review & Finalize" }).click()
  await expect(page.getByRole("heading", { name: "Review & Finalize" })).toBeVisible()
})
