---
name: drf-state-machine-frontend
description: Build frontend screens for a Django DRF ModelViewSet with state machine transitions, nested resources, multi-step wizard form, and contextual action buttons
source: auto-skill
extracted_at: '2026-06-21T11:05:33.351Z'
---

# DRF State Machine Frontend Pattern

## When to Use

When building frontend screens for a backend resource that:
- Has a **state machine** (e.g., DRAFT → SUBMITTED → UNDER_REVIEW → APPROVED → CONVERTED)
- Exposes **state transition endpoints** as POST actions on a ModelViewSet
- Has **nested resources** (documents, tasks, comments) via nested ViewSets
- Uses a **response envelope** `{ success, data, meta }` with camelCase rendering

## API Layer Pattern

### Base URL + query string helper
```typescript
const BASE = "/api/v1/onboarding"

function qs(params: Record<string, string | number | undefined>): string {
  const entries = Object.entries(params).filter(([, v]) => v !== undefined && v !== "")
  if (!entries.length) return ""
  return "?" + new URLSearchParams(entries.map(([k, v]) => [k, String(v)])).toString()
}
```

### CRUD operations with envelope unwrapping
```typescript
export async function listApplications(params: ListParams): Promise<PaginatedResponse<T>> {
  const res = await apiFetchAuth(`${BASE}/applications/${qs(params)}`)
  if (!res.ok) throw new Error(extractError(res, await res.json().catch(() => null)))
  return res.json()  // DRF pagination: { count, next, previous, results }
}

export async function getApplication(id: string): Promise<Detail> {
  const res = await apiFetchAuth(`${BASE}/applications/${id}/`)
  if (!res.ok) throw new Error(extractError(res, await res.json().catch(() => null)))
  return (await res.json()).data  // envelope: { data: Detail }
}

export async function createApplication(data: Record<string, unknown>): Promise<Detail> {
  return (await apiPost(`${BASE}/applications/`, data)) as Detail
}

// PATCH for partial updates
export async function updateApplication(id: string, data: Record<string, unknown>): Promise<Detail> {
  const res = await apiFetchAuth(`${BASE}/applications/${id}/`, {
    method: "PATCH",
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error(extractError(res, await res.json().catch(() => null)))
  return (await res.json()).data
}
```

### State transition endpoints (all POST, no body or small body)
```typescript
export async function submitApplication(id: string): Promise<Detail> {
  return (await apiPost(`${BASE}/applications/${id}/submit/`)) as Detail
}

export async function approveApplication(id: string, notes?: string): Promise<Detail> {
  return (await apiPost(`${BASE}/applications/${id}/approve/`, {
    ...(notes ? { notes } : {}),
  })) as Detail
}

export async function rejectApplication(id: string, reason: string, notes?: string): Promise<Detail> {
  return (await apiPost(`${BASE}/applications/${id}/reject/`, {
    rejection_reason: reason,
    ...(notes ? { notes } : {}),
  })) as Detail
}
```

### Helper for POST with envelope unwrapping
```typescript
async function apiPost(path: string, body?: Record<string, unknown>): Promise<unknown> {
  const res = await apiFetchAuth(path, {
    method: "POST",
    body: body ? JSON.stringify(body) : undefined,
  })
  const json = await res.json().catch(() => null)
  if (!res.ok) throw new Error(extractError(res, json))
  return (json as Record<string, unknown>)?.data ?? json
}
```

### File upload (FormData, no JSON Content-Type)
```typescript
export async function uploadDocument(
  applicationId: string,
  file: File,
  documentType: string,
  documentName?: string,
): Promise<Document> {
  const formData = new FormData()
  formData.append("file", file)
  formData.append("document_type", documentType)
  formData.append("document_name", documentName || file.name)

  const headers = new Headers()
  const token = getAccessToken()
  if (token) headers.set("Authorization", `Bearer ${token}`)
  // Do NOT set Content-Type — browser sets it with boundary

  const res = await fetch(`${API_BASE}${BASE}/applications/${applicationId}/documents/`, {
    method: "POST",
    headers,
    body: formData,
  })
  const json = await res.json().catch(() => null)
  if (!res.ok) throw new Error(extractError(res, json))
  return (json as Record<string, unknown>)?.data ?? json
}
```

### Nested resource list (paginated or plain array)
```typescript
export async function listDocuments(applicationId: string): Promise<Document[]> {
  const res = await apiFetchAuth(`${BASE}/applications/${applicationId}/documents/`)
  if (!res.ok) throw new Error(extractError(res, await res.json().catch(() => null)))
  const json = await res.json()
  // DRF pagination OR plain array OR envelope — handle all three
  return json.results ?? json.data ?? json
}
```

## List Page Pattern

### Features
- Search input (debounced or on-change with page reset)
- Filter dropdowns (status, type)
- Paginated table with clickable rows
- Color-coded status badges
- Action buttons per row (view, delete for DRAFT only)

```typescript
const [page, setPage] = useState(1)
const [search, setSearch] = useState("")
const [statusFilter, setStatusFilter] = useState<ApplicationStatus | "">("")

const load = useCallback(async () => {
  const result = await listApplications({
    page,
    search: search || undefined,
    status: statusFilter || undefined,
    ordering: "-created_at",
  })
  setItems(result.results)
  setCount(result.count)
}, [page, search, statusFilter])

useEffect(() => { load() }, [load])
```

### Status badge map
```typescript
const STATUS_LABELS: Record<ApplicationStatus, string> = {
  DRAFT: "Draft",
  SUBMITTED: "Submitted",
  UNDER_REVIEW: "Under Review",
  APPROVED: "Approved",
  // ...
}

const STATUS_COLORS: Record<ApplicationStatus, string> = {
  DRAFT: "bg-gray-100 text-gray-700",
  SUBMITTED: "bg-blue-100 text-blue-700",
  APPROVED: "bg-green-100 text-green-700",
  // ...
}
```

## Multi-Step Wizard Form Pattern

### Step management
```typescript
type Step = "type" | "details" | "documents" | "review"
const [step, setStep] = useState<Step>("type")
const STEPS = [
  { key: "type", label: "Type" },
  { key: "details", label: "Details" },
  { key: "documents", label: "Documents" },
  { key: "review", label: "Review" },
]
```

### Form state with typed updater
```typescript
interface FormState {
  partnerType: "INDIVIDUAL" | "CORPORATE" | ""
  firstName: string
  email: string
  // ...
}

const update = useCallback(
  <K extends keyof FormState>(key: K, val: FormState[K]) =>
    setForm((f) => ({ ...f, [key]: val })),
  [],
)
```

### Frontend → backend payload conversion (camelCase → snake_case)
```typescript
function toPayload(f: FormState): Record<string, unknown> {
  const base: Record<string, unknown> = { partner_type: f.partnerType }
  if (f.partnerType === "INDIVIDUAL") {
    base.first_name = f.firstName
    base.date_of_birth = f.dateOfBirth || null
  }
  base.email = f.email
  return base
}
```

### Backend → frontend form population
```typescript
function fromDetail(d: Detail): FormState {
  return {
    partnerType: d.partnerType,
    firstName: d.firstName || "",
    dateOfBirth: d.dateOfBirth || "",
    email: d.email || "",
    // ...
  }
}
```

### Save → redirect to detail, or advance step
```typescript
async function handleSave() {
  const err = validateDetails()
  if (err) { setError(err); return }

  if (isEdit) {
    await updateApplication(id!, toPayload(form))
    setStep("documents")  // advance in edit mode
  } else {
    const result = await createApplication(toPayload(form))
    navigate(`/onboarding/${(result as Detail).id}`)  // redirect to detail
  }
}
```

### Submit with required documents check
```typescript
async function handleSubmit() {
  if (docs.length === 0) {
    setError("At least one document is required")
    return
  }
  await submitApplication(id!)
  navigate(`/onboarding/${id}`)
}
```

## Detail Page Pattern

### Load detail + nested resources in parallel
```typescript
useEffect(() => {
  const [appData, docsData, tasksData] = await Promise.all([
    getApplication(id!),
    listDocuments(id!),
    listTasks(id!),
  ])
  setApp(appData)
  setDocs(docsData)
  setTasks(tasksData)
}, [id])
```

### Status timeline visualization
```typescript
const STATUS_FLOW: ApplicationStatus[] = [
  "DRAFT", "SUBMITTED", "UNDER_REVIEW", "COMPLIANCE_CHECK", "APPROVED", "CONVERTED",
]
const statusIdx = STATUS_FLOW.indexOf(app.status)

// Render: done (green) / current (primary) / future (muted)
{STATUS_FLOW.map((s, i) => {
  const done = i < statusIdx
  const current = s === app.status
  return (
    <div className={done ? "bg-green-100" : current ? "bg-primary" : "bg-muted"}>
      {STATUS_LABELS[s]}
    </div>
  )
})}
```

### Contextual action buttons based on current status
```typescript
const actions = []
if (app.status === "DRAFT") {
  actions.push({ label: "Submit", fn: () => submitApplication(app.id), variant: "primary" })
  actions.push({ label: "Edit", fn: () => navigate(`/onboarding/${app.id}/edit`) })
}
if (app.status === "UNDER_REVIEW") {
  actions.push({ label: "Send to Compliance", fn: () => sendToCompliance(app.id) })
}
if (app.status === "COMPLIANCE_CHECK") {
  actions.push({ label: "Approve", fn: () => approveApplication(app.id), variant: "green" })
  actions.push({ label: "Reject", fn: () => setShowRejectModal(true), variant: "red" })
}
if (app.status === "APPROVED") {
  actions.push({ label: "Convert", fn: () => convertApplication(app.id), variant: "emerald" })
}
```

### Action execution with loading state
```typescript
const [actionLoading, setActionLoading] = useState<string | null>(null)

async function doAction(actionKey: string, fn: () => Promise<unknown>) {
  setActionLoading(actionKey)
  try {
    await fn()
    load()  // refresh detail after action
  } catch (e) {
    setError(e instanceof Error ? e.message : "Action failed")
  } finally {
    setActionLoading(null)
  }
}
```

### Reject modal pattern
```typescript
{showRejectModal && (
  <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
    <div className="w-full max-w-md rounded-xl bg-card p-6">
      <h3>Reject Application</h3>
      <textarea value={rejectReason} onChange={e => setRejectReason(e.target.value)} />
      <button onClick={() => {
        setShowRejectModal(false)
        doAction("reject", () => rejectApplication(app.id, rejectReason))
      }}>Reject</button>
    </div>
  </div>
)}
```

### Tabbed content (details, documents, tasks)
```typescript
const [tab, setTab] = useState<"details" | "documents" | "tasks">("details")

{tab === "details" && <DetailsTab app={app} />}
{tab === "documents" && <DocumentsTab docs={docs} applicationId={app.id} onRefresh={load} />}
{tab === "tasks" && <TasksTab tasks={tasks} applicationId={app.id} onRefresh={load} />}
```

## Nested Resource Patterns

### Documents tab
- Upload via file input + document type selector
- FormData POST (no JSON Content-Type)
- Verify action (admin-only on backend)
- Delete action (only when application is DRAFT)

### Tasks tab
- Inline create form (title, type, priority, due date)
- Status badges with color coding
- "Complete" button for non-terminal tasks
- Create → refresh, Complete → refresh

## Common Pitfalls

- **FormData uploads**: Do NOT set `Content-Type` header — the browser must set it with the multipart boundary. Only set `Authorization`.
- **Paginated vs plain arrays**: Nested resource endpoints may return paginated `{ results: [...] }` or plain arrays. Always fallback: `json.results ?? json.data ?? json`.
- **State transition validation**: The backend enforces valid transitions. The frontend should only show actions that are valid for the current status. Don't rely on client-side validation alone.
- **Edit mode redirect**: After saving a new application, redirect to the detail page (which has the ID). Don't stay on the form — the form needs an ID for subsequent document uploads.
- **Document requirement for submit**: The backend requires at least one document before submission. Check `docs.length > 0` before enabling the submit button.
- **Concurrent action prevention**: Disable all action buttons while any action is in progress (`actionLoading !== null`).
