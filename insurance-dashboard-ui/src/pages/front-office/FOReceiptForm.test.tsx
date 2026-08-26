import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react"
import { MemoryRouter, Route, Routes } from "react-router-dom"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { ToastProvider } from "../../components/ui/Toast"
import { ApiClientError } from "../../lib/apiClient"
import type { ReceiptRecord } from "../../lib/receipts-api"
import FOReceiptForm from "./FOReceiptForm"

const apiMocks = vi.hoisted(() => ({
  get: vi.fn(),
  create: vi.fn(),
  patchDraft: vi.fn(),
  post: vi.fn(),
  options: {
    sourceModules: vi.fn(),
    paymentModes: vi.fn(),
  },
}))

vi.mock("../../lib/access", () => ({
  useAccess: () => ({
    access: { permissions: [
      { module: "front_office.receipts", action: "create" },
      { module: "front_office.receipts", action: "edit" },
      { module: "front_office.receipts", action: "post" },
    ] },
    isSuperAdmin: false,
    hasPermission: (code: string) => ["front_office.receipts.create", "front_office.receipts.edit", "front_office.receipts.post"].includes(code),
  }),
}))

vi.mock("../../lib/receipts-api", () => ({ receiptsApi: apiMocks }))

vi.mock("../../components/ui/SmartSelect", () => ({
  SmartSelect: ({ name, label, value = "", onChange, onOptionChange, error, disabled }: { name?: string; label?: string; value?: string; onChange?: (value: string) => void; onOptionChange?: (option: { value: string; label: string; meta?: Record<string, unknown> }) => void; error?: string; disabled?: boolean }) => {
    const options = name === "payment_mode"
      ? [{ value: "CASH", label: "Cash", meta: { requires_reference: false, requires_bank_account: false } }, { value: "BANK_TRANSFER", label: "Bank Transfer", meta: { requires_reference: true, requires_bank_account: true } }]
      : name === "currency" ? [{ value: "TZS", label: "TZS — Tanzanian Shilling" }] : name === "branch" ? [{ value: "branch-1", label: "Zanzibar Main Branch" }] : name === "payer" ? [{ value: "partner-1", label: "Amani Assurance Partner" }] : name === "bank_account" ? [{ value: "bank-1", label: "CRDB — Zanzibar Operations — **** 0042" }] : [{ value: "proposal-1", label: "OLP-2026-000001 — Amani Assurance Partner", meta: { status_hint: "First premium due" } }]
    return <div><label htmlFor={name}>{label}</label><select id={name} name={name} aria-label={label} value={value} disabled={disabled} onChange={(event) => { const option = options.find((candidate) => candidate.value === event.target.value); onChange?.(event.target.value); if (option) onOptionChange?.(option) }}><option value="">Select {label?.toLowerCase()}</option>{options.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select>{error && <p role="alert">{error}</p>}</div>
  },
}))

function renderForm(path = "/front-office/receipts/new") {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={client}><MemoryRouter initialEntries={[path]}><ToastProvider><Routes><Route path="/front-office/receipts/new" element={<FOReceiptForm />} /><Route path="/front-office/receipts/:id" element={<FOReceiptForm />} /></Routes></ToastProvider></MemoryRouter></QueryClientProvider>)
}

function completeRequiredFields() {
  fireEvent.change(screen.getByLabelText("Branch"), { target: { value: "branch-1" } })
  fireEvent.change(screen.getByLabelText("Payer / partner"), { target: { value: "partner-1" } })
  fireEvent.change(screen.getByLabelText("Currency"), { target: { value: "TZS" } })
  fireEvent.change(screen.getByLabelText("Payment mode"), { target: { value: "CASH" } })
  fireEvent.change(screen.getByLabelText(/Amount/), { target: { value: "150000" } })
}

const draft: ReceiptRecord = {
  id: "receipt-draft-1",
  receipt_number: "RCT-2026-000002",
  receipt_date: "2026-08-24",
  payer_display: "Amani Assurance Partner",
  payer_id: "partner-1",
  branch_display: "Zanzibar Main Branch",
  branch_id: "branch-1",
  payment_mode_display: "Cash",
  payment_mode: "CASH",
  currency_display: "TZS — Tanzanian Shilling",
  currency: "TZS",
  receipt_amount: "150000.00",
  allocated_amount: "0.00",
  unallocated_amount: "150000.00",
  status: "DRAFT",
  created_by_display: "Sultan Admin",
  allowed_actions: ["view", "edit", "post"],
}

const posted: ReceiptRecord = { ...draft, id: "receipt-posted-1", receipt_number: "RCT-2026-000003", status: "POSTED", posted_by_display: "Sultan Admin", posted_at: "2026-08-24T09:00:00Z" }

beforeEach(() => {
  vi.clearAllMocks()
  apiMocks.get.mockResolvedValue(draft)
  apiMocks.create.mockResolvedValue(draft)
  apiMocks.patchDraft.mockResolvedValue(draft)
  apiMocks.post.mockResolvedValue(posted)
  apiMocks.options.sourceModules.mockResolvedValue({ count: 4, next: null, previous: null, results: [{ value: "DIRECT", label: "Direct payment" }, { value: "OL_PROPOSAL", label: "Ordinary Life proposal" }, { value: "POLICY", label: "Policy" }, { value: "COMMITMENT", label: "Commitment" }] })
  apiMocks.options.paymentModes.mockResolvedValue({ count: 2, next: null, previous: null, results: [{ value: "CASH", label: "Cash", meta: { requires_reference: false, requires_bank_account: false } }, { value: "BANK_TRANSFER", label: "Bank Transfer", meta: { requires_reference: true, requires_bank_account: true } }] })
})

describe("FOReceiptForm Prompt 3", () => {
  it("applies payment-mode rules live and previews amount in words", async () => {
    renderForm()
    expect(await screen.findByText("Payment details")).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText("Payment mode"), { target: { value: "BANK_TRANSFER" } })
    expect(await screen.findByLabelText(/Payment reference/)).toBeInTheDocument()
    expect(screen.getByLabelText(/Receiving bank account/)).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText(/Amount/), { target: { value: "150000" } })
    expect(screen.getByTestId("amount-in-words")).toHaveTextContent("One hundred fifty thousand Tanzanian shillings only")
    fireEvent.change(screen.getByLabelText("Payment mode"), { target: { value: "CASH" } })
    expect(screen.queryByLabelText(/Payment reference/)).not.toBeInTheDocument()
    expect(screen.queryByLabelText(/Receiving bank account/)).not.toBeInTheDocument()
  })

  it("saves a validated draft with a generated idempotency key", async () => {
    renderForm()
    await screen.findByText("Payment details")
    completeRequiredFields()
    fireEvent.click(screen.getByRole("button", { name: "Save Draft" }))
    await waitFor(() => expect(apiMocks.create).toHaveBeenCalledWith(expect.objectContaining({ receipt_date: expect.any(String), branch: "branch-1", payer: "partner-1", payment_mode: "CASH", receipt_amount: "150000" }), expect.stringMatching(/^[0-9a-f-]{20,}$/i)))
    expect(await screen.findByText("Receipt draft saved")).toBeInTheDocument()
  })

  it("confirms Save & Post, then posts the saved receipt with the next-step hint", async () => {
    renderForm()
    await screen.findByText("Payment details")
    completeRequiredFields()
    fireEvent.click(screen.getByRole("button", { name: "Save & Post" }))
    const dialog = await screen.findByRole("dialog")
    expect(dialog).toHaveTextContent("Branch: Zanzibar Main Branch")
    expect(dialog).toHaveTextContent("Payer: Amani Assurance Partner")
    fireEvent.click(within(dialog).getByRole("button", { name: "Save & Post" }))
    await waitFor(() => expect(apiMocks.post).toHaveBeenCalledWith(draft.id, expect.stringMatching(/^[0-9a-f-]{20,}:post$/i)))
    expect(await screen.findByText(/Next step: Allocate to commitments/)).toBeInTheDocument()
  })

  it("turns an idempotent duplicate into an actionable existing-receipt banner", async () => {
    apiMocks.create.mockRejectedValueOnce(new ApiClientError({ status: 409, code: "RECEIPT_DUPLICATE", message: "This submission was already received.", fieldErrors: {}, deepLink: "/front-office/receipts/receipt-existing" }))
    renderForm()
    await screen.findByText("Payment details")
    completeRequiredFields()
    fireEvent.click(screen.getByRole("button", { name: "Save Draft" }))
    expect(await screen.findByText("This receipt was already submitted")).toBeInTheDocument()
    expect(screen.getByRole("link", { name: "Open existing receipt" })).toHaveAttribute("href", "/front-office/receipts/receipt-existing")
  })

  it("renders backend field errors inline with structured guidance", async () => {
    apiMocks.create.mockRejectedValueOnce(new ApiClientError({ status: 422, code: "RECEIPT_INVALID", message: "The receipt needs correction before it can be saved.", fieldErrors: { receipt_amount: ["Amount must be greater than zero."] }, resolutionSteps: ["Enter the amount received, then try again."] }))
    renderForm()
    await screen.findByText("Payment details")
    completeRequiredFields()
    fireEvent.click(screen.getByRole("button", { name: "Save Draft" }))
    expect(await screen.findByText("Amount must be greater than zero.")).toBeInTheDocument()
    expect(screen.getByText("Enter the amount received, then try again.")).toBeInTheDocument()
  })

  it("keeps posted receipts read-only and explains the immutability rule", async () => {
    apiMocks.get.mockResolvedValueOnce(posted)
    renderForm("/front-office/receipts/receipt-posted-1")
    expect(await screen.findByText("Posted receipt is read-only")).toBeInTheDocument()
    expect(screen.getByLabelText(/Receipt date/)).toBeDisabled()
    expect(screen.queryByRole("button", { name: "Save Draft" })).not.toBeInTheDocument()
    expect(screen.getByText(/Posted receipts are immutable/)).toBeInTheDocument()
  })
})
