import * as vscode from "vscode";

import type { ContextFile } from "../types.js";

const MAX_CONTEXT_BYTES = 200_000; // guard the single `context` string sent to the backend

function toContextFile(uri: vscode.Uri): ContextFile {
  return { path: vscode.workspace.asRelativePath(uri, false), fsPath: uri.fsPath };
}

// The file open in the active editor, if any (skips non-file schemes like output panes).
export function activeFile(): ContextFile | null {
  const editor = vscode.window.activeTextEditor;
  if (!editor || editor.document.uri.scheme !== "file") {
    return null;
  }
  return toContextFile(editor.document.uri);
}

// A Ctrl+P-style multi-select picker over workspace files.
export async function pickFiles(): Promise<ContextFile[]> {
  const uris = await vscode.workspace.findFiles("**/*", "**/{node_modules,.git,out,dist,.venv}/**", 5000);
  const items: (vscode.QuickPickItem & { uri: vscode.Uri })[] = uris
    .map((uri) => ({ label: vscode.workspace.asRelativePath(uri, false), uri }))
    .sort((a, b) => a.label.localeCompare(b.label));

  const picked = await vscode.window.showQuickPick(items, {
    canPickMany: true,
    matchOnDetail: true,
    placeHolder: "Select files to add to context",
  });
  return (picked ?? []).map((item) => toContextFile(item.uri));
}

// Fold attached files into the single `context` string the backend expects,
// truncating once the budget is exhausted so one large file can't blow the turn.
export async function buildContextString(files: ContextFile[]): Promise<string | null> {
  if (files.length === 0) {
    return null;
  }
  const blocks: string[] = [];
  let used = 0;
  for (const file of files) {
    let text: string;
    try {
      const bytes = await vscode.workspace.fs.readFile(vscode.Uri.file(file.fsPath));
      text = new TextDecoder().decode(bytes);
    } catch {
      continue;
    }
    if (used + text.length > MAX_CONTEXT_BYTES) {
      text = text.slice(0, MAX_CONTEXT_BYTES - used);
    }
    used += text.length;
    blocks.push(`--- ${file.path} ---\n${text}`);
    if (used >= MAX_CONTEXT_BYTES) {
      break;
    }
  }
  return blocks.join("\n\n");
}
