import { LitElement, css, html } from "lit"
import { customElement, property } from "lit/decorators.js"

@customElement("onboarding-stats-card")
export class OnboardingStatsCard extends LitElement {
  @property({ type: String }) label = "Applications"
  @property({ type: String }) value = "0"
  @property({ type: String }) caption = "Current pipeline"
  @property({ type: String }) trend = ""
  @property({ type: String }) tone: "blue" | "green" | "amber" | "violet" | "slate" = "blue"

  static styles = css`
    :host { display: block; height: 100%; font-family: var(--font-sans, Inter, sans-serif); }
    .card { position: relative; overflow: hidden; height: 100%; min-height: 108px; box-sizing: border-box; padding: 17px 18px; border: 1px solid var(--border, #e2e8f0); border-radius: var(--radius, 12px); background: var(--card, #fff); box-shadow: 0 1px 3px rgba(15,23,42,.05); }
    .card::after { content: ""; position: absolute; right: -22px; top: -28px; width: 92px; height: 92px; border-radius: 999px; background: color-mix(in srgb, var(--tone) 13%, transparent); }
    .label { position: relative; z-index: 1; color: var(--muted-foreground, #64748b); font-size: 11px; font-weight: 700; letter-spacing: .02em; text-transform: uppercase; }
    .main { position: relative; z-index: 1; display: flex; align-items: baseline; gap: 9px; margin-top: 8px; }
    .value { color: var(--foreground, #0f172a); font-size: 28px; font-weight: 800; letter-spacing: -.04em; }
    .trend { color: var(--color-feedback-success, #15803d); font-size: 11px; font-weight: 800; }
    .caption { position: relative; z-index: 1; margin-top: 4px; color: var(--muted-foreground, #64748b); font-size: 11px; }
    .blue { --tone: #2563eb; } .green { --tone: #16a34a; } .amber { --tone: #d97706; } .violet { --tone: #7c3aed; } .slate { --tone: #64748b; }
  `

  render() { return html`<article class="card ${this.tone}" aria-label=${`${this.label}: ${this.value}`}><div class="label">${this.label}</div><div class="main"><span class="value">${this.value}</span>${this.trend ? html`<span class="trend">${this.trend}</span>` : ""}</div><div class="caption">${this.caption}</div></article>` }
}

declare global { interface HTMLElementTagNameMap { "onboarding-stats-card": OnboardingStatsCard } }
