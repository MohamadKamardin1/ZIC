import { RefreshCw, ShieldCheck } from "lucide-react"
import { ErrorCoach } from "../../components/ErrorCoach"
import { LoanStatusBadge, MoneyCell, ProgressCell } from "../../components/loans/LoanPrimitives"
import { useLoanKpis, useLoanList } from "../../lib/loansHooks"

function amountForKpi(value: string | Record<string, string>, currency: string) {
  if (typeof value === "string") return <MoneyCell value={value} currency={currency} />
  return <span className="space-y-1">{Object.entries(value).map(([code, amount]) => <span key={code} className="block"><MoneyCell value={amount} currency={code} /></span>)}</span>
}

export default function OLLoans() {
  const listQuery = useLoanList({ page: 1, pageSize: 5, ordering: "-created_at" })
  const kpiQuery = useLoanKpis()
  const rows = listQuery.data?.results ?? []
  const kpis = kpiQuery.data

  const error = listQuery.error ?? kpiQuery.error
  const retry = () => {
    void listQuery.refetch()
    void kpiQuery.refetch()
  }

  return (
    <div className="min-h-full space-y-5 bg-[var(--background)] px-1 py-1 text-[var(--foreground)]">
      <header className="flex flex-col gap-4 border-b border-[var(--border)] pb-5 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <div className="mb-2 flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.16em] text-[var(--muted-foreground)]"><span>ZIC</span><span>/</span><span>Ordinary Life / Servicing</span></div>
          <h1 className="text-2xl font-semibold tracking-[-0.04em] sm:text-3xl">Policy loans</h1>
          <p className="mt-1 max-w-2xl text-sm leading-6 text-[var(--muted-foreground)]">A contract-first servicing workspace for controlled requests, disbursements, repayments, offsets, and loan evidence.</p>
        </div>
        <div className="inline-flex items-center gap-2 rounded-lg border border-[var(--border)] bg-[var(--card)] px-3 py-2 text-xs font-semibold text-[var(--muted-foreground)]"><ShieldCheck size={15} className="text-[var(--success)]" aria-hidden="true" />Permission-gated workspace</div>
      </header>

      {error && <ErrorCoach title="Loans data needs attention" message={error.message || "The Loans service could not be reached."} actionLabel="Try again" resolutionSteps={["Confirm the backend is running and your session is active.", "Retry the request. If the issue remains, provide the correlation reference to ZIC support."]} onDismiss={retry} />}

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4" aria-label="Loan foundation metrics">
        <article className="surface-card p-4"><p className="text-[11px] font-bold uppercase tracking-[0.08em] text-[var(--muted-foreground)]">Outstanding balance</p><p className="mt-2 text-xl font-bold">{kpis ? amountForKpi(kpis.totalOutstanding, kpis.currency) : <span className="text-sm text-[var(--muted-foreground)]">Loading…</span>}</p><p className="mt-1 text-xs text-[var(--muted-foreground)]">Across the current loan scope</p></article>
        <article className="surface-card p-4"><p className="text-[11px] font-bold uppercase tracking-[0.08em] text-[var(--muted-foreground)]">Active loans</p><p className="mt-2 text-2xl font-bold">{kpis?.activeCount ?? <span className="text-sm text-[var(--muted-foreground)]">Loading…</span>}</p><p className="mt-1 text-xs text-[var(--muted-foreground)]">Active or partially repaid</p></article>
        <article className="surface-card p-4"><p className="text-[11px] font-bold uppercase tracking-[0.08em] text-[var(--muted-foreground)]">Defaulted loans</p><p className="mt-2 text-2xl font-bold text-[var(--destructive)]">{kpis?.defaultedCount ?? <span className="text-sm text-[var(--muted-foreground)]">Loading…</span>}</p><p className="mt-1 text-xs text-[var(--muted-foreground)]">Requires servicing review</p></article>
        <article className="surface-card p-4"><p className="text-[11px] font-bold uppercase tracking-[0.08em] text-[var(--muted-foreground)]">Settled / closed</p><p className="mt-2 text-2xl font-bold">{kpis?.settledCount ?? <span className="text-sm text-[var(--muted-foreground)]">Loading…</span>}</p><p className="mt-1 text-xs text-[var(--muted-foreground)]">Financially cleared records</p></article>
      </section>

      <section className="surface-card overflow-hidden" aria-label="Recent loans">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--border)] bg-[var(--muted)]/35 px-4 py-3"><div><h2 className="text-sm font-bold">Recent loan records</h2><p className="mt-1 text-xs text-[var(--muted-foreground)]">The full table, filters, and action menu arrive in the Loans list prompt.</p></div><button type="button" className="button-secondary inline-flex min-h-9 items-center gap-2" onClick={retry} disabled={listQuery.isFetching || kpiQuery.isFetching}><RefreshCw size={14} className={listQuery.isFetching ? "animate-spin" : ""} aria-hidden="true" />Refresh</button></div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[860px] text-left text-sm"><caption className="sr-only">Recent loan records</caption><thead className="bg-[var(--muted)]/45 text-xs uppercase tracking-[0.08em] text-[var(--muted-foreground)]"><tr><th scope="col" className="px-4 py-3">Loan</th><th scope="col" className="px-4 py-3">Policyholder</th><th scope="col" className="px-4 py-3">Product</th><th scope="col" className="px-4 py-3">Principal</th><th scope="col" className="px-4 py-3">Balance</th><th scope="col" className="px-4 py-3">Status</th></tr></thead><tbody className="divide-y divide-[var(--border)]">{listQuery.isLoading && <tr><td colSpan={6} className="px-4 py-12 text-center text-sm text-[var(--muted-foreground)]">Loading loan records…</td></tr>}{!listQuery.isLoading && !rows.length && <tr><td colSpan={6} className="px-4 py-12 text-center text-sm text-[var(--muted-foreground)]">No loan records are available in the current scope.</td></tr>}{rows.map((loan) => <tr key={loan.id} className="transition hover:bg-[var(--muted)]/25"><td className="px-4 py-3 font-semibold">{loan.loanNumber || "—"}</td><td className="px-4 py-3">{loan.policyholderName || loan.partnerDisplay || "—"}<span className="mt-1 block text-xs text-[var(--muted-foreground)]">{loan.policyDisplay || loan.policyNumber || "—"}</span></td><td className="px-4 py-3">{loan.productDisplay || "—"}</td><td className="px-4 py-3"><MoneyCell value={loan.principalAmount} currency={loan.currency} /></td><td className="px-4 py-3"><ProgressCell principal={loan.principalAmount} balance={loan.outstandingBalance} currency={loan.currency} /></td><td className="px-4 py-3"><LoanStatusBadge status={loan.status} statusDisplay={loan.statusDisplay} /></td></tr>)}</tbody></table>
        </div>
      </section>
    </div>
  )
}
