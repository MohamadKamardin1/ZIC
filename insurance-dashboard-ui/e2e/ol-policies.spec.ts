import { expect, test } from "@playwright/test"
import { mockAccessApi, mockPolicyApi, mockUnifiedDocumentApi, seedSuperuserSession } from "./fixtures"

const staffPermissions = [
  { module: "ol_policies", action: "view" },
  { module: "ol_policies", action: "create" },
  { module: "ol_policies", action: "service" },
  { module: "ol_policies", action: "endorse" },
  { module: "ol_policies", action: "cancel" },
  { module: "ol_policies", action: "print" },
]

async function openStaffPolicy(page: import("@playwright/test").Page) {
  await page.goto("/ordinary-life/policies/policy-active-1")
  await expect(page.getByText("ZIC-OL-2026-000001").first()).toBeVisible()
}

test.describe("OL policies UI release", () => {
  test.beforeEach(async ({ page }) => {
    await seedSuperuserSession(page)
    await mockAccessApi(page, ["ol_policies", "ordinary_life", "ol_parameters"], staffPermissions)
    await mockUnifiedDocumentApi(page)
    await mockPolicyApi(page)
  })

  test("staff issues a policy from a ready proposal and lands on policy detail", async ({ page }) => {
    await page.goto("/ordinary-life/policies/new")
    await expect(page.getByText("OLP-E2E-0001")).toBeVisible()
    await page.getByRole("button", { name: /OLP-E2E-0001/ }).click()
    await page.getByRole("button", { name: "Next", exact: true }).click()
    await page.getByRole("button", { name: "Issue Policy", exact: true }).click()
    await expect(page).toHaveURL(/\/ordinary-life\/policies\/policy-active-1$/)
    await expect(page.getByText("Active").first()).toBeVisible()
  })

  test("staff views detail and creates an endorsement", async ({ page }) => {
    await openStaffPolicy(page)
    await page.getByRole("button", { name: "Endorse", exact: true }).click()
    const dialog = page.getByRole("dialog", { name: "Create endorsement" })
    await dialog.getByLabel("Endorsement type").selectOption("ADDRESS_CHANGE")
    await dialog.getByLabel("Effective date").fill("2026-08-26")
    await dialog.getByLabel("Reason / description").fill("Correct the policyholder address")
    await dialog.getByRole("button", { name: "Submit endorsement" }).click()
    await expect(page.getByText("Endorsement submitted")).toBeVisible()
  })

  test("staff receives loan validation guidance and can submit a valid loan request", async ({ page }) => {
    await openStaffPolicy(page)
    await page.getByRole("button", { name: "Financials" }).click()
    await page.getByRole("button", { name: "Request Loan" }).click()
    const dialog = page.getByRole("dialog", { name: "Request policy loan" })
    await dialog.getByLabel("Loan amount").fill("0")
    await dialog.getByRole("button", { name: "Request loan", exact: true }).click()
    await expect(dialog.getByRole("alert")).toContainText("greater than zero")
    await dialog.getByLabel("Loan amount").fill("500000")
    await dialog.getByRole("button", { name: "Request loan", exact: true }).click()
    await expect(page.getByText("Loan request submitted")).toBeVisible()
  })

  test("staff surrenders a policy only after reason and strong confirmation", async ({ page }) => {
    await openStaffPolicy(page)
    await page.getByRole("button", { name: "Surrender" }).click()
    const dialog = page.getByRole("dialog", { name: "Surrender Policy" })
    await dialog.getByLabel("Reason for surrender").fill("Policyholder requested surrender")
    await dialog.getByRole("button", { name: "Confirm surrender" }).click()
    await expect(dialog.getByRole("alert")).toContainText("understand this action")
    await dialog.getByRole("checkbox").check()
    await dialog.getByRole("button", { name: "Confirm surrender" }).click()
    await expect(page.getByText("Surrender requested")).toBeVisible()
    await expect(page.getByText(/Surrender Pending/)).toBeVisible()
  })

  test("staff previews a policy contract through the authenticated PDF pipeline", async ({ page }) => {
    await openStaffPolicy(page)
    await page.getByRole("button", { name: "Print Contract" }).click()
    await expect(page.getByRole("dialog", { name: "Print preview — policy contract" })).toBeVisible()
    await expect(page.getByTestId("policy-print-preview-frame")).toHaveAttribute("src", /^blob:/)
    await expect(page.getByTestId("policy-print-metadata")).toContainText("Template Policy Contract v2")
  })

  test("partner policy portal is scoped and read-only", async ({ page }) => {
    await page.goto("/portal/policies")
    await expect(page.getByRole("heading", { name: "My Policies" })).toBeVisible()
    await expect(page.getByText("Contact agent for changes.")).toBeVisible()
    await expect(page.getByTestId("portal-policies-table")).toBeVisible()
    await expect(page.getByRole("button", { name: "Endorse", exact: true })).toHaveCount(0)
    await expect(page.getByRole("button", { name: "Loan", exact: true })).toHaveCount(0)
    await expect(page.getByRole("button", { name: "Surrender", exact: true })).toHaveCount(0)
    await expect(page.getByRole("button", { name: "Cancel Policy", exact: true })).toHaveCount(0)
    await page.getByTestId("portal-policy-row-policy-active-1").click()
    await expect(page).toHaveURL(/\/portal\/policies\/policy-active-1$/)
    await expect(page.getByTestId("portal-policy-overview")).toBeVisible()
    await expect(page.getByTestId("portal-policy-members")).toBeVisible()
    await expect(page.getByTestId("portal-policy-documents")).toBeVisible()
    await expect(page.getByRole("button", { name: "Endorse", exact: true })).toHaveCount(0)
    await expect(page.getByRole("button", { name: "Loan", exact: true })).toHaveCount(0)
    await expect(page.getByRole("button", { name: "Surrender", exact: true })).toHaveCount(0)
    await expect(page.getByRole("button", { name: "Cancel Policy", exact: true })).toHaveCount(0)
  })
})
