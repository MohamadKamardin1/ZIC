import { fireEvent, render, screen, waitFor, within } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { MemoryRouter } from "react-router-dom"
import { createChoiceList, createChoiceOption, deleteChoiceList, deleteChoiceOption, listChoiceLists, listChoiceOptions, updateChoiceList, updateChoiceOption } from "../../lib/api"
import { useAccess } from "../../lib/access"
import { useToast } from "../../components/ui/Toast"
import type { ChoiceList, ChoiceOption } from "../../lib/types"
import OLDropdownConfiguration from "./OLDropdownConfiguration"

vi.mock("../../lib/api", async () => {
  const actual = await vi.importActual<typeof import("../../lib/api")>("../../lib/api")
  return {
    ...actual,
    createChoiceList: vi.fn(),
    createChoiceOption: vi.fn(),
    deleteChoiceList: vi.fn(),
    deleteChoiceOption: vi.fn(),
    listChoiceLists: vi.fn(),
    listChoiceOptions: vi.fn(),
    updateChoiceList: vi.fn(),
    updateChoiceOption: vi.fn(),
  }
})
vi.mock("../../lib/access", () => ({ useAccess: vi.fn() }))
vi.mock("../../components/ui/Toast", () => ({ useToast: vi.fn() }))

const apiMocks = {
  createChoiceList: vi.mocked(createChoiceList),
  createChoiceOption: vi.mocked(createChoiceOption),
  deleteChoiceList: vi.mocked(deleteChoiceList),
  deleteChoiceOption: vi.mocked(deleteChoiceOption),
  listChoiceLists: vi.mocked(listChoiceLists),
  listChoiceOptions: vi.mocked(listChoiceOptions),
  updateChoiceList: vi.mocked(updateChoiceList),
  updateChoiceOption: vi.mocked(updateChoiceOption),
}
const accessMock = vi.mocked(useAccess)
const toastMock = vi.fn()

const frequencyList: ChoiceList = {
  id: "list-frequency",
  group: "ordinary-life",
  code: "OL_PREMIUM_FREQUENCY_CHOICES",
  name: "OL Premium Frequencies",
  description: "Quotation payment frequency catalog",
  isActive: true,
  options: [],
  createdAt: "2026-01-01T00:00:00Z",
  updatedAt: "2026-01-01T00:00:00Z",
}
const modeList: ChoiceList = {
  id: "list-mode",
  group: "ordinary-life",
  code: "OL_PAYMENT_MODE_CHOICES",
  name: "OL Payment Modes",
  description: "Quotation payment mode catalog",
  isActive: true,
  options: [],
  createdAt: "2026-01-01T00:00:00Z",
  updatedAt: "2026-01-01T00:00:00Z",
}
const monthlyOption: ChoiceOption = {
  id: "option-monthly",
  choiceList: frequencyList.id,
  code: "MONTHLY",
  label: "Monthly",
  isDefault: false,
  isActive: true,
  sortOrder: 1,
  metadata: null,
  createdAt: "2026-01-01T00:00:00Z",
  updatedAt: "2026-01-01T00:00:00Z",
}

function accessValue(canManage = true) {
  return {
    access: {
      visibleModules: ["ol_parameters"],
      permissions: canManage ? [{ module: "system_parameters", action: "manage" }] : [{ module: "ol_parameters", action: "view" }],
      groups: [],
    },
    isLoading: false,
    isError: false,
    canAccess: vi.fn(() => true),
    isSuperAdmin: false,
  }
}

function renderPage(entity = "payment-frequencies") {
  return render(
    <MemoryRouter initialEntries={[`/ordinary-life/parameters/dropdown-configuration?entity=${entity}`]}>
      <OLDropdownConfiguration />
    </MemoryRouter>,
  )
}

describe("OL Drop Down Configuration", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    accessMock.mockReturnValue(accessValue())
    vi.mocked(useToast).mockReturnValue({ toast: toastMock, dismiss: vi.fn() })
    apiMocks.listChoiceLists.mockResolvedValue([frequencyList, modeList])
    apiMocks.listChoiceOptions.mockResolvedValue([monthlyOption])
  })

  it("selects the catalog from a SmartSelect Manage deep link and loads its options", async () => {
    renderPage()
    expect(await screen.findByRole("heading", { name: "OL Premium Frequencies" })).toBeInTheDocument()
    expect(apiMocks.listChoiceOptions).toHaveBeenCalledWith(frequencyList.id)
    expect((await screen.findAllByText("MONTHLY")).length).toBeGreaterThanOrEqual(1)
    expect((await screen.findAllByText("Monthly")).length).toBeGreaterThanOrEqual(1)
  })

  it("creates, edits, deactivates, and deletes a dropdown option", async () => {
    const created: ChoiceOption = { ...monthlyOption, id: "option-annual", code: "ANNUAL", label: "Annual" }
    const updated: ChoiceOption = { ...created, label: "Annual Premium" }
    apiMocks.createChoiceOption.mockResolvedValue(created)
    apiMocks.updateChoiceOption.mockResolvedValue(updated)
    apiMocks.deleteChoiceOption.mockResolvedValue()

    renderPage()
    await screen.findByRole("heading", { name: "OL Premium Frequencies" })

    fireEvent.click(screen.getByRole("button", { name: /Add option/i }))
    const addDialog = within(screen.getByRole("dialog"))
    fireEvent.change(addDialog.getByRole("textbox", { name: /Code/i }), { target: { value: "ANNUAL" } })
    fireEvent.change(addDialog.getByRole("textbox", { name: /Display label/i }), { target: { value: "Annual" } })
    fireEvent.click(addDialog.getByRole("button", { name: /Save option/i }))
    await waitFor(() => expect(apiMocks.createChoiceOption).toHaveBeenCalledWith(expect.objectContaining({ choice_list: frequencyList.id, code: "ANNUAL", label: "Annual" })))
    expect(screen.getByText("Annual")).toBeInTheDocument()

    fireEvent.click(screen.getByRole("button", { name: "Edit Annual" }))
    const editDialog = within(screen.getByRole("dialog"))
    fireEvent.change(editDialog.getByRole("textbox", { name: /Display label/i }), { target: { value: "Annual Premium" } })
    fireEvent.click(editDialog.getByRole("button", { name: /Save option/i }))
    await waitFor(() => expect(apiMocks.updateChoiceOption).toHaveBeenCalledWith(created.id, expect.objectContaining({ label: "Annual Premium" })))

    fireEvent.click(screen.getByRole("button", { name: "Deactivate Annual Premium" }))
    await waitFor(() => expect(apiMocks.updateChoiceOption).toHaveBeenCalledWith(created.id, { is_active: false }))

    fireEvent.click(screen.getByRole("button", { name: "Delete Annual Premium" }))
    const confirmDialog = within(screen.getByRole("dialog"))
    fireEvent.click(confirmDialog.getByRole("button", { name: /Delete/i }))
    await waitFor(() => expect(apiMocks.deleteChoiceOption).toHaveBeenCalledWith(created.id))
  })

  it("supports catalog create, edit, deactivate, and delete actions", async () => {
    const created: ChoiceList = { ...modeList, id: "list-new", code: "OL_NEW_CHOICES", name: "New Catalog" }
    const updated: ChoiceList = { ...created, name: "Updated Catalog" }
    apiMocks.createChoiceList.mockResolvedValue(created)
    apiMocks.updateChoiceList.mockResolvedValue(updated)
    apiMocks.deleteChoiceList.mockResolvedValue()

    renderPage()
    await screen.findByRole("heading", { name: "OL Premium Frequencies" })

    fireEvent.click(screen.getByRole("button", { name: /Add dropdown catalog/i }))
    const addDialog = within(screen.getByRole("dialog"))
    fireEvent.change(addDialog.getByRole("textbox", { name: /^Code/i }), { target: { value: "OL_NEW_CHOICES" } })
    fireEvent.change(addDialog.getByRole("textbox", { name: /^Name/i }), { target: { value: "New Catalog" } })
    fireEvent.click(addDialog.getByRole("button", { name: /Save catalog/i }))
    await waitFor(() => expect(apiMocks.createChoiceList).toHaveBeenCalledWith(expect.objectContaining({ code: "OL_NEW_CHOICES", name: "New Catalog" })))

    expect(screen.getByRole("heading", { name: "New Catalog" })).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: /Edit catalog/i }))
    const editDialog = within(screen.getByRole("dialog"))
    fireEvent.change(editDialog.getByRole("textbox", { name: /^Name/i }), { target: { value: "Updated Catalog" } })
    fireEvent.click(editDialog.getByRole("button", { name: /Save catalog/i }))
    await waitFor(() => expect(apiMocks.updateChoiceList).toHaveBeenCalledWith(created.id, expect.objectContaining({ name: "Updated Catalog" })))

    expect(screen.getByRole("heading", { name: "Updated Catalog" })).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "Deactivate catalog Updated Catalog" }))
    await waitFor(() => expect(apiMocks.updateChoiceList).toHaveBeenCalledWith(created.id, { is_active: false }))

    fireEvent.click(screen.getByRole("button", { name: /^Delete catalog/ }))
    const confirmDialog = within(screen.getByRole("dialog"))
    fireEvent.click(confirmDialog.getByRole("button", { name: /Delete/i }))
    await waitFor(() => expect(apiMocks.deleteChoiceList).toHaveBeenCalled())
    expect(apiMocks.deleteChoiceList).toHaveBeenCalledWith(created.id)
  })

  it("hides mutation controls without the system_parameters.manage permission", async () => {
    accessMock.mockReturnValue(accessValue(false))
    renderPage()
    await screen.findByRole("heading", { name: "OL Premium Frequencies" })
    expect(screen.queryByRole("button", { name: /Add dropdown catalog/i })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /Add option/i })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /Edit catalog/i })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /Deactivate/i })).not.toBeInTheDocument()
  })
})
