import { Api, BackendError } from "./api.js";
import type { Effort, StreamEvent } from "../types.js";

// Streaming client. Kept separate from the verb helpers in api.ts because SSE
// needs the raw response body, not parsed JSON. Auth + base URL come from Api.

export interface ChatBody {
  session_id: string;
  message: string;
  context: string | null;
  provider: string;
  model: string;
  effort: Effort | null;
}

// POST /api/chat — streams normalized SSE events; yields each parsed StreamEvent.
export async function* streamChat(body: ChatBody, signal: AbortSignal): AsyncGenerator<StreamEvent> {
  const res = await fetch(`${Api.baseUrl}/api/chat`, {
    method: "POST",
    headers: { ...Api.authHeaders(), Accept: "text/event-stream" },
    body: JSON.stringify(body),
    signal,
  });
  if (!res.ok || !res.body) {
    throw new BackendError(`POST /api/chat failed (${res.status})`, res.status);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }
    buffer += decoder.decode(value, { stream: true });
    // SSE frames are separated by a blank line; keep the trailing partial frame.
    let sep: number;
    while ((sep = buffer.indexOf("\n\n")) !== -1) {
      const frame = buffer.slice(0, sep);
      buffer = buffer.slice(sep + 2);
      const event = parseFrame(frame);
      if (event) {
        yield event;
      }
    }
  }
}

function parseFrame(frame: string): StreamEvent | null {
  const dataLine = frame.split("\n").find((line) => line.startsWith("data:"));
  if (!dataLine) {
    return null;
  }
  try {
    return JSON.parse(dataLine.slice(5).trim()) as StreamEvent;
  } catch {
    return null;
  }
}
