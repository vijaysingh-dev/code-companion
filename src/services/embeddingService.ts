import { ModelConfig } from "../config/types";

// ─── Unified interface — each provider adapter must implement this ────────────

interface EmbeddingAdapter {
  embedOne(text: string): Promise<number[]>;
  embedMany(texts: string[]): Promise<number[][]>;
}

// ─── OpenAI embedding adapter ─────────────────────────────────────────────────

class OpenAIEmbeddingAdapter implements EmbeddingAdapter {
  private client: import("openai").default;

  constructor(private config: ModelConfig) {
    const OpenAI = require("openai").default;
    this.client = new OpenAI({ apiKey: config.apiKey });
  }

  async embedOne(text: string): Promise<number[]> {
    const res = await this.client.embeddings.create({
      model: this.config.model,
      input: text,
    });
    return res.data[0].embedding;
  }

  async embedMany(texts: string[]): Promise<number[][]> {
    const res = await this.client.embeddings.create({
      model: this.config.model,
      input: texts,
    });
    return res.data.map((d: { embedding: number[] }) => d.embedding);
  }
}

// ─── Google Gemini embedding adapter ─────────────────────────────────────────

class GeminiEmbeddingAdapter implements EmbeddingAdapter {
  private genai: import("@google/generative-ai").GoogleGenerativeAI;

  constructor(private config: ModelConfig) {
    const { GoogleGenerativeAI } = require("@google/generative-ai");
    this.genai = new GoogleGenerativeAI(config.apiKey);
  }

  async embedOne(text: string): Promise<number[]> {
    const model = this.genai.getGenerativeModel({ model: this.config.model });
    const result = await model.embedContent(text);
    return result.embedding.values;
  }

  async embedMany(texts: string[]): Promise<number[][]> {
    return Promise.all(texts.map((t) => this.embedOne(t)));
  }
}

// ─── Anthropic does not offer a public embedding API — surface clear error ───

class AnthropicEmbeddingAdapter implements EmbeddingAdapter {
  async embedOne(_text: string): Promise<number[]> {
    throw new Error(
      "Anthropic does not provide an embedding API. Use 'openai' or 'gemini'.",
    );
  }

  async embedMany(_texts: string[]): Promise<number[][]> {
    throw new Error(
      "Anthropic does not provide an embedding API. Use 'openai' or 'gemini'.",
    );
  }
}

// ─── Public service — delegates to the correct adapter from config ────────────

export class EmbeddingService {
  private adapter: EmbeddingAdapter;

  constructor(config: ModelConfig) {
    switch (config.provider) {
      case "openai":
        this.adapter = new OpenAIEmbeddingAdapter(config);
        break;
      case "gemini":
        this.adapter = new GeminiEmbeddingAdapter(config);
        break;
      case "anthropic":
        this.adapter = new AnthropicEmbeddingAdapter();
        break;
      default:
        throw new Error(
          `Unknown embedding provider: ${(config as ModelConfig).provider}`,
        );
    }
  }

  embedOne(text: string): Promise<number[]> {
    return this.adapter.embedOne(text);
  }

  embedMany(texts: string[]): Promise<number[][]> {
    return this.adapter.embedMany(texts);
  }
}
