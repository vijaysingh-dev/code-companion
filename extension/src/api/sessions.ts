import { Api } from "./api.js";
import type { SessionInfo } from "../types.js";

// POST /api/sessions — create a server-side session bound to a provider/model.
export function createSession(provider: string, model: string): Promise<SessionInfo> {
  return Api.post<SessionInfo>("/api/sessions", { provider, model });
}
