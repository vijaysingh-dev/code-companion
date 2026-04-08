import * as fs from "fs";
import * as path from "path";
import { ChromaService } from "../services/chromaService";
import { EmbeddingService } from "../services/embeddingService";
import { chunkCode } from "../utils/chunker";
import { SUPPORTED_EXTENSIONS } from "../utils/editorUtils";

export interface BuildContext {
  selectedCode: string;
  retrievedChunks: string[];
}

export class ContextBuilder {
  constructor(
    private chroma: ChromaService,
    private embeddings: EmbeddingService,
  ) {}

  // Embed the question + selected code, retrieve related chunks from Chroma
  async build(question: string, selectedCode: string): Promise<BuildContext> {
    const queryText = `${question}\n\n${selectedCode}`;
    const queryEmbedding = await this.embeddings.embedOne(queryText);
    const retrievedChunks = await this.chroma.query(queryEmbedding, 5);

    return { selectedCode, retrievedChunks };
  }

  // Read a single file, chunk it, embed chunks, and upsert into Chroma
  async indexFile(filePath: string) {
    const content = fs.readFileSync(filePath, "utf-8");
    const chunks = chunkCode(content);
    if (chunks.length === 0) return;

    const embeddings = await this.embeddings.embedMany(chunks);
    await this.chroma.upsert(chunks, embeddings, filePath);
  }

  // Recursively walk workspace, index all supported code files
  async indexWorkspace(rootPath: string) {
    const files = collectFiles(rootPath);
    for (const file of files) {
      await this.indexFile(file);
    }
  }
}

// Walk directory tree and return all code files with supported extensions
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
