import { expect, test } from "@playwright/test"
import { mockAccessApi, mockCommitmentPrintApi, mockQuotationApi, mockUnifiedDocumentApi, seedSuperuserSession } from "./fixtures"

async function expectPdfPreview(page: import("@playwright/test").Page, title: string) {
  await page.getByRole("button", { name: "Preview" }).click()
  await expect(page.getByRole("heading", { name: title }).last()).toBeVisible()
  const frame = page.locator('iframe[title$="PDF"]').last()
  await expect(frame).toBeVisible()
  await expect(frame).toHaveAttribute("src", /^blob:/)
  await page.getByRole("button", { name: "Close PDF preview" }).click()
}

test.describe("unified print engine", () => {
  test("staff prints a quotation from the list, previews the PDF, downloads it, and opens only a signed ticket", async ({ page }) => {
    await seedSuperuserSession(page)
    await mockAccessApi(page, ["ol_quotations", "ol_parameters", "ordinary_life"])
    await mockQuotationApi(page, { status: "FINALIZED", quote_number: "Q-E2E-0002" })
    await mockUnifiedDocumentApi(page)

    await page.goto("/ordinary-life/quotations")
    await expect(page.getByText("Q-E2E-0002")).toBeVisible()
    const quotationRow = page.getByRole("row").filter({ hasText: "Q-E2E-0002" }).first()
    await quotationRow.getByRole("button", { name: /Actions for row/ }).click()
    await page.getByRole("button", { name: "Print" }).click()
    await expect(page.getByRole("heading", { name: "Quotation documents · Q-E2E-0002" })).toBeVisible()

    await expectPdfPreview(page, "Quotation documents")
    const downloadPromise = page.waitForEvent("download")
    await page.getByRole("button", { name: "Download" }).click()
    const download = await downloadPromise
    expect(download.suggestedFilename()).toBe("ol_quotation-document-quote-1.pdf")
    expect(await download.path()).not.toBeNull()

    const popupPromise = page.waitForEvent("popup")
    await page.getByRole("button", { name: "Open in new tab" }).click()
    const popup = await popupPromise
    await expect.poll(() => popup.url()).toContain("ticket=quote-ticket")
    expect(popup.url()).toMatch(/\/api\/v1\/documents\/instances\/document-quote-1\/download\/\?ticket=/)
    await popup.close()
    await expect(page.getByText(/401|Session expired/i)).not.toBeVisible()
  })

  test("retries one expired document token transparently before showing the PDF", async ({ page }) => {
    await seedSuperuserSession(page)
    await mockAccessApi(page, ["ol_quotations", "ol_parameters", "ordinary_life"])
    await mockQuotationApi(page)
    const documentMock = await mockUnifiedDocumentApi(page, { expireFirstDownload: true })

    await page.goto("/ordinary-life/quotations/quote-1")
    await page.getByRole("button", { name: "Documents" }).click()
    await expectPdfPreview(page, "Quotation documents")
    expect(documentMock.getRefreshCalls()).toBeGreaterThanOrEqual(1)
    await expect(page.getByText(/Session expired/i)).not.toBeVisible()
  })

  test("prints a proposal through the same authenticated document panel", async ({ page }) => {
    await seedSuperuserSession(page)
    await mockAccessApi(page, ["ol_proposals", "ol_parameters", "ordinary_life"])
    await mockUnifiedDocumentApi(page)

    await page.goto("/ordinary-life/proposals")
    await expect(page.getByText("OLP-E2E-0001")).toBeVisible()
    await page.getByText("OLP-E2E-0001").click()
    await page.getByRole("button", { name: "Print" }).click()
    await expect(page.getByRole("heading", { name: "Print preview — proposal summary" })).toBeVisible()
    await expect(page.locator('iframe[title="Print preview"]')).toBeVisible()
    const proposalDownloadPromise = page.waitForEvent("download")
    await page.getByRole("button", { name: "Download PDF" }).click()
    expect(await (await proposalDownloadPromise).path()).not.toBeNull()
    const proposalPopupPromise = page.waitForEvent("popup")
    await page.getByRole("button", { name: "Open in New Tab" }).click()
    const proposalPopup = await proposalPopupPromise
    await expect.poll(() => proposalPopup.url()).toContain("ticket=proposal-ticket")
    await proposalPopup.close()
  })

  test("prints a commitment through the same authenticated document panel", async ({ page }) => {
    await seedSuperuserSession(page)
    await mockAccessApi(page, ["ol_commitments", "ol_parameters", "ordinary_life"], [{ module: "ol_commitments", action: "view" }])
    await mockCommitmentPrintApi(page)
    await mockUnifiedDocumentApi(page)

    await page.goto("/ordinary-life/commitments/c-1")
    await expect(page.getByText("OLC-2026-00001")).toBeVisible()
    await page.getByRole("button", { name: "Documents" }).click()
    await expect(page.getByRole("heading", { name: "Commitment documents" })).toBeVisible()
    await expectPdfPreview(page, "Commitment documents")
    const commitmentDownloadPromise = page.waitForEvent("download")
    await page.getByRole("button", { name: "Download" }).click()
    expect(await (await commitmentDownloadPromise).path()).not.toBeNull()
    const commitmentPopupPromise = page.waitForEvent("popup")
    await page.getByRole("button", { name: "Open in new tab" }).click()
    const commitmentPopup = await commitmentPopupPromise
    await expect.poll(() => commitmentPopup.url()).toContain("ticket=commitment-ticket")
    await commitmentPopup.close()
  })
})
