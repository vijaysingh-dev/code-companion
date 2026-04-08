import * as vscode from "vscode";
import { ChromaService } from "./services/chromaService";
import { EmbeddingService } from "./services/embeddingService";
import { LLMService } from "./services/llmService";
import { ContextBuilder } from "./context/contextBuilder";
import { ResponsePanel } from "./ui/responsePanel";
import { getSelectedCode, getActiveFilePath } from "./utils/editorUtils";

export function registerCommands(
  context: vscode.ExtensionContext,
  chromaService: ChromaService,
  embeddingService: EmbeddingService,
) {
  const llmService = new LLMService();
  const contextBuilder = new ContextBuilder(chromaService, embeddingService);

  // Command: Ask AI about currently selected code
  const askAboutCode = vscode.commands.registerCommand(
    "codeCompanion.askAboutCode",
    async () => {
      const selectedCode = getSelectedCode();
      if (!selectedCode) {
        vscode.window.showWarningMessage("Select some code first.");
        return;
      }

      const question = await vscode.window.showInputBox({
        prompt: "What do you want to know about this code?",
        placeHolder: "e.g. Why is this buggy? What does this do?",
      });
      if (!question) return;

      await handleQuery(question, selectedCode, context, contextBuilder, llmService);
    },
  );

  // Command: Index a file manually into Chroma for retrieval
  const indexFile = vscode.commands.registerCommand(
    "codeCompanion.indexFile",
    async () => {
      const filePath = getActiveFilePath();
      if (!filePath) {
        vscode.window.showWarningMessage("No active file to index.");
        return;
      }

      await vscode.window.withProgress(
        { location: vscode.ProgressLocation.Notification, title: "Indexing file..." },
        async () => {
          await contextBuilder.indexFile(filePath);
        },
      );

      vscode.window.showInformationMessage(`Indexed: ${filePath}`);
    },
  );

  // Command: Index all files in the current workspace
  const indexWorkspace = vscode.commands.registerCommand(
    "codeCompanion.indexWorkspace",
    async () => {
      const workspaceFolders = vscode.workspace.workspaceFolders;
      if (!workspaceFolders) {
        vscode.window.showWarningMessage("No workspace open.");
        return;
      }

      await vscode.window.withProgress(
        {
          location: vscode.ProgressLocation.Notification,
          title: "Indexing workspace...",
        },
        async () => {
          await contextBuilder.indexWorkspace(workspaceFolders[0].uri.fsPath);
        },
      );

      vscode.window.showInformationMessage("Workspace indexed successfully.");
    },
  );

  context.subscriptions.push(askAboutCode, indexFile, indexWorkspace);
}

// Build context, call LLM, display response in webview panel
async function handleQuery(
  question: string,
  selectedCode: string,
  context: vscode.ExtensionContext,
  contextBuilder: ContextBuilder,
  llmService: LLMService,
) {
  await vscode.window.withProgress(
    { location: vscode.ProgressLocation.Notification, title: "Thinking..." },
    async () => {
      const builtContext = await contextBuilder.build(question, selectedCode);
      const response = await llmService.query(question, builtContext);
      ResponsePanel.show(context.extensionUri, question, response);
    },
  );
}
