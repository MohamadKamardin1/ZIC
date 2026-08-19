import { fireEvent, render, screen } from "@testing-library/react"
import { useState } from "react"
import { describe, expect, it, vi } from "vitest"
import { EditableGrid } from "./EditableGrid"

type Rate = { id: string; description: string; rate: number }

function renderGrid(onChange = vi.fn()) {
  return render(<EditableGrid<Rate> rows={[{ id: "1", description: "Year 1", rate: 40 }, { id: "2", description: "Year 2", rate: 60 }]} columns={[{ key: "description", label: "Description", render: (row, _index, update) => <input aria-label="Description" value={row.description} onChange={(event) => update({ description: event.target.value })} /> }, { key: "rate", label: "Rate (%)", render: (row, _index, update) => <input aria-label="Rate" type="number" value={row.rate} onChange={(event) => update({ rate: Number(event.target.value) })} /> }]} getRowId={(row) => row.id} createRow={() => ({ id: "3", description: "New row", rate: 0 })} onChange={onChange} validateRow={(row): Record<string, string> => row.description ? {} : { description: "Description is required." }} total={{ label: "Rate total", getValue: (row) => row.rate, target: 100, format: (value) => `${value.toFixed(2)}%` }} />)
}

function ControlledGrid() {
  const [rows, setRows] = useState<Rate[]>([{ id: "1", description: "Year 1", rate: 40 }, { id: "2", description: "Year 2", rate: 60 }])
  return <EditableGrid<Rate> rows={rows} columns={[{ key: "description", label: "Description", render: (row, _index, update) => <input aria-label="Description" value={row.description} onChange={(event) => update({ description: event.target.value })} /> }, { key: "rate", label: "Rate (%)", render: (row, _index, update) => <input aria-label="Rate" type="number" value={row.rate} onChange={(event) => update({ rate: Number(event.target.value) })} /> }]} getRowId={(row) => row.id} createRow={() => ({ id: "3", description: "New row", rate: 0 })} onChange={setRows} validateRow={(row): Record<string, string> => row.description ? {} : { description: "Description is required." }} total={{ label: "Rate total", getValue: (row) => row.rate, target: 100, format: (value) => `${value.toFixed(2)}%` }} />
}

describe("EditableGrid", () => {
  it("shows a valid total and supports adding and removing rows", () => {
    const onChange = vi.fn()
    renderGrid(onChange)
    expect(screen.getByText("100.00%")).toBeInTheDocument()
    expect(screen.getByText("/ 100.00%")).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "Add row" }))
    expect(onChange).toHaveBeenCalledWith(expect.arrayContaining([expect.objectContaining({ id: "3" })]))
    fireEvent.click(screen.getByRole("button", { name: "Remove row 1" }))
    expect(onChange).toHaveBeenCalledWith(expect.arrayContaining([expect.objectContaining({ id: "2" })]))
  })

  it("marks the total invalid and exposes inline validation", () => {
    const onChange = vi.fn()
    render(<ControlledGrid />)
    fireEvent.change(screen.getAllByLabelText("Rate")[0], { target: { value: "20" } })
    expect(screen.getByText("80.00%")).toBeInTheDocument()
    expect(screen.getByText("/ 100.00%")).toBeInTheDocument()
    fireEvent.change(screen.getAllByLabelText("Description")[0], { target: { value: "" } })
    expect(screen.getByRole("alert")).toHaveTextContent("Description is required.")
  })
})
