import { Api } from "./api.js";
import type { SessionDetail, SessionInfo } from "../types.js";

// POST /api/sessions — create a server-side session bound to a provider/model.
export function createSession(provider: string, model: string): Promise<SessionInfo> {
  return Api.post<SessionInfo>("/api/sessions", { provider, model });
}

// GET /api/sessions — the caller's sessions, newest first.
export async function listSessions(): Promise<SessionInfo[]> {
  const data = await Api.get<{ sessions: SessionInfo[] }>("/api/sessions");
  return data.sessions;
}

// GET /api/sessions/{id} — a session with its full message history.
export function getSession(id: string): Promise<SessionDetail> {
  return Api.get<SessionDetail>(`/api/sessions/${id}`);
}

// PATCH /api/sessions/{id} — rename a session.
export function updateSessionTitle(id: string, title: string): Promise<SessionInfo> {
  return Api.patch<SessionInfo>(`/api/sessions/${id}`, { title });
}

// DELETE /api/sessions/{id} — remove a session and its messages.
export function deleteSession(id: string): Promise<void> {
  return Api.del(`/api/sessions/${id}`);
}
