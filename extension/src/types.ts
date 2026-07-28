// Wire types shared by the extension host and the webview UI.
// Backend DTOs here MUST mirror app/models/schema.py and app/models/response.py.

export type Effort = "low" | "medium" | "high" | "max";

// Ask = answer only; Plan = read/plan, no edits; Agent = edits + asks on risky commands.
// UI-only for now (the backend does not yet act on it).
export type PermissionMode = "ask" | "plan" | "agent";

// Backend reachability shown as a status dot; UI-only, not a wire DTO.
export type HealthStatus = "unknown" | "healthy" | "unreachable";

// Mirrors app/models/schema.py::ModelInfo
export interface ModelInfo {
  provider: string;
  provider_name: string;
  model: string;
  supports_effort: boolean;
}

// Mirrors app/models/schema.py::SessionInfo
export interface SessionInfo {
  id: string;
  provider: string;
  model: string;
  title: string | null;
  created_at: string;
  updated_at: string;
}

// Mirrors app/models/schema.py::MessageInfo
export interface MessageInfo {
  id: number;
  role: string;
  content: string;
  created_at: string;
}

// Mirrors app/models/schema.py::SessionDetail
export interface SessionDetail extends SessionInfo {
  messages: MessageInfo[];
}

// Mirrors app/models/response.py::StreamEvent (only the fields the UI reads).
export type StreamEventType =
  | "message_start"
  | "text_delta"
  | "thinking_delta"
  | "tool_use_start"
  | "tool_use_delta"
  | "tool_use_stop"
  | "usage"
  | "stop"
  | "error"
  | "title"
  | "done";

export interface StreamEvent {
  type: StreamEventType;
  index?: number;
  text?: string;
  tool_id?: string;
  tool_name?: string;
  tool_args_delta?: string;
  stop_reason?: string;
  model?: string;
  error?: string;
  title?: string;
}

// A file attached as context for the next turn.
export interface ContextFile {
  path: string; // workspace-relative, for display
  fsPath: string; // absolute, the source of truth
}

// ── Messages: webview → extension host ──────────────────────────────────────
export type InboundMessage =
  | { type: "ready" }
  | { type: "send"; text: string; mode: PermissionMode; provider: string; model: string; effort: Effort }
  | { type: "stop" }
  | { type: "newSession" }
  | { type: "goHome" }
  | { type: "showHistory" }
  | { type: "openSession"; id: string }
  | { type: "renameSession"; id: string; title: string }
  | { type: "deleteSession"; id: string }
  | { type: "expand" }
  | { type: "pickFiles" }
  | { type: "addActiveFile" }
  | { type: "removeContext"; fsPath: string }
  | { type: "login" }
  | { type: "logout" };

// ── Messages: extension host → webview ──────────────────────────────────────
export type OutboundMessage =
  | { type: "init"; models: ModelInfo[]; context: ContextFile[]; authenticated: boolean; error?: string }
  | { type: "auth"; authenticated: boolean }
  | { type: "models"; models: ModelInfo[] }
  | { type: "context"; files: ContextFile[] }
  | { type: "activeFile"; canAdd: boolean }
  | { type: "sessions"; sessions: SessionInfo[] }
  | { type: "home" }
  | { type: "sessionOpened"; session: SessionDetail }
  | { type: "title"; id: string; title: string }
  | { type: "stream"; event: StreamEvent }
  | { type: "turnEnd" }
  | { type: "cleared" }
  | { type: "health"; status: HealthStatus }
  | { type: "error"; message: string };
