import { Api } from "./api.js";
import type { ModelInfo } from "../types.js";

// GET /api/models — unauthenticated catalog of selectable main-tier models.
export async function listModels(): Promise<ModelInfo[]> {
  const data = await Api.get<{ models: ModelInfo[] }>("/api/models", { useAuth: false });
  return data.models;
}
