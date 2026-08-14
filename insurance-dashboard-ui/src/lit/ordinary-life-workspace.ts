import { LitElement, css, html } from "lit"
import { customElement, property } from "lit/decorators.js"

export type OrdinaryLifeMetric = {
  label: string
  value: string
  detail?: string
  tone?: "dark" | "soft" | "line"
}

export type OrdinaryLifeColumn = {
  key: string
  label: string
  emphasis?: boolean
  muted?: boolean
}

@customElement("zic-ordinary-life-workspace")
export class OrdinaryLifeWorkspace extends LitElement {
  static styles = css`
    :host {
      display: block;
      color: #171717;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    .frame {
      display: grid;
      gap: 18px;
    }
    .metrics {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 10px;
    }
    .metric {
      min-height: 96px;
      border: 1px solid #dedede;
      border-radius: 12px;
      background: #fff;
      padding: 16px;
      box-shadow: 0 8px 24px rgba(20, 20, 20, 0.035);
    }
    .metric.dark {
      background: #171717;
      border-color: #171717;
      color: #fff;
    }
    .metric.soft {
      background: #f5f5f5;
    }
    .metric.line {
      background: linear-gradient(135deg, #fff 0%, #f6f6f6 100%);
    }
    .metric-label {
      color: #737373;
      font-size: 10px;
      font-weight: 700;
      letter-spacing: 0.12em;
      text-transform: uppercase;
    }
    .dark .metric-label {
      color: #a3a3a3;
    }
    .metric-value {
      margin-top: 8px;
      font-size: 27px;
      font-weight: 750;
      letter-spacing: -0.04em;
      line-height: 1;
    }
    .metric-detail {
      margin-top: 8px;
      color: #737373;
      font-size: 11px;
    }
    .dark .metric-detail {
      color: #d4d4d4;
    }
    .toolbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      border: 1px solid #dedede;
      border-bottom: 0;
      border-radius: 12px 12px 0 0;
      background: #fff;
      padding: 14px 16px;
    }
    .toolbar-left,
    .toolbar-right {
      display: flex;
      align-items: center;
      gap: 8px;
      min-width: 0;
    }
    .search {
      display: flex;
      align-items: center;
      gap: 9px;
      width: min(360px, 42vw);
      border: 1px solid #dedede;
      border-radius: 8px;
      background: #fafafa;
      padding: 8px 10px;
      color: #737373;
    }
    .search svg {
      flex: 0 0 auto;
    }
    .search input {
      width: 100%;
      border: 0;
      outline: 0;
      background: transparent;
      color: #171717;
      font: inherit;
      font-size: 12px;
    }
    select {
      min-width: 128px;
      border: 1px solid #dedede;
      border-radius: 8px;
      background: #fff;
      padding: 8px 10px;
      color: #404040;
      font: inherit;
      font-size: 12px;
      outline: 0;
    }
    .primary {
      border: 1px solid #171717;
      border-radius: 8px;
      background: #171717;
      color: #fff;
      padding: 9px 13px;
      font: inherit;
      font-size: 12px;
      font-weight: 700;
      cursor: pointer;
      transition: transform 160ms ease-out, background 160ms ease-out;
    }
    .primary:hover {
      background: #333;
    }
    .primary:active {
      transform: scale(0.97);
    }
    .table-wrap {
      overflow: hidden;
      border: 1px solid #dedede;
      border-radius: 0 0 12px 12px;
      background: #fff;
      box-shadow: 0 8px 24px rgba(20, 20, 20, 0.035);
    }
    table {
      width: 100%;
      border-collapse: collapse;
      table-layout: fixed;
    }
    th {
      border-bottom: 1px solid #dedede;
      background: #f7f7f7;
      padding: 12px 16px;
      color: #737373;
      font-size: 10px;
      font-weight: 750;
      letter-spacing: 0.11em;
      text-align: left;
      text-transform: uppercase;
    }
    td {
      border-bottom: 1px solid #eeeeee;
      padding: 14px 16px;
      color: #262626;
      font-size: 12px;
      vertical-align: middle;
    }
    tr:last-child td {
      border-bottom: 0;
    }
    tbody tr {
      cursor: pointer;
      transition: background 140ms ease-out;
    }
    tbody tr:hover,
    tbody tr:focus-visible {
      background: #fafafa;
      outline: none;
    }
    .emphasis {
      color: #171717;
      font-weight: 750;
    }
    .muted {
      color: #737373;
    }
    .status {
      display: inline-flex;
      align-items: center;
      border: 1px solid #d4d4d4;
      border-radius: 999px;
      background: #fafafa;
      padding: 4px 8px;
      color: #404040;
      font-size: 10px;
      font-weight: 750;
      letter-spacing: 0.04em;
    }
    .row-action {
      border: 1px solid #dedede;
      border-radius: 7px;
      background: #fff;
      padding: 6px 9px;
      color: #404040;
      font: inherit;
      font-size: 11px;
      font-weight: 700;
      cursor: pointer;
    }
    .row-action:hover {
      border-color: #171717;
      color: #171717;
    }
    .empty,
    .loading {
      padding: 48px 16px;
      color: #737373;
      font-size: 13px;
      text-align: center;
    }
    .error {
      border: 1px solid #a3a3a3;
      border-radius: 8px;
      background: #f5f5f5;
      padding: 12px 14px;
      color: #404040;
      font-size: 12px;
    }
    @media (max-width: 900px) {
      .metrics {
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }
      .toolbar {
        align-items: stretch;
        flex-direction: column;
      }
      .toolbar-left,
      .toolbar-right,
      .search {
        width: 100%;
      }
      .toolbar-right {
        justify-content: space-between;
      }
    }
    @media (max-width: 640px) {
      .metrics {
        grid-template-columns: 1fr 1fr;
      }
      .table-wrap {
        overflow-x: auto;
      }
      table {
        min-width: 720px;
      }
    }
    @media (prefers-reduced-motion: reduce) {
      *, *::before, *::after {
        transition-duration: 0.01ms !important;
      }
    }
  `

  @property({ attribute: false }) title = "Ordinary Life"
  @property({ attribute: false }) metrics: OrdinaryLifeMetric[] = []
  @property({ attribute: false }) columns: OrdinaryLifeColumn[] = []
  @property({ attribute: false }) rows: Record<string, unknown>[] = []
  @property({ attribute: false }) loading = false
  @property({ attribute: false }) error = ""
  @property({ attribute: false }) actionLabel = "New record"
  @property({ attribute: false }) emptyLabel = "No records match the current view."
  @property({ attribute: false }) statusOptions: string[] = []
  @property({ attribute: false }) searchable = true

  private query = ""
  private status = "ALL"

  private get filteredRows() {
    const query = this.query.trim().toLowerCase()
    return this.rows.filter((row) => {
      const matchesQuery = !query || Object.values(row).some((value) => String(value ?? "").toLowerCase().includes(query))
      const matchesStatus = this.status === "ALL" || String(row.status ?? "").toUpperCase() === this.status
      return matchesQuery && matchesStatus
    })
  }

  private value(row: Record<string, unknown>, key: string) {
    const raw = row[key]
    if (raw === null || raw === undefined || raw === "") return "—"
    if (typeof raw === "object") return JSON.stringify(raw)
    return String(raw)
  }

  private emit(name: string, detail: Record<string, unknown>) {
    this.dispatchEvent(new CustomEvent(name, { detail, bubbles: true, composed: true }))
  }

  private renderIcon() {
    return html`<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="11" cy="11" r="7"></circle><path d="m20 20-4-4"></path></svg>`
  }

  render() {
    return html`
      <section class="frame" aria-label=${this.title}>
        ${this.error ? html`<div class="error" role="alert">${this.error}</div>` : ""}
        ${this.metrics.length ? html`
          <div class="metrics">
            ${this.metrics.map((metric) => html`
              <article class="metric ${metric.tone ?? "line"}">
                <div class="metric-label">${metric.label}</div>
                <div class="metric-value">${metric.value}</div>
                ${metric.detail ? html`<div class="metric-detail">${metric.detail}</div>` : ""}
              </article>
            `)}
          </div>
        ` : ""}
        <div>
          <div class="toolbar">
            <div class="toolbar-left">
              ${this.searchable ? html`
                <label class="search">
                  ${this.renderIcon()}
                  <input
                    aria-label="Search records"
                    placeholder="Search records, references, clients..."
                    .value=${this.query}
                    @input=${(event: InputEvent) => {
                      this.query = (event.target as HTMLInputElement).value
                      this.requestUpdate()
                    }}
                  />
                </label>
              ` : ""}
            </div>
            <div class="toolbar-right">
              ${this.statusOptions.length ? html`
                <select aria-label="Filter by status" @change=${(event: Event) => {
                  this.status = (event.target as HTMLSelectElement).value
                  this.requestUpdate()
                }}>
                  <option value="ALL">All statuses</option>
                  ${this.statusOptions.map((option) => html`<option value=${option}>${option}</option>`)}
                </select>
              ` : ""}
              <button class="primary" type="button" @click=${() => this.emit("ol-primary-action", {})}>${this.actionLabel}</button>
            </div>
          </div>
          <div class="table-wrap">
            ${this.loading ? html`<div class="loading" role="status">Loading ${this.title.toLowerCase()}...</div>` : this.filteredRows.length === 0 ? html`<div class="empty">${this.emptyLabel}</div>` : html`
              <table>
                <thead>
                  <tr>
                    ${this.columns.map((column) => html`<th scope="col">${column.label}</th>`)}
                    <th scope="col">Action</th>
                  </tr>
                </thead>
                <tbody>
                  ${this.filteredRows.map((row) => html`
                    <tr tabindex="0" @click=${() => this.emit("ol-row-select", { row })} @keydown=${(event: KeyboardEvent) => {
                      if (event.key === "Enter" || event.key === " ") {
                        event.preventDefault()
                        this.emit("ol-row-select", { row })
                      }
                    }}>
                      ${this.columns.map((column) => html`
                        <td class=${column.emphasis ? "emphasis" : column.muted ? "muted" : ""}>
                          ${column.key === "status" ? html`<span class="status">${this.value(row, column.key)}</span>` : this.value(row, column.key)}
                        </td>
                      `)}
                      <td><button class="row-action" type="button" @click=${(event: Event) => {
                        event.stopPropagation()
                        this.emit("ol-row-select", { row })
                      }}>Open</button></td>
                    </tr>
                  `)}
                </tbody>
              </table>
            `}
          </div>
        </div>
      </section>
    `
  }
}
