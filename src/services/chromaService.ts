import { ChromaClient, Collection } from "chromadb";

const COLLECTION_NAME = "codebase_chunks";

export class ChromaService {
  private client: ChromaClient;
  private collection!: Collection;

  constructor(uri?: string) {
    // Default to localhost:8000 if no URI provided
    const chromaUri = uri || "http://localhost:8000";
    this.client = new ChromaClient({ path: chromaUri });
  }

  // Connect to Chroma and get-or-create the persistent collection
  async init() {
    this.collection = await this.client.getOrCreateCollection({
      name: COLLECTION_NAME,
      metadata: { "hnsw:space": "cosine" },
    });
  }

  // Upsert code chunks with embeddings and source file metadata
  async upsert(chunks: string[], embeddings: number[][], filePath: string) {
    const ids = chunks.map((_, i) => `${filePath}::chunk::${i}::${Date.now()}`);
    await this.collection.upsert({
      ids,
      embeddings,
      documents: chunks,
      metadatas: chunks.map(() => ({ filePath })),
    });
  }

  // Retrieve the top-k most relevant chunks for a given query embedding
  async query(queryEmbedding: number[], topK = 5): Promise<string[]> {
    const results = await this.collection.query({
      queryEmbeddings: [queryEmbedding],
      nResults: topK,
    });
    return (results.documents?.[0]?.filter(Boolean) as string[]) ?? [];
  }
}
