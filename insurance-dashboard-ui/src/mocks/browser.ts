import { setupWorker } from "msw/browser"
import { receiptsHandlers } from "./receiptsHandlers"

export const worker = setupWorker(...receiptsHandlers)
