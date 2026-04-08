import * as vscode from "vscode";
import { registerCommands } from "./commands";
import { ChromaService } from "./services/chromaService";
import { EmbeddingService } from "./services/embeddingService";

// Bootstrap all services and register commands on activation
export async function activate(context: vscode.ExtensionContext) {
  console.log("AI Debugging Copilot is now active");

  const chromaService = new ChromaService();
  const embeddingService = new EmbeddingService();

  await chromaService.init();

  registerCommands(context, chromaService, embeddingService);
}

export function deactivate() {}
