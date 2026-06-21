import { useState, useRef, useCallback } from "react"
import { Upload, Download, X, Loader2, FileSpreadsheet, AlertCircle, CheckCircle2 } from "lucide-react"
import { downloadTemplate, bulkUploadPartners } from "../../lib/api"

interface Props {
  open: boolean
  onClose: () => void
  onSuccess: () => void
}

type Step = "form" | "uploading" | "result"

export default function BulkUploadModal({ open, onClose, onSuccess }: Props) {
  const [clientType, setClientType] = useState<"INDIVIDUAL" | "CORPORATE" | "">("")
  const [downloading, setDownloading] = useState(false)
  const [file, setFile] = useState<File | null>(null)
  const [dragOver, setDragOver] = useState(false)
  const [step, setStep] = useState<Step>("form")
  const [result, setResult] = useState<{ imported: number; skipped: number; errors: { row: number; message: string }[] } | null>(null)
  const [error, setError] = useState("")
  const inputRef = useRef<HTMLInputElement>(null)

  const handleDownload = useCallback(async () => {
    if (!clientType) return
    setDownloading(true)
    setError("")
    try {
      const blob = await downloadTemplate(clientType)
      const url = URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = `partner-template-${clientType.toLowerCase()}.xlsx`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to download template")
    } finally {
      setDownloading(false)
    }
  }, [clientType])

  function handleFileDrop(e: React.DragEvent) {
    e.preventDefault()
    setDragOver(false)
    const f = e.dataTransfer.files[0]
    if (f) validateAndSetFile(f)
  }

  function handleFileSelect(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0]
    if (f) validateAndSetFile(f)
  }

  function validateAndSetFile(f: File) {
    const ext = f.name.split(".").pop()?.toLowerCase()
    if (!ext || !["xlsx", "xls"].includes(ext)) {
      setError("Please select an Excel file (.xlsx or .xls)")
      return
    }
    setError("")
    setFile(f)
  }

  async function handleUpload() {
    if (!file) return
    setStep("uploading")
    setError("")
    try {
      const res = await bulkUploadPartners(file)
      setResult(res)
      setStep("result")
      if (res.imported > 0) onSuccess()
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
    onClose()
  }

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="mx-4 w-full max-w-lg rounded-xl bg-white shadow-xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4">
          <h2 className="text-lg font-semibold text-gray-900">Bulk Upload Partner</h2>
          <button onClick={handleClose} className="rounded p-1 text-gray-400 transition hover:bg-gray-100 hover:text-gray-600">
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Body */}
        <div className="space-y-5 px-6 py-5">
          {step === "form" && (
            <>
              {/* Client type + Download row */}
              <div className="flex items-end gap-4">
                <div className="flex-1">
                  <label className="mb-1.5 block text-sm font-medium text-gray-700">Client Type</label>
                  <select
                    value={clientType}
                    onChange={(e) => setClientType(e.target.value as "INDIVIDUAL" | "CORPORATE")}
                    className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 transition hover:border-indigo-500 focus:border-indigo-500 focus:outline-none focus:ring-3 focus:ring-indigo-100"
                  >
                    <option value="">Select client type</option>
                    <option value="INDIVIDUAL">Individual</option>
                    <option value="CORPORATE">Corporate</option>
                  </select>
                </div>
                <button
                  onClick={handleDownload}
                  disabled={!clientType || downloading}
                  className="inline-flex h-[38px] items-center gap-2 rounded-lg bg-indigo-600 px-4 text-sm font-semibold text-white transition hover:bg-indigo-700 active:scale-[0.97] disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {downloading ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Download className="h-4 w-4" />
                  )}
                  Download Template
                </button>
              </div>

              {/* Drag & drop zone */}
              <div
                onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
                onDragLeave={() => setDragOver(false)}
                onDrop={handleFileDrop}
                onClick={() => inputRef.current?.click()}
                className={`flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed px-6 py-10 transition ${
                  dragOver
                    ? "border-indigo-500 bg-indigo-50"
                    : file
                      ? "border-green-400 bg-green-50"
                      : "border-gray-300 bg-gray-50 hover:border-indigo-400 hover:bg-indigo-50/50"
                }`}
              >
                {file ? (
                  <>
                    <FileSpreadsheet className="mb-2 h-10 w-10 text-green-600" />
                    <p className="text-sm font-medium text-gray-900">{file.name}</p>
                    <p className="text-xs text-gray-500">{(file.size / 1024).toFixed(1)} KB</p>
                    <p className="mt-2 text-xs text-gray-400">Click or drag to replace</p>
                  </>
                ) : (
                  <>
                    <Upload className="mb-3 h-10 w-10 text-gray-400" />
                    <p className="text-sm font-medium text-gray-700">
                      Drop your Excel file here, or <span className="text-indigo-600">browse</span>
                    </p>
                    <p className="mt-1 text-xs text-gray-400">Supports .xlsx and .xls files</p>
                  </>
                )}
                <input
                  ref={inputRef}
                  type="file"
                  accept=".xlsx,.xls"
                  className="hidden"
                  onChange={handleFileSelect}
                />
              </div>

              {/* Upload button */}
              <div className="flex justify-end">
                <button
                  onClick={handleUpload}
                  disabled={!file}
                  className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-6 py-2 text-sm font-semibold text-white transition hover:bg-indigo-700 active:scale-[0.97] disabled:cursor-not-allowed disabled:opacity-50"
                >
                  <Upload className="h-4 w-4" />
                  Upload
                </button>
              </div>
            </>
          )}

          {step === "uploading" && (
            <div className="flex flex-col items-center py-10">
              <Loader2 className="mb-4 h-10 w-10 animate-spin text-indigo-600" />
              <p className="text-sm font-medium text-gray-700">Uploading and processing file...</p>
              <p className="mt-1 text-xs text-gray-400">Please wait while partners are being imported</p>
            </div>
          )}

          {step === "result" && result && (
            <div className="space-y-4 py-2">
              {result.errors.length === 0 ? (
                <div className="flex flex-col items-center rounded-lg bg-green-50 px-4 py-6 text-center">
                  <CheckCircle2 className="mb-3 h-12 w-12 text-green-600" />
                  <p className="text-lg font-semibold text-green-800">Upload Complete</p>
                  <p className="mt-1 text-sm text-green-700">
                    {result.imported} partner{result.imported !== 1 ? "s" : ""} imported successfully.
                    {result.skipped > 0 && ` ${result.skipped} skipped.`}
                  </p>
                </div>
              ) : (
                <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-4">
                  <div className="flex items-center gap-2">
                    <AlertCircle className="h-5 w-5 text-amber-600" />
                    <p className="text-sm font-semibold text-amber-800">
                      {result.imported} imported, {result.skipped} skipped, {result.errors.length} error{result.errors.length !== 1 ? "s" : ""}
                    </p>
                  </div>
                  {result.errors.length > 0 && (
                    <div className="mt-3 max-h-32 space-y-1 overflow-y-auto">
                      {result.errors.map((err, i) => (
                        <p key={i} className="text-xs text-amber-700">
                          Row {err.row}: {err.message}
                        </p>
                      ))}
                    </div>
                  )}
                </div>
              )}
              <div className="flex justify-end">
                <button
                  onClick={handleClose}
                  className="rounded-lg bg-indigo-600 px-5 py-2 text-sm font-semibold text-white transition hover:bg-indigo-700"
                >
                  Done
                </button>
              </div>
            </div>
          )}

          {/* Inline error */}
          {error && step === "form" && (
            <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              <AlertCircle className="h-4 w-4 shrink-0" />
              {error}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
