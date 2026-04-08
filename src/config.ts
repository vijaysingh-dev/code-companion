import * as vscode from "vscode";

// Fetch a typed value from the extension's VS Code settings namespace
export function getConfig<T>(key: string): T {
  const value = vscode.workspace.getConfiguration("codeCompanion").get<T>(key);
  if (value === undefined) {
    throw new Error(`Missing config: codeCompanion.${key}. Check your settings.json.`);
  }
  return value;
}
