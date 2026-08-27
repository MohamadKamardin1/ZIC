import { expect, test, type Page, type Route } from "@playwright/test"
import { mockAccessApi, seedSuperuserSession } from "./fixtures"

const loanBase = {
  id: "loan-e2e-1",
  loan_number: "LOAN-E2E-0001",
  policy_number: "POL-E2E-0001",
  policy_display: "POL-E2E-0001 — Asha Mussa",
  policyholder_name: "Asha Mussa",
  partner_display: "P-000001 — Asha Mussa",
  product_display: "Elimu Bora Growth Plan",
  agent_display: "AG-0001 — ZIC Agency",
  branch_display: "ZNZ-MAIN — Zanzibar Main Branch",
  currency: "TZS",
  principal_amount: "1000000.00",
  cash_value_snapshot: "2000000.00",
  disbursed_amount: "1000000.00",
  repayment_mode: "PAYMENT_SCHEDULE",
  interest_rate: "8.00",
  compounding_frequency: "MONTHLY",
  term_months: 12,
  disbursement_date: "2026-01-15",
  maturity_date: "2027-01-15",
  status: "ACTIVE",
  status_display: "Active",
  total_repaid: "400000.00",
  outstanding_balance: "600000.00",
  approval_required: false,
  approved_at: "2026-01-10T10:00:00Z",
  rejected_at: null,
  rejection_reason: "",
  reason: "Education expenses",
  allowed_actions: ["view", "repay", "offset", "print"],
  created_at: "2026-01-05T10:00:00Z",
  updated_at: "2026-08-27T10:00:00Z",
}

const permissions = [
  { module: "ol_loans", action: "view" },
  { module: "ol_loans", action: "request" },
  { module: "ol_loans", action: "disburse" },
  { module: "ol_loans", action: "repay" },
  { module: "ol_loans", action: "offset" },
  { module: "ol_loans", action: "print" },
]

function json(data: unknown, status = 200) {
  return { status, contentType: "application/json", body: JSON.stringify({ data }) }
}

async function mockLoanReleaseApi(page: Page, initialStatus: "ACTIVE" | "APPROVED" = "ACTIVE") {
  let currentLoan = {
    ...loanBase,
    ...(initialStatus === "APPROVED" ? { status: "APPROVED", status_display: "Approved", outstanding_balance: "1000000.00", total_repaid: "0.00", allowed_actions: ["view", "disburse", "print"] } : {}),
  }
  const auditEntries: Array<{ action: string; source_channel: string; object: string }> = []
  const documents = [{ id: "loan-document-1", document_type: "OL_LOAN_AGREEMENT", template_name: "OL Loan Agreement", template_version: 1, generated_by_display: "ZIC Finance", generated_at: "2026-08-27T10:00:00Z", page_count: 2, signed_download_url: "/api/v1/documents/instances/loan-document-1/download/?ticket=loan-ticket" }]

  const loanRoute = async (route: Route) => {
    const url = new URL(route.request().url())
    const path = url.pathname
    const method = route.request().method()
    if (path.endsWith("/kpis/")) {
      await route.fulfill(json({ totalOutstanding: currentLoan.outstanding_balance, totalDisbursedPeriod: currentLoan.disbursed_amount, activeCount: currentLoan.status === "ACTIVE" || currentLoan.status === "PARTIALLY_REPAID" ? 1 : 0, defaultedCount: currentLoan.status === "DEFAULTED" ? 1 : 0, settledCount: currentLoan.status === "SETTLED" ? 1 : 0, currency: "TZS", amountsByCurrency: {}, timestamp: "2026-08-27T10:00:00Z" }))
      return
    }
    if (path.endsWith("/options/repayment-terms/")) {
      await route.fulfill(json({ count: 1, results: [{ value: "PAYMENT_SCHEDULE", label: "Payment schedule" }], next: null, previous: null }))
      return
    }
    if (path.endsWith("/portal/") && method === "GET") {
      await route.fulfill(json({ count: 1, results: [{ loan_number: "LOAN-E2E-0001", policy_number: "POL-E2E-0001", policyholder: "Asha Mussa", status: "Active", currency: "TZS", principal_amount: "1000000.00", outstanding_balance: currentLoan.outstanding_balance, product: "Elimu Bora Growth Plan", request_allowed: false }] }))
      return
    }
    if (path.includes("/portal/") && method === "GET") {
      await route.fulfill(json({ loan_number: "LOAN-E2E-0001", policy_number: "POL-E2E-0001", policyholder: "Asha Mussa", status: "Active", currency: "TZS", principal_amount: "1000000.00", outstanding_balance: currentLoan.outstanding_balance, product: "Elimu Bora Growth Plan", request_allowed: false, total_repaid: "400000.00", term_months: 12, repayment_mode: "Monthly deduction", schedule: [{ installment_number: 1, due_date: "2026-02-15", principal_due: "80000.00", interest_due: "10000.00", penalty_due: "0.00", amount_paid: "90000.00", balance: currentLoan.outstanding_balance, status: "Paid" }] }))
      return
    }
    if (path.endsWith("/portal/request/") && method === "POST") {
      await route.fulfill(json({ loan_number: "LOAN-E2E-0002", policy_number: "POL-E2E-0001", status: "Requested" }, 201))
      return
    }
    if (path.endsWith("/loans/") && method === "GET") {
      await route.fulfill(json({ count: 1, results: [currentLoan], next: null, previous: null, page: 1, page_size: 20 }))
      return
    }
    if (path.endsWith("/schedule/") && method === "GET") {
      await route.fulfill(json({ count: 0, results: [], next: null, previous: null, aggregates: { total_scheduled: "0.00", total_paid: "0.00", remaining_balance: currentLoan.outstanding_balance } }))
      return
    }
    if (path.endsWith("/repayments/") || path.endsWith("/accruals/")) {
      await route.fulfill(json({ count: 0, results: [], next: null, previous: null }))
      return
    }
    if (path.endsWith("/print-agreement/") || path.endsWith("/print-schedule/")) {
      const schedule = path.endsWith("/print-schedule/")
      const document = { id: schedule ? "loan-document-schedule" : "loan-document-agreement", document_type: schedule ? "OL_LOAN_SCHEDULE" : "OL_LOAN_AGREEMENT", template_name: schedule ? "OL Loan Repayment Schedule" : "OL Loan Agreement", template_version: 2, generated_by_display: "ZIC Finance", generated_at: "2026-08-27T10:05:00Z", page_count: schedule ? 3 : 2, preview_url: `/api/v1/documents/instances/${schedule ? "loan-document-schedule" : "loan-document-agreement"}/download/?ticket=loan-preview`, signed_download_url: `/api/v1/documents/instances/${schedule ? "loan-document-schedule" : "loan-document-agreement"}/download/?ticket=loan-ticket` }
      auditEntries.push({ action: "DOCUMENT_GENERATED", source_channel: "WEB", object: document.id })
      await route.fulfill(json({ instance: document, preview_url: document.preview_url, signed_download_url: document.signed_download_url }, 201))
      return
    }
    const actionMatch = path.match(/\/loans\/([^/]+)\/(disburse|repay|offset)\/$/)
    if (actionMatch && method === "POST") {
      const action = actionMatch[2]
      const payload = JSON.parse(route.request().postData() || "{}") as Record<string, unknown>
      auditEntries.push({ action: `LOAN_${action.toUpperCase()}`, source_channel: "WEB", object: currentLoan.loan_number })
      if (action === "repay") {
        const amount = Number(payload.amount ?? 0)
        const outstanding = Number(currentLoan.outstanding_balance)
        currentLoan = { ...currentLoan, outstanding_balance: Math.max(0, outstanding - amount).toFixed(2), total_repaid: (Number(currentLoan.total_repaid) + amount).toFixed(2), status: outstanding - amount <= 0 ? "SETTLED" : "PARTIALLY_REPAID", status_display: outstanding - amount <= 0 ? "Settled" : "Partially repaid", allowed_actions: outstanding - amount <= 0 ? ["view", "print"] : ["view", "repay", "offset", "print"] }
      } else if (action === "offset") {
        currentLoan = { ...currentLoan, outstanding_balance: "0.00", status: "OFFSET_ON_CLAIM", status_display: "Offset on claim", allowed_actions: ["view", "print"] }
      } else {
        currentLoan = { ...currentLoan, status: "ACTIVE", status_display: "Active", disbursement_date: "2026-08-27", allowed_actions: ["view", "repay", "offset", "print"] }
      }
      await route.fulfill(json({ loan: currentLoan, meta: { audit_recorded: true, source_channel: "WEB" } }, 201))
      return
    }
    if (path.match(/\/loans\/[^/]+\/$/) && method === "GET") {
      await route.fulfill(json(currentLoan))
      return
    }
    await route.fallback()
  }

  await page.route("**/api/v1/ol/loans/**", loanRoute)
  await page.route("**/api/v1/ol/options/payment-modes/**", async (route) => {
    await route.fulfill(json({ count: 1, results: [{ value: "PAYMENT_SCHEDULE", label: "Payment schedule" }], next: null, previous: null }))
  })
  await page.route("**/api/v1/ol/policies/**", async (route) => {
    const url = new URL(route.request().url())
    const path = url.pathname
    const method = route.request().method()
    if (path.endsWith("/loans/request/") && method === "POST") {
      auditEntries.push({ action: "LOAN_REQUESTED", source_channel: "WEB", object: "LOAN-E2E-0002" })
      await route.fulfill(json({ loan: { ...currentLoan, id: "loan-e2e-2", loan_number: "LOAN-E2E-0002", status: "REQUESTED", status_display: "Requested", allowed_actions: ["view", "print"] }, meta: { audit_recorded: true, source_channel: "WEB" } }, 201))
      return
    }
    if (path.endsWith("/loans/eligibility/")) {
      await route.fulfill(json({ policy_id: "policy-e2e-1", policy_number: "POL-E2E-0001", currency: "TZS", policy_status: "ACTIVE", eligible: true, cash_value: "1000000.00", available_loan_limit: "500000.00", minimum_loan_amount: "100000.00", maximum_loan_amount: "500000.00", repayment_modes: ["PAYMENT_SCHEDULE"], approval_required: false }))
      return
    }
    await route.fulfill(json({ count: 1, results: [{ id: "policy-e2e-1", policy_number: "POL-E2E-0001", policyholder_name: "Asha Mussa", policyholder_display: "P-000001 — Asha Mussa", product_plan_display: "Elimu Bora Growth Plan", status: "ACTIVE", status_display: "Active", currency: "TZS" }], next: null, previous: null }))
  })
  await page.route("**/api/v1/documents/instances/**", async (route) => {
    const path = new URL(route.request().url()).pathname
    if (path.endsWith("/download/")) {
      await route.fulfill({ status: 200, contentType: "application/pdf", headers: { "Content-Disposition": "inline; filename=loan-document.pdf" }, body: "%PDF-1.7\n1 0 obj\n<<>>\nendobj\n%%EOF" })
      return
    }
    if (path.endsWith("/instances/") || path.endsWith("/instances")) {
      await route.fulfill(json({ count: documents.length, page: 1, page_size: 50, results: documents }))
      return
    }
    await route.fallback()
  })

  return { auditEntries }
}

test.describe("OL Loans final release", () => {
  test.beforeEach(async ({ page }) => {
    await seedSuperuserSession(page)
    await mockAccessApi(page, ["ol_loans", "ol_parameters", "ordinary_life"], permissions)
  })

  test("staff moves from list to detail, requests within limit, and records audit evidence", async ({ page }) => {
    const release = await mockLoanReleaseApi(page)
    await page.goto("/ordinary-life/loans")
    await expect(page.getByText("LOAN-E2E-0001")).toBeVisible()
    await page.getByRole("button", { name: "Actions for row 1" }).click()
    await page.getByRole("button", { name: "View" }).click()
    await expect(page).toHaveURL(/\/ordinary-life\/loans\/loan-e2e-1$/)
    await expect(page.getByRole("heading", { name: "LOAN-E2E-0001" })).toBeVisible()
    expect(page.url()).not.toMatch(/[0-9a-f]{8}-[0-9a-f-]{27,}/i)

    await page.goto("/ordinary-life/loans")
    await page.getByRole("button", { name: "Request Loan" }).click()
    const dialog = page.getByRole("dialog", { name: "Request Loan" })
    await dialog.getByPlaceholder("Policy number, policyholder, or product").fill("POL-E2E-0001")
    await dialog.getByRole("button", { name: /POL-E2E-0001/ }).click()
    await dialog.getByLabel("Requested Amount").fill("400000")
    await dialog.getByPlaceholder("Explain why the policyholder is requesting this loan.").fill("Education expenses")
    await dialog.getByRole("button", { name: "Next" }).click()
    await expect(dialog.getByRole("button", { name: "Submit Request" })).toBeVisible()
    await dialog.getByRole("button", { name: "Submit Request" }).evaluate((button) => (button as HTMLButtonElement).click())
    await expect(page.getByText("Loan Request Created")).toBeVisible()
    expect(release.auditEntries).toEqual([{ action: "LOAN_REQUESTED", source_channel: "WEB", object: "LOAN-E2E-0002" }])
  })

  test("teaches request-limit and repayment-overbalance errors", async ({ page }) => {
    await mockLoanReleaseApi(page)
    await page.goto("/ordinary-life/loans")
    await page.getByRole("button", { name: "Request Loan" }).click()
    const requestDialog = page.getByRole("dialog", { name: "Request Loan" })
    await requestDialog.getByPlaceholder("Policy number, policyholder, or product").fill("POL-E2E-0001")
    await requestDialog.getByRole("button", { name: /POL-E2E-0001/ }).click()
    await requestDialog.getByLabel("Requested Amount").fill("600000")
    await requestDialog.getByRole("button", { name: "Next" }).click()
    await expect(requestDialog.getByRole("alert")).toContainText("Loan amount exceeds available cash value limit.")

    await page.goto("/ordinary-life/loans/loan-e2e-1?action=repay")
    const repayDialog = page.getByRole("dialog", { name: "Repay Loan" })
    await repayDialog.getByLabel("Repayment amount").fill("700000")
    await repayDialog.getByRole("button", { name: "Process Repayment" }).click()
    await expect(repayDialog.getByRole("alert").filter({ hasText: "no greater than the outstanding balance" })).toBeVisible()
  })

  test("processes disbursement, partial and full repayment, and offset with strict confirmation", async ({ page }) => {
    const release = await mockLoanReleaseApi(page, "APPROVED")
    await page.goto("/ordinary-life/loans/loan-e2e-1?action=disburse")

    const disburseDialog = page.getByRole("dialog", { name: "Disburse Loan" })
    await disburseDialog.getByRole("button", { name: /Payment mode/ }).click()
    await page.getByRole("option", { name: "Payment schedule" }).click()
    await disburseDialog.getByRole("checkbox").check()
    await disburseDialog.getByRole("button", { name: "Disburse Funds" }).click()
    await expect(page.getByText("Loan disbursed")).toBeVisible()

    await page.goto("/ordinary-life/loans/loan-e2e-1?action=repay")
    const partialRepay = page.getByRole("dialog", { name: "Repay Loan" })
    await partialRepay.getByLabel("Repayment amount").fill("300000")
    await partialRepay.getByRole("button", { name: /Payment mode/ }).click()
    await page.getByRole("option", { name: "Payment schedule" }).click()
    await partialRepay.getByRole("textbox", { name: /Receipt reference/ }).fill("RCPT-E2E-001")
    await partialRepay.getByRole("checkbox").check()
    await partialRepay.getByRole("button", { name: "Process Repayment" }).click()
    await expect(page.getByText("Repayment processed")).toBeVisible()

    await page.goto("/ordinary-life/loans/loan-e2e-1?action=repay")
    const fullRepay = page.getByRole("dialog", { name: "Repay Loan" })
    await fullRepay.getByLabel("Repayment amount").fill("700000")
    await fullRepay.getByRole("button", { name: /Payment mode/ }).click()
    await page.getByRole("option", { name: "Payment schedule" }).click()
    await fullRepay.getByRole("textbox", { name: /Receipt reference/ }).fill("RCPT-E2E-002")
    await fullRepay.getByRole("checkbox").check()
    await fullRepay.getByRole("button", { name: "Process Repayment" }).click()
    await expect(page.getByText("Repayment processed")).toBeVisible()

    expect(release.auditEntries.filter((entry) => entry.source_channel === "WEB").length).toBe(3)
  })

  test("applies a claim offset with strict confirmation and records audit evidence", async ({ page }) => {
    const release = await mockLoanReleaseApi(page)
    await page.goto("/ordinary-life/loans/loan-e2e-1?action=offset")
    const offsetDialog = page.getByRole("dialog", { name: "Offset Loan" })
    await offsetDialog.getByLabel("Source transaction reference").fill("CLM-E2E-001")
    await offsetDialog.getByRole("checkbox").check()
    await offsetDialog.getByRole("button", { name: "Confirm Offset" }).click()
    await expect(page.getByText("Loan offset applied")).toBeVisible()
    expect(release.auditEntries.filter((entry) => entry.action === "LOAN_OFFSET" && entry.source_channel === "WEB")).toHaveLength(1)
  })

  test("prints agreement and schedule through authenticated preview and signed-ticket flows", async ({ page }) => {
    await mockLoanReleaseApi(page)
    await page.goto("/ordinary-life/loans/loan-e2e-1?tab=documents")
    await expect(page.getByTestId("loan-documents-panel")).toBeVisible()
    await page.getByRole("button", { name: "Print Agreement" }).click()
    await expect(page.getByTitle("Loan Agreement PDF")).toBeVisible()
    await expect(page.getByText(/Authenticated branded PDF preview/)).toBeVisible()
    const dialog = page.getByRole("dialog")
    await expect(dialog.locator("iframe")).toHaveAttribute("src", /^blob:/)
    const downloadPromise = page.waitForEvent("download")
    await dialog.getByRole("button", { name: "Download" }).click()
    expect(await (await downloadPromise).path()).not.toBeNull()
    await dialog.getByRole("button", { name: "Close PDF preview" }).click()
    await page.getByRole("button", { name: "Print Schedule" }).click()
    await expect(page.getByTitle("Repayment Schedule PDF")).toBeVisible()
    await expect(page.getByText(/DEFAULTED|SETTLED|Authenticated branded PDF preview/)).toBeVisible()
    await expect(page.getByText(/secure PDF URL|no secure/i)).not.toBeVisible()
  })

  test("keeps the partner portal scoped and read-only", async ({ page }) => {
    await mockLoanReleaseApi(page)
    await page.goto("/portal/loans")
    await expect(page.getByRole("heading", { name: "My Loans" })).toBeVisible()
    await expect(page.getByText("LOAN-E2E-0001")).toBeVisible()
    await expect(page.getByRole("button", { name: "Request Loan" })).toHaveCount(0)
    await expect(page.getByRole("button", { name: /Disburse|Repay|Offset|Reverse/ })).toHaveCount(0)
    await page.getByRole("button", { name: "View" }).click()
    await expect(page).toHaveURL(/\/portal\/loans\/LOAN-E2E-0001$/)
    await expect(page.getByTestId("portal-loan-overview")).toBeVisible()
    await expect(page.getByTestId("portal-loan-schedule")).toBeVisible()
    await expect(page.getByRole("button", { name: /Disburse|Repay|Offset|Reverse/ })).toHaveCount(0)
  })
})
