import { setupServer } from "msw/node"
import { policiesHandlers } from "./policiesHandlers"
import { receiptsHandlers } from "./receiptsHandlers"

export const server = setupServer(...receiptsHandlers, ...policiesHandlers)
