import { useQuery, useQueryClient } from "@tanstack/react-query"
import { Check, ChevronDown, ExternalLink, Loader2, Plus, Search, X } from "lucide-react"
import { useEffect, useMemo, useRef, useState, type CSSProperties, type ReactNode } from "react"
import { createPortal } from "react-dom"
import { useAccess } from "../../lib/access"
import { ApiClientError, request } from "../../lib/apiClient"
import { useToast } from "./Toast"
import { FieldLabel } from "./FormControls"
import { QuickCreateModal, type QuickCreateOption } from "./QuickCreateModal"
import type { FormFieldProps, FilterOption } from "./types"

export type SmartOption = FilterOption & {
  meta?: Record<string, unknown>
}

export type SmartSelectEntity = string

export const OPTION_CREATE_PERMISSIONS: Record<string, string> = {
  "identity-types": "system_parameters.manage",
  locations: "ol_parameters.create",
  agents: "partners.create",
  products: "ol_parameters.create",
  "plan-types": "ol_parameters.create",
  "payment-frequencies": "system_parameters.manage",
  "quote-bases": "system_parameters.manage",
  "premium-factors": "system_parameters.manage",
  "member-relations": "system_parameters.manage",
  "cover-types": "system_parameters.manage",
  "payment-modes": "system_parameters.manage",
  "investment-funds": "ol_parameters.create",
  "investment-fund-types": "ol_parameters.create",
  riders: "ol_parameters.create",
  "benefit-types": "system_parameters.manage",
  currencies: "system_parameters.manage",
}

export type SmartSelectProps = FormFieldProps & {
  entity: SmartSelectEntity
  value?: string
  values?: string[]
  onChange?: (value: string) => void
  onOptionChange?: (option: SmartOption) => void
  onValuesChange?: (values: string[]) => void
  placeholder?: string
  pageSize?: number
  manageHref?: string
  manageLabel?: string
  createPermission?: string
  multiple?: boolean
  disabled?: boolean
  emptyEntityLabel?: string
  className?: string
}

type OptionListPayload = {
  items?: unknown[]
  results?: unknown[]
  options?: unknown[]
  count?: number
  total?: number
  has_next?: boolean
  hasNext?: boolean
}

function prettifyEntity(entity: string): string {
  return entity
    .replace(/[-_]/g, " ")
    .replace(/\b\w/g, (character) => character.toUpperCase())
    .replace(/Types$/, "Types")
    .replace(/s$/, "")
}

function normalizeOption(value: unknown): SmartOption | null {
  if (!value || typeof value !== "object") return null
  const record = value as Record<string, unknown>
  const optionValue = record.value ?? record.id ?? record.code
  const label = record.label ?? record.name ?? record.display_name ?? record.displayName
  if (optionValue === null || optionValue === undefined || !label) return null
  const meta = record.meta && typeof record.meta === "object" && !Array.isArray(record.meta)
    ? record.meta as Record<string, unknown>
    : record
  return { value: String(optionValue), label: String(label), meta }
}

function normalizeOptions(payload: unknown): SmartOption[] {
  if (Array.isArray(payload)) return payload.map(normalizeOption).filter((item): item is SmartOption => Boolean(item))
  if (!payload || typeof payload !== "object") return []
  const record = payload as OptionListPayload
  const items = record.items ?? record.results ?? record.options ?? []
  return Array.isArray(items) ? items.map(normalizeOption).filter((item): item is SmartOption => Boolean(item)) : []
}

function getPayloadTotal(payload: unknown, fallback: number): number {
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) return fallback
  const record = payload as OptionListPayload
  return Number(record.count ?? record.total ?? fallback)
}

function getErrorMessage(error: unknown): string {
  if (error instanceof ApiClientError) return error.message
  if (error instanceof Error) return error.message
  return "Unable to load options."
}

function useDebouncedValue(value: string, delay = 250): string {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const timer = window.setTimeout(() => setDebounced(value), delay)
    return () => window.clearTimeout(timer)
  }, [delay, value])
  return debounced
}

export function SmartSelect({
  entity,
  value,
  values = [],
  onChange,
  onOptionChange,
  onValuesChange,
  label,
  name,
  required,
  hint,
  error,
  placeholder = "Select an option",
  pageSize = 30,
  manageHref,
  manageLabel = "Manage…",
  createPermission,
  multiple = false,
  disabled = false,
  emptyEntityLabel,
  className = "",
}: SmartSelectProps) {
  const { access, isSuperAdmin, hasPermission } = useAccess()
  const { toast } = useToast()
  const queryClient = useQueryClient()
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState("")
  const [quickCreateOpen, setQuickCreateOpen] = useState(false)
  const [createdOptions, setCreatedOptions] = useState<SmartOption[]>([])
  const buttonRef = useRef<HTMLButtonElement>(null)
  const menuRef = useRef<HTMLDivElement>(null)
  const debouncedQuery = useDebouncedValue(query)
  const entityLabel = emptyEntityLabel ?? prettifyEntity(entity)
  const permissionCode = createPermission ?? OPTION_CREATE_PERMISSIONS[entity]
  const canCreate = isSuperAdmin || Boolean(permissionCode && hasPermission?.(permissionCode))
  const hasAccessMetadata = isSuperAdmin || access.permissions.length > 0 || access.visibleModules.length > 0

  const optionsQuery = useQuery({
    queryKey: ["ol-options", entity, debouncedQuery, pageSize],
    queryFn: () => request<OptionListPayload | unknown[]>(`/api/v1/ol/options/${encodeURIComponent(entity)}/?q=${encodeURIComponent(debouncedQuery)}&page=1&page_size=${pageSize}`),
    enabled: !disabled,
    staleTime: 30_000,
  })
  const options = useMemo(() => {
    const remoteOptions = normalizeOptions(optionsQuery.data)
    const merged = new Map<string, SmartOption>()
    remoteOptions.forEach((option) => merged.set(option.value, option))
    createdOptions.forEach((option) => merged.set(option.value, option))
    return Array.from(merged.values())
  }, [createdOptions, optionsQuery.data])
  const total = getPayloadTotal(optionsQuery.data, options.length)
  const selectedValues = multiple ? values : value ? [value] : []
  const selectedOptions = selectedValues.map((selectedValue) => options.find((option) => option.value === selectedValue)).filter((item): item is SmartOption => Boolean(item))
  const selectedLabel = multiple
    ? selectedOptions.length ? selectedOptions.map((option) => option.label).join(", ") : placeholder
    : selectedOptions[0]?.label ?? placeholder

  useEffect(() => {
    if (!open) return undefined
    const onDocumentClick = (event: MouseEvent) => {
      const target = event.target as Node
      if (!buttonRef.current?.contains(target) && !menuRef.current?.contains(target)) setOpen(false)
    }
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false)
    }
    document.addEventListener("mousedown", onDocumentClick)
    document.addEventListener("keydown", onKeyDown)
    return () => {
      document.removeEventListener("mousedown", onDocumentClick)
      document.removeEventListener("keydown", onKeyDown)
    }
  }, [open])

  const menuStyle = useMemo<CSSProperties>(() => {
    const rect = buttonRef.current?.getBoundingClientRect()
    return {
      position: "fixed",
      top: (rect?.bottom ?? 0) + 4,
      left: rect?.left ?? 0,
      width: rect?.width ?? "min(420px, calc(100vw - 2rem))",
      zIndex: 100,
    }
  }, [open])

  const choose = (option: SmartOption) => {
    if (multiple) {
      const next = selectedValues.includes(option.value)
        ? selectedValues.filter((selectedValue) => selectedValue !== option.value)
        : [...selectedValues, option.value]
      onValuesChange?.(next)
      return
    }
    onOptionChange?.(option)
    onChange?.(option.value)
    setOpen(false)
    setQuery("")
  }

  const clear = () => {
    if (multiple) onValuesChange?.([])
    else onChange?.("")
  }

  const handleCreated = (option: QuickCreateOption) => {
    setCreatedOptions((current) => [...current.filter((item) => item.value !== option.value), option])
    queryClient.invalidateQueries({ queryKey: ["ol-options", entity] })
    if (multiple) onValuesChange?.([...selectedValues, option.value])
    else {
      onOptionChange?.(option)
      onChange?.(option.value)
    }
    setQuickCreateOpen(false)
    toast({ title: `${entityLabel} created`, message: `${option.label} is now selected.`, tone: "success" })
  }

  return (
    <div className="space-y-1">
      <FieldLabel label={label} htmlFor={name} required={required} hint={hint} />
      <div className="flex items-start gap-2">
        <div className="relative min-w-0 flex-1">
          <button
            ref={buttonRef}
            id={name}
            type="button"
            disabled={disabled}
            aria-haspopup="listbox"
            aria-expanded={open}
            aria-invalid={Boolean(error)}
            aria-describedby={error ? `${name}-error` : undefined}
            onClick={() => setOpen((current) => !current)}
            className={`flex h-10 w-full items-center justify-between rounded-[10px] border bg-[var(--card)] px-3 text-left text-sm text-[var(--foreground)] shadow-sm outline-none transition focus:border-[var(--ring)] focus:ring-2 focus:ring-[color-mix(in_srgb,var(--ring)_18%,transparent)] disabled:cursor-not-allowed disabled:opacity-60 ${className}`}
          >
            <span className={`min-w-0 truncate ${selectedOptions.length ? "text-[var(--foreground)]" : "text-[var(--muted-foreground)]"}`}>{selectedLabel}</span>
            <ChevronDown size={16} className="ml-2 shrink-0 text-[var(--muted-foreground)]" aria-hidden="true" />
          </button>
          {open && createPortal(
            <div ref={menuRef} style={menuStyle} className="overflow-hidden rounded-[10px] border bg-[var(--popover)] p-1 shadow-2xl" role="listbox" aria-label={label} aria-multiselectable={multiple || undefined}>
              <div className="flex items-center gap-2 border-b px-2">
                <Search size={14} className="shrink-0 text-[var(--muted-foreground)]" aria-hidden="true" />
                <input autoFocus value={query} onChange={(event) => setQuery(event.target.value)} placeholder={`Search ${entityLabel.toLowerCase()}`} className="h-9 w-full bg-transparent text-sm outline-none" aria-label={`Search ${label}`} />
                {query && <button type="button" aria-label="Clear search" onClick={() => setQuery("")} className="rounded p-1 text-[var(--muted-foreground)] hover:bg-[var(--secondary)]"><X size={14} aria-hidden="true" /></button>}
              </div>
              <div className="max-h-60 overflow-auto py-1">
                {optionsQuery.isLoading && <div className="flex items-center justify-center gap-2 px-3 py-4 text-xs text-[var(--muted-foreground)]" role="status"><Loader2 size={14} className="animate-spin" aria-hidden="true" /> Loading options…</div>}
                {optionsQuery.isError && <p className="px-3 py-4 text-center text-xs text-[var(--destructive)]" role="alert">{getErrorMessage(optionsQuery.error)}</p>}
                {!optionsQuery.isLoading && !optionsQuery.isError && options.length === 0 && <p className="px-3 py-4 text-center text-xs text-[var(--muted-foreground)]">No results found. Use + to add a new {entityLabel.toLowerCase()}.</p>}
                {!optionsQuery.isLoading && !optionsQuery.isError && options.map((option) => {
                  const selected = selectedValues.includes(option.value)
                  return <button key={option.value} type="button" role="option" aria-selected={selected} onClick={() => choose(option)} className="flex w-full items-center justify-between gap-3 rounded-md px-3 py-2 text-left text-sm hover:bg-[var(--secondary)]"><span className="min-w-0 truncate">{option.label}</span>{selected && <Check size={15} className="shrink-0 text-[var(--primary)]" aria-hidden="true" />}</button>
                })}
              </div>
              {total > options.length && <p className="border-t px-3 py-2 text-[11px] text-[var(--muted-foreground)]">Showing {options.length} of {total} results. Search to refine.</p>}
            </div>,
            document.body,
          )}
        </div>
        {hasAccessMetadata && canCreate && <button type="button" disabled={disabled} onClick={() => setQuickCreateOpen(true)} className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-[10px] border border-[var(--border)] bg-[var(--card)] text-[var(--primary)] shadow-sm transition hover:bg-[var(--secondary)] disabled:cursor-not-allowed disabled:opacity-60" aria-label={`Add new ${entityLabel}`} title={`Add new ${entityLabel}`}><Plus size={17} aria-hidden="true" /></button>}
      </div>
      {(selectedOptions.length > 0 || (multiple && selectedValues.length > 0)) && <div className="flex flex-wrap items-center gap-1.5">{selectedOptions.map((option) => <span key={option.value} className="inline-flex max-w-full items-center gap-1 rounded-full bg-[var(--secondary)] px-2.5 py-1 text-xs text-[var(--foreground)]"><span className="max-w-[18rem] truncate">{option.label}</span></span>)}<button type="button" onClick={clear} className="text-xs font-semibold text-[var(--muted-foreground)] underline-offset-2 hover:text-[var(--foreground)] hover:underline">Clear</button></div>}
      {manageHref && hasAccessMetadata && canCreate && <a href={manageHref} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-xs font-semibold text-[var(--primary)] hover:underline">{manageLabel}<ExternalLink size={12} aria-hidden="true" /></a>}
      {error && <p id={`${name}-error`} className="mt-1 text-xs font-medium text-[var(--destructive)]" role="alert">{error}</p>}
      {optionsQuery.isError && !open && <p className="text-xs text-[var(--destructive)]" role="alert">{getErrorMessage(optionsQuery.error)}</p>}
      <QuickCreateModal open={quickCreateOpen} entity={entity} entityLabel={entityLabel} permissionCode={permissionCode} onClose={() => setQuickCreateOpen(false)} onCreated={handleCreated} />
    </div>
  )
}

export function SmartMultiSelect(props: Omit<SmartSelectProps, "multiple"> & { values: string[]; onValuesChange: (values: string[]) => void }) {
  return <SmartSelect {...props} multiple values={props.values} onValuesChange={props.onValuesChange} />
}

export type { ReactNode }
