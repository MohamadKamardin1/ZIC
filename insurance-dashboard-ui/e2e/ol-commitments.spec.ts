import { expect, test, type Page, type Route } from "@playwright/test"
import { seedSuperuserSession, mockAccessApi } from "./fixtures"

const CSV_ERROR_ROWS = "source_type,currency,due_date,premium_amount,reason\nPOLICY,TZS,2026-09-01,50000.00,Valid row\nMANUAL,bad,2026-09-15,75000.00,Invalid row\n"
const CSV_CLEAN_ROWS = "source_type,currency,due_date,premium_amount,reason\nPOLICY,TZS,2026-09-01,50000.00,Valid row\nMANUAL,TZS,2026-09-15,75000.00,Valid row two\n"

function todayOffset(days: number): string {
  const d = new Date()
  d.setDate(d.getDate() + days)
  const pad = (n: number) => String(n).padStart(2, "0")
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

const ROW_A = {
  id: "c-1",
  commitmentNumber: "OLC-2026-00001",
  sourceType: "POLICY",
  sourceReference: "POL-2026-0001",
  partnerName: "Zanzibar Trading Co.",
  productName: "Family Protection",
  planName: "Standard",
  currency: "TZS",
  premiumFrequency: "MONTHLY",
  installmentNumber: 7,
  installmentCount: 120,
  dueDate: todayOffset(5),
  premiumAmount: "100000.00",
  amountPaid: "40000.00",
  balance: "60000.00",
  status: "PARTIALLY_PAID",
  graceDate: todayOffset(35),
  lapseDate: todayOffset(50),
  allowedActions: ["view", "record_payment", "suspend", "cancel", "reschedule"],
}

const ROW_B = {
  id: "c-2",
  commitmentNumber: "OLC-2026-00002",
  sourceType: "PROPOSAL",
  sourceReference: "OLP-2026-0001",
  partnerName: "Amina Hassan",
  productName: "Investment Linked",
  planName: "Growth",
  currency: "TZS",
  premiumFrequency: "ANNUAL",
  installmentNumber: 1,
  installmentCount: 1,
  dueDate: todayOffset(-10),
  premiumAmount: "250000.00",
  amountPaid: "0.00",
  balance: "250000.00",
  status: "PENDING",
  graceDate: todayOffset(20),
  lapseDate: todayOffset(35),
  allowedActions: ["view", "record_payment", "reschedule"],
}

const DETAIL = {
  ...ROW_A,
  graceDays: 30,
  statusHistory: [
    { fromStatus: "PENDING", toStatus: "PARTIALLY_PAID", actorName: "Amina Hassan", createdAt: "2026-08-20T10:05:00Z", reason: "Cash allocation posted", sourceChannel: "API" },
  ],
  allocations: [
    { id: "a-1", receiptReference: "RCT-2026-001", amount: "40000.00", paymentMode: "CASH", currency: "TZS", exchangeRate: "1.000000", reversalOf: null, allocatedAt: "2026-08-20T10:00:00Z" },
  ],
  notificationLogs: [
    { id: "n-1", eventType: "GRACE_START", dispatchOn: todayOffset(36), notificationChannel: "SMS", recipientType: "POLICYHOLDER", recipientIdentifier: "+255700000000", status: "DISPATCHED" },
  ],
}

const KPI_PAYLOAD = { totalDue: "1000000.00", totalOutstanding: "650000.00", overdueCount: 3, collectedInPeriod: "350000.00", approvalsPending: 2 }
const OPTIONS_PAYLOAD = {
  paymentModes: ["CASH", "M-PESA"],
  currencies: ["TZS", "USD"],
  statuses: [
    { code: "PENDING", name: "Pending" },
    { code: "PARTIALLY_PAID", name: "Partially Paid" },
    { code: "COMPLETED", name: "Completed" },
    { code: "OVERDUE", name: "Overdue" },
  ],
}

const OVERPAYMENT_BODY = {
  error_code: "COMMITMENT_OVERPAYMENT",
  message: "The payment amount exceeds the outstanding balance.",
  resolution_steps: ["Adjust the amount so it is equal to or below the outstanding balance.", "If you collected more, record the surplus as a credit."],
}

async function fulfillJson(route: Route, json: unknown, status = 200) {
  await route.fulfill({ status, json: { data: json } })
}

async function fulfillError(route: Route, status: number, code: string, message: string, steps: string[], extra: Record<string, unknown> = {}) {
  await route.fulfill({
    status,
    json: {
      success: false,
      status_code: status,
      error_code: code,
      message,
      resolution_steps: steps,
      field_errors: {},
      doc_ref: "docs/OL_COMMITMENTS_USER_GUIDE.md",
      error: { code, message, details: null },
      meta: {},
      ...extra,
    },
  })
}


export async function mockCommitmentsApi(page: Page) {
  await page.route("**/api/v1/ol/options/**", async (route) => {
    const path = new URL(route.request().url()).pathname
    if (path.includes("/payment-modes/")) {
      await fulfillJson(route, { items: [{ id: "CASH", label: "Cash" }, { id: "M-PESA", label: "M-PESA" }] })
      return
    }
    if (path.includes("/currencies/")) {
      await fulfillJson(route, { items: [{ id: "TZS", label: "TZS" }, { id: "USD", label: "USD" }] })
      return
    }
    await fulfillJson(route, { count: 0, results: [] })
  })

  await page.route("**/api/v1/ol-commitments/**", async (route) => {
    const url = new URL(route.request().url())
    const path = url.pathname
    const method = route.request().method()
    let body: Record<string, unknown>
    try { body = route.request().postDataJSON() ?? {} } catch { body = {} }

    if (path.includes("/process-overdue/")) {
      await fulfillJson(route, { processed: 5, overdue: 3, notified: 4, lapse_reviews: 2 })
      return
    }
    if (path.includes("/lapse-review/")) {
      await fulfillJson(route, { results: [{ id: "c-2", commitment_number: "OLC-2026-00002", policy_reference: "OLP-2026-0001", partner_name: "Amina Hassan", due_date: todayOffset(-10), lapse_date: todayOffset(35), status: "PENDING", recommended_action: "Initiate policy lapse review" }] })
      return
    }
    if (path.includes("/notifications/overdue/")) {
      await fulfillJson(route, { results: [{ id: "evt-1", title: "Commitment OLC-2026-00002 is overdue", message: "Past its grace date.", deep_link: "/ordinary-life/commitments/c-2", created_at: new Date().toISOString() }] })
      return
    }
    if (path.includes("/imports/")) {
      if (method === "GET") await fulfillJson(route, { results: [{ id: "import-1", file_name: "commitments_e2e.csv", uploaded_by_name: "E2E Superadmin", created_at: "2026-08-20T10:00:00Z", ok_count: 2, error_count: 1, created_count: 2, status: "COMPLETED" }] })
      else if (path.endsWith("import-1/")) await fulfillJson(route, { errors: [{ row: 2, field_errors: { currency: ["Must be a three-letter code."] } }] })
      return
    }
    if (path.includes("/commitments/import/")) {
      const rows = (body.rows ?? []) as Array<Record<string, string>>
      const badRow = rows.find((row) => row.currency === "bad")
      if (domainKey(route) === "dry_run" && badRow) {
        await fulfillJson(route, { dry_run: true, imported: 1, created: 0, errors: [{ row: 2, field_errors: { currency: ["Must be a three-letter code."] } }] })
      } else if (domainKey(route) === "dry_run") {
        await fulfillJson(route, { dry_run: true, imported: rows.length, created: 0, errors: [] })
      } else {
        await fulfillJson(route, { dry_run: false, imported: rows.length, created: rows.length, errors: [] })
      }
      return
    }
    if (path.endsWith("/generate-preview/")) {
      const sourceId = String(body.sourceId ?? "")
      if (sourceId === "prop-missing") {
        await fulfillError(route, 422, "PARAMETER_MISSING", "OL Grace Period is not configured.", ["Configure the OL Grace Period row."], { deep_link: "/ordinary-life/parameters/policy-setup" })
      } else {
        await fulfillJson(route, {
          rows: [
            { installmentNumber: 1, dueDate: todayOffset(30), amount: "50000.00", currency: "TZS", graceDate: todayOffset(60), lapseDate: todayOffset(75), status: "PENDING" },
            { installmentNumber: 2, dueDate: todayOffset(60), amount: "60000.00", currency: "TZS", graceDate: todayOffset(90), lapseDate: todayOffset(105), status: "PENDING" },
          ],
        })
      }
      return
    }
    if (path.endsWith("/generate/")) {
      await fulfillJson(route, { created: 2, events: 2 })
      return
    }
    if (path.includes("/ol/options/payment-modes/")) {
      await fulfillJson(route, { items: [{ id: "CASH", label: "Cash" }, { id: "M-PESA", label: "M-PESA" }] })
      return
    }
    if (path.includes("/ol/options/currencies/")) {
      await fulfillJson(route, { items: [{ id: "TZS", label: "TZS" }, { id: "USD", label: "USD" }] })
      return
    }
    if (path.includes("/options/")) {
      if (path.includes("/options/sources/")) {
        await fulfillJson(route, { results: [{ id: "prop-1", label: "Zanzibar Trading Co.", reference: "OLP-2026-0001" }, { id: "prop-missing", label: "Param Missing", reference: "OLP-2026-0002" }] })
        return
      }
      await fulfillJson(route, OPTIONS_PAYLOAD)
      return
    }
    if (path.endsWith("/kpis/")) {
      await fulfillJson(route, KPI_PAYLOAD)
      return
    }
    if (path.endsWith("/commitments/") && method === "GET") {
      await fulfillJson(route, { count: 2, results: [ROW_A, ROW_B], next: null, previous: null })
      return
    }
    if (path.includes("/c-1/")) {
      if (path.endsWith("/record_payment/")) {
        const amount = Number(body.amount ?? 0)
        if ((amount || 0) > Number(ROW_A.balance)) {
          await fulfillError(route, 422, "COMMITMENT_OVERPAYMENT", OVERPAYMENT_BODY.message, OVERPAYMENT_BODY.resolution_steps)
        } else {
          await fulfillJson(route, { ...DETAIL, amountPaid: String(Number(ROW_A.amountPaid) + amount), balance: String(Number(ROW_A.balance) - amount), status: "COMPLETED" })
        }
        return
      }
      if (path.endsWith("/cancel/")) {
        await fulfillError(route, 422, "COMMITMENT_INVALID_TRANSITION", "This commitment cannot be cancelled from its current state.", [
          "Allowed transitions: record payment from PARTIALLY_PAID.",
          "Allowed transitions: suspend from PARTIALLY_PAID.",
          "Allowed transitions: waive from PARTIALLY_PAID.",
        ])
        return
      }
      await fulfillJson(route, DETAIL)
      return
    }
    await fulfillJson(route, { count: 0, results: [] })
  })
}

function domainKey(route: Route): "dry_run" | "commit" {
  return new URL(route.request().url()).searchParams.get("dry_run") === "true" ? "dry_run" : "commit"
}

test.beforeEach(async ({ page }) => {
  await seedSuperuserSession(page)
  await mockAccessApi(
    page,
    ["ol_commitments", "ol_proposals", "ol_policies", "ol_parameters", "system_parameters", "ordinary_life", "reports"],
    [
      { module: "ol_commitments", action: "view" },
      { module: "ol_commitments", action: "create" },
      { module: "ol_commitments", action: "generate" },
      { module: "ol_commitments", action: "record_payment" },
      { module: "ol_commitments", action: "suspend" },
      { module: "ol_commitments", action: "cancel" },
      { module: "ol_commitments", action: "reschedule" },
      { module: "ol_commitments", action: "waive" },
    ],
  )
  await mockCommitmentsApi(page)
})

test("list page shows KPIs, chips, and export", async ({ page }) => {
  await page.goto("/ordinary-life/commitments")
  await expect(page.getByRole("heading", { name: "Ordinary Life Commitments" })).toBeVisible()
  await expect(page.locator("body")).toContainText("TZS 1,000,000.00")
  await expect(page.locator("body")).toContainText("TZS 650,000.00")

  const overdueChip = page.getByRole("button", { name: "Overdue", exact: true })
  await overdueChip.click()
  await expect(overdueChip).toHaveAttribute("aria-pressed", "true")

  await page.getByRole("textbox", { name: "Search records" }).fill("Zanzibar")
  await expect(page.getByLabel("Ordinary Life commitments register").locator("tbody")).toContainText("Zanzibar Trading Co.")

  await page.getByRole("button", { name: "Export CSV" }).click()
})

test("generation wizard dry-runs then executes", async ({ page }) => {
  await page.goto("/ordinary-life/commitments")
  await page.getByRole("button", { name: "Generate Commitments" }).click()

  await page.getByLabel(/Proposal/).click()
  await page.getByRole("option", { name: /Zanzibar Trading/ }).click()
  await expect(page.getByText("Preview schedule (dry-run)")).toBeVisible({ timeout: 15000 })
  await expect(page.getByText("TZS 50,000.00")).toBeVisible({ timeout: 15000 })

  await page.getByTestId("execute-generation").click()
  await expect(page.getByText(/Commitments generated/i)).toBeVisible()
})

test("PARAMETER_MISSING deep link opens the OL Parameters screen", async ({ page }) => {
  await page.goto("/ordinary-life/commitments")
  await page.getByRole("button", { name: "Generate Commitments" }).click()

  await page.getByLabel(/Proposal/).click()
  await page.getByRole("option", { name: /Param Missing/ }).click()

  await expect(page.getByTestId("error-coach-code")).toContainText("PARAMETER_MISSING")
  await page.getByTestId("error-coach-deep-link").click()
  await expect(page).toHaveURL(/\/ordinary-life\/parameters\/policy-setup$/)
})

test("import dry-runs with row errors then commits clean rows", async ({ page }) => {
  await page.goto("/ordinary-life/commitments")
  await page.getByRole("button", { name: "Import CSV" }).click()

  await page.getByTestId("import-file-input").setInputFiles({ name: "bad.csv", mimeType: "text/csv", buffer: Buffer.from(CSV_ERROR_ROWS) })
  await expect(page.getByText(/2 data row\(s\)/)).toBeVisible()
  await page.getByTestId("dry-run").click()
  await expect(page.getByText("Fix and reprocess before creating")).toBeVisible()
  await expect(page.getByText("Must be a three-letter code.")).toBeVisible()
  await expect(page.getByTestId("commit-import")).toBeDisabled()

  await page.getByTestId("import-file-input").setInputFiles({ name: "clean.csv", mimeType: "text/csv", buffer: Buffer.from(CSV_CLEAN_ROWS) })
  await expect(page.getByText(/2 data row\(s\)/)).toBeVisible()
  await page.getByTestId("dry-run").click()
  await expect(page.getByText("Dry run passed")).toBeVisible()
  await page.getByTestId("commit-import").click()
  await expect(page.getByText(/Commitments imported/i)).toBeVisible()
})

test("detail tabs and payment recording success", async ({ page }) => {
  await page.goto("/ordinary-life/commitments")
  await page.getByText("OLC-2026-00001").click()
  await expect(page).toHaveURL(/\/ordinary-life\/commitments\/c-1$/)

  await page.getByRole("button", { name: "Allocations" }).click()
  await expect(page.getByText("RCT-2026-001")).toBeVisible()
  await page.getByRole("button", { name: "History" }).click()
  await expect(page.getByText("Cash allocation posted")).toBeVisible()
  await page.locator('[aria-label="Commitment tabs"]').getByRole("button", { name: "Notifications" }).click()
  await expect(page.getByText("GRACE_START")).toBeVisible()

  await page.getByRole("button", { name: "Record Payment" }).click()
  await page.getByLabel(/Amount/).fill("25000")
  await page.getByLabel(/Payment mode/).click()
  await page.getByRole("option", { name: "Cash" }).click()
  await page.getByLabel(/Receipt reference/).fill("RCT-E2E-1")
  await page.getByTestId("record-payment-submit").click()
  await expect(page.getByText(/Payment recorded/i)).toBeVisible()
})

test("overpayment renders the ErrorCoach with resolution steps", async ({ page }) => {
  await page.goto("/ordinary-life/commitments")
  await page.getByText("OLC-2026-00001").click()
  await page.getByRole("button", { name: "Record Payment" }).click()
  await page.getByLabel(/Amount/).fill("999999")
  await page.getByLabel(/Payment mode/).click()
  await page.getByRole("option", { name: "Cash" }).click()
  await page.getByLabel(/Receipt reference/).fill("RCT-E2E-OVER")
  await page.getByTestId("record-payment-submit").click()

  await expect(page.getByTestId("error-coach-code")).toHaveText("COMMITMENT_OVERPAYMENT")
  await expect(page.getByText(/Adjust the amount so it is equal to or below the outstanding balance/)).toBeVisible()
})

test("invalid transition ErrorCoach lists allowed transitions", async ({ page }) => {
  await page.goto("/ordinary-life/commitments")
  await page.getByText("OLC-2026-00001").click()
  await page.getByRole("button", { name: "Cancel" }).click()
  await page.getByLabel(/Reason/).fill("Attempting an invalid cancellation")
  await page.getByTestId("lifecycle-submit-cancel").click()

  await expect(page.getByTestId("error-coach-code")).toContainText("COMMITMENT_INVALID_TRANSITION")
  await expect(page.getByText(/Allowed transitions: suspend from PARTIALLY_PAID/)).toBeVisible()
})

test("overdue processing summary and bell deep link", async ({ page }) => {
  await page.goto("/ordinary-life/commitments")
  await page.getByRole("button", { name: "Run Overdue Processing" }).click()
  await page.getByTestId("run-overdue").click()

  await expect(page.getByTestId("overdue-summary")).toBeVisible()
  await expect(page.getByTestId("overdue-summary")).toContainText("Marked overdue")
  await expect(page.getByTestId("overdue-summary")).toContainText("3")

  await page.getByLabel("Close dialog").last().click()
  await expect(page.getByRole("heading", { name: "Overdue Processing" })).toBeHidden()
  await page.getByLabel("Notifications").click()
  const bellItem = page.getByText("Commitment OLC-2026-00002 is overdue")
  await bellItem.click()
  await expect(page).toHaveURL(/\/ordinary-life\/commitments\/c-2$/)
})

test("portal read-only scoping shows banner and no actions", async ({ page }) => {
  await page.goto("/portal/commitments")
  await expect(page.getByRole("heading", { name: "My Commitments" })).toBeVisible()
  await expect(page.getByText(/To make a payment or dispute a commitment/)).toBeVisible()
  await expect(page.getByTestId("raise-ticket")).toHaveAttribute("href", "/tickets")
  await expect(page.getByRole("button", { name: /Record Payment/ })).toHaveCount(0)
  await expect(page.getByRole("button", { name: /Cancel/ })).toHaveCount(0)
})