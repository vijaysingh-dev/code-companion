// ─── Supported provider identifiers ─────────────────────────────────────────

export type Provider = "openai" | "anthropic" | "gemini";

// ─── Config shape for a single model slot (embedding or inference) ───────────

export interface ModelConfig {
  provider: Provider;
  model: string;
  apiKey: string;
}

// ─── ChromaDB configuration ──────────────────────────────────────────────────

export interface ChromaConfig {
  uri?: string; // Optional URI for ChromaDB server, defaults to localhost:8000
}

// ─── Top-level config file structure ─────────────────────────────────────────

export interface CodeCompanionConfig {
  embedding: ModelConfig;
  inference: ModelConfig;
  chroma?: ChromaConfig; // Optional ChromaDB configuration
}

// ─── Sane defaults written when user creates a new config file ────────────────

export const DEFAULT_CONFIG: CodeCompanionConfig = {
  embedding: {
    provider: "openai",
    model: "text-embedding-3-small",
    apiKey: "",
  },
  inference: {
    provider: "openai",
    model: "gpt-4o",
    apiKey: "",
  },
  chroma: {
    // URI is optional, defaults to localhost:8000
  },
};
