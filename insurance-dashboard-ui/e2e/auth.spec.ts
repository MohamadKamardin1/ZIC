import { expect, test } from "@playwright/test"
import { mockAccessApi, superuser } from "./fixtures"

test("login and role-aware Ordinary Life navigation", async ({ page }) => {
  await page.route("**/api/v1/auth/login/**", async (route) => {
    await route.fulfill({ json: { data: { accessToken: "login-access-token", refreshToken: "login-refresh-token", user: superuser } } })
  })
  await mockAccessApi(page)

  await page.goto("/login")
  await page.getByPlaceholder("Email").fill("superadmin@zic.test")
  await page.getByPlaceholder("Password").fill("password")
  await page.getByRole("button", { name: "Login" }).click()

  await expect(page).toHaveURL(/\/$/)
  await expect(page.getByText("Ordinary Life", { exact: true })).toBeVisible()
  await expect(page.getByRole("button", { name: "Quotations" }).first()).toBeVisible()
  await expect(page.getByText("Ordinary Life Parameters", { exact: true })).toBeVisible()
})
