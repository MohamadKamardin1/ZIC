import type { DetailedHTMLProps, HTMLAttributes, Ref } from "react"

type CustomEl = DetailedHTMLProps<HTMLAttributes<HTMLElement> & { ref?: Ref<HTMLElement> }, HTMLElement>

declare module "react" {
  namespace JSX {
    interface IntrinsicElements {
      "zic-policies-card": CustomEl
      "zic-claims-card": CustomEl
      "zic-partners-card": CustomEl
      "zic-debited-gauge": CustomEl
      "zic-quotations-chart": CustomEl
      "zic-notifications-panel": CustomEl
      "zic-todo-leads": CustomEl
      "zic-todo": CustomEl
      "zic-leads": CustomEl
    }
  }
}
