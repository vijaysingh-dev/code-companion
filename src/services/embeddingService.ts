import OpenAI from "openai";
import { getConfig } from "../config";

export class EmbeddingService {
  private client: OpenAI;

  constructor() {
    this.client = new OpenAI({ apiKey: getConfig("openaiApiKey") });
  }

  // Embed a single string (used for query-time retrieval)
  async embedOne(text: string): Promise<number[]> {
    const response = await this.client.embeddings.create({
      model: "text-embedding-3-small",
      input: text,
    });
    return response.data[0].embedding;
  }

  // Batch embed multiple chunks (used during file indexing)
  async embedMany(texts: string[]): Promise<number[][]> {
    const response = await this.client.embeddings.create({
      model: "text-embedding-3-small",
      input: texts,
    });
    return response.data.map((d) => d.embedding);
  }
}
