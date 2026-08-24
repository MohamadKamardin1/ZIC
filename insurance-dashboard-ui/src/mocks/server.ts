import { setupServer } from "msw/node"
import { receiptsHandlers } from "./receiptsHandlers"

export const server = setupServer(...receiptsHandlers)
