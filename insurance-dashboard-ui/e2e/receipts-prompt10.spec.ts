import { expect, test, type Page } from "@playwright/test"
import { mockAccessApi, seedSuperuserSession } from "./fixtures"

const UUID_RE = /\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b/i

const receipt = {
  id: "receipt-p10-1",
  receipt_number: "RCT-P10-0001",
  receipt_date: "2026-08-25",
  payer_display: "Zanzibar Trading Co.",
  branch_display: "Zanzibar Main Branch",
  payment_mode_display: "Mobile Money",
  payment_mode: "MOBILE_MONEY",
  currency_display: "TZS — Tanzanian Shilling",
  currency: "TZS",
  receipt_amount: "150000.00",
  allocated_amount: "0.00",
  unallocated_amount: "150000.00",
  source_module: "OL_PROPOSAL",
  created_by_display: "ZIC Superadmin",
  posted_by_display: null,
  status: "DRAFT",
  allowed_actions: ["view", "edit", "post", "allocate", "reverse", "cancel", "print"],
}

async function mockReceiptListApi(page: Page, options: { failList?: boolean } = {}) {
  const requests: string[] = []
  await page.route("**/api/v1/front-office/receipts/**", async (route) => {
    const url = new URL(route.request().url())
    const path = url.pathname
    requests.push(url.toString())
    if (options.failList && path.endsWith("/receipts/")) {
      await route.fulfill({
        status: 422,
        json: {
          error: {
            code: "RECEIPT_PARAMETER_MISSING",
            message: "Receipt parameters are not configured.",
            resolutionSteps: ["Configure the missing receipt parameters."],
            deepLink: "/ordinary-life/parameters/dropdowns",
          },
        },
      })
      return
    }
    if (path.endsWith("/kpis/")) {
      await route.fulfill({ json: { data: { received_today: "150000.00", allocated_in_period: "0.00", unallocated_amount: "150000.00", receipt_count: 1, reversed_amount: "0.00" } } })
      return
    }
    if (path.endsWith("/options/branches/")) {
      await route.fulfill({ json: { data: { count: 1, results: [{ value: "branch-p10", label: "Zanzibar Main Branch" }] } } })
      return
    }
    if (path.endsWith("/options/currencies/")) {
      await route.fulfill({ json: { data: { count: 1, results: [{ value: "TZS", label: "TZS — Tanzanian Shilling" }] } } })
      return
    }
    if (path.endsWith("/options/payment-modes/")) {
      await route.fulfill({ json: { data: { count: 1, results: [{ value: "MOBILE_MONEY", label: "Mobile Money" }] } } })
      return
    }
    if (path.endsWith("/options/statuses/")) {
      await route.fulfill({ json: { data: { count: 1, results: [{ value: "DRAFT", label: "Draft" }] } } })
      return
    }
    if (path.endsWith("/receipts/")) {
      await route.fulfill({ json: { data: { count: 1, results: [receipt], next: null, previous: null, page: 1, page_size: 20 } } })
      return
    }
    await route.fulfill({ json: { data: receipt } })
  })
  return requests
}

test.describe("Front Office receipts Prompt 10 release regressions", () => {
  test.beforeEach(async ({ page }) => {
    await seedSuperuserSession(page)
    await mockAccessApi(page, ["front_office", "front_office_receipts"])
  })

  test("keeps labels, UUID safety, keyboard quick filters, focus states, and dark-theme tokens intact", async ({ page }) => {
    const requests = await mockReceiptListApi(page)
    await page.emulateMedia({ colorScheme: "dark" })
    await page.goto("/front-office/receipts")

    await expect(page.getByRole("heading", { name: "Receipts Work Queue" })).toBeVisible()
    await expect(page.getByText("RCT-P10-0001")).toBeVisible()
    await expect(page.getByText("Zanzibar Trading Co.")).toBeVisible()
    await expect(page.locator("body")).not.toContainText(UUID_RE)

    const quickFilter = page.getByRole("button", { name: "Today" })
    await quickFilter.focus()
    await expect(quickFilter).toBeFocused()
    await page.keyboard.press("Enter")
    await expect(quickFilter).toHaveAttribute("aria-pressed", "true")
    await expect.poll(() => requests.some((url) => new URL(url).searchParams.get("today") === "true")).toBe(true)

    const bodyBackground = await page.locator("body").evaluate((element) => getComputedStyle(element).backgroundColor)
    expect(bodyBackground).not.toBe("")
  })

  test("teaches a structured parameter error with an actionable deep link", async ({ page }) => {
    await mockReceiptListApi(page, { failList: true })
    await page.goto("/front-office/receipts")
    await expect(page.getByRole("alert")).toContainText("Receipt parameters are not configured.")
    await expect(page.getByRole("link", { name: "Open resolution page" })).toHaveAttribute("href", "/ordinary-life/parameters/dropdowns")
  })
})

test.describe("Front Office receipts real merged-backend run", () => {
  test.skip(!process.env.E2E_REAL_BACKEND, "Opt in with E2E_REAL_BACKEND=1; this describe never installs page-route mocks.")

  test("runs against VITE_USE_MOCKS=false and proves the legacy receipt contract is reachable", async ({ page }) => {
    test.skip(!process.env.E2E_REAL_BACKEND_EMAIL || !process.env.E2E_REAL_BACKEND_PASSWORD, "Provide E2E_REAL_BACKEND_EMAIL and E2E_REAL_BACKEND_PASSWORD for the seeded backend.")
    await page.goto("/login")
    const login = await page.evaluate(async ({ email, password }) => {
      const response = await fetch("/api/v1/auth/login/", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ username: email, password }) })
      return { ok: response.ok, payload: await response.json() }
    }, { email: process.env.E2E_REAL_BACKEND_EMAIL ?? "", password: process.env.E2E_REAL_BACKEND_PASSWORD ?? "" })
    expect(login.ok).toBe(true)
    const loginData = login.payload.data ?? login.payload
    await page.evaluate((data) => {
      const payload = data as { accessToken?: string; refreshToken?: string; user?: unknown }
      localStorage.setItem("aims_access_token", payload.accessToken ?? "")
      localStorage.setItem("aims_refresh_token", payload.refreshToken ?? "")
      localStorage.setItem("aims_user", JSON.stringify(payload.user ?? {}))
      sessionStorage.setItem("aims_access_token", payload.accessToken ?? "")
      sessionStorage.setItem("aims_refresh_token", payload.refreshToken ?? "")
      sessionStorage.setItem("aims_user", JSON.stringify(payload.user ?? {}))
    }, loginData)
    await page.reload()
    await page.goto("/front-office/receipts")
    await expect(page.getByRole("heading", { name: "Receipts Work Queue" })).toBeVisible()
    await expect(page.locator("body")).not.toContainText(UUID_RE)
    await expect(page.getByText(/No receipts match|Receipts API|Receipt number/i).first()).toBeVisible()
  })
})

