import * as vscode from "vscode";
import * as fs from "fs";
import * as path from "path";
import { ChromaService } from "./services/chromaService";
import { EmbeddingService } from "./services/embeddingService";
import { InferenceService } from "./services/inferenceService";
import { ContextBuilder } from "./context/contextBuilder";
import { ResponsePanel } from "./ui/responsePanel";
import { getSelectedCode, getActiveFilePath } from "./utils/editorUtils";
import {
  loadConfig,
  getConfigFilePath,
  createDefaultConfig,
} from "./config/configLoader";

type AttachmentType = "file" | "snippet";

interface Attachment {
  type: AttachmentType;
  path: string;
  content: string;
  description: string;
}

export function registerCommands(
  context: vscode.ExtensionContext,
  chromaService: ChromaService,
) {
  // ── Config: open the config file in the editor, create it if missing ────────
  const openConfig = vscode.commands.registerCommand(
    "codeCompanion.openConfig",
    async () => {
      const filePath = getConfigFilePath();

      if (!fs.existsSync(filePath)) {
        const create = await vscode.window.showInformationMessage(
          `Config not found at: ${filePath}. Create it?`,
          "Create",
          "Cancel",
        );
        if (create !== "Create") return;
        createDefaultConfig(filePath);
      }

      const doc = await vscode.workspace.openTextDocument(filePath);
      await vscode.window.showTextDocument(doc);
    },
  );

  // ── Ask: select code / file attachment / code block attachment → infer → show panel ─────
  const askAboutCode = vscode.commands.registerCommand(
    "codeCompanion.askAboutCode",
    async () => {
      const workspaceFolders = vscode.workspace.workspaceFolders;
      if (!workspaceFolders) {
        vscode.window.showWarningMessage("No workspace open.");
        return;
      }

      const workspaceRoot = workspaceFolders[0].uri.fsPath;
      const selectedCode = getSelectedCode() ?? "";
      const attachments: Attachment[] = [];

      const resolveFilePath = async (input: string): Promise<string | null> => {
        const candidate = path.isAbsolute(input)
          ? path.normalize(input)
          : path.normalize(path.join(workspaceRoot, input));
        if (!candidate.startsWith(path.normalize(workspaceRoot + path.sep))) {
          return null;
        }
        return fs.existsSync(candidate) ? candidate : null;
      };

      const promptForFilePath = async (prompt: string) => {
        const relativePath = await vscode.window.showInputBox({
          prompt,
          placeHolder: "src/index.ts or path/to/file.js",
        });
        if (!relativePath) return null;
        const filePath = await resolveFilePath(relativePath);
        if (!filePath) {
          vscode.window.showErrorMessage(
            `Unable to resolve file path: ${relativePath}. Use a path relative to the workspace root.`,
          );
          return null;
        }
        return filePath;
      };

      const addFileAttachment = async () => {
        const filePath = await promptForFilePath(
          "Enter the workspace-relative path of the file to attach.",
        );
        if (!filePath) return;
        const content = fs.readFileSync(filePath, "utf-8");
        attachments.push({
          type: "file",
          path: path.relative(workspaceRoot, filePath),
          content,
          description: `File: ${path.relative(workspaceRoot, filePath)}`,
        });
        vscode.window.showInformationMessage(
          `Added file attachment: ${path.relative(workspaceRoot, filePath)}`,
        );
      };

      const addSnippetAttachment = async () => {
        const filePath = await promptForFilePath(
          "Enter the workspace-relative path of the file containing the snippet.",
        );
        if (!filePath) return;

        const lineRange = await vscode.window.showInputBox({
          prompt: "Enter the start and end line numbers for the snippet (e.g. 10-20).",
          placeHolder: "start-end",
        });
        if (!lineRange) return;

        const match = lineRange.match(/^(\d+)\s*-\s*(\d+)$/);
        if (!match) {
          vscode.window.showErrorMessage(
            "Invalid line range. Use the format start-end.",
          );
          return;
        }

        const startLine = Number(match[1]);
        const endLine = Number(match[2]);
        if (startLine <= 0 || endLine < startLine) {
          vscode.window.showErrorMessage(
            "Invalid line range. The end line must be greater than or equal to the start line.",
          );
          return;
        }

        const fileContent = fs.readFileSync(filePath, "utf-8");
        const lines = fileContent.split(/\r?\n/);
        if (startLine > lines.length) {
          vscode.window.showErrorMessage("Start line is beyond the end of the file.");
          return;
        }

        const snippet = lines
          .slice(startLine - 1, Math.min(endLine, lines.length))
          .join("\n");
        attachments.push({
          type: "snippet",
          path: path.relative(workspaceRoot, filePath),
          content: snippet,
          description: `Snippet from ${path.relative(workspaceRoot, filePath)}:${startLine}-${Math.min(endLine, lines.length)}`,
        });
        vscode.window.showInformationMessage(
          `Added snippet attachment from ${path.relative(workspaceRoot, filePath)}:${startLine}-${Math.min(endLine, lines.length)}`,
        );
      };

      while (true) {
        const choices: vscode.QuickPickItem[] = [
          {
            label: "Add file attachment",
            description: "Attach a file by workspace-relative path.",
          },
          {
            label: "Add code block from file",
            description: "Attach a specific snippet from a file.",
          },
        ];

        if (selectedCode || attachments.length > 0) {
          choices.push({
            label: "Ask about code",
            description: "Continue to enter your question and run inference.",
          });
        }

        choices.push({
          label: "Cancel",
          description: "Abort the question flow.",
        });

        const action = await vscode.window.showQuickPick(choices, {
          placeHolder: selectedCode
            ? `Selected code is included. Attach files or ask now.`
            : attachments.length
              ? `Attachments added. Ask your question or add more.`
              : `Select a file option to attach content before asking.`,
        });

        if (!action || action.label === "Cancel") {
          return;
        }

        if (action.label === "Add file attachment") {
          await addFileAttachment();
          continue;
        }

        if (action.label === "Add code block from file") {
          await addSnippetAttachment();
          continue;
        }

        if (action.label === "Ask about code") {
          break;
        }
      }

      const question = await vscode.window.showInputBox({
        prompt: "What do you want to know about this code?",
        placeHolder: "e.g. Why is this buggy? What does this do?",
      });
      if (!question) return;

      let config;
      try {
        config = loadConfig();
      } catch (e: unknown) {
        vscode.window.showErrorMessage(String(e instanceof Error ? e.message : e));
        return;
      }

      const embeddingService = new EmbeddingService(config.embedding);
      const inferenceService = new InferenceService(config.inference);
      const contextBuilder = new ContextBuilder(chromaService, embeddingService);

      await vscode.window.withProgress(
        {
          location: vscode.ProgressLocation.Notification,
          title: "Code Companion thinking...",
        },
        async () => {
          const builtContext = await contextBuilder.build(
            question,
            selectedCode,
            attachments,
          );
          const response = await inferenceService.query(question, builtContext);
          ResponsePanel.show(context.extensionUri, question, response);
        },
      );
    },
  );

  // ── Index: embed the currently open file into Chroma ─────────────────────────
  const indexFile = vscode.commands.registerCommand(
    "codeCompanion.indexFile",
    async () => {
      const filePath = getActiveFilePath();
      if (!filePath) {
        vscode.window.showWarningMessage("No active file to index.");
        return;
      }

      let config;
      try {
        config = loadConfig();
      } catch (e: unknown) {
        vscode.window.showErrorMessage(String(e instanceof Error ? e.message : e));
        return;
      }

      const embeddingService = new EmbeddingService(config.embedding);
      const contextBuilder = new ContextBuilder(chromaService, embeddingService);

      await vscode.window.withProgress(
        { location: vscode.ProgressLocation.Notification, title: "Indexing file..." },
        async () => {
          await contextBuilder.indexFile(filePath);
        },
      );

      vscode.window.showInformationMessage(`Indexed: ${filePath}`);
    },
  );

  // ── Index: embed all workspace files into Chroma ─────────────────────────────
  const indexWorkspace = vscode.commands.registerCommand(
    "codeCompanion.indexWorkspace",
    async () => {
      const workspaceFolders = vscode.workspace.workspaceFolders;
      if (!workspaceFolders) {
        vscode.window.showWarningMessage("No workspace open.");
        return;
      }

      let config;
      try {
        config = loadConfig();
      } catch (e: unknown) {
        vscode.window.showErrorMessage(String(e instanceof Error ? e.message : e));
        return;
      }

      const embeddingService = new EmbeddingService(config.embedding);
      const contextBuilder = new ContextBuilder(chromaService, embeddingService);

      await vscode.window.withProgress(
        {
          location: vscode.ProgressLocation.Notification,
          title: "Indexing workspace...",
        },
        async () => {
          await contextBuilder.indexWorkspace(workspaceFolders[0].uri.fsPath);
        },
      );

      vscode.window.showInformationMessage("Workspace indexed.");
    },
  );

  context.subscriptions.push(openConfig, askAboutCode, indexFile, indexWorkspace);
}
