import { LitElement, css, html } from "lit"
import { customElement, property } from "lit/decorators.js"

const FLOW = [
  { key: "DRAFT", label: "Draft", hint: "Application started" },
  { key: "SUBMITTED", label: "Submitted", hint: "Ready for review" },
  { key: "UNDER_REVIEW", label: "Review", hint: "Partner verification" },
  { key: "COMPLIANCE_CHECK", label: "Compliance", hint: "Risk screening" },
  { key: "APPROVED", label: "Approved", hint: "Approval granted" },
  { key: "CONVERTED", label: "Converted", hint: "Partner created" },
]

const ORDER: Record<string, number> = {
  DRAFT: 0,
  SUBMITTED: 1,
  UNDER_REVIEW: 2,
  PENDING_DOCUMENTS: 2,
  COMPLIANCE_CHECK: 3,
  APPROVED: 4,
  CONVERTED: 5,
}

@customElement("onboarding-status-timeline")
export class OnboardingStatusTimeline extends LitElement {
  @property({ type: String }) status = "DRAFT"
  @property({ type: String }) applicationNumber = ""
  @property({ type: Boolean }) compact = false

  static styles = css`
    :host { display: block; font-family: var(--font-sans, Inter, sans-serif); color: var(--foreground, #0f172a); }
    .shell { background: var(--card, #fff); border: 1px solid var(--border, #e2e8f0); border-radius: var(--radius, 12px); padding: 20px; box-shadow: 0 1px 3px rgba(15,23,42,.05); }
    .header { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 22px; }
    h3 { margin: 0; font-size: 15px; font-weight: 700; letter-spacing: -.01em; }
    .number { color: var(--muted-foreground, #64748b); font: 600 12px/1.2 ui-monospace, SFMono-Regular, Menlo, monospace; }
    .rail { display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 0; }
    .step { position: relative; text-align: center; min-width: 0; }
    .step:not(:last-child)::after { content: ""; position: absolute; height: 2px; top: 13px; left: calc(50% + 14px); right: calc(-50% + 14px); background: var(--border, #e2e8f0); z-index: 0; }
    .step.complete:not(:last-child)::after { background: var(--color-feedback-success, #16a34a); }
    .dot { position: relative; z-index: 1; width: 26px; height: 26px; margin: 0 auto 9px; display: grid; place-items: center; border-radius: 999px; color: var(--muted-foreground, #64748b); background: var(--card, #fff); border: 2px solid var(--border, #cbd5e1); font-size: 12px; font-weight: 800; }
    .complete .dot { color: #fff; background: var(--color-feedback-success, #16a34a); border-color: var(--color-feedback-success, #16a34a); }
    .current .dot { color: var(--primary-foreground, #fff); background: var(--primary, #2563eb); border-color: var(--primary, #2563eb); box-shadow: 0 0 0 4px color-mix(in srgb, var(--primary, #2563eb) 14%, transparent); }
    .label { display: block; font-size: 12px; font-weight: 700; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .hint { display: block; margin-top: 4px; color: var(--muted-foreground, #64748b); font-size: 10px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .exception { display: flex; align-items: center; gap: 9px; margin-top: 16px; padding: 10px 12px; border-radius: 9px; background: var(--color-bg-danger-soft, #fef2f2); color: var(--color-feedback-danger, #b91c1c); font-size: 12px; font-weight: 600; }
    .exception.suspended { background: var(--color-bg-warning-soft, #fffbeb); color: var(--color-feedback-warning, #b45309); }
    @media (max-width: 720px) { .shell { padding: 16px; } .rail { grid-template-columns: repeat(3, minmax(0, 1fr)); row-gap: 20px; } .step::after { display: none; } .hint { display: none; } }
  `

  render() {
    const normalized = this.status === "PENDING_DOCUMENTS" ? "UNDER_REVIEW" : this.status
    const current = ORDER[normalized] ?? 0
    const terminal = this.status === "REJECTED" || this.status === "SUSPENDED"
    return html`
      <section class="shell" aria-label="Application status timeline">
        <div class="header"><h3>Application journey</h3>${this.applicationNumber ? html`<span class="number">${this.applicationNumber}</span>` : ""}</div>
        <div class="rail">
          ${FLOW.map((step, index) => html`
            <div class="step ${index < current ? "complete" : ""} ${index === current && !terminal ? "current" : ""}">
              <div class="dot">${index < current ? "✓" : index + 1}</div>
              <span class="label">${step.label}</span>
              ${this.compact ? "" : html`<span class="hint">${step.hint}</span>`}
            </div>
          `)}
        </div>
        ${terminal ? html`<div class="exception ${this.status === "SUSPENDED" ? "suspended" : ""}"><span>${this.status === "SUSPENDED" ? "Ⅱ" : "!"}</span><span>This application is ${this.status.toLowerCase()}. Review the event history for the latest decision.</span></div>` : ""}
      </section>
    `
  }
}

declare global { interface HTMLElementTagNameMap { "onboarding-status-timeline": OnboardingStatusTimeline } }
