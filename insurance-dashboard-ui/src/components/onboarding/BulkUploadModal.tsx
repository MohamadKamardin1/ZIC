import { useState, useRef, useCallback } from "react"
import { Upload, Download, X, Loader2, FileSpreadsheet, AlertCircle, CheckCircle2, FileText, RotateCcw } from "lucide-react"
import { downloadTemplate, bulkUploadPartners } from "../../lib/api"

interface Props {
  open: boolean
  onClose: () => void
  onSuccess: () => void
}

type Step = "form" | "uploading" | "result"

type ImportResult = { imported: number; skipped: number; errors: { row: number; message: string }[] }

export default function BulkUploadModal({ open, onClose, onSuccess }: Props) {
  const [clientType, setClientType] = useState<"INDIVIDUAL" | "CORPORATE" | "">("")
  const [downloading, setDownloading] = useState(false)
  const [file, setFile] = useState<File | null>(null)
  const [dragOver, setDragOver] = useState(false)
  const [step, setStep] = useState<Step>("form")
  const [result, setResult] = useState<ImportResult | null>(null)
  const [error, setError] = useState("")
  const inputRef = useRef<HTMLInputElement>(null)

  const handleDownload = useCallback(async () => {
    if (!clientType) return
    setDownloading(true)
    setError("")
    try {
      const blob = await downloadTemplate(clientType)
      const url = URL.createObjectURL(blob)
      const anchor = document.createElement("a")
      anchor.href = url
      anchor.download = `partner-template-${clientType.toLowerCase()}.xlsx`
      document.body.appendChild(anchor)
      anchor.click()
      anchor.remove()
      URL.revokeObjectURL(url)
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to download the template")
    } finally {
      setDownloading(false)
    }
  }, [clientType])

  function validateAndSetFile(selected: File) {
    const extension = selected.name.split(".").pop()?.toLowerCase()
    if (!extension || !["xlsx", "xls"].includes(extension)) {
      setError("Select an Excel workbook in .xlsx or .xls format.")
      setFile(null)
      return
    }
    if (selected.size > 10 * 1024 * 1024) {
      setError("The workbook must be smaller than 10 MB.")
      setFile(null)
      return
    }
    setError("")
    setFile(selected)
  }

  function handleFileDrop(event: React.DragEvent<HTMLDivElement>) {
    event.preventDefault()
    setDragOver(false)
    const dropped = event.dataTransfer.files[0]
    if (dropped) validateAndSetFile(dropped)
  }

  function handleFileSelect(event: React.ChangeEvent<HTMLInputElement>) {
    const selected = event.target.files?.[0]
    if (selected) validateAndSetFile(selected)
  }

  async function handleUpload() {
    if (!file || !clientType) {
      setError("Choose a client type and select a workbook before uploading.")
      return
    }
    setStep("uploading")
    setError("")
    try {
      const response = await bulkUploadPartners(file)
      setResult(response)
      setStep("result")
      if (response.imported > 0) onSuccess()
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed")
      setStep("form")
    }
  }

  function handleClose() {
    setClientType("")
    setFile(null)
    setDragOver(false)
    setStep("form")
    setResult(null)
    setError("")
    if (inputRef.current) inputRef.current.value = ""
    onClose()
  }

  function startAgain() {
    setFile(null)
    setResult(null)
    setError("")
    setStep("form")
    if (inputRef.current) inputRef.current.value = ""
  }

  if (!open) return null

  const ready = Boolean(clientType && file)

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/55 p-4" role="dialog" aria-modal="true" aria-labelledby="bulk-upload-title">
      <div className="max-h-[calc(100vh-2rem)] w-full max-w-2xl overflow-y-auto rounded-2xl border border-[#d9d9d9] bg-white shadow-[0_28px_80px_rgba(0,0,0,0.22)]">
        <div className="flex items-start justify-between border-b border-[#e8e8e8] px-6 py-5 sm:px-8">
          <div>
            <div className="mb-2 flex items-center gap-2 text-[11px] font-bold uppercase tracking-[0.12em] text-[#777]"><Upload className="h-3.5 w-3.5" /> Partner register</div>
            <h2 id="bulk-upload-title" className="text-xl font-semibold tracking-[-0.02em] text-[#111]">Bulk upload partners</h2>
            <p className="mt-1 text-sm text-[#777]">Import multiple partner records from the approved Excel template.</p>
          </div>
          <button onClick={handleClose} className="rounded-lg p-2 text-[#777] transition hover:bg-[#f2f2f2] hover:text-[#111]" aria-label="Close bulk upload"><X className="h-5 w-5" /></button>
        </div>

        <div className="space-y-6 px-6 py-6 sm:px-8">
          {step === "form" && <>
            <div className="grid gap-4 rounded-xl border border-[#e2e2e2] bg-[#fafafa] p-4 sm:grid-cols-[1fr_auto] sm:items-end">
              <label className="text-xs font-bold uppercase tracking-[0.08em] text-[#707070]">Client type<span className="mt-1.5 block"><select value={clientType} onChange={(e) => { setClientType(e.target.value as "INDIVIDUAL" | "CORPORATE"); setError("") }} className="h-11 w-full rounded-lg border border-[#d8d8d8] bg-white px-3 text-sm font-medium normal-case tracking-normal text-[#222] outline-none focus:border-[#111] focus:ring-2 focus:ring-[#111]/10"><option value="">Select client type</option><option value="INDIVIDUAL">Individual</option><option value="CORPORATE">Corporate</option></select></span></label>
              <button onClick={handleDownload} disabled={!clientType || downloading} className="inline-flex h-11 items-center justify-center gap-2 rounded-lg border border-[#bdbdbd] bg-white px-4 text-sm font-semibold text-[#222] transition hover:border-[#111] disabled:cursor-not-allowed disabled:opacity-45">{downloading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />} Download template</button>
            </div>

            <div className="flex items-start gap-3 rounded-lg border border-[#e2e2e2] bg-white px-4 py-3 text-sm text-[#555]"><FileText className="mt-0.5 h-4 w-4 shrink-0 text-[#777]" /><p>Use the template that matches the selected client type. Keep the header row unchanged so validation can identify every field correctly.</p></div>

            <div onDragOver={(event) => { event.preventDefault(); setDragOver(true) }} onDragLeave={() => setDragOver(false)} onDrop={handleFileDrop} onClick={() => inputRef.current?.click()} className={`flex min-h-[190px] cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed px-6 text-center transition ${dragOver ? "border-[#111] bg-[#f4f4f4]" : file ? "border-[#333] bg-[#fafafa]" : "border-[#cfcfcf] bg-[#fcfcfc] hover:border-[#777] hover:bg-[#fafafa]"}`}>
              <input ref={inputRef} type="file" accept=".xlsx,.xls" className="hidden" onChange={handleFileSelect} />
              {file ? <><FileSpreadsheet className="mb-3 h-10 w-10 text-[#222]" /><p className="max-w-full truncate text-sm font-semibold text-[#222]">{file.name}</p><p className="mt-1 text-xs text-[#777]">{(file.size / 1024).toFixed(1)} KB · Ready to upload</p><p className="mt-3 text-xs font-semibold text-[#555]">Click or drag another workbook to replace it</p></> : <><Upload className="mb-3 h-9 w-9 text-[#555]" /><p className="text-sm font-semibold text-[#222]">Drag and drop an Excel file here</p><p className="mt-1 text-sm text-[#777]">or click to browse from your computer</p><p className="mt-3 text-xs text-[#999]">Accepted: .xlsx, .xls · Maximum size: 10 MB</p></>}
            </div>

            {error && <div role="alert" className="flex items-start gap-2 rounded-lg border border-[#d5d5d5] bg-[#f6f6f6] px-4 py-3 text-sm text-[#333]"><AlertCircle className="mt-0.5 h-4 w-4 shrink-0" /> <span>{error}</span></div>}

            <div className="flex flex-col-reverse gap-2 border-t border-[#e8e8e8] pt-5 sm:flex-row sm:justify-end"><button onClick={handleClose} className="rounded-lg border border-[#d6d6d6] px-4 py-2.5 text-sm font-semibold text-[#555] transition hover:border-[#111] hover:text-[#111]">Cancel</button><button onClick={handleUpload} disabled={!ready} className="inline-flex items-center justify-center gap-2 rounded-lg bg-[#111] px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-[#2b2b2b] disabled:cursor-not-allowed disabled:opacity-40"><Upload className="h-4 w-4" /> Upload partners</button></div>
          </>}

          {step === "uploading" && <div className="flex flex-col items-center justify-center py-14 text-center"><div className="mb-5 flex h-16 w-16 items-center justify-center rounded-full border border-[#d8d8d8] bg-[#fafafa]"><Loader2 className="h-7 w-7 animate-spin text-[#222]" /></div><h3 className="text-lg font-semibold text-[#111]">Processing workbook</h3><p className="mt-2 max-w-sm text-sm text-[#777]">We are validating each row and creating eligible partner records. Keep this window open.</p><div className="mt-6 h-1.5 w-56 overflow-hidden rounded-full bg-[#ededed]"><div className="h-full w-2/3 animate-pulse rounded-full bg-[#111]" /></div></div>}

          {step === "result" && result && <div className="space-y-5"><div className="flex flex-col items-center rounded-xl border border-[#dedede] bg-[#fafafa] px-5 py-8 text-center"><div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full border border-[#cfcfcf] bg-white">{result.errors.length === 0 ? <CheckCircle2 className="h-7 w-7 text-[#222]" /> : <AlertCircle className="h-7 w-7 text-[#555]" />}</div><h3 className="text-lg font-semibold text-[#111]">{result.errors.length === 0 ? "Upload complete" : "Upload completed with exceptions"}</h3><p className="mt-1 text-sm text-[#777]">{result.imported} imported · {result.skipped} skipped · {result.errors.length} validation error{result.errors.length === 1 ? "" : "s"}</p></div><div className="grid grid-cols-3 gap-2"><ResultMetric label="Imported" value={result.imported} /><ResultMetric label="Skipped" value={result.skipped} /><ResultMetric label="Errors" value={result.errors.length} /></div>{result.errors.length > 0 && <div className="rounded-xl border border-[#dedede]"><div className="border-b border-[#e8e8e8] px-4 py-3 text-sm font-semibold text-[#222]">Rows requiring attention</div><div className="max-h-48 divide-y divide-[#eeeeee] overflow-y-auto">{result.errors.map((item, index) => <div key={`${item.row}-${index}`} className="flex gap-4 px-4 py-3 text-sm"><span className="shrink-0 font-semibold text-[#555]">Row {item.row}</span><span className="text-[#777]">{item.message}</span></div>)}</div></div>}<div className="flex flex-col-reverse gap-2 border-t border-[#e8e8e8] pt-5 sm:flex-row sm:justify-end"><button onClick={startAgain} className="inline-flex items-center justify-center gap-2 rounded-lg border border-[#d6d6d6] px-4 py-2.5 text-sm font-semibold text-[#555] hover:border-[#111] hover:text-[#111]"><RotateCcw className="h-4 w-4" /> Upload another</button><button onClick={handleClose} className="rounded-lg bg-[#111] px-5 py-2.5 text-sm font-semibold text-white hover:bg-[#2b2b2b]">Done</button></div></div>}
        </div>
      </div>
    </div>
  )
}

function ResultMetric({ label, value }: { label: string; value: number }) { return <div className="rounded-lg border border-[#e2e2e2] bg-white px-3 py-3 text-center"><div className="text-xl font-semibold text-[#111]">{value}</div><div className="mt-1 text-[11px] font-bold uppercase tracking-[0.08em] text-[#888]">{label}</div></div> }
