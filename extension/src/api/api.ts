import * as vscode from "vscode";

// Core HTTP client for the Code Companion backend. Mirrors the singleton
// `ApiService` pattern from the web app: one place owns the base URL, the
// bearer token, expiry handling, and the generic verb helpers. Domain calls
// live in sibling files (auth, models, sessions) and streaming in client.ts.

const SECTION = "codeCompanion";
const TOKEN_KEY = "codeCompanion.token";
const MAX_TIMEOUT_MS = 2_147_483_647; // setTimeout caps here (~24.8 days); longer delays fire instantly

// Thrown for non-2xx responses so callers can surface a clean message; `status`
// lets callers special-case 401 (expired/invalid token → re-login).
export class BackendError extends Error {
  constructor(
    message: string,
    public readonly status?: number,
  ) {
    super(message);
  }
}

interface RequestOptions {
  useAuth?: boolean;
  body?: unknown;
  signal?: AbortSignal;
}

class ApiService {
  private secrets: vscode.SecretStorage | undefined;
  private token = "";
  private clearTimer: ReturnType<typeof setTimeout> | undefined;
  private readonly authChanged = new vscode.EventEmitter<boolean>();

  /** Fires with the current auth state whenever the token is set, cleared, or expires. */
  readonly onDidChangeAuth = this.authChanged.event;

  /** Called once from activate(): loads the stored token and checks expiry on startup. */
  async init(context: vscode.ExtensionContext): Promise<void> {
    this.secrets = context.secrets;
    context.subscriptions.push(
      this.authChanged,
      this.secrets.onDidChange((e) => {
        if (e.key === TOKEN_KEY) {
          void this.reload();
        }
      }),
    );
    await this.reload();
  }

  get baseUrl(): string {
    const url = vscode.workspace.getConfiguration(SECTION).get<string>("backendUrl") ?? "http://127.0.0.1:8000";
    return url.replace(/\/+$/, "");
  }

  isAuthenticated(): boolean {
    return Boolean(this.token) && getTokenExpiryMs(this.token) > 0;
  }

  async setToken(token: string): Promise<void> {
    await this.secrets?.store(TOKEN_KEY, token); // onDidChange → reload → schedule + emit
  }

  async logout(): Promise<void> {
    await this.secrets?.delete(TOKEN_KEY);
  }

  /** Auth headers for a request; throws if `useAuth` but we aren't signed in. */
  authHeaders(useAuth = true): Record<string, string> {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (useAuth) {
      if (!this.isAuthenticated()) {
        throw new BackendError("Not signed in — run “Code Companion: Sign In”.", 401);
      }
      headers.Authorization = `Bearer ${this.token}`;
    }
    return headers;
  }

  get<T>(path: string, opts: RequestOptions = {}): Promise<T> {
    return this.request<T>("GET", path, opts);
  }

  post<T>(path: string, body: unknown, opts: RequestOptions = {}): Promise<T> {
    return this.request<T>("POST", path, { ...opts, body });
  }

  patch<T>(path: string, body: unknown, opts: RequestOptions = {}): Promise<T> {
    return this.request<T>("PATCH", path, { ...opts, body });
  }

  del(path: string, opts: RequestOptions = {}): Promise<void> {
    return this.request<void>("DELETE", path, opts);
  }

  private async request<T>(method: string, path: string, { useAuth = true, body, signal }: RequestOptions): Promise<T> {
    const res = await fetch(`${this.baseUrl}${path}`, {
      method,
      headers: this.authHeaders(useAuth),
      body: body === undefined ? undefined : JSON.stringify(body),
      signal,
    });
    if (!res.ok) {
      throw new BackendError(`${method} ${path} failed (${res.status})`, res.status);
    }
    return res.status === 204 ? (undefined as T) : ((await res.json()) as T);
  }

  private async reload(): Promise<void> {
    this.token = (await this.secrets?.get(TOKEN_KEY)) ?? "";
    this.scheduleExpiry();
  }

  // On (re)load: clear an already-expired token, otherwise arm a timer to clear
  // it exactly when it expires. Either way, broadcast the resulting auth state.
  private scheduleExpiry(): void {
    if (this.clearTimer) {
      clearTimeout(this.clearTimer);
      this.clearTimer = undefined;
    }
    if (!this.token) {
      this.authChanged.fire(false);
      return;
    }
    const remaining = getTokenExpiryMs(this.token);
    if (remaining <= 0) {
      void this.logout(); // → onDidChange → reload → fire(false)
      return;
    }
    this.authChanged.fire(true);
    if (remaining <= MAX_TIMEOUT_MS) {
      this.clearTimer = setTimeout(() => void this.logout(), remaining);
    }
  }
}

export const Api = new ApiService();

/** Milliseconds until the token expires; 0 if expired, malformed, or unparsable. */
export function getTokenExpiryMs(token: string): number {
  const exp = decodeJwt(token)?.exp;
  const seconds = typeof exp === "number" ? exp : 0;
  return Math.max(seconds - Math.floor(Date.now() / 1000), 0) * 1000;
}

function decodeJwt(token: string): { exp?: number; sub?: string } | null {
  const part = token.split(".")[1];
  if (!part) {
    return null;
  }
  try {
    let b64 = part.replace(/-/g, "+").replace(/_/g, "/");
    b64 += "=".repeat((4 - (b64.length % 4)) % 4);
    return JSON.parse(atob(b64)) as { exp?: number; sub?: string };
  } catch {
    return null;
  }
}
