import { setupWorker } from "msw/browser"
import { policiesHandlers } from "./policiesHandlers"
import { receiptsHandlers } from "./receiptsHandlers"

export const worker = setupWorker(...receiptsHandlers, ...policiesHandlers)
