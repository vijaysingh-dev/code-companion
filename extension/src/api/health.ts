import { Api } from "./api.js";

// GET /api/health — unauthenticated liveness probe. True if the backend answered
// with 2xx, false if it was unreachable or replied with an error status.
export async function checkHealth(): Promise<boolean> {
  try {
    await Api.get<{ status: string; version: string }>("/api/health", { useAuth: false });
    return true;
  } catch {
    return false;
  }
}
