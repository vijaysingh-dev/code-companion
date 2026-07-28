import * as vscode from "vscode";

import { Api, BackendError } from "../api/api.js";
import * as auth from "../api/auth.js";
import { streamChat } from "../api/client.js";
import { checkHealth } from "../api/health.js";
import { listModels } from "../api/models.js";
import { createSession } from "../api/sessions.js";
import { activeFile, buildContextString, pickFiles } from "../context/files.js";
import type { ContextFile, HealthStatus, InboundMessage, ModelInfo, OutboundMessage } from "../types.js";

// Backend liveness is probed only while the view is visible, to avoid a timer
// that runs forever in the background.
const HEALTH_POLL_MS = 30_000;

export class ChatViewProvider implements vscode.WebviewViewProvider {
  public static readonly viewId = "codeCompanion.chat";

  private view: vscode.WebviewView | undefined;
  private panel: vscode.WebviewPanel | undefined;
  private models: ModelInfo[] = [];
  private context: ContextFile[] = [];
  private sessionId: string | null = null;
  private inFlight: AbortController | undefined;
  private health: HealthStatus = "unknown";
  private healthTimer: ReturnType<typeof setInterval> | undefined;

  constructor(private readonly extensionUri: vscode.Uri) {}

  public async resolveWebviewView(view: vscode.WebviewView): Promise<void> {
    this.view = view;
    view.onDidChangeVisibility(() => this.syncHealthPolling());
    view.onDidDispose(() => this.stopHealthPolling());
    await this.render(view.webview);
    this.syncHealthPolling();
  }

  /** Opens (or focuses) the same chat as a full-width webview in the editor area. */
  public async openInEditor(): Promise<void> {
    if (this.panel) {
      this.panel.reveal(vscode.ViewColumn.Active);
      return;
    }
    const panel = vscode.window.createWebviewPanel(
      "codeCompanion.chatEditor",
      "Code Companion",
      vscode.ViewColumn.Active,
      { enableScripts: true, retainContextWhenHidden: true, localResourceRoots: [this.mediaRoot()] },
    );
    this.panel = panel;
    panel.onDidDispose(() => (this.panel = undefined));
    panel.onDidChangeViewState(() => this.syncHealthPolling());
    await this.render(panel.webview);
  }

  private mediaRoot(): vscode.Uri {
    return vscode.Uri.joinPath(this.extensionUri, "media");
  }

  private async render(webview: vscode.Webview): Promise<void> {
    webview.options = { enableScripts: true, localResourceRoots: [this.mediaRoot()] };
    // Attach the listener before the HTML loads so the webview's "ready" isn't missed.
    webview.onDidReceiveMessage((message: InboundMessage) => void this.onMessage(message));
    webview.html = await this.html(webview);
  }

  // ── Command entry points ──────────────────────────────────────────────────
  public async reveal(): Promise<void> {
    await vscode.commands.executeCommand(`${ChatViewProvider.viewId}.focus`);
  }

  public addActiveFile(): void {
    const file = activeFile();
    if (!file) {
      void vscode.window.showInformationMessage("No active file to add.");
      return;
    }
    this.addContext([file]);
  }

  public async addFiles(): Promise<void> {
    this.addContext(await pickFiles());
  }

  public newSession(): void {
    this.inFlight?.abort();
    this.sessionId = null;
    this.context = [];
    this.post({ type: "cleared" });
  }

  // ── Webview messages ──────────────────────────────────────────────────────
  private async onMessage(message: InboundMessage): Promise<void> {
    switch (message.type) {
      case "ready":
        await this.init();
        return;
      case "send":
        await this.handleSend(message);
        return;
      case "stop":
        this.inFlight?.abort();
        return;
      case "newSession":
        this.newSession();
        return;
      case "expand":
        await this.openInEditor();
        return;
      case "addActiveFile":
        this.addActiveFile();
        return;
      case "pickFiles":
        await this.addFiles();
        return;
      case "removeContext":
        this.context = this.context.filter((f) => f.fsPath !== message.fsPath);
        this.post({ type: "context", files: this.context });
        return;
      case "login":
        await auth.login();
        return;
      case "logout":
        await auth.logout();
        return;
    }
  }

  /** Pushes the current auth state to the webview so it can gate the chat UI. */
  public setAuthenticated(authenticated: boolean): void {
    if (!authenticated) {
      this.sessionId = null;
    }
    this.post({ type: "auth", authenticated });
  }

  private async init(): Promise<void> {
    this.post({ type: "health", status: this.health }); // re-sync a freshly (re)loaded webview
    try {
      this.models = await listModels();
      this.post({ type: "init", models: this.models, context: this.context, authenticated: Api.isAuthenticated() });
      this.setHealth("healthy");
    } catch (err) {
      this.post({
        type: "init",
        models: [],
        context: this.context,
        authenticated: Api.isAuthenticated(),
        error: this.describe(err),
      });
      void this.refreshHealth();
    }
  }

  // ── Backend health ─────────────────────────────────────────────────────────
  private syncHealthPolling(): void {
    if (!this.view?.visible && !this.panel?.visible) {
      this.stopHealthPolling();
      return;
    }
    void this.refreshHealth();
    this.healthTimer ??= setInterval(() => void this.refreshHealth(), HEALTH_POLL_MS);
  }

  private stopHealthPolling(): void {
    if (this.healthTimer) {
      clearInterval(this.healthTimer);
      this.healthTimer = undefined;
    }
  }

  private async refreshHealth(): Promise<void> {
    this.setHealth((await checkHealth()) ? "healthy" : "unreachable");
  }

  private setHealth(status: HealthStatus): void {
    if (status === this.health) {
      return;
    }
    this.health = status;
    this.post({ type: "health", status });
  }

  private async handleSend(message: Extract<InboundMessage, { type: "send" }>): Promise<void> {
    this.inFlight?.abort();
    const controller = new AbortController();
    this.inFlight = controller;
    try {
      if (!this.sessionId) {
        const session = await createSession(message.provider, message.model);
        this.sessionId = session.id;
      }
      const supportsEffort = this.models.find((m) => m.model === message.model)?.supports_effort ?? false;
      const context = await buildContextString(this.context);
      const events = streamChat(
        {
          session_id: this.sessionId,
          message: message.text,
          context,
          provider: message.provider,
          model: message.model,
          effort: supportsEffort ? message.effort : null,
        },
        controller.signal,
      );
      for await (const event of events) {
        this.post({ type: "stream", event });
      }
      this.post({ type: "turnEnd" });
      this.setHealth("healthy");
    } catch (err) {
      if (!controller.signal.aborted) {
        this.post({ type: "error", message: this.describe(err) });
        if (err instanceof BackendError && err.status === 401) {
          void auth.requireLogin();
        }
        // A BackendError means the server replied; anything else is a reachability failure.
        if (err instanceof BackendError) {
          this.setHealth("healthy");
        } else {
          void this.refreshHealth();
        }
      }
      this.post({ type: "turnEnd" });
    } finally {
      if (this.inFlight === controller) {
        this.inFlight = undefined;
      }
    }
  }

  private addContext(files: ContextFile[]): void {
    for (const file of files) {
      if (!this.context.some((f) => f.fsPath === file.fsPath)) {
        this.context.push(file);
      }
    }
    this.post({ type: "context", files: this.context });
  }

  private describe(err: unknown): string {
    if (err instanceof BackendError) {
      return err.message;
    }
    return err instanceof Error ? err.message : String(err);
  }

  // Broadcast to every live surface so the sidebar view and the editor tab stay in sync.
  private post(message: OutboundMessage): void {
    for (const webview of [this.view?.webview, this.panel?.webview]) {
      void webview?.postMessage(message);
    }
  }

  // Loads media/index.html and fills the {{...}} placeholders with the CSP,
  // a per-load nonce, and webview-safe resource URLs.
  private async html(webview: vscode.Webview): Promise<string> {
    const nonce = getNonce();
    const uri = (...parts: string[]): string =>
      webview.asWebviewUri(vscode.Uri.joinPath(this.extensionUri, "media", ...parts)).toString();
    const csp = [
      "default-src 'none'",
      `img-src ${webview.cspSource}`,
      `style-src ${webview.cspSource}`,
      `script-src 'nonce-${nonce}' ${webview.cspSource}`,
    ].join("; ");
    const bytes = await vscode.workspace.fs.readFile(vscode.Uri.joinPath(this.extensionUri, "media", "index.html"));
    return new TextDecoder()
      .decode(bytes)
      .replaceAll("{{csp}}", csp)
      .replaceAll("{{nonce}}", nonce)
      .replaceAll("{{styleUri}}", uri("styles.css"))
      .replaceAll("{{scriptUri}}", uri("main.js"));
  }
}

function getNonce(): string {
  const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
  let text = "";
  for (let i = 0; i < 32; i++) {
    text += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return text;
}
