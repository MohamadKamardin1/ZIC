export async function startReceiptMocks(): Promise<void> {
  if (import.meta.env.VITE_USE_MOCKS !== "true") return
  const { worker } = await import("./browser")
  await worker.start({ onUnhandledRequest: "bypass" })
}
