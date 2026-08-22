import { Check, ChevronDown, Search } from "lucide-react"
import { useId, useMemo, useState } from "react"
import type { ChangeEvent, InputHTMLAttributes, ReactNode, SelectHTMLAttributes, TextareaHTMLAttributes } from "react"
import type { FilterOption, FormFieldProps } from "./types"

function useFieldId(name?: string, label?: string) {
  const generated = useId()
  return name ?? `${label?.toLowerCase().replace(/[^a-z0-9]+/g, "-") ?? "field"}-${generated}`
}

export function FieldLabel({ label, htmlFor, required, hint }: { label: string; htmlFor?: string; required?: boolean; hint?: string }) {
  return (
    <div className="mb-1.5 flex items-baseline justify-between gap-3">
      <label htmlFor={htmlFor} className="text-sm font-semibold text-[var(--foreground)]">
        {label}{required && <span className="ml-1 text-[var(--destructive)]" aria-label="required">*</span>}
      </label>
      {hint && <span className="text-[11px] text-[var(--muted-foreground)]">{hint}</span>}
    </div>
  )
}

function FieldMessage({ error, id }: { error?: string; id: string }) {
  return error ? <p id={`${id}-error`} className="mt-1 text-xs font-medium text-[var(--destructive)]" role="alert">{error}</p> : null
}

function fieldClass(readOnly = false, disabled = false, className = "") {
  return `h-10 w-full rounded-[10px] border bg-[var(--card)] px-3 text-sm text-[var(--foreground)] shadow-sm outline-none transition placeholder:text-[var(--muted-foreground)] focus:border-[var(--ring)] focus:ring-2 focus:ring-[color-mix(in_srgb,var(--ring)_18%,transparent)] ${readOnly ? "bg-[var(--muted)] text-[var(--muted-foreground)]" : ""} ${disabled ? "cursor-not-allowed opacity-60" : ""} ${className}`
}

export function TextInput({ label, name, required, hint, error, readOnly, className, ...props }: FormFieldProps & InputHTMLAttributes<HTMLInputElement>) {
  const id = useFieldId(name, label)
  return <div className="space-y-1"><FieldLabel label={label} htmlFor={id} required={required} hint={hint} /><input {...props} id={id} name={name} readOnly={readOnly} aria-invalid={Boolean(error)} aria-describedby={error ? `${id}-error` : undefined} className={fieldClass(readOnly, props.disabled, className)} /><FieldMessage error={error} id={id} /></div>
}

export function DecimalInput(props: FormFieldProps & InputHTMLAttributes<HTMLInputElement>) {
  return <TextInput {...props} type="number" inputMode="decimal" step="any" />
}

export function DateInput(props: FormFieldProps & InputHTMLAttributes<HTMLInputElement>) {
  return <TextInput {...props} type="date" />
}

export function SelectInput({ label, name, required, hint, error, className, children, ...props }: FormFieldProps & SelectHTMLAttributes<HTMLSelectElement> & { children: ReactNode }) {
  const id = useFieldId(name, label)
  return <div className="space-y-1"><FieldLabel label={label} htmlFor={id} required={required} hint={hint} /><div className="relative"><select {...props} id={id} name={name} aria-invalid={Boolean(error)} aria-describedby={error ? `${id}-error` : undefined} className={`${fieldClass(false, props.disabled, className)} appearance-none pr-9`}>{children}</select><ChevronDown className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-[var(--muted-foreground)]" size={16} aria-hidden="true" /></div><FieldMessage error={error} id={id} /></div>
}

export function SearchableSelect({ label, name, required, hint, error, options, value, onChange, placeholder = "Select an option", disabled, className }: FormFieldProps & { options: FilterOption[]; value?: string; onChange?: (value: string) => void; placeholder?: string }) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState("")
  const id = useFieldId(name, label)
  const filtered = useMemo(() => options.filter((option) => option.label.toLowerCase().includes(query.toLowerCase())), [options, query])
  const selected = options.find((option) => option.value === value)
  return <div className="relative space-y-1"><FieldLabel label={label} htmlFor={id} required={required} hint={hint} /><button id={id} type="button" disabled={disabled} aria-haspopup="listbox" aria-expanded={open} aria-invalid={Boolean(error)} onClick={() => setOpen((current) => !current)} className={`${fieldClass(false, disabled, className)} flex items-center justify-between text-left`}><span className={selected ? "text-[var(--foreground)]" : "text-[var(--muted-foreground)]"}>{selected?.label ?? placeholder}</span><ChevronDown size={16} aria-hidden="true" /></button>{open && <div className="absolute z-[70] mt-1 w-full overflow-hidden rounded-[10px] border bg-[var(--popover)] p-1 shadow-lg" role="listbox" aria-label={label}><div className="flex items-center gap-2 border-b px-2"><Search size={14} className="text-[var(--muted-foreground)]" aria-hidden="true" /><input autoFocus value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search" className="h-9 w-full bg-transparent text-sm outline-none" aria-label={`Search ${label}`} /></div><div className="max-h-48 overflow-auto py-1">{filtered.map((option) => <button key={option.value} type="button" role="option" aria-selected={option.value === value} className="flex w-full items-center justify-between rounded-md px-2 py-2 text-left text-sm hover:bg-[var(--secondary)]" onClick={() => { onChange?.(option.value); setOpen(false); setQuery("") }}>{option.label}{option.value === value && <Check size={15} aria-hidden="true" />}</button>)}{filtered.length === 0 && <p className="px-2 py-3 text-center text-xs text-[var(--muted-foreground)]">No options found.</p>}</div></div>}<FieldMessage error={error} id={id} /></div>
}

export function TextareaInput({ label, name, required, hint, error, readOnly, className, ...props }: FormFieldProps & TextareaHTMLAttributes<HTMLTextAreaElement>) {
  const id = useFieldId(name, label)
  return <div className="space-y-1"><FieldLabel label={label} htmlFor={id} required={required} hint={hint} /><textarea {...props} id={id} name={name} readOnly={readOnly} aria-invalid={Boolean(error)} aria-describedby={error ? `${id}-error` : undefined} className={`min-h-24 w-full resize-y rounded-[10px] border bg-[var(--card)] px-3 py-2.5 text-sm text-[var(--foreground)] shadow-sm outline-none transition placeholder:text-[var(--muted-foreground)] focus:border-[var(--ring)] focus:ring-2 focus:ring-[color-mix(in_srgb,var(--ring)_18%,transparent)] ${readOnly ? "bg-[var(--muted)] text-[var(--muted-foreground)]" : ""} ${className ?? ""}`} /><FieldMessage error={error} id={id} /></div>
}

export function ReadOnlyField({ label, value, hint, required, className }: { label: string; value: ReactNode; hint?: string; required?: boolean; className?: string }) {
  return <div className={className}><FieldLabel label={label} hint={hint} required={required} /><div className="ol-quote-readonly flex h-10 items-center rounded-[10px] border px-3 text-sm font-semibold" aria-readonly="true">{value || "—"}</div></div>
}

export function Toggle({ label, checked, onChange, disabled, hint }: { label: string; checked: boolean; onChange: (checked: boolean) => void; disabled?: boolean; hint?: string }) {
  const id = useId()
  return <div className="flex items-center justify-between gap-3"><div><label htmlFor={id} className="text-sm font-semibold">{label}</label>{hint && <p className="text-xs text-[var(--muted-foreground)]">{hint}</p>}</div><button id={id} type="button" role="switch" aria-checked={checked} disabled={disabled} onClick={() => onChange(!checked)} className={`relative h-6 w-11 rounded-full transition ${checked ? "bg-[var(--primary)]" : "bg-[var(--muted-foreground)]/35"} ${disabled ? "cursor-not-allowed opacity-50" : ""}`}><span className={`absolute top-1 h-4 w-4 rounded-full bg-white shadow transition ${checked ? "left-6" : "left-1"}`} /></button></div>
}

export function FormGrid({ children, columns = 2 }: { children: ReactNode; columns?: 1 | 2 | 3 | 4 }) {
  return <div className={`grid gap-4 ${columns === 1 ? "grid-cols-1" : columns === 2 ? "grid-cols-1 md:grid-cols-2" : columns === 3 ? "grid-cols-1 md:grid-cols-2 xl:grid-cols-3" : "grid-cols-1 md:grid-cols-2 xl:grid-cols-4"}`}>{children}</div>
}

export function normalizeInputValue(event: ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) {
  return event.target.value
}
