import * as vscode from "vscode";
import { registerCommands } from "./commands";
import { ChromaService } from "./services/chromaService";

// Bootstrap Chroma and register all extension commands on activation
export async function activate(context: vscode.ExtensionContext) {
  console.log("Code Companion is now active");

  const chromaService = new ChromaService();

  try {
    await chromaService.init();
  } catch {
    vscode.window.showWarningMessage(
      "Code Companion: Could not connect to Chroma. " +
        "Start it with: chroma run --path ./chroma-data",
    );
  }

  registerCommands(context, chromaService);
}

export function deactivate() {}
