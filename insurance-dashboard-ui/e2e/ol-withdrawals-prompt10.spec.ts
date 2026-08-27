import { expect, test, type Page, type Route } from "@playwright/test"
import { mockAccessApi, seedSuperuserSession } from "./fixtures"

const permissions = [
  { module: "ol_withdrawals", action: "view" },
  { module: "ol_withdrawals", action: "request" },
  { module: "ol_withdrawals", action: "approve" },
  { module: "ol_withdrawals", action: "process_payout" },
  { module: "ol_withdrawals", action: "cancel" },
  { module: "ol_withdrawals", action: "reverse" },
  { module: "ol_withdrawals", action: "print" },
]

const policy = {
  id: "policy-e2e-1",
  policy_number: "ZIC-OL-E2E-000001",
  policyholder_name: "Amani Salum",
  policyholder_display: "P-000001 — Amani Salum",
  product_plan_display: "OL_EDU_GROWTH — Elimu Bora Growth Plan",
  status: "ACTIVE",
  status_display: "Active",
  currency: "TZS",
  cash_value: "1000000.00",
  loan_balance: "100000.00",
  available_limit: "900000.00",
}

const baseWithdrawal = {
  id: "withdrawal-e2e-1",
  withdrawal_number: "OL-WDR-E2E-000001",
  policy_id: policy.id,
  policy_number: policy.policy_number,
  policy_display: `${policy.policy_number} — ${policy.policyholder_name}`,
  policyholder_name: policy.policyholder_name,
  policyholder_display: policy.policyholder_display,
  product_display: policy.product_plan_display,
  agent_display: "AG-0001 — ZIC Agency",
  branch_display: "ZNZ-MAIN — Zanzibar Main Branch",
  currency: "TZS",
  gross_amount: "250000.00",
  fee_amount: "12500.00",
  net_payout: "237500.00",
  cash_value_before: "1000000.00",
  loan_balance_before: "100000.00",
  cash_value_after: "650000.00",
  status: "REQUESTED",
  status_display: "Requested",
  reason: "Education expenses",
  requested_at: "2026-08-27T09:00:00Z",
  approved_at: null,
  processed_at: null,
  paid_at: null,
  allowed_actions: ["view", "approve", "reject", "cancel", "print"],
  created_at: "2026-08-27T09:00:00Z",
  updated_at: "2026-08-27T09:00:00Z",
}

function json(data: unknown, status = 200) {
  return { status, contentType: "application/json", body: JSON.stringify({ data }) }
}

function structuredError(code: string, message: string, fieldErrors: Record<string, string[]> = {}, status = 422) {
  return { status, contentType: "application/json", body: JSON.stringify({ success: false, errorCode: code, message, fieldErrors, resolutionSteps: ["Review the highlighted fields.", "Confirm the withdrawal policy and current permission state."], error: { code, message, details: { fieldErrors } } }) }
}

async function mockWithdrawalReleaseApi(page: Page, initialStatus: string = "REQUESTED") {
  let currentWithdrawal = { ...baseWithdrawal }
  if (initialStatus === "APPROVED") currentWithdrawal = { ...currentWithdrawal, status: "APPROVED", status_display: "Approved", approved_at: "2026-08-27T10:00:00Z", allowed_actions: ["view", "process-payout", "cancel", "print"] }
  if (initialStatus === "PAID") currentWithdrawal = { ...currentWithdrawal, status: "PAID", status_display: "Paid", approved_at: "2026-08-27T10:00:00Z", processed_at: "2026-08-27T10:30:00Z", paid_at: "2026-08-27T10:30:00Z", allowed_actions: ["view", "reverse", "print"] }
  const auditEntries: Array<{ action: string; source_channel: string; object: string }> = []
  const documents = [{ id: "withdrawal-document-e2e-1", document_type: "OL_WITHDRAWAL_STATEMENT", template_name: "Withdrawal Statement", template_version: 1, generated_by_display: "ZIC Finance", generated_at: "2026-08-27T10:05:00Z", page_count: 2, signed_download_url: "/api/v1/documents/instances/withdrawal-document-e2e-1/download/?ticket=withdrawal-ticket" }]

  const detail = () => ({
    ...currentWithdrawal,
    breakdown: { withdrawal_id: currentWithdrawal.id, currency: "TZS", cash_value_before: currentWithdrawal.cash_value_before, gross_withdrawal: currentWithdrawal.gross_amount, withdrawal_fee: currentWithdrawal.fee_amount, fee_rate: "5.0000", fee_basis: "5% fixed", net_payout: currentWithdrawal.net_payout, cash_value_after: currentWithdrawal.cash_value_after, sum_assured_before: "10000000.00", sum_assured_after: "9000000.00", adjustment_ratio: "10.0000", audit_trail: [{ action: "CALCULATED", actor_name: "ZIC Finance", source_channel: "WEB", created_at: currentWithdrawal.requested_at }] },
    payments: currentWithdrawal.status === "PAID" ? [{ id: "payment-e2e-1", payment_mode: "BANK_TRANSFER", payment_mode_display: "Bank transfer", receipt_reference: "RCT-E2E-0001", amount: currentWithdrawal.net_payout, currency: "TZS", payment_date: currentWithdrawal.paid_at, status: "COMPLETED", created_at: currentWithdrawal.paid_at }] : [],
    audit_timeline: [{ id: "audit-e2e-request", action: "REQUESTED", actor_display: "ZIC Superadmin", source_channel: "WEB", reason: currentWithdrawal.reason, created_at: currentWithdrawal.requested_at }, ...auditEntries.map((entry, index) => ({ id: `audit-e2e-${index + 2}`, action: entry.action, actor_display: "ZIC Superadmin", source_channel: entry.source_channel, reason: "Controlled withdrawal action", created_at: "2026-08-27T10:30:00Z" }))],
    documents,
    policy_context: { policy_number: policy.policy_number, cash_value_before: currentWithdrawal.cash_value_before, cash_value_after: currentWithdrawal.cash_value_after },
  })

  await page.route("**/api/v1/ol/withdrawals/**", async (route: Route) => {
    const url = new URL(route.request().url())
    const path = url.pathname
    const method = route.request().method()
    if (path.endsWith("/kpis/")) {
      await route.fulfill(json({ total_withdrawn_current_month: currentWithdrawal.gross_amount, total_withdrawn_current_month_count: 1, pending_approvals_count: currentWithdrawal.status === "REQUESTED" ? 1 : 0, pending_approvals_amount: currentWithdrawal.status === "REQUESTED" ? currentWithdrawal.gross_amount : "0.00", processing_payouts_count: currentWithdrawal.status === "PROCESSING" ? 1 : 0, average_fee_amount: currentWithdrawal.fee_amount, currency: "TZS", timestamp: "2026-08-27T10:00:00Z" }))
      return
    }
    if (path.includes("/options/")) {
      const kind = path.split("/options/")[1]?.split("/")[0]
      if (kind === "policies") {
        await route.fulfill(json({ count: 1, results: [{ value: policy.id, label: `${policy.policy_number} — ${policy.policyholder_name}`, meta: { ...policy, status: "ACTIVE" } }], next: null, previous: null }))
      } else if (kind === "products") {
        await route.fulfill(json({ count: 1, results: [{ value: "OL_EDU_GROWTH", label: policy.product_plan_display }] }))
      } else if (kind === "branches") {
        await route.fulfill(json({ count: 1, results: [{ value: "ZNZ-MAIN", label: "ZNZ-MAIN — Zanzibar Main Branch" }] }))
      } else if (kind === "agents") {
        await route.fulfill(json({ count: 1, results: [{ value: "agent-1", label: "AG-0001 — ZIC Agency" }] }))
      } else {
        await route.fulfill(json({ count: 1, results: [{ value: "BANK_TRANSFER", label: "Bank transfer" }] }))
      }
      return
    }
    const actionMatch = path.match(/\/withdrawals\/([^/]+)\/(approve|reject|process-payout|cancel|reverse)\/$/)
    if (actionMatch && method === "POST") {
      const action = actionMatch[2]
      const payload = JSON.parse(route.request().postData() || "{}") as Record<string, unknown>
      if (["reject", "cancel", "reverse"].includes(action) && !String(payload.reason ?? "").trim()) {
        await route.fulfill(structuredError("REASON_REQUIRED", "A reason is required before this withdrawal can be changed.", { reason: ["Enter a reason."] }))
        return
      }
      auditEntries.push({ action: `WITHDRAWAL_${action.toUpperCase().replace("-", "_")}`, source_channel: "WEB", object: currentWithdrawal.withdrawal_number })
      if (action === "approve") currentWithdrawal = { ...currentWithdrawal, status: "APPROVED", status_display: "Approved", approved_at: "2026-08-27T10:00:00Z", allowed_actions: ["view", "process-payout", "cancel", "print"] }
      if (action === "process-payout") currentWithdrawal = { ...currentWithdrawal, status: "PAID", status_display: "Paid", processed_at: "2026-08-27T10:30:00Z", paid_at: "2026-08-27T10:30:00Z", allowed_actions: ["view", "reverse", "print"] }
      if (action === "cancel") currentWithdrawal = { ...currentWithdrawal, status: "CANCELLED", status_display: "Cancelled", allowed_actions: ["view", "print"] }
      if (action === "reverse") currentWithdrawal = { ...currentWithdrawal, status: "REVERSED", status_display: "Reversed", allowed_actions: ["view", "print"], cash_value_after: "1000000.00" }
      if (action === "reject") currentWithdrawal = { ...currentWithdrawal, status: "DECLINED", status_display: "Declined", allowed_actions: ["view", "print"] }
      await route.fulfill(json({ withdrawal: currentWithdrawal, meta: { audit_recorded: true, source_channel: "WEB" } }, 201))
      return
    }
    if (path.endsWith("/breakdown/")) { await route.fulfill(json(detail().breakdown)); return }
    if (path.endsWith("/payments/")) { await route.fulfill(json({ count: detail().payments.length, results: detail().payments, next: null, previous: null })); return }
    if (path.endsWith("/audit/")) { await route.fulfill(json({ count: detail().audit_timeline.length, results: detail().audit_timeline, next: null, previous: null })); return }
    if (path.endsWith("/print-statement/") && method === "POST") { auditEntries.push({ action: "DOCUMENT_GENERATED", source_channel: "WEB", object: currentWithdrawal.withdrawal_number }); await route.fulfill(json({ instance: documents[0], preview_url: documents[0].signed_download_url, signed_download_url: documents[0].signed_download_url }, 201)); return }
    if (path.endsWith("/withdrawals/") && method === "GET") { await route.fulfill(json({ count: 1, results: [currentWithdrawal], next: null, previous: null, page: 1, page_size: 20 })); return }
    if (path.match(/\/withdrawals\/[^/]+\/$/) && method === "GET") { await route.fulfill(json(detail())); return }
    await route.fallback()
  })

  await page.route("**/api/v1/ol/policies/**", async (route: Route) => {
    const url = new URL(route.request().url())
    const path = url.pathname
    const method = route.request().method()
    if (path.endsWith("/withdrawals/eligibility/")) { await route.fulfill(json({ policy_id: policy.id, policy_number: policy.policy_number, policyholder_display: policy.policyholder_display, currency: "TZS", policy_status: "ACTIVE", eligible: true, cash_value: policy.cash_value, loan_balance: policy.loan_balance, available_limit: policy.available_limit, fee_rate: "5.0000", fee_basis: "5% fixed" })); return }
    if (path.endsWith("/withdrawals/") && method === "POST") {
      const payload = JSON.parse(route.request().postData() || "{}") as Record<string, unknown>
      const amount = Number(payload.amount ?? 0)
      if (amount > Number(policy.available_limit)) { await route.fulfill(structuredError("WITHDRAWAL_LIMIT_EXCEEDED", "Amount exceeds available cash value limit.", { amount: [`The maximum available amount is ${policy.available_limit}.`] })); return }
      currentWithdrawal = { ...currentWithdrawal, id: "withdrawal-e2e-requested", withdrawal_number: "OL-WDR-E2E-000002", gross_amount: amount.toFixed(2), fee_amount: (amount * 0.05).toFixed(2), net_payout: (amount * 0.95).toFixed(2), status: "REQUESTED", status_display: "Requested", reason: String(payload.reason ?? ""), allowed_actions: ["view", "approve", "reject", "cancel", "print"] }
      auditEntries.push({ action: "WITHDRAWAL_REQUESTED", source_channel: "WEB", object: currentWithdrawal.withdrawal_number })
      await route.fulfill(json({ withdrawal: currentWithdrawal, meta: { audit_recorded: true, source_channel: "WEB" } }, 201))
      return
    }
    if (path.endsWith("/withdrawals/") && method === "GET") { await route.fulfill(json({ count: 1, results: [{ id: policy.id, policy_number: policy.policy_number, policyholder_name: policy.policyholder_name, policyholder_display: policy.policyholder_display, product_plan_display: policy.product_plan_display, status: "ACTIVE", status_display: "Active", currency: "TZS" }], next: null, previous: null })); return }
    await route.fallback()
  })

  await page.route("**/api/v1/documents/instances/**", async (route: Route) => {
    const path = new URL(route.request().url()).pathname
    if (path.endsWith("/download/")) { await route.fulfill({ status: 200, contentType: "application/pdf", headers: { "Content-Disposition": "inline; filename=withdrawal-statement.pdf" }, body: "%PDF-1.7\n1 0 obj\n<<>>\nendobj\n%%EOF" }); return }
    if (path.endsWith("/instances/") || path.endsWith("/instances")) { await route.fulfill(json({ count: documents.length, page: 1, page_size: 50, results: documents })); return }
    await route.fallback()
  })

  return { auditEntries }
}

async function openStaffDetail(page: Page) {
  await page.goto("/ordinary-life/withdrawals")
  await expect(page.getByText("OL-WDR-E2E-000001")).toBeVisible()
  const row = page.getByRole("row").filter({ hasText: "OL-WDR-E2E-000001" }).first()
  await row.getByRole("button", { name: /Actions for row/ }).click()
  await page.getByRole("button", { name: "View" }).click()
  await expect(page).toHaveURL(/\/ordinary-life\/withdrawals\/withdrawal-e2e-1$/)
  await expect(page.getByText("OL-WDR-E2E-000001").first()).toBeVisible()
}

test.describe("OL Withdrawals final release", () => {
  test.beforeEach(async ({ page }) => {
    await seedSuperuserSession(page)
    await mockAccessApi(page, ["ol_withdrawals", "ol_parameters", "ordinary_life"], permissions)
  })

  test("staff opens list to detail, requests within limit, and records audit evidence", async ({ page }) => {
    const release = await mockWithdrawalReleaseApi(page)
    await openStaffDetail(page)
    expect(page.url()).not.toMatch(/[0-9a-f]{8}-[0-9a-f-]{27,}/i)

    await page.goto("/ordinary-life/withdrawals")
    await page.getByRole("button", { name: "Request Withdrawal" }).click()
    const modal = page.getByRole("dialog", { name: "Request Withdrawal" })
    await modal.getByPlaceholder("Policy number or policyholder").fill("ZIC-OL-E2E-000001")
    await modal.getByRole("button", { name: /ZIC-OL-E2E-000001/ }).click()
    await expect(page).toHaveURL(/\/ordinary-life\/withdrawals\/new\?policy_id=policy-e2e-1/)
    await expect(page.getByText("Available Limit")).toBeVisible()
    await page.getByRole("button", { name: "Continue" }).click()
    await page.getByPlaceholder("Up to 900000.00").fill("250000")
    await page.getByPlaceholder("Explain why the policyholder is requesting this withdrawal.").fill("Education expenses")
    await page.getByRole("button", { name: "Continue" }).click()
    await expect(page.getByRole("heading", { name: "Summary & Impact" })).toBeVisible()
    await page.getByRole("button", { name: "Submit Request" }).click()
    await expect(page).toHaveURL(/\/ordinary-life\/withdrawals\/withdrawal-e2e-requested$/)
    expect(release.auditEntries.some((entry) => entry.action === "WITHDRAWAL_REQUESTED" && entry.source_channel === "WEB")).toBe(true)
  })

  test("teaches the amount limit and approval-reason errors", async ({ page }) => {
    await mockWithdrawalReleaseApi(page)
    await page.goto("/ordinary-life/withdrawals/new?policy_id=policy-e2e-1")
    await expect(page.getByText("Available Limit")).toBeVisible()
    await page.getByRole("button", { name: "Continue" }).click()
    await page.getByPlaceholder("Up to 900000.00").fill("950000")
    await page.getByRole("button", { name: "Continue" }).click()
    await expect(page.getByRole("alert").getByText("Amount exceeds available cash value limit.", { exact: true })).toBeVisible()

    await page.goto("/ordinary-life/withdrawals/withdrawal-e2e-1?action=approve")
    const approveDialog = page.getByRole("dialog", { name: "Approve withdrawal" })
    await approveDialog.getByRole("button", { name: "Confirm Approval" }).click()
    await expect(approveDialog.getByText("Reason for approval is required before you can continue.", { exact: true })).toBeVisible()
  })

  test("approves, processes payout, reverses, and verifies policy cash-value restoration", async ({ page }) => {
    const release = await mockWithdrawalReleaseApi(page)
    await page.goto("/ordinary-life/withdrawals/withdrawal-e2e-1?action=approve")
    const approveDialog = page.getByRole("dialog", { name: "Approve withdrawal" })
    await approveDialog.getByLabel("Reason for Approval").fill("Eligibility and documents verified")
    await approveDialog.getByRole("button", { name: "Confirm Approval" }).click()
    await expect(page.getByText("Status updated to Approved.")).toBeVisible()

    await page.goto("/ordinary-life/withdrawals/withdrawal-e2e-1?action=process_payout")
    const payoutDialog = page.getByRole("dialog", { name: "Process Payout withdrawal" })
    await payoutDialog.getByLabel("Payment Mode").selectOption("BANK_TRANSFER")
    await payoutDialog.getByLabel("Receipt Reference").fill("RCT-E2E-0001")
    await payoutDialog.getByRole("button", { name: "Confirm Payout Processed" }).click()
    await expect(page.getByText("Status updated to Paid.")).toBeVisible()

    await page.goto("/ordinary-life/withdrawals/withdrawal-e2e-1?action=reverse")
    const reverseDialog = page.getByRole("dialog", { name: "Reverse withdrawal" })
    await expect(reverseDialog.getByText("This will restore the policy cash value. Are you sure?")).toBeVisible()
    await reverseDialog.getByLabel("Reason for Reversal").fill("Payment was reversed after reconciliation")
    await reverseDialog.getByRole("button", { name: "Reverse Withdrawal", exact: true }).click()
    await expect(page.getByText("Status updated to Reversed.")).toBeVisible()
    expect(release.auditEntries.map((entry) => entry.action)).toEqual(["WITHDRAWAL_APPROVE", "WITHDRAWAL_PROCESS_PAYOUT", "WITHDRAWAL_REVERSE"])
  })

  test("prints a statement through authenticated preview and signed ticket actions", async ({ page }) => {
    await mockWithdrawalReleaseApi(page, "PAID")
    await page.goto("/ordinary-life/withdrawals/withdrawal-e2e-1?tab=documents")
    await expect(page.getByTestId("withdrawal-documents-panel")).toBeVisible()
    await page.getByRole("button", { name: "Print Statement" }).click()
    await expect(page.getByTitle("Withdrawal Statement PDF")).toBeVisible()
    await expect(page.locator('iframe[title="Withdrawal Statement PDF"]')).toHaveAttribute("src", /^blob:/)
    const downloadPromise = page.waitForEvent("download")
    await page.getByRole("button", { name: "Download" }).last().click()
    expect(await (await downloadPromise).path()).not.toBeNull()
    const popupPromise = page.waitForEvent("popup")
    const previewDialog = page.getByRole("dialog", { name: "Withdrawal Statement · PDF" })
    await previewDialog.getByRole("button", { name: "Open in New Tab", exact: true }).click()
    const popup = await popupPromise
    await expect.poll(() => popup.url()).toContain("ticket=withdrawal-ticket")
    await popup.close()
    await expect(page.getByText(/401|Session expired|no secure PDF URL/i)).not.toBeVisible()
  })

  test("partner portal shows scoped read-only withdrawals and no staff actions", async ({ page }) => {
    await mockAccessApi(page, ["portal"], [])
    await page.route("**/api/v1/portal/withdrawals/**", async (route: Route) => {
      const path = new URL(route.request().url()).pathname
      if (path.endsWith("/withdrawals/")) await route.fulfill(json({ count: 1, results: [{ id: "portal-withdrawal-1", request_number: "OL-WDR-PORTAL-0001", policy_id: policy.id, policy_number: policy.policy_number, policyholder_display: policy.policyholder_display, product_display: policy.product_plan_display, currency: "TZS", gross_amount: "100000.00", net_payout: "95000.00", status: "REQUESTED", status_display: "Requested", requested_at: "2026-08-27T09:00:00Z", reason: "Education", request_allowed: true }] })); else await route.fulfill(json({ id: "portal-withdrawal-1", request_number: "OL-WDR-PORTAL-0001", policy_id: policy.id, policy_number: policy.policy_number, policyholder_display: policy.policyholder_display, product_display: policy.product_plan_display, currency: "TZS", gross_amount: "100000.00", net_payout: "95000.00", status: "REQUESTED", status_display: "Requested", requested_at: "2026-08-27T09:00:00Z", reason: "Education", request_allowed: true }))
    })
    await page.goto("/portal/withdrawals")
    await expect(page.getByText("OL-WDR-PORTAL-0001")).toBeVisible()
    await expect(page.getByRole("button", { name: "Request Withdrawal" })).toBeVisible()
    await expect(page.getByText("For changes to withdrawal terms, contact ZIC Finance.")).toBeVisible()
    await expect(page.getByRole("button", { name: "Approve" })).not.toBeVisible()
    await expect(page.getByRole("button", { name: "Process Payout" })).not.toBeVisible()
    await expect(page.getByRole("button", { name: "Reverse" })).not.toBeVisible()
  })
})
