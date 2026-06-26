const bar = (className: string) => (
  <div className={`h-3 animate-pulse rounded bg-muted-foreground/15 ${className}`} />
)

export function SkeletonBar({ className }: { className?: string }) {
  return bar(className ?? "")
}

export function SkeletonTable({ rows = 5, cols }: { rows?: number; cols: number }) {
  return (
    <div className="rounded-xl border border-border bg-card shadow-sm">
      <table className="hidden w-full text-sm md:table">
        <thead>
          <tr className="border-b border-border bg-muted/30">
            {Array.from({ length: cols }).map((_, i) => (
              <th key={i} className="px-3 py-3">
                {bar(i === 0 ? "w-16" : i === cols - 1 ? "w-12 ml-auto" : "w-20")}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {Array.from({ length: rows }).map((_, r) => (
            <tr key={r} className="border-b border-border/50">
              {Array.from({ length: cols }).map((_, c) => (
                <td key={c} className="px-3 py-3">
                  {bar(
                    c === 0
                      ? "w-24"
                      : c === cols - 1
                        ? "w-16 ml-auto"
                        : ["w-32", "w-28", "w-36", "w-24", "w-40", "w-20"][c % 6],
                  )}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      <div className="divide-y divide-border md:hidden">
        {Array.from({ length: rows }).map((_, r) => (
          <div key={r} className="space-y-2 p-4">
            <div className="flex items-center justify-between">
              {bar("h-4 w-40")}
              {bar("h-5 w-16 rounded-full")}
            </div>
            <div className="grid grid-cols-2 gap-2">
              {bar("h-3 w-full")}
              {bar("h-3 w-3/4")}
              {bar("h-3 w-5/6")}
              {bar("h-3 w-2/3")}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export function SkeletonCard({ className = "" }: { className?: string }) {
  return (
    <div className={`rounded-xl border border-border bg-card p-5 shadow-sm ${className}`}>
      <div className="mb-4 flex items-center justify-between">
        {bar("h-4 w-32")}
        {bar("h-8 w-8 rounded-full")}
      </div>
      <div className="space-y-3">
        {bar("h-7 w-20")}
        {bar("h-3 w-44")}
        {bar("h-3 w-36")}
      </div>
    </div>
  )
}

export function DashboardSkeleton() {
  return (
    <div className="flex flex-col gap-5">
      <div className="rounded-2xl border border-border bg-card p-6 shadow-sm">
        <div className="mb-4 flex items-center justify-between">
          <div className="space-y-2">
            {bar("h-6 w-56")}
            {bar("h-4 w-80")}
          </div>
          {bar("h-10 w-10 rounded-full")}
        </div>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="rounded-lg bg-muted/30 p-3">
              {bar("h-6 w-12 mb-1")}
              {bar("h-3 w-20")}
            </div>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-4">
        <div className="xl:col-span-2">
          <div className="rounded-xl border border-border bg-card p-5 shadow-sm">
            <div className="mb-4 flex items-center justify-between">
              {bar("h-4 w-36")}
              {bar("h-8 w-16 rounded-md")}
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                {bar("h-32 w-full rounded-lg")}
              </div>
              <div className="space-y-2">
                {bar("h-3 w-full")}
                {bar("h-3 w-3/4")}
                {bar("h-3 w-5/6")}
                {bar("h-3 w-2/3")}
              </div>
            </div>
          </div>
        </div>
        <div className="rounded-xl border border-border bg-card p-5 shadow-sm">
          <div className="mb-4 flex items-center justify-between">
            {bar("h-4 w-28")}
            {bar("h-6 w-6 rounded-full")}
          </div>
          <div className="space-y-3">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="flex items-start gap-3">
                {bar("h-8 w-8 rounded-full shrink-0")}
                <div className="flex-1 space-y-1">
                  {bar("h-3 w-full")}
                  {bar("h-2 w-3/4")}
                </div>
              </div>
            ))}
          </div>
        </div>
        <div className="flex flex-col gap-5">
          {Array.from({ length: 2 }).map((_, i) => (
            <div key={i} className="flex-1 rounded-xl border border-border bg-card p-5 shadow-sm">
              <div className="mb-4 flex items-center justify-between">
                {bar("h-4 w-24")}
                {bar("h-5 w-5 rounded-full")}
              </div>
              <div className="space-y-3">
                {bar("h-4 w-16")}
                {bar("h-3 w-40")}
                {bar("h-3 w-32")}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
