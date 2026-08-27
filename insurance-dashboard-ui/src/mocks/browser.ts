import { setupWorker } from "msw/browser"
import { policiesHandlers } from "./policiesHandlers"
import { receiptsHandlers } from "./receiptsHandlers"
import { loansHandlers } from "./loansHandlers"
import { withdrawalsHandlers } from "./withdrawalsHandlers"

export const worker = setupWorker(...receiptsHandlers, ...policiesHandlers, ...loansHandlers, ...withdrawalsHandlers)
