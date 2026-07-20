import * as vscode from "vscode";

// Phase 0: bare activation. The chat panel + backend client get built here next.
// The old RAG-in-the-extension code lives in .archive/extension-legacy/ for reference.
export function activate(_context: vscode.ExtensionContext): void {
  console.log("Code Companion is now active");
}

export function deactivate(): void {}
