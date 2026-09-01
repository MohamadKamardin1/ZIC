import { setupWorker } from "msw/browser"
import { policiesHandlers } from "./policiesHandlers"
import { receiptsHandlers } from "./receiptsHandlers"
import { loansHandlers } from "./loansHandlers"
import { withdrawalsHandlers } from "./withdrawalsHandlers"
import { claimsHandlers } from "./claimsHandlers"
import { maturityInstallmentsHandlers } from "./maturityInstallmentsHandlers"

export const worker = setupWorker(...receiptsHandlers, ...policiesHandlers, ...loansHandlers, ...withdrawalsHandlers, ...claimsHandlers, ...maturityInstallmentsHandlers)
