import * as vscode from "vscode";

import { Api } from "./api/api.js";
import * as auth from "./api/auth.js";
import { ChatViewProvider } from "./panel/chatPanel.js";

export async function activate(context: vscode.ExtensionContext): Promise<void> {
  await Api.init(context); // loads the stored token and clears it if already expired

  const provider = new ChatViewProvider(context.extensionUri);

  context.subscriptions.push(
    vscode.window.registerWebviewViewProvider(ChatViewProvider.viewId, provider),
    Api.onDidChangeAuth((authenticated) => provider.setAuthenticated(authenticated)),
    vscode.window.onDidChangeActiveTextEditor(() => provider.syncActiveFile()),
    vscode.commands.registerCommand("codeCompanion.focus", () => void provider.reveal()),
    vscode.commands.registerCommand("codeCompanion.newSession", () => provider.newSession()),
    vscode.commands.registerCommand("codeCompanion.showHistory", () => void provider.goHome()),
    vscode.commands.registerCommand("codeCompanion.openInEditor", () => void provider.openInEditor()),
    vscode.commands.registerCommand("codeCompanion.addActiveFile", () => provider.addActiveFile()),
    vscode.commands.registerCommand("codeCompanion.addFiles", () => void provider.addFiles()),
    vscode.commands.registerCommand("codeCompanion.login", () => void auth.login()),
    vscode.commands.registerCommand("codeCompanion.logout", () => void auth.logout()),
  );
}

export function deactivate(): void {}
