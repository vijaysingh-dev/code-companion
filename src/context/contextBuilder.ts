import * as fs from "fs";
import * as path from "path";
import { ChromaService } from "../services/chromaService";
import { EmbeddingService } from "../services/embeddingService";
import { chunkCode } from "../utils/chunker";
import { SUPPORTED_EXTENSIONS } from "../utils/editorUtils";

export interface Attachment {
  type: "file" | "snippet";
  path: string;
  content: string;
  description: string;
}

export interface BuiltContext {
  selectedCode: string;
  retrievedChunks: string[];
  attachments: Attachment[];
}

export class ContextBuilder {
  constructor(
    private chroma: ChromaService,
    private embeddings: EmbeddingService,
  ) {}

  // Embed the question + selected code + attachments together, then retrieve related chunks
  async build(
    question: string,
    selectedCode: string,
    attachments: Attachment[],
  ): Promise<BuiltContext> {
    const queryParts = [question];

    if (selectedCode.trim()) {
      queryParts.push(`Selected Code:\n${selectedCode}`);
    }

    for (const attachment of attachments) {
      queryParts.push(
        `Attachment: ${attachment.description}\nPath: ${attachment.path}\n${attachment.content}`,
      );
    }

    const queryText = queryParts.join("\n\n");
    const queryEmbedding = await this.embeddings.embedOne(queryText);
    const retrievedChunks = await this.chroma.query(queryEmbedding, 5);
    return { selectedCode, retrievedChunks, attachments };
  }

  // Chunk a single file, embed the chunks, and upsert into Chroma
  async indexFile(filePath: string) {
    const content = fs.readFileSync(filePath, "utf-8");
    const chunks = chunkCode(content);
    if (chunks.length === 0) return;

    const embeddings = await this.embeddings.embedMany(chunks);
    await this.chroma.upsert(chunks, embeddings, filePath);
  }

  // Walk the workspace and index all supported code files
  async indexWorkspace(rootPath: string) {
    const files = collectFiles(rootPath);
    for (const file of files) {
      await this.indexFile(file);
    }
  }
}

// Recursively collect all code files, skipping build and dependency folders
function collectFiles(dir: string): string[] {
  const results: string[] = [];
  const IGNORED_DIRS = new Set(["node_modules", ".git", "dist", "out", ".vscode"]);

  function walk(current: string) {
    const entries = fs.readdirSync(current, { withFileTypes: true });
    for (const entry of entries) {
      const fullPath = path.join(current, entry.name);
      if (entry.isDirectory()) {
        if (!IGNORED_DIRS.has(entry.name)) walk(fullPath);
      } else if (SUPPORTED_EXTENSIONS.has(path.extname(entry.name))) {
        results.push(fullPath);
      }
    }
  }

  walk(dir);
  return results;
}
