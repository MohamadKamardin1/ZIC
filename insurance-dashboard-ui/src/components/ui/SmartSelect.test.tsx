import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { useState } from "react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { SmartSelect } from "./SmartSelect"
import { ToastProvider } from "./Toast"
import { ApiClientError, request } from "../../lib/apiClient"

vi.mock("../../lib/access", () => ({
  useAccess: () => ({
    access: { permissions: [{ module: "ol_parameters", action: "create" }], visibleModules: ["ol_parameters"], groups: [] },
    isLoading: false,
    isError: false,
    isSuperAdmin: true,
    canAccess: () => true,
    hasPermission: (permission: string) => permission === "ol_parameters.create",
  }),
}))

vi.mock("../../lib/apiClient", async () => {
  const actual = await vi.importActual<typeof import("../../lib/apiClient")>("../../lib/apiClient")
  return { ...actual, request: vi.fn() }
})

const mockedRequest = vi.mocked(request)

function ControlledSmartSelect(props: Partial<React.ComponentProps<typeof SmartSelect>>) {
  const [value, setValue] = useState("")
  return <SmartSelect entity="locations" label="Location" name="location" {...props} value={value} onChange={(next) => { setValue(next); props.onChange?.(next) }} />
}

function renderSmartSelect(props: Partial<React.ComponentProps<typeof SmartSelect>> = {}, controlled = false) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const field = controlled ? <ControlledSmartSelect {...props} /> : <SmartSelect entity="locations" label="Location" name="location" {...props} />
  return render(<QueryClientProvider client={client}><ToastProvider>{field}</ToastProvider></QueryClientProvider>)
}

describe("SmartSelect", () => {
  beforeEach(() => {
    mockedRequest.mockReset()
    mockedRequest.mockResolvedValue({ items: [{ value: "location-1", label: "MALINDI — Malindi" }], total: 1 })
  })

  it("renders backend labels and never renders the UUID as the option text", async () => {
    renderSmartSelect()
    fireEvent.click(screen.getByRole("button", { name: "Location" }))
    await waitFor(() => expect(screen.getByRole("option", { name: "MALINDI — Malindi" })).toBeInTheDocument())
    expect(screen.queryByText("location-1")).not.toBeInTheDocument()
  })

  it("hides the plus control when the create permission is absent", () => {
    renderSmartSelect({ createPermission: "ol_parameters.update" })
    expect(screen.queryByRole("button", { name: "Add new Location" })).not.toBeInTheDocument()
  })

  it("quick-creates an option and auto-selects the returned labeled record", async () => {
    const onChange = vi.fn()
    mockedRequest.mockImplementation(async (path) => {
      if (path.includes("quick-create-schema")) return { entity: "locations", permission: "ol_parameters.create", fields: [{ name: "code", required: true }, { name: "name", required: true }] }
      if (path.includes("quick-create/")) return { entity: "locations", option: { value: "location-new", label: "NEW — New Location" } }
      return { items: [], total: 0 }
    })
    renderSmartSelect({ onChange }, true)
    fireEvent.click(screen.getByRole("button", { name: "Add new Location" }))
    await waitFor(() => expect(screen.getByLabelText(/Code/)).toBeInTheDocument())
    fireEvent.change(screen.getByLabelText(/Code/), { target: { value: "NEW" } })
    fireEvent.change(screen.getByLabelText(/Name/), { target: { value: "New Location" } })
    fireEvent.click(screen.getByRole("button", { name: "Create option" }))
    await waitFor(() => expect(onChange).toHaveBeenCalledWith("location-new"))
    expect(screen.getAllByText("NEW — New Location").length).toBeGreaterThan(0)
    expect(screen.getByText("Location created and selected")).toBeInTheDocument()
  })

  it("opens quick-create from the keyboard and exposes the permission-gated manage link", async () => {
    mockedRequest.mockImplementation(async (path) => {
      if (path.includes("quick-create-schema")) return { entity: "locations", permission: "ol_parameters.create", fields: [{ name: "code", required: true }, { name: "name", required: true }] }
      return { items: [], total: 0 }
    })
    renderSmartSelect()
    const addButton = screen.getByRole("button", { name: "Add new Location" })
    addButton.focus()
    fireEvent.keyDown(addButton, { key: "Enter" })
    await waitFor(() => expect(screen.getByLabelText(/Code/)).toBeInTheDocument())
    expect(screen.getByRole("link", { name: "Manage…" })).toHaveAttribute("href", "/ordinary-life/parameters")
    expect(screen.getByText(/This creates a minimal record\. Complete full configuration in/)).toBeInTheDocument()
    expect(screen.getByRole("link", { name: "Default Setup" })).toHaveAttribute("href", "/ordinary-life/parameters")
  })

  it("shows duplicate field errors and a duplicate warning", async () => {
    mockedRequest.mockImplementation(async (path) => {
      if (path.includes("quick-create-schema")) return { entity: "locations", permission: "ol_parameters.create", fields: [{ name: "code", required: true }, { name: "name", required: true }] }
      if (path.includes("quick-create/")) throw new ApiClientError({ status: 400, code: "DUPLICATE", message: "A location with this code already exists.", fieldErrors: { code: ["A location with this code already exists."] } })
      return { items: [], total: 0 }
    })
    renderSmartSelect()
    fireEvent.click(screen.getByRole("button", { name: "Add new Location" }))
    await waitFor(() => expect(screen.getByLabelText(/Code/)).toBeInTheDocument())
    fireEvent.change(screen.getByLabelText(/Code/), { target: { value: "DUP" } })
    fireEvent.change(screen.getByLabelText(/Name/), { target: { value: "Duplicate" } })
    fireEvent.click(screen.getByRole("button", { name: "Create option" }))
    await waitFor(() => expect(screen.getByText(/Duplicate detected:/)).toBeInTheDocument())
    expect(screen.getByText("A location with this code already exists.")).toBeInTheDocument()
  })
})
