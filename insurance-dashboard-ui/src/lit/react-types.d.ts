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
      "onboarding-status-timeline": CustomEl
      "onboarding-event-feed": CustomEl
      "onboarding-document-panel": CustomEl
      "onboarding-workflow-actions": CustomEl
      "onboarding-stats-card": CustomEl
    }
  }
}
