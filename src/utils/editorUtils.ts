import * as vscode from "vscode";

export const SUPPORTED_EXTENSIONS = new Set([
  ".ts",
  ".tsx",
  ".js",
  ".jsx",
  ".py",
  ".go",
  ".java",
  ".cpp",
  ".c",
  ".cs",
  ".rb",
  ".rs",
  ".php",
  ".swift",
  ".kt",
]);

// Get the text currently selected in the active editor
export function getSelectedCode(): string | null {
  const editor = vscode.window.activeTextEditor;
  if (!editor || editor.selection.isEmpty) return null;
  return editor.document.getText(editor.selection);
}

// Get the file system path of the currently open document
export function getActiveFilePath(): string | null {
  return vscode.window.activeTextEditor?.document.uri.fsPath ?? null;
}
