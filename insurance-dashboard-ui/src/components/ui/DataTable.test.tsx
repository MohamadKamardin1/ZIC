import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"
import { DataTable } from "./DataTable"
import type { FilterValues } from "./FilterBar"
import type { TableMetadata } from "./types"

type Row = Record<string, unknown> & { id: string; name: string; status: string }

const metadata: TableMetadata<Row> = { pageSize: 1, columns: [{ key: "name", label: "Name", field: "name", sortable: true }, { key: "status", label: "Status", field: "status" }] }
const rows: Row[] = [{ id: "1", name: "Alpha", status: "DRAFT" }]

describe("DataTable", () => {
  it("fetches server-side pagination, sorting, search, and filters", async () => {
    const fetcher = vi.fn().mockResolvedValue({ results: rows, count: 3, page: 1, page_size: 1 })
    const { rerender } = render(<DataTable<Row> metadata={metadata} fetcher={fetcher} filters={{ status: "DRAFT" }} caption="Quotation table" />)
    await waitFor(() => expect(screen.getByText("Alpha")).toBeInTheDocument())
    expect(fetcher).toHaveBeenCalledWith(expect.objectContaining({ page: 1, pageSize: 1, filters: { status: "DRAFT" } }))

    fireEvent.change(screen.getByLabelText("Search records"), { target: { value: "Alpha" } })
    await waitFor(() => expect(fetcher).toHaveBeenLastCalledWith(expect.objectContaining({ search: "Alpha", page: 1 })))

    fireEvent.click(screen.getByRole("button", { name: "Name" }))
    await waitFor(() => expect(fetcher).toHaveBeenLastCalledWith(expect.objectContaining({ ordering: "name" })))

    const next = screen.getByRole("button", { name: "Next" })
    expect(next).toBeEnabled()
    fireEvent.click(next)
    await waitFor(() => expect(fetcher).toHaveBeenLastCalledWith(expect.objectContaining({ page: 2 })))

    const nextFilters: FilterValues = { status: "FINALIZED", quote_date: { from: "2026-01-01", to: "2026-01-31" } }
    rerender(<DataTable<Row> metadata={metadata} fetcher={fetcher} filters={nextFilters} caption="Quotation table" />)
    await waitFor(() => expect(fetcher).toHaveBeenLastCalledWith(expect.objectContaining({ filters: { status: "FINALIZED", quote_date: "2026-01-01,2026-01-31" } })))
    expect(screen.getByRole("table")).toHaveAccessibleName("Quotation table")
  })

  it("gates row actions by permission and record state", async () => {
    const fetcher = vi.fn().mockResolvedValue({ results: rows, count: 1 })
    const onEdit = vi.fn()
    render(<DataTable<Row> metadata={metadata} fetcher={fetcher} actions={[{ key: "edit", label: "Edit", permission: "ol_quotations.update", isVisible: (row) => row.status === "DRAFT", onSelect: onEdit }]} permissions={["ol_quotations.update"]} />)
    await waitFor(() => expect(screen.getByRole("button", { name: "Actions for row 1" })).toBeInTheDocument())
    fireEvent.click(screen.getByRole("button", { name: "Actions for row 1" }))
    await waitFor(() => expect(screen.getByRole("button", { name: "Edit" })).toBeInTheDocument())
    fireEvent.click(screen.getByRole("button", { name: "Edit" }))
    await waitFor(() => expect(onEdit).toHaveBeenCalledWith(rows[0]))
    expect(screen.getByRole("table")).toBeInTheDocument()
  })
})
