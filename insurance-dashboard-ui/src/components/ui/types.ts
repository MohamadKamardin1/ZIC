import type { ReactNode } from "react"

export type TableColumn<T> = {
  key: string
  label: string
  field?: keyof T
  sortable?: boolean
  width?: string
  align?: "left" | "center" | "right"
  render?: (value: unknown, row: T, index: number) => ReactNode
}

export type TableResponse<T> = {
  results: T[]
  count: number
  next?: string | null
  previous?: string | null
  page?: number
  page_size?: number
}

export type TableMetadata<T> = {
  columns: TableColumn<T>[]
  defaultOrdering?: string
  pageSize?: number
  totalLabel?: string
}

export type FilterOption = { label: string; value: string }

export type FilterDefinition = {
  key: string
  label: string
  type: "text" | "select" | "multi-select" | "date-range"
  options?: FilterOption[]
  placeholder?: string
}

export type RowAction<T> = {
  key: string
  label: string
  permission?: string
  tone?: "default" | "danger"
  isVisible?: (row: T) => boolean
  onSelect: (row: T) => void
}

export type FormFieldProps = {
  label: string
  name?: string
  required?: boolean
  hint?: string
  error?: string
  disabled?: boolean
  readOnly?: boolean
  className?: string
}
