import * as vscode from "vscode";

export class ResponsePanel {
  private static currentPanel: vscode.WebviewPanel | undefined;

  // Open or reuse the side panel, inject question and markdown response
  static show(extensionUri: vscode.Uri, question: string, response: string) {
    if (this.currentPanel) {
      this.currentPanel.reveal(vscode.ViewColumn.Beside);
    } else {
      this.currentPanel = vscode.window.createWebviewPanel(
        "codeCompanionResponse",
        "Code Companion",
        vscode.ViewColumn.Beside,
        { enableScripts: true },
      );

      // Handle gear icon click from inside the webview
      this.currentPanel.webview.onDidReceiveMessage((msg) => {
        if (msg.command === "openConfig") {
          vscode.commands.executeCommand("codeCompanion.openConfig");
        }
      });

      this.currentPanel.onDidDispose(() => {
        this.currentPanel = undefined;
      });
    }

    this.currentPanel.webview.html = buildHtml(question, response);
  }
}

// Build the full webview HTML — header with gear, question block, markdown response
function buildHtml(question: string, response: string): string {
  const escaped = response
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  return /* html */ `
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8" />
      <style>
        /* ── Base layout ──────────────────────────────────────────────────── */
        body {
          font-family: var(--vscode-editor-font-family, monospace);
          font-size: 14px;
          padding: 0;
          margin: 0;
          color: var(--vscode-editor-foreground);
          background: var(--vscode-editor-background);
          line-height: 1.6;
        }

        /* ── Top header bar with title and settings gear ──────────────────── */
        .header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 10px 16px;
          border-bottom: 1px solid var(--vscode-panel-border);
          background: var(--vscode-titleBar-activeBackground);
          position: sticky;
          top: 0;
          z-index: 10;
        }
        .header-title {
          font-weight: 600;
          font-size: 13px;
          letter-spacing: 0.3px;
          opacity: 0.9;
        }
        .gear-btn {
          background: none;
          border: none;
          cursor: pointer;
          padding: 4px 6px;
          border-radius: 4px;
          color: var(--vscode-editor-foreground);
          opacity: 0.7;
          font-size: 16px;
          line-height: 1;
          transition: opacity 0.15s, background 0.15s;
        }
        .gear-btn:hover {
          opacity: 1;
          background: var(--vscode-toolbar-hoverBackground);
        }
        .gear-btn title { display: none; }

        /* ── Content area ─────────────────────────────────────────────────── */
        .content {
          padding: 16px 20px;
        }
        .question {
          background: var(--vscode-textBlockQuote-background);
          border-left: 3px solid var(--vscode-focusBorder);
          padding: 10px 14px;
          margin-bottom: 20px;
          border-radius: 4px;
          font-style: italic;
          font-size: 13px;
        }

        /* ── Code blocks ──────────────────────────────────────────────────── */
        pre, code {
          background: var(--vscode-textCodeBlock-background);
          border-radius: 4px;
          font-family: var(--vscode-editor-font-family, monospace);
        }
        pre {
          padding: 12px;
          overflow-x: auto;
          white-space: pre-wrap;
          word-wrap: break-word;
        }
        code {
          padding: 1px 5px;
          font-size: 0.92em;
        }
      </style>
    </head>
    <body>
      <div class="header">
        <span class="header-title">⚡ Code Companion</span>
        <button class="gear-btn" id="gearBtn" title="Open Config">⚙</button>
      </div>

      <div class="content">
        <div class="question">❓ ${question}</div>
        <div id="response"><pre id="raw" style="display:none">${escaped}</pre></div>
      </div>

      <script>
        // ── Gear icon → tell extension to open config file ──────────────────
        const vscode = acquireVsCodeApi();
        document.getElementById('gearBtn').addEventListener('click', () => {
          vscode.postMessage({ command: 'openConfig' });
        });

        // ── Lightweight markdown renderer for the response ──────────────────
        const raw = document.getElementById('raw').textContent;
        const rendered = raw
          .replace(/\`\`\`(\w+)?\n([\s\S]*?)\`\`\`/g, '<pre><code>$2</code></pre>')
          .replace(/\`([^\`]+)\`/g, '<code>$1</code>')
          .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
          .replace(/^### (.+)$/gm, '<h3>$1</h3>')
          .replace(/^## (.+)$/gm, '<h2>$1</h2>')
          .replace(/^# (.+)$/gm, '<h1>$1</h1>')
          .replace(/\n/g, '<br>');
        document.getElementById('response').innerHTML = rendered;
      </script>
    </body>
    </html>
  `;
}
