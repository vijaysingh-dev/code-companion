import * as vscode from "vscode";

export class ResponsePanel {
  private static currentPanel: vscode.WebviewPanel | undefined;

  // Open or reuse the panel and render the latest response
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

      this.currentPanel.onDidDispose(() => {
        this.currentPanel = undefined;
      });
    }

    this.currentPanel.webview.html = buildHtml(question, response);
  }
}

// Build the full HTML page with markdown-like rendering for the response
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
        /* Base layout and typography */
        body {
          font-family: var(--vscode-editor-font-family, monospace);
          font-size: 14px;
          padding: 20px;
          color: var(--vscode-editor-foreground);
          background: var(--vscode-editor-background);
          line-height: 1.6;
        }

        /* Question header styling */
        .question {
          background: var(--vscode-textBlockQuote-background);
          border-left: 3px solid var(--vscode-focusBorder);
          padding: 10px 14px;
          margin-bottom: 20px;
          border-radius: 4px;
          font-style: italic;
        }

        /* Code block styling */
        pre {
          background: var(--vscode-textCodeBlock-background);
          padding: 12px;
          border-radius: 4px;
          overflow-x: auto;
          white-space: pre-wrap;
          word-wrap: break-word;
        }
      </style>
    </head>
    <body>
      <div class="question">❓ ${question}</div>
      <div id="response"><pre>${escaped}</pre></div>
      <script>
        // Basic markdown-to-HTML conversion for code blocks and bold text
        const raw = document.getElementById('response').querySelector('pre').textContent;
        const rendered = raw
          .replace(/\`\`\`(\w+)?\n([\s\S]*?)\`\`\`/g, '<pre><code>$2</code></pre>')
          .replace(/\`([^\`]+)\`/g, '<code>$1</code>')
          .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
          .replace(/\n/g, '<br>');
        document.getElementById('response').innerHTML = rendered;
      </script>
    </body>
    </html>
  `;
}
