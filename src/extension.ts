import * as vscode from "vscode";
import { registerCommands } from "./commands";
import { ChromaService } from "./services/chromaService";
import { loadConfig, getConfigFilePath } from "./config/configLoader";
import * as fs from "fs";

// Bootstrap Chroma and register all extension commands on activation
export async function activate(context: vscode.ExtensionContext) {
  console.log("Code Companion is now active");

  // Load config to get ChromaDB URI
  let chromaUri: string | undefined;
  try {
    if (fs.existsSync(getConfigFilePath())) {
      const config = loadConfig();
      chromaUri = config.chroma?.uri;
    }
  } catch (error) {
    // Config might not exist yet, use default
    console.log("Config not found, using default ChromaDB URI");
  }

  const chromaService = new ChromaService(chromaUri);

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
