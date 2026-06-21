import { useEffect, useRef } from "react"

/**
 * Sets object/array props as DOM *properties* on a Lit custom element.
 * React would otherwise stringify complex values onto attributes.
 */
export function useLitProps<T extends HTMLElement = HTMLElement>(props: Record<string, unknown>) {
  const ref = useRef<T>(null)
  useEffect(() => {
    const el = ref.current as unknown as Record<string, unknown> | null
    if (!el) return
    for (const key in props) {
      el[key] = props[key]
    }
  }, [props])
  return ref
}
