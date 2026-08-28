import { setupServer } from "msw/node"
import { policiesHandlers } from "./policiesHandlers"
import { receiptsHandlers } from "./receiptsHandlers"
import { loansHandlers } from "./loansHandlers"
import { withdrawalsHandlers } from "./withdrawalsHandlers"
import { claimsHandlers } from "./claimsHandlers"

export const server = setupServer(...receiptsHandlers, ...policiesHandlers, ...loansHandlers, ...withdrawalsHandlers, ...claimsHandlers)
