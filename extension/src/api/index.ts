// Single entry point for the API layer, grouped by domain (mirrors the web app).
export { Api, BackendError, getTokenExpiryMs } from "./api.js";

import * as auth from "./auth.js";
import { checkHealth } from "./health.js";
import { listModels } from "./models.js";
import { createSession } from "./sessions.js";
import { streamChat } from "./client.js";

export const api = {
  auth,
  health: { check: checkHealth },
  models: { list: listModels },
  sessions: { create: createSession },
  chat: { stream: streamChat },
};
