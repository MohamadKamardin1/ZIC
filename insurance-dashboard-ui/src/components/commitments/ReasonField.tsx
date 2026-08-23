import { useState } from "react"
import { TextareaInput } from "../ui/FormControls"

export const DEFAULT_REASON_MIN_LENGTH = 8
export const DEFAULT_REASON_PLACEHOLDER = "Record the business reason for this action. Reasons are audited with your name."

export function reasonError(value: string, minLength = DEFAULT_REASON_MIN_LENGTH): string | null {
  const trimmed = (value ?? "").trim()
  if (!trimmed) return "A reason is required."
  if (trimmed.length < minLength) return `Provide at least ${minLength} characters.`
  return null
}

export interface ReasonFieldProps {
  value: string
  onChange: (value: string) => void
  label?: string
  required?: boolean
  minLength?: number
  placeholder?: string
  hint?: string
  disabled?: boolean
  /** External trigger to reveal inline errors (e.g., failed submit attempt). */
  showError?: boolean
  testId?: string
}

/**
 * Mandatory reason textarea for lifecycle actions.
 *
 * Reveals an inline, accessible error below the field when the reason is
 * missing or shorter than ``minLength``; the error clears as the user types.
 */
export function ReasonField({
  value,
  onChange,
  label = "Reason",
  required = true,
  minLength = DEFAULT_REASON_MIN_LENGTH,
  placeholder = DEFAULT_REASON_PLACEHOLDER,
  hint,
  disabled = false,
  showError = false,
  testId = "commitment-reason-field",
}: ReasonFieldProps) {
  const [touched, setTouched] = useState(false)
  const error = reasonError(value, minLength)
  const displayError = (touched || showError) && error ? error : undefined

  return (
    <div data-testid={testId}>
      <TextareaInput
        label={label}
        name="reason"
        required={required}
        hint={hint}
        value={value}
        error={displayError}
        disabled={disabled}
        placeholder={placeholder}
        minLength={required ? minLength : undefined}
        aria-describedby={undefined}
        onChange={(event) => onChange(event.target.value)}
        onBlur={() => setTouched(true)}
      />
    </div>
  )
}

export default ReasonField